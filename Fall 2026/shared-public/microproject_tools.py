"""
microproject_tools.py  —  Regression Microprojects (Elements of Data Science)

Lives in the course repo at 'Fall 2026/shared-public/' next to init.py (delivered by nbgitpuller).

Students use:
    my_project(name)                      -> shows which microproject they were assigned
    submit_plot(fig, name, 'MP1', r=..., slope=..., intercept=..., caption='...')

The instructor notebook writes the assignments and reads the submissions.
Everything lives under MICRO_ROOT (override with the MICRO_ROOT environment variable for testing).
"""
import os, csv, json, re, datetime, hashlib

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


def user_key(username):
    """Scrambled stand-in for a hub login, so IDs never appear in the shared assignments file.
    The same login always gives the same key."""
    username = str(username).strip().lower()
    if not username:
        return ''
    return hashlib.sha256(('eds-microprojects:' + username).encode()).hexdigest()[:12]


def _current_user_key():
    return user_key(os.environ.get('JUPYTERHUB_USER', ''))


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


# ----------------------------------------------------------------------------- rosters
_NAME_HEADERS  = ['student', 'name', 'student name', 'full name', 'sortable name', 'student_name']
_FIRST_HEADERS = ['first name', 'first_name', 'first', 'given name', 'preferred name']
_LAST_HEADERS  = ['last name', 'last_name', 'last', 'surname', 'family name']
_LOGIN_HEADERS = ['sis login id', 'login id', 'login', 'username', 'user name', 'user', 'netid',
                  'accessnet', 'accessnet id', 'tuid login', 'email']
_SECTION_HEADERS = ['section', 'sections', 'section number', 'class section']
_LOGIN_RE = re.compile(r'^[a-z][a-z0-9._-]{2,}(@[a-z0-9.-]+)?$')


def _find(headers, wanted):
    for w in wanted:
        if w in headers:
            return headers.index(w)
    return None


def _is_login_column(values):
    vals = [v.strip().lower() for v in values if v.strip()]
    return bool(vals) and sum(bool(_LOGIN_RE.match(v)) for v in vals) >= 0.9 * len(vals)


def _split_name(full):
    "'Last, First Middle' or 'First Middle Last'  ->  (first, last)"
    full = ' '.join(str(full).split())
    if ',' in full:
        last, first = full.split(',', 1)
    else:
        parts = full.split(' ')
        first, last = parts[0], (parts[-1] if len(parts) > 1 else '')
    first = first.strip().split(' ')[0] if first.strip() else ''
    return first, last.strip()


def read_roster(path, section=None):
    """Read a class roster in whatever layout it was exported in.

    Handles: a registrar export with no header ("Last, First", login, section, ...),
    a Canvas gradebook export (Student, ID, SIS User ID, SIS Login ID, Section, ...),
    and simple tables with first/last name columns. Returns a list of dicts with
    first, last, login, section. The section label is the number in the file name
    (class_08.csv -> '08'), else the file's section column, unless given explicitly."""
    with open(path, newline='', encoding='utf-8-sig') as f:
        rows = [[c.strip() for c in r] for r in csv.reader(f)]
    rows = [r for r in rows if any(r)]
    if not rows:
        raise ValueError(f'{path} is empty')

    header = [c.lower() for c in rows[0]]
    has_header = (_find(header, _NAME_HEADERS + _FIRST_HEADERS) is not None
                  and not any(_LOGIN_RE.match(c) and re.search(r'\d', c) for c in header))
    body = rows[1:] if has_header else rows
    # Canvas puts a "Points Possible" row (and sometimes a test student) under the header
    body = [r for r in body if 'points possible' not in ' '.join(r).lower()
            and not r[0].lower().startswith(('student, test', 'test student'))]
    width = max(len(r) for r in body)
    body = [r + [''] * (width - len(r)) for r in body]
    columns = [[r[j] for r in body] for j in range(width)]

    if has_header:
        name_col, first_col = _find(header, _NAME_HEADERS), _find(header, _FIRST_HEADERS)
        last_col = _find(header, _LAST_HEADERS)
        login_col, sec_col = _find(header, _LOGIN_HEADERS), _find(header, _SECTION_HEADERS)
    else:
        name_col = next(j for j in range(width) if any(re.search(r'[A-Za-z]', v) for v in columns[j]))
        first_col = last_col = sec_col = None
        others = [j for j in range(width) if j != name_col]
        login_col = next((j for j in others if _is_login_column(columns[j])), None)
        sec_col = next((j for j in others if j != login_col and columns[j][0]
                        and all(re.fullmatch(r'\d{1,4}', v) for v in columns[j] if v)), None)

    if section is None:                      # prefer the number in the file name: class_08.csv -> '08'
        digits = re.findall(r'\d+', os.path.basename(path))
        if digits:
            section = digits[-1]
        elif sec_col is None:
            section = os.path.splitext(os.path.basename(path))[0]

    roster = []
    for r in body:
        if first_col is not None:
            first = r[first_col].split(' ')[0] if r[first_col] else ''
            last = r[last_col] if last_col is not None else ''
            if not first and name_col is not None:
                first, last = _split_name(r[name_col])
        else:
            first, last = _split_name(r[name_col])
        if not first:
            continue
        login = r[login_col].split('@')[0].lower() if login_col is not None else ''
        sec = section if section is not None else (r[sec_col] or '?')
        roster.append({'first': first, 'last': last, 'login': login, 'section': str(sec)})
    return roster


def _read_assignments():
    if not os.path.exists(ASSIGN_FILE):
        return []
    with open(ASSIGN_FILE, newline='') as f:
        return list(csv.DictReader(f))


def my_project(name):
    "Look up and print this student's microproject. Returns the project id (e.g. 'MP3') or None."
    first, last_initial = _name_parts(name)
    assignments = _read_assignments()
    # 1) Match on the hub login (most reliable)
    me = _current_user_key()
    rows = [r for r in assignments if me and r.get('user_key') == me]
    if rows:
        return _announce(rows[0])
    # 2) Fall back to the name the student typed
    rows = [r for r in assignments if _clean(r['first_name']) == _clean(first)]
    if len(rows) > 1 and last_initial:
        narrowed = [r for r in rows if _clean(r.get('last_initial', ''))[:1] == _clean(last_initial)]
        rows = narrowed or rows
    if len(rows) == 0:
        print(f"No assignment found for '{first}'. Check the spelling of your name, or ask your instructor.")
        return None
    if len(rows) > 1:
        print(f"More than one student named '{first}'. Use your full name, e.g. name = '{first} Smith'.")
        return None
    return _announce(rows[0])


def _announce(row):
    pid = row['project']
    title, notebook = PROJECTS[pid]
    print(f"Hi {row['display_name']}! You are assigned to {pid}: {title}")
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
    me = _current_user_key()
    mine = [a for a in _read_assignments() if me and a.get('user_key') == me]
    section = ''
    if mine:                                   # use the roster's name and section when the login matches
        first, last_initial = mine[0]['first_name'], mine[0]['last_initial']
        section = mine[0].get('section', '')
    # Section and a short login key keep file names unique across all classes
    stem = f"{project}_{section + '_' if section else ''}{_clean(first).capitalize()}{last_initial.upper()}"
    if me:
        stem += '_' + me[:4]
    record = {'name': str(name).strip(), 'first_name': first, 'project': project,
              'user_key': _current_user_key(), 'section': section,
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
