"""
microproject_instructor.py — instructor tools for the Regression Microprojects.

Lives in 'Fall 2026/shared-public/' next to microproject_tools.py. The instructor notebook
calls these functions, one per cell. Every function rereads the saved files, so cells can be
run in any order, any number of times.

    setup()                       folders + a status summary
    assign()                      read class_*.csv rosters, keep saved groups, deal new students
    show_groups('03')             glossy group boards ('all' for every class)
    draw('03')                    live, dramatic reveal of one class's groups
    fix_groups('01')              drag-and-drop correction of one class's groups
    who_submitted('03')           submission status, and any figures not linked to a student
    gallery('03')                 figures + reflections, also saved as a web page
    slideshow('03')               stand-alone results slide show
    add_submission(...)           put a student's figure in the gallery by hand
    compare_lines('03')           did everyone on a project get the same line?
    export_canvas('03')           Canvas gradebook CSV, with partial credit
    link_submissions('01')        drag-and-drop: attach or discard unlinked figures and reflections

Wherever a function takes a class: '03', 3 and '3' all mean class 03; 'all' means every class.
"""
import os, glob, json, csv, re, html, base64, shutil, datetime, time, uuid
from collections import Counter

import numpy as np
from datascience import Table, make_array, are
from IPython.display import display, HTML

from microproject_tools import MICRO_ROOT, SUBMIT_DIR, ASSIGN_FILE, PROJECTS, user_key

REFLECT_DIR = os.path.join(MICRO_ROOT, 'reflections')
BACKUP_DIR = os.path.join(MICRO_ROOT, 'backups')
COLUMNS = ['section', 'display_name', 'first_name', 'last_initial', 'user_key', 'project']

PIDS = list(PROJECTS)
TITLES = {pid: PROJECTS[pid][0] for pid in PIDS}
TITLES['DEMO'] = 'Instructor demo'
EMOJI = {'MP1': '🌍', 'MP2': '📏', 'MP3': '👶', 'MP4': '🐧', 'MP5': '⚛️', 'DEMO': '🚗'}
PROJECT_INFO = {
    'MP1': ('How fast is CO₂ rising — and is it speeding up?',
            'r = 0.99, yet the errors curve: the rise is now 2.3× faster than in the 1960s.'),
    'MP2': ('Do tall parents have tall children?',
            'Where “regression” got its name: children of extreme parents are closer to average.'),
    'MP3': ('How much does each extra day of pregnancy add?',
            'At the same gestation, babies of smokers are lighter. Cause, or association?'),
    'MP4': ('Can flipper length predict body mass?',
            'r = 0.87 for all penguins, but much weaker within each species.'),
    'MP5': ('Does electronegativity track ionization energy?',
            'A strong r, but both share one cause: the pull of the nucleus.'),
}


# ============================================================================ small helpers
def _section(which):
    "'03', 3, '3' -> '03';  'all' or None -> None."
    if which is None or str(which).strip().lower() in ('all', '', 'none'):
        return None
    text = str(which).strip()
    return text.zfill(2) if text.isdigit() else text


def _plural(n, word):
    return f'{n} {word}{"" if n == 1 else "s"}'


def _esc(text):
    return html.escape(str(text))


def _img64(path):
    with open(path, 'rb') as f:
        return base64.b64encode(f.read()).decode()


def _empty_assignments():
    return Table().with_columns(*sum([[c, make_array()] for c in COLUMNS], []))


def load_assignments():
    "The saved groups as a Table (empty if none are saved yet)."
    if not os.path.exists(ASSIGN_FILE):
        return _empty_assignments()
    t = Table.read_table(ASSIGN_FILE, dtype=str, keep_default_na=False)
    if not all(c in t.labels for c in COLUMNS):
        return _empty_assignments()
    return t.select(COLUMNS)


def _save_assignments(t):
    "Back up the current file, then save. Keeps the 30 newest backups."
    if os.path.exists(ASSIGN_FILE):
        os.makedirs(BACKUP_DIR, exist_ok=True)
        stamp = datetime.datetime.now().strftime('%Y%m%d-%H%M%S-%f')
        shutil.copy(ASSIGN_FILE, os.path.join(BACKUP_DIR, f'assignments_{stamp}.csv'))
        for old in sorted(glob.glob(os.path.join(BACKUP_DIR, 'assignments_*.csv')))[:-30]:
            os.remove(old)
    t.select(COLUMNS).to_csv(ASSIGN_FILE)
    try:
        os.chmod(ASSIGN_FILE, 0o644)
    except PermissionError:
        pass


def _classes(t):
    return list(np.unique(t.column('section'))) if t.num_rows else []


def _check_class(t, sec):
    "Return True if the class exists; otherwise say which classes do."
    if sec in _classes(t):
        return True
    print(f'No saved groups for class {sec!r}. Saved classes: {", ".join(_classes(t)) or "none — run assign() first"}')
    return False


def _labels(t):
    "user_key -> 'First L. · 03' from the saved groups."
    out = {}
    for key, first, initial, sec in zip(t.column('user_key'), t.column('first_name'),
                                        t.column('last_initial'), t.column('section')):
        out[key] = f'{first} {initial}. · {sec}' if initial else f'{first} · {sec}'
    return out


def _label(labels, key, typed_name, sec):
    "Roster label for this login; otherwise built from the name the student typed."
    if key in labels:
        return labels[key]
    parts = str(typed_name).split()
    first = parts[0] if parts else '?'
    initial = f' {parts[-1][0].upper()}.' if len(parts) > 1 else ''
    return f'{first}{initial}' + (f' · {sec}' if sec else '')


def _link(record, t, by_name, known):
    "Link one submission/reflection record to a roster student: by login, else by typed name."
    key, sec = record.get('user_key', ''), str(record.get('section', '') or '')
    if key in known:
        if not sec:
            sec = t.where('user_key', key).column('section').item(0)
        return key, sec, ('linked by you' if record.get('linked_by_instructor') else 'login')
    if str(record.get('project', '')).upper() == 'DEMO':
        return key, sec, 'demo'
    words = str(record.get('name', '')).replace('.', ' ').split()
    first = words[0].lower() if words else ''
    hits = {}
    for w in words[1:]:                                # 'Isabelle Van Wert' tries V and W
        for k, s_ in by_name.get((first, w[0].lower()), []):
            hits[k] = s_
    if not hits:                                       # no last name typed: a first name unique across classes
        only = by_name.get((first, ''), [])
        if len(only) == 1:
            hits = {only[0][0]: only[0][1]}
        elif len(only) > 1:
            return key, sec, 'ambiguous name'
    if len(hits) == 1:
        k, s_ = next(iter(hits.items()))
        return k, s_, 'name'
    return key, sec, ('ambiguous name' if hits else 'unmatched')


def _name_index(t):
    by_name = {}
    for key, first, initial, sec in zip(t.column('user_key'), t.column('first_name'),
                                        t.column('last_initial'), t.column('section')):
        by_name.setdefault((first.lower(), initial.lower()), []).append((key, sec))
        by_name.setdefault((first.lower(), ''), []).append((key, sec))
    return by_name, set(t.column('user_key'))


