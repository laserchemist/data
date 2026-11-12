# Philadelphia Daily PM2.5, 2021–2024

**File:** `philly_pm25_2021_2024.csv` (8,192 rows: one row per monitoring site per day)
**Build script:** `build_philly_pm25.py` (downloads the EPA files and rebuilds the CSV)

## Source
US Environmental Protection Agency, Air Quality System (AQS), pre-generated daily data files for
parameter 88101 (PM2.5 mass, FRM/FEM), years 2021–2024:
https://aqs.epa.gov/aqsweb/airdata/download_files.html
Monitors are operated by the City of Philadelphia Air Management Services.

## What PM2.5 is
Fine particulate matter: particles 2.5 micrometers across or smaller, small enough to reach deep
into the lungs. Sources include vehicles, power plants, industry, and smoke. In June 2023, smoke from
wildfires in Quebec, Canada blew south over the eastern United States; Philadelphia's worst day was
7 June 2023.

## Columns
| Column | Meaning |
|---|---|
| date | local date (YYYY-MM-DD) |
| site_id | AQS site number within Philadelphia County |
| site_name | monitoring site name |
| latitude, longitude | site location |
| pm25 | 24-hour average PM2.5 concentration, micrograms per cubic meter (µg/m³) |
| aqi | EPA Air Quality Index for that day, as reported by AQS |

## Sites
| site_id | Site | Days | Coverage |
|---|---|---|---|
| 0004 | Air Management Services Laboratory (AMS LAB) | 1,108 | starts 2 Oct 2021 |
| 0048 | North East Waste (NEW) | 1,447 | 2021–2024 |
| 0055 | Ritner (RIT) | 1,444 | 2021–2024 |
| 0057 | Fire Administration Building (FAB) | 1,379 | 2021–2024 |
| 0075 | Torresdale Station | 1,430 | 2021–2024 |
| 0076 | Car-Barn Montgomery I-76 | 1,384 | 2021–2024 |

Days are missing when a monitor was down; there are no blank values in the file.

## How the file was built
- Philadelphia County (state 42, county 101) rows only.
- AQS lists most days twice: one record tied to the 24-hour PM2.5 standard (rounded) and one
  unrounded record with no standard. The standard-linked record is kept.
- All sites use continuous Teledyne T640/T640X optical monitors. EPA applies a correction to these
  instruments. Through 30 June 2023 the corrected values are separate "(Corrected)" records; from
  1 July 2023 the correction ("Network Data Alignment") is applied in the instrument. The file uses
  the corrected values in both periods. This is a change in how the correction is delivered, not in
  the instrument, but keep it in mind when comparing before and after July 2023.
- The filter-based sampler at site 0048 (every 3rd or 6th day) is left out so all sites use the
  same method. Where a site has two monitors (site 0048), their values are averaged.

## Things to know before analyzing
- **Reference values:** EPA's 24-hour standard is 35 µg/m³; the annual standard is 9.0 µg/m³
  (tightened from 12.0 in 2024).
- **The smoke days:** citywide averages above 35 µg/m³ occurred on 6–8 June and 29–30 June 2023, and
  on 20–21 July 2021 (smoke from western wildfires). The highest site-day was 239.8 µg/m³ at
  Torresdale Station on 7 June 2023 (AQI 329, "Hazardous").
- **Days are not independent.** Pollution on one day is strongly related to the day before; smoke
  arrives in multi-day episodes. Simulations that treat days as independent draws will overstate
  how precise an estimate is.
- **Use `pm25`, not `aqi`, for averages and comparisons.** The AQI is a nonlinear index, and EPA
  revised the PM2.5 AQI breakpoints in 2024.
- **Sites are close together** (all within the city), so they usually rise and fall together.

## Citation
US Environmental Protection Agency. Air Quality System Data Mart, daily PM2.5 (parameter 88101)
files for 2021–2024. https://aqs.epa.gov/aqsweb/airdata/download_files.html
Built for SCTC Elements of Data Science, November 2026.
