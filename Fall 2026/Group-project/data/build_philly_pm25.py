"""Build philly_pm25_2021_2024.csv: daily PM2.5 at each Philadelphia monitoring site, 2021-2024.

Source: US EPA Air Quality System (AQS), pre-generated daily data files for parameter 88101
(PM2.5 FRM/FEM mass), https://aqs.epa.gov/aqsweb/airdata/download_files.html
Run:  python build_philly_pm25.py   (downloads the yearly files if not present)
"""
import os
import urllib.request
import pandas as pd

YEARS = [2021, 2022, 2023, 2024]
URL = "https://aqs.epa.gov/aqsweb/airdata/daily_88101_{}.zip"

frames = []
for y in YEARS:
    path = f"daily_88101_{y}.zip"
    if not os.path.exists(path):
        urllib.request.urlretrieve(URL.format(y), path)
    d = pd.read_csv(path, dtype={"State Code": str, "County Code": str, "Site Num": str})
    frames.append(d[(d["State Code"] == "42") & (d["County Code"] == "101")])  # Philadelphia County, PA
d = pd.concat(frames)

# Keep the regulatory record for each day (rows tied to the 24-hour standard; AQS also lists an
# unrounded duplicate with no standard).
d = d[d["Pollutant Standard"].notna()]
# Continuous Teledyne T640/T640X monitors, using EPA's corrected values: through 2023-06-30 these are
# reported as separate "(Corrected)" records; from 2023-07-01 the correction ("Network Data
# Alignment") is applied in the instrument itself. The every-3rd/6th-day filter sampler at site 0048
# (gravimetric, POC 1) is left out so that every site uses the same method.
corrected = d["Method Name"].str.contains("Corrected") & (d["Date Local"] <= "2023-06-30")
aligned = d["Method Name"].str.contains("Network Data Alignment") & (d["Date Local"] >= "2023-07-01")
d = d[corrected | aligned]

# Site 0048 has two monitors; average monitors at the same site and day.
daily = (d.groupby(["Date Local", "Site Num", "Local Site Name", "Latitude", "Longitude"], as_index=False)
          .agg(pm25=("Arithmetic Mean", "mean"), aqi=("AQI", "max"), monitors=("POC", "nunique")))
daily = daily.rename(columns={"Date Local": "date", "Site Num": "site_id",
                              "Local Site Name": "site_name", "Latitude": "latitude", "Longitude": "longitude"})
daily["pm25"] = daily["pm25"].round(1)
daily["aqi"] = daily["aqi"].astype("Int64")
daily = daily[["date", "site_id", "site_name", "latitude", "longitude", "pm25", "aqi"]]
daily = daily.sort_values(["date", "site_id"], ignore_index=True)
assert not daily.duplicated(["date", "site_id"]).any()
daily.to_csv("philly_pm25_2021_2024.csv", index=False)
print(daily.shape)
