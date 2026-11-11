"""Build pennypack_wy2024.csv: 15-minute data for Pennypack Creek, water year 2024.

Source: US Geological Survey, National Water Information System (NWIS) instantaneous values,
site 01467042 "Pennypack Creek at Pine Road, at Philadelphia, PA".
https://waterdata.usgs.gov/monitoring-location/01467042/
Water year 2024 = 1 October 2023 through 30 September 2024.
Run:  python build_pennypack_wy2024.py
"""
import io
import urllib.request
import pandas as pd

URL = ("https://nwis.waterservices.usgs.gov/nwis/iv/?format=rdb&sites=01467042"
       "&startDT=2023-10-01&endDT=2024-09-30"
       "&parameterCd=00010,00060,00065,00095,00300,00301,00400,63680")
NAMES = {
    "121357_00060": "discharge_cfs",
    "121358_00065": "gage_height_ft",
    "121360_00010": "temperature_C",
    "121361_00095": "specific_conductance_uS_cm",
    "121364_00300": "dissolved_oxygen_mg_L",
    "121365_00301": "dissolved_oxygen_pct_sat",
    "121362_00400": "pH",
    "277154_63680": "turbidity_FNU",
}

text = urllib.request.urlopen(URL).read().decode()
d = pd.read_csv(io.StringIO(text), sep="\t", comment="#", dtype=str).iloc[1:]  # row 0 is a format line

# USGS reports local clock time (EDT in summer, EST in winter). Put everything on Eastern
# Standard Time so there is no repeated or skipped hour when the clocks change.
t = pd.to_datetime(d["datetime"])
t = t - pd.to_timedelta((d["tz_cd"] == "EDT").astype(int), unit="h")
out = pd.DataFrame({"datetime": t.dt.strftime("%Y-%m-%d %H:%M")})
for code, name in NAMES.items():
    out[name] = pd.to_numeric(d[code], errors="coerce").values   # '***' (unavailable) becomes blank
# '<' qualifier: the true turbidity is below the reported value (the sensor's lower limit)
out["turbidity_below_limit"] = d["277154_63680_cd"].fillna("").str.contains("<").values

assert out["datetime"].is_unique and len(out) == 366 * 96
out.to_csv("pennypack_wy2024.csv", index=False)
print(out.shape, out["datetime"].iloc[0], "to", out["datetime"].iloc[-1])
