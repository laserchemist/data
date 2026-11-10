"""Build protein_sequences_uniprot.csv: 50 real human proteins in each of four functional classes.

Source: UniProtKB/Swiss-Prot (reviewed entries), https://www.uniprot.org, via the REST API.
Each class is defined by a reproducible UniProt query (below); 50 entries are drawn at random
(fixed seed) from all entries that match. Run:  python build_protein_sequences_uniprot.py
"""
import io
import urllib.parse
import urllib.request
import numpy as np
import pandas as pd

STREAM = "https://rest.uniprot.org/uniprotkb/stream"
FIELDS = "accession,protein_name,gene_primary,length,sequence"
BASE = "reviewed:true AND organism_id:9606 AND fragment:false AND length:[100 TO 2000]"
CLASSES = {
    # soluble enzymes: has an EC number, no transmembrane segment
    "Enzyme": "ec:* AND NOT keyword:KW-0812",
    # membrane proteins that are not transporters or enzymes (mostly receptors and adhesion
    # proteins); olfactory receptors excluded so ~400 near-identical ORs don't dominate
    "Membrane": "keyword:KW-0812 AND NOT keyword:KW-0813 AND NOT ec:* AND NOT keyword:KW-0552",
    # mechanical-support proteins: structural constituent of cytoskeleton (GO:0005200),
    # of extracellular matrix (GO:0005201), or of skin epidermis (GO:0030280);
    # not membrane, not enzyme
    "Structural": "(go:0005200 OR go:0005201 OR go:0030280) AND NOT keyword:KW-0812 AND NOT ec:*",
    # membrane transporters and channels: Transport keyword + transmembrane, not enzyme
    "Transport": "keyword:KW-0813 AND keyword:KW-0812 AND NOT ec:*",
}
N_PER_CLASS = 50
SEED = 2026


def fetch(query):
    url = STREAM + "?" + urllib.parse.urlencode(
        {"query": f"({BASE}) AND ({query})", "format": "tsv", "fields": FIELDS})
    with urllib.request.urlopen(url) as r:
        release = r.headers.get("X-UniProt-Release", "unknown")
        text = r.read().decode()
    df = pd.read_csv(io.StringIO(text), sep="\t").sort_values("Entry", ignore_index=True)
    return df, release  # sorted so the seeded sample depends only on the UniProt release


rng = np.random.default_rng(SEED)
parts, info = [], []
for cls, q in CLASSES.items():
    df, release = fetch(q)
    pick = df.iloc[rng.choice(len(df), N_PER_CLASS, replace=False)].copy()
    pick["Function_Class"] = cls
    parts.append(pick)
    info.append((cls, len(df)))

out = pd.concat(parts, ignore_index=True)
out = out.rename(columns={"Entry": "Protein_ID", "Protein names": "Name",
                          "Gene Names (primary)": "Gene", "Length": "Length",
                          "Sequence": "Sequence"})
# keep the recommended name only (UniProt appends alternative names in parentheses)
out["Name"] = out["Name"].str.replace(r"\s+\(.*$", "", regex=True)
out["Organism"] = "Human"
out = out[["Protein_ID", "Name", "Gene", "Function_Class", "Sequence", "Length", "Organism"]]
assert out.Protein_ID.is_unique and (out.Sequence.str.len() == out.Length).all()
out.to_csv("protein_sequences_uniprot.csv", index=False)
print("UniProt release:", release)
for cls, n in info:
    print(f"{cls}: sampled {N_PER_CLASS} of {n} matching entries")