# ============================================================================ reading files
def load_submissions(t=None):
    "Every submitted figure as a Table, linked to the roster (early submissions are linked by name)."
    t = load_assignments() if t is None else t
    by_name, known = _name_index(t)
    rows = []
    for p in sorted(glob.glob(os.path.join(SUBMIT_DIR, '*.json'))):
        try:
            r = json.load(open(p))
        except ValueError:
            print('⚠️ Could not read', os.path.basename(p))
            continue
        png = p[:-5] + '.png'
        if not os.path.exists(png):
            print('⚠️ Missing image for', os.path.basename(p))
            continue
        key, sec, how = _link(r, t, by_name, known)
        rows.append([r.get('project', ''), sec, r.get('name', ''), key, how, r.get('r', np.nan),
                     r.get('slope', np.nan), r.get('intercept', np.nan), r.get('caption', ''),
                     r.get('submitted', ''), os.path.basename(p[:-5]), png,
                     ' | '.join(r.get('figure_warnings', []) or [])])
    labels = ['project', 'section', 'name', 'user_key', 'matched', 'r', 'slope', 'intercept',
              'caption', 'submitted', 'file', 'png', 'warnings']
    newest = {}
    for row in sorted(rows, key=lambda r: str(r[9])):
        linked = row[4] in ('login', 'name', 'linked by you')
        newest[(row[3], row[0]) if linked else ('file', row[10])] = row
    rows = list(newest.values())
    return Table().with_columns(*sum([[lab, make_array(*[row[i] for row in rows])]
                                      for i, lab in enumerate(labels)], []))


def load_reflections(t=None):
    "Every submitted reflection as a Table, linked to the roster like the figures."
    t = load_assignments() if t is None else t
    by_name, known = _name_index(t)
    rows = []
    for p in sorted(glob.glob(os.path.join(REFLECT_DIR, '*.json'))):
        try:
            r = json.load(open(p))
        except ValueError:
            continue
        key, sec, _ = _link(r, t, by_name, known)
        project = r.get('project', '')
        if not project and key in known:
            project = t.where('user_key', key).column('project').item(0)
        rows.append([project, sec, r.get('name', ''), key, r.get('reflection', ''), r.get('submitted', '')])
    labels = ['project', 'section', 'name', 'user_key', 'reflection', 'submitted']
    return Table().with_columns(*sum([[lab, make_array(*[row[i] for row in rows])]
                                      for i, lab in enumerate(labels)], []))


def read_roster(path):
    "One class roster, in its exported layout -> list of dicts (section, first, last, login)."
    with open(path, newline='', encoding='utf-8-sig') as f:
        rows = [[cell.strip() for cell in row] for row in csv.reader(f)]
    rows = [row for row in rows if any(row)]
    header = [cell.lower() for cell in rows[0]]
    name_col, login_col = 0, 1
    if 'student' in header or 'name' in header:                  # Canvas-style export with a header row
        name_col = header.index('student') if 'student' in header else header.index('name')
        for label in ['sis login id', 'login id', 'login', 'username', 'user']:
            if label in header:
                login_col = header.index(label)
                break
        rows = rows[1:]
    section = re.findall(r'\d+', os.path.basename(path))[-1].zfill(2)
    students = []
    for row in rows:
        full = row[name_col]
        if full.lower().startswith(('student, test', 'test student')) or 'points possible' in full.lower():
            continue
        if ',' in full:
            last, given = full.split(',', 1)                      # 'Last, First Middle'
        else:
            given, last = full.rsplit(' ', 1) if ' ' in full else (full, '')
        if not given.split():
            continue
        login = row[login_col].split('@')[0].lower() if len(row) > login_col else ''
        students.append({'section': section, 'first': given.split()[0], 'last': last.strip(), 'login': login,
                         'full': full, 'roster_section': row[2] if len(row) > 2 else ''})
    return students


# ============================================================================ setup + assign
def setup():
    "Create the shared folders and print a summary of what is saved."
    for folder in [MICRO_ROOT, SUBMIT_DIR, REFLECT_DIR]:
        os.makedirs(folder, exist_ok=True)
        try:
            os.chmod(folder, 0o777)              # every student must be able to write here
        except PermissionError:
            pass
    t = load_assignments()
    rosters = sorted(glob.glob('class_[0-9]*.csv'))
    print('Shared folder :', MICRO_ROOT)
    print('Rosters here  :', ', '.join(rosters) or 'none yet — upload class_03.csv etc. to this folder')
    print('Saved classes :', ', '.join(f'{s} ({t.where("section", s).num_rows})' for s in _classes(t)) or 'none yet')
    print('Figures       :', len(glob.glob(os.path.join(SUBMIT_DIR, '*.png'))))
    print('Reflections   :', len(glob.glob(os.path.join(REFLECT_DIR, '*.json'))))


def assign(redeal=None, drop=None, seed=1013):
    """Read every class_*.csv roster here and save the groups.
    Students keep their saved project; new students go into the smallest groups; students no longer
    on their roster are removed. Classes with no roster file here are kept exactly as saved.
      redeal='03'   deal class 03 again from scratch (only before students have seen it)
      drop='99'     delete a class from the saved groups (e.g. a test class)"""
    redeal = {_section(x) for x in (redeal if isinstance(redeal, (list, tuple)) else [redeal]) if x is not None}
    drop = {_section(x) for x in (drop if isinstance(drop, (list, tuple)) else [drop]) if x is not None}
    old = load_assignments()
    saved = dict(zip(old.column('user_key'), old.column('project')))

    rosters = sorted(glob.glob('class_[0-9]*.csv'))
    students = []
    for f in rosters:
        one = read_roster(f)
        print(f'  {f}: {len(one)} students')
        students += one
    if not students and not old.num_rows:
        print('No rosters found. Upload class_03.csv (etc.) into this folder, then run assign() again.')
        return

    new_parts = []
    roster_classes = sorted({s['section'] for s in students})
    for i, sec in enumerate(roster_classes):
        if sec in drop:
            continue
        group = [s for s in students if s['section'] == sec]
        firsts = [s['first'] for s in group]
        rows = []
        for s in group:
            label = f"{s['first']} {s['last'][:1]}." if firsts.count(s['first']) > 1 else s['first']
            key = user_key(s['login']) or user_key(f"{sec}|{s['first']}|{s['last']}")
            rows.append([sec, label, s['first'], s['last'][:1].upper(), key, ''])
        # keep saved projects, then deal the rest into the smallest groups
        np.random.seed(seed + int(sec) if sec.isdigit() else seed + i)
        counts = {pid: 0 for pid in PIDS}
        for row in rows:
            if sec not in redeal and saved.get(row[4], '') in counts:
                row[5] = saved[row[4]]
                counts[row[5]] += 1
        kept = sum(1 for row in rows if row[5])
        for j in np.random.choice(np.arange(len(rows)), len(rows), replace=False):
            if not rows[j][5]:
                order = np.random.choice(PIDS, len(PIDS), replace=False)
                smallest = min(order, key=lambda p: counts[p])
                rows[j][5] = smallest
                counts[smallest] += 1
        print(f'Class {sec}: {kept} kept their project, {len(rows) - kept} newly assigned'
              + (' (re-dealt)' if sec in redeal else ''))
        new_parts.append(rows)

    carried = [s for s in _classes(old) if s not in roster_classes and s not in drop]
    for s in carried:
        print(f'Class {s}: kept exactly as saved (no roster file here)')
    all_rows = [r for part in new_parts for r in part]
    for s in carried:
        one = old.where('section', s)
        all_rows += [[one.column(c).item(k) for c in COLUMNS] for k in range(one.num_rows)]
    for s in drop:
        print(f'Class {s}: removed')

    t = Table().with_columns(*sum([[c, make_array(*[r[i] for r in all_rows])] for i, c in enumerate(COLUMNS)], []))
    _save_assignments(t)
    print(f'Saved {t.num_rows} students. (A backup of the previous groups is in {BACKUP_DIR}.)')
    if t.num_rows:
        display(t.pivot('project', 'section'))


