"""Build philly_weather_daily.csv: daily weather at Philadelphia International Airport, 1940-2025.

Source: NOAA National Centers for Environmental Information, Global Historical Climatology
Network - Daily (GHCN-Daily), station USW00013739 (Philadelphia International Airport, PA).
https://www.ncei.noaa.gov/products/land-based-station/global-historical-climatology-network-daily
Run:  python build_philly_weather_daily.py
"""
import pandas as pd

URL = ("https://www.ncei.noaa.gov/data/global-historical-climatology-network-daily/"
       "access/USW00013739.csv")
FIRST, LAST = "1940-07-01", "2025-12-31"     # start of record through the last complete year

d = pd.read_csv(URL, dtype=str)
d = d[(d["DATE"] >= FIRST) & (d["DATE"] <= LAST)]


def value(element, divide_by):
    """Numeric value of one element; blank if missing or if it failed NOAA's quality check.

    ELEMENT_ATTRIBUTES is 'measurement flag,quality flag,source flag[,time]'.
    A non-blank quality flag means the value failed a quality-assurance check.
    """
    x = pd.to_numeric(d[element], errors="coerce")
    quality = d[element + "_ATTRIBUTES"].fillna(",,").str.split(",").str[1]
    return (x.where(quality == "") / divide_by)


out = pd.DataFrame({
    "date": d["DATE"],
    "tmax_C": value("TMAX", 10).round(1),          # stored in tenths of a degree C
    "tmin_C": value("TMIN", 10).round(1),
    "precip_mm": value("PRCP", 10).round(1),       # stored in tenths of a mm
    "snowfall_mm": value("SNOW", 1),               # stored in mm
    "snow_depth_mm": value("SNWD", 1),
    "wind_m_s": value("AWND", 10).round(1),        # stored in tenths of a meter per second
})
# 'T' measurement flag = trace: precipitation or snow fell but was too little to measure
out["precip_trace"] = (d["PRCP_ATTRIBUTES"].fillna("").str.split(",").str[0] == "T").values
out["snow_trace"] = (d["SNOW_ATTRIBUTES"].fillna("").str.split(",").str[0] == "T").values

assert out["date"].is_unique
out.to_csv("philly_weather_daily.csv", index=False)
print(out.shape, out["date"].iloc[0], "to", out["date"].iloc[-1])
