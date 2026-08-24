"""
dashboard_helpers.py
====================
Backend for instructor_dashboard.ipynb.
Place in course root alongside lab_submit.py.

All data loading, chart building, and export logic lives here.
The notebook stays clean — just configuration and widget calls.
"""

import json, os, warnings
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
import matplotlib.ticker as ticker
import matplotlib.dates as mdates
import ipywidgets as widgets
from IPython.display import display, clear_output

# Suppress emoji/glyph font warnings
warnings.filterwarnings("ignore", message="Glyph.*missing from.*font")

# ── configuration (set in notebook, overrides these defaults) ─────────────────
SHEET_ID   = "1JTlIyJCAGE7obspq04ERJkQHOku_d8jZn1sxmIedWJU"
CREDS_PATH = "/home/jovyan/shared/nordic-knowledge-6598a7fdb7c8.json"
LOCAL_JSON = os.path.expanduser("~/shared-public/submissions.json")

# ── colours ────────────────────────────────────────────────────────────────────
BLUE   = "#5DABB5"
RED    = "#E05C5C"
CHERRY = "#9B2335"
NAVY   = "#1a3a5c"
GREEN  = "#1a6e2e"

# ══════════════════════════════════════════════════════════════════════════════
#  DATA LOADING
# ══════════════════════════════════════════════════════════════════════════════

def load_all(sheet_id=None, creds_path=None, local_json=None):
    """
    Load submissions from Google Sheets and/or local JSON.
    Returns a tuple (df_all, df_latest, messages).
    df_latest = one row per student+lab (most recent submission).
    """
    sheet_id   = sheet_id   or SHEET_ID
    creds_path = creds_path or CREDS_PATH
    local_json = local_json or LOCAL_JSON

    records  = []
    messages = []

    # Google Sheets — primary
    try:
        import gspread
        gc   = gspread.service_account(filename=creds_path)
        ws   = gc.open_by_key(sheet_id).sheet1
        rows = ws.get_all_records()
        records.extend(rows)
        messages.append(f"✅ Google Sheets: {len(rows)} record(s)")
    except FileNotFoundError:
        messages.append(f"❌ Credentials not found: {creds_path}")
    except Exception as e:
        messages.append(f"❌ Google Sheets: {e}")

    # Local JSON fallback
    if os.path.exists(local_json):
        try:
            with open(local_json) as f:
                data = json.load(f)
            local_records = data if isinstance(data, list) else [data]
            records.extend(local_records)
            messages.append(f"✅ Local JSON: {len(local_records)} record(s)")
        except Exception as e:
            messages.append(f"❌ Local JSON: {e}")
    else:
        messages.append(f"–  Local JSON not found: {local_json}")

    if not records:
        return pd.DataFrame(), pd.DataFrame(), messages

    df = pd.json_normalize(records).drop_duplicates()

    # Coerce types
    if "score_pct" in df.columns:
        df["score_pct"] = pd.to_numeric(df["score_pct"], errors="coerce").fillna(0)
    if "timestamp" in df.columns:
        df["timestamp_dt"] = pd.to_datetime(df["timestamp"], errors="coerce")

    df_latest = (df.sort_values("timestamp")
                   .drop_duplicates(subset=["user","lab"], keep="last")
                   .reset_index(drop=True))

    messages.append(f"\n{len(df)} total submission(s) | "
                    f"{len(df_latest)} unique student-lab pair(s)")
    messages.append(f"Labs: {sorted(df['lab'].unique().tolist())}")
    messages.append(f"Students: {df['user'].nunique()}")

    # ── auto-export to CSV on every load ─────────────────────────────────────
    if not df_latest.empty:
        try:
            csv_path = os.path.join(os.getcwd(), "submissions_all.csv")
            df_latest.to_csv(csv_path, index=False)
            messages.append(f"✅ submissions_all.csv updated ({len(df_latest)} rows)")
        except Exception as e:
            messages.append(f"⚠️  Could not write submissions_all.csv: {e}")

    return df, df_latest, messages


