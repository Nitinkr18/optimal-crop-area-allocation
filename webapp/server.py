"""
webapp/server.py — backend for the crop-area allocation interface.

All computation is delegated to ../or_core.py (the same engine used by the
report), so every number shown in the browser matches the
documented results. The data is the bundled Government of India record.

Run:   python webapp/server.py        (opens http://127.0.0.1:8000)
"""
from __future__ import annotations

import difflib
import json
import math
import os
import re
import sys
import threading
import time
import webbrowser
from functools import lru_cache
from pathlib import Path

import numpy as np
import pandas as pd
import plotly
from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse, Response
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
sys.path.insert(0, str(ROOT))
import or_core as oc  # noqa: E402

GOV = Path(os.environ.get("CROP_DATA") or
           ROOT / "Indian Agriculture Crop Production and yield (GOV)" / "Indian_crop_production_yield_dataset.csv")
DISTRICT_GEO = HERE / "geo" / "india_districts.json"
PLOTLY_JS = Path(plotly.__file__).parent / "package_data" / "plotly.min.js"
DEFAULT_STATE, DEFAULT_SEASON = "Karnataka", "Kharif"
# district boundaries are pre-2014, so some states' districts sit under an older parent
GEO_PARENT = {"Telangana": "Andhra Pradesh", "Laddakh": "Jammu and Kashmir"}

app = FastAPI(title="Optimal Crop-Area Allocation")
_lock = threading.Lock()
DB: dict = {}


def _plain(x):
    """numpy types -> Python, NaN/inf -> None, recursively."""
    if isinstance(x, dict):
        return {str(k): _plain(v) for k, v in x.items()}
    if isinstance(x, (list, tuple)):
        return [_plain(v) for v in x]
    if isinstance(x, np.generic):
        x = x.item()
    if isinstance(x, float) and not math.isfinite(x):
        return None
    return x


def J(content) -> Response:
    return Response(json.dumps(_plain(content)), media_type="application/json")


def records(df: pd.DataFrame, cols, rnd=4):
    d = df[cols].replace([np.inf, -np.inf], np.nan).astype(object)
    d = d.where(d.notna(), None)
    return [{k: round(v, rnd) if isinstance(v, float) else v for k, v in r.items()} for r in d.to_dict("records")]


# ---------------------------------------------------------------------------
# data: read and cleaned once, and again whenever the CSV changes on disk
# ---------------------------------------------------------------------------
def _stamp():
    s = GOV.stat()
    return (s.st_mtime_ns, s.st_size)


def _settled_stamp():
    """Wait until the file stops changing, so a save in progress is never read half-written."""
    last = _stamp()
    for _ in range(20):
        time.sleep(0.4)
        now = _stamp()
        if now == last:
            return now
        last = now
    return last


def _load() -> dict:
    raw = pd.read_csv(GOV, low_memory=False)
    raw["Source_Row"] = raw.index + 2                       # line number in the CSV (line 1 is the header)
    data, rep = oc.clean(oc.standardise(raw, oc.guess_column_map(raw.columns)))
    rpy = data.groupby("Crop_Year").size()
    full = rpy[rpy >= 0.65 * rpy.median()].index           # drop partial years (1997, 2020)
    years = (int(full.min()), int(full.max()))
    win = oc.filter_scope(data, years=years)
    area = win.groupby(["State_Name", "Season"])["Area"].sum()
    seasons = {st: area[st].sort_values(ascending=False).index.tolist()
               for st in sorted(win["State_Name"].unique())}
    # seasons with fewer than 2 crops reported in enough years have no LP; the crop count does not depend
    # on the model inputs, so it is found once here and the browser greys those seasons out
    return dict(data=data, rep=rep, years=years, seasons=seasons, blocked=blocked_scopes(win, years))


