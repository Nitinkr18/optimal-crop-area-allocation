# Case-study results (auto-generated)

## Cleaning log

| Cleaning step | Rows removed | Why |
|---|---|---|
| Missing Crop / Area / Production | 0 | Cannot form a yield coefficient |
| Exact duplicate rows | 0 | Would double-weight a year |
| Stacked duplicate source reconciled | 212373 | 212,373 records appear twice with Production x100; 339,501 rows from row 236,378 on rescaled (/100) to one unit, twins dropped |
| Area <= 0 | 0 | Yield undefined (division by zero) |
| Production = 0 | 3634 | Usually unreported, not true crop failure; would drag the yield average to 0 |
| Aggregate rows (Total foodgrain, Pulses total, Oilseeds total) | 1133 | These rows are sums of other rows -> double counting |
| Crop-name spelling variants merged | 0 | 3565 rows renamed (e.g. Paddy -> Rice) |

Rows: 575,879 -> 358,739

## Stacked-source reconciliation

{'pairs': 212373, 'factor': 100, 'share_with_factor': 0.9942882704713472, 'boundary_row': 236378, 'rows_rescaled': 339501, 'rows_dropped': 212373}

| Crop_Year | Pooled_yield_raw | Pooled_yield_clean | YoY_change_% |
|---|---|---|---|
| 1997 | 162.707 | 5.338 |  |
| 1998 | 181.344 | 3.417 | -35.992 |
| 1999 | 193.842 | 3.653 | 6.918 |
| 2000 | 182.557 | 3.523 | -3.564 |
| 2001 | 187.580 | 3.625 | 2.884 |
| 2002 | 182.426 | 3.555 | -1.934 |
| 2003 | 171.065 | 3.354 | -5.657 |
| 2004 | 163.477 | 3.140 | -6.357 |
| 2005 | 188.039 | 3.814 | 21.459 |
| 2006 | 200.163 | 3.846 | 0.825 |
| 2007 | 220.678 | 4.064 | 5.683 |
| 2008 | 189.211 | 4.003 | -1.505 |
| 2009 | 195.363 | 4.143 | 3.500 |
| 2010 | 208.875 | 4.451 | 7.420 |
| 2011 | 240.503 | 4.327 | -2.786 |
| 2012 | 230.003 | 4.124 | -4.688 |
| 2013 | 254.490 | 4.448 | 7.871 |
| 2014 | 283.946 | 4.594 | 3.280 |
| 2015 | 408.898 | 4.204 | -8.501 |
| 2016 | 434.516 | 4.345 | 3.364 |
| 2017 | 479.019 | 4.790 | 10.242 |
| 2018 | 488.544 | 4.885 | 1.988 |
| 2019 | 471.382 | 4.714 | -3.513 |
| 2020 | 1,108.732 | 11.087 | 135.209 |

## Unit check — Karnataka Kharif 1998-2019

