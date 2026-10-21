"""
make_clean_data.py — build the data file the app and the case study read, from the raw download.

The raw data.gov.in / Kaggle CSV (kept compressed in raw/) is two stacked releases of the same
records: lines 2-236,379 (1997-2015, Production in tonnes) and, from line 236,380, a later release
(1997-2020) with Production x100 that repeats 213,888 of the earlier records. This script writes
one line per record (state, district, year, season, crop), everything in tonnes:

  * a record in both releases keeps its first-release line (the later release rounds to
    thousands); if that line is unusable (blank, zero or negative Area or Production) the
    later line is used instead, divided by 100;
  * a record in one release only keeps its line (divided by 100 if it is from the later release);
  * a record also listed under a spelling variant of its crop ('Paddy' beside 'Rice', 'Other  Rabi pulses'
    beside 'Other Rabi pulses') keeps only the line with the standard name;
  * the 'yield' column is dropped: yield is always recomputed as Production / Area.

Nothing else is removed here (zero production, aggregate rows, ... stay in the file and are
handled by the cleaning step in or_core.clean, so their effect stays visible). With this file
every line feeds the model: changing or deleting any line changes the results of its scope.

Run:   python make_clean_data.py
"""
from pathlib import Path

import numpy as np
import pandas as pd

import or_core as oc

ROOT = Path(__file__).resolve().parent
FOLDER = ROOT / "Indian Agriculture Crop Production and yield (GOV)"
RAW = FOLDER / "raw" / "Indian_crop_production_yield_dataset_raw.csv.gz"
OUT = FOLDER / "Indian_crop_production_yield_dataset.csv"
COLS = ["State_Name", "District_Name", "Crop_Year", "Season", "Crop", "Area", "Production"]


def main():
    raw = pd.read_csv(RAW, low_memory=False)
    raw["Source_Row"] = raw.index + 2
    std = oc.standardise(raw, oc.guess_column_map(raw.columns))

    # where the later release starts and its factor, found exactly as the app's cleaning step does
    usable = std.dropna(subset=["Crop", "Area", "Production"])
    usable = usable[(usable["Area"] > 0) & (usable["Production"] > 0)]
    _, info = oc.reconcile_stacked_sources(usable)
    start, k = info["boundary_line"], info["factor"]

    later = raw["Source_Row"] >= start
    ok = (pd.to_numeric(raw["Area"], errors="coerce") > 0) & (pd.to_numeric(raw["Production"], errors="coerce") > 0)
    # per record: the first usable line in file order, else the first line
    tmp = pd.DataFrame({"rank": np.where(ok, 0, 1), "row": raw.index})
    for c in oc.RECORD_KEY:
        tmp[c] = std[c].values
    tmp = tmp.sort_values(["rank", "row"])
    keep = np.sort(tmp.drop_duplicates(oc.RECORD_KEY, keep="first")["row"].to_numpy())

    out = raw.loc[keep, COLS].copy()
    prod = pd.to_numeric(out["Production"], errors="coerce")
    scaled = later.loc[keep].to_numpy() & prod.notna().to_numpy()
    out.loc[scaled, "Production"] = prod[scaled] / k            # full precision: reads back exactly

    # a record also listed under a spelling variant of its crop ("Paddy" next to "Rice", "Other  Rabi pulses"
    # next to "Other Rabi pulses"): keep only the line with the standard name
    s = oc.standardise(out.reset_index(drop=True), oc.guess_column_map(out.columns))
    variant = s["Crop"].isin(oc.CROP_ALIASES.keys())
    s["Crop"] = s["Crop"].replace(oc.CROP_ALIASES)
    twin = oc._has_standard_twin(s, variant)
    out = out[~twin]
    out.to_csv(OUT, index=False)
    print(f"{len(raw):,} raw lines -> {len(out):,} records written to {OUT.relative_to(ROOT)}")
    print(f"  {int(scaled.sum()):,} later-release lines divided by {k}; {len(raw) - len(out) - int(twin.sum()):,} duplicate "
          f"lines left out (later release from raw line {start:,}); {int(twin.sum()):,} lines left out that repeat a record "
          f"under a spelling variant of its crop")


if __name__ == "__main__":
    main()
