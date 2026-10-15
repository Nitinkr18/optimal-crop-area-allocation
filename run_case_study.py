"""
run_case_study.py — reproducible Review-II/III results for the report.

Case study: Karnataka, Kharif season, crop years 1998-2019 (GOV dataset).
Writes tables (CSV + Markdown) and figures (PNG) to ./results/.

Run:  python run_case_study.py
"""
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
import numpy as np  # noqa: E402
import pandas as pd  # noqa: E402

import or_core as oc  # noqa: E402

ROOT = Path(__file__).parent
OUT = ROOT / "results"
OUT.mkdir(exist_ok=True)
GOV = ROOT / "Indian Agriculture Crop Production and yield (GOV)" / "Indian_crop_production_yield_dataset.csv"

STATE, SEASON, YEARS = "Karnataka", "Kharif", (1998, 2019)
BLUE, ORANGE, GRAY = "#2a78d6", "#eb6834", "#8a8984"
plt.rcParams.update({"font.size": 10, "axes.spines.top": False, "axes.spines.right": False,
                     "axes.grid": True, "grid.alpha": 0.25, "figure.dpi": 130})


NL = chr(10)


def md(df, floatfmt=",.2f"):
    """Markdown table without the optional 'tabulate' dependency."""
    def cell(v):
        if isinstance(v, (float, np.floating)):
            return "" if np.isnan(v) else format(v, floatfmt)
        return str(v)
    head = "| " + " | ".join(map(str, df.columns)) + " |"
    sep = "|" + "|".join("---" for _ in df.columns) + "|"
    rows = ["| " + " | ".join(cell(v) for v in r) + " |" for r in df.itertuples(index=False)]
    return "\n".join([head, sep] + rows)


