"""
or_core.py — Optimal Crop-Area Allocation: data pipeline + LP models.

Implements the workflow from the Review-I deck (slide 14):

    Dataset -> Filter state/district/season, clean rows
            -> Check production-unit consistency across crops
            -> Average Yield/ha per crop across years
            -> Formulate LP (Max Output / Min Land)
            -> Solve (PuLP-CBC and SciPy linprog-HiGHS, cross-checked)
            -> Compare vs. historical allocation
            -> Sensitivity analysis + multi-district comparison (Review III)

Every function is pure (DataFrame in, DataFrame/dict out) so the web app,
the case-study script and any notebook can share it.
"""
from __future__ import annotations

import re
from dataclasses import dataclass, field

import numpy as np
import pandas as pd
import pulp
from scipy.optimize import linprog

# --------------------------------------------------------------------------
# 1. Schema handling
# --------------------------------------------------------------------------
CANONICAL = ["State_Name", "District_Name", "Crop_Year", "Season", "Crop",
             "Area", "Production", "Yield"]

# Synonyms accepted for uploaded files (lower-cased, non-alphanumerics stripped)
SYNONYMS = {
    "State_Name": ["statename", "state", "statenm", "stname"],
    "District_Name": ["districtname", "district", "dist", "districtnm"],
    "Crop_Year": ["cropyear", "year", "yr", "season_year", "cropyr"],
    "Season": ["season", "seasons"],
    "Crop": ["crop", "cropname", "crops", "commodity"],
    "Area": ["area", "areahectares", "areaha", "areainhectares", "hectares", "cultivatedarea"],
    "Production": ["production", "productiontonnes", "productionquintals", "prod", "output"],
    "Yield": ["yield", "yieldperha", "yieldquintalsperhectare", "yieldha", "productivity"],
}


def _norm(s: str) -> str:
    return re.sub(r"[^a-z0-9]", "", str(s).lower())


def guess_column_map(columns) -> dict:
    """Map canonical names -> column names present in an uploaded file."""
    normed = {_norm(c): c for c in columns}
    out = {}
    for canon, syns in SYNONYMS.items():
        for s in [_norm(canon)] + syns:
            if s in normed:
                out[canon] = normed[s]
                break
    # second pass: prefix match, e.g. "Production_q" -> Production
    for canon, syns in SYNONYMS.items():
        if canon in out:
            continue
        for s in [_norm(canon)] + syns:
            hit = [orig for n, orig in normed.items() if n.startswith(s) and orig not in out.values()]
            if hit:
                out[canon] = hit[0]
                break
    return out


def standardise(raw: pd.DataFrame, colmap: dict) -> pd.DataFrame:
    """Rename to canonical schema, fill optional columns, compute Yield if absent."""
    df = raw.rename(columns={v: k for k, v in colmap.items() if v})
    missing_required = [c for c in ["Crop", "Area", "Production"] if c not in df]
    if missing_required:
        raise ValueError(f"Required column(s) missing: {missing_required}")
    if "State_Name" not in df:
        df["State_Name"] = "All"
    if "District_Name" not in df:
        df["District_Name"] = "All"
    if "Season" not in df:
        df["Season"] = "All"
    if "Crop_Year" not in df:
        df["Crop_Year"] = 0
    for c in ["Area", "Production"]:
        df[c] = pd.to_numeric(df[c], errors="coerce")
    df["Crop_Year"] = pd.to_numeric(df["Crop_Year"].astype(str).str[:4], errors="coerce").fillna(0).astype(int)
    if "Yield" in df:
        df["Yield"] = pd.to_numeric(df["Yield"], errors="coerce")
    else:
        df["Yield"] = np.nan
    # The deck says Yield = Production / Area; recompute where missing.
    need = df["Yield"].isna() & (df["Area"] > 0)
    df.loc[need, "Yield"] = df.loc[need, "Production"] / df.loc[need, "Area"]
    for c in ["State_Name", "District_Name", "Season", "Crop"]:
        df[c] = df[c].astype(str).str.strip()
    return df[CANONICAL + (["Source_Row"] if "Source_Row" in df else [])]   # Source_Row: line in the input file


