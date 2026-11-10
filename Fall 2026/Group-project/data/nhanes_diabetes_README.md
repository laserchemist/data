# NHANES Diabetes Dataset (August 2021 – August 2023)

**File:** `nhanes_diabetes_2021_2023.csv` (5,730 rows × 20 columns)
**Data dictionary:** `nhanes_diabetes_data_dictionary.csv`
**Build script:** `build_nhanes_diabetes.py` (downloads the source files from CDC and rebuilds the CSV)

## Source
National Health and Nutrition Examination Survey (NHANES), National Center for Health Statistics,
Centers for Disease Control and Prevention. Public-use files, August 2021 – August 2023 cycle,
first published September 2024. https://wwwn.cdc.gov/nchs/nhanes/

| NHANES file | Contents used |
|---|---|
| DEMO_L | age, sex, race/Hispanic origin, education, income-to-poverty ratio, pregnancy status |
| GHB_L | HbA1c, blood-test survey weight |
| GLU_L | fasting plasma glucose, fasting survey weight |
| BMX_L | height, weight, BMI, waist circumference |
| BPXO_L | three oscillometric blood-pressure readings |
| DIQ_L | doctor-diagnosed diabetes, insulin, diabetes pills |
| SMQ_L | cigarette smoking |

Codebooks: `https://wwwn.cdc.gov/Nchs/Data/Nhanes/Public/2021/DataFiles/<FILE>.htm`

## How the data were collected
NHANES is a nationally representative survey of the US civilian, non-institutionalized population.
Participants are chosen by a multistage probability sample, interviewed at home, and examined in a
mobile examination center, where blood is drawn and body measurements are taken. Lab values and
body measurements are **measured**; diagnosis, medication, smoking, education and income are
**self-reported**.

## Who is in this file
Examined adults age 20 and older who had an HbA1c result, excluding women who were pregnant at the
exam (pregnancy changes HbA1c and glucose). Each row is one person; there are no duplicate people.

## Things to know before analyzing
- **Survey design.** NHANES deliberately oversamples some groups (for example, older adults and some
  racial/ethnic groups). Unweighted percentages describe this sample, not the US population. Example:
  14.3% of rows have diagnosed diabetes, but the weighted US estimate is 11.8%.
  `sample_weight` (or `fasting_weight` for glucose) gives the number of US adults each person
  represents. Most in-class analyses can ignore the weights if the limitation is stated.
- **Fasting glucose is a subsample.** Only about half of participants were assigned to the morning
  fasting session and fasted 8–24 hours. Glucose is blank for everyone else; this is by design,
  not because of anything about the person.
- **`glycemic_status` is derived**, using American Diabetes Association cutoffs. People without
  fasting glucose are classified by HbA1c alone, which misses some undiagnosed cases.
- **Treatment lowers HbA1c.** People taking insulin or diabetes pills may have "normal" lab values.
  Compare `diabetes_medication` before treating HbA1c as a measure of disease.
- **Top-coding.** Age 80 means 80 or older; income-to-poverty ratio 5 means 5 or more.
- **Missing values** are blank (they appear as `nan` in a Table). Categorical gaps are coded `Unknown`.
- **Observational data.** Associations (e.g., waist size and HbA1c) are not causal effects.

## Validation
Reproduces the published NCHS estimates for adults 20+ in this cycle (NCHS Data Brief No. 516,
November 2024, https://www.cdc.gov/nchs/products/databriefs/db516.htm), using the fasting subsample
(n = 2,938) and fasting weights:

| | This file | NCHS Data Brief 516 |
|---|---|---|
| Diagnosed diabetes | 11.3% | 11.3% |
| Undiagnosed diabetes | 4.5% | 4.5% |
| Total diabetes | 15.8% | 15.8% |

## Citation
Centers for Disease Control and Prevention, National Center for Health Statistics. National Health
and Nutrition Examination Survey Data, August 2021 – August 2023. Hyattsville, MD: U.S. Department
of Health and Human Services. https://wwwn.cdc.gov/nchs/nhanes/
Built for SCTC Elements of Data Science, November 2026.