# ============================================================================ group boards
def _board_html(revealed, message, highlight=None):
    "Five group Tables side by side, with a big message line on top."
    cards = ''
    for pid in PIDS:
        names = revealed[pid]
        group = Table().with_columns(f'{len(names)} students', make_array(*names) if names else make_array())
        border = '#F2B705' if pid == highlight else '#A7A8AA'
        glow = 'box-shadow:0 0 18px #F2B705;' if pid == highlight else ''
        cards += (f'<div style="flex:1 1 180px;min-width:170px;border:3px solid {border};border-radius:12px;'
                  f'overflow:hidden;{glow}">'
                  f'<div style="background:#A41E35;color:white;padding:8px 10px;font-weight:800;font-size:1.15em">'
                  f'{EMOJI[pid]} {pid}<div style="font-size:.75em;font-weight:600">{TITLES[pid]}</div></div>'
                  f'<div style="padding:4px 8px;font-size:1.05em">{group.as_html()}</div></div>')
    return (f'<div style="font-family:sans-serif;margin-bottom:22px">'
            f'<div style="font-size:2em;font-weight:900;margin:6px 0 12px;min-height:1.4em">{message}</div>'
            f'<div style="display:flex;flex-wrap:wrap;gap:10px;align-items:flex-start">{cards}</div></div>')


def show_groups(which='all'):
    "Glossy group board for one class ('03') or every class ('all')."
    t = load_assignments()
    sec = _section(which)
    if sec is not None and not _check_class(t, sec):
        return
    for s in ([sec] if sec else _classes(t)):
        one = t.where('section', s)
        revealed = {pid: sorted(one.where('project', pid).column('display_name')) for pid in PIDS}
        display(HTML(_board_html(revealed, f'Class {s}: {_plural(one.num_rows, "student")}')))


def draw(which, pause=0.8):
    """Reveal one class's saved groups one student at a time, with a drumroll.
    Only reveals; never changes anyone's group. pause = seconds per student (0 = instant)."""
    t = load_assignments()
    sec = _section(which)
    if sec is None:
        print("draw() needs one class, e.g. draw('03').")
        return
    if not _check_class(t, sec):
        return
    one = t.where('section', sec)
    n = one.num_rows
    revealed = {pid: [] for pid in PIDS}
    board = display(HTML(_board_html(revealed, f'🎲 Class {sec}: {n} students, 5 projects…')), display_id=True)
    time.sleep(2 * pause)
    for k, i in enumerate(np.random.choice(np.arange(n), n, replace=False)):
        name, pid = one.column('display_name').item(i), one.column('project').item(i)
        if pause:
            board.update(HTML(_board_html(revealed, f'🥁 Student {k + 1} of {n}…')))
            time.sleep(pause / 2)
        revealed[pid].append(name)
        if pause:
            board.update(HTML(_board_html(revealed, f'<span style="color:#A41E35">{_esc(name)}</span> → '
                                                    f'{EMOJI[pid]} {TITLES[pid]}', highlight=pid)))
            time.sleep(pause)
    board.update(HTML(_board_html(revealed, f'🎉 Class {sec}: all {n} students drawn!')))


def fix_groups(which):
    """Drag-and-drop board for one class. Nothing changes until you click Save.
    Students who submitted a figure for a different project are tagged; 'Match submitted projects'
    moves them all to the project they did."""
    import ipywidgets as widgets
    t = load_assignments()
    sec = _section(which)
    if sec is None:
        print("fix_groups() needs one class, e.g. fix_groups('01').")
        return
    if not _check_class(t, sec):
        return
    one = t.where('section', sec)
    subs = load_submissions(t)
    submitted = {k: p for k, p in zip(subs.column('user_key'), subs.column('project')) if k and p in PIDS}
    uid = uuid.uuid4().hex[:8]
    students = sorted([{'key': k, 'name': n, 'project': p, 'submitted': submitted.get(k, '')}
                       for k, n, p in zip(one.column('user_key'), one.column('display_name'), one.column('project'))],
                      key=lambda s: s['name'])
    columns = ''.join(f'<div class="mp-col" data-project="{pid}"><div class="mp-head">{EMOJI[pid]} {pid} '
                      f'<span class="mp-n"></span><div class="mp-title">{TITLES[pid]}</div></div>'
                      f'<div class="mp-drop"></div></div>' for pid in PIDS)
    board = f'''
<div id="mp-{uid}" class="mp-board">
<style>
  #mp-{uid} {{ font-family: sans-serif; }}
  #mp-{uid} .mp-cols {{ display: flex; gap: 10px; align-items: flex-start; flex-wrap: wrap; }}
  #mp-{uid} .mp-col {{ flex: 1 1 170px; min-width: 165px; border: 3px solid #A7A8AA; border-radius: 12px; overflow: hidden; background: #fff; }}
  #mp-{uid} .mp-col.over {{ border-color: #F2B705; box-shadow: 0 0 14px #F2B705; }}
  #mp-{uid} .mp-head {{ background: #A41E35; color: #fff; padding: 8px 10px; font-weight: 800; font-size: 1.1em; }}
  #mp-{uid} .mp-title {{ font-size: .75em; font-weight: 600; }}
  #mp-{uid} .mp-drop {{ min-height: 120px; padding: 5px; display: flex; flex-direction: column; gap: 3px; }}
  #mp-{uid} .mp-card {{ padding: 3px 8px; line-height: 1.3; border: 1px solid #ccc; border-radius: 7px; background: #FBF9F6; cursor: grab; font-size: 1.02em; user-select: none; }}
  #mp-{uid} .mp-card.moved {{ background: #FFF4CC; border-color: #E0B000; font-weight: 700; }}
  #mp-{uid} .mp-card .mp-flag {{ color: #A41E35; font-size: .8em; }}
  #mp-{uid} .mp-bar {{ display: flex; gap: 8px; margin: 0 0 10px; align-items: center; flex-wrap: wrap; }}
  #mp-{uid} button {{ padding: 6px 12px; border-radius: 8px; border: 1px solid #A41E35; background: #fff; color: #A41E35; font-weight: 700; cursor: pointer; }}
  #mp-{uid} .mp-status {{ color: #555; }}
</style>
<div class="mp-bar">
  <b style="font-size:1.25em">Class {sec}: drag names between projects</b>
  <button class="mp-match">Match submitted projects</button>
  <button class="mp-reset">Undo all changes</button>
  <span class="mp-status"></span>
</div>
<div class="mp-cols">{columns}</div>
</div>
<script>
(function () {{
  const root = document.getElementById('mp-{uid}');
  const students = {json.dumps(students)};
  let dragged = null;
  function card(s) {{
    const c = document.createElement('div');
    c.className = 'mp-card'; c.draggable = true; c.dataset.key = s.key; c.dataset.orig = s.project;
    c.dataset.submitted = s.submitted;
    c.innerHTML = s.name.replace(/[&<>]/g, ch => ({{'&':'&amp;','<':'&lt;','>':'&gt;'}})[ch]) +
      (s.submitted && s.submitted !== s.project ? ' <span class="mp-flag">submitted ' + s.submitted + '</span>' : '');
    c.addEventListener('dragstart', e => {{ dragged = c; e.dataTransfer.setData('text/plain', s.key); }});
    return c;
  }}
  function place(projectOf) {{
    root.querySelectorAll('.mp-drop').forEach(d => d.innerHTML = '');
    students.forEach(s => root.querySelector('.mp-col[data-project="' + projectOf(s) + '"] .mp-drop').appendChild(card(s)));
    sync();
  }}
  function sync() {{
    const result = {{}}; let moved = 0;
    root.querySelectorAll('.mp-col').forEach(col => {{
      const cards = col.querySelectorAll('.mp-card');
      col.querySelector('.mp-n').textContent = '(' + cards.length + ')';
      cards.forEach(c => {{
        result[c.dataset.key] = col.dataset.project;
        const m = col.dataset.project !== c.dataset.orig; c.classList.toggle('moved', m); if (m) moved++;
        const f = c.querySelector('.mp-flag');
        if (f) f.style.display = (c.dataset.submitted === col.dataset.project) ? 'none' : '';
      }});
    }});
    root.querySelector('.mp-status').textContent = moved + ' change' + (moved === 1 ? '' : 's') + ' not yet saved';
    const box = document.querySelector('.mpsync-{uid} input, .mpsync-{uid} textarea');
    if (box) {{
      box.value = JSON.stringify(result);
      box.dispatchEvent(new Event('input', {{ bubbles: true }}));
      box.dispatchEvent(new Event('change', {{ bubbles: true }}));
    }}
  }}
  root.querySelectorAll('.mp-col').forEach(col => {{
    col.addEventListener('dragover', e => {{ e.preventDefault(); col.classList.add('over'); }});
    col.addEventListener('dragleave', () => col.classList.remove('over'));
    col.addEventListener('drop', e => {{
      e.preventDefault(); col.classList.remove('over');
      if (dragged) {{ col.querySelector('.mp-drop').appendChild(dragged); dragged = null; sync(); }}
    }});
  }});
  root.querySelector('.mp-reset').onclick = () => place(s => s.project);
  root.querySelector('.mp-match').onclick = () => place(s => s.submitted || s.project);
  place(s => s.project);
}})();
</script>'''
    pending = {s['key']: s['project'] for s in students}
    sync_box = widgets.Text(value=json.dumps(pending), layout=widgets.Layout(display='none'))
    sync_box.add_class(f'mpsync-{uid}')
    save = widgets.Button(description=f'💾 Save class {sec}', button_style='danger',
                          layout=widgets.Layout(width='220px', height='40px'))
    out = widgets.Output()

    def on_change(change):
        try:
            pending.update(json.loads(change['new']))
        except ValueError:
            pass

    def on_save(_):
        current = load_assignments()                       # reread: never overwrite other classes' changes
        new_projects = make_array(*[pending.get(k, p) if s == sec else p for k, p, s in
                                    zip(current.column('user_key'), current.column('project'),
                                        current.column('section'))])
        changed = int(np.count_nonzero(new_projects != current.column('project')))
        _save_assignments(current.with_column('project', new_projects))
        with out:
            out.clear_output()
            print(f'Saved {_plural(changed, "change")} for class {sec}. '
                  'Students see their new project the next time they run my_project().')
            show_groups(sec)

    sync_box.observe(on_change, names='value')
    save.on_click(on_save)
    display(HTML(board))
    display(widgets.VBox([sync_box, save, out]))


