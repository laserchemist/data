"""
survey_helpers.py

Helper functions for visualizing class survey data using only datascience Tables.
Keep this file next to your notebook and import from it, e.g.:

    from datascience import *
    import numpy as np
    import matplotlib.pyplot as plt
    %matplotlib inline

    from survey_helpers import (
        load_survey, plot_bar_chart, plot_histogram, plot_wordcloud, auto_plot_all,
        standardize_categorical, numeric_summary
    )
"""

import numpy as np
import matplotlib.pyplot as plt
from datascience import *

try:
    from wordcloud import WordCloud
except ImportError:
    import sys
    import subprocess
    subprocess.run([sys.executable, "-m", "pip", "install", "wordcloud"], check=True)
    from wordcloud import WordCloud


def load_survey(sheet_id, gid):
    """Load a class survey Table directly from a Google Sheet's CSV export."""
    csv_url = f"https://docs.google.com/spreadsheets/d/{sheet_id}/export?format=csv&gid={gid}"
    return Table.read_table(csv_url)


def _clean_text_column(table, column):
    """Return a copy of `table` where `column` has been stripped of whitespace,
    with blank/missing responses removed."""
    cleaned_values = table.apply(lambda v: str(v).strip(), column)
    cleaned = table.with_column(column, cleaned_values)
    cleaned = cleaned.where(column, are.not_equal_to(''))
    cleaned = cleaned.where(column, are.not_equal_to('nan'))
    return cleaned


def _to_numeric(value):
    """Try to convert a single value to a float; return np.nan if it can't be converted."""
    try:
        return float(value)
    except (TypeError, ValueError):
        return np.nan


def standardize_categorical(table, column):
    """Return a copy of `table` where `column` has been stripped of extra whitespace
    and standardized to title case, so that responses like '  philadelphia' and
    'Philadelphia ' are treated as the same answer instead of two separate categories.

    This is useful before `.group(...)` on any free-response text field where people
    might type the same answer with different spacing or capitalization.
    """
    cleaned = _clean_text_column(table, column)
    standardized_values = cleaned.apply(lambda v: v.title(), column)
    return cleaned.with_column(column, standardized_values)


def plot_bar_chart(table, column, title=None, top_n=15, standardize_case=True):
    """Horizontal bar chart of response counts for a categorical column.

    table:            a datascience Table (e.g. the full survey, or a Table.where(...) subset)
    column:           the column label to summarize
    top_n:            only show the top_n most common responses (set to None to show all)
    standardize_case: if True (default), extra whitespace and inconsistent capitalization
                       are cleaned up first so e.g. 'philadelphia' and 'Philadelphia' are
                       counted as the same response
    """
    cleaned = standardize_categorical(table, column) if standardize_case else _clean_text_column(table, column)
    if cleaned.num_rows == 0:
        print(f"No responses for '{column}'")
        return

    counts = cleaned.group(column).sort('count', descending=True)
    if top_n:
        counts = counts.take(np.arange(min(top_n, counts.num_rows)))
    # Sort ascending so the largest bar ends up at the top of the horizontal chart
    counts = counts.sort('count', descending=False)

    counts.barh(column)
    plt.title(title or column)
    plt.xlabel('Number of responses')
    plt.tight_layout()
    plt.show()


def plot_histogram(table, column, title=None, bins=10):
    """Histogram for a numeric column.

    table:  a datascience Table (e.g. the full survey, or a Table.where(...) subset)
    column: the column label to summarize (values are coerced to numbers)
    bins:   number of bins, or an array of bin edges
    """
    numeric_values = table.apply(_to_numeric, column)
    numeric_values = numeric_values[~np.isnan(numeric_values)]
    if len(numeric_values) == 0:
        print(f"No numeric responses for '{column}'")
        return

    numeric_table = Table().with_column(column, numeric_values)
    numeric_table.hist(column, bins=bins, unit='response')
    plt.title(title or column)
    plt.tight_layout()
    plt.show()


def numeric_summary(table, column):
    """Return a Table of descriptive statistics (count, mean, median, standard
    deviation, min, max) for a numeric column.

    table:  a datascience Table (e.g. the full survey, or a Table.where(...) subset)
    column: the column label to summarize (values are coerced to numbers)
    """
    numeric_values = table.apply(_to_numeric, column)
    numeric_values = numeric_values[~np.isnan(numeric_values)]
    if len(numeric_values) == 0:
        print(f"No numeric responses for '{column}'")
        return None

    return Table().with_columns(
        'Statistic', ['Count', 'Mean', 'Median', 'Standard Deviation', 'Min', 'Max'],
        'Value', [
            len(numeric_values),
            round(np.mean(numeric_values), 2),
            np.median(numeric_values),
            round(np.std(numeric_values), 2),
            np.min(numeric_values),
            np.max(numeric_values),
        ]
    )


def plot_wordcloud(table, column, title=None, extra_stopwords=None):
    """Word cloud for a free-text column.

    table:            a datascience Table (e.g. the full survey, or a Table.where(...) subset)
    column:           the column label to summarize
    extra_stopwords:  optional iterable of extra words to exclude (e.g. the question's own wording)
    """
    cleaned = _clean_text_column(table, column)
    if cleaned.num_rows == 0:
        print(f"No responses for '{column}'")
        return

    text = ' '.join(cleaned.column(column))
    stopwords = set(WordCloud().stopwords)
    if extra_stopwords:
        stopwords |= set(extra_stopwords)

    wc = WordCloud(width=900, height=450, background_color='white',
                    stopwords=stopwords, collocations=False).generate(text)

    plt.figure(figsize=(10, 5))
    plt.imshow(wc, interpolation='bilinear')
    plt.axis('off')
    plt.title(title or column, fontsize=14)
    plt.tight_layout()
    plt.show()


def auto_plot_all(table, skip_columns=('Timestamp',), unique_ratio_threshold=0.5):
    """Loop over every column in `table` and plot it with a chart type chosen automatically:

    - Mostly-numeric columns with few unique values -> histogram
    - Text columns with few unique values relative to responses -> bar chart
    - Everything else (long, varied free text) -> word cloud

    table:        a datascience Table (e.g. the full survey, or a Table.where(...) subset)
    skip_columns: column labels to skip entirely (e.g. 'Timestamp')
    """
    for column in table.labels:
        if column in skip_columns:
            continue

        cleaned = _clean_text_column(table, column)
        if cleaned.num_rows == 0:
            continue

        values = cleaned.column(column)
        numeric_values = np.array([_to_numeric(v) for v in values])
        frac_numeric = np.mean(~np.isnan(numeric_values))
        num_unique = len(np.unique(values))
        unique_ratio = num_unique / len(values)

        if frac_numeric > 0.9 and num_unique <= 15:
            plot_histogram(table, column, bins=min(10, num_unique))
        elif unique_ratio <= unique_ratio_threshold:
            plot_bar_chart(table, column, standardize_case=True)
        else:
            plot_wordcloud(table, column)