def main():
    log = []
    raw = pd.read_csv(GOV)
    df = oc.standardise(raw, oc.guess_column_map(raw.columns))
    data, rep = oc.clean(df)
    log.append("## Cleaning log\n\n" + md(rep.as_frame(), ",.0f") +
               f"\n\nRows: {rep.rows_in:,} -> {rep.rows_out:,}\n")

    # --- stacked-source quirk: pooled yield before vs after reconciliation ---
    raw_d, _ = oc.clean(df, reconcile_stacked=False)
    pool = lambda x: x[x["Crop"].isin(oc.unit_check(x).query("status=='Pool'")["Crop"])]  # noqa: E731
    sb_raw = oc.structural_break_check(pool(raw_d))
    sb = oc.structural_break_check(pool(data))
    fig, axs = plt.subplots(1, 2, figsize=(10, 3.4))
    axs[0].plot(sb_raw["Crop_Year"], sb_raw["Pooled_yield"], marker="o", color=ORANGE, lw=2, label="raw file")
    axs[0].set_title("Raw file: pooled yield ΣP/ΣA (mixed scales)"); axs[0].set_xlabel("Crop year")
    axs[1].plot(sb["Crop_Year"], sb["Pooled_yield"], marker="o", color=BLUE, lw=2, label="reconciled")
    axs[1].set_title("After reconciliation (t/ha)"); axs[1].set_xlabel("Crop year")
    fig.tight_layout(); fig.savefig(OUT / "fig1_stacked_source_fix.png"); plt.close(fig)
    log.append("## Stacked-source reconciliation" + NL + NL + str(rep.stacked) + NL + NL +
               md(sb_raw[["Crop_Year", "Pooled_yield"]].merge(sb[["Crop_Year", "Pooled_yield", "YoY_change_%"]],
                                                            on="Crop_Year", suffixes=("_raw", "_clean")).round(3),
                  ",.3f") + NL)

    # --- scope + unit check ----------------------------------------------
    scope = oc.filter_scope(data, STATE, None, SEASON, YEARS)
    unit = oc.unit_check(scope)
    log.append(f"## Unit check — {STATE} {SEASON} {YEARS[0]}-{YEARS[1]}\n\n" +
               md(unit[["Crop", "records", "median_yield", "cv", "ratio_to_pool_median", "status", "reason"]]))
    crops = unit.query("status=='Pool'")["Crop"].tolist()
    coef = oc.build_coefficients(scope, crops, "mean", min_years=15)
    coef = oc.apply_bounds(coef, "historical")
    coef.to_csv(OUT / "coefficients.csv", index=False)
    log.append("\n## LP coefficients\n\n" +
               md(coef[["Crop", "y_c", "yield_sd", "a_c", "m_c", "hist_area", "years"]]))

    L, D = oc.historical_baseline(coef)
    feas = oc.feasibility_bounds(coef)

    # --- Opt 1 ------------------------------------------------------------
    r1 = oc.solve_max_output(coef, L)
    r1.alloc.to_csv(OUT / "opt1_allocation.csv", index=False)
    s1 = dict(L=L, hist_output=D, Z=r1.objective, gain_pct=100 * (r1.objective - D) / D,
              shadow_price=r1.shadow_price, scipy_Z=r1.scipy_objective, scipy_dual=r1.scipy_shadow)
    log.append("\n## Optimization 1 — Max output\n\n" + md(pd.DataFrame([s1]), ",.4f") + "\n\n" +
               md(r1.alloc[["Crop", "y_c", "a_c", "m_c", "hist_area", "x_opt", "change_ha", "change_%",
                            "reduced_cost", "bound_status"]]))

    # --- Opt 2 ------------------------------------------------------------
    r2 = oc.solve_min_land(coef, D)
    r2.alloc.to_csv(OUT / "opt2_allocation.csv", index=False)
    r1b = oc.solve_max_output(coef, r2.objective)
    s2 = dict(D=D, hist_land=L, min_land=r2.objective, saving_pct=100 * (L - r2.objective) / L,
              mu=r2.shadow_price, lambda_at_min_land=r1b.shadow_price, inv_lambda=1 / r1b.shadow_price,
              scipy_land=r2.scipy_objective)
    log.append("\n## Optimization 2 — Min land\n\n" + md(pd.DataFrame([s2]), ",.6f") + "\n\n" +
               md(r2.alloc[["Crop", "y_c", "a_c", "m_c", "hist_area", "x_opt", "change_ha", "bound_status"]]))

    for r, name, title in [(r1, "fig3_opt1_allocation.png", "Opt 1 (max output): hectares per crop")]:
        a = r.alloc.sort_values("hist_area")
        y = np.arange(len(a))
        fig, ax = plt.subplots(figsize=(8, 0.38 * len(a) + 1.2))
        ax.barh(y - 0.2, a["hist_area"] / 1e3, 0.38, color=BLUE, label="Historical average")
        ax.barh(y + 0.2, a["x_opt"] / 1e3, 0.38, color=ORANGE, label="LP optimal")
        ax.scatter(a["m_c"] / 1e3, y, marker="|", s=160, color=GRAY, label="Upper bound $m_c$")
        ax.set_yticks(y, a["Crop"]); ax.set_xlabel("Thousand hectares"); ax.set_title(title)
        ax.legend(frameon=False, loc="lower right"); ax.grid(axis="y", alpha=0)
        fig.tight_layout(); fig.savefig(OUT / name); plt.close(fig)

    # --- Sensitivity ------------------------------------------------------
    Ls = np.linspace(feas["min_land"], feas["max_land"] * 1.05, 80)
    pl = oc.parametric_land(coef, Ls)
    fig, axs = plt.subplots(1, 2, figsize=(10, 3.4))
    axs[0].plot(pl["L"] / 1e6, pl["Z"] / 1e6, color=BLUE, lw=2)
    axs[0].axvline(L / 1e6, ls=":", color=GRAY); axs[0].set_title("Z*(L): optimal output vs land")
    axs[0].set_xlabel("Land budget L (million ha)"); axs[0].set_ylabel("Z* (million units)")
    axs[1].step(pl["L"] / 1e6, pl["shadow_price"], where="post", color=ORANGE, lw=2)
    axs[1].axvline(L / 1e6, ls=":", color=GRAY); axs[1].set_title("Shadow price of land λ*(L)")
    axs[1].set_xlabel("Land budget L (million ha)")
    fig.tight_layout(); fig.savefig(OUT / "fig5_parametric_land.png"); plt.close(fig)

    rg, lam = oc.yield_ranging(coef, L)
    log.append(f"\n## Yield ranging (λ* = {lam:.4f})\n\n" + md(rg.replace(np.inf, np.nan)))

    shocks = []
    for crop_set, label in [(None, "all crops"), (["Maize"], "Maize only"), (["Rice"], "Rice only"),
                            (["Soyabean"], "Soyabean only")]:
        for s in [-30, -15, 15]:
            rs = oc.yield_shock(coef, L, s, crop_set)
            shocks.append(dict(scenario=label, shock_pct=s, Z=rs.objective,
                               Z_change_pct=100 * (rs.objective - r1.objective) / r1.objective,
                               ha_reallocated=(rs.alloc["x_opt"] - r1.alloc["x_opt"]).abs().sum() / 2))
    log.append("\n## Yield-shock scenarios\n\n" + md(pd.DataFrame(shocks)))

    bb = oc.bound_band_sweep(coef, [0, 5, 10, 15, 20, 30, 50, 75, 100])
    log.append("\n## Bound-band sweep\n\n" + md(bb))

    # --- Multi-district ---------------------------------------------------
    md_scope = oc.filter_scope(data, STATE, None, SEASON, YEARS)
    mdist = oc.multi_district(md_scope, crops, "mean", "historical", 30, min_years=15)
    mdist.to_csv(OUT / "multi_district.csv", index=False)
    log.append("\n## Multi-district comparison\n\n" + md(mdist[["District", "crops", "land_L", "output_gain_pct",
                                                                 "land_saving_pct", "land_shadow_price",
                                                                 "best_yield_crop", "biggest_expansion"]]))
    m = mdist.sort_values("output_gain_pct")
    y = np.arange(len(m))
    fig, ax = plt.subplots(figsize=(8, 0.3 * len(m) + 1.2))
    ax.barh(y - 0.2, m["output_gain_pct"], 0.38, color=BLUE, label="Output gain % (Opt 1)")
    ax.barh(y + 0.2, m["land_saving_pct"], 0.38, color=ORANGE, label="Land saving % (Opt 2)")
    ax.set_yticks(y, m["District"]); ax.set_xlabel("%"); ax.legend(frameon=False, loc="lower right")
    ax.set_title(f"{STATE} {SEASON}: LP improvement by district"); ax.grid(axis="y", alpha=0)
    fig.tight_layout(); fig.savefig(OUT / "fig7_multi_district.png"); plt.close(fig)

    (OUT / "case_study_results.md").write_text("# Case-study results (auto-generated)\n\n" + "\n".join(log),
                                               encoding="utf-8")
    print(f"Opt1: Z*={r1.objective:,.0f}  hist={D:,.0f}  gain={s1['gain_pct']:.2f}%  λ*={r1.shadow_price:.4f}")
    print(f"Opt2: land*={r2.objective:,.0f}  hist={L:,.0f}  saving={s2['saving_pct']:.2f}%  μ*={r2.shadow_price:.6f}")
    print(f"Wrote results to {OUT}")


if __name__ == "__main__":
    main()