# ============================================================================ submissions
def who_submitted(which='all'):
    "Who has submitted a figure and a reflection, for one class ('03') or every class ('all')."
    t = load_assignments()
    sec = _section(which)
    if sec is not None and not _check_class(t, sec):
        return
    subs, refl = load_submissions(t), load_reflections(t)
    fig_keys, refl_keys = set(subs.column('user_key')), set(refl.column('user_key'))
    status = t.with_columns(
        'figure',     make_array(*['✅' if k in fig_keys else '—' for k in t.column('user_key')]),
        'reflection', make_array(*['✅' if k in refl_keys else '—' for k in t.column('user_key')]))
    if sec is not None:
        status = status.where('section', sec)
    n_fig = np.count_nonzero(status.column('figure') == '✅')
    n_ref = np.count_nonzero(status.column('reflection') == '✅')
    print(f'{class_name(sec)}: {n_fig} of {status.num_rows} figures, {n_ref} of {status.num_rows} reflections')
    problems = subs.where('matched', are.contained_in(make_array('unmatched', 'ambiguous name')))
    lost_refl = refl.where('user_key', are.not_contained_in(make_array(*t.column('user_key')))) if refl.num_rows else refl
    if problems.num_rows or lost_refl.num_rows:
        print(f"⚠️ {_plural(problems.num_rows, 'figure')} and {_plural(lost_refl.num_rows, 'reflection')} aren't linked "
              "to a roster student. Attach or discard them with link_submissions('01'):")
        if problems.num_rows:
            problems.select('file', 'name', 'project', 'matched').show()
    status.select('section', 'project', 'display_name', 'figure', 'reflection') \
          .relabeled('display_name', 'student').sort('student').sort('project').sort('section').show()


def class_name(sec):
    return 'All classes' if sec is None else f'Class {sec}'


def add_submission(png_file, name, section, project, caption='', r=np.nan, slope=np.nan, intercept=np.nan):
    """Put a student's figure in the gallery for them. name = their name as shown in the groups,
    e.g. 'Chloe B.'; png_file = the image uploaded into this folder."""
    t = load_assignments()
    sec = _section(section)
    project = str(project).upper()
    match = t.where('section', sec).where('display_name', name)
    if match.num_rows != 1:
        print(f'No single student {name!r} in class {sec}. Names in that class:')
        print(', '.join(sorted(t.where('section', sec).column('display_name'))))
        return
    key = match.column('user_key').item(0)
    first, initial = match.column('first_name').item(0), match.column('last_initial').item(0)
    stem = f'{project}_{sec}_{first}{initial}_{key[:4]}'
    shutil.copy(png_file, os.path.join(SUBMIT_DIR, stem + '.png'))
    record = {'name': f'{first} {initial}.', 'first_name': first, 'project': project, 'user_key': key,
              'section': sec, 'r': float(r), 'slope': float(slope), 'intercept': float(intercept),
              'caption': caption, 'submitted': datetime.datetime.now().isoformat(timespec='seconds'),
              'added_by_instructor': True}
    with open(os.path.join(SUBMIT_DIR, stem + '.json'), 'w') as f:
        json.dump(record, f, indent=1)
    print(f'✅ Added {stem}.png. Run gallery() to see it.')


# ============================================================================ gallery
STOP_WORDS = set("""
a about above after again against all also am an and any are as at be because been before being below between both
but by can could did do does doing done down during each even every few for from further get got had has have having
he her here hers him his how i if in into is it its itself just like lot lots made make many me more most much my
myself no nor not now of off on once only or other our out over own really same she should so some something such
than that the their them then there these they thing things this those through to too under until up us very was we
were what when where which while who whom why will with would you your yours i'm it's didn't don't wasn't couldn't
think felt feel bit kind way well one two first overall able still since though
""".split())