# --------------------------------------------------------------------------
# 2. Cleaning (slide 14, step 2) + data-quality report
# --------------------------------------------------------------------------
# Rows that are sums of other rows -> double counting if pooled.
AGGREGATE_CROPS = {"Total foodgrain", "Pulses total", "Oilseeds total"}

# Spelling variants observed in the GOV file.
CROP_ALIASES = {
    "Dry Ginger": "Dry ginger",
    "Other  Rabi pulses": "Other Rabi pulses",
    "Atcanut (Raw)": "Arecanut (Raw)",
    "Arcanut (Processed)": "Arecanut (Processed)",
    "Paddy": "Rice",
}

# Crops whose Production is NOT a weight in data.gov.in convention.
NON_WEIGHT_UNITS = {
    "Coconut": "nuts (count)",
    "Cotton(lint)": "bales of 170 kg",
    "Kapas": "bales of 170 kg",
    "Jute": "bales of 180 kg",
    "Mesta": "bales of 180 kg",
    "Jute & mesta": "bales of 180 kg",
    "Sannhamp": "bales of 180 kg",
}


# Pulse crops, for the optional "minimum share of land under pulses" constraint.
PULSE_CROPS = {
    "Arhar/Tur", "Bean", "Blackgram", "Cowpea(Lobia)", "Gram", "Horse-gram", "Khesari", "Lab-Lab", "Lentil",
    "Masoor", "Moong(Green Gram)", "Moth", "Other Kharif pulses", "Other Rabi pulses", "Other Summer Pulses",
    "Peas & beans (Pulses)", "Rajmash Kholar", "Ricebean (nagadal)", "Urad", "other misc. pulses",
}


@dataclass
class CleaningReport:
    rows_in: int = 0
    rows_out: int = 0
    steps: list = field(default_factory=list)  # (step, rows_removed, note)
    stacked: dict | None = None                 # details of the stacked-source fix, if applied

    def add(self, step, removed, note=""):
        self.steps.append((step, int(removed), note))

    def as_frame(self):
        return pd.DataFrame(self.steps, columns=["Cleaning step", "Rows removed", "Why"])


# One record = one crop in one district, season and year. Area and Production are values, not part of the key,
# so editing either can never make a record look new.
RECORD_KEY = ["State_Name", "District_Name", "Crop_Year", "Season", "Crop"]