| Crop | records | median_yield | cv | ratio_to_pool_median | status | reason |
|---|---|---|---|---|---|---|
| Dry ginger | 118 | 13.00 | 0.05 | 17.07 | Pool | Weight unit (consistent scale) |
| Ginger | 118 | 13.00 | 0.05 | 17.07 | Pool | Weight unit (consistent scale) |
| Peas & beans (Pulses) | 76 | 8.90 | 0.29 | 11.69 | Pool | Weight unit (consistent scale) |
| Potato | 267 | 7.00 | 0.51 | 9.19 | Pool | Weight unit (consistent scale) |
| Onion | 369 | 6.00 | 0.42 | 7.88 | Pool | Weight unit (consistent scale) |
| Maize | 587 | 2.94 | 0.34 | 3.87 | Pool | Weight unit (consistent scale) |
| Rice | 629 | 2.56 | 0.32 | 3.37 | Pool | Weight unit (consistent scale) |
| Mesta | 39 | 2.00 | 0.34 | 2.63 | Exclude | Known non-weight unit: bales of 180 kg |
| Cotton(lint) | 385 | 1.84 | 0.54 | 2.42 | Exclude | Known non-weight unit: bales of 170 kg |
| Ragi | 453 | 1.39 | 0.38 | 1.83 | Pool | Weight unit (consistent scale) |
| Jowar | 471 | 1.25 | 0.42 | 1.64 | Pool | Weight unit (consistent scale) |
| Dry chillies | 346 | 0.98 | 0.69 | 1.29 | Pool | Weight unit (consistent scale) |
| Soyabean | 270 | 0.90 | 0.31 | 1.18 | Pool | Weight unit (consistent scale) |
| Castor seed | 483 | 0.78 | 0.46 | 1.02 | Pool | Weight unit (consistent scale) |
| Bajra | 394 | 0.75 | 0.46 | 0.98 | Pool | Weight unit (consistent scale) |
| Groundnut | 583 | 0.68 | 0.41 | 0.90 | Pool | Weight unit (consistent scale) |
| Small millets | 419 | 0.52 | 0.50 | 0.68 | Pool | Weight unit (consistent scale) |
| Arhar/Tur | 569 | 0.51 | 0.47 | 0.68 | Pool | Weight unit (consistent scale) |
| Sesamum | 572 | 0.50 | 0.52 | 0.66 | Pool | Weight unit (consistent scale) |
| Sunflower | 532 | 0.50 | 0.42 | 0.66 | Pool | Weight unit (consistent scale) |
| Horse-gram | 554 | 0.49 | 0.58 | 0.65 | Pool | Weight unit (consistent scale) |
| Other Kharif pulses | 540 | 0.48 | 0.87 | 0.63 | Pool | Weight unit (consistent scale) |
| Cowpea(Lobia) | 270 | 0.38 | 0.58 | 0.50 | Pool | Weight unit (consistent scale) |
| Urad | 448 | 0.32 | 0.47 | 0.43 | Pool | Weight unit (consistent scale) |
| Gram | 46 | 0.27 | 0.62 | 0.36 | Pool | Weight unit (consistent scale) |
| Niger seed | 513 | 0.24 | 0.29 | 0.32 | Pool | Weight unit (consistent scale) |
| Rapeseed &Mustard | 159 | 0.22 | 0.33 | 0.29 | Pool | Weight unit (consistent scale) |
| Moong(Green Gram) | 517 | 0.21 | 0.60 | 0.28 | Pool | Weight unit (consistent scale) |

## LP coefficients

| Crop | y_c | yield_sd | a_c | m_c | hist_area | years |
|---|---|---|---|---|---|---|
| Potato | 6.61 | 2.52 | 17,797.00 | 67,728.00 | 34,385.73 | 15 |
| Onion | 6.08 | 1.79 | 67,739.00 | 193,156.00 | 141,525.33 | 15 |
| Maize | 2.86 | 0.51 | 450,472.00 | 1,355,321.00 | 950,336.77 | 22 |
| Rice | 2.63 | 0.28 | 737,547.00 | 1,129,883.00 | 1,037,666.23 | 22 |
| Ragi | 1.57 | 0.33 | 514,756.00 | 986,173.00 | 741,456.50 | 22 |
| Jowar | 1.33 | 0.18 | 92,465.00 | 420,808.00 | 242,460.18 | 22 |
| Soyabean | 0.86 | 0.26 | 48,444.00 | 336,850.00 | 168,252.55 | 22 |
| Bajra | 0.81 | 0.29 | 163,108.00 | 461,048.00 | 314,334.55 | 22 |
| Castor seed | 0.79 | 0.18 | 2,650.00 | 30,366.00 | 16,778.05 | 22 |
| Groundnut | 0.66 | 0.19 | 389,994.00 | 1,012,577.00 | 638,593.09 | 22 |
| Other Kharif pulses | 0.64 | 0.29 | 28,375.00 | 169,312.00 | 98,553.76 | 21 |
| Arhar/Tur | 0.58 | 0.18 | 475,396.00 | 1,626,389.00 | 752,171.45 | 22 |
| Sesamum | 0.54 | 0.15 | 24,776.00 | 115,250.00 | 67,683.91 | 22 |
| Small millets | 0.54 | 0.12 | 19,229.00 | 71,447.00 | 40,699.45 | 20 |
| Sunflower | 0.51 | 0.17 | 95,442.00 | 661,178.00 | 287,392.23 | 22 |
| Horse-gram | 0.49 | 0.10 | 35,541.00 | 189,486.00 | 99,059.45 | 22 |
| Urad | 0.33 | 0.13 | 63,176.00 | 152,106.00 | 110,523.90 | 21 |
| Niger seed | 0.24 | 0.06 | 993.00 | 44,000.00 | 22,590.59 | 22 |
| Moong(Green Gram) | 0.23 | 0.09 | 169,271.00 | 520,630.00 | 360,993.77 | 22 |