def _word_cloud(texts, n_words=45):
    words = []
    for text in texts:
        words += [w.strip("'") for w in re.findall(r"[a-zA-Z][a-zA-Z'-]+", str(text).lower())]
    top = Counter(w for w in words if len(w) > 2 and w not in STOP_WORDS).most_common(n_words)
    if not top:
        return '<div style="color:#777">No words yet.</div>'
    biggest = top[0][1]
    palette = ['#A41E35', '#221C1E', '#7A1626', '#5B4A50', '#8A5F00', '#2F5D8A']
    rng = np.random.RandomState(7)
    spans = ''
    for i in rng.choice(np.arange(len(top)), len(top), replace=False):
        word, n = top[i]
        spans += (f'<span title="{_plural(n, "use")}" style="font-size:{15 + 47 * np.sqrt(n / biggest):.0f}px;'
                  f'font-weight:{800 if n / biggest > 0.5 else 600};color:{palette[i % len(palette)]};'
                  f'margin:2px 10px;line-height:1.1;display:inline-block">{_esc(word)}</span>')
    return ('<div style="background:white;border:1px solid #ddd;border-radius:12px;padding:18px 16px;'
            f'text-align:center;margin-bottom:14px">{spans}</div>')


def _figure_part(subs, labels, card_width):
    parts = ['<h2 style="margin:30px 0 0">Part 1 · Figures</h2>']
    for pid in PIDS + (['DEMO'] if 'DEMO' in subs.column('project') else []):
        sub = subs.where('project', pid)
        names = [_label(labels, k, n, s) for k, n, s in zip(sub.column('user_key'), sub.column('name'), sub.column('section'))]
        banner = ('<div style="background:#A41E35;color:white;border-radius:10px;padding:12px 18px;margin:28px 0 12px;'
                  f'font-size:1.6em;font-weight:900">{EMOJI.get(pid, "")} {pid}: {_esc(TITLES.get(pid, pid))}'
                  f'<span style="font-size:.6em;font-weight:600"> &nbsp;— {_plural(sub.num_rows, "figure")}</span></div>')
        if sub.num_rows == 0:
            parts.append(banner + '<div style="color:#777;margin-left:6px">No submissions yet.</div>')
            continue
        cards = ''
        for i in np.argsort(names):
            caption = _esc(sub.column('caption').item(i)) or '<i>(no caption)</i>'
            cards += ('<div style="background:white;border:1px solid #ccc;border-radius:10px;padding:10px 12px;'
                      'box-shadow:0 2px 6px rgba(0,0,0,.15)">'
                      f'<div style="font-size:1.3em;font-weight:800;margin-bottom:4px">{_esc(names[i])}</div>'
                      f'<img src="data:image/png;base64,{_img64(sub.column("png").item(i))}" alt="Figure by {_esc(names[i])}" '
                      'style="width:100%;border-radius:6px">'
                      f'<div style="font-size:1.05em;line-height:1.35;margin-top:8px">{caption}</div>'
                      f'<div style="font-size:.85em;color:#555;margin-top:6px">r = {sub.column("r").item(i):.3f} '
                      f'&nbsp;·&nbsp; slope = {sub.column("slope").item(i):.4g}</div></div>')
        parts.append(banner + f'<div style="display:grid;grid-template-columns:repeat(auto-fill,minmax({card_width}px,1fr));'
                              f'gap:16px;align-items:start">{cards}</div>')
    return parts


def _reflection_part(refl, labels):
    parts = ['<h2 style="margin:40px 0 0">Part 2 · Reflections</h2>']
    for pid in PIDS:
        sub = refl.where('project', pid)
        banner = ('<div style="background:#221C1E;color:white;border-radius:10px;padding:12px 18px;margin:28px 0 12px;'
                  f'font-size:1.5em;font-weight:900">💬 {EMOJI[pid]} {pid}: {_esc(TITLES[pid])}'
                  f'<span style="font-size:.6em;font-weight:600"> &nbsp;— {_plural(sub.num_rows, "reflection")}</span></div>')
        if sub.num_rows == 0:
            parts.append(banner + '<div style="color:#777;margin-left:6px">No reflections yet.</div>')
            continue
        names = [_label(labels, k, n, s) for k, n, s in zip(sub.column('user_key'), sub.column('name'), sub.column('section'))]
        cards = ''
        for i in np.argsort(names):
            body = _esc(sub.column('reflection').item(i)).replace('\n\n', '<br><br>').replace('\n', '<br>')
            cards += ('<div style="background:white;border:1px solid #ccc;border-left:5px solid #A41E35;border-radius:10px;'
                      'padding:12px 16px;box-shadow:0 2px 6px rgba(0,0,0,.08)">'
                      f'<div style="font-size:1.15em;font-weight:800;margin-bottom:6px">{_esc(names[i])}</div>'
                      f'<div style="font-size:1.02em;line-height:1.45">{body}</div></div>')
        parts.append(banner + _word_cloud(sub.column('reflection')) +
                     f'<div style="display:grid;grid-template-columns:repeat(auto-fill,minmax(420px,1fr));gap:14px">{cards}</div>')
    return parts


def gallery(which='all', reflections=True, save_page=True, card_width=460):
    """Figures (Part 1) and reflections with a word cloud per project (Part 2), for one class or 'all'.
    Also saved as microproject_gallery_03.html (or _all) in this folder, viewable in any browser.
      reflections=False   figures only        save_page=False   don't write the web page
      card_width=600      bigger figures on the projector"""
    t = load_assignments()
    sec = _section(which)
    labels = _labels(t)
    subs = load_submissions(t)
    refl = load_reflections(t)
    if sec is not None:
        subs, refl = subs.where('section', sec), refl.where('section', sec)
    parts = _figure_part(subs, labels, card_width)
    if reflections:
        parts += _reflection_part(refl, labels)
    print(f'{class_name(sec)}: {_plural(subs.num_rows, "figure")}'
          + (f', {_plural(refl.num_rows, "reflection")}' if reflections else ''))
    for part in parts:
        display(HTML(part))
    if save_page:
        page_file = f'microproject_gallery_{sec or "all"}.html'
        page = ('<!DOCTYPE html><html><head><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1">'
                '<title>Microproject Results Gallery</title></head>'
                '<body style="font-family:-apple-system,Segoe UI,Roboto,Arial,sans-serif;background:#FBF9F6;color:#221C1E;'
                'max-width:1500px;margin:0 auto;padding:24px 20px 48px">'
                '<div style="background:#221C1E;color:#FBF9F6;border-radius:12px;padding:22px 26px">'
                '<div style="font-size:.9em;font-weight:700;letter-spacing:2px;text-transform:uppercase;color:#F2B8C4">'
                'Elements of Data Science · Regression Microprojects</div>'
                '<div style="font-size:2.2em;font-weight:900">Results Gallery</div>'
                f'<div style="color:#D9CFD2">{class_name(sec)} · {_plural(subs.num_rows, "figure")}</div></div>'
                + ''.join(parts) + '</body></html>')
        with open(page_file, 'w', encoding='utf-8') as f:
            f.write(page)
        display(HTML(f'<p style="font-size:1.15em">💾 Saved <b>{page_file}</b> — '
                     f'<a href="{page_file}" target="_blank" download>download it</a> to view outside Jupyter.</p>'))


