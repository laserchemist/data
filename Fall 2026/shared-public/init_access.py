"""
init_access.py
==============
Accessibility-focused drop-in replacement for init.py.
Lives in shared-public/ next to init.py. Students never need to open or edit it.

Everything init.py provides is still provided (same names, same behavior), plus:

  • Notebook text   — larger, more readable font (Atkinson Hyperlegible, designed
                      for low-vision readers), more line spacing, underlined links,
                      visible keyboard focus, darker body text in light themes.
  • Plots           — colorblind-safe Okabe–Ito palette, line styles that differ
                      as well as colors, larger fonts and markers, white background
                      (higher contrast than ggplot's gray), 'cividis' colormap.
  • Tables          — datascience Table plots (.scatter, .hist, .plot, .barh)
                      use the same colorblind-safe palette and larger figures.
  • show_plot(alt)  — display the current figure with alt text that screen
                      readers can announce.
  • set_access(...) — change the settings at any time (bigger text, a different
                      font, turn the notebook styling off, ...).

In the first cell of a lab notebook, use it exactly like init.py:

    import sys, os
    sys.path.insert(0, os.path.abspath(os.path.join(os.getcwd(), "..", "shared-public")))
    from init_access import *

Instructor note: every setting lives in ACCESS_DEFAULTS below. Adjust there to
change the course-wide default; students can override per notebook with
set_access(...).
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

# ── standard data-science stack (same as init.py) ────────────────────────────
import numpy as np

import math
import json, glob
import base64, io
import nbformat as nbf
from datascience import *
import matplotlib
import matplotlib.pyplot as plt
from cycler import cycler
get_ipython().run_line_magic("matplotlib", "inline")
from gofer.ok import check
from IPython.display import display, HTML
from jupyterquiz import display_quiz

# ── submission helper + course helper functions (alongside this file) ────────
from lab_submit import submit_lab
from eds_mod import ptrend

# The regular course styling is applied first, so anything it sets that the
# accessibility layer doesn't touch (headers, logos, ...) is kept. If it is
# missing or fails, the accessibility layer still works on its own.
try:
    from notebook_style import apply_style
    apply_style()
except Exception:
    pass

# ── course / content version ──────────────────────────────────────────────────
COURSE_VERSION = "2026FallV1"
ACCESSIBLE = True          # labs can check this to know which init was loaded

# ── current notebook path ─────────────────────────────────────────────────────
notebook = max(glob.glob("*.ipynb"), key=os.path.getmtime)

# ── JupyterHub username ───────────────────────────────────────────────────────
user = os.getenv("JUPYTERHUB_USER", "student")


# ══════════════════════════════════════════════════════════════════════════════
#  ACCESSIBILITY SETTINGS — instructor: edit defaults here
# ══════════════════════════════════════════════════════════════════════════════

# Okabe & Ito (2008) colorblind-safe palette, ordered so the first colors are
# distinguishable under all common color-vision deficiencies and readable on
# white. Yellow (#F0E442) has low contrast on white, so it comes last.
OKABE_ITO = [
    "#0072B2",  # blue
    "#D55E00",  # vermillion
    "#009E73",  # bluish green
    "#CC79A7",  # reddish purple
    "#E69F00",  # orange
    "#56B4E9",  # sky blue
    "#000000",  # black
    "#F0E442",  # yellow
]

ACCESS_DEFAULTS = dict(
    font_scale=1.15,                   # 1.0 = JupyterLab default size
    font="Atkinson Hyperlegible",      # any Google Font name, or None for the theme font
    code_font="Atkinson Hyperlegible Mono",
    line_height=1.6,
    high_contrast=True,                # darker text + underlined links (light themes only)
    notebook_css=True,                 # False = leave the notebook appearance alone
    plot_scale=1.0,                    # scales plot fonts, lines and markers
    palette=OKABE_ITO,
    colormap="cividis",                # perceptually uniform and colorblind-safe
)

ACCESS = dict(ACCESS_DEFAULTS)


def _hex_to_rgb(h):
    h = h.lstrip("#")
    return tuple(int(h[i:i + 2], 16) / 255 for i in (0, 2, 4))


def _apply_plot_style():
    s = ACCESS["plot_scale"]
    palette = ACCESS["palette"]
    styles = ["-", "--", "-.", ":"]
    plt.style.use("default")           # white background: higher contrast than ggplot gray
    plt.rcParams.update({
        "figure.figsize": (8, 5),
        "figure.dpi": 110,
        "savefig.dpi": 150,
        "font.size": 13 * s,
        "axes.titlesize": 16 * s,
        "axes.titleweight": "bold",
        "axes.labelsize": 15 * s,
        "xtick.labelsize": 13 * s,
        "ytick.labelsize": 13 * s,
        "legend.fontsize": 12 * s,
        "legend.frameon": True,
        "legend.framealpha": 0.9,
        "lines.linewidth": 2.5 * s,
        "lines.markersize": 7 * s,
        "axes.linewidth": 1.2,
        "axes.grid": True,
        "grid.alpha": 0.35,
        "axes.spines.top": False,
        "axes.spines.right": False,
        "axes.edgecolor": "#222222",
        "axes.labelcolor": "#111111",
        "xtick.color": "#222222",
        "ytick.color": "#222222",
        "image.cmap": ACCESS["colormap"],
        # Lines differ by style as well as color, so they can be told apart
        # in grayscale printouts and without color vision.
        "axes.prop_cycle": cycler(color=palette)
                           + cycler(linestyle=(styles * 2)[:len(palette)]),
    })
    # datascience Table plots use their own palette and sizes
    Table.chart_colors = tuple(_hex_to_rgb(c) for c in palette)
    Table.default_width = 8
    Table.default_height = 5


def _notebook_css():
    a = ACCESS
    fonts = []
    for f in (a["font"], a["code_font"]):
        if f:
            fonts.append("family=" + f.replace(" ", "+") + ":ital,wght@0,400;0,700;1,400")
    font_import = (f"@import url('https://fonts.googleapis.com/css2?{'&'.join(fonts)}&display=swap');"
                   if fonts else "")
    body_font = f"'{a['font']}', " if a["font"] else ""
    code_font = f"'{a['code_font']}', " if a["code_font"] else ""
    size = 14 * a["font_scale"]
    code_size = 13 * a["font_scale"]

    contrast = ""
    if a["high_contrast"]:
        contrast = """