## Optimization 1 — Max output

| L | hist_output | Z | gain_pct | shadow_price | scipy_Z | scipy_dual |
|---|---|---|---|---|---|---|
| 6,125,457.5015 | 9,729,946.9594 | 11,831,630.8919 | 21.6002 | 0.8082 | 11,831,630.8931 | 0.8082 |

| Crop | y_c | a_c | m_c | hist_area | x_opt | change_ha | change_% | reduced_cost | bound_status |
|---|---|---|---|---|---|---|---|---|---|
| Potato | 6.61 | 17,797.00 | 67,728.00 | 34,385.73 | 67,728.00 | 33,342.27 | 96.97 | 5.80 | at max (m_c) |
| Onion | 6.08 | 67,739.00 | 193,156.00 | 141,525.33 | 193,156.00 | 51,630.67 | 36.48 | 5.28 | at max (m_c) |
| Maize | 2.86 | 450,472.00 | 1,355,321.00 | 950,336.77 | 1,355,321.00 | 404,984.23 | 42.61 | 2.05 | at max (m_c) |
| Rice | 2.63 | 737,547.00 | 1,129,883.00 | 1,037,666.23 | 1,129,883.00 | 92,216.77 | 8.89 | 1.82 | at max (m_c) |
| Ragi | 1.57 | 514,756.00 | 986,173.00 | 741,456.50 | 986,173.00 | 244,716.50 | 33.00 | 0.76 | at max (m_c) |
| Jowar | 1.33 | 92,465.00 | 420,808.00 | 242,460.18 | 420,808.00 | 178,347.82 | 73.56 | 0.52 | at max (m_c) |
| Soyabean | 0.86 | 48,444.00 | 336,850.00 | 168,252.55 | 336,850.00 | 168,597.45 | 100.20 | 0.05 | at max (m_c) |
| Bajra | 0.81 | 163,108.00 | 461,048.00 | 314,334.55 | 330,695.50 | 16,360.95 | 5.20 | -0.00 | basic (between bounds) |
| Castor seed | 0.79 | 2,650.00 | 30,366.00 | 16,778.05 | 2,650.00 | -14,128.05 | -84.21 | -0.02 | at min (a_c) |
| Groundnut | 0.66 | 389,994.00 | 1,012,577.00 | 638,593.09 | 389,994.00 | -248,599.09 | -38.93 | -0.15 | at min (a_c) |
| Other Kharif pulses | 0.64 | 28,375.00 | 169,312.00 | 98,553.76 | 28,375.00 | -70,178.76 | -71.21 | -0.16 | at min (a_c) |
| Arhar/Tur | 0.58 | 475,396.00 | 1,626,389.00 | 752,171.45 | 475,396.00 | -276,775.45 | -36.80 | -0.22 | at min (a_c) |
| Sesamum | 0.54 | 24,776.00 | 115,250.00 | 67,683.91 | 24,776.00 | -42,907.91 | -63.39 | -0.27 | at min (a_c) |
| Small millets | 0.54 | 19,229.00 | 71,447.00 | 40,699.45 | 19,229.00 | -21,470.45 | -52.75 | -0.27 | at min (a_c) |
| Sunflower | 0.51 | 95,442.00 | 661,178.00 | 287,392.23 | 95,442.00 | -191,950.23 | -66.79 | -0.30 | at min (a_c) |
| Horse-gram | 0.49 | 35,541.00 | 189,486.00 | 99,059.45 | 35,541.00 | -63,518.45 | -64.12 | -0.32 | at min (a_c) |
| Urad | 0.33 | 63,176.00 | 152,106.00 | 110,523.90 | 63,176.00 | -47,347.90 | -42.84 | -0.48 | at min (a_c) |
| Niger seed | 0.24 | 993.00 | 44,000.00 | 22,590.59 | 993.00 | -21,597.59 | -95.60 | -0.57 | at min (a_c) |
| Moong(Green Gram) | 0.23 | 169,271.00 | 520,630.00 | 360,993.77 | 169,271.00 | -191,722.77 | -53.11 | -0.58 | at min (a_c) |

