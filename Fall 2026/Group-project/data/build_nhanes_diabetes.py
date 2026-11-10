"""Build nhanes_diabetes_2021_2023.csv from public NHANES August 2021-August 2023 files.

Source: CDC/NCHS National Health and Nutrition Examination Survey
https://wwwn.cdc.gov/nchs/nhanes/  (files DEMO_L, GHB_L, GLU_L, BMX_L, BPXO_L, DIQ_L, SMQ_L)

Run:  python build_nhanes_diabetes.py   (downloads the .xpt files if not present)
"""
import os
import urllib.request
import numpy as np
import pandas as pd

BASE = "https://wwwn.cdc.gov/Nchs/Data/Nhanes/Public/2021/DataFiles/"
FILES = ["DEMO_L", "GHB_L", "GLU_L", "BMX_L", "BPXO_L", "DIQ_L", "SMQ_L"]


def load(name):
    path = name + ".xpt"
    if not os.path.exists(path):
        urllib.request.urlretrieve(BASE + path, path)
    df = pd.read_sas(path)
    # SAS transport stores 0 as ~5e-79; set tiny values back to 0
    num = df.select_dtypes("number").columns
    df[num] = df[num].mask(df[num].abs() < 1e-10, 0)
    df["SEQN"] = df["SEQN"].astype(int)
    return df.set_index("SEQN")


demo, ghb, glu, bmx, bpx, diq, smq = (load(f) for f in FILES)

# ---- sample: examined, non-pregnant adults 20+ with an HbA1c result ----
d = demo[(demo.RIDSTATR == 2) & (demo.RIDAGEYR >= 20) & (demo.RIDEXPRG != 1)]  # exclude pregnant
d = d.join(ghb, how="inner")
d = d[d.LBXGH.notna()]
d = d.join([glu, bmx, bpx, diq, smq], how="left")

out = pd.DataFrame(index=d.index)
out["age"] = d.RIDAGEYR.astype(int)
out["sex"] = d.RIAGENDR.map({1: "Male", 2: "Female"})
out["race_ethnicity"] = d.RIDRETH3.map({
    1: "Mexican American", 2: "Other Hispanic", 3: "Non-Hispanic White",
    4: "Non-Hispanic Black", 6: "Non-Hispanic Asian", 7: "Other or Multiracial"})
out["education"] = d.DMDEDUC2.map({
    1: "Less than 9th grade", 2: "9-11th grade", 3: "High school/GED",
    4: "Some college/AA", 5: "College graduate"})
out["income_poverty_ratio"] = d.INDFMPIR.round(2)

# smoking: SMQ020 (100+ cigarettes ever), SMQ040 (smoke now)
smoke = pd.Series(np.nan, index=d.index, dtype=object)
smoke[d.SMQ020 == 2] = "Never"
smoke[(d.SMQ020 == 1) & (d.SMQ040 == 3)] = "Former"
smoke[(d.SMQ020 == 1) & d.SMQ040.isin([1, 2])] = "Current"
out["smoking"] = smoke

out["height_cm"] = d.BMXHT.round(1)
out["weight_kg"] = d.BMXWT.round(1)
out["bmi"] = d.BMXBMI.round(1)
out["waist_cm"] = d.BMXWAIST.round(1)
out["systolic_bp"] = d[["BPXOSY1", "BPXOSY2", "BPXOSY3"]].mean(axis=1).round(1)
out["diastolic_bp"] = d[["BPXODI1", "BPXODI2", "BPXODI3"]].mean(axis=1).round(1)

out["hba1c"] = d.LBXGH.round(1)
# fasting glucose only where the participant met the 8-24 h fasting requirement
valid_fast = d.WTSAF2YR > 0
out["fasting_glucose"] = d.LBXGLU.where(valid_fast)

out["diagnosed_diabetes"] = d.DIQ010.map({1: "Yes", 2: "No", 3: "Borderline"})

# medication: insulin (DIQ050) or diabetes pills (DIQ070)
med = pd.Series(np.nan, index=d.index, dtype=object)
med[(d.DIQ050 == 2) | (d.DIQ070 == 2) | d.DIQ010.isin([2, 3])] = "No"
med[(d.DIQ050 == 1) | (d.DIQ070 == 1)] = "Yes"
out["diabetes_medication"] = med

# glycemic status (ADA lab cutoffs; a reported diagnosis takes precedence)
a1c, fpg = out.hba1c, out.fasting_glucose
status = pd.Series("Normal", index=d.index, dtype=object)
status[(a1c >= 5.7) | (fpg >= 100)] = "Prediabetes"
status[(a1c >= 6.5) | (fpg >= 126)] = "Undiagnosed diabetes"
status[out.diagnosed_diabetes == "Yes"] = "Diagnosed diabetes"
out["glycemic_status"] = status

out["sample_weight"] = d.WTPH2YR.round(1)
out["fasting_weight"] = d.WTSAF2YR.where(valid_fast).round(1)

for c in ["education", "smoking"]:
    out[c] = out[c].fillna("Unknown")

out = out.reset_index().rename(columns={"SEQN": "id"})
out.to_csv("nhanes_diabetes_2021_2023.csv", index=False)
print(out.shape)