# ============================================================================ slide show
_SLIDE_STYLE = '''
* { box-sizing: border-box; margin: 0; }
html, body { height: 100%; background: #1d1719; font-family: -apple-system, "Segoe UI", Roboto, Arial, sans-serif; }
#deck { position: absolute; width: 1920px; height: 1080px; left: 50%; top: 50%; transform-origin: center; }
section { position: absolute; inset: 0; display: none; flex-direction: column; padding: 70px 110px; background: #FBF9F6; color: #221C1E; }
section.on { display: flex; }
.title, .project { justify-content: center; background: #221C1E; color: #FBF9F6; }
.project { background: linear-gradient(135deg, #7A1626, #A41E35); }
.eyebrow { font-size: 30px; font-weight: 700; letter-spacing: 4px; text-transform: uppercase; color: #F2B8C4; }
.title h1 { font-size: 150px; font-weight: 900; margin: 16px 0; }
.project h1 { font-size: 110px; font-weight: 900; line-height: 1.05; margin: 10px 0 34px; }
.sub { font-size: 44px; color: #D9CFD2; }
.icon { font-size: 120px; }
.question { font-size: 54px; font-weight: 700; line-height: 1.25; max-width: 1500px; }
.twist { font-size: 40px; line-height: 1.35; margin-top: 26px; max-width: 1550px; color: #F6E3E7; }
.stats { font-size: 32px; margin-top: 46px; color: #F2B8C4; }
.bar { display: flex; justify-content: space-between; font-size: 34px; font-weight: 800; color: #A41E35;
       border-bottom: 4px solid #A41E35; padding-bottom: 14px; margin-bottom: 22px; }
.figure img { flex: 1; min-height: 0; width: 100%; object-fit: contain; }
.caption { font-size: 40px; line-height: 1.3; margin-top: 22px; font-weight: 600; }
.numbers { font-size: 28px; color: #6a5f63; margin-top: 10px; }
#count { position: fixed; right: 18px; bottom: 12px; color: #a99; font-size: 16px; }
'''
_SLIDE_SCRIPT = '''
const s = [...document.querySelectorAll('section')]; let k = 0;
function show(i) { k = Math.max(0, Math.min(s.length - 1, i)); s.forEach((x, j) => x.classList.toggle('on', j === k));
  document.getElementById('count').textContent = (k + 1) + ' / ' + s.length + '   ← → to move · F full screen'; }
function fit() { const d = document.getElementById('deck'); const z = Math.min(innerWidth / 1920, innerHeight / 1080);
  d.style.transform = 'translate(-50%, -50%) scale(' + z + ')'; }
addEventListener('keydown', e => {
  if (['ArrowRight', 'ArrowDown', ' ', 'PageDown'].includes(e.key)) show(k + 1);
  if (['ArrowLeft', 'ArrowUp', 'PageUp'].includes(e.key)) show(k - 1);
  if (e.key === 'Home') show(0); if (e.key === 'End') show(s.length - 1);
  if (e.key === 'f' || e.key === 'F') document.fullscreenElement ? document.exitFullscreen() : document.documentElement.requestFullscreen(); });
addEventListener('click', e => show(e.clientX < innerWidth / 3 ? k - 1 : k + 1));
addEventListener('resize', fit); fit(); show(0);
'''


def slideshow(which='all', shuffle=False):
    """Stand-alone slide show: a title slide, then a project slide before each project's figures.
    Saved as microproject_results_03.html (or _all). shuffle=True puts students in random order."""
    t = load_assignments()
    sec = _section(which)
    labels = _labels(t)
    subs = load_submissions(t)
    if sec is not None:
        subs = subs.where('section', sec)
    slides = [f'<section class="title"><p class="eyebrow">Elements of Data Science · Regression Microprojects</p>'
              f'<h1>Results Gallery</h1><p class="sub">{class_name(sec)} · {_plural(subs.num_rows, "figure")} · 5 projects</p></section>']
    for pid in PIDS:
        sub = subs.where('project', pid)
        if sub.num_rows == 0:
            continue
        question, twist = PROJECT_INFO[pid]
        rs = sub.column('r')
        names = [_label(labels, k, n, s) for k, n, s in zip(sub.column('user_key'), sub.column('name'), sub.column('section'))]
        order = np.random.choice(np.arange(sub.num_rows), sub.num_rows, replace=False) if shuffle else np.argsort(names)
        slides.append(f'<section class="project"><div class="icon">{EMOJI[pid]}</div><p class="eyebrow">{pid}</p>'
                      f'<h1>{_esc(TITLES[pid])}</h1><p class="question">{_esc(question)}</p>'
                      f'<p class="twist"><b>Twist:</b> {_esc(twist)}</p>'
                      f'<p class="stats">{_plural(sub.num_rows, "figure")} · average r = {np.nanmean(rs):.3f} · '
                      f'range {np.nanmin(rs):.3f} to {np.nanmax(rs):.3f}</p></section>')
        for i in order:
            slides.append(f'<section class="figure"><div class="bar"><span>{EMOJI[pid]} {pid} · {_esc(TITLES[pid])}</span>'
                          f'<span>{_esc(names[i])}</span></div>'
                          f'<img src="data:image/png;base64,{_img64(sub.column("png").item(i))}" alt="Figure by {_esc(names[i])}">'
                          f'<p class="caption">{_esc(sub.column("caption").item(i) or "(no caption)")}</p>'
                          f'<p class="numbers">r = {sub.column("r").item(i):.3f} · slope = {sub.column("slope").item(i):.4g} · '
                          f'intercept = {sub.column("intercept").item(i):.4g}</p></section>')
    page = ('<!DOCTYPE html><html><head><meta charset="utf-8"><title>Microproject Results</title>'
            f'<style>{_SLIDE_STYLE}</style></head><body><div id="deck">{"".join(slides)}</div>'
            f'<div id="count"></div><script>{_SLIDE_SCRIPT}</script></body></html>')
    page_file = f'microproject_results_{sec or "all"}.html'
    with open(page_file, 'w', encoding='utf-8') as f:
        f.write(page)
    print(f'{_plural(len(slides), "slide")} ({_plural(subs.num_rows, "figure")}).')
    display(HTML(f'<p style="font-size:1.3em;font-weight:700">▶ <a href="{page_file}" target="_blank">{page_file}</a></p>'
                 '<p>In the file browser: right-click the file → <b>Open in New Browser Tab</b>. '
                 'Then ← → or click to move, <b>F</b> for full screen.</p>'))


# ============================================================================ discussion
def compare_lines(which='all'):
    "Average and spread of r and slope for each project: did everyone get the same line?"
    t = load_assignments()
    sec = _section(which)
    subs = load_submissions(t)
    if sec is not None:
        subs = subs.where('section', sec)
    if subs.num_rows == 0:
        print(f'{class_name(sec)}: no figures yet.')
        return
    rows = []
    for pid in PIDS:
        sub = subs.where('project', pid)
        if sub.num_rows:
            rows.append([pid, TITLES[pid], sub.num_rows, np.nanmean(sub.column('r')), np.nanmin(sub.column('r')),
                         np.nanmax(sub.column('r')), np.nanmean(sub.column('slope'))])
    labels = ['project', 'title', 'figures', 'mean r', 'lowest r', 'highest r', 'mean slope']
    print(class_name(sec))
    display(Table().with_columns(*sum([[lab, make_array(*[r[i] for r in rows])] for i, lab in enumerate(labels)], []))
            .set_format(['mean r', 'lowest r', 'highest r'], lambda x: f'{x:.3f}'))


# ============================================================================ Canvas export
_SHORT = {'horizontal axis label': 'no x-axis label', 'vertical axis label': 'no y-axis label',
          'title': 'no title', 'scatter points': 'no scatter points', 'regression line': 'no regression line',
          'legend': 'no legend', 'figure is empty': 'empty figure'}