## Optimization 2 — Min land

| D | hist_land | min_land | saving_pct | mu | lambda_at_min_land | inv_lambda | scipy_land |
|---|---|---|---|---|---|---|---|
| 9,729,946.959430 | 6,125,457.501515 | 4,663,668.260000 | 23.864164 | 0.380616 | 2.627323 | 0.380616 | 4,663,668.259502 |

| Crop | y_c | a_c | m_c | hist_area | x_opt | change_ha | bound_status |
|---|---|---|---|---|---|---|---|
| Potato | 6.61 | 17,797.00 | 67,728.00 | 34,385.73 | 67,728.00 | 33,342.27 | at max (m_c) |
| Onion | 6.08 | 67,739.00 | 193,156.00 | 141,525.33 | 193,156.00 | 51,630.67 | at max (m_c) |
| Maize | 2.86 | 450,472.00 | 1,355,321.00 | 950,336.77 | 1,355,321.00 | 404,984.23 | at max (m_c) |
| Rice | 2.63 | 737,547.00 | 1,129,883.00 | 1,037,666.23 | 923,847.26 | -113,818.97 | basic (between bounds) |
| Ragi | 1.57 | 514,756.00 | 986,173.00 | 741,456.50 | 514,756.00 | -226,700.50 | at min (a_c) |
| Jowar | 1.33 | 92,465.00 | 420,808.00 | 242,460.18 | 92,465.00 | -149,995.18 | at min (a_c) |
| Soyabean | 0.86 | 48,444.00 | 336,850.00 | 168,252.55 | 48,444.00 | -119,808.55 | at min (a_c) |
| Bajra | 0.81 | 163,108.00 | 461,048.00 | 314,334.55 | 163,108.00 | -151,226.55 | at min (a_c) |
| Castor seed | 0.79 | 2,650.00 | 30,366.00 | 16,778.05 | 2,650.00 | -14,128.05 | at min (a_c) |
| Groundnut | 0.66 | 389,994.00 | 1,012,577.00 | 638,593.09 | 389,994.00 | -248,599.09 | at min (a_c) |
| Other Kharif pulses | 0.64 | 28,375.00 | 169,312.00 | 98,553.76 | 28,375.00 | -70,178.76 | at min (a_c) |
| Arhar/Tur | 0.58 | 475,396.00 | 1,626,389.00 | 752,171.45 | 475,396.00 | -276,775.45 | at min (a_c) |
| Sesamum | 0.54 | 24,776.00 | 115,250.00 | 67,683.91 | 24,776.00 | -42,907.91 | at min (a_c) |
| Small millets | 0.54 | 19,229.00 | 71,447.00 | 40,699.45 | 19,229.00 | -21,470.45 | at min (a_c) |
| Sunflower | 0.51 | 95,442.00 | 661,178.00 | 287,392.23 | 95,442.00 | -191,950.23 | at min (a_c) |
| Horse-gram | 0.49 | 35,541.00 | 189,486.00 | 99,059.45 | 35,541.00 | -63,518.45 | at min (a_c) |
| Urad | 0.33 | 63,176.00 | 152,106.00 | 110,523.90 | 63,176.00 | -47,347.90 | at min (a_c) |
| Niger seed | 0.24 | 993.00 | 44,000.00 | 22,590.59 | 993.00 | -21,597.59 | at min (a_c) |
| Moong(Green Gram) | 0.23 | 169,271.00 | 520,630.00 | 360,993.77 | 169,271.00 | -191,722.77 | at min (a_c) |

