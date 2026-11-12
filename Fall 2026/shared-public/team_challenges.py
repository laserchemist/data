"""
team_challenges.py — short team-vs-team challenges for the Group Project teams.

Lives next to group_project.py and class_games.py in 'Fall 2026/shared-public/'.
Teams are the ones students spun onto in GroupProject_Teams, so nobody signs in again.
Progress is saved, one small file per student, in

    /home/jovyan/shared-public/group_project/<TERM>/challenges/fix_the_bug/<section>/<player>.json

🐛 Fix the Bug: seven broken cells. A bug counts for the team as soon as ANY teammate fixes it,
so teams do best by splitting the bugs up. The first team to squash all seven wins.

Students:   genes = bug_data()     bug_check()
Instructor: bug_light('08')   bug_board('08')   bug_reset('08', confirm='08')
"""
import os, glob, html, shutil, datetime

import numpy as np

import class_games as cg
import group_project as gp
from group_project import _dir, _read, _write, _now, _ns, _box, _show, _my_record, load_members, get_section
from class_games import _player, _live, _norm_section, WHEEL_COLORS, CHERRY, GOLD, MEDALS

__all__ = ['bug_data', 'bug_check', 'bug_light', 'bug_board', 'bug_reset', 'BUGS']

BUGS = ['.num_rows', '.where', 'np.mean', 'Boolean', 'for loop', '.hist', 'Bootstrap']
HIGH = 8.0             # the "high expression" cutoff in Bug 5
N_BOOT = 500


def _game(section):
    "The start-light name for one class's challenge (it starts on red)."
    game = f'fix_the_bug_{_norm_section(section)}'
    cg.GATED_GAMES.add(game)
    return game


