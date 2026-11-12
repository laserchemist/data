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
"""
import os, json, glob, time, datetime, shutil, html, csv

import numpy as np

from class_games import _player, _slug, _live, _norm_section, uuid_hex, WHEEL_COLORS, CHERRY, GOLD

__all__ = ['team_sign_in', 'team_spin', 'team_page', 'team_choose_project', 'team_choose_role', 'team_messages',
           'show_messages', 'remove_message', 'load_messages', 'ROLES',
           'set_teams', 'teams_board', 'open_teams', 'close_teams', 'open_projects', 'close_projects',
           'move_student', 'add_student', 'remove_student', 'assign_project', 'release_project',
           'save_teams', 'save_team_sheets', 'team_sheet', 'reset_section', 'export_teams_html',
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
    _flag(section, 'teams_open', True, 'the wheel is OPEN. Students can spin.')


def close_teams(section):
    "Instructor: close the wheel. Students already on a team keep it; nobody new can spin."
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
                         for m in load_messages(section, team)]}


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
        if not cfg.get('teams_open', True):
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
    sub = (f'{"🔓 wheel open" if cfg.get("teams_open", True) else "🔒 wheel closed"} · '
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
