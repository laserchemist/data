"""
lab06_init.py
=============
Initialization for Lab 06 — Sampling and Simulation.
Students never need to open or edit this file.

Expected layout:
    course_root/
    ├── notebook_style.py
    ├── lab_submit.py
    ├── lab_submit_canvas.py
    ├── stemds_quiz.py
    └── lab06/
        ├── lab06_init.py           ← this file
        ├── lab6_*.ipynb
        ├── quiz06_hs.ipynb
        ├── questions_quiz06.json
        ├── data/
        │   ├── darwin_origin_species.txt
        │   ├── RSV_waste_1.txt
        │   └── stop.txt
        └── tests/

In the notebook:
    from lab06_init import *
"""

import sys, os

# ── add parent directory so shared files are importable ──────────────────────
# os.getcwd() is used instead of __file__ because __file__ is unreliable
# in JupyterHub — the notebook runs from inside the lab folder, so
# os.getcwd() gives the lab directory and '..' reaches the course root.
_parent = os.path.abspath(os.path.join(os.getcwd(), '..'))
if _parent not in sys.path:
    sys.path.insert(0, _parent)

# ── standard imports ──────────────────────────────────────────────────────────
import numpy as np
import math
import json, glob
import nbformat as nbf
import matplotlib
import matplotlib.pyplot as plt
get_ipython().run_line_magic("matplotlib", "inline")
plt.style.use("ggplot")
from datascience import *
from gofer.ok import check
from IPython.display import display
from jupyterquiz import display_quiz

# ── styling ───────────────────────────────────────────────────────────────────
from notebook_style import apply_style
apply_style()

# ── lab version ───────────────────────────────────────────────────────────────
ver = '2026V106'

# ── current notebook path ─────────────────────────────────────────────────────
notebook = max(glob.glob('*.ipynb'), key=os.path.getmtime)

# ── JupyterHub username ───────────────────────────────────────────────────────
user = os.getenv('JUPYTERHUB_USER', 'student')

# ── open-ended answer checker ─────────────────────────────────────────────────
def test_open(text, notebook, length):
    """Check that the markdown cell after the one containing 'text'
    has at least 'length' characters."""
    nb_path = max(glob.glob('*.ipynb'), key=os.path.getmtime)
    ntbk = nbf.read(nb_path, nbf.NO_CONVERT)
    for i, cell in enumerate(ntbk.cells):
        if text in cell.source:
            nxt = ntbk.cells[i + 1]
            return 1 if len(nxt.source) >= length else 0
    return 0
