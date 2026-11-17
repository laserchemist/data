"""
group_project.py — Group Project teams: the team wheel, live team board, and one-project-per-team choice.

Lives next to class_games.py in the course repo at 'Fall 2026/shared-public/' (delivered by nbgitpuller).
Everything is saved in the hub folder every student can write:

    /home/jovyan/shared-public/group_project/<TERM>/
        sections/01.json                  the team names for class 01, and whether the wheel / projects are open
        members/<player>.json             one small file per student: name, section, team
        claims/01__<dataset>.json         one file per claimed dataset (so two teams can never hold the same one)
        picks/01__<team>.json             one file per team that has chosen (so a team can never hold two)
        messages/01__<team>/<time>__<player>.json   one file per team message
        teams/01/<team>.json              each team's sheet: members, roles, project and messages
        _archive/                         where reset_section() moves a class's files; nothing is deleted

One file per student and per claim, so students spinning at the same moment never overwrite each other.

Students:   team_sign_in()   team_spin()   team_page()   team_choose_project()   team_choose_role()   team_messages()
Instructor: set_teams('01', Groups)   teams_board('01')   open_projects('01')   close_teams('01')
            move_student(...)   add_student(...)   remove_student(...)   assign_project(...)   release_project(...)
            show_messages('01')   remove_message(...)   save_teams('01')   export_teams_html('01')   reset_section('01')
Recovery:   find_saved()   restore_section('01')   place_students('01', from_section='08')
Roster:     roster_check('01')   roster_review('01')   missing_students('01', link=...)   open_teams_for_missing('01')
            match_student('Sam T', 'tuv12345')   rename_student('sammy', 'Sam T')   canvas_groups('01')
            (these read the class roster class_01.csv from the notebook's folder)
"""
import os, json, glob, time, datetime, shutil, html, csv, hashlib, re, unicodedata, difflib

import numpy as np

from class_games import _player, _slug, _live, _norm_section, uuid_hex, WHEEL_COLORS, CHERRY, GOLD

__all__ = ['team_sign_in', 'team_spin', 'team_page', 'team_choose_project', 'team_choose_role', 'team_messages',
           'show_messages', 'remove_message', 'load_messages', 'ROLES',
           'set_teams', 'teams_board', 'open_teams', 'close_teams', 'open_projects', 'close_projects',
           'move_student', 'add_student', 'remove_student', 'assign_project', 'release_project',
           'save_teams', 'save_team_sheets', 'team_sheet', 'reset_section', 'export_teams_html',
           'roster_check', 'roster_review', 'missing_students', 'open_teams_for_missing', 'match_student', 'rename_student',
           'canvas_groups', 'find_saved', 'restore_section', 'place_students',
           'load_members', 'load_claims', 'get_section', 'DATASETS', 'SECTIONS']

ROOT = os.environ.get('GROUP_PROJECT_ROOT', '/home/jovyan/shared-public/group_project')
TERM = 'Fall2026'
SECTIONS = ['01', '02', '03', '04', '05', '06', '07', '08']

# The project pulldown. Keep these labels the same as DATASETS in GroupProject_Submission.ipynb.
DATASETS = [
    'DS1  · Ecological Footprint by Country',
    'DS2  · Heart Disease',
    'DS3  · Periodic Table',
    'DS5  · Air Quality',
    'DS6  · East Coast Earthquakes',
    'DS7  · Pennypack Creek Stream Gauge',
    'DS8  · Philadelphia Weather Data',
    'DS9  · Fetal Health',
    'DS10 · Diabetes Prediction',
    'DS11 · Philly School Graduation Rates',
    'DS12 · Jeopardy Dataset',
    'DS14 · Global Sustainable Energy Production',
    'DS16 · Gene Expression in Cancer vs. Normal Tissue',
    'DS17 · Human Microbiome Diversity',
    'DS18 · Student Performance in Secondary Education',
    'DS20 · Protein Amino Acid Composition',
    'CAMELS · Hydrology Dataset',
]
PICK = '--- Select a dataset ---'

# The role pulldown. Keep these the same as ROLES in GroupProject_Submission.ipynb.
ROLES = ['Coder 1', 'Coder 2', 'Coder 3', 'Analyst', 'Context Expert', 'Writer', 'Project Manager', 'Visualizer']
NO_ROLE = '--- Select a role ---'
MESSAGE_LIMIT = 500          # characters in one team message


# ============================================================================ storage
def _dir(*parts):
    "ROOT/TERM/<parts>, created if needed and writable by every student."
    path = ROOT
    for part in ('', TERM) + parts:
        path = os.path.join(path, part) if part else path
        os.makedirs(path, exist_ok=True)
        try:
            os.chmod(path, 0o777)
        except PermissionError:
            pass
    return path


def _read(path):
    try:
        with open(path, encoding='utf-8') as f:
            rec = json.load(f)
        return rec if isinstance(rec, dict) else None
    except (OSError, ValueError):
        return None


def _write(path, rec):
    tmp = f'{path}.{os.getpid()}.tmp'
    with open(tmp, 'w', encoding='utf-8') as f:
        json.dump(rec, f, indent=1, ensure_ascii=False)
    os.replace(tmp, path)
    try:
        os.chmod(path, 0o666)
    except PermissionError:
        pass


def _now():
    return datetime.datetime.now().isoformat(timespec='seconds')


def _ns():
    "The notebook's variables (an empty dict outside a notebook)."
    try:
        from IPython import get_ipython
        return get_ipython().user_ns
    except AttributeError:
        return {}


def _box(big, small, color='#E0DDD6'):
    return (f'<div style="font-family:sans-serif;border:2px solid {color};border-radius:10px;padding:10px 14px;margin:6px 0;'
            f'max-width:760px"><div style="font-size:1.3em;font-weight:900">{big}</div>'
            f'<div style="color:#555;margin-top:3px">{small}</div></div>')


def _show(markup):
    from IPython.display import display, HTML
    display(HTML(markup))


# ---------------------------------------------------------------------------- sections
def get_section(section):
    "The saved setup for one class: {'teams': [...], 'teams_open': bool, 'projects_open': bool} (None if not set up)."
    return _read(os.path.join(_dir('sections'), f'{_norm_section(section)}.json'))


def _save_section(cfg):
    cfg['updated'] = _now()
    _write(os.path.join(_dir('sections'), f"{cfg['section']}.json"), cfg)


def set_teams(section, teams, n_teams=None):
    """Instructor: name the teams for one class, e.g. set_teams('01', Groups, n_teams=7) uses the first 7 names.
    Safe to run again: students already on a team stay there, and the open / closed settings are kept."""
    section = _norm_section(section)
    teams = [' '.join(str(t).split()) for t in teams if str(t).strip()][:n_teams]
    if len(teams) < 2 or len({t.lower() for t in teams}) < len(teams):
        print('Give at least two team names, all different. Nothing was changed.')
        return
    seated = {m['team'] for m in load_members(section)}
    gone = sorted(seated - set(teams))
    if gone:
        print(f'Students are already on: {", ".join(gone)}. Keep those names in the list (or move the students with '
              'move_student first). Nothing was changed.')
        return
    cfg = get_section(section) or {'section': section, 'teams_open': True, 'projects_open': False}
    cfg['teams'] = teams
    _save_section(cfg)
    for sub in ('members', 'claims'):
        _dir(sub)
    print(f'Class {section}: {len(teams)} teams · wheel {"OPEN" if cfg["teams_open"] else "CLOSED"} · '
          f'project choice {"OPEN" if cfg["projects_open"] else "CLOSED"}')
    print('   ' + ' · '.join(teams))


def _flag(section, key, value, said):
    cfg = get_section(section)
    if not cfg:
        print(f"Class {_norm_section(section)} has no teams yet: run set_teams('{_norm_section(section)}', Groups) first.")
        return
    cfg[key] = bool(value)
    _save_section(cfg)
    print(f'Class {cfg["section"]}: {said}')


def open_teams(section):
    "Instructor: let students spin onto a team (the wheel is open as soon as you set the teams)."
    cfg = get_section(section)
    if cfg and cfg.pop('allow', None) is not None:
        _save_section(cfg)
    _flag(section, 'teams_open', True, 'the wheel is OPEN. Students can spin.')


def close_teams(section):
    "Instructor: close the wheel. Students already on a team keep it; nobody new can spin."
    cfg = get_section(section)
    if cfg and cfg.pop('allow', None) is not None:      # also ends open_teams_for_missing
        _save_section(cfg)
    _flag(section, 'teams_open', False, 'the wheel is CLOSED to new students.')


def open_projects(section):
    "Instructor: once the teams have gathered, let them choose their project."
    _flag(section, 'projects_open', True, 'project choice is OPEN. Teams can claim a dataset.')


def close_projects(section):
    "Instructor: stop teams from choosing or changing projects."
    _flag(section, 'projects_open', False, 'project choice is CLOSED.')


# ---------------------------------------------------------------------------- members
def load_members(section=None):
    "Every student who has a team (in one class, or all classes), in the order they joined."
    out = []
    for p in glob.glob(os.path.join(ROOT, TERM, 'members', '*.json')):
        rec = _read(p)
        if rec and rec.get('team') and (section is None or rec.get('section') == _norm_section(section)):
            out.append(rec)
    return sorted(out, key=lambda r: (r.get('at', ''), r.get('name', '')))


def _member_path(player=None):
    return os.path.join(_dir('members'), f'{player or _player()}.json')


def _my_record():
    return _read(_member_path())


def _balanced_pick(section, teams):
    "A team picked at random from the teams with the fewest members so far."
    counts = {t: 0 for t in teams}
    for m in load_members(section):
        if m['team'] in counts:
            counts[m['team']] += 1
    fewest = min(counts.values())
    return str(np.random.choice([t for t in teams if counts[t] == fewest]))


# ---------------------------------------------------------------------------- project claims
def _claim_path(section, dataset):
    return os.path.join(_dir('claims'), f'{_norm_section(section)}__{_slug(dataset)}.json')


def load_claims(section):
    "dataset -> the claim record {'dataset', 'team', 'by', 'at'} for one class."
    out = {}
    for p in glob.glob(os.path.join(ROOT, TERM, 'claims', f'{_norm_section(section)}__*.json')):
        rec = _read(p)
        if rec is None:                                 # caught mid-write: look once more
            time.sleep(0.05)
            rec = _read(p)
        if rec and rec.get('dataset'):
            out[rec['dataset']] = rec
    return out


def _team_claim(section, team):
    "The team's project claim, or None."
    mine = sorted((c for c in load_claims(section).values() if c.get('team') == team),
                  key=lambda c: (c.get('at', ''), c['dataset']))
    return mine[0] if mine else None


def _pick_path(section, team):
    return os.path.join(_dir('picks'), f'{_norm_section(section)}__{_slug(team)}.json')


def _create(path, rec):
    "Write a new file in one all-or-nothing step. False if the file already exists (someone else got there first)."
    tmp = f'{path}.{os.getpid()}.{uuid_hex()}.tmp'
    with open(tmp, 'w', encoding='utf-8') as f:
        json.dump(rec, f, indent=1, ensure_ascii=False)
    try:
        os.link(tmp, path)
        os.chmod(path, 0o666)
        return True
    except FileExistsError:
        return False
    finally:
        os.remove(tmp)