# ============================================================================ the data
def bug_data():
    """A small practice table (simulated, in the style of the gene expression data set DS16):
    one row per tissue sample, with the Patient, the Tissue ('Tumor' or 'Normal') and the Expression of one gene."""
    from datascience import Table
    rng = np.random.RandomState(1013)
    n = 120
    tissue = np.array(['Tumor', 'Normal'] * (n // 2))
    expression = np.round(np.where(tissue == 'Tumor', rng.normal(8.6, 1.4, n), rng.normal(7.1, 1.2, n)), 2)
    return Table().with_columns('Patient', np.repeat(np.arange(1, n // 2 + 1), 2), 'Tissue', tissue, 'Expression', expression)


def _truth():
    t = bug_data()
    expr, tissue = t.column('Expression'), t.column('Tissue')
    return {'n': t.num_rows, 'n_tumor': int(np.count_nonzero(tissue == 'Tumor')),
            'tumor_mean': float(np.mean(expr[tissue == 'Tumor'])), 'first': bool(tissue.item(0) == 'Tumor'),
            'high': int(np.count_nonzero(expr > HIGH))}


# ============================================================================ checking
def _checks(ns):
    "[(solved, hint), ...] for the seven bugs, read from the notebook's variables."
    T = _truth()

    def val(name):
        v = ns.get(name)
        return None if v is Ellipsis else v

    out = []
    # 1 · .num_rows
    v = val('n_samples')
    ok = isinstance(v, (int, np.integer)) and not isinstance(v, bool) and v == T['n']
    out.append((ok, '' if ok else 'n_samples should be the number of rows in genes. Read the error: is num_rows a function?'))
    # 2 · .where
    v = val('tumor')
    ok, hint = False, 'make the table tumor: only the rows of genes where Tissue is Tumor'
    try:
        if v.num_rows == 0:
            hint = 'tumor has 0 rows, and no error! Python compares text exactly: look at how Tissue is spelled in the table'
        elif v.num_rows == T['n_tumor'] and all(x == 'Tumor' for x in v.column('Tissue')):
            ok, hint = True, ''
        else:
            hint = f'tumor has {v.num_rows} rows; there are {T["n_tumor"]} tumor samples'
    except (AttributeError, ValueError, TypeError):
        pass
    out.append((ok, hint))
    # 3 · np.mean of a column
    v = val('tumor_mean')
    ok = isinstance(v, (float, np.floating)) and np.isclose(v, T['tumor_mean'])
    out.append((ok, '' if ok else 'tumor_mean should be the average Expression in tumor (fix Bug 2 first). '
                                  'A column label is text: what does text need around it?'))
    # 4 · Boolean
    v = val('first_is_tumor')
    ok = isinstance(v, (bool, np.bool_)) and bool(v) == T['first']
    out.append((ok, '' if ok else 'first_is_tumor should be True or False. One = stores a value; which symbol asks "are these equal?"'))
    # 5 · for loop
    v = val('high_count')
    ok = isinstance(v, (int, np.integer)) and not isinstance(v, bool) and v == T['high']
    hint = ''
    if not ok:
        hint = (f'high_count should be how many samples have Expression above {HIGH:g}. A for loop needs a list of '
                'row numbers to walk through: 0, 1, 2, …')
        if isinstance(v, (int, np.integer)) and v == 0:
            hint = 'high_count is still 0: the loop did not finish. ' + hint
    out.append((ok, hint))
    # 6 · .hist
    ok = val('histogram_drawn') is True
    out.append((ok, '' if ok else 'the cell must run to its last line and draw the histogram. Which Table method draws one?'))
    # 7 · bootstrap
    v = val('boot_means')
    ok, hint = False, 'fill boot_means with one average per resample'
    try:
        arr = np.asarray(v, dtype=float)
        if arr.ndim != 1 or len(arr) != N_BOOT:
            hint = f'boot_means should hold {N_BOOT} averages; it holds {arr.size}'
        elif not np.all(np.isfinite(arr)):
            hint = 'the bootstrap means are not numbers: is your tumor table empty? Fix Bug 2 first'
        elif np.std(arr) < 1e-9:
            hint = ('every one of your bootstrap means is identical, so there is no variation to study. '
                    'How must a bootstrap resample be drawn?')
        elif abs(np.mean(arr) - T['tumor_mean']) > 0.5:
            hint = 'the bootstrap means are far from the tumor mean: resample the tumor table'
        else:
            ok, hint = True, ''
    except (TypeError, ValueError):
        pass
    out.append((ok, hint))
    return out


def _folder(section):
    return _dir('challenges', 'fix_the_bug', _norm_section(section))


def _load(section):
    out = []
    for p in glob.glob(os.path.join(gp.ROOT, gp.TERM, 'challenges', 'fix_the_bug', _norm_section(section), '*.json')):
        rec = _read(p)
        if rec and rec.get('team'):
            out.append(rec)
    return out


def _team_progress(section):
    """Each team's bugs: {'team', 'solved': {bug number: (time, name)}, 'n', 'done_at', 'players'}, best team first.
    A bug belongs to the team from the moment its first member fixes it."""
    section = _norm_section(section)
    cfg = get_section(section) or {'teams': []}
    team_of = {m['player']: m['team'] for m in load_members(section)}
    teams = {t: {'team': t, 'solved': {}, 'players': 0} for t in cfg['teams']}
    for rec in _load(section):
        team = team_of.get(rec.get('player'), rec['team'])            # follows a student the instructor moved
        t = teams.setdefault(team, {'team': team, 'solved': {}, 'players': 0})
        t['players'] += 1
        for k, when in (rec.get('solved') or {}).items():
            if k not in t['solved'] or when < t['solved'][k][0]:
                t['solved'][k] = (when, rec.get('name', '?'))
    for t in teams.values():
        t['n'] = len(t['solved'])
        t['reached'] = max((w for w, _ in t['solved'].values()), default='')
        t['done_at'] = t['reached'] if t['n'] == len(BUGS) else ''
    return sorted(teams.values(), key=lambda t: (-t['n'], t['reached'] or '9'))


def bug_check():
    """Student: check every bug you have fixed so far and add them to your team's score.
    Run it as often as you like; a bug, once squashed, stays squashed."""
    rec = _my_record()
    if not rec or not rec.get('team'):
        _show(_box('🎡 You are not on a team yet.', 'Open GroupProject_Teams, sign in and spin first; then run this cell again.', CHERRY))
        return
    section, team = rec['section'], rec['team']
    game = _game(section)
    gate = cg._gate(game)
    if gate:
        _show(gate)
        return
    checks = _checks(_ns())
    path = os.path.join(_folder(section), f'{_player()}.json')
    old = _read(path) or {}
    solved = dict(old.get('solved') or {})
    now = _now()
    new = []
    for k, (ok, _) in enumerate(checks, start=1):
        if ok and str(k) not in solved:
            solved[str(k)] = now
            new.append(k)
    _write(path, {'player': _player(), 'name': rec.get('name', ''), 'team': team, 'section': section,
                  'solved': solved, 'checkins': int(old.get('checkins', 0)) + 1, 'updated': now})
    mine = next((t for t in _team_progress(section) if t['team'] == team), {'solved': solved, 'n': len(solved)})
    rows = ''
    for k, (ok, hint) in enumerate(checks, start=1):
        by = mine['solved'].get(str(k))
        if ok or str(k) in solved:
            mark, note = '✅', ('🆕 squashed!' if k in new else '')
        elif by:
            mark, note = '🤝', f'squashed for your team by {html.escape(by[1])}'
        else:
            mark, note = '🐛', html.escape(hint)
        rows += (f'<tr><td style="padding:3px 8px;font-size:18px">{mark}</td><td style="padding:3px 8px;white-space:nowrap">'
                 f'<b>Bug {k}</b> · {BUGS[k - 1]}</td><td style="padding:3px 8px;color:{"#2E7D50" if mark != "🐛" else CHERRY}">{note}</td></tr>')
    n, total = mine['n'], len(BUGS)
    banner = (f'🏆 {html.escape(team)} squashed all {total} bugs!' if n == total
              else f'{html.escape(team)}: {n} of {total} bugs squashed' + (' — nice one!' if new else ''))
    left = [str(k) for k in range(1, total + 1) if str(k) not in mine['solved']]
    tip = ('Help a teammate understand a fix they did not make.' if not left else
           f'Still loose: Bug {", ".join(left)}. Split them up with your teammates!')
    _show(f'<div style="font-family:sans-serif;max-width:780px"><div style="font-size:1.35em;font-weight:900;color:{CHERRY};'
          f'margin:6px 0">{banner}</div><table style="border-collapse:collapse;font-size:1.02em">{rows}</table>'
          f'<div style="color:#666;margin-top:6px">✅ you · 🤝 a teammate · 🐛 still loose. {tip}</div></div>')


# ============================================================================ instructor
def bug_light(section):
    "Instructor: the start light for one class's Fix the Bug. Check-ins count only on green; GO starts the clock."
    cg.stoplight(_game(section))


def _bug_board_html(section):
    section = _norm_section(section)
    game = _game(section)
    teams = _team_progress(section)
    cfg = get_section(section) or {'teams': []}
    rows = ''
    for i, t in enumerate(teams):
        color = (WHEEL_COLORS[cfg['teams'].index(t['team']) % len(WHEEL_COLORS)] if t['team'] in cfg['teams']
                 else WHEEL_COLORS[i % len(WHEEL_COLORS)])
        rank = (('🏆' if i == 0 else MEDALS[i] if i < 3 else '✅') if t['done_at']
                else MEDALS[i] if i < 3 and t['n'] else f'<span style="color:#999">{i + 1}</span>')
        cells = ''
        for k, label in enumerate(BUGS, start=1):
            hit = t['solved'].get(str(k))
            cells += (f'<div style="flex:1;min-width:0;text-align:center;border-radius:8px;padding:5px 2px;'
                      f'background:{"#2E7D50" if hit else "#ECE8E1"};color:{"#fff" if hit else "#999"}">'
                      f'<div style="font-size:20px;line-height:1.1">{"✅" if hit else "🐛"}</div>'
                      f'<div style="font-size:11px;font-weight:700">{label}</div>'
                      f'<div style="font-size:11px;white-space:nowrap;overflow:hidden;text-overflow:ellipsis">'
                      f'{html.escape(hit[1]) if hit else "&nbsp;"}</div></div>')
        right = (f'<div style="color:#2E7D50;font-weight:900;font-size:16px">🏁 ALL SQUASHED</div>'
                 f'<div style="color:#2E7D50;font-weight:700">{cg._since_go(t["done_at"], game)}</div>' if t['done_at'] else
                 f'<div style="font-size:30px;font-weight:900;color:{color}">{t["n"]}<span style="font-size:14px;color:#888">'
                 f'/{len(BUGS)}</span></div>')
        rows += (f'<div style="display:flex;gap:14px;align-items:center;background:#fff;border:3px solid '
                 f'{"#2E7D50" if t["done_at"] else color};border-radius:12px;padding:10px 14px;margin-bottom:10px">'
                 f'<div style="font-size:28px;width:42px;text-align:center">{rank}</div>'
                 f'<div style="flex:1;min-width:0"><div style="display:flex;justify-content:space-between;align-items:baseline">'
                 f'<span style="font-size:20px;font-weight:900;color:{color}">{html.escape(t["team"])}</span>'
                 f'<span style="font-size:13px;color:#666">{t["players"]} checked in</span></div>'
                 f'<div style="display:flex;gap:5px;margin-top:6px">{cells}</div></div>'
                 f'<div style="width:140px;text-align:center">{right}</div></div>')
    if not rows:
        rows = f'<div style="padding:14px;color:#999;font-style:italic">Class {section} has no teams yet.</div>'
    winners = [t for t in teams if t['done_at']]
    banner = (f'<div style="background:#2E7D50;color:#fff;border-radius:12px;padding:14px 20px;margin-bottom:12px;font-size:24px;'
              f'font-weight:900">🏆 {html.escape(winners[0]["team"])} wins — all {len(BUGS)} bugs squashed, '
              f'{cg._since_go(winners[0]["done_at"], game)}!</div>' if winners else '')
    head = (f'<div style="background:linear-gradient(135deg,#1a1a2e 0%,#2d0a16 100%);padding:18px 24px;border-radius:12px;'
            f'margin-bottom:14px"><div style="color:{GOLD};font-size:2em;font-weight:900;letter-spacing:2px">🐛 FIX THE BUG'
            f'<span style="float:right;color:#fff;font-size:.6em;margin-top:10px">Class {section}</span></div>'
            f'<div style="color:#ddd">{cg._light_chip(game)} · A bug is squashed for the team when <b>any</b> teammate fixes it '
            f'(their name shows under it) · first team to squash all {len(BUGS)} wins</div></div>')
    return f'<div style="font-family:system-ui,sans-serif">{head}{banner}{rows}</div>'


def bug_board(section, interval=6):
    "Instructor: the live Fix the Bug board for one class: each team's seven bugs, and who squashed each one first."
    section = _norm_section(section)
    _folder(section)
    _live(lambda: _bug_board_html(section), interval, f'Fix the Bug · class {section}', f'fix_the_bug_{section}.html')


def bug_reset(section, confirm=''):
    "Instructor: clear one class's Fix the Bug results and put its light back to red. Files are archived, not deleted."
    section = _norm_section(section)
    if confirm != section:
        print(f"Nothing changed. To clear class {section}, run bug_reset('{section}', confirm='{section}').")
        return
    files = glob.glob(os.path.join(_folder(section), '*.json'))
    light = cg._light_path(_game(section))
    archive = os.path.join(_dir('_archive'), f'fix_the_bug_{section}_{datetime.datetime.now():%Y%m%d-%H%M%S}')
    os.makedirs(archive, exist_ok=True)
    for p in files + ([light] if os.path.exists(light) else []):
        shutil.move(p, archive)
    print(f'Class {section}: cleared {len(files)} check-ins; the light is back to 🔴. Archived in {archive}.')
