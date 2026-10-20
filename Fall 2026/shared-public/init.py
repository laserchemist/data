"""
init.py
=======
Universal initialization, shared by EVERY lab in this course.
Lives in shared-public/, one directory above lab00/, lab01/, lab05/, etc.
Students never need to open or edit this file.

Expected directory layout:
    Fall 2026/
    ├── shared-public/
    │   ├── init.py            ← this file
    │   ├── lab_submit.py      ← shared submission helper
    │   ├── notebook_style.py  ← shared styling
    │   └── eds_mod.py         ← shared helper functions (ptrend, etc.)
    ├── lab00/
    │   └── lab00_undergrad.ipynb
    ├── lab01/
    │   ├── lab01_undergrad.ipynb
    │   └── tests_01/
    ├── lab04/
    │   ├── lab04_undergrad.ipynb
    │   └── tests/
    └── lab05/
        ├── lab05_undergrad.ipynb
        └── tests/

In the first cell of any lab notebook, the entire setup is just:

    import sys, os
    sys.path.insert(0, os.path.abspath(os.path.join(os.getcwd(), "..", "shared-public")))
    from init import *
"""

import sys, os, subprocess

# ── make sure gspread is available for Google-Sheets submission ──────────────
try:
    import gspread  # noqa: F401
except ImportError:
    subprocess.run(
        [sys.executable, "-m", "pip", "install", "-q", "gspread", "google-auth"],
        check=False,
    )

# ── standard data-science stack ───────────────────────────────────────────────
import numpy as np

import math
import json, glob
import nbformat as nbf
from datascience import *
import matplotlib
import matplotlib.pyplot as plt
get_ipython().run_line_magic("matplotlib", "inline")
plt.style.use("ggplot")
from gofer.ok import check
from IPython.display import display
from jupyterquiz import display_quiz

# ── styling + submission helper + course helper functions (all alongside this file) ──
from notebook_style import apply_style
from lab_submit import submit_lab
from eds_mod import ptrend
apply_style()

# ── course / content version ──────────────────────────────────────────────────
COURSE_VERSION = "2026FallV1"

# ── current notebook path ─────────────────────────────────────────────────────
notebook = max(glob.glob("*.ipynb"), key=os.path.getmtime)

# ── JupyterHub username ───────────────────────────────────────────────────────
user = os.getenv("JUPYTERHUB_USER", "student")


# ── open-ended answer checker ──────────────────────────────────────────────────
def _open_answer_text(source):
    """Student text in one markdown cell, with course placeholders removed."""
    import re
    kept = []
    for line in source.splitlines():
        s = line.strip()
        if s in ("---", "***", "<br>"):
            continue
        if re.fullmatch(r"#+\s*save notebook before check\.?", s, re.I):
            continue
        kept.append(line)
    text = "\n".join(kept).strip()
    text = re.sub(r"<font color=['\"]?blue['\"]?>\s*\*Write your answer here, replacing this text\.\*\s*</font>",
                  "", text, flags=re.I)
    for placeholder in ("*Your answer — double-click to edit*", "YOUR FEEDBACK..."):
        text = text.replace(placeholder, "")
    text = text.strip()
    if text.upper().startswith("ANSWER"):
        text = text[len("ANSWER"):].lstrip(" :.-\n")
    if text.upper().startswith("HERE"):
        text = text[len("HERE"):].lstrip(" :.-\n")
    if text == "...":
        text = ""
    return text.strip()


def test_open(text, notebook, length):
    """Check that the student wrote at least `length` characters in answer to
    the question in the first cell containing `text`.

    The answer may be in the cell right after the question (the ANSWER
    placeholder, overwritten or not) or in any markdown cells the student
    added below it. The answer region ends at the next code cell, the next
    heading (e.g. "#### Save notebook before check"), or a cell that starts
    with '---' followed by more text. Placeholders ("ANSWER", "...", etc.)
    and separators don't count. The original rule (next cell >= length) is
    kept, so nothing that passed before can fail now."""
    nb_path = max(glob.glob("*.ipynb"), key=os.path.getmtime)
    ntbk = nbf.read(nb_path, nbf.NO_CONVERT)
    for i, cell in enumerate(ntbk.cells):
        if text in cell.source:
            if i + 1 < len(ntbk.cells) and len(ntbk.cells[i + 1].source) >= length:
                return 1                      # original rule
            answer = ""
            for nxt in ntbk.cells[i + 1:]:
                src = nxt.source.strip()
                if nxt.cell_type == "code" or src.startswith("#"):
                    break
                if src.startswith("---") and src.lstrip("-").strip():
                    break
                if nxt.cell_type == "markdown":
                    answer += _open_answer_text(nxt.source)
            if len(answer) >= length:
                return 1
            print(f"Found the question in {nb_path}, but your answer there has "
                  f"{len(answer)} characters (at least {length} needed, not counting "
                  f"'ANSWER'). Save the notebook (File > Save), then run this check again.")
            return 0
    print(f"Couldn't find this question in {nb_path}, the most recently saved "
          f"notebook in this folder. Save this notebook (File > Save), then run this check again.")
    return 0