## Yield ranging (λ* = 0.8082)

| Crop | y_c | status | allowable_min_yield | allowable_max_yield | allowable_decrease | allowable_increase |
|---|---|---|---|---|---|---|
| Potato | 6.61 | at max (m_c) | 0.81 |  | 5.80 |  |
| Onion | 6.08 | at max (m_c) | 0.81 |  | 5.28 |  |
| Maize | 2.86 | at max (m_c) | 0.81 |  | 2.05 |  |
| Rice | 2.63 | at max (m_c) | 0.81 |  | 1.82 |  |
| Ragi | 1.57 | at max (m_c) | 0.81 |  | 0.76 |  |
| Jowar | 1.33 | at max (m_c) | 0.81 |  | 0.52 |  |
| Soyabean | 0.86 | at max (m_c) | 0.81 |  | 0.05 |  |
| Bajra | 0.81 | basic (between bounds) | 0.79 | 0.86 | 0.02 | 0.05 |
| Castor seed | 0.79 | at min (a_c) | 0.00 | 0.81 | 0.79 | 0.02 |
| Groundnut | 0.66 | at min (a_c) | 0.00 | 0.81 | 0.66 | 0.15 |
| Other Kharif pulses | 0.64 | at min (a_c) | 0.00 | 0.81 | 0.64 | 0.16 |
| Arhar/Tur | 0.58 | at min (a_c) | 0.00 | 0.81 | 0.58 | 0.22 |
| Sesamum | 0.54 | at min (a_c) | 0.00 | 0.81 | 0.54 | 0.27 |
| Small millets | 0.54 | at min (a_c) | 0.00 | 0.81 | 0.54 | 0.27 |
| Sunflower | 0.51 | at min (a_c) | 0.00 | 0.81 | 0.51 | 0.30 |
| Horse-gram | 0.49 | at min (a_c) | 0.00 | 0.81 | 0.49 | 0.32 |
| Urad | 0.33 | at min (a_c) | 0.00 | 0.81 | 0.33 | 0.48 |
| Niger seed | 0.24 | at min (a_c) | 0.00 | 0.81 | 0.24 | 0.57 |
| Moong(Green Gram) | 0.23 | at min (a_c) | 0.00 | 0.81 | 0.23 | 0.58 |

## Yield-shock scenarios

| scenario | shock_pct | Z | Z_change_pct | ha_reallocated |
|---|---|---|---|---|
| all crops | -30 | 8,282,141.63 | -30.00 | 0.00 |
| all crops | -15 | 10,056,886.26 | -15.00 | 0.00 |
| all crops | 15 | 13,606,375.53 | 15.00 | 0.00 |
| Maize only | -30 | 10,670,748.13 | -9.81 | 0.00 |
| Maize only | -15 | 11,251,189.51 | -4.91 | 0.00 |
| Maize only | 15 | 12,412,072.28 | 4.91 | 0.00 |
| Rice only | -30 | 10,941,060.62 | -7.53 | 0.00 |
| Rice only | -15 | 11,386,345.75 | -3.76 | 0.00 |
| Rice only | 15 | 12,276,916.03 | 3.76 | 0.00 |
| Soyabean only | -30 | 11,784,799.44 | -0.40 | 288,406.00 |
| Soyabean only | -15 | 11,800,114.33 | -0.27 | 158,068.50 |
| Soyabean only | 15 | 11,875,026.85 | 0.37 | 0.00 |

