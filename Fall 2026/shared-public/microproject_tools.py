"""
microproject_tools.py  —  Regression Microprojects (Elements of Data Science)

Copy this file into /home/jovyan/shared-public/ next to init.py.

Students use:
    my_project(name)                      -> shows which microproject they were assigned
    submit_plot(fig, name, 'MP1', r=..., slope=..., intercept=..., caption='...')

The instructor notebook writes the assignments and reads the submissions.
Everything lives under MICRO_ROOT (override with the MICRO_ROOT environment variable for testing).
"""
import os, csv, json, re, datetime

MICRO_ROOT = os.environ.get('MICRO_ROOT', '/home/jovyan/shared-public/microprojects')
SUBMIT_DIR = os.path.join(MICRO_ROOT, 'submissions')
ASSIGN_FILE = os.path.join(MICRO_ROOT, 'assignments.csv')

PROJECTS = {
    'MP1': ('Carbon Dioxide at Mauna Loa', 'mp1_co2_mauna_loa.ipynb'),
    'MP2': ("Galton's Heights",            'mp2_galton_heights.ipynb'),
    'MP3': ('Birth Weight and Gestation',  'mp3_births.ipynb'),
    'MP4': ('Palmer Penguins',             'mp4_penguins.ipynb'),
    'MP5': ('Periodic Trends',             'mp5_periodic_trends.ipynb'),
}


def _clean(text):
    "Lower-case letters only, for matching names."
    return re.sub(r'[^a-z]', '', str(text).lower())


def _name_parts(name):
    parts = str(name).strip().split()
    if not parts or parts[0] == 'Ellipsis':
        raise ValueError("Set your name first, e.g.  name = 'Ada Lovelace'")
    first = parts[0]
    last_initial = parts[-1][0] if len(parts) > 1 else ''
    return first, last_initial


def _read_assignments():
    if not os.path.exists(ASSIGN_FILE):
        return []
    with open(ASSIGN_FILE, newline='') as f:
        return list(csv.DictReader(f))


def my_project(name):
    "Look up and print this student's microproject. Returns the project id (e.g. 'MP3') or None."
    first, last_initial = _name_parts(name)
    rows = [r for r in _read_assignments() if _clean(r['first_name']) == _clean(first)]
    if len(rows) > 1 and last_initial:
        narrowed = [r for r in rows if _clean(r.get('last_initial', ''))[:1] == _clean(last_initial)]
        rows = narrowed or rows
    if len(rows) == 0:
        print(f"No assignment found for '{first}'. Check the spelling of your name, or ask your instructor.")
        return None
    if len(rows) > 1:
        print(f"More than one student named '{first}'. Use your full name, e.g. name = '{first} Smith'.")
        return None
    pid = rows[0]['project']
    title, notebook = PROJECTS[pid]
    print(f"Hi {rows[0]['display_name']}! You are assigned to {pid}: {title}")
    print(f"Your notebook: {notebook}")
    return pid


def _check_figure(fig):
    "Return a list of warnings about missing pieces of the final figure."
    warnings = []
    if not fig.axes:
        return ['The figure is empty — make your plot after fig = plt.figure(...).']
    ax = fig.axes[0]
    if not ax.get_xlabel():
        warnings.append('Add a horizontal axis label with units (plt.xlabel).')
    if not ax.get_ylabel():
        warnings.append('Add a vertical axis label with units (plt.ylabel).')
    if not ax.get_title():
        warnings.append('Add a title (plt.title).')
    if not ax.collections:
        warnings.append('No scatter points found (plt.scatter).')
    if not ax.lines:
        warnings.append('No regression line found (plt.plot).')
    if ax.get_legend() is None:
        warnings.append('Add a legend (plt.legend) showing your line equation and r.')
    return warnings


def submit_plot(fig, name, project, r, slope, intercept, caption=''):
    """Save your final figure (and its numbers) to the shared class gallery.
    Re-submitting replaces your earlier submission."""
    first, last_initial = _name_parts(name)
    project = str(project).upper()
    if project not in PROJECTS and project != 'DEMO':        # 'DEMO' = instructor demonstration
        raise ValueError(f"project must be one of {list(PROJECTS)}")
    for label, value in [('r', r), ('slope', slope), ('intercept', intercept)]:
        if value is Ellipsis:
            raise ValueError(f"Fill in {label} before submitting.")

    problems = _check_figure(fig)
    stem = f"{project}_{_clean(first).capitalize()}{last_initial.upper()}"
    record = {'name': str(name).strip(), 'first_name': first, 'project': project,
              'r': round(float(r), 4), 'slope': float(slope), 'intercept': float(intercept),
              'caption': str(caption).strip(),
              'submitted': datetime.datetime.now().isoformat(timespec='seconds'),
              'figure_warnings': problems}

    try:
        os.makedirs(SUBMIT_DIR, exist_ok=True)
        folder = SUBMIT_DIR
    except PermissionError:
        folder = os.getcwd()
    png_path = os.path.join(folder, stem + '.png')
    try:
        fig.savefig(png_path, dpi=120, bbox_inches='tight')
        with open(os.path.join(folder, stem + '.json'), 'w') as f:
            json.dump(record, f, indent=1)
    except PermissionError:
        folder = os.getcwd()
        png_path = os.path.join(folder, stem + '.png')
        fig.savefig(png_path, dpi=120, bbox_inches='tight')
        with open(os.path.join(folder, stem + '.json'), 'w') as f:
            json.dump(record, f, indent=1)

    if folder == SUBMIT_DIR:
        print(f'✅ Submitted! Your plot is in the class gallery as {stem}.png')
    else:
        print(f'⚠️ Could not write to the shared folder. Saved {stem}.png here instead — tell your instructor.')
    if not record['caption']:
        print('   Tip: add a one-sentence caption describing your finding, then submit again.')
    for p in problems:
        print('   Tip:', p)
    return None