# ══════════════════════════════════════════════════════════════════════════════
#  CHARTS
# ══════════════════════════════════════════════════════════════════════════════

def _score_histogram(ax, scores, title="Score distribution"):
    bins = [0,10,20,30,40,50,60,70,80,90,100.1]
    ax.hist(scores, bins=bins, color=BLUE, edgecolor="white", linewidth=0.8)
    ax.axvline(80, color=RED, linestyle="--", linewidth=1.2, label="80% pass")
    ax.set_xlabel("Score (%)")
    ax.set_ylabel("Students")
    ax.set_title(title)
    ax.set_xlim(0, 100)
    ax.xaxis.set_major_locator(ticker.MultipleLocator(20))
    ax.legend(fontsize=8)


def _score_bars(ax, filt, title="Score per student"):
    by_s   = filt.sort_values("score_pct", ascending=True)
    colors = [BLUE if s >= 80 else RED for s in by_s["score_pct"].astype(float)]
    bars   = ax.barh(range(len(by_s)), by_s["score_pct"].astype(float),
                     color=colors, edgecolor="white", height=0.7)
    ax.set_yticks(range(len(by_s)))
    ax.set_yticklabels([str(n)[:18] for n in by_s["name"]], fontsize=8)
    ax.axvline(80, color=RED, linestyle="--", linewidth=1.0)
    ax.set_xlim(0, 110)
    ax.set_xlabel("Score (%)")
    ax.set_title(title)
    for i, (_, val) in enumerate(zip(bars, by_s["score_pct"].astype(float))):
        ax.text(val + 1, i, f"{val:.0f}%", va="center", fontsize=7)


def _summary_panel(ax, filt):
    ax.axis("off")
    scores = filt["score_pct"].astype(float)
    n_pass = (scores >= 80).sum()
    stats  = [
        ("Submissions",      len(filt)),
        ("Mean score",       f"{scores.mean():.1f}%"),
        ("Median score",     f"{scores.median():.1f}%"),
        ("Highest",          f"{scores.max():.1f}%"),
        ("Lowest",           f"{scores.min():.1f}%"),
        ("Pass (>=80%)",     f"{n_pass} / {len(filt)}"),
        ("Review (<80%)",    f"{len(filt)-n_pass} / {len(filt)}"),
    ]
    y = 0.95
    for label, val in stats:
        color = GREEN if "Pass" in label else (RED if "Review" in label else "#222")
        ax.text(0.05, y, label, transform=ax.transAxes, fontsize=10, color="#555")
        ax.text(0.62, y, str(val), transform=ax.transAxes,
                fontsize=10, fontweight="bold", color=color)
        y -= 0.13
    ax.set_title("Summary")


def _submission_trend(ax, df_all, lab):
    """Line chart of cumulative submissions over time."""
    src = df_all if lab == "All" else df_all[df_all["lab"] == lab]
    if "timestamp_dt" not in src.columns or src["timestamp_dt"].isna().all():
        ax.axis("off")
        ax.text(0.5, 0.5, "No timestamp data", ha="center", va="center",
                transform=ax.transAxes, color="#888")
        return

    ts = src["timestamp_dt"].dropna().sort_values()
    cumulative = range(1, len(ts) + 1)
    ax.plot(ts, cumulative, color=CHERRY, linewidth=2, marker="o",
            markersize=4, markerfacecolor="white", markeredgecolor=CHERRY)
    ax.set_xlabel("Date")
    ax.set_ylabel("Cumulative submissions")
    ax.set_title("Submission trend")
    ax.xaxis.set_major_formatter(mdates.DateFormatter("%b %d"))
    ax.xaxis.set_major_locator(mdates.AutoDateLocator())
    plt.setp(ax.xaxis.get_majorticklabels(), rotation=30, ha="right", fontsize=7)
    ax.yaxis.set_major_locator(ticker.MaxNLocator(integer=True))