def blocked_scopes(win, years):
    """
    Seasons with fewer than 2 crops reported in enough years: solve_scope would return < 2 crops for them.
    The same test as solve_scope, for all states and seasons in one pass: a crop counts if it is pooled
    (weight unit, median yield within 250x of the scope's median of crop medians) and reported in at
    least the loosest year threshold solve_scope tries. It does not depend on the model inputs.
    """
    n_years = years[1] - years[0] + 1
    g = win.groupby(["State_Name", "Season", "Crop"]).agg(med=("Yield", "median"), n=("Crop_Year", "nunique")).reset_index()
    pool_med = g.groupby(["State_Name", "Season"])["med"].transform("median")
    ratio = g["med"] / pool_med
    pooled = ~g["Crop"].isin(oc.NON_WEIGHT_UNITS) & (ratio <= 250) & (ratio >= 1 / 250)
    usable = g[pooled & (g["n"] >= max(1, round(0.33 * n_years)))].groupby(["State_Name", "Season"]).size()
    blocked = {}
    for st, se in win[["State_Name", "Season"]].drop_duplicates().itertuples(index=False):
        if usable.get((st, se), 0) < 2:
            blocked.setdefault(st, []).append(se)
    return blocked


def db() -> dict:
    """The cleaned data. Editing the CSV (change, add or delete rows) is picked up on the next request."""
    with _lock:
        stamp = _stamp()
        if DB.get("stamp") != stamp:
            if DB.get("stamp"):                                  # a change while running: let the save finish first
                stamp = _settled_stamp()
            try:
                fresh = _load()
            except Exception as e:                           # e.g. the file is half-saved: keep the last good data
                if DB.get("data") is None:
                    raise
                DB.update(stamp=stamp, load_error=f"Could not read the edited file ({e}); still showing the previous data.")
            else:
                DB.clear()
                DB.update(fresh, stamp=stamp, load_error=None)
                india.cache_clear()
                crop_by_state.cache_clear()
        return DB


def data_info(d):
    return dict(file=GOV.name, version=str(d["stamp"][0]), rows_in=d["rep"].rows_in, rows_out=d["rep"].rows_out,
                modified=pd.Timestamp(d["stamp"][0], unit="ns", tz="UTC").strftime("%Y-%m-%dT%H:%M:%SZ"),
                error=d.get("load_error"))


class Settings(BaseModel):
    """User-set model inputs. The defaults reproduce the report."""
    land_pct: float = 100.0         # land available for Model 1, % of historical land
    target_pct: float = 100.0       # production target for Model 2, % of historical output
    bounds: str = "historical"      # "historical" (min..max area) or "band" (avg area +/- band_pct)
    band_pct: float = 20.0
    pulse_share: float = 0.0        # minimum % of land under pulses (0 = off)
    yield_method: str = "mean"      # mean | median | weighted

    def key(self):
        return tuple(self.model_dump().values())


def solve_scope(scope, years, st: Settings = Settings()):
    """Unit check and LP coefficients for one state/season scope."""
    n_years = years[1] - years[0] + 1
    unit = oc.unit_check(scope)
    pooled = unit.loc[unit["status"] == "Pool", "Crop"].tolist()
    for frac in (0.67, 0.33):                                        # relax for sparsely reported scopes
        min_years = max(1, round(frac * n_years))
        coef = oc.apply_bounds(oc.build_coefficients(scope, pooled, st.yield_method, min_years), st.bounds, st.band_pct)
        if len(coef) >= 2:
            break
    return unit, coef, min_years


def pulse_constraint(coef, st: Settings):
    if st.pulse_share <= 0 or not coef["Crop"].isin(oc.PULSE_CROPS).any():
        return None
    return (frozenset(oc.PULSE_CROPS), st.pulse_share / 100)


@lru_cache(maxsize=None)
def district_shapes():
    return json.loads(DISTRICT_GEO.read_text())["features"] if DISTRICT_GEO.exists() else []


def _key(s):
    return re.sub(r"[^a-z]", "", str(s).lower())


def district_geo(state, names):
    """GeoJSON features for this state's districts, with ids matched to the dataset's district names."""
    parent = GEO_PARENT.get(state, state)
    pool = {_key(f["properties"]["district"]): f for f in district_shapes() if f["properties"]["state"] in (state, parent)}
    feats = []
    for name in names:
        hit = difflib.get_close_matches(_key(name), pool, n=1, cutoff=0.72)
        if hit:
            f = pool.pop(hit[0])
            feats.append({"type": "Feature", "id": name, "properties": {}, "geometry": f["geometry"]})
    return {"type": "FeatureCollection", "features": feats}


# ---------------------------------------------------------------------------
# routes
# ---------------------------------------------------------------------------
@app.get("/api/version")
def version():
    """Cheap check for the browser: has the CSV been saved since it was last read?"""
    return J(dict(version=str(_stamp()[0]), loaded=str(DB["stamp"][0]) if DB.get("stamp") else None))