def _claim(section, team, dataset, by):
    """Claim a dataset for a team. Returns (True, record) or (False, why).
    Two files are each created in a step that fails if the file already exists: the team's pick (so a team
    holds one project, even if two teammates click at once) and the dataset's claim (so a dataset goes to one team)."""
    section = _norm_section(section)
    have = _team_claim(section, team)
    if have:
        return (True, have) if have['dataset'] == dataset else (False, f'Your team already has {have["dataset"]}.')
    rec = {'dataset': dataset, 'team': team, 'section': section, 'by': by, 'at': _now()}
    pick = _pick_path(section, team)
    if not _create(pick, rec):
        try:
            stale = time.time() - os.path.getmtime(pick) > 10      # a pick left behind with no claim
        except OSError:
            stale = True
        if not stale:
            return False, 'A teammate is claiming a project right now. Click Refresh to see it.'
        try:
            os.remove(pick)
        except OSError:
            pass
        if not _create(pick, rec):
            return False, 'A teammate is claiming a project right now. Click Refresh to see it.'
    if not _create(_claim_path(section, dataset), rec):
        os.remove(pick)
        other = (_read(_claim_path(section, dataset)) or {}).get('team', 'Another team')
        return False, f'{other} just claimed {dataset}. Pick another one.'
    return True, rec


def _release(section, team):
    had = _team_claim(section, team)
    for path in ([_claim_path(section, had['dataset'])] if had else []) + [_pick_path(section, team)]:
        try:
            os.remove(path)
        except OSError:
            pass
    return had


# ---------------------------------------------------------------------------- game scores
def _game_lines(section):
    "team -> a short text of the team's challenge scores (Fix the Bug, P-value Poker, ...); {} if no games were played."
    try:
        import team_challenges
        return team_challenges.team_scores(section)
    except Exception:                                   # the challenges are optional extras: never break a board
        return {}


# ---------------------------------------------------------------------------- team sheets
def _messages_dir(section, team):
    return _dir('messages', f'{_norm_section(section)}__{_slug(team)}')


def load_messages(section, team):
    "A team's messages, oldest first: [{'name', 'text', 'at', 'file'}, ...]."
    out = []
    for p in sorted(glob.glob(os.path.join(ROOT, TERM, 'messages', f'{_norm_section(section)}__{_slug(team)}', '*.json'))):
        rec = _read(p)
        if rec and rec.get('text'):
            out.append(dict(rec, file=os.path.basename(p)))
    return out


def _post_message(section, team, name, text, player=None):
    text = str(text).strip()[:MESSAGE_LIMIT]
    if not text:
        return None
    rec = {'name': name, 'text': text, 'at': _now(), 'player': player or _player()}
    _write(os.path.join(_messages_dir(section, team), f'{time.time_ns()}__{rec["player"]}.json'), rec)
    return rec


def team_sheet(section, team):
    "One team's sheet, built from the saved files: members and their roles, the project, and the team's messages."
    section = _norm_section(section)
    claim = _team_claim(section, team)
    return {'term': TERM, 'section': section, 'team': team,
            'members': [{'name': m.get('name', ''), 'role': m.get('role', ''), 'joined': m.get('at', '')}
                        for m in load_members(section) if m['team'] == team],
            'project': ({'dataset': claim['dataset'], 'chosen_by': claim.get('by', ''), 'at': claim.get('at', '')}
                        if claim else None),
            'messages': [{'name': m.get('name', ''), 'text': m['text'], 'at': m.get('at', '')}
                         for m in load_messages(section, team)],
            'proposal': _proposal(section, team)}


def _proposal(section, team):
    "The team's proposal summary, from proposals.py (None if not started, or if that module is not there)."
    try:
        import proposals
        return proposals.proposal_summary(section, team)
    except Exception:
        return None


def save_team_sheets(section, quiet=True):
    """Write each team's sheet to shared-public/group_project/<TERM>/teams/<section>/<team>.json.
    The live board does this by itself on every refresh; a sheet is rewritten only when it has changed."""
    section = _norm_section(section)
    cfg = get_section(section)
    if not cfg:
        return []
    folder, written = _dir('teams', section), []
    for team in cfg['teams']:
        sheet = team_sheet(section, team)
        path = os.path.join(folder, f'{_slug(team)}.json')
        old = _read(path) or {}
        for key in old:                                  # keep any fields added later (notes, messages, ...)
            sheet.setdefault(key, old[key])
        if {k: v for k, v in old.items() if k != 'updated'} != sheet:
            _write(path, dict(sheet, updated=_now()))
        written.append(path)
    if not quiet:
        print(f'Class {section}: {len(written)} team sheets in {folder}')
    return written


# ============================================================================ student side
_W = {}           # the sign-in widgets, made once so re-running a cell keeps what was typed


def team_sign_in():
    "Student: a box for your name and a pulldown for your class section. Run this before team_spin()."
    import ipywidgets as widgets
    from IPython.display import display
    rec = _my_record() or {}
    if 'name' not in _W:
        _W['name'] = widgets.Text(value=rec.get('name', ''), description='📛 Your name:', placeholder='First name, last initial',
                                  style={'description_width': '130px'}, layout=widgets.Layout(width='420px'))
        _W['section'] = widgets.Dropdown(options=['--'] + SECTIONS, value=rec.get('section', '--'),
                                         description='🏫 Section:', style={'description_width': '130px'},
                                         layout=widgets.Layout(width='240px'))
    note = (f'✅ You are on <b>{html.escape(rec["team"])}</b> (section {rec["section"]}). Run the next cell to see your wheel.'
            if rec.get('team') else '⬇️ Fill in both, then run the next cell to spin.')
    display(widgets.VBox([_W['name'], _W['section'],
                          widgets.HTML(f'<div style="color:#555;font-size:13px;margin-top:4px">{note}</div>')]))


def team_spin():
    """Student: spin the wheel to join a team in your section. The team is picked at random from the teams with
    the fewest members so far (so the teams stay about equal) and saved; spinning again lands on the same team.
    Sets team_name and team_section in the notebook."""
    rec = _my_record()
    if 'name' not in _W and not rec:
        _show(_box('⚠️ Run the sign-in cell above first.', 'Type your name, pick your section, then run this cell again.', CHERRY))
        return
    name = ' '.join(_W['name'].value.split())[:40] if 'name' in _W else rec['name']
    section = _W['section'].value if 'section' in _W else rec['section']
    note = ''
    if rec and rec.get('team'):                         # already on a team: that is where the wheel lands
        if section not in ('--', rec['section']):
            note = (f'You already spun in section {rec["section"]}, so you stay on that team. '
                    f'If {rec["section"]} is the wrong section, ask your instructor to move you.')
        section = rec['section']
        name = name or rec.get('name', '')
    if not name:
        _show(_box('⚠️ Type your name in the box above.', 'Then run this cell again.', CHERRY))
        return
    if section == '--':
        _show(_box('⚠️ Pick your section from the pulldown above.', 'Then run this cell again.', CHERRY))
        return
    cfg = get_section(section)
    if not cfg or not cfg.get('teams'):
        _show(_box(f'⏳ The teams for section {section} are not set up yet.',
                   'Check that you picked the right section. If you did, wait for your instructor, then run this cell again.'))
        return
    teams = cfg['teams']
    already = bool(rec and rec.get('team') in teams)
    if not already:
        if not cfg.get('teams_open', True) and _player() not in cfg.get('allow', []):
            _show(_box('🔒 The wheel is closed.', 'Ask your instructor to let you in, then run this cell again.'))
            return
        rec = {'player': _player(), 'name': name, 'section': section, 'team': _balanced_pick(section, teams), 'at': _now()}
        _write(_member_path(), rec)
    elif name != rec.get('name'):                       # keep the name current
        rec['name'] = name
        _write(_member_path(), rec)
    ns = _ns()
    ns['team_name'], ns['team_section'] = rec['team'], section
    _show(_wheel_html(teams, teams.index(rec['team']), f'{name} · section {section}', already, note))


def _team_card(section, team, me=None):
    sheet = team_sheet(section, team)
    cfg = get_section(section) or {'teams': [team]}
    color = WHEEL_COLORS[cfg['teams'].index(team) % len(WHEEL_COLORS)] if team in cfg['teams'] else CHERRY
    chips = ''.join(f'<span style="display:inline-block;background:#F7F5F0;border-radius:14px;padding:4px 12px;margin:3px 4px 0 0;'
                    f'font-size:15px;{"font-weight:800;border:2px solid " + color if m["name"] == me else ""}">'
                    f'{html.escape(m["name"])}'
                    + (f' <span style="color:#888;font-weight:400;font-size:12px">· {html.escape(m["role"])}</span>' if m['role'] else '')
                    + '</span>' for m in sorted(sheet['members'], key=lambda m: m['name'].lower()))
    proj = sheet['project']
    games = _game_lines(section).get(team, '')
    line = (f'📂 <b>{html.escape(proj["dataset"])}</b> <span style="color:#888;font-size:12px">· chosen by '
            f'{html.escape(proj["chosen_by"])}</span>' if proj else '<span style="color:#999">📂 No project chosen yet</span>')
    return (f'<div style="font-family:sans-serif;max-width:760px;background:#fff;border:3px solid {color};border-radius:12px;'
            f'overflow:hidden"><div style="background:{color};color:#fff;padding:9px 14px;font-weight:900;font-size:19px">'
            f'{html.escape(team)}<span style="float:right;font-size:14px;font-weight:600;margin-top:3px">section {section} · '
            f'{len(sheet["members"])} member{"s" if len(sheet["members"]) != 1 else ""}</span></div>'
            f'<div style="padding:8px 12px">{chips or "<i style=color:#aaa>no members yet</i>"}'
            f'<div style="border-top:1px solid #F0EDE8;margin-top:10px;padding-top:8px;font-size:15px">{line}</div>'
            + (f'<div style="margin-top:5px;font-size:11px;color:#999">🎮 {html.escape(games)}</div>' if games else '')
            + '</div></div>')


def _need_team():
    rec = _my_record()
    if not rec or not rec.get('team'):
        _show(_box('🎡 You are not on a team yet.', 'Run the sign-in and spin cells above first.', CHERRY))
        return None
    _ns()['team_name'], _ns()['team_section'] = rec['team'], rec['section']
    return rec


def team_page():
    "Student: your team's sheet — who is on it, and the project it chose. Run it again to see new teammates."
    rec = _need_team()
    if rec:
        _show(_team_card(rec['section'], rec['team'], rec.get('name'))
              + '<div style="font-family:sans-serif;color:#888;font-size:12px;margin-top:4px">'
                'Run this cell again to see teammates who joined after you.</div>')


