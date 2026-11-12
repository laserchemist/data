"""Build gene_expression_samples.csv: one row per sample for GEO series GSE15852.

Source: NCBI Gene Expression Omnibus, series GSE15852 (Pau Ni et al., breast tumors and
paired normal tissue, Affymetrix HG-U133A). Sample titles such as 'Normal BC0043N' and
'Cancer BC0043T' give the patient ID, which is what links each tumor to its paired normal sample.
Run:  python build_gene_expression_samples.py
"""
import urllib.request
import pandas as pd

URL = "https://www.ncbi.nlm.nih.gov/geo/query/acc.cgi?acc=GSE15852&targ=gsm&form=text&view=brief"
text = urllib.request.urlopen(URL).read().decode()

rows, cur = [], None
for line in text.splitlines():
    if line.startswith("^SAMPLE"):
        cur = {"Sample": line.split("= ")[1]}
        rows.append(cur)
    elif line.startswith("!Sample_title"):
        cur["title"] = line.split("= ")[1]
    elif line.startswith("!Sample_characteristics_ch1"):
        key, value = line.split("= ")[1].split(": ", 1)
        cur[key] = value

m = pd.DataFrame(rows)
out = pd.DataFrame({
    "Sample": m["Sample"],
    "Patient": m["title"].str.extract(r"(BC\d+)")[0],
    "Sample_Type": m["title"].str.split().str[0],          # Normal or Cancer
    "Grade": m["grade"].str.replace("grade ", "Grade "),   # normal, Grade 1, Grade 2, Grade 3
    "Age": m["age in years"].astype(int),
    "Histology": m["histopathological exam"],
})
out["Grade"] = out["Grade"].replace("normal", "Normal tissue")
out["Histology"] = out["Histology"].replace("normal", "normal tissue")
assert out["Patient"].notna().all() and (out.groupby("Patient").size() == 2).all()
out.to_csv("gene_expression_samples.csv", index=False)
print(out.shape, out["Patient"].nunique(), "patients")