def reconcile_stacked_sources(d: pd.DataFrame, min_share=0.05):
    """
    Detect and fix a file made of two stacked releases of the same records whose
    Production differs by a constant power-of-ten factor.

    The bundled GOV/Kaggle CSV is exactly this: rows 0-236,377 (1997-2015,
    Production in tonnes, the first data.gov.in release) are followed by rows
    236,378-575,878 (1997-2020, a later release) where Production is 100x larger.
    213,891 records appear in both; 1,518 of them have a revised Area in the
    later release.

    Fix, in four steps that do not depend on any Area or Production value:
      (1) twins = rows sharing State/District/Year/Season/Crop;
      (2) k = most common Production ratio between twins, snapped to a power of ten;
      (3) the second release starts at the first row that is the later twin of a
          pair; every row from there on is divided by k (row order, unlike values,
          is untouched by editing or deleting rows);
      (4) one row per record is kept: the first release where both exist.
    If the rows were re-ordered (no clean split), each row's unit is decided from
    its own values instead: of two twins the higher-Production one is divided by k;
    a lone row is divided by k when its year is after the first release ends, or its
    yield is more than sqrt(k) times the crop's typical yield. This is approximate
    (about 3% of lone rows have yields that fit either unit), so keep the row order.
    Twins that still disagree after rescaling (a revision in the later release, or
    an edit to one copy) are listed in info["revised"].
    """
    d = d.reset_index(drop=True)
    dup = d.duplicated(RECORD_KEY, keep=False)
    if dup.sum() < min_share * len(d):
        return d, None
    pos = pd.Series(d.index[dup], index=d.index[dup])
    g = pos.groupby([d.loc[dup, c] for c in RECORD_KEY], sort=False)
    first, last = g.min().to_numpy(), g.max().to_numpy()        # twins in file order
    P = d["Production"].to_numpy(dtype=float)
    hi, lo = np.maximum(P[first], P[last]), np.minimum(P[first], P[last])
    ok = lo > 0
    if not ok.any():
        return d, None
    ratio = np.round(hi[ok] / lo[ok], 2)
    vals, counts = np.unique(ratio, return_counts=True)
    k, share_k = float(vals[counts.argmax()]), float(counts.max() / ok.sum())
    if k < 5 or share_k < 0.5:
        return d, None
    k = float(10 ** round(np.log10(k)))

    # (3) where does the second release start? the candidate that splits the most pairs cleanly
    cands = np.unique(np.sort(last)[:50])
    agree = np.array([((first < b) & (last >= b)).mean() for b in cands])
    boundary = int(cands[agree.argmax()]) if agree.max() >= 0.99 else None
    line = (int(d["Source_Row"].iloc[boundary]) if boundary is not None and "Source_Row" in d else None)
    info = dict(pairs=int(len(first)), factor=int(k), share_with_factor=share_k, boundary_row=boundary, boundary_line=line,
                mode="row position" if boundary is not None else "per-row yield (rows were re-ordered)",
                rows_rescaled=0, rows_dropped=0, revised=0)
    scaled = np.zeros(len(d), dtype=bool)
    if boundary is not None:
        scaled[boundary:] = True
        keep_first, drop_twin = first, last
    else:
        twin_hi = np.where(P[first] >= P[last], first, last)       # the x k copy of each pair
        twin_lo = np.where(P[first] >= P[last], last, first)
        scaled[twin_hi] = True
        lone = ~dup.to_numpy()
        y = (d["Production"] / d["Area"].where(d["Area"] > 0)).to_numpy(dtype=float)
        ref = pd.Series(y[twin_lo]).groupby(d["Crop"].to_numpy()[twin_lo]).median()
        typical = d["Crop"].map(ref).to_numpy(dtype=float)
        after = d["Crop_Year"].to_numpy() > d["Crop_Year"].to_numpy()[twin_lo].max()   # only the later release has these years
        scaled |= lone & (after | (np.isfinite(typical) & (y > typical * np.sqrt(k))))
        keep_first, drop_twin = twin_lo, twin_hi
    d.loc[scaled, "Production"] = d.loc[scaled, "Production"] / k
    info["rows_rescaled"] = int(scaled.sum())
    if "Source_Row" in d:
        info["scaled_lines"] = frozenset(d["Source_Row"].to_numpy()[scaled].tolist())

    # twins that disagree once in one unit: revised in the later release, or edited
    a1, a2 = d["Area"].to_numpy()[keep_first], d["Area"].to_numpy()[drop_twin]
    p1, p2 = d["Production"].to_numpy()[keep_first], d["Production"].to_numpy()[drop_twin]
    differ = ~np.isclose(a1, a2, rtol=1e-6) | ~np.isclose(p1, p2, rtol=5e-3)
    rev = d.loc[keep_first[differ], RECORD_KEY].reset_index(drop=True)
    rev["Area_used"], rev["Production_used"] = a1[differ], p1[differ]
    rev["Area_other"], rev["Production_other"] = a2[differ], p2[differ]
    if "Source_Row" in d:
        rev["Row_used"], rev["Row_other"] = d["Source_Row"].to_numpy()[keep_first[differ]], d["Source_Row"].to_numpy()[drop_twin[differ]]
    info["revised"], info["revised_records"] = int(differ.sum()), rev
    if "Source_Row" in d:                                          # line of the unused copy, for tracing by hand
        info["twin_line"] = pd.Series(d["Source_Row"].to_numpy()[drop_twin], index=d["Source_Row"].to_numpy()[keep_first])

    keep = np.ones(len(d), dtype=bool)
    keep[drop_twin] = False
    keep &= ~d.duplicated(RECORD_KEY, keep="first").to_numpy() | ~dup.to_numpy()  # a 3rd copy, if any, goes too
    keep[keep_first] = True
    info["rows_dropped"] = int((~keep).sum())
    return d[keep].reset_index(drop=True), info