def team_choose_project():
    """Student: choose your team's project from the datasets no other team in your class has taken.
    One teammate clicks Claim; everyone on the team then sees the same project. Sets team_dataset in the notebook."""
    import ipywidgets as widgets
    from IPython.display import display, HTML, clear_output
    rec = _need_team()
    if not rec:
        return
    section, team, name = rec['section'], rec['team'], rec.get('name', '')
    card, status = widgets.HTML(), widgets.HTML()
    pick = widgets.Dropdown(options=[PICK], description='📂 Dataset:', style={'description_width': '90px'},
                            layout=widgets.Layout(width='520px'))
    claim = widgets.Button(description='✅ Claim for our team', layout=widgets.Layout(width='200px', height='36px'),
                           style={'button_color': CHERRY, 'text_color': 'white', 'font_weight': 'bold'})
    again = widgets.Button(description='🔄 Refresh', layout=widgets.Layout(width='110px', height='36px'))
    sure = widgets.Checkbox(value=False, description='Our whole team agrees to give up this project', indent=False,
                            layout=widgets.Layout(width='340px'))
    release = widgets.Button(description='↩️ Release it', layout=widgets.Layout(width='130px', height='32px'))
    out = widgets.Output()
    choosing = widgets.HBox([pick, claim], layout=widgets.Layout(gap='10px', align_items='center'))
    changing = widgets.HBox([sure, release], layout=widgets.Layout(gap='10px', align_items='center'))

    def refresh(_=None):
        cfg = get_section(section) or {}
        claims = load_claims(section)
        mine = _team_claim(section, team)
        _ns()['team_dataset'] = mine['dataset'] if mine else None
        card.value = _team_card(section, team, name)
        is_open = cfg.get('projects_open', False)
        free = [d for d in DATASETS if d not in claims]
        keep = pick.value
        pick.options = [PICK] + free
        pick.value = keep if keep in free else PICK
        choosing.layout.display = 'flex' if is_open and not mine else 'none'
        changing.layout.display = 'flex' if is_open and mine else 'none'
        taken = ''.join(f'<li>{html.escape(d)} — <b>{html.escape(c.get("team", "?"))}</b></li>'
                        for d, c in sorted(claims.items(), key=lambda kv: DATASETS.index(kv[0]) if kv[0] in DATASETS else 99)
                        if c.get('team') != team)
        taken = (f'<div style="color:#666;font-size:13px;margin-top:6px">Already taken in section {section}:'
                 f'<ul style="margin:2px 0">{taken}</ul></div>' if taken else '')
        if mine:
            head = f'🎉 Your team\'s project is <b>{html.escape(mine["dataset"])}</b>.'
        elif not is_open:
            head = ('⏳ Project choice is not open yet. Meet your team and look through <b>Group_Project_Datasets</b> '
                    'together; when your instructor opens it, click Refresh.')
        else:
            head = (f'Decide <b>as a team</b>, then one of you claims it. {len(free)} of {len(DATASETS)} datasets are '
                    'still free; each one can go to only one team in your class.')
        status.value = f'<div style="font-family:sans-serif;font-size:15px;margin:8px 0 4px;max-width:760px">{head}{taken}</div>'

    def say(text, good=True):
        with out:
            clear_output(wait=True)
            display(HTML(f'<div style="font-family:sans-serif;font-weight:bold;padding:4px 0;'
                         f'color:{"#2E7D50" if good else CHERRY}">{text}</div>'))

    def on_claim(_):
        if pick.value == PICK:
            say('⚠️ Pick a dataset from the pulldown first.', False)
        elif not (get_section(section) or {}).get('projects_open'):
            say('⏳ Project choice is not open.', False)
        else:
            ok, result = _claim(section, team, pick.value, name)
            say(f'✅ {html.escape(result["dataset"])} is now {html.escape(team)}\'s project!' if ok
                else f'⚠️ {html.escape(result)}', ok)
        refresh()

    def on_release(_):
        if not sure.value:
            say('⚠️ Tick the box first: releasing lets another team take this dataset.', False)
            return
        if not (get_section(section) or {}).get('projects_open'):
            say('⏳ Project choice is closed, so the project can\'t be changed. Ask your instructor.', False)
            return
        had = _release(section, team)
        sure.value = False
        say(f'↩️ Released {html.escape(had["dataset"])}. Choose your new project.' if had else 'Nothing to release.')
        refresh()

    claim.on_click(on_claim)
    again.on_click(refresh)
    release.on_click(on_release)
    refresh()
    display(widgets.VBox([card, status, choosing, changing, again, out]))


def team_choose_role():
    """Student: choose your own role on the team, once the team has its project. Each teammate does this in their
    own notebook; choose again any time to change it. Sets team_role in the notebook."""
    import ipywidgets as widgets
    from IPython.display import display, HTML, clear_output
    rec = _need_team()
    if not rec:
        return
    section, team = rec['section'], rec['team']
    card, status = widgets.HTML(), widgets.HTML()
    pick = widgets.Dropdown(options=[NO_ROLE] + ROLES, value=rec.get('role') if rec.get('role') in ROLES else NO_ROLE,
                            description='🎭 My role:', style={'description_width': '90px'}, layout=widgets.Layout(width='340px'))
    save = widgets.Button(description='✅ Save my role', layout=widgets.Layout(width='160px', height='36px'),
                          style={'button_color': CHERRY, 'text_color': 'white', 'font_weight': 'bold'})
    again = widgets.Button(description='🔄 Refresh', layout=widgets.Layout(width='110px', height='36px'))
    out = widgets.Output()
    choosing = widgets.HBox([pick, save], layout=widgets.Layout(gap='10px', align_items='center'))

    def refresh(_=None):
        me = _my_record() or rec
        _ns()['team_role'] = me.get('role') or None
        card.value = _team_card(section, team, me.get('name'))
        ready = _team_claim(section, team) is not None
        choosing.layout.display = 'flex' if ready else 'none'
        held = {}
        for m in load_members(section):
            if m['team'] == team and m.get('role') and m.get('player') != me.get('player'):
                held.setdefault(m['role'], []).append(m.get('name', '?'))
        free = [r for r in ROLES if r not in held and r != me.get('role')]
        if not ready:
            head = '⏳ Your team chooses its project first (Step 4). Then click Refresh.'
        else:
            head = (f'Your role: <b>{html.escape(me["role"])}</b>. ' if me.get('role') else 'Talk it over, then pick your role. ') \
                   + ('Roles nobody on your team has yet: ' + ', '.join(free) + '.' if free else 'Every role is covered.') \
                   + ' Two teammates can share a role if your team is larger than the list.'
        status.value = f'<div style="font-family:sans-serif;font-size:15px;margin:8px 0 4px;max-width:760px">{head}</div>'

    def on_save(_):
        with out:
            clear_output(wait=True)
            me = _my_record()
            if pick.value == NO_ROLE or not me:
                display(HTML(f'<b style="color:{CHERRY}">⚠️ Pick a role from the pulldown first.</b>'))
            else:
                me['role'] = pick.value
                _write(_member_path(), me)
                display(HTML(f'<b style="color:#2E7D50">✅ Saved: {html.escape(me.get("name", ""))} · {pick.value}</b>'))
        refresh()

    save.on_click(on_save)
    again.on_click(refresh)
    refresh()
    display(widgets.VBox([card, status, choosing, again, out]))


def _messages_html(section, team, me=None, limit=30):
    msgs = load_messages(section, team)
    rows = ''.join(
        f'<div style="padding:6px 10px;margin:4px 0;border-radius:10px;background:{"#FDF3D7" if m.get("player") == me else "#F7F5F0"}">'
        f'<b>{html.escape(m.get("name", "?"))}</b> <span style="color:#999;font-size:11px">'
        f'{html.escape(m.get("at", "")[5:16].replace("T", " "))}</span><br>{html.escape(m["text"]).replace(chr(10), "<br>")}</div>'
        for m in msgs[-limit:])
    more = f'<div style="color:#999;font-size:12px">… {len(msgs) - limit} earlier messages</div>' if len(msgs) > limit else ''
    return (f'<div style="font-family:sans-serif;max-width:760px;border:1px solid #E0DDD6;border-radius:12px;overflow:hidden">'
            f'<div style="background:#2d0a16;color:#fff;padding:8px 14px;font-weight:800">💬 {html.escape(team)} · team messages'
            f'<span style="float:right;color:{GOLD};font-weight:600">{len(msgs)}</span></div>'
            f'<div style="padding:8px 10px;font-size:14px;max-height:340px;overflow-y:auto">{more}'
            f'{rows or "<i style=color:#aaa>No messages yet. Say hello to your team!</i>"}</div></div>')


def team_messages():
    """Student: your team's message board. Everyone on your team (and your instructor) can read what you post.
    Click Refresh to see new messages."""
    import ipywidgets as widgets
    from IPython.display import display, HTML, clear_output
    rec = _need_team()
    if not rec:
        return
    section, team = rec['section'], rec['team']
    view = widgets.HTML()
    box = widgets.Textarea(placeholder=f'Write a message to your team (up to {MESSAGE_LIMIT} characters): when to meet, who is doing what, a question…',
                           layout=widgets.Layout(width='760px', height='70px'))
    post = widgets.Button(description='📤 Post to my team', layout=widgets.Layout(width='180px', height='36px'),
                          style={'button_color': CHERRY, 'text_color': 'white', 'font_weight': 'bold'})
    again = widgets.Button(description='🔄 Refresh', layout=widgets.Layout(width='110px', height='36px'))
    out = widgets.Output()

    def refresh(_=None):
        view.value = _messages_html(section, team, _player())

    def on_post(_):
        with out:
            clear_output(wait=True)
            me = _my_record()
            if not me or me.get('team') != team:
                display(HTML(f'<b style="color:{CHERRY}">⚠️ Your team has changed: run this cell again.</b>'))
            elif not box.value.strip():
                display(HTML(f'<b style="color:{CHERRY}">⚠️ Type a message first.</b>'))
            else:
                _post_message(section, team, me.get('name', ''), box.value)
                box.value = ''
        refresh()

    post.on_click(on_post)
    again.on_click(refresh)
    refresh()
    display(widgets.VBox([view, box, widgets.HBox([post, again], layout=widgets.Layout(gap='10px')), out,
                          widgets.HTML('<div style="font-family:sans-serif;color:#888;font-size:12px">Keep it about the project. '
                                       'Your teammates and your instructor can read these messages.</div>')]))


