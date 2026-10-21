# Optimal Crop-Area Allocation for Agricultural Resource Planning

*A linear-programming approach using district-level crop production data (Government of India).*
Operations Research project: Nitin Krishna V, Vishal Suresh, Manogna Challa, Gaurav Mahesh (Amrita School of AI).

Two LP models allocate land across crops: **maximise output** on a fixed area, and **minimise land** for a production target. Every coefficient comes from the government crop record. For Karnataka, Kharif, 1998–2019, the result is **+21.6% output** on the same land, or the same output on **23.9% less land**.

* Short write-up: [REPORT.md](REPORT.md)

## Run

```bash
pip install -r requirements.txt
python webapp/server.py        # or double-click run_app.bat on Windows
```

The browser opens **<http://127.0.0.1:8000>**. The dataset loads automatically (about 10 s the first time).

| Script | Purpose |
|---|---|
| `python run_case_study.py` | Reproduces every number and figure in the report (writes to `results/`) |
| `python generate_synthetic_data.py` | Regenerates the two test files in `sample_data/` |
| `python make_clean_data.py` | Rebuilds the app's data file (one line per record) from the raw download |

## The interface

A left sidebar switches between seven pages and shows the solvers used (PuLP · CBC, cross-checked with SciPy linprog · HiGHS). The bar at the top picks the **State** and **Season**; every page re-solves and redraws for that choice. The data is the bundled Government of India record.

| Page | Content |
|---|---|
| Overview | Problem, approach, questions, headline results, **India map** of output gain (Model 1) or land saved (Model 2) by state (click a state to load it), states ranked |
| Data | State profile, what is grown, area and production per year, yield trends, records per year, yield per crop (y_c ± s.d.), rows far from the usual yield, **check the numbers by hand** (one crop's y_c, a_c, m_c worked out from the yearly totals, down to the CSV lines), the data file and cleaning |
| Model inputs | Inputs with defaults that every page re-solves with: land available, production target, area limits per crop (historical min–max or ±p%), minimum land under pulses, yield estimate. Shows the effect against the default plan |
| Results | Model 1 / Model 2 toggle: key numbers, a constraint check (Σx, Σyx, bounds) from the table, what the plan says, hectares per crop, change from history, where the extra output comes from, allocation table |
| Crops | Pick a crop: its yield in every state on an India map, the state's rank, and what the model does with it |
| Sensitivity | Output and λ* vs land budget, gain under ±p% limits per crop |
| Districts | **District map** of the chosen state (Model 1 or Model 2), gain by district, number of crops vs gain |

A state, season and inputs can be opened directly, e.g. <http://127.0.0.1:8000/?state=Punjab&season=Rabi#results> or <http://127.0.0.1:8000/?land=90&pulse=30&bounds=band&band=40#model> (parameters: `land`, `target`, `bounds` = historical|band, `band`, `pulse`, `yield` = mean|median|weighted).

Model 1 is shown in green and Model 2 in brown throughout. Seasons with fewer than two crops reported in enough years have no LP and are greyed out in the menu.

The defaults reproduce the report. The pulse floor is an extra LP constraint (`share` in `or_core.lp_model`): land under pulse crops ≥ the chosen fraction of all land used.

### Changing the data

The app reads `Indian Agriculture Crop Production and yield (GOV)/Indian_crop_production_yield_dataset.csv`: **one line per record** (state, district, year, season, crop), Production in tonnes. Open it in LibreOffice Calc, Numbers, Excel or a text editor, change, add or delete rows, and save it as CSV while the app runs: within about 10 seconds it reloads the file, re-solves and shows *Data file changed*. Saving from LibreOffice Calc leaves every other value exactly as it was (tested on all 358,657 lines).

* *Data → Look up a CSV line* tells you where any line goes: the crop-year total it is summed into, or why it is not used (another state, the edge years 1997/2020, a crop counted in nuts or bales, zero production, …).
* A crop's coefficients come from its **yearly totals** (sum over districts): y_c = mean of the yearly yields P_t/A_t (or median, or ΣP/ΣA), a_c = smallest yearly area, m_c = largest yearly area, over 1998–2019. *Data → Check the numbers by hand* shows these sums and formulas with the CSV lines behind them.
* So any change to a used line changes that scope's results: a little for one district in one of 22 years, more if its year is the crop's smallest or largest year (it then moves a bound). Deleting a used line removes it from its year's total.
* Blank, zero or negative values make a line unusable (it is left out); a large typo is kept and listed under *rows far from the crop's usual yield*.
* Keep the rows in order and the header unchanged; there is no `yield` column (yield is always Production ÷ Area).

The file is built from the raw download (`raw/Indian_crop_production_yield_dataset_raw.csv.gz`, 575,879 lines) by `python make_clean_data.py`. The raw file holds a second release of the data from line 236,380 (Production ×100, repeating 213,888 records) and lists 3,331 records twice under two spellings of the crop; the script keeps one line per record. `run_case_study.py` starts from the raw file and checks that the app's file cleans to exactly the same records and values.

Map boundaries are built by `python webapp/geo/make_geo.py` from public GeoJSON (states: datta07/INDIAN-SHAPEFILES; districts: geohacker/india, GADM, whose district names match the dataset's era). A few districts created recently, or renamed, have no boundary and appear only in the charts.

## Folder structure

```
├── or_core.py                     Cleaning, unit check, coefficients, both LPs, sensitivity, districts
├── webapp/
│   ├── server.py                  FastAPI backend: loads data and calls or_core
│   ├── static/                    index.html · app.css · app.js · icons.js (Lucide, ISC) · india_states.json
│   └── geo/                       make_geo.py · india_districts.json (map boundaries)
├── run_case_study.py              Builds results/ used in REPORT.md
├── generate_synthetic_data.py     Builds sample_data/*.csv
├── results/                       Tables and figures from run_case_study.py
├── sample_data/                   Two small synthetic test files (validation in REPORT.md)
└── Indian Agriculture Crop Production and yield (GOV)/
    ├── Indian_crop_production_yield_dataset.csv   (358,657 lines, one per record: the file the app reads)
    └── raw/Indian_crop_production_yield_dataset_raw.csv.gz   (the raw download, 575,879 lines)
```
