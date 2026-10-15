"""
generate_synthetic_data.py — builds test CSVs for the faculty demo.

Outputs (in ./sample_data/):
  1. synthetic_crop_data_demo.csv
       Same 8-column schema as the GOV file, for a fictional state
       "Demo Pradesh" (6 districts, 3 seasons, 2008-2019).  It deliberately
       contains the quirks the pipeline must catch:
         - Coconut in nuts and Cotton(lint) in bales  -> unit check
         - "Total foodgrain" aggregate rows           -> double counting
         - "Paddy" spelling of Rice                   -> alias merge
         - zero-Production rows, exact duplicates     -> cleaning
         - one drought year (2015 Kharif)             -> yield sensitivity
  2. synthetic_minimal_farm.csv
       Only Crop / Year / Area_ha / Production_q (different column names, no
       Yield column) -> shows the app's column mapping and Yield = P/A.

Run:  python generate_synthetic_data.py   (seeded, so output is reproducible)
"""
from pathlib import Path

import numpy as np
import pandas as pd

RNG = np.random.default_rng(42)
OUT = Path(__file__).parent / "sample_data"
OUT.mkdir(exist_ok=True)

# base yield (quintals/ha), base area per district (ha) by season
CROPS = {
    "Kharif": {"Rice": (32, 42000), "Maize": (34, 18000), "Jowar": (11, 22000),
               "Bajra": (13, 15000), "Ragi": (16, 9000), "Groundnut": (14, 16000),
               "Soyabean": (12, 20000), "Arhar/Tur": (8, 14000), "Urad": (6, 7000),
               "Moong(Green Gram)": (5, 6500), "Cotton(lint)": (3, 12000)},
    "Rabi": {"Wheat": (33, 38000), "Gram": (10, 15000), "Rapeseed &Mustard": (12, 9000),
             "Barley": (26, 5000), "Masoor": (8, 6000), "Potato": (220, 3000)},
    "Whole Year": {"Sugarcane": (760, 9000), "Banana": (340, 2500), "Coconut": (9500, 4000),
                   "Turmeric": (55, 1800)},
}
DISTRICTS = {"NORTHFIELD": 1.10, "RIVERBEND": 1.20, "DRYLANDS": 0.75,
             "HILLCREST": 0.90, "COASTAL": 1.05, "CENTRALPUR": 1.00}
YEARS = range(2008, 2020)


def main():
    rows = []
    season_shock = {(y, s): RNG.normal(1.0, 0.06) for y in YEARS for s in CROPS}
    season_shock[(2015, "Kharif")] = 0.72                       # drought year
    for dist, prod_mult in DISTRICTS.items():
        # districts differ in which crops do well (comparative advantage)
        crop_affinity = {c: RNG.uniform(0.75, 1.30) for s in CROPS for c in CROPS[s]}
        for season, crops in CROPS.items():
            for crop, (y0, a0) in crops.items():
                area = a0 * RNG.uniform(0.4, 1.6)
                for t, year in enumerate(YEARS):
                    area = max(50, area * RNG.normal(1.0, 0.09))        # random walk
                    yld = (y0 * prod_mult * crop_affinity[crop] * (1.012 ** t)
                           * season_shock[(year, season)] * RNG.normal(1.0, 0.07))
                    rows.append(["Demo Pradesh", dist, year, season, crop,
                                 round(area), round(area * yld, 1)])
    df = pd.DataFrame(rows, columns=["State_Name", "District_Name", "Crop_Year", "Season",
                                     "Crop", "Area", "Production"])

    # --- inject the data quirks ------------------------------------------
    paddy = (df["Crop"] == "Rice") & (df["District_Name"] == "COASTAL") & (df["Crop_Year"] < 2011)
    df.loc[paddy, "Crop"] = "Paddy"
    zero_idx = RNG.choice(df.index, 25, replace=False)
    df.loc[zero_idx, "Production"] = 0.0
    agg = (df[df["Season"].isin(["Kharif", "Rabi"]) &
              df["Crop"].isin(["Rice", "Paddy", "Maize", "Jowar", "Bajra", "Ragi", "Wheat", "Barley",
                               "Arhar/Tur", "Urad", "Moong(Green Gram)", "Gram", "Masoor"])]
           .groupby(["State_Name", "District_Name", "Crop_Year", "Season"], as_index=False)
           [["Area", "Production"]].sum())
    agg["Crop"] = "Total foodgrain"
    df = pd.concat([df, agg, df.sample(8, random_state=1)], ignore_index=True)   # + duplicates
    df["yield"] = np.where(df["Area"] > 0, df["Production"] / df["Area"], 0)
    df = df.sort_values(["State_Name", "District_Name", "Crop_Year", "Season", "Crop"])
    df.to_csv(OUT / "synthetic_crop_data_demo.csv", index=False)

    # --- minimal single-block file with different headers ----------------
    farm = df[(df["District_Name"] == "RIVERBEND") & (df["Season"] == "Kharif")
              & (df["Crop"] != "Total foodgrain")]
    farm = farm.rename(columns={"Crop_Year": "Year", "Area": "Area_ha", "Production": "Production_q"})
    farm[["Crop", "Year", "Area_ha", "Production_q"]].to_csv(OUT / "synthetic_minimal_farm.csv", index=False)

    print(f"Wrote {len(df):,} rows -> {OUT/'synthetic_crop_data_demo.csv'}")
    print(f"Wrote {len(farm):,} rows -> {OUT/'synthetic_minimal_farm.csv'}")


if __name__ == "__main__":
    main()
