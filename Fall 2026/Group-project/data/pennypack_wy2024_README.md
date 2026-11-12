# Pennypack Creek, Water Year 2024 (15-minute data)

**File:** `pennypack_wy2024.csv` (35,136 rows: one reading every 15 minutes for 366 days)
**Build script:** `build_pennypack_wy2024.py` (downloads from USGS and rebuilds the CSV)

## Source
US Geological Survey, National Water Information System, site 01467042,
"Pennypack Creek at Pine Road, at Philadelphia, PA".
https://waterdata.usgs.gov/monitoring-location/01467042/
Retrieved November 2026. Water year 2024 runs from 1 October 2023 to 30 September 2024.

## Columns
| Column | Measurement | Units |
|---|---|---|
| datetime | time of the reading, Eastern Standard Time all year | YYYY-MM-DD HH:MM |
| discharge_cfs | discharge (stream flow) | cubic feet per second |
| gage_height_ft | gage height (water level) | feet |
| temperature_C | water temperature | °C |
| specific_conductance_uS_cm | specific conductance at 25 °C (a measure of dissolved salts) | microsiemens per cm |
| dissolved_oxygen_mg_L | dissolved oxygen | mg/L |
| dissolved_oxygen_pct_sat | dissolved oxygen | percent of saturation |
| pH | pH | standard units |
| turbidity_FNU | turbidity (cloudiness from suspended particles) | formazin nephelometric units |
| turbidity_below_limit | True when the true turbidity is below the reported value (sensor's lower limit of 0.3) | True/False |

## How the file was built
- Columns were renamed from USGS time-series codes (for example `121357_00060` is discharge).
- **Time is Eastern Standard Time all year.** USGS reports local clock time; readings taken during
  daylight saving time were shifted back one hour, so no hour is repeated or skipped. Because of
  this the file starts at 23:00 on 30 September 2023 and ends at 22:45 on 30 September 2024.
- Values USGS marks as unavailable are blank.
- USGS quality codes were dropped except the turbidity "less than" flag. Discharge, gage height,
  temperature, conductance, dissolved oxygen (mg/L), pH and turbidity are **approved** (reviewed)
  values, apart from one provisional discharge reading. Dissolved oxygen percent saturation is
  still marked provisional.

## Things to know before analyzing
- **The water-quality sensors were removed for the winter.** USGS pulls them because they ice
  over. Temperature, conductance, dissolved
  oxygen, pH and turbidity are blank from 4 December 2023 (13:45) to 29 February 2024 (16:00).
  Discharge and gage height are recorded all year. Dissolved oxygen percent saturation is also
  blank from 1 October to 10 November 2023.
- **No road-salt season.** Road salt reaches streams in winter and raises specific conductance,
  but the conductance sensor is out of the water for exactly those months. The missing values are
  not missing at random: they are missing when a particular thing happens.
- **Readings are not independent.** Each reading is almost identical to the one 15 minutes earlier
  (correlation 0.94 or higher for every measurement). Treating 35,000 readings as 35,000 independent
  observations makes any estimate look far more certain than it is. Days, or storms, are closer to
  independent units.
- **Storms dominate.** Median discharge is 43 cfs; the peak is 4,930 cfs (18 December 2023 and
  10 January 2024). Daily peak discharge exceeded 200 cfs on 50 days. Use logarithms for discharge
  and turbidity.
- **Discharge is computed from gage height** with a rating curve, so their close relationship is
  built in, not a finding.
- **Turbidity has a floor.** 142 readings are at the sensor's lower limit of 0.3 FNU.

## Citation
U.S. Geological Survey, 2026, National Water Information System data available on the World Wide
Web (USGS Water Data for the Nation), site 01467042, accessed November 2026.
https://waterdata.usgs.gov/nwis
Built for SCTC Elements of Data Science, November 2026.