# ---------------------------------------------------------------------------- the wheel
_WHEEL = r"""
<div id="gw-%%UID%%" style="font-family:'Segoe UI',Arial,sans-serif;max-width:780px;border:1px solid #e2e2e2;border-radius:14px;overflow:hidden">
  <div style="background:linear-gradient(135deg,#1a1a2e,#2d0a16);color:%%GOLD%%;padding:12px 20px;font-weight:900;font-size:20px;letter-spacing:1px">
    🎡 SPIN FOR YOUR PROJECT TEAM <span style="float:right;color:#fff;font-size:14px;font-weight:600;margin-top:4px" class="gw-who"></span></div>
  <div style="display:flex;flex-wrap:wrap;background:#fff">
    <div style="padding:18px;text-align:center;flex:0 0 auto">
      <div style="position:relative;display:inline-block">
        <div style="position:absolute;top:-6px;left:50%;transform:translateX(-50%);font-size:30px;color:#222;z-index:5;line-height:1">&#9660;</div>
        <canvas class="gw-canvas" width="420" height="420" style="display:block;border-radius:50%;border:1px solid #ddd"></canvas>
      </div>
      <div style="margin-top:12px"><button class="gw-btn" style="background:%%CHERRY%%;color:#fff;border:none;padding:11px 40px;font-size:17px;
        font-weight:800;border-radius:26px;cursor:pointer">Spin!</button></div>
    </div>
    <div style="flex:1;min-width:230px;padding:22px 20px;display:flex;flex-direction:column;justify-content:center">
      <div style="font-size:12px;color:#aaa;letter-spacing:2px;text-transform:uppercase">your team</div>
      <div class="gw-result" style="font-size:28px;font-weight:900;color:#ccc;margin:6px 0 10px">?</div>
      <div class="gw-note" style="color:#666;font-size:14px;line-height:1.4">Click <b>Spin!</b> to find out.</div>
      <div class="gw-extra" style="color:%%CHERRY%%;font-size:13px;line-height:1.4;margin-top:8px"></div>
    </div>
  </div>
</div>
<script>
(function () {
  var D = %%DATA%%;
  function init() {
    var root = document.getElementById('gw-%%UID%%');
    if (!root) { setTimeout(init, 80); return; }
    var canvas = root.querySelector('.gw-canvas'), ctx = canvas.getContext('2d');
    var n = D.teams.length, TWO = Math.PI * 2, slice = TWO / n, angle = 0, spinning = false;
    var cx = canvas.width / 2, cy = canvas.height / 2, R = cx - 6;
    root.querySelector('.gw-who').textContent = D.name;
    root.querySelector('.gw-extra').textContent = D.extra;
    function label(text) {                      /* shrink long team names until they fit their slice */
      var size = n <= 6 ? 17 : 15;
      do { ctx.font = '700 ' + size + 'px "Segoe UI",Arial,sans-serif'; size -= 1; }
      while (ctx.measureText(text).width > R - 46 && size >= 9);
      ctx.fillText(text, R - 12, 5);
    }
    function draw(a, win) {
      ctx.clearRect(0, 0, canvas.width, canvas.height);
      for (var i = 0; i < n; i++) {
        var s = -Math.PI / 2 + a + i * slice;
        ctx.beginPath(); ctx.moveTo(cx, cy); ctx.arc(cx, cy, R, s, s + slice); ctx.closePath();
        ctx.fillStyle = (win !== undefined && win !== i) ? '#d9d9d9' : D.colors[i]; ctx.fill();
        ctx.strokeStyle = '#fff'; ctx.lineWidth = 3; ctx.stroke();
        ctx.save(); ctx.translate(cx, cy); ctx.rotate(s + slice / 2); ctx.textAlign = 'right';
        ctx.fillStyle = '#fff'; label(D.teams[i]); ctx.restore();
      }
      ctx.beginPath(); ctx.arc(cx, cy, 20, 0, TWO); ctx.fillStyle = '#fff'; ctx.fill();
      ctx.strokeStyle = '#ccc'; ctx.lineWidth = 1; ctx.stroke();
    }
    function reveal() {
      draw(angle, D.target);
      var r = root.querySelector('.gw-result'); r.textContent = D.teams[D.target]; r.style.color = D.colors[D.target];
      root.querySelector('.gw-note').innerHTML = D.already
        ? 'You were already on this team. Spinning again always lands here.'
        : '🎉 Welcome to your team! Find your teammates, then run the next cells.';
    }
    function spin() {
      if (spinning) return; spinning = true;
      var btn = root.querySelector('.gw-btn'); btn.disabled = true; btn.style.opacity = '0.4';
      var goal = -((D.target + 0.5) * slice) + (Math.random() - 0.5) * slice * 0.5;
      while (goal <= angle) goal += TWO;
      goal += (6 + Math.floor(Math.random() * 3)) * TWO;
      var a0 = angle, dur = 4200, t0 = performance.now();
      function frame(t) {
        var p = Math.min((t - t0) / dur, 1);
        angle = a0 + (goal - a0) * (1 - Math.pow(1 - p, 5)); draw(angle);
        if (p < 1) { requestAnimationFrame(frame); return; }
        spinning = false; btn.style.display = 'none'; reveal();
      }
      requestAnimationFrame(frame);
    }
    draw(0); root.querySelector('.gw-btn').addEventListener('click', spin);
  }
  setTimeout(init, 50);
})();
</script>"""


def _wheel_html(teams, target, name, already, extra=''):
    data = (json.dumps({'teams': teams, 'target': target, 'colors': (WHEEL_COLORS * 3)[:len(teams)], 'name': name,
                        'already': already, 'extra': extra})
            .replace('<', '\\u003c').replace('>', '\\u003e').replace('&', '\\u0026'))
    return (_WHEEL.replace('%%UID%%', uuid_hex()).replace('%%DATA%%', data)
            .replace('%%GOLD%%', GOLD).replace('%%CHERRY%%', CHERRY))


# ============================================================================ instructor: live board
def _board_html(section):
    section = _norm_section(section)
    cfg = get_section(section)
    head = (f'<div style="background:linear-gradient(135deg,#1a1a2e 0%,#2d0a16 100%);padding:18px 24px;border-radius:12px;'
            f'margin-bottom:14px;font-family:system-ui,sans-serif"><div style="color:{GOLD};font-size:2em;font-weight:900;'
            f'letter-spacing:2px">🎡 GROUP PROJECT · TEAMS<span style="float:right;color:#fff;font-size:.6em;margin-top:10px">'
            f'Class {section}</span></div><div style="color:#ddd">@SUB@</div></div>')
    if not cfg:
        return head.replace('@SUB@', f"No teams yet for class {section}: run set_teams('{section}', Groups).")
    members, claims = load_members(section), load_claims(section)
    save_team_sheets(section)
    by_team = {t: [] for t in cfg['teams']}
    for m in members:
        by_team.setdefault(m['team'], []).append((m.get('name', '?'), m.get('role', '')))
    project = {c['team']: d for d, c in claims.items()}
    games = _game_lines(section)
    cards = ''
    for i, (team, names) in enumerate(by_team.items()):
        prop = _proposal(section, team)
        if prop:
            games = dict(games)
            games[team] = ' · '.join(x for x in [('📝 proposal submitted' if prop.get('status') == 'submitted'
                                                   else '📝 proposal draft'), games.get(team, '')] if x)
        color = WHEEL_COLORS[i % len(WHEEL_COLORS)]
        chips = ''.join(f'<div style="padding:4px 10px;border-radius:14px;background:#F7F5F0;margin:3px 0;font-size:15px">'
                        f'{html.escape(n)}'
                        + (f' <span style="color:#888;font-size:12px">· {html.escape(r)}</span>' if r else '') + '</div>'
                        for n, r in sorted(names, key=lambda x: x[0].lower()))
        n_msgs = len(load_messages(section, team))
        talk = f' <span style="float:right;color:#888;font-weight:400">💬 {n_msgs}</span>' if n_msgs else ''
        proj = (f'<div style="border-top:1px solid #F0EDE8;padding:7px 10px;font-size:13px;font-weight:700;color:{color}">'
                f'📂 {html.escape(project[team])}{talk}</div>' if team in project else
                f'<div style="border-top:1px solid #F0EDE8;padding:7px 10px;font-size:12px;color:#aaa">📂 no project yet{talk}</div>')
        cards += (f'<div style="min-width:0;background:#fff;border:3px solid {color};border-radius:12px;overflow:hidden">'
                  f'<div style="background:{color};color:#fff;padding:9px 12px;font-weight:900;font-size:17px">{html.escape(team)}'
                  f'<span style="float:right">{len(names)}</span></div><div style="padding:8px 10px">'
                  f'{chips or "<i style=color:#aaa>waiting for spins…</i>"}</div>{proj}'
                  + (f'<div style="padding:0 10px 6px;font-size:11px;color:#999">🎮 {html.escape(games[team])}</div>'
                     if games.get(team) else '') + '</div>')
    rows = ''.join(
        f'<tr style="border-top:1px solid #F0EDE8"><td style="padding:5px 12px;font-size:13px">{html.escape(d)}</td>'
        + (f'<td style="padding:5px 12px;font-size:13px;font-weight:700;color:{CHERRY}">{html.escape(claims[d]["team"])}</td>'
           if d in claims else '<td style="padding:5px 12px;font-size:13px;color:#2E7D50">available</td>') + '</tr>'
        for d in DATASETS + sorted(set(claims) - set(DATASETS)))
    table = (f'<div style="background:#fff;border:1px solid #E0DDD6;border-radius:10px;margin-top:14px;overflow:hidden;'
             f'font-family:system-ui,sans-serif"><div style="padding:9px 14px;background:#F7F5F0;font-weight:800">📂 Projects '
             f'<span style="font-weight:400;color:#888;font-size:12px">· one team per dataset · {len(claims)} of '
             f'{len(cfg["teams"])} teams have chosen</span></div><table style="width:100%;border-collapse:collapse">{rows}</table></div>')
    waiting = len(set(cfg.get('allow', [])) - {m['player'] for m in load_members()})
    sub = (f'{"🔓 wheel open" if cfg.get("teams_open", True) else f"🔓 wheel open for {waiting} missing" if waiting else "🔒 wheel closed"} · '
           f'{"🔓 project choice open" if cfg.get("projects_open") else "🔒 project choice closed"} · '
           f'{len(members)} student{"s" if len(members) != 1 else ""} on {len(cfg["teams"])} teams')
    return (head.replace('@SUB@', sub) + f'<div style="display:grid;grid-template-columns:repeat(auto-fit,minmax(180px,1fr));gap:10px;'
            f'align-items:start;font-family:system-ui,sans-serif">{cards}</div>' + table)


def teams_board(section, interval=8):
    """Instructor: the live board for one class — every team, who has spun onto it so far, and each team's project.
    It also keeps each team's sheet in shared-public up to date."""
    section = _norm_section(section)
    _live(lambda: _board_html(section), interval, f'Group Project Teams · class {section}',
          f'group_project_teams_{section}.html')


# ============================================================================ instructor: fixes
def _find(name, section=None):
    hits = [m for m in load_members(section) if m.get('name', '').strip().lower() == name.strip().lower()]
    if len(hits) != 1:
        where = f' in class {_norm_section(section)}' if section else ''
        print(f'{len(hits)} students named {name!r}{where}: add section=..., or use the exact name on the board.' if hits
              else f'Nobody named {name!r}{where} has spun yet.')
        return None
    return hits[0]


def move_student(name, team, section=None, to_section=None):
    """Instructor: move a student (by the name on the board) to another team, e.g. move_student('Priya S', 'Data Owls').
    to_section='03' also moves them to another class (for a student who picked the wrong section)."""
    rec = _find(name, section)
    if not rec:
        return
    target = _norm_section(to_section) or rec['section']
    cfg = get_section(target) or {}
    if team not in cfg.get('teams', []):
        print(f'Class {target} teams are:', ', '.join(cfg.get('teams', [])) or '(none yet)')
        return
    if team != rec['team']:
        rec.pop('role', None)                           # a new team: choose a role again
    rec.update(team=team, section=target, moved=_now())
    _write(_member_path(rec['player']), rec)
    print(f'Moved {rec["name"]} to {team} (class {target}). They should run their spin cell again.')


def add_student(name, section, team=None):
    "Instructor: put a student who can't spin (absent, no laptop) on a team; team=None picks a balanced random team."
    section = _norm_section(section)
    cfg = get_section(section)
    if not cfg:
        print(f"Class {section} has no teams yet.")
        return
    if team is not None and team not in cfg['teams']:
        print(f'Class {section} teams are:', ', '.join(cfg['teams']))
        return
    name = ' '.join(str(name).split())
    rec = {'player': f'manual-{section}-{_slug(name).lower()}', 'name': name, 'section': section,
           'team': team or _balanced_pick(section, cfg['teams']), 'at': _now(), 'manual': True}
    _write(_member_path(rec['player']), rec)
    print(f'Added {name} to {rec["team"]} (class {section}).')


def remove_student(name, section=None):
    "Instructor: take a student off their team (e.g. they dropped the course). They can spin again if the wheel is open."
    rec = _find(name, section)
    if rec:
        os.remove(_member_path(rec['player']))
        print(f'Removed {rec["name"]} from {rec["team"]} (class {rec["section"]}).')


def assign_project(section, team, dataset):
    "Instructor: give a team a dataset yourself (replaces the team's current choice). Works while choice is closed."
    section = _norm_section(section)
    cfg = get_section(section) or {}
    matches = [d for d in DATASETS if dataset.lower() in d.lower()]
    if team not in cfg.get('teams', []) or len(matches) != 1:
        print('Use a team from this class and a dataset label (or a unique part of one, e.g. "DS17").')
        return
    holder = load_claims(section).get(matches[0])
    if holder and holder['team'] != team:
        print(f'{matches[0]} already belongs to {holder["team"]}. release_project first if you mean to swap.')
        return
    _release(section, team)
    ok, result = _claim(section, team, matches[0], 'instructor')
    print(f'{team}: {matches[0]}' if ok else result)


