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
import matplotlib
import matplotlib.pyplot as plt
get_ipython().run_line_magic("matplotlib", "inline")
plt.style.use("ggplot")
import math
import json, glob
import nbformat as nbf
from datascience import *
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
def test_open(text, notebook, length):
    """Check that the markdown cell after the one containing `text`
    has at least `length` characters."""
    nb_path = max(glob.glob("*.ipynb"), key=os.path.getmtime)
    ntbk = nbf.read(nb_path, nbf.NO_CONVERT)
    for i, cell in enumerate(ntbk.cells):
        if text in cell.source:
            nxt = ntbk.cells[i + 1]
            return 1 if len(nxt.source) >= length else 0
    return 0