@app.get("/api/meta")
def meta():
    d = db()
    rep = d["rep"]
    return J(dict(seasons=d["seasons"], blocked=d["blocked"], data=data_info(d), state=DEFAULT_STATE, season=DEFAULT_SEASON, years=d["years"],
                  cleaning=dict(rows_in=rep.rows_in, rows_out=rep.rows_out,
                                steps=[dict(step=a, removed=b, note=w) for a, b, w in rep.steps])))


@lru_cache(maxsize=32)
def india(season: str, key: tuple):
    """Both LPs for every state in one season, for the India map."""
    d, st = db(), Settings(**dict(zip(Settings.model_fields, key)))
    rows = []
    for state in d["seasons"]:
        scope = oc.filter_scope(d["data"], state, None, season, d["years"])
        if scope.empty:
            continue
        _, coef, _ = solve_scope(scope, d["years"], st)
        if len(coef) < 2:
            continue
        L, D = oc.historical_baseline(coef)
        share = pulse_constraint(coef, st)
        r1 = oc.solve_max_output(coef, L * st.land_pct / 100, use_pulp=False, share=share)
        r2 = oc.solve_min_land(coef, D * st.target_pct / 100, use_pulp=False, share=share)
        if r1.ok and r2.ok and D > 0:
            rows.append(dict(state=state, crops=len(coef), land=L, gain_pct=100 * (r1.objective - D) / D,
                             saving_pct=100 * (L - r2.objective) / L))
    return rows


class IndiaReq(BaseModel):
    season: str
    settings: Settings = Settings()


@app.post("/api/india")
def india_route(req: IndiaReq):
    return J(india(req.season, req.settings.key()))


@lru_cache(maxsize=64)
def crop_by_state(crop: str, season: str):
    """Area-weighted yield (sum P / sum A) and area of one crop in every state, for the crop map."""
    d = db()
    sc = oc.filter_scope(d["data"], None, None, season, d["years"])
    g = sc[sc["Crop"] == crop].groupby("State_Name").agg(P=("Production", "sum"), A=("Area", "sum"))
    g = g[g["A"] > 0]
    n_years = d["years"][1] - d["years"][0] + 1
    return [dict(state=st, yield_=r.P / r.A, area=r.A / n_years) for st, r in g.iterrows()]


@app.get("/api/crop")
def crop_route(crop: str, season: str):
    return J(crop_by_state(crop, season))


@app.get("/api/trace")
def trace(state: str, season: str, crop: str, yield_method: str = "mean"):
    """Every number behind one crop's LP coefficients, down to the CSV lines they come from, for checking by hand."""
    d = db()
    data, years, rep = d["data"], d["years"], d["rep"]
    scope = oc.filter_scope(data, state, None, season)
    rows = scope[scope["Crop"] == crop]
    if rows.empty:
        raise HTTPException(404, f"No {crop} records for {state} · {season}.")
    st = Settings(yield_method=yield_method if yield_method in ("mean", "median", "weighted") else "mean")
    unit, coef, min_years = solve_scope(oc.filter_scope(data, state, None, season, years), years, st)
    used = coef[coef["Crop"] == crop]
    u = unit[unit["Crop"] == crop]
    why = None
    if used.empty:
        why = (u["reason"].iloc[0] if len(u) and u["status"].iloc[0] == "Exclude"
               else f"reported in fewer than {min_years} of the {years[1] - years[0] + 1} years, so it is left out of the LP")
    yr = rows.groupby("Crop_Year").agg(area=("Area", "sum"), prod=("Production", "sum"), n=("Area", "size")).reset_index()
    yr["yield_"] = yr["prod"] / yr["area"]
    yr["in_window"] = yr["Crop_Year"].between(*years)
    s = rep.stacked or {}
    b, twin = s.get("boundary_line"), s.get("twin_line")
    lines = rows.sort_values(["Crop_Year", "District_Name"])
    rev = s.get("revised_records")
    if rev is not None and len(rev):
        rev = rev[(rev["State_Name"] == state) & (rev["Season"] == season) & (rev["Crop"] == crop)]
    return J(dict(
        state=state, season=season, crop=crop, years=years, min_years=min_years, yield_method=st.yield_method,
        included=not used.empty, why=why, factor=s.get("factor"), boundary_line=b, split=s.get("mode"),
        coef=records(used, ["y_c", "a_c", "m_c", "hist_area", "years"], rnd=8)[0] if len(used) else None,
        by_year=records(yr, ["Crop_Year", "area", "prod", "yield_", "n", "in_window"], rnd=6),
        lines=[dict(line=int(r.Source_Row), district=r.District_Name, year=int(r.Crop_Year), area=float(r.Area),
                    prod=float(r.Production), divided=r.Source_Row in s.get("scaled_lines", ()),
                    twin=int(twin[r.Source_Row]) if twin is not None and r.Source_Row in twin.index else None)
               for r in lines.itertuples()],
        revised=records(rev, list(rev.columns)) if rev is not None and len(rev) else [],
    ))