def release_project(section, team):
    "Instructor: free a team's dataset so it (or another team) can choose again."
    had = _release(_norm_section(section), team)
    print(f'Released {had["dataset"]} from {team}.' if had else f'{team} has no project to release.')


def show_messages(section, team=None):
    "Instructor: read the team messages for one class (or one team). Each message is numbered for remove_message."
    section = _norm_section(section)
    cfg = get_section(section) or {'teams': []}
    parts = []
    for t in ([team] if team else cfg['teams']):
        msgs = load_messages(section, t)
        rows = ''.join(f'<div style="padding:3px 0"><span style="color:#999">#{i}</span> <b>{html.escape(m.get("name", "?"))}</b> '
                       f'<span style="color:#999;font-size:11px">{html.escape(m.get("at", "")[5:16].replace("T", " "))}</span> — '
                       f'{html.escape(m["text"])}</div>' for i, m in enumerate(msgs, start=1))
        parts.append(f'<div style="font-family:sans-serif;margin:8px 0"><div style="font-weight:800;color:{CHERRY}">'
                     f'💬 {html.escape(t)} · {len(msgs)}</div>{rows or "<i style=color:#aaa>no messages</i>"}</div>')
    _show(''.join(parts) or f'Class {section} has no teams yet.')


def remove_message(section, team, number):
    "Instructor: take down one message, by its # in show_messages. It is moved to the archive folder, not deleted."
    section = _norm_section(section)
    msgs = load_messages(section, team)
    if not 1 <= number <= len(msgs):
        print(f'{team} has {len(msgs)} messages; give a number from show_messages.')
        return
    m = msgs[number - 1]
    dest = _dir('_archive', 'removed_messages', f'{section}__{_slug(team)}')
    shutil.move(os.path.join(_messages_dir(section, team), m['file']), dest)
    print(f'Removed message #{number} by {m.get("name", "?")} from {team}.')


# ============================================================================ instructor: the class roster
EMAIL_DOMAIN = 'temple.edu'          # a student's email is their SIS Login ID @ this, unless the roster has an Email column
MASTER_ROSTER = 'master_roster.csv'  # every section in one file, with a Section column; used when it is in this folder
# The link students open to spin: it pulls the course folder and opens GroupProject_Teams on the hub
TEAMS_LINK = ('https://temple.2i2c.cloud/hub/user-redirect/git-pull?repo=https%3A%2F%2Fgithub.com%2Flaserchemist%2Fdata'
              '&urlpath=lab%2Ftree%2Fdata%2FFall%202026%2FGroup-project%2FGroupProject_Teams.ipynb&branch=main')


def _email_button(link, title='📋 Group Dashboard', sub='Teams & Project Assignments'):
    "A link styled as a button with inline styles only (a table cell), so it survives being pasted into an email."
    return (f'<table role="presentation" cellspacing="0" cellpadding="0" style="margin:14px 0"><tr>'
            f'<td style="background-color:{CHERRY};border-radius:8px;padding:12px 26px;text-align:center">'
            f'<a href="{html.escape(link, quote=True)}" target="_blank" style="color:#ffffff;text-decoration:none;'
            f'font-family:Arial,sans-serif;font-size:16px;font-weight:bold">{html.escape(title)}<br>'
            f'<span style="font-size:12px;font-weight:normal;color:#F3D9DE">{html.escape(sub)}</span></a></td></tr></table>')


def _section_of(value):
    "A roster's Section entry ('8', '008', 'SCTC 1013-008') as '08'; '' if it holds no number."
    found = re.findall(r'\d+', str(value))
    return f'{int(found[-1]) % 100:02d}' if found else ''


def _hash(login):
    "The scrambled id class_games gives a hub login (so a roster login can be matched to a spin)."
    return hashlib.sha256(('class-games:' + str(login).strip().lower()).encode()).hexdigest()[:10]


def _tokens(text):
    text = unicodedata.normalize('NFKD', str(text)).encode('ascii', 'ignore').decode().lower()
    return re.findall(r'[a-z]+', text)


def _read_roster(section, path=None, quiet=False, every=False):
    """The class roster as [{'full', 'first', 'last', 'login', 'email', 'sections', 'class', 'ids', 'file'}, ...].
    With no path it reads master_roster.csv from this folder, keeping only the rows whose Section is this class
    (every=True keeps all sections); if there is no master roster it reads class_<section>.csv. A roster needs a
    Student column ('Last, First') and a SIS Login ID column. path may be one file or a list of files.
    Returns None, with a message, if there is no usable roster."""
    section = _norm_section(section)
    if path is None:
        path = MASTER_ROSTER if os.path.exists(MASTER_ROSTER) else f'class_{section}.csv'
    paths = [path] if isinstance(path, str) else list(path)
    out, seen = [], set()
    for path in paths:
        if not os.path.exists(path):
            if not quiet:
                print(f'No roster file {path} in this folder. Put {MASTER_ROSTER} here (all sections, with Student, '
                      f'SIS Login ID and Section columns), or class_{section}.csv, or pass roster="your_file.csv".')
            return None
        with open(path, newline='', encoding='utf-8-sig') as f:
            rows = list(csv.DictReader(f))
        cols = {re.sub(r'[^a-z]', '', (c or '').lower()): c for c in (rows[0].keys() if rows else [])}
        name_col = cols.get('student') or cols.get('name') or cols.get('studentname')
        login_col = cols.get('sisloginid') or cols.get('loginid') or cols.get('login')
        if not name_col or not login_col:
            if not quiet:
                print(f'{path} needs a "Student" column and a "SIS Login ID" column; it has: '
                      f'{", ".join(c for c in cols.values() if c)}')
            return None
        master = os.path.basename(path) == MASTER_ROSTER
        if master and not cols.get('section'):
            if not quiet:
                print(f'{path} needs a "Section" column to tell the classes apart.')
            return None
        for r in rows:
            full, login = (r.get(name_col) or '').strip(), (r.get(login_col) or '').strip()
            if not full or not login or full.lower().startswith(('points possible', 'student, test', 'test student')):
                continue
            cls = _section_of(r.get(cols['section'], '')) if cols.get('section') else ''
            seen.add(cls)
            if master and not every and cls != section:
                continue
            last, _, first = full.partition(',')
            if not first:                                    # 'First Last'
                first, _, last = full.rpartition(' ')
            email = ((r.get(cols.get('email', '')) or '').strip() if cols.get('email') else '') or f'{login.lower()}@{EMAIL_DOMAIN}'
            # the hub login may be the bare login or the email: both scrambled ids are tried
            ids = list(dict.fromkeys([_hash(login), _hash(f'{login}@{EMAIL_DOMAIN}'), _hash(email)]))
            out.append({'full': full, 'first': first.strip(), 'last': last.strip(), 'login': login, 'email': email,
                        'sections': (r.get(cols.get('section', '')) or '').strip() if cols.get('section') else '',
                        'class': cls or section, 'ids': ids, 'player': ids[0],
                        'file': f'{path}, class {cls}' if master else path})
    if not out:
        if not quiet:
            print(f'{", ".join(paths)}: no students for class {section}.'
                  + (f' Its Section column has: {", ".join(sorted(x for x in seen if x)) or "no section numbers"}.' if seen else ''))
        return None
    # which form of login does this hub use? The one that matches the most spins (the email form, if none do yet)
    spun = {m['player'] for m in load_members()}
    hits = [sum(1 for st in out if len(st['ids']) > k and st['ids'][k] in spun) for k in range(2)]
    form = 0 if hits[0] > hits[1] else 1
    for st in out:
        st['player'] = st['ids'][min(form, len(st['ids']) - 1)]
    return sorted(out, key=lambda st: (st['last'].lower(), st['first'].lower()))


def _name_fit(typed, st):
    """How well a typed name ('Ada L', 'adal', 'Lovelace, Ada', 'Ada Lovelace') fits a roster student:
    0 no · 1 first name only, or only a middle initial · 2 first name + last initial · 3 first and last name."""
    toks = _tokens(typed)
    given, last = _tokens(st['first']), _tokens(st['last'])
    if not toks or not given:
        return 0

    def like(a, b):
        if a == b:
            return True
        if min(len(a), len(b)) < 3:
            return False
        return b.startswith(a) or a.startswith(b) or difflib.SequenceMatcher(None, a, b).ratio() >= 0.8

    if len(toks) > 1 and any(like(toks[0], l) for l in last) and any(like(t, g) for t in toks[1:] for g in given):
        toks = toks[1:] + toks[:1]                       # 'Lovelace Ada'
    first_ok = any(like(toks[0], g) for g in given)
    glued = next((g for g in given if len(g) >= 3 and toks[0].startswith(g) and 0 < len(toks[0]) - len(g) <= 2), None)   # 'adal'
    if not first_ok and glued:
        toks, first_ok = [glued, toks[0][len(glued):]] + toks[1:], True
    if not first_ok:                                     # goes by a middle name: 'Caleb' for 'Elissa C.'
        return 1 if len(toks) == 1 and any(len(g) == 1 and toks[0].startswith(g) for g in given[1:]) else 0
    rest = [t for t in toks[1:] if not any(like(t, g) for g in given)]
    if not rest:
        return 1
    joined = ''.join(last)
    if any(len(t) > 2 and (like(t, joined) or any(like(t, l) for l in last)) for t in rest):
        return 3
    if any(len(t) <= 2 and any(l.startswith(t) or l.startswith(t[0]) for l in last) for t in rest):
        return 2
    return 0                                             # a last name or initial that does not fit


def _roster_match(section, roster=None):
    """Line the roster up with the teams. Returns None without a roster, else a dict:
    'on'      [(student, member, how)]  on a team in this class; how = 'login' (hub login), 'checked' (you confirmed
                                        it) or 'name' (first name + last initial fit exactly one roster student)
    'other'   [(student, member)]       on the roster here, but spun in another class
    'review'  [(member, student or None)]   team members still unmatched; student = a weaker guess, if there is one
    'missing' [student]                 on the roster, on no team"""
    section = _norm_section(section)
    students = _read_roster(section, roster)
    if students is None:
        return None
    everyone = load_members()
    by_player = {m['player']: m for m in everyone}
    by_login = {str(m['login']).lower(): m for m in everyone if m.get('login')}
    on, other, free = [], [], []
    for st in students:
        m = by_login.get(st['login'].lower())
        how = 'checked'
        if m is None:
            m, how = next((by_player[i] for i in st['ids'] if i in by_player), None), 'login'
        if m is None:
            free.append(st)
        elif m['section'] == section:
            on.append((st, m, how))
        else:
            other.append((st, m))
    known = {id(m) for _, m, _ in on}
    loose = [m for m in everyone if m['section'] == section and id(m) not in known and m.get('roster') != 'none']
    guess = {}                                           # member -> (score, the one roster student that fits best)
    for m in loose:
        fits = sorted(((_name_fit(m.get('name', ''), st), i) for i, st in enumerate(free)), reverse=True)
        if fits and fits[0][0] and (len(fits) == 1 or fits[1][0] < fits[0][0]):
            guess[id(m)] = (fits[0][0], free[fits[0][1]])
    wanted = {}
    for score, st in guess.values():
        wanted[id(st)] = wanted.get(id(st), 0) + 1
    review, taken = [], set()
    for m in loose:
        score, st = guess.get(id(m), (0, None))
        if st is not None and score >= 2 and wanted[id(st)] == 1:
            on.append((st, m, 'name'))
            taken.add(id(st))
        else:
            review.append((m, st))
            if st is not None:
                taken.add(id(st))
    on.sort(key=lambda x: (x[0]['last'].lower(), x[0]['first'].lower()))
    return {'section': section, 'students': students, 'on': on, 'other': other, 'review': review,
            'missing': [st for st in free if id(st) not in taken],
            'left_out': [m for m in everyone if m['section'] == section and m.get('roster') == 'none']}