def _has_standard_twin(d, variant):
    """Rows (renamed from a spelling variant) whose record also has a row that was already under the standard name."""
    std_keys = pd.MultiIndex.from_frame(d.loc[~variant, RECORD_KEY])
    return pd.MultiIndex.from_frame(d[RECORD_KEY]).isin(std_keys) & variant.to_numpy()


def clean(df: pd.DataFrame, drop_zero_production=True, merge_aliases=True,
          drop_aggregates=True, reconcile_stacked=True) -> tuple[pd.DataFrame, CleaningReport]:
    rep = CleaningReport(rows_in=len(df))
    d = df.copy()

    n = len(d)
    d = d.dropna(subset=["Crop", "Area", "Production"])
    rep.add("Missing Crop / Area / Production", n - len(d), "Cannot form a yield coefficient")

    n = len(d)
    d = d.drop_duplicates(subset=[c for c in d.columns if c != "Source_Row"])
    rep.add("Exact duplicate rows", n - len(d), "Would double-weight a year")

    n = len(d)
    d = d[d["Area"] > 0]
    rep.add("Area <= 0", n - len(d), "Yield undefined (division by zero)")

    if drop_zero_production:
        n = len(d)
        d = d[d["Production"] > 0]
        rep.add("Production = 0", n - len(d),
                "Usually unreported, not true crop failure; would drag the yield average to 0")

    # after the unusable rows are gone: a record disappears only when every copy of it is gone or unusable
    if reconcile_stacked:
        d, info = reconcile_stacked_sources(d)
        rep.stacked = info
        if info:
            if info["boundary_row"] is None:
                where = "rows whose year or yield shows the larger unit (the file was re-ordered)"
            else:
                where = f"rows from {'line' if info['boundary_line'] else 'row'} {info['boundary_line'] or info['boundary_row']:,} of the file on"
            rep.add("Stacked duplicate source reconciled", info["rows_dropped"],
                    f"{info['pairs']:,} records appear twice with Production x{info['factor']:,}; "
                    f"{info['rows_rescaled']:,} {where} divided by {info['factor']:,}; one row kept per record "
                    f"(the first release). {info['revised']:,} records differ between the two copies.")
        else:
            rep.add("Stacked duplicate source check", 0, "No stacked copy detected")

    if drop_aggregates:
        n = len(d)
        d = d[~d["Crop"].isin(AGGREGATE_CROPS)]
        rep.add("Aggregate rows (Total foodgrain, Pulses total, Oilseeds total)", n - len(d),
                "These rows are sums of other rows -> double counting")

    if merge_aliases:
        variant = d["Crop"].isin(CROP_ALIASES.keys())
        d["Crop"] = d["Crop"].replace(CROP_ALIASES)
        # a record can be in the file under both spellings (e.g. "Other  Rabi pulses" and "Other Rabi pulses"):
        # keep the row that already had the standard name, so the record is counted once
        n = len(d)
        d = d[~_has_standard_twin(d, variant)]
        rep.add("Same record under two crop spellings", n - len(d),
                "Kept the row with the standard name (e.g. 'Rice' over 'Paddy'), so the record is counted once")
        rep.add("Crop-name spelling variants merged", 0, f"{int(variant.sum()) - (n - len(d))} rows renamed (e.g. Paddy -> Rice)")

    d["Yield"] = d["Production"] / d["Area"]  # recompute: guarantees Yield = Prod/Area
    rep.rows_out = len(d)
    return d.reset_index(drop=True), rep


def filter_scope(df, state=None, districts=None, season=None, years=None):
    d = df
    if state and state != "(All)":
        d = d[d["State_Name"] == state]
    if districts:
        d = d[d["District_Name"].isin(districts)]
    if season and season != "(All)":
        d = d[d["Season"] == season]
    if years:
        d = d[(d["Crop_Year"] >= years[0]) & (d["Crop_Year"] <= years[1])]
    return d