/* Light themes only: darker body text, never color-only links */
body[data-jp-theme-light='true'] {
  --jp-content-font-color1: #111111;
  --jp-content-font-color2: #222222;
  --jp-ui-font-color1: #111111;
}
.jp-RenderedHTMLCommon a, .rendered_html a { text-decoration: underline; }
"""
    return f"""
<style>
{font_import}
:root {{
  --jp-content-font-family: {body_font}system-ui, -apple-system, 'Segoe UI', sans-serif;
  --jp-ui-font-family: {body_font}system-ui, -apple-system, 'Segoe UI', sans-serif;
  --jp-code-font-family: {code_font}'DejaVu Sans Mono', Menlo, Consolas, monospace;
  --jp-content-font-size1: {size:.1f}px;
  --jp-content-line-height: {a['line_height']};
  --jp-code-font-size: {code_size:.1f}px;
  --jp-code-line-height: 1.5;
}}
/* Classic Notebook / NbClassic equivalents */
.rendered_html, .text_cell_render {{
  font-family: {body_font}system-ui, sans-serif; font-size: {size:.1f}px; line-height: {a['line_height']};
}}
.CodeMirror, .cm-editor {{ font-family: {code_font}monospace; font-size: {code_size:.1f}px; }}
/* Readable line length for long paragraphs */
.jp-RenderedMarkdown p, .rendered_html p {{ max-width: 80ch; }}
/* Tables (including datascience Tables): bigger, zebra-striped */
.jp-RenderedHTMLCommon table, .rendered_html table {{ font-size: {size * 0.95:.1f}px; }}
.jp-RenderedHTMLCommon tbody tr:nth-child(odd), .rendered_html tbody tr:nth-child(odd) {{
  background: rgba(127, 127, 127, 0.08);
}}
/* Always-visible keyboard focus */
*:focus-visible {{ outline: 3px solid #0072B2 !important; outline-offset: 2px; }}
{contrast}
</style>
"""


def set_access(**settings):
    """Change accessibility settings and re-apply them.

        set_access(font_scale=1.4)            # bigger text
        set_access(font=None)                 # keep the theme's font
        set_access(plot_scale=1.3)            # bigger plot text and lines
        set_access(notebook_css=False)        # plots only, leave the notebook alone
        set_access(**ACCESS_DEFAULTS)         # back to the defaults

    Settings: font_scale, font, code_font, line_height, high_contrast,
    notebook_css, plot_scale, palette, colormap.
    """
    unknown = set(settings) - set(ACCESS_DEFAULTS)
    if unknown:
        raise ValueError(f"Unknown setting(s): {', '.join(sorted(unknown))}. "
                         f"Choose from: {', '.join(ACCESS_DEFAULTS)}")
    ACCESS.update(settings)
    _apply_plot_style()
    if ACCESS["notebook_css"]:
        display(HTML(_notebook_css()))


def show_plot(alt, fig=None):
    """Show the current figure with alt text for screen readers.

        plt.scatter(x, y)
        show_plot("Scatter plot of distance versus speed; points rise in a straight line.")

    The alt text is also printed in small type under the figure, so sighted
    readers see the same description.
    """
    fig = fig or plt.gcf()
    buf = io.BytesIO()
    fig.savefig(buf, format="png", bbox_inches="tight")
    plt.close(fig)
    data = base64.b64encode(buf.getvalue()).decode()
    safe = (alt.replace("&", "&amp;").replace('"', "&quot;")
               .replace("<", "&lt;").replace(">", "&gt;"))
    display(HTML(
        f'<figure style="margin:0">'
        f'<img src="data:image/png;base64,{data}" alt="{safe}" style="max-width:100%">'
        f'<figcaption style="font-size:0.85em;opacity:0.8">{safe}</figcaption></figure>'))


# ── open-ended answer checker (same as init.py) ──────────────────────────────
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


# ── apply on import ───────────────────────────────────────────────────────────
set_access()