## Bound-band sweep

| band_pct | output_gain_pct | land_saving_pct |
|---|---|---|
| 0 | -0.00 | -0.00 |
| 5 | 3.12 | 2.50 |
| 10 | 6.24 | 5.00 |
| 15 | 9.36 | 7.50 |
| 20 | 12.48 | 10.00 |
| 30 | 18.72 | 15.00 |
| 50 | 31.20 | 25.01 |
| 75 | 46.81 | 37.51 |
| 100 | 62.41 | 50.01 |

## Multi-district comparison

| District | crops | land_L | output_gain_pct | land_saving_pct | land_shadow_price | best_yield_crop | biggest_expansion |
|---|---|---|---|---|---|---|---|
| KOPPAL | 15 | 257,501.08 | 65.44 | 41.36 | 0.89 | Onion | Maize |
| GADAG | 17 | 214,055.74 | 55.12 | 44.61 | 0.51 | Onion | Maize |
| RAICHUR | 13 | 264,831.15 | 48.12 | 36.29 | 0.75 | Onion | Rice |
| HASSAN | 17 | 229,752.76 | 45.79 | 31.14 | 3.52 | Onion | Maize |
| BIJAPUR | 11 | 327,157.99 | 45.40 | 58.30 | 0.47 | Maize | Bajra |
| DHARWAD | 17 | 187,322.01 | 44.54 | 43.35 | 0.77 | Potato | Maize |
| BAGALKOT | 14 | 150,227.04 | 42.96 | 47.39 | 0.67 | Maize | Maize |
| CHITRADURGA | 17 | 338,163.00 | 39.80 | 37.61 | 0.84 | Onion | Maize |
| BELLARY | 16 | 309,023.63 | 33.99 | 23.90 | 2.78 | Rice | Maize |
| CHAMARAJANAGAR | 16 | 111,032.80 | 28.14 | 34.08 | 0.82 | Rice | Maize |
| KOLAR | 12 | 130,841.24 | 28.13 | 25.28 | 1.57 | Onion | Maize |
| GULBARGA | 16 | 641,072.60 | 27.29 | 26.85 | 0.63 | Maize | Groundnut |
| BIDAR | 17 | 302,562.81 | 26.46 | 21.90 | 0.90 | Potato | Soyabean |
| MYSORE | 14 | 251,779.69 | 25.81 | 29.80 | 1.06 | Maize | Ragi |
| CHIKMAGALUR | 15 | 134,691.12 | 25.33 | 23.81 | 1.37 | Maize | Maize |
| HAVERI | 18 | 239,544.75 | 21.60 | 16.60 | 2.65 | Onion | Maize |
| BELGAUM | 17 | 399,114.16 | 21.30 | 26.77 | 0.82 | Maize | Maize |
| BANGALORE RURAL | 16 | 114,059.05 | 20.59 | 19.94 | 2.05 | Potato | Rice |
| TUMKUR | 16 | 387,746.96 | 20.07 | 20.72 | 0.56 | Rice | Ragi |
| MANDYA | 17 | 139,627.39 | 19.35 | 24.42 | 1.64 | Potato | Rice |
| BENGALURU URBAN | 16 | 36,709.36 | 14.04 | 13.28 | 2.17 | Potato | Rice |
| DAVANGERE | 18 | 302,856.43 | 13.13 | 13.19 | 1.96 | Onion | Maize |
| UTTAR KANNAD | 8 | 78,230.11 | 6.80 | 6.98 | 1.82 | Maize | Maize |
| SHIMOGA | 14 | 168,564.03 | 6.22 | 6.95 | 2.36 | Maize | Maize |
| KODAGU | 4 | 35,901.22 | 3.03 | 3.21 | 2.45 | Maize | Maize |
| DAKSHIN KANNAD | 2 | 31,688.45 | 0.57 | 0.57 | 2.49 | Rice | Rice |
| UDUPI | 2 | 47,416.33 | 0.17 | 0.17 | 2.47 | Rice | Rice |