# --------------------------------------------------------------------------
# 3. Production-unit consistency check (slides 8, 9, 16-1)
# --------------------------------------------------------------------------
def unit_check(d: pd.DataFrame, ratio_threshold: float = 250.0) -> pd.DataFrame:
    """
    Flag crops that must not be pooled with weight-based crops.

    Two independent signals:
      (a) Known convention: data.gov.in reports Coconut in nuts, Cotton/Jute/Mesta
          in bales -> 'Known non-weight unit'.
      (b) Data-driven: crop's median yield is > ratio_threshold x (or <
          1/ratio_threshold x) the median of all crops' medians -> 'Scale outlier'.
          This catches unknown count-type crops in uploaded data.
    """
    g = d.groupby("Crop").agg(records=("Yield", "size"),
                              median_yield=("Yield", "median"),
                              mean_yield=("Yield", "mean"),
                              cv=("Yield", lambda s: s.std() / s.mean() if s.mean() else np.nan))
    pool_median = g["median_yield"].median()
    g["ratio_to_pool_median"] = g["median_yield"] / pool_median
    status, reason = [], []
    for crop, r in g.iterrows():
        if crop in NON_WEIGHT_UNITS:
            status.append("Exclude")
            reason.append(f"Known non-weight unit: {NON_WEIGHT_UNITS[crop]}")
        elif r.ratio_to_pool_median > ratio_threshold or r.ratio_to_pool_median < 1 / ratio_threshold:
            status.append("Exclude")
            reason.append(f"Scale outlier: median yield {r.ratio_to_pool_median:,.0f}x pool median")
        else:
            status.append("Pool")
            reason.append("Weight unit (consistent scale)")
    g["status"] = status
    g["reason"] = reason
    return g.reset_index().sort_values("median_yield", ascending=False)


def structural_break_check(d: pd.DataFrame) -> pd.DataFrame:
    """Area-weighted yield of the pooled crops per year (to spot reporting-unit changes)."""
    y = d.groupby("Crop_Year").agg(Production=("Production", "sum"), Area=("Area", "sum"))
    y["Pooled_yield"] = y["Production"] / y["Area"]
    y["YoY_change_%"] = y["Pooled_yield"].pct_change() * 100
    return y.reset_index()


# --------------------------------------------------------------------------
# 4. LP coefficients (slide 11/12): y_c, a_c, m_c, historical allocation
# --------------------------------------------------------------------------
def build_coefficients(d: pd.DataFrame, crops, yield_method="mean",
                       min_years: int = 1) -> pd.DataFrame:
    """
    For each crop c in scope:
      y_c  = average Yield across years (method: mean | median | weighted)
      a_c  = historical minimum yearly area,  m_c = historical maximum yearly area
      hist = average yearly area (the 'actual' allocation to compare against)
    Rows are first summed to crop-year level (a district scope with several
    districts -> the state's yearly area for that crop).
    """
    d = d[d["Crop"].isin(crops)]
    # Per crop-year totals (sums over districts in scope)
    cy = d.groupby(["Crop", "Crop_Year"]).agg(Area=("Area", "sum"),
                                               Production=("Production", "sum"),
                                               mean_row_yield=("Yield", "mean")).reset_index()
    cy["Yield_cy"] = cy["Production"] / cy["Area"]
    out = []
    for crop, g in cy.groupby("Crop"):
        if len(g) < min_years:
            continue
        if yield_method == "mean":            # deck: "averaged over available years"
            y = g["Yield_cy"].mean()
        elif yield_method == "median":
            y = g["Yield_cy"].median()
        else:                                 # area-weighted = sum P / sum A
            y = g["Production"].sum() / g["Area"].sum()
        out.append(dict(Crop=crop, y_c=y, a_c=g["Area"].min(), m_c=g["Area"].max(),
                        hist_area=g["Area"].mean(), hist_prod=g["Production"].mean(),
                        years=len(g), yield_sd=g["Yield_cy"].std(ddof=0)))
    cols = ["Crop", "y_c", "a_c", "m_c", "hist_area", "hist_prod", "years", "yield_sd"]
    if not out:
        return pd.DataFrame(columns=cols)
    return pd.DataFrame(out, columns=cols).sort_values("y_c", ascending=False).reset_index(drop=True)