class RunReq(BaseModel):
    state: str
    season: str
    settings: Settings = Settings()


@app.post("/api/run")
def run(req: RunReq):
    d = db()
    data, years = d["data"], d["years"]
    n_years = years[1] - years[0] + 1
    scope = oc.filter_scope(data, req.state, None, req.season, years)
    if scope.empty:
        raise HTTPException(400, f"No {req.season} records for {req.state}.")
    st = req.settings
    unit, coef, min_years = solve_scope(scope, years, st)
    if len(coef) < 2:
        raise HTTPException(400, f"{req.state} · {req.season}: fewer than 2 crops are reported in enough years "
                                 "for an LP. Try another season.")

    L0, D0 = oc.historical_baseline(coef)
    L, D = L0 * st.land_pct / 100, D0 * st.target_pct / 100
    feas = oc.feasibility_bounds(coef)
    share = pulse_constraint(coef, st)
    is_pulse = coef["Crop"].isin(oc.PULSE_CROPS)
    limits = dict(land_min_pct=100 * feas["min_land"] / L0, target_max_pct=100 * feas["max_output"] / D0,
                  pulse_hist_pct=100 * coef.loc[is_pulse, "hist_area"].sum() / L0,
                  pulse_max_pct=100 * coef.loc[is_pulse, "hi"].sum() / (coef.loc[is_pulse, "hi"].sum() + coef.loc[~is_pulse, "lo"].sum()),
                  has_pulses=bool(is_pulse.any()))

    r1 = oc.solve_max_output(coef, L, share=share)
    if not r1.ok:
        why = (f"the crops' minimum areas alone need {limits['land_min_pct']:.0f}% of historical land"
               if L < feas["min_land"] else f"{st.pulse_share:.0f}% pulses cannot be reached within the area limits "
               f"(at most about {limits['pulse_max_pct']:.0f}%)")
        raise HTTPException(400, f"Model 1 has no solution with {st.land_pct:.0f}% land: {why}.")
    r2 = oc.solve_min_land(coef, D, share=share)
    if not r2.ok:
        why = (f"even with every crop at its maximum area, output reaches only {limits['target_max_pct']:.0f}% of history"
               if D > feas["max_output"] else f"{st.pulse_share:.0f}% pulses cannot be reached within the area limits")
        raise HTTPException(400, f"Model 2 has no solution with a {st.target_pct:.0f}% target: {why}.")
    r1b = oc.solve_max_output(coef, r2.objective, use_pulp=False, share=share)
    curve = oc.parametric_land(coef, np.linspace(feas["min_land"], feas["max_land"] * 1.05, 60), share=share)
    band = oc.bound_band_sweep(coef, [0, 5, 10, 15, 20, 30, 40, 50], share=share)
    dist = oc.multi_district(scope, coef["Crop"].tolist(), st.yield_method, st.bounds, st.band_pct, min_years, share=share)

    # state profile: what is grown, how much, and how yields moved
    pooled = set(coef["Crop"])
    by_crop = scope.groupby("Crop")["Area"].sum().sort_values(ascending=False) / n_years
    yearly = scope[scope["Crop"].isin(pooled)].groupby("Crop_Year").agg(A=("Area", "sum"), P=("Production", "sum"))
    top = coef.sort_values("hist_area", ascending=False)["Crop"].head(5).tolist()
    ty = scope[scope["Crop"].isin(top)].groupby(["Crop", "Crop_Year"]).agg(P=("Production", "sum"), A=("Area", "sum"))
    trend = {c: dict(x=g.index.get_level_values(1).tolist(), y=(g["P"] / g["A"]).round(4).tolist())
             for c, g in ty.groupby(level=0)}
    all_years = oc.filter_scope(data, req.state, None, req.season).groupby("Crop_Year").size()

    # rows whose yield is far from the crop's usual yield here (a typo or a unit slip moves y_c a lot)
    lp = scope[scope["Crop"].isin(pooled)]
    med = lp.groupby("Crop")["Yield"].transform("median")
    odd = lp.assign(median=med, ratio=lp["Yield"] / med)
    odd = odd[(odd["ratio"] > 10) | (odd["ratio"] < 0.1)]
    n_odd = len(odd)
    odd = odd.reindex(odd["ratio"].map(lambda v: abs(np.log10(v))).sort_values(ascending=False).index).head(10)

    alloc_cols = ["Crop", "y_c", "a_c", "m_c", "hist_area", "x_opt", "change_ha", "bound_status"]
    return J(dict(
        state=req.state, season=req.season, years=years, min_years=min_years, unit="t", limits=limits, data_version=data_info(d)["version"],
        pulse_active=share is not None, pulse_crops=coef.loc[is_pulse, "Crop"].tolist(),
        profile=dict(records=len(scope), districts=len(dist) if len(dist) else int(scope["District_Name"].nunique()),
                     crops=int(scope["Crop"].nunique()), area=float(yearly["A"].mean()), production=float(yearly["P"].mean())),
        rows_per_year={int(y): int(n) for y, n in all_years.items()},
        crop_area=[dict(Crop=c, area=a, pooled=c in pooled) for c, a in by_crop.head(15).items()],
        yearly=dict(x=yearly.index.tolist(), area=yearly["A"].tolist(), prod=yearly["P"].tolist()),
        trend=trend,
        excluded=records(unit[unit["status"] == "Exclude"], ["Crop", "reason"]),
        unusual_total=n_odd, unusual=[dict(line=int(r.Source_Row), crop=r.Crop, district=r.District_Name, year=int(r.Crop_Year), area=float(r.Area),
                      prod=float(r.Production), yield_=float(r.Yield), median=float(r.median)) for r in odd.itertuples()],
        data=data_info(d), cleaning=dict(rows_in=d["rep"].rows_in, rows_out=d["rep"].rows_out,
                                         steps=[dict(step=a, removed=b, note=w) for a, b, w in d["rep"].steps]),
        coef=records(coef, ["Crop", "y_c", "yield_sd", "a_c", "m_c", "hist_area", "years"]),
        opt1=dict(L=L, L_hist=L0, D_hist=D0, Z=r1.objective, lam=r1.shadow_price, scipy_Z=r1.scipy_objective,
                  gain_pct=100 * (r1.objective - D0) / D0, alloc=records(r1.alloc, alloc_cols, rnd=8)),
        opt2=dict(D=D, D_hist=D0, L_hist=L0, land=r2.objective, mu=r2.shadow_price, saving_pct=100 * (L0 - r2.objective) / L0,
                  inv_lam=1 / r1b.shadow_price if r1b.ok and r1b.shadow_price else None,
                  alloc=records(r2.alloc, alloc_cols, rnd=8)),
        curve=dict(L=curve["L"].tolist(), Z=curve["Z"].tolist(), lam=curve["shadow_price"].tolist()),
        band=records(band, ["band_pct", "output_gain_pct", "land_saving_pct"]),
        districts=records(dist, ["District", "crops", "output_gain_pct", "land_saving_pct"]) if len(dist) > 1 else [],
        district_geo=district_geo(req.state, dist["District"].tolist()) if len(dist) > 1 else None,
    ))


@app.get("/vendor/plotly.min.js")
def plotly_js():
    return FileResponse(PLOTLY_JS, media_type="application/javascript", headers={"Cache-Control": "max-age=86400"})


@app.get("/")
def index():
    return FileResponse(HERE / "static" / "index.html", headers={"Cache-Control": "no-cache"})


app.mount("/static", StaticFiles(directory=HERE / "static"), name="static")


if __name__ == "__main__":
    import uvicorn

    port = int(os.environ.get("PORT", 8000))
    url = f"http://127.0.0.1:{port}"
    threading.Thread(target=db, daemon=True).start()  # read the dataset while the browser opens
    if "--no-browser" not in sys.argv:
        threading.Timer(1.5, lambda: webbrowser.open(url)).start()
    print(f"\n  Running at {url}   (Ctrl+C to stop)\n")
    uvicorn.run(app, host="127.0.0.1", port=port, log_level="warning")
