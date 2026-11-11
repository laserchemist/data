# Philadelphia Daily Weather, 1940–2025

**File:** `philly_weather_daily.csv` (31,069 rows: one row per day)
**Build script:** `build_philly_weather_daily.py` (downloads from NOAA and rebuilds the CSV)

## Source
NOAA National Centers for Environmental Information, Global Historical Climatology Network – Daily
(GHCN-Daily), station USW00013739, Philadelphia International Airport, PA (39.873° N, 75.227° W,
elevation 2 m). This is an official National Weather Service station.
https://www.ncei.noaa.gov/products/land-based-station/global-historical-climatology-network-daily
Retrieved November 2026.

## Columns
| Column | Meaning | Units |
|---|---|---|
| date | calendar date | YYYY-MM-DD |
| tmax_C | highest temperature of the day | °C |
| tmin_C | lowest temperature of the day | °C |
| precip_mm | precipitation (rain plus melted snow) | mm |
| snowfall_mm | new snow that fell | mm |
| snow_depth_mm | depth of snow on the ground | mm |
| wind_m_s | average wind speed | meters per second |
| precip_trace | True when precipitation fell but was too little to measure (recorded as 0) | True/False |
| snow_trace | True when snow fell but was too little to measure (recorded as 0) | True/False |

To convert: °F = °C × 9/5 + 32; inches = mm ÷ 25.4.

## How the file was built
- The NOAA file has about 100 columns; seven measurements were kept.
- NOAA stores temperature in tenths of a degree, precipitation in tenths of a millimeter and wind in
  tenths of a meter per second. These were converted to whole units.
- A value that failed one of NOAA's quality checks is left blank.
- Rows run from the start of the record (1 July 1940) through 31 December 2025, the last complete
  year.

## Things to know before analyzing
- **Two incomplete years.** The record starts in July 1940, and there are no observations at all
  from 23 June to 30 November 1945 (161 days). Annual totals or averages for 1940 and 1945 are not
  comparable with other years. 1946–2025 gives 80 complete years.
- **Wind speed starts in 1984.** `wind_m_s` is blank before then.
- **Trace amounts.** On 4,375 days precipitation fell but was too little to measure; it is recorded
  as 0 with `precip_trace` True. Whether those count as "rainy days" is your decision.
- **Days are not independent.** Today's temperature is strongly related to yesterday's
  (correlation 0.92). For questions about change over time, summarize by year first: years are much
  closer to independent than days.
- **One station is not the region, and the station's surroundings changed.** The airport and the
  city around it grew over these 86 years. Some warming at this site reflects the urban heat island
  and changes in instruments, not only regional climate. A trend here is a trend at this station.
- **Snow is measured by season, not calendar year.** A winter spans two calendar years; add up
  snowfall from July through June.

## A few reference values (1946–2025)
Hottest day 40.0 °C (3 July 1966); coldest −21.7 °C (17 January 1982); wettest day 203.7 mm
(28 July 2013); largest one-day snowfall 701 mm (7 January 1996). Warmest year 2024; coldest 1963.

## Citation
Menne, M. J., Durre, I., Vose, R. S., Gleason, B. E., & Houston, T. G. (2012). An overview of the
Global Historical Climatology Network-Daily database. *Journal of Atmospheric and Oceanic
Technology*, 29, 897–910. Data for station USW00013739 accessed November 2026.
Built for SCTC Elements of Data Science, November 2026.