def apply_bounds(coef: pd.DataFrame, mode="historical", pct=30.0) -> pd.DataFrame:
    """
    Set the bound columns lo/hi used by the LP.
      historical : a_c = min yearly area, m_c = max yearly area   (deck, slide 12)
      band       : a_c = (1-pct%) * avg area, m_c = (1+pct%) * avg area
                   (a tighter, 'realistic re-planning' variant used in sensitivity)
    """
    c = coef.copy()
    if mode == "historical":
        c["lo"], c["hi"] = c["a_c"], c["m_c"]
    else:
        c["lo"] = c["hist_area"] * max(0.0, 1 - pct / 100)
        c["hi"] = c["hist_area"] * (1 + pct / 100)
    return c


def _ensure_bounds(coef):
    return coef if "lo" in coef else apply_bounds(coef)


# --------------------------------------------------------------------------
# 5. LP models — PuLP/CBC (primary) + SciPy linprog/HiGHS (cross-check)
# --------------------------------------------------------------------------
@dataclass
class LPResult:
    model: str
    status: str
    objective: float
    alloc: pd.DataFrame            # per-crop solution table
    shadow_price: float            # dual of Land (Opt 1) or Target (Opt 2)
    scipy_objective: float | None = None
    scipy_shadow: float | None = None

    @property
    def ok(self):
        return self.status == "Optimal"


def _bound_status(x, lo, hi):
    tol = 1e-6 * max(1.0, abs(hi))
    if abs(x - hi) <= tol:
        return "at max (m_c)"
    if abs(x - lo) <= tol:
        return "at min (a_c)"
    return "basic (between bounds)"


def _safe_name(s):
    return re.sub(r"[^A-Za-z0-9_]", "_", s)


def _share_row(c, share):
    """Row for  share * sum_c x_c - sum_{c in group} x_c <= 0  (group gets at least `share` of the land)."""
    crops, frac = share
    g = c["Crop"].isin(crops).astype(float).values
    return frac - g                                   # coefficient frac for every crop, frac-1 for group crops


def _scipy(c, model, rhs, share=None):
    """Solve with SciPy linprog (HiGHS). Returns (res, objective, dual of the land/target row)."""
    bounds = list(zip(c["lo"], c["hi"]))
    if model == "max":
        A, b, obj, sign = [np.ones(len(c))], [rhs], -c["y_c"].values, -1
    else:
        A, b, obj, sign = [-c["y_c"].values], [-rhs], np.ones(len(c)), 1
    if share:
        A.append(_share_row(c, share)); b.append(0.0)
    res = linprog(obj, A_ub=np.vstack(A), b_ub=b, bounds=bounds, method="highs")
    if res.status != 0:
        return res, None, None
    return res, sign * res.fun, -res.ineqlin.marginals[0]


def lp_model(c, model, rhs, share=None):
    """Build Optimization 1 (model='max', rhs=L) or Optimization 2 (model='min', rhs=D) in PuLP.
    share = (crops, fraction) adds: land under those crops >= fraction of all land used."""
    sense = pulp.LpMaximize if model == "max" else pulp.LpMinimize
    prob = pulp.LpProblem("Max_Output" if model == "max" else "Min_Land", sense)
    x = {r.Crop: pulp.LpVariable(f"x_{_safe_name(r.Crop)}", lowBound=r.lo, upBound=r.hi)  # a_c <= x_c <= m_c
         for r in c.itertuples()}
    output = pulp.lpSum(r.y_c * x[r.Crop] for r in c.itertuples())  # sum y_c x_c
    land = pulp.lpSum(x.values())                                  # sum x_c
    if model == "max":
        prob += output, "Total_Output"
        prob += land <= rhs, "Land"
    else:
        prob += land, "Total_Land"
        prob += output >= rhs, "Target"
    if share:
        crops, frac = share
        prob += pulp.lpSum(x[k] for k in x if k in crops) >= frac * land, "Group_share"
    return prob, x