def _shorten(warning):
    for key, short in _SHORT.items():
        if key in warning.lower():
            return short
    return warning


GRAPH_PROBLEMS = {'empty figure', 'no scatter points', 'no regression line'}


def _grade(caption, warnings, points, element_penalty, graph_penalty):
    "Score one submission: -element_penalty per missing element, -graph_penalty once for an incomplete graph."
    missing = []
    if not str(caption).strip() or str(caption).strip() in ('...', 'Ellipsis'):
        missing.append('no caption')
    problems = [_shorten(w) for w in str(warnings).split(' | ') if w.strip()]
    graph = [w for w in problems if w in GRAPH_PROBLEMS]
    elements = [w for w in problems if w not in GRAPH_PROBLEMS and w != 'empty figure']
    missing += elements
    deduct = element_penalty * len(missing) + (graph_penalty if graph else 0)
    return max(0.0, points - deduct), missing + graph


def export_canvas(which='all', points=5, element_penalty=1, graph_penalty=2.5, incomplete=0,
                  require_reflection=False, assignment='Regression Microproject'):
    """Write a Canvas gradebook import file for the microproject.
    Each student's best submission (any project) starts at `points` and loses
      element_penalty (1) for each missing element: caption, x-axis label, y-axis label, title, legend
      graph_penalty (2.5) once if the graph itself is incomplete: empty, no scatter points, or no regression line
    never going below 0. Students with no figure get `incomplete` (0; '' leaves their Canvas grade unchanged).
      require_reflection=True       a missing reflection also costs element_penalty
      assignment='...'              the Canvas column name; to update an existing assignment, copy its
                                    header from a Canvas gradebook export, e.g. 'Regression Microproject (123456)'
    Needs the class_*.csv rosters in this folder (they hold the SIS Login IDs Canvas matches on)."""
    sec = _section(which)
    rosters = sorted(glob.glob('class_[0-9]*.csv'))
    students = [s for f in rosters for s in read_roster(f) if sec is None or s['section'] == sec]
    if not students:
        print(f'No roster here for {class_name(sec)}. Upload its class_*.csv to this folder first.')
        return
    t = load_assignments()
    subs, refl = load_submissions(t), load_reflections(t)
    refl_keys = set(refl.column('user_key'))

    rows, review = [], []
    for s in students:
        key = user_key(s['login']) or user_key(f"{s['section']}|{s['first']}|{s['last']}")
        mine = subs.where('user_key', key)
        best = None                                       # (score, project, missing)
        for i in range(mine.num_rows):
            score, missing = _grade(mine.column('caption').item(i), mine.column('warnings').item(i),
                                    points, element_penalty, graph_penalty)
            if require_reflection and key not in refl_keys:
                score, missing = max(0.0, score - element_penalty), missing + ['no reflection']
            if best is None or score > best[0]:
                best = (score, mine.column('project').item(i), missing)
        score = (round(best[0], 2) if best else incomplete)
        rows.append([s['full'], '', '', s['login'], s['roster_section'] or s['section'], score])
        review.append([s['section'], f"{s['first']} {s['last'][:1]}.", best[1] if best else '—',
                       f'{score:g}' if best else '', ', '.join(best[2]) if best else 'no figure', score if best else None])

    out_file = f'canvas_microproject_{sec or "all"}.csv'
    with open(out_file, 'w', newline='', encoding='utf-8') as f:
        w = csv.writer(f)
        w.writerow(['Student', 'ID', 'SIS User ID', 'SIS Login ID', 'Section', assignment])
        w.writerows(rows)
    full = sum(1 for r in review if r[5] is not None and r[5] >= points)
    partial = sum(1 for r in review if r[5] is not None and r[5] < points)
    none = len(review) - full - partial
    print(f'{class_name(sec)}: {full} full credit ({points}) · {partial} partial · {none} no figure '
          f'({incomplete if incomplete != "" else "left blank"}).')
    display(HTML(f'<p style="font-size:1.15em">💾 Saved <b>{out_file}</b> — '
                 f'<a href="{out_file}" target="_blank" download>download it</a>, then in Canvas: '
                 '<b>Grades → Import</b>. 🔒 It holds names and logins: keep it off GitHub.</p>'))
    table = Table().with_columns('class', make_array(*[r[0] for r in review]), 'student', make_array(*[r[1] for r in review]),
                                 'project', make_array(*[r[2] for r in review]), 'score', make_array(*[r[3] for r in review]),
                                 'what is missing', make_array(*[r[4] for r in review]))
    part = table.where('score', are.not_equal_to('')).where('what is missing', are.not_equal_to(''))
    if part.num_rows:
        print(f'⚠️ Partial credit ({_plural(part.num_rows, "student")}) — check before importing:')
        part.sort('student').sort('class').show()
    nofig = table.where('what is missing', 'no figure')
    for c in np.unique(nofig.column('class')):
        names = sorted(nofig.where('class', c).column('student'))
        print(f'No figure yet, class {c} ({len(names)}): ' + ', '.join(names))


# ============================================================================ link unlinked submissions
DISCARD_DIR = os.path.join(MICRO_ROOT, 'discarded')


def _unlinked(t):
    "Figures and reflections not linked to any roster student (instructor DEMO figures excluded)."
    by_name, known = _name_index(t)
    items = []
    for kind, folder in (('figure', SUBMIT_DIR), ('reflection', REFLECT_DIR)):
        for p in sorted(glob.glob(os.path.join(folder, '*.json'))):
            try:
                r = json.load(open(p))
            except ValueError:
                continue
            key, sec, how = _link(r, t, by_name, known)
            if how in ('unmatched', 'ambiguous name'):
                words = str(r.get('name', '')).replace('.', ' ').split()
                first = words[0].lower() if words else ''
                suggest = [k for k, _ in by_name.get((first, ''), [])]
                thumb = (_img64(p[:-5] + '.png') if kind == 'figure' and os.path.exists(p[:-5] + '.png') else '')
                items.append({'id': f'{kind}:{os.path.basename(p)}', 'kind': kind, 'name': str(r.get('name', '')),
                              'project': r.get('project', ''), 'why': how, 'suggest': suggest, 'thumb': thumb,
                              'text': (str(r.get('reflection', '')) if kind == 'reflection' else str(r.get('caption', '')))[:140]})
    return items