def _other_rosters(section, used):
    "Students on the other classes' rosters (the master roster, or other class_NN.csv files), to spot who belongs elsewhere."
    section = _norm_section(section)
    if os.path.exists(MASTER_ROSTER):
        return [st for st in (_read_roster(section, MASTER_ROSTER, quiet=True, every=True) or []) if st['class'] != section]
    out = []
    for f in sorted(glob.glob('class_[0-9]*.csv')):
        if f not in used:
            out += _read_roster(section, f, quiet=True) or []
    return out


def roster_check(section, roster=None):
    """Instructor: compare the class roster (class_<section>.csv in this folder) with the teams.
    Students are matched by hub login when that works, and otherwise by name: a first name plus last initial that
    fits exactly one roster student counts as a match. Shows who still needs a look, and who is missing.
    The roster is this class's rows of master_roster.csv (or class_<section>.csv if there is no master roster)."""
    r = _roster_match(section, roster)
    if r is None:
        return
    sec = r['section']
    td = 'padding:3px 10px;font-size:13px;border-top:1px solid #F0EDE8;vertical-align:top'

    def table(head, rows):
        return (f'<table style="border-collapse:collapse;margin:4px 0 12px"><tr>'
                + ''.join(f'<th style="padding:3px 10px;font-size:11px;color:#888;text-align:left">{h}</th>' for h in head) + '</tr>'
                + ''.join('<tr>' + ''.join(f'<td style="{td}">{c}</td>' for c in row) + '</tr>' for row in rows) + '</table>')

    def code(text):
        return f'<code style="background:#F7F5F0;padding:1px 5px;border-radius:4px">{html.escape(text)}</code>'

    e = html.escape
    by = {how: [(st, m) for st, m, h in r['on'] if h == how] for how in ('login', 'checked', 'name')}
    source = sorted({st['file'].split(',')[0] for st in r['students']})
    parts = [f'<div style="font-family:system-ui,sans-serif;max-width:980px"><div style="font-size:1.3em;font-weight:900;color:{CHERRY}">'
             f'📋 Roster check · class {sec}</div><div style="color:#555;margin-bottom:10px">{len(r["students"])} on the roster '
             f'({html.escape(", ".join(source))}) · '
             f'✅ {len(r["on"])} on a team ({len(by["login"])} by login, {len(by["checked"])} checked by you, {len(by["name"])} by name) · '
             f'🔶 {len(r["review"]) + len(r["other"])} to review · ❌ {len(r["missing"])} missing</div>']
    if by['name']:
        rows = [[f'<b>{e(m.get("name", "?"))}</b>', '→', e(st['full']), e(st['login']), e(m['team'])] for st, m in by['name']]
        parts.append('<details><summary style="cursor:pointer"><b>✅ Matched by name</b> (click to look them over). '
                     f'To confirm or correct any of them, use {code(f"roster_review({sec!r})")}.</summary>'
                     + table(['typed name', '', 'roster name', 'login', 'team'], rows) + '</details><div style="height:8px"></div>')
    if r['review']:
        others = _other_rosters(sec, {st['file'] for st in r['students']})
        rows = []
        for m, st in r['review']:
            name = m.get('name', '')
            if st:
                note = f'could be <b>{e(st["full"])}</b> (a weaker fit)'
            else:
                far = sorted(((_name_fit(name, o), o) for o in others), key=lambda x: -x[0])
                note = (f'not on this roster; fits <b>{e(far[0][1]["full"])}</b> on {e(far[0][1]["file"])}'
                        if far and far[0][0] >= 2 and (len(far) == 1 or far[1][0] < far[0][0]) else 'no one left on this roster fits')
            rows.append([f'<b>{e(name or "?")}</b>', e(m['team']), 'added by you' if m.get('manual') else '', note])
        parts.append(f'<b>🔶 On a team, not matched to this roster.</b> Settle these with {code(f"roster_review({sec!r})")}: '
                     'pick the roster student, or mark them as not on this roster.'
                     + table(['typed name', 'team', '', 'best guess'], rows))
    if r['other']:
        rows = [[e(st['full']), f'class {m["section"]} · {e(m["team"])}',
                 code(f"move_student({m.get('name', '')!r}, 'TEAM NAME', section={m['section']!r}, to_section={sec!r})")]
                for st, m in r['other']]
        parts.append(f'<b>🔶 On this roster, but they spun in another class.</b> Move them to a class {sec} team if that was a mistake:'
                     + table(['roster name', 'spun in', 'to fix'], rows))
    odd = [(st, m) for st, m in by['login'] + by['checked'] if _name_fit(m.get('name', ''), st) == 0]
    if odd:
        rows = [[f'<b>{e(m.get("name", "?"))}</b>', e(st['full']), e(m['team']),
                 code(f"rename_student({m.get('name', '')!r}, {(st['first'].split() or [''])[0] + ' ' + st['last'][:1]!r})")]
                for st, m in odd]
        parts.append('<b>✏️ Matched, but the typed name does not look like the roster name.</b> Rename if you want the '
                     'boards to show the real name:' + table(['typed name', 'roster name', 'team', 'to rename'], rows))
    if r['left_out']:
        parts.append(f'<div style="color:#777;font-size:13px;margin-bottom:8px">Marked "not on this roster": '
                     f'{e(", ".join(m.get("name", "?") for m in r["left_out"]))}</div>')
    if r['missing']:
        rows = [[e(st['full']), e(st['login']), e(st['email'])] for st in r['missing']]
        parts.append(f'<b>❌ Missing: on the roster, on no team.</b>' + table(['roster name', 'login', 'email'], rows)
                     + f'<div style="color:#555">Next: {code(f"missing_students({sec!r})")} for the email list, and '
                       f'{code(f"open_teams_for_missing({sec!r})")} to open the wheel for just these students.</div>')
    else:
        parts.append('<b>🎉 Nobody on the roster is missing.</b>')
    _show(''.join(parts) + '</div>')


def _link(rec, st):
    "Record that team member rec is roster student st."
    old = rec['player']
    rec['login'] = st['login']
    rec.pop('roster', None)
    if rec.get('manual'):                                # hand-added: re-key it so the student's own notebook finds the team
        rec['player'] = st['player']
        _write(_member_path(rec['player']), rec)
        if old != rec['player']:
            os.remove(_member_path(old))
    else:
        _write(_member_path(old), rec)


def roster_review(section, roster=None):
    """Instructor: a check-off list to match team members to the roster. Each row shows a typed name and the roster
    student it seems to be. Tick the rows that are right (confident ones start ticked), change the pulldown where the
    guess is wrong, choose 'not on this roster' for a student who belongs elsewhere, then click Save."""
    import ipywidgets as widgets
    from IPython.display import display
    r = _roster_match(section, roster)
    if r is None:
        return
    sec = r['section']
    rows = [(m, st, True) for st, m, how in r['on'] if how == 'name'] + [(m, st, False) for m, st in r['review']]
    if not rows:
        _show(_box(f'✅ Class {sec}: every team member is matched to the roster.', 'Nothing to review.'))
        return
    open_students = sorted([st for st, m, how in r['on'] if how == 'name'] + [st for _, st in r['review'] if st] + r['missing'],
                           key=lambda st: (st['last'].lower(), st['first'].lower()))
    NOT, NONE = '✖ not on this roster', '— choose —'
    label = {st['login']: f'{st["full"]} · {st["login"]}' for st in open_students}
    by_login = {st['login']: st for st in open_students}
    lines = []
    for m, st, sure in sorted(rows, key=lambda x: (not x[2], x[0].get('name', '').lower())):
        tick = widgets.Checkbox(value=sure, indent=False, layout=widgets.Layout(width='28px'))
        who = widgets.HTML(f'<div style="font-family:system-ui,sans-serif;font-size:14px"><b>{html.escape(m.get("name", "?"))}</b> '
                           f'<span style="color:#888;font-size:12px">· {html.escape(m["team"])}'
                           f'{" · added by you" if m.get("manual") else ""}</span></div>', layout=widgets.Layout(width='330px'))
        pick = widgets.Dropdown(options=[(NONE, NONE)] + [(v, k) for k, v in label.items()] + [(NOT, NOT)],
                                value=st['login'] if st else NONE, layout=widgets.Layout(width='380px'))
        lines.append((m, tick, pick, widgets.HBox([tick, who, widgets.HTML('→', layout=widgets.Layout(width='22px')), pick],
                                                  layout=widgets.Layout(align_items='center'))))
    save = widgets.Button(description='✅ Save the ticked rows', layout=widgets.Layout(width='220px', height='38px'),
                          style={'button_color': CHERRY, 'text_color': 'white', 'font_weight': 'bold'})
    said = widgets.HTML()

    def on_save(_):
        chosen = [(m, pick.value) for m, tick, pick, _ in lines if tick.value and pick.value != NONE]
        logins = [v for _, v in chosen if v != NOT]
        twice = sorted({label[v] for v in logins if logins.count(v) > 1})
        if twice:
            said.value = (f'<b style="color:{CHERRY}">⚠️ Chosen for more than one row: {html.escape("; ".join(twice))}. '
                          'Nothing was saved.</b>')
            return
        linked = left = 0
        for m, value in chosen:
            rec = _read(_member_path(m['player']))
            if not rec:
                continue
            if value == NOT:
                rec['roster'] = 'none'
                rec.pop('login', None)
                _write(_member_path(rec['player']), rec)
                left += 1
            else:
                _link(rec, by_login[value])
                linked += 1
        save.disabled = True
        said.value = (f'<b style="color:#2E7D50">✅ Saved: {linked} matched to the roster, {left} marked as not on this roster.</b> '
                      f'Run roster_check({sec!r}) again to see what is left.')

    save.on_click(on_save)
    n_sure = sum(1 for x in rows if x[2])
    head = widgets.HTML(f'<div style="font-family:system-ui,sans-serif;max-width:860px"><div style="font-size:1.2em;font-weight:900;'
                        f'color:{CHERRY}">☑️ Roster review · class {sec}</div><div style="color:#555;margin:2px 0 8px">'
                        f'{n_sure} confident name matches are ticked already; {len(rows) - n_sure} need your choice. Untick a row to leave '
                        f'it for later. Only ticked rows are saved.</div></div>')
    display(widgets.VBox([head] + [x[3] for x in lines] + [widgets.HBox([save, said], layout=widgets.Layout(align_items='center', gap='10px',
                                                                                                         margin='10px 0 0 0'))]))