def _recent_submissions(ax, df_all, n=8):
    """Table of the N most recent submissions."""
    ax.axis("off")
    recent = (df_all.sort_values("timestamp", ascending=False)
                    .head(n)
                    .reset_index(drop=True))
    if recent.empty:
        ax.text(0.5, 0.5, "No submissions", ha="center", va="center",
                transform=ax.transAxes)
        return

    cols   = ["name", "lab", "score_pct", "timestamp"]
    cols   = [c for c in cols if c in recent.columns]
    data   = [[str(recent.loc[i, c])[:22] for c in cols] for i in range(len(recent))]
    table  = ax.table(
        cellText  = data,
        colLabels = [c.replace("_pct","(%)").replace("_"," ").title() for c in cols],
        cellLoc   = "left",
        loc       = "center",
        bbox      = [0, 0, 1, 1],
    )
    table.auto_set_font_size(False)
    table.set_fontsize(8)
    for (row, col), cell in table.get_celld().items():
        cell.set_edgecolor("#ddd")
        if row == 0:
            cell.set_facecolor(CHERRY)
            cell.set_text_props(color="white", fontweight="bold")
        elif row % 2 == 0:
            cell.set_facecolor("#f9f9f9")
    ax.set_title(f"Last {n} submissions", pad=12)


# ══════════════════════════════════════════════════════════════════════════════
#  MAIN DASHBOARD
# ══════════════════════════════════════════════════════════════════════════════

def make_dashboard(df_all, df_latest, lab_value, view_value):
    """Render the full dashboard for the selected lab/view."""
    with warnings.catch_warnings():
        warnings.simplefilter("ignore")

        src  = df_latest if view_value == "Latest only" else df_all
        filt = src if lab_value == "All" else src[src["lab"] == lab_value]

        if filt.empty:
            print("No submissions for this selection.")
            return

        # Row 1: histogram | per-student bars | summary
        fig, axes = plt.subplots(1, 3, figsize=(16, 4))
        fig.suptitle(f"{lab_value}  —  {len(filt)} submission(s)",
                     fontsize=13, y=1.01, color=NAVY, fontweight="bold")

        _score_histogram(axes[0], filt["score_pct"].astype(float))
        _score_bars(axes[1], filt)
        _summary_panel(axes[2], filt)

        plt.tight_layout()
        plt.show()

        # Row 2: trend | recent submissions
        fig2, axes2 = plt.subplots(1, 2, figsize=(16, 3.5))
        _submission_trend(axes2[0], df_all, lab_value)
        _recent_submissions(axes2[1], df_all)
        plt.tight_layout()
        plt.show()

        # Submission table
        show_cols = [c for c in
            ["name","user","lab","timestamp","score_pct","correct","total"]
            if c in filt.columns]
        print()
        display(filt[show_cols]
                .sort_values("score_pct", ascending=False)
                .reset_index(drop=True))

        # Open-ended answers
        ans_cols = [c for c in filt.columns
                    if c.startswith("answers.") or
                       (c.startswith("open") and not c.endswith("_label"))]
        if ans_cols:
            print(f"\n{'─'*60}")
            print("Open-ended responses:")
            for _, row in filt.iterrows():
                print(f"\n── {row.get('name','')}  ({row.get('user','')}) ──")
                for col in ans_cols:
                    val = str(row.get(col,"")).strip()
                    if val and val.lower() not in ("nan","answer",""):
                        q = (col.replace("answers.","")
                                .replace("open","Q").replace("_"," "))
                        print(f"  {q}:\n    {val[:300]}")


# ══════════════════════════════════════════════════════════════════════════════
#  EXPORT
# ══════════════════════════════════════════════════════════════════════════════

def export(df_latest, lab="all"):
    """
    Export latest submissions to CSV.
    Usage: export(df_latest, 'Lab04')  or  export(df_latest)
    """
    if df_latest.empty:
        print("No data loaded.")
        return
    src   = df_latest if lab == "all" else df_latest[df_latest["lab"] == lab]
    fname = f"submissions_{lab}.csv"
    src.to_csv(fname, index=False)
    print(f"Saved {len(src)} rows -> {fname}")