def _solve(coef, model, rhs, use_pulp=True, share=None) -> LPResult:
    c = _ensure_bounds(coef).reset_index(drop=True)
    res, sp_obj, sp_dual = _scipy(c, model, rhs, share)
    name = "Max Output" if model == "max" else "Min Land"

    if use_pulp:
        prob, x = lp_model(c, model, rhs, share)
        prob.solve(pulp.PULP_CBC_CMD(msg=False))
        status = pulp.LpStatus[prob.status]
        ok = status == "Optimal"
        xs = [x[r.Crop].varValue if ok else np.nan for r in c.itertuples()]
        dj = [x[r.Crop].dj if ok else np.nan for r in c.itertuples()]
        cname = "Land" if model == "max" else "Target"
        shadow = prob.constraints[cname].pi if ok else np.nan
        obj = pulp.value(prob.objective) if ok else np.nan
    else:
        ok = res.status == 0
        status = "Optimal" if ok else ("Infeasible" if res.status == 2 else "Not solved")
        xs = list(res.x) if ok else [np.nan] * len(c)
        # reduced cost = y_c - lambda (max) / 1 - mu*y_c (min)
        if ok:
            dj = list(c["y_c"] - sp_dual) if model == "max" else list(1 - sp_dual * c["y_c"])
        else:
            dj = [np.nan] * len(c)
        shadow, obj = (sp_dual, sp_obj) if ok else (np.nan, np.nan)

    a = c[["Crop", "y_c", "lo", "hi", "hist_area"]].rename(columns={"lo": "a_c", "hi": "m_c"}).copy()
    a["x_opt"] = xs
    a["x_scipy"] = res.x if res.status == 0 else np.nan
    a["reduced_cost"] = dj
    a["hist_output"] = a["y_c"] * a["hist_area"]
    a["opt_output"] = a["y_c"] * a["x_opt"]
    a["change_ha"] = a["x_opt"] - a["hist_area"]
    a["change_%"] = 100 * a["change_ha"] / a["hist_area"]
    a["bound_status"] = [_bound_status(r.x_opt, r.a_c, r.m_c) if ok else "-" for r in a.itertuples()]
    return LPResult(name, status, obj, a, shadow, sp_obj, sp_dual)


def solve_max_output(coef: pd.DataFrame, L: float, use_pulp=True, share=None) -> LPResult:
    """Optimization 1:  max sum_c y_c x_c  s.t.  sum_c x_c <= L,  a_c <= x_c <= m_c,  x_c >= 0."""
    return _solve(coef, "max", L, use_pulp, share)


def solve_min_land(coef: pd.DataFrame, D: float, use_pulp=True, share=None) -> LPResult:
    """Optimization 2:  min sum_c x_c  s.t.  sum_c y_c x_c >= D,  a_c <= x_c <= m_c,  x_c >= 0."""
    return _solve(coef, "min", D, use_pulp, share)


# --------------------------------------------------------------------------
# 6. Feasibility helpers
# --------------------------------------------------------------------------
def feasibility_bounds(coef):
    c = _ensure_bounds(coef)
    return dict(min_land=c["lo"].sum(), max_land=c["hi"].sum(),
                min_output=(c["y_c"] * c["lo"]).sum(), max_output=(c["y_c"] * c["hi"]).sum())


def historical_baseline(coef):
    L = coef["hist_area"].sum()
    D = (coef["y_c"] * coef["hist_area"]).sum()
    return L, D


# --------------------------------------------------------------------------
# 7. Sensitivity analysis (Review III)
# --------------------------------------------------------------------------
def parametric_land(coef, L_values, share=None):
    """Z*(L) over a sweep of land budgets; slope of the curve = shadow price of land."""
    rows = []
    for L in L_values:
        r = solve_max_output(coef, L, use_pulp=False, share=share)
        rows.append(dict(L=L, Z=r.objective, shadow_price=r.shadow_price, status=r.status))
    return pd.DataFrame(rows)