def missing_students(section, link='', roster=None):
    """Instructor: the students on the roster who are on no team, with their emails and a message you can send.
    The message has a button that opens GroupProject_Teams on the hub (TEAMS_LINK; link=... uses another address).
    Saves the list as a CSV and the message as an HTML file."""
    r = _roster_match(section, roster)
    if r is None:
        return
    sec, missing = r['section'], r['missing']
    held = [st for _, st in r['review'] if st]
    if held:
        print(f'⚠️ Not listed because a team member might be them (settle these in roster_review({sec!r})): '
              + '; '.join(st['full'] for st in held))
    if not missing:
        print(f'🎉 Class {sec}: nobody on the roster is missing.')
        return
    path = f'group_project_teams_{sec}_missing.csv'
    with open(path, 'w', newline='', encoding='utf-8-sig') as f:
        w = csv.writer(f)
        w.writerow(['section', 'student', 'login', 'email'])
        w.writerows([sec, st['full'], st['login'], st['email']] for st in missing)
    names = ''.join(f'<tr><td style="padding:2px 10px">{html.escape(st["full"])}</td><td style="padding:2px 10px">'
                    f'{html.escape(st["email"])}</td></tr>' for st in missing)
    emails = '; '.join(st['email'] for st in missing)
    link = link or TEAMS_LINK
    subject = 'SCTC 1013 Group Project: please join your team'
    steps = ['Click the button. It opens the <b>GroupProject_Teams</b> notebook on the JupyterHub.',
             f'Run the Setup cell, type your name, and pick section <b>{sec}</b>.',
             'Run the spin cell and click <b>Spin!</b> The wheel puts you on a team.',
             'Run the next cells to see your teammates and your team\'s project, pick your role, and say hello on the '
             'team message board.']
    body = ('<div style="font-family:Arial,sans-serif;font-size:14px;color:#222222;line-height:1.5">'
            '<p>Hello,</p><p>Our group project teams are set, and you are not on one yet. Please join today:</p>'
            + _email_button(link)
            + '<ol>' + ''.join(f'<li>{x}</li>' for x in steps) + '</ol>'
            f'<p>If the button does not work, copy this link into your browser:<br>'
            f'<a href="{html.escape(link, quote=True)}" style="color:{CHERRY};word-break:break-all">{html.escape(link)}</a></p>'
            '<p>If the wheel says it is closed, reply to this email and I will let you in.</p><p>Thank you,</p></div>')
    plain = (f'Hello,\n\nOur group project teams are set, and you are not on one yet. Please join today:\n\n'
             f'  1. Open this link: {link}\n'
             f'  2. Run the Setup cell, type your name, and pick section {sec}.\n'
             f'  3. Run the spin cell and click Spin! The wheel puts you on a team.\n'
             f'  4. Run the next cells to see your teammates and your team\'s project, pick your role, '
             f'and say hello on the team message board.\n\n'
             f'If the wheel says it is closed, reply to this email and I will let you in.\n\nThank you,\n')
    page = f'group_project_teams_{sec}_missing_email.html'
    with open(page, 'w', encoding='utf-8') as f:
        f.write(f'<!DOCTYPE html><html><head><meta charset="utf-8"><title>{html.escape(subject)}</title></head><body>{body}</body></html>')
    pre = 'background:#F7F5F0;padding:8px 10px;border-radius:6px;white-space:pre-wrap'
    _show(f'<div style="font-family:system-ui,sans-serif;max-width:900px"><div style="font-size:1.2em;font-weight:900;color:{CHERRY}">'
          f'❌ Class {sec}: {len(missing)} student{"s" if len(missing) != 1 else ""} not on a team</div>'
          f'<table style="border-collapse:collapse;font-size:13px;margin:6px 0">{names}</table>'
          f'<div style="font-weight:700;margin-top:8px">Addresses (paste into BCC):</div>'
          f'<pre style="{pre}">{html.escape(emails)}</pre>'
          f'<div style="font-weight:700">Subject:</div><pre style="{pre}">{html.escape(subject)}</pre>'
          f'<div style="font-weight:700">Message — select everything inside the box, copy, and paste into your email '
          f'(the button and link come with it):</div>'
          f'<div style="border:2px dashed #C9C4BA;border-radius:8px;padding:6px 16px;margin:6px 0;background:#ffffff">{body}</div>'
          f'<details><summary style="cursor:pointer;color:#555">Plain-text version (no button)</summary>'
          f'<pre style="{pre}">{html.escape(plain)}</pre></details>'
          f'<div style="color:#555;margin-top:6px">💾 Saved {path} (the list) and {page} (the message: open it in a browser tab to '
          f'copy from there). 🔒 The list holds names and logins: keep it off GitHub.</div></div>')


def open_teams_for_missing(section, roster=None):
    """Instructor: open the wheel ONLY for the roster students who are on no team. Everyone else stays locked.
    Each of them lands on one of the smallest teams. close_teams(section) ends it."""
    r = _roster_match(section, roster)
    if r is None:
        return
    cfg = get_section(r['section'])
    if not cfg:
        print(f'Class {r["section"]} has no teams yet.')
        return
    cfg['allow'] = [i for st in r['missing'] for i in st['ids']]
    cfg['teams_open'] = False
    _save_section(cfg)
    print(f'Class {r["section"]}: the wheel is open for {len(r["missing"])} missing student(s) only:')
    print('   ' + ', '.join(st['full'] for st in r['missing']) if r['missing'] else '   (nobody is missing)')
    if not any(how == 'login' for _, _, how in r['on']):
        print('   ⚠️ No one in this class has been matched by hub login so far, so this lock may not recognise the missing '
              'students either. If one of them still sees "the wheel is closed", use open_teams while they spin, then '
              'close_teams, or put them on a team yourself with add_student.')
    print('   Everyone else stays locked. close_teams ends it.')


def match_student(name, login, section=None, roster=None):
    """Instructor: say which roster student a team member is, e.g. match_student('Sam T', 'tuv12345').
    (roster_review does the same for many students at once.)"""
    rec = _find(name, section)
    if not rec:
        return
    students = _read_roster(rec['section'], roster) or []
    st = next((x for x in students if x['login'].lower() == str(login).strip().lower()), None)
    if not st:
        print(f'{login!r} is not a login on the class {rec["section"]} roster.')
        return
    for i in st['ids']:
        theirs = _read(_member_path(i))
        if theirs and theirs.get('team') and theirs['player'] != rec['player']:
            print(f'{st["full"]} already spun as {theirs.get("name")!r} onto {theirs["team"]} (class {theirs["section"]}). '
                  f'Remove the extra entry: remove_student({name!r}) or remove_student({theirs.get("name")!r}).')
            return
    _link(rec, st)
    print(f'Matched {rec["name"]!r} ({rec["team"]}) to {st["full"]} · {st["login"]}.')


def rename_student(name, new_name, section=None):
    "Instructor: change the name shown for a student, e.g. rename_student('sammy', 'Sam T')."
    rec = _find(name, section)
    if rec:
        rec['name'] = ' '.join(str(new_name).split())[:40]
        _write(_member_path(rec['player']), rec)
        print(f'{name!r} is now shown as {rec["name"]!r} ({rec["team"]}, class {rec["section"]}).')


def canvas_groups(section, with_section=True, roster=None):
    """Instructor: write the CSV that creates these teams as Canvas groups: group_project_teams_<section>_canvas_groups.csv.
    In Canvas: People → + Group Set → name it, choose "I'll create groups later" → Save → Import → upload the file.
    with_section=True names the groups 'Data Owls (08)', so classes that share a Canvas course and team names stay apart."""
    r = _roster_match(section, roster)
    if r is None:
        return
    sec = r['section']
    rows = [[st['full'], '', '', st['login'], st['sections'], f'{m["team"]} ({sec})' if with_section else m['team']]
            for st, m, how in sorted(r['on'], key=lambda x: (x[1]['team'].lower(), x[0]['last'].lower()))]
    path = f'group_project_teams_{sec}_canvas_groups.csv'
    with open(path, 'w', newline='', encoding='utf-8') as f:
        w = csv.writer(f)
        w.writerow(['name', 'canvas_user_id', 'user_id', 'login_id', 'sections', 'group_name'])
        w.writerows(rows)
    by_name = sum(1 for _, _, how in r['on'] if how == 'name')
    print(f'💾 Saved {path}: {len(rows)} students in {len({row[-1] for row in rows})} groups.')
    if by_name:
        print(f'   {by_name} of them were matched by name only: look them over in roster_review({sec!r}) before importing.')
    if r['missing'] or r['review'] or r['other']:
        print(f'   ⚠️ Not in the file: {len(r["missing"])} missing, {len(r["review"])} unmatched team member(s), '
              f'{len(r["other"])} who spun in another class.')
    print('   In Canvas: People → + Group Set → name it → "I\'ll create groups later" → Save → Import → upload this file.')
    print('   🔒 It holds names and logins: keep it off GitHub.')


def place_students(section, from_section=None, names=None, roster=None):
    """Instructor: a board to put students on teams by hand: one row per student, with a pulldown of the class's teams.
    Rows come from the class roster (class_<section>.csv in this folder). For each student it shows where they are now:
    on a team in this class, on a team in another class (choosing a team here MOVES them, keeping their own login, so
    their notebook still finds their team), or on no team (choosing a team places them).
    from_section='08' also looks, by name, for roster students who spun in class 08 by mistake.
    names=['Ada L', 'Sam T'] uses a typed list instead of a roster (those students are added by hand).
    Set the class's teams first with set_teams. Only rows where you pick a team are changed."""
    import ipywidgets as widgets
    from IPython.display import display
    section = _norm_section(section)
    cfg = get_section(section)
    if not cfg or not cfg.get('teams'):
        print(f"Class {section} has no teams yet: run set_teams('{section}', Groups, n_teams=...) first.")
        return
    teams = cfg['teams']
    rows = []                                            # (label, where-now text, current team or None, member rec or None, student or None)
    if names:
        here = {m.get('name', '').lower(): m for m in load_members(section)}
        for n in names:
            n = ' '.join(str(n).split())
            m = here.get(n.lower())
            rows.append((n, f'on {m["team"]}' if m else 'not on a team', m['team'] if m else None, m, None))
    else:
        r = _roster_match(section, roster)
        if r is None:
            print(f"   Or give the names yourself: place_students('{section}', names=['Ada L', 'Sam T', ...]).")
            return
        placed = {id(st): (m, how) for st, m, how in r['on']}
        elsewhere = {id(st): m for st, m in r['other']}
        guess = {}
        if from_section:
            src = _norm_section(from_section)
            theirs = _read_roster(src, None, quiet=True)
            if theirs:                                   # skip the students who really belong to that class
                rm = _roster_match(src)
                own = {m['player'] for _, m, _ in rm['on']}
            else:
                own = set()
            pool = [m for m in load_members(src) if m['player'] not in own and not m.get('login')]
            used = set()
            for st in r['missing'] + [x for _, x in r['review'] if x]:
                fits = sorted(((_name_fit(m.get('name', ''), st), i) for i, m in enumerate(pool)), reverse=True)
                if fits and fits[0][0] >= 2 and (len(fits) == 1 or fits[1][0] < fits[0][0]) and fits[0][1] not in used:
                    guess[id(st)] = pool[fits[0][1]]
                    used.add(fits[0][1])
        for st in r['students']:
            if id(st) in placed:
                m, how = placed[id(st)]
                rows.append((st['full'], f'on {m["team"]}' + (' (matched by name)' if how == 'name' else ''), m['team'], m, st))
            elif id(st) in elsewhere:
                m = elsewhere[id(st)]
                rows.append((st['full'], f'in class {m["section"]} · {m["team"]}', None, m, st))
            elif id(st) in guess:
                m = guess[id(st)]
                rows.append((st['full'], f'in class {m["section"]} · {m["team"]} as "{m.get("name", "")}" (by name)', None, m, st))
            else:
                rows.append((st['full'], 'not on a team', None, None, st))
    KEEP = '— leave as is —'
    lines = []
    for label, where, current, m, st in rows:
        pick = widgets.Dropdown(options=[KEEP] + teams, value=KEEP, layout=widgets.Layout(width='260px'))
        color = '#2E7D50' if current else ('#B26A00' if m else CHERRY)
        text = widgets.HTML(f'<div style="font-family:system-ui,sans-serif;font-size:14px"><b>{html.escape(label)}</b> '
                            f'<span style="color:{color};font-size:12px">· {html.escape(where)}</span></div>',
                            layout=widgets.Layout(width='470px'))
        lines.append((pick, current, m, st, label, widgets.HBox([text, pick], layout=widgets.Layout(align_items='center'))))
    save = widgets.Button(description='✅ Save the teams I picked', layout=widgets.Layout(width='240px', height='38px'),
                          style={'button_color': CHERRY, 'text_color': 'white', 'font_weight': 'bold'})
    said = widgets.HTML()

    def short(st, label):
        return ((st['first'].split() or [''])[0] + ' ' + st['last'][:1]).strip() if st else label

    def on_save(_):
        moved = made = changed = 0
        for pick, current, m, st, label, _ in lines:
            team = pick.value
            if team == KEEP or team == current:
                continue
            rec = _read(_member_path(m['player'])) if m else None
            if rec:                                      # already saved somewhere: move them, keeping their own login
                if rec['section'] != section:
                    moved += 1
                else:
                    changed += 1
                rec.pop('role', None)
                rec.update(team=team, section=section, moved=_now())
                if st:
                    rec['login'] = st['login']
                    rec.pop('roster', None)
                _write(_member_path(rec['player']), rec)
            else:
                rec = {'player': st['player'] if st else f'manual-{section}-{_slug(label).lower()}', 'name': short(st, label),
                       'section': section, 'team': team, 'at': _now(), 'placed': True}
                if st:
                    rec['login'] = st['login']
                else:
                    rec['manual'] = True
                _write(_member_path(rec['player']), rec)
                made += 1
        save.disabled = True
        said.value = (f'<b style="color:#2E7D50">✅ Saved: {made} placed, {moved} moved from another class, {changed} changed team.</b> '
                      f'Run this cell again to see the result, or teams_board({section!r}).')

    save.on_click(on_save)
    n_none = sum(1 for x in rows if not x[3])
    n_else = sum(1 for x in rows if x[3] and not x[2])
    head = widgets.HTML(f'<div style="font-family:system-ui,sans-serif;max-width:860px"><div style="font-size:1.2em;font-weight:900;'
                        f'color:{CHERRY}">🧩 Place students · class {section}</div><div style="color:#555;margin:2px 0 8px">'
                        f'{len(rows)} students: <span style="color:#2E7D50">{len(rows) - n_none - n_else} on a team here</span> · '
                        f'<span style="color:#B26A00">{n_else} in another class</span> · <span style="color:{CHERRY}">{n_none} on no team</span>. '
                        f'Pick a team only for the students you want to place or move; the rest stay as they are.</div></div>')
    display(widgets.VBox([head] + [x[5] for x in lines] + [widgets.HBox([save, said], layout=widgets.Layout(align_items='center', gap='10px',
                                                                                                         margin='10px 0 0 0'))]))


