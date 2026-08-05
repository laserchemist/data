"""
eds_mod.py
==========
Small collection of course helper functions, shared by every lab.
Lives in shared-public/, one directory above lab00/, lab01/, lab04/, etc.

Currently provides:
    ptrend(table, date_col, value_col, scale=1)

── IMPORTANT NOTE FOR THE INSTRUCTOR ─────────────────────────────────────────
Lab 04 (and the original course materials) reference a `ptrend()` function
from "the EDS module" (`from EDS_mod.EDS_mod import *`), but that module's
source was not part of what was uploaded when this course was restructured.

The implementation below was reconstructed from the date-axis-formatting
code pattern you shared (matplotlib.dates.AutoDateLocator/AutoDateFormatter
applied to a Table's date column), matched against how `ptrend()` is called
in Lab 04:
    ptrend(Nobel, "Week", "Nobel Prize: (United States)")
    ptrend(COVID, "date", "deaths_avg", 7)   # optional scale factor

If your actual EDS_mod.ptrend() behaves differently (different smoothing,
different default styling, additional parameters), replace this function
with your original — everything downstream just calls `ptrend(...)` and
doesn't care where it comes from.
"""

import matplotlib.pyplot as plt
import matplotlib.dates as mdates


def ptrend(table, date_col, value_col, scale=1, **plot_kwargs):
    """
    Plot a time trend from a datascience Table with a nicely auto-formatted
    date axis (short for "plot trend").

    Parameters
    ----------
    table : datascience.Table
        Table containing a date column and a numeric column to plot.
    date_col : str
        Name of the column holding dates (parsed as datetime64).
    value_col : str
        Name of the numeric column to plot on the y-axis.
    scale : float, optional
        Multiplies every y-value before plotting — handy for matching the
        amplitude of a weekly-aggregated series to a daily one (e.g. `* 7`).
    **plot_kwargs :
        Passed through to `plt.plot()` (color, linestyle, etc.).

    Returns
    -------
    bool
        True if the plot was drawn successfully (used by some `check()`
        cells as a simple "did this run" signal).
    """
    dates = table.column(date_col).astype("datetime64[s]")
    values = table.column(value_col) * scale

    loc = mdates.AutoDateLocator()
    fmt = mdates.AutoDateFormatter(loc)
    ax = plt.gca()
    ax.xaxis.set_major_locator(loc)
    ax.xaxis.set_major_formatter(fmt)

    plot_kwargs.setdefault("label", value_col)
    plt.plot(dates, values, **plot_kwargs)
    plt.gcf().autofmt_xdate()
    plt.legend()

    return True