def yield_ranging(coef, L):
    """
    Objective-coefficient ranging for Optimization 1.

    The LP has one coupling constraint (land) plus box bounds, so the optimal
    basis is characterised by the land shadow price lambda*:
        y_c > lambda*  -> x_c at m_c,   y_c < lambda* -> x_c at a_c,
        y_c = lambda*  -> the single 'basic' crop between its bounds.
    Hence the basis is unchanged while
        crop at m_c : y_c in [lambda*, +inf)
        crop at a_c : y_c in [0, lambda*]
        basic crop  : y_c between the neighbouring at-min and at-max yields.
    """
    base = solve_max_output(coef, L, use_pulp=False)
    lam = base.shadow_price if base.ok else np.nan
    a = base.alloc
    at_max = a.loc[a["bound_status"].str.startswith("at max"), "y_c"]
    at_min = a.loc[a["bound_status"].str.startswith("at min"), "y_c"]
    rows = []
    for r in a.itertuples():
        if r.bound_status.startswith("at max"):
            lo, hi = max(lam, 0.0), np.inf
        elif r.bound_status.startswith("at min"):
            lo, hi = 0.0, lam if lam > 0 else np.inf
        else:
            lo = at_min.max() if len(at_min) else 0.0
            hi = at_max.min() if len(at_max) else np.inf
        rows.append(dict(Crop=r.Crop, y_c=r.y_c, status=r.bound_status,
                         allowable_min_yield=lo, allowable_max_yield=hi,
                         allowable_decrease=r.y_c - lo, allowable_increase=hi - r.y_c))
    return pd.DataFrame(rows), lam


def yield_shock(coef, L, shock_pct, crops=None):
    """Re-solve with y_c scaled by (1+shock) for the chosen crops (all if None)."""
    c = _ensure_bounds(coef).copy()
    mask = c["Crop"].isin(crops) if crops else np.ones(len(c), bool)
    c.loc[mask, "y_c"] = c.loc[mask, "y_c"] * (1 + shock_pct / 100)
    return solve_max_output(c, L, use_pulp=False)


def bound_band_sweep(coef, pcts, share=None):
    """How much of the gain survives if re-allocation is limited to +/-p% of historical area."""
    L, D = historical_baseline(coef)
    rows = []
    for p in pcts:
        c = apply_bounds(coef, "band", p)
        r1 = solve_max_output(c, L, use_pulp=False, share=share)
        r2 = solve_min_land(c, D, use_pulp=False, share=share)
        rows.append(dict(band_pct=p,
                         output_gain_pct=100 * (r1.objective - D) / D if r1.ok else np.nan,
                         land_saving_pct=100 * (L - r2.objective) / L if r2.ok else np.nan))
    return pd.DataFrame(rows)


# --------------------------------------------------------------------------
# 8. Multi-district comparison (Review III)
# --------------------------------------------------------------------------
def multi_district(d_scope, crops, yield_method="mean", bound_mode="historical", pct=30.0,
                   min_years=1, min_crops=2, share=None):
    """Run both LPs independently for every district (L, D = that district's historical values)."""
    rows = []
    for dist, g in d_scope.groupby("District_Name"):
        coef = build_coefficients(g, crops, yield_method, min_years)
        if len(coef) < min_crops:
            continue
        coef = apply_bounds(coef, bound_mode, pct)
        L, D = historical_baseline(coef)
        r1 = solve_max_output(coef, L, use_pulp=False, share=share)
        r2 = solve_min_land(coef, D, use_pulp=False, share=share)
        if not r1.ok or D <= 0:
            continue
        top = r1.alloc.sort_values("change_ha", ascending=False).iloc[0]["Crop"]
        rows.append(dict(District=dist, crops=len(coef), land_L=L, hist_output=D,
                         opt_output=r1.objective,
                         output_gain_pct=100 * (r1.objective - D) / D,
                         min_land=r2.objective if r2.ok else np.nan,
                         land_saving_pct=100 * (L - r2.objective) / L if r2.ok else np.nan,
                         land_shadow_price=r1.shadow_price,
                         best_yield_crop=coef.sort_values("y_c").iloc[-1]["Crop"],
                         biggest_expansion=top))
    if not rows:
        return pd.DataFrame()
    return pd.DataFrame(rows).sort_values("output_gain_pct", ascending=False).reset_index(drop=True)