# ============================================================================ instructor: what is saved, and getting it back
def find_saved():
    """Instructor: show everything that is saved, for every class: students by the day and time they spun, projects,
    and what has been archived by reset_section. Changes nothing."""
    base = os.path.join(ROOT, TERM)
    print(f'📁 {base}')
    terms = [d for d in sorted(os.listdir(ROOT)) if os.path.isdir(os.path.join(ROOT, d))] if os.path.isdir(ROOT) else []
    if len(terms) > 1:
        print(f'   (other folders here: {", ".join(t for t in terms if t != TERM)})')
    everyone = load_members()
    sections = sorted({m['section'] for m in everyone} | {os.path.basename(p)[:-5] for p in glob.glob(os.path.join(base, 'sections', '*.json'))})
    if not sections:
        print('   Nothing is saved here.')
    for sec in sections:
        mine = [m for m in everyone if m['section'] == sec]
        cfg = get_section(sec)
        n_prop = len(glob.glob(os.path.join(base, 'proposals', sec, '*.json')))
        print(f'\nClass {sec}: {len(mine)} students · {len(cfg["teams"]) if cfg else "no"} teams set · '
              f'{len(load_claims(sec))} projects chosen · {n_prop} proposals saved')
        days = {}
        for m in mine:
            days.setdefault(m.get('at', '')[:10], []).append(m.get('at', '')[11:16])
        for day in sorted(days):
            times = sorted(days[day])
            print(f'   spun {day}: {len(times):>3} students, {times[0]}–{times[-1]}')
    found = sorted(d for d in glob.glob(os.path.join(base, '_archive', '[0-9][0-9]_*')) if os.path.isdir(d))
    print('\n🗄️ Archived by reset_section:' if found else '\n🗄️ Nothing has been archived by reset_section.')
    for d in found:
        n = {k: len(glob.glob(os.path.join(d, k, '**', '*.json'), recursive=True)) for k in ('members', 'claims', 'messages')}
        sec = os.path.basename(d)[:2]
        print(f'   {os.path.basename(d)}: class {sec} · {n["members"]} students · {n["claims"]} projects · {n["messages"]} messages'
              + (f"   → restore_section('{sec}')" if n['members'] else ''))


def restore_section(section, archive=None):
    """Instructor: put back a class that reset_section archived: its students, roles, projects and messages.
    Uses the newest archive that holds students (or archive='01_20261112-101500'). Files that exist now are kept."""
    section = _norm_section(section)
    base = os.path.join(ROOT, TERM)
    if archive:
        chosen = os.path.join(base, '_archive', archive)
    else:
        having = [d for d in sorted(glob.glob(os.path.join(base, '_archive', f'{section}_*')))
                  if glob.glob(os.path.join(d, 'members', '*.json'))]
        chosen = having[-1] if having else ''
    if not chosen or not os.path.isdir(chosen):
        print(f'No archive with students was found for class {section}. Run find_saved() to see what there is.')
        return
    put, kept = 0, 0
    has_members = bool(load_members(section))
    for path in glob.glob(os.path.join(chosen, '**', '*.json'), recursive=True):
        rel = os.path.relpath(path, chosen)
        dest = os.path.join(base, rel)
        is_config = rel.startswith('sections' + os.sep)
        if os.path.exists(dest) and not (is_config and not has_members):
            kept += 1
            continue
        _dir(*os.path.dirname(rel).split(os.sep))
        shutil.copy2(path, dest)
        try:
            os.chmod(dest, 0o666)
        except OSError:
            pass
        put += 1
    print(f'Class {section}: restored {put} files from {os.path.basename(chosen)}'
          + (f' ({kept} already existed and were left as they are).' if kept else '.'))
    print(f'   Now: {len(load_members(section))} students, {len(load_claims(section))} projects chosen. The archive copy is still there.')


def save_teams(section):
    "Instructor: save one class's teams to group_project_teams_<section>_<date>.csv in this folder (names: keep it off GitHub)."
    section = _norm_section(section)
    project = {c['team']: d for d, c in load_claims(section).items()}
    path = f'group_project_teams_{section}_{datetime.date.today():%Y-%m-%d}.csv'
    with open(path, 'w', newline='', encoding='utf-8-sig') as f:
        w = csv.writer(f)
        w.writerow(['section', 'team', 'name', 'role', 'joined', 'project'])
        w.writerows(sorted([section, m['team'], m.get('name', ''), m.get('role', ''), m.get('at', '')[:16].replace('T', ' '),
                            project.get(m['team'], '')] for m in load_members(section)))
    print(f'💾 Saved {path}. 🔒 It holds students\' names: keep it off GitHub.')
    return path


def export_teams_html(section, title=None):
    """Instructor: save one class's teams as a small HTML file to paste into a Canvas page: every team with its
    members and roles, its project, and its game scores. Plain tables and simple inline styles only, because
    Canvas removes scripts, style sheets and fancier styling when a page is saved."""
    section = _norm_section(section)
    cfg = get_section(section)
    if not cfg:
        print(f'Class {section} has no teams yet.')
        return
    games = _game_lines(section)
    title = title or f'Group Project Teams · Section {section}'
    cell = 'border:1px solid #cccccc;padding:8px 10px;vertical-align:top;font-size:14px'
    rows = ''
    for i, team in enumerate(cfg['teams']):
        sheet = team_sheet(section, team)
        color = WHEEL_COLORS[i % len(WHEEL_COLORS)]
        people = '<br>'.join(
            html.escape(m['name']) + (f' <span style="color:#666666;font-size:12px">· {html.escape(m["role"])}</span>' if m['role'] else '')
            for m in sorted(sheet['members'], key=lambda m: m['name'].lower())) or '<em>no members yet</em>'
        project = html.escape(sheet['project']['dataset']) if sheet['project'] else '<em>not chosen yet</em>'
        if (sheet.get('proposal') or {}).get('title'):
            project = f'<b>{html.escape(sheet["proposal"]["title"])}</b><br>' + project
        small = (f'<br><span style="color:#777777;font-size:11px">🎮 {html.escape(games[team])}</span>' if games.get(team) else '')
        rows += (f'<tr><td style="{cell};background-color:{color};color:#ffffff;font-weight:bold;width:24%">{html.escape(team)}'
                 f'<br><span style="font-weight:normal;font-size:12px">{len(sheet["members"])} member'
                 f'{"s" if len(sheet["members"]) != 1 else ""}</span></td>'
                 f'<td style="{cell};width:40%">{people}</td><td style="{cell}">📂 {project}{small}</td></tr>\n')
    head = 'border:1px solid #cccccc;padding:6px 10px;background-color:#f2f2f2;text-align:left;font-size:13px'
    page = (f'<h3>{html.escape(title)}</h3>\n'
            f'<table style="border-collapse:collapse;width:100%">\n'
            f'<thead><tr><th style="{head}">Team</th><th style="{head}">Members and roles</th>'
            f'<th style="{head}">Project</th></tr></thead>\n<tbody>\n{rows}</tbody></table>\n'
            f'<p style="font-size:11px;color:#777777">Updated {datetime.datetime.now():%B %d, %Y at %H:%M}</p>\n')
    path = f'group_project_teams_{section}_canvas.html'
    with open(path, 'w', encoding='utf-8') as f:
        f.write(page)
    print(f'💾 Saved {path} ({len(cfg["teams"])} teams).')
    print('   In Canvas: edit the page → click  </>  (HTML editor) under the text box → paste the file\'s contents → Save.')
    print('   To copy it: right-click the file → Open With → Editor, then select all and copy.')
    print('   🔒 It holds students\' names: fine inside your Canvas course, but keep it off GitHub.')


def reset_section(section, confirm=''):
    """Instructor: clear one class's teams and project choices to start over, e.g. reset_section('01', confirm='01').
    Everything is moved to an archive folder; nothing is deleted."""
    section = _norm_section(section)
    if confirm != section:
        print(f"Nothing changed. To clear class {section}, run reset_section('{section}', confirm='{section}').")
        return
    base = os.path.join(ROOT, TERM)
    files = ([_member_path(m['player']) for m in load_members(section)]
             + glob.glob(os.path.join(base, 'claims', f'{section}__*.json'))
             + glob.glob(os.path.join(base, 'picks', f'{section}__*.json'))
             + glob.glob(os.path.join(base, 'messages', f'{section}__*', '*.json'))
             + glob.glob(os.path.join(base, 'proposals', section, '**', '*.json'), recursive=True)
             + glob.glob(os.path.join(base, 'teams', section, '*.json'))
             + glob.glob(os.path.join(base, 'sections', f'{section}.json')))
    if not files:
        print(f'Class {section}: nothing to clear.')
        return
    archive = os.path.join(_dir('_archive'), f'{section}_{datetime.datetime.now():%Y%m%d-%H%M%S}')
    for p in files:
        dest = os.path.join(archive, os.path.relpath(os.path.dirname(p), base))
        os.makedirs(dest, exist_ok=True)
        shutil.move(p, dest)
    print(f'Class {section}: cleared {len(files)} files. Archived in {archive}. Run set_teams to start again.')