def link_submissions(which):
    """Drag-and-drop board: attach unlinked figures and reflections to the right student in one class,
    or drop them on 🗑 Discard (e.g. your trial runs). Nothing changes until you click Save.
    Suggested students (same first name) are outlined in gold."""
    import ipywidgets as widgets
    t = load_assignments()
    sec = _section(which)
    if sec is None:
        print("link_submissions() needs one class, e.g. link_submissions('01').")
        return
    if not _check_class(t, sec):
        return
    items = _unlinked(t)
    if not items:
        print('✅ Every figure and reflection is linked to a student. Nothing to do.')
        return
    one = t.where('section', sec)
    roster = sorted([{'key': k, 'name': n, 'project': p} for k, n, p in
                     zip(one.column('user_key'), one.column('display_name'), one.column('project'))], key=lambda r: r['name'])
    uid = uuid.uuid4().hex[:8]
    board = f'''
<div id="ln-{uid}" style="font-family:sans-serif">
<style>
  #ln-{uid} .ln-wrap {{ display:flex; gap:16px; align-items:flex-start; flex-wrap:wrap; }}
  #ln-{uid} .ln-items {{ flex:1 1 380px; display:flex; flex-direction:column; gap:8px; }}
  #ln-{uid} .ln-item {{ display:flex; gap:10px; align-items:center; border:2px solid #ccc; border-radius:10px; padding:6px 10px;
                        background:#fff; cursor:grab; user-select:none; }}
  #ln-{uid} .ln-item.done {{ border-color:#2E7D50; background:#EEF7F0; }}
  #ln-{uid} .ln-item.trash {{ border-color:#A41E35; background:#FBEDEF; opacity:.75; }}
  #ln-{uid} .ln-item img {{ width:120px; border-radius:6px; border:1px solid #ddd; }}
  #ln-{uid} .ln-item .ln-ref {{ font-size:28px; width:120px; text-align:center; }}
  #ln-{uid} .ln-target {{ font-weight:800; color:#2E7D50; }}
  #ln-{uid} .ln-item.trash .ln-target {{ color:#A41E35; }}
  #ln-{uid} .ln-names {{ flex:1 1 420px; display:flex; flex-wrap:wrap; gap:5px; align-content:flex-start; }}
  #ln-{uid} .ln-chip {{ padding:5px 10px; border:1px solid #bbb; border-radius:16px; background:#FBF9F6; font-size:.98em; }}
  #ln-{uid} .ln-chip.suggest {{ border:2px solid #F2B705; background:#FFF8DC; font-weight:700; }}
  #ln-{uid} .ln-chip.over, #ln-{uid} .ln-bin.over {{ box-shadow:0 0 12px #F2B705; border-color:#F2B705; }}
  #ln-{uid} .ln-bin {{ width:100%; margin-top:8px; padding:14px; text-align:center; border:3px dashed #A41E35; border-radius:12px;
                       color:#A41E35; font-weight:800; font-size:1.1em; }}
  #ln-{uid} button {{ padding:3px 9px; border-radius:7px; border:1px solid #888; background:#fff; cursor:pointer; }}
</style>
<div style="font-size:1.3em;font-weight:800;margin-bottom:8px">Drag each item onto the student it belongs to (class {sec}), or onto 🗑 Discard</div>
<div class="ln-wrap"><div class="ln-items"></div><div class="ln-names"></div></div>
</div>
<script>
(function () {{
  const root = document.getElementById('ln-{uid}');
  const items = {json.dumps(items)}, roster = {json.dumps(roster)};
  const choice = {{}}; let dragged = null;
  const esc = t => String(t).replace(/[&<>"]/g, c => ({{'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;'}})[c]);
  const nameOf = k => (roster.find(r => r.key === k) || {{}}).name || k;
  function sync() {{
    const box = document.querySelector('.lnsync-{uid} input, .lnsync-{uid} textarea');
    if (box) {{ box.value = JSON.stringify(choice); box.dispatchEvent(new Event('input', {{bubbles:true}}));
               box.dispatchEvent(new Event('change', {{bubbles:true}})); }}
  }}
  function paint(card, it) {{
    const c = choice[it.id];
    card.classList.toggle('done', !!c && c !== 'DISCARD'); card.classList.toggle('trash', c === 'DISCARD');
    card.querySelector('.ln-target').textContent = !c ? '' : (c === 'DISCARD' ? '🗑 discard' : '→ ' + nameOf(c));
    card.querySelector('.ln-undo').style.display = c ? '' : 'none';
  }}
  items.forEach(it => {{
    const card = document.createElement('div'); card.className = 'ln-item'; card.draggable = true;
    card.innerHTML = (it.thumb ? '<img src="data:image/png;base64,' + it.thumb + '">' : '<div class="ln-ref">💬</div>') +
      '<div style="flex:1"><div><b>' + esc(it.name || '(no name)') + '</b> · ' + esc(it.project) + ' · ' + it.kind +
      ' <span style="color:#999">(' + it.why + ')</span></div><div style="font-size:.9em;color:#555">' + esc(it.text) +
      '</div><div class="ln-target"></div></div><button class="ln-undo">undo</button>';
    card.addEventListener('dragstart', () => {{ dragged = it; }});
    card.querySelector('.ln-undo').onclick = () => {{ delete choice[it.id]; paint(card, it); sync(); }};
    it.card = card; paint(card, it); root.querySelector('.ln-items').appendChild(card);
  }});
  const targets = roster.map(r => ({{key: r.key, label: r.name + ' · ' + r.project}}));
  targets.forEach(r => {{
    const chip = document.createElement('div'); chip.className = 'ln-chip'; chip.textContent = r.label; chip.dataset.key = r.key;
    if (items.some(it => it.suggest.includes(r.key))) chip.classList.add('suggest');
    root.querySelector('.ln-names').appendChild(chip);
  }});
  const bin = document.createElement('div'); bin.className = 'ln-bin'; bin.dataset.key = 'DISCARD'; bin.textContent = '🗑 Discard (trial runs)';
  root.querySelector('.ln-names').appendChild(bin);
  root.querySelectorAll('.ln-chip, .ln-bin').forEach(el => {{
    el.addEventListener('dragover', e => {{ e.preventDefault(); el.classList.add('over'); }});
    el.addEventListener('dragleave', () => el.classList.remove('over'));
    el.addEventListener('drop', e => {{ e.preventDefault(); el.classList.remove('over');
      if (dragged) {{ choice[dragged.id] = el.dataset.key; paint(dragged.card, dragged); dragged = null; sync(); }} }});
  }});
}})();
</script>'''
    pending = {}
    sync_box = widgets.Text(value='{}', layout=widgets.Layout(display='none'))
    sync_box.add_class(f'lnsync-{uid}')
    save = widgets.Button(description='💾 Save links', button_style='danger', layout=widgets.Layout(width='200px', height='40px'))
    out = widgets.Output()

    def on_change(change):
        try:
            pending.clear()
            pending.update(json.loads(change['new']))
        except ValueError:
            pass

    def on_save(_):
        current = load_assignments()
        linked = discarded = 0
        for item_id, target in pending.items():
            kind, fname = item_id.split(':', 1)
            folder = SUBMIT_DIR if kind == 'figure' else REFLECT_DIR
            path = os.path.join(folder, fname)
            if not os.path.exists(path):
                continue
            if target == 'DISCARD':
                dest = os.path.join(DISCARD_DIR, kind + 's')
                os.makedirs(dest, exist_ok=True)
                for f in (path, path[:-5] + '.png'):
                    if os.path.exists(f):
                        shutil.move(f, os.path.join(dest, os.path.basename(f)))
                discarded += 1
                continue
            student = current.where('user_key', target)
            if student.num_rows != 1:
                continue
            with open(path) as f:
                r = json.load(f)
            first, initial = student.column('first_name').item(0), student.column('last_initial').item(0)
            r.update({'user_key': target, 'section': student.column('section').item(0), 'first_name': first,
                      'name': f'{first} {initial}.', 'linked_by_instructor': True})
            with open(path, 'w') as f:
                json.dump(r, f, indent=1)
            linked += 1
        with out:
            out.clear_output()
            print(f'Saved: {_plural(linked, "item")} linked, {_plural(discarded, "item")} discarded '
                  f'(discarded files are kept in {DISCARD_DIR}). Run who_submitted() to see the result.')

    sync_box.observe(on_change, names='value')
    save.on_click(on_save)
    display(HTML(board))
    display(widgets.VBox([sync_box, save, out]))
