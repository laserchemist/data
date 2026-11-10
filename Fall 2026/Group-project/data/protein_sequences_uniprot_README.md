# Protein Sequences by Functional Class (UniProt)

**File:** `protein_sequences_uniprot.csv` (200 rows: 50 proteins in each of 4 classes)
**Build script:** `build_protein_sequences_uniprot.py` (queries UniProt and rebuilds the CSV)

Replaces `protein_sequences.csv` in the honors notebook. That older file contains
computer-generated sequences under real protein names (only 8 of 200 begin with methionine,
glutamine is the most common residue, and the class differences were set by the generator).
It is left in place because another section's notebook still uses it.

## Source
UniProtKB/Swiss-Prot, release 2026_04 — the manually reviewed section of the Universal Protein
Resource. https://www.uniprot.org. Every `Protein_ID` is a real UniProt accession; look any protein up
at `https://www.uniprot.org/uniprotkb/<Protein_ID>`.

## Columns
| Column | Meaning |
|---|---|
| Protein_ID | UniProt accession |
| Name | UniProt recommended protein name |
| Gene | Primary gene symbol |
| Function_Class | Enzyme, Membrane, Structural, or Transport (definitions below) |
| Sequence | Amino acid sequence, one-letter codes (canonical isoform) |
| Length | Number of amino acids |
| Organism | Human for every row |

## How the classes were defined
All entries: reviewed (Swiss-Prot), human, complete sequence (not a fragment), 100–2,000 amino acids.

| Class | UniProt query | Matching entries |
|---|---|---|
| Enzyme | has an EC number; no transmembrane segment | 3,515 |
| Membrane | Transmembrane keyword (KW-0812); not Transport (KW-0813); no EC number; olfactory receptors (KW-0552) excluded | 2,582 |
| Structural | GO: structural constituent of cytoskeleton (0005200), extracellular matrix (0005201), or skin epidermis (0030280); not transmembrane; no EC number | 225 |
| Transport | Transport (KW-0813) and Transmembrane (KW-0812) keywords; no EC number | 968 |

The classes do not overlap. From each class, 50 entries were drawn at random (seed 2026) from all
matching entries, sorted by accession, so rerunning the script against the same UniProt release
gives the same 200 proteins. A later release may give a different sample.

## Things to know before analyzing
- **The classes are definitions, not nature.** "Membrane" here means membrane proteins that are not
  transporters (mostly receptors and adhesion proteins); "Transport" means membrane transporters and
  channels, so both are membrane proteins. Soluble carriers such as hemoglobin are not in Transport.
  A different definition would give different results; that is worth discussing.
- **Olfactory receptors were excluded** from Membrane because about 400 nearly identical ones would
  dominate a random sample.
- **Structural is dominated by keratins** (12 of 50), because the human genome has many keratin genes.
  The 2,000-amino-acid limit drops the longest collagens.
- **Whole-sequence composition dilutes local signals.** A single-pass receptor may have one
  20-residue hydrophobic segment in a 500-residue protein; a transporter may have twelve.
- **One sequence does not start with M.** Q9Y6I0 is a retroviral protease that is cut out of a
  longer polyprotein, so its listed sequence starts in the middle. Every other sequence starts with
  methionine, as translated proteins do.
- **Annotations improve over time.** Keywords, GO terms and EC numbers are curated and can change
  between UniProt releases.

## Citation
The UniProt Consortium. UniProt: the Universal Protein Knowledgebase in 2025. *Nucleic Acids Research*
53:D609–D617 (2025). Data from UniProtKB/Swiss-Prot release 2026_04.
Built for SCTC Elements of Data Science, November 2026.
