"""
class_games.py — live class competitions (Neighbor Games, Bootstrap Smackdown).

Lives in the course repo at 'Fall 2026/shared-public/' (delivered by nbgitpuller).
Scores are written to the hub folder every student can write:
    /home/jovyan/shared-public/games/<game>/
one small file per student per round, so simultaneous submissions never overwrite each other.

Students:   submit_button('Arena', 'arena_rmse')          (Neighbor Games)
            smackdown_spin()   smackdown_check_in()   smackdown_summary()     (Bootstrap Smackdown)
Instructor: stoplight()   neighbor_scoreboard()   smackdown_teams()   smackdown_scoreboard()   smackdown_team_race()   smackdown_players()   smackdown_summaries()   manual_score(...)   reset_game(...)
"""
import os, re, json, glob, time, hashlib, datetime, threading, shutil, html

import numpy as np

GAMES_ROOT = os.environ.get('GAMES_ROOT', '/home/jovyan/shared-public/games')
CHERRY, GOLD = '#9E1B34', '#FFD700'
MEDALS = ['🥇', '🥈', '🥉']


# ============================================================================ storage
def _game_dir(game):
    path = os.path.join(GAMES_ROOT, game)
    os.makedirs(path, exist_ok=True)
    for folder in (GAMES_ROOT, path):
        try:
            os.chmod(folder, 0o777)
        except PermissionError:
            pass
    return path


def _player():
    "A short scrambled id for this hub login (never the login itself)."
    login = os.environ.get('JUPYTERHUB_USER', '') or os.environ.get('USER', 'student')
    return hashlib.sha256(('class-games:' + login.lower()).encode()).hexdigest()[:10]


def _slug(text):
    return re.sub(r'[^A-Za-z0-9]+', '-', str(text)).strip('-')[:40] or 'team'


def submit(game, team, round_name, score, extra=None, player=None):
    "Save one score. Resubmitting the same round replaces your earlier score for it."
    team = str(team).strip()
    if team in ('', '...', 'Ellipsis'):
        raise ValueError('Set your team name first.')
    entry = {'team': team, 'round': round_name, 'score': float(score), 'player': player or _player(),
             'time': time.strftime('%H:%M:%S'), 'submitted': datetime.datetime.now().isoformat(timespec='seconds')}
    if extra:
        entry.update(extra)
    folder = _game_dir(game)
    path = os.path.join(folder, f"{_slug(round_name)}__{_slug(team)}__{entry['player']}.json")
    tmp = path + '.tmp'
    with open(tmp, 'w') as f:
        json.dump(entry, f)
    os.replace(tmp, path)
    return entry


def load(game):
    "Every saved score for a game, as a list of dicts."
    out = []
    for p in glob.glob(os.path.join(GAMES_ROOT, game, '*.json')):
        try:
            with open(p) as f:
                out.append(json.load(f))
        except (ValueError, OSError):
            pass
    return out


def reset_game(game, section=None):
    """Clear a game's boards for the next class. Saves the class's results to CSV first (see save_results),
    then moves everything to an archive folder; nothing is deleted."""
    folder = os.path.join(GAMES_ROOT, game)
    files = glob.glob(os.path.join(folder, '*.json'))
    posts = glob.glob(os.path.join(folder, 'summaries', '*.json'))
    light = _light_path(game)
    if not files and not posts and not glob.glob(os.path.join(folder, 'teams', '*.json')):
        if os.path.exists(light):
            os.remove(light)
        print(f'{game}: nothing to clear. The start light is back to its starting state.')
        return
    section = _norm_section(section) or SECTION
    if not section:
        print("Set the class first, e.g. set_section('08'), so the saved results are labeled. Nothing was cleared.")
        return
    saved = save_results(game, section)
    if not saved:
        print('Saving failed, so nothing was cleared.')
        return
    archive = os.path.join(GAMES_ROOT, '_archive', f"{game}_{section}_{datetime.datetime.now():%Y%m%d-%H%M%S}")
    os.makedirs(os.path.join(archive, 'summaries'), exist_ok=True)
    for p in files:
        shutil.move(p, archive)
    for p in posts:
        shutil.move(p, os.path.join(archive, 'summaries'))
    spins = glob.glob(os.path.join(folder, 'teams', '*.json'))
    if spins:
        os.makedirs(os.path.join(archive, 'teams'), exist_ok=True)
        for p in spins:
            shutil.move(p, os.path.join(archive, 'teams'))
    for f in saved:
        shutil.copy(f, archive)
    if os.path.exists(light):
        shutil.move(light, os.path.join(archive, 'start_light.json'))
    print(f'{game}: cleared {len(files)} scores and {len(posts)} summaries for class {section}. '
          f'Boards are empty and the start light is back to 🔴, '
          f'ready for the next class. (Raw files archived in {archive}.)')


def manual_score(game, team, round_name, score, **extra):
    "Enter a score for a team that couldn't submit from their notebook."
    submit(game, team, round_name, score, dict(extra, manual=True), player='instructor')
    print(f'Saved: {team} · {round_name} · {score}')


# ============================================================================ student side
def _user_ns():
    from IPython import get_ipython
    return get_ipython().user_ns


def submit_button(round_name, score_var, extra_fn=None, game='neighbor_games', unit='K'):
    """A button that submits the notebook variable `score_var` (by name, read at click time)
    for this round, under the notebook's `team_name`."""
    import ipywidgets as widgets
    from IPython.display import display, HTML
    btn = widgets.Button(description=f'📡 Submit {round_name} score',
                         layout=widgets.Layout(width='260px', height='36px'),
                         style={'button_color': CHERRY, 'font_weight': 'bold', 'text_color': 'white'})
    out = widgets.Output()

    def on_click(_):
        ns = _user_ns()
        with out:
            out.clear_output()
            try:
                gate = _gate(game, again='Click Submit again after GO.')
                if gate:
                    display(HTML(gate))
                    return
                score = ns.get(score_var)
                if score is None or score is Ellipsis:
                    raise ValueError(f'Run the {round_name} cells first — {score_var} has no value yet.')
                team = ns.get('team_name', '')
                extra = dict(extra_fn() if extra_fn else {})
                members = _clean_members(ns.get('team_members'))
                if members:
                    extra['members'] = members
                    _register_team(game, team, members)
                submit(game, team, round_name, score, extra)
                display(HTML(f'<div style="color:#2E7D50;font-weight:bold;padding:6px 0;">✅ Submitted! '
                             f'<em>{html.escape(str(team))}</em> · {round_name} · {float(score):.3f} {unit}</div>'))
            except Exception as e:
                display(HTML(f'<div style="color:{CHERRY};font-weight:bold;">⚠️ {html.escape(str(e))}</div>'))

    btn.on_click(on_click)
    display(widgets.VBox([btn, out]))


def _pct(values, p):
    "The datascience percentile(): the smallest value with at least p% of values at or below it."
    v = np.sort(np.asarray(values, dtype=float))
    return v[max(int(np.ceil(p / 100 * len(v))) - 1, 0)]


def smackdown_check_in():
    """Bootstrap Smackdown: check every step so far, submit the points, and say what's left.
    Reads the notebook's own variables, so run it any time and as often as you like."""
    from IPython.display import display, HTML
    ns = _user_ns()
    steps = []        # (name, points possible, points earned, note)

    def val(name):
        v = ns.get(name, None)
        return None if v is Ellipsis else v

    tbl, x, y = val('my_table'), val('x_col'), val('y_col')
    team = val('team_name')
    if tbl is None or x is None or team is None:
        display(HTML(f'<b style="color:{CHERRY}">⚠️ Run your team\'s dataset cell first.</b>'))
        return
    gate = _gate('bootstrap_smackdown')
    if gate:
        display(HTML(gate))
        return
    spins = {x.get('player') for x in load_team_spins()}
    if spins and _player() not in spins:
        display(HTML('<div style="font-family:sans-serif;border:2px solid #E0DDD6;border-radius:10px;padding:10px 14px">'
                     '<div style="font-size:1.35em;font-weight:900">🔒 You\'re not on a team yet.</div>'
                     '<div style="color:#555;margin-top:3px">Check-ins count only for players who spun the wheel. '
                     'Ask your instructor to open the teams, then run the spin cell and this cell again.</div></div>'))
        return
    xs, ys = np.asarray(tbl.column(x), float), np.asarray(tbl.column(y), float)
    r = np.mean((xs - xs.mean()) / xs.std() * (ys - ys.mean()) / ys.std())
    true_slope = r * ys.std() / xs.std()
    true_int = ys.mean() - true_slope * xs.mean()

    steps.append(('1 · Data loaded', 1, 1, ''))
    obs = val('obs_slope')
    ok2 = obs is not None and np.isclose(float(obs), true_slope, rtol=1e-6)
    steps.append(('2 · Observed slope', 1, 1 if ok2 else 0, '' if ok2 else 'compute obs_slope on the full table'))

    sl, ic = val('sample_slopes'), val('sample_intercepts')
    ok3, note3 = False, 'fill in the bootstrap loop'
    try:
        sl_arr = np.asarray(sl, dtype=float)
        if len(sl_arr) < 1000:
            note3 = f'need 1000 bootstrap slopes, have {len(sl_arr)}'
        elif np.std(sl_arr) < 1e-9:
            note3 = 'every slope is identical: sample WITH replacement'
        elif abs(np.mean(sl_arr) - true_slope) > 0.5 * abs(true_slope) + 1e-9:
            note3 = 'bootstrap slopes are far from the observed slope'
        else:
            ok3, note3 = True, ''
    except (TypeError, ValueError):
        pass
    steps.append(('3 · Bootstrap loop (1000 samples)', 3, 3 if ok3 else 0, note3))

    left, right = val('slope_CI_left'), val('slope_CI_right')
    ok4 = False
    if ok3 and left is not None and right is not None:
        ok4 = (np.isclose(float(left), _pct(sl_arr, 2.5), rtol=1e-6)
               and np.isclose(float(right), _pct(sl_arr, 97.5), rtol=1e-6))
    steps.append(('4 · 95% CI on the slope', 2, 2 if ok4 else 0,
                  '' if ok4 else 'use percentile(2.5, …) and percentile(97.5, …) of sample_slopes'))

    pl, pr = val('pred_CI_left'), val('pred_CI_right')
    ok5 = False
    try:
        if not ok3:
            raise ValueError('needs a working bootstrap')
        pam = np.asarray(sl_arr) * float(np.mean(xs)) + np.asarray(ic, dtype=float)
        ok5 = (np.isclose(float(pl), _pct(pam, 2.5), rtol=1e-6) and np.isclose(float(pr), _pct(pam, 97.5), rtol=1e-6))
    except (TypeError, ValueError, NameError):
        pass
    steps.append(('5 · CI for prediction at mean x', 2, 2 if ok5 else 0,
                  '' if ok5 else ('percentiles of predicted_at_mean' if ok3 else 'needs a working bootstrap (step 3)')))

    figs = glob.glob('smackdown_*.png')
    ok6 = bool(figs) and ok4 and ok5
    steps.append(('6 · Smackdown figure saved', 2, 2 if ok6 else 0, '' if ok6 else 'run the figure cell (after steps 4–5)'))

    real = val('slope_is_real')
    ok7 = ok4 and isinstance(real, (bool, np.bool_)) and bool(real) == bool(float(left) > 0 or float(right) < 0)
    steps.append(('7 · Is the slope real?', 2, 2 if ok7 else 0,
                  '' if ok7 else ('set slope_is_real = True or False' if not isinstance(real, (bool, np.bool_))
                                  else 'check your CI against 0 again')))

    points = sum(s[2] for s in steps)
    possible = sum(s[1] for s in steps)

    # Keep the time you FIRST reached your best score: that decides ties ("fastest correct wins")
    folder = _game_dir('bootstrap_smackdown')
    mine = os.path.join(folder, f"Smackdown__{_slug(team)}__{_player()}.json")
    first_at = datetime.datetime.now().isoformat(timespec='seconds')
    try:
        with open(mine) as f:
            old = json.load(f)
    except (OSError, ValueError):
        old = None
    # Merge with what you earned before: a step, once earned, stays earned (e.g. after a kernel restart),
    # and each step remembers when YOU first earned it (the players board uses this).
    now = first_at
    earned = [s_[2] for s_ in steps]
    old_steps = (old or {}).get('steps') or [0] * len(steps)
    best_steps = [max(a, b) for a, b in zip(earned, old_steps)]
    step_times = list((old or {}).get('step_times') or [''] * len(steps))
    for k, pts in enumerate(best_steps):
        if pts and not step_times[k]:
            step_times[k] = now
    saved = sum(best_steps)
    kept = f" Your best, {saved}/{possible}, stays on the board." if saved > points else ''
    if old and old.get('score') == saved:
        first_at = old.get('first_at', first_at)        # same total again: keep the time you first reached it
    name = str(val('my_name') or '').strip()
    submit('bootstrap_smackdown', team, 'Smackdown', saved,
           {'possible': possible, 'first_at': first_at, 'name': '' if name in ('...', 'Ellipsis') else name,
            'slope': float(true_slope), 'ci': [float(left), float(right)] if ok4 else (old or {}).get('ci'),
            'steps': best_steps, 'step_times': step_times,
            'checkins': int((old or {}).get('checkins', 0)) + 1})

    rows = ''.join(f'<tr><td style="padding:3px 10px">{"✅" if s[2] == s[1] else "⬜"}</td>'
                   f'<td style="padding:3px 10px">{s[0]}</td><td style="padding:3px 10px;text-align:right">{s[2]}/{s[1]}</td>'
                   f'<td style="padding:3px 10px;color:{CHERRY}">{s[3]}</td></tr>' for s in steps)
    banner = ('🏆 ALL STEPS DONE — you\'re on the board!' if points == possible
              else f'{points} / {possible} points so far — keep going!')
    display(HTML(f'<div style="font-family:sans-serif"><div style="font-size:1.4em;font-weight:900;color:{CHERRY};'
                 f'margin:6px 0">{banner}</div><table style="border-collapse:collapse;font-size:1.05em">{rows}</table>'
                 f'<div style="color:#666;margin-top:6px">Submitted for <b>{html.escape(team)}</b>.{kept} '
                 'Fix anything unchecked and run this cell again.</div></div>'))


# ============================================================================ instructor: live boards
def _live(render, interval, title, page_file):
    """Show `render()` in a widget that refreshes every `interval` seconds, and keep a copy in
    `page_file` that reloads itself — open it in a new browser tab for a full-screen projector view."""
    import ipywidgets as widgets
    from IPython.display import display
    board = widgets.HTML()
    status = widgets.Label()
    refresh = widgets.Button(description='🔄 Refresh now', layout=widgets.Layout(width='150px', height='34px'),
                             style={'button_color': CHERRY, 'text_color': 'white', 'font_weight': 'bold'})
    pause = widgets.ToggleButton(description='⏸ Pause', layout=widgets.Layout(width='120px', height='34px'))
    stop = threading.Event()

    def draw(_=None):
        body = render()
        board.value = body
        status.value = f'Last refreshed {time.strftime("%H:%M:%S")} · every {interval} s'
        try:
            with open(page_file, 'w', encoding='utf-8') as f:
                f.write(f'<!DOCTYPE html><html><head><meta charset="utf-8"><meta http-equiv="refresh" content="{interval}">'
                        f'<title>{title}</title></head><body style="font-family:system-ui,sans-serif;background:#F7F5F0;'
                        f'max-width:1400px;margin:0 auto;padding:20px">{body}</body></html>')
        except OSError:
            pass

    def loop():
        while not stop.wait(interval):
            if not pause.value:
                try:
                    draw()
                except Exception as e:          # keep the board alive through a bad file
                    status.value = f'Refresh problem: {e}'

    def on_pause(change):
        pause.description = '▶ Resume' if change['new'] else '⏸ Pause'

    refresh.on_click(draw)
    pause.observe(on_pause, names='value')
    draw()
    threading.Thread(target=loop, daemon=True).start()
    display(widgets.HBox([refresh, pause, status], layout=widgets.Layout(gap='12px', align_items='center')), board)
    print(f'Projector view: right-click {page_file} in the file browser → Open in New Browser Tab '
          '(it reloads itself while this notebook is running).')
    return stop


def _header(title, subtitle):
    tag = (f'<span style="float:right;color:#fff;font-size:.6em;margin-top:10px">Class {SECTION}</span>' if SECTION else '')
    return (f'<div style="background:linear-gradient(135deg,#1a1a2e 0%,#2d0a16 100%);padding:18px 24px;border-radius:12px;'
            f'margin-bottom:14px"><div style="color:{GOLD};font-size:2em;font-weight:900;letter-spacing:2px">{title}{tag}</div>'
            f'<div style="color:#ddd">{subtitle}</div></div>')



# ============================================================================ the start light (🚦)
GATED_GAMES = {'bootstrap_smackdown', 'neighbor_games'}   # these start on red: no submissions until the instructor turns the light green
WHEEL_GAMES = {'bootstrap_smackdown'}                     # games whose teams come from the wheel (and close at GO)


def _light_path(game):
    folder = os.path.join(GAMES_ROOT, '_lights')
    os.makedirs(folder, exist_ok=True)
    for f in (GAMES_ROOT, folder):
        try:
            os.chmod(f, 0o777)
        except PermissionError:
            pass
    return os.path.join(folder, f'{game}.json')


def get_light(game='bootstrap_smackdown'):
    """The game's start light: {'state': 'red' | 'yellow' | 'green', 'go_at': time of the first GO, ...}.
    With no light set, gated games (the Smackdown) are red and other games are green."""
    try:
        with open(_light_path(game)) as f:
            rec = json.load(f)
    except (OSError, ValueError):
        rec = {}
    rec.setdefault('state', 'red' if game in GATED_GAMES else 'green')
    return rec


def set_light(game='bootstrap_smackdown', state='green'):
    "Instructor: set the light to 'red', 'yellow' or 'green'. Students can submit only on green."
    if state not in ('red', 'yellow', 'green'):
        raise ValueError("state must be 'red', 'yellow' or 'green'")
    path = _light_path(game)
    rec = get_light(game) if os.path.exists(path) else {}
    now = datetime.datetime.now().isoformat(timespec='seconds')
    rec.update(state=state, at=now, section=SECTION)
    if state == 'green':
        if not rec.get('go_at'):
            rec['go_at'] = now
            rec['teams_open'] = False          # the wheel closes at the first GO; open_teams() lets latecomers in
        rec.pop('stopped_at', None)
    elif rec.get('go_at'):
        rec['stopped_at'] = now
    with open(path + '.tmp', 'w') as f:
        json.dump(rec, f)
    os.replace(path + '.tmp', path)
    try:
        os.chmod(path, 0o666)
    except PermissionError:
        pass
    return rec


def teams_are_open(game='bootstrap_smackdown'):
    "True while new students may spin onto a team: until the first GO, or while you've reopened the teams."
    return bool(get_light(game).get('teams_open', True))


def open_teams(game='bootstrap_smackdown', is_open=True):
    """Instructor: open_teams() lets latecomers spin onto a team after GO; open_teams(is_open=False) closes the wheel again.
    Students who join after GO are marked late (⏰)."""
    path = _light_path(game)
    rec = get_light(game) if os.path.exists(path) else {}
    rec['teams_open'] = bool(is_open)
    with open(path + '.tmp', 'w') as f:
        json.dump(rec, f)
    os.replace(path + '.tmp', path)
    print(f'Teams are now {"OPEN: new students can spin" if is_open else "CLOSED: new students can no longer spin"}.')


def close_teams(game='bootstrap_smackdown'):
    "Instructor: close the wheel to new students (it closes by itself at the first GO)."
    open_teams(game, is_open=False)


def _clock(seconds):
    "Seconds as m:ss (or h:mm:ss)."
    h, rest = divmod(max(int(seconds), 0), 3600)
    m, sec = divmod(rest, 60)
    return f'{h}:{m:02d}:{sec:02d}' if h else f'{m}:{sec:02d}'


def _elapsed(rec):
    "Seconds since the first GO, up to the stop if the light was turned back to red."
    if not rec.get('go_at'):
        return None
    end = rec.get('stopped_at') if rec['state'] != 'green' else None
    stop = datetime.datetime.fromisoformat(end) if end else datetime.datetime.now()
    return (stop - datetime.datetime.fromisoformat(rec['go_at'])).total_seconds()


def _gate(game, allow_after_stop=False, again='Run this cell again after GO.'):
    "None if students may submit now; otherwise the message to show them."
    rec = get_light(game)
    if rec['state'] == 'green':
        return None
    if rec['state'] == 'red' and rec.get('go_at'):
        if allow_after_stop:
            return None
        msg = ('🛑', "Time's up — the competition has stopped.",
               'Your last score stays on the board. Your instructor can turn the light green again.')
    elif rec['state'] == 'yellow':
        msg = ('🟡', 'Get ready — almost time!', 'Nothing is submitted until the light turns green. ' + again)
    else:
        msg = ('🔴', "The competition hasn't started yet.",
               'Find your teammates and look over your data. Nothing is submitted until your instructor turns the light '
               'green; your work stays in your notebook. ' + again)
    return (f'<div style="font-family:sans-serif;border:2px solid #E0DDD6;border-radius:10px;padding:10px 14px;margin:6px 0">'
            f'<div style="font-size:1.35em;font-weight:900">{msg[0]} {msg[1]}</div>'
            f'<div style="color:#555;margin-top:3px">{msg[2]}</div></div>')


def _light_chip(game):
    "A small status label for the boards' subtitles."
    rec = get_light(game)
    el = _elapsed(rec)
    if rec['state'] == 'green':
        return f'🟢 <b>GO</b> · {_clock(el)} elapsed'
    if rec['state'] == 'yellow':
        return '🟡 <b>Get ready</b>'
    if el is not None:
        return f'🛑 <b>Stopped</b> after {_clock(el)}'
    return '🔴 <b>Not started</b>'


def _light_html(state, big, small):
    lamps = ''.join(
        f'<div style="width:74px;height:74px;border-radius:50%;margin:10px auto;background:{on if state == name else off};'
        f'box-shadow:{"0 0 28px " + on if state == name else "inset 0 0 12px #000"}"></div>'
        for name, on, off in (('red', '#FF3B30', '#4a1513'), ('yellow', '#FFCC00', '#4a3d10'), ('green', '#34C759', '#123d1c')))
    return (f'<div style="display:flex;align-items:center;gap:28px;font-family:system-ui,sans-serif">'
            f'<div style="background:#1a1a2e;border-radius:22px;padding:8px 14px;width:100px;border:4px solid #333">{lamps}</div>'
            f'<div><div style="font-size:3.2em;font-weight:900;line-height:1.1">{big}</div>'
            f'<div style="font-size:1.3em;color:#555;margin-top:6px">{small}</div></div></div>')


def stoplight(game='bootstrap_smackdown'):
    """Instructor: the start light. 🔴 before the start (students spin and find their teams; no check-ins),
    🟡 get ready, 🟢 GO! counts down 3-2-1, then opens check-ins and starts the clock.
    Back to 🔴 after GO = time's up: no more check-ins. The light is saved, so every notebook sees the same state.
    stoplight('neighbor_games') is the same light for the Neighbor Games' Submit buttons."""
    import ipywidgets as widgets
    from IPython.display import display
    view = widgets.HTML()
    style = dict(text_color='white', font_weight='bold')
    b_red = widgets.Button(description='🔴 Stop', layout=widgets.Layout(width='150px', height='44px'),
                           style=dict(style, button_color='#C62828'))
    b_yel = widgets.Button(description='🟡 Get ready', layout=widgets.Layout(width='150px', height='44px'),
                           style=dict(style, button_color='#B8860B'))
    b_go = widgets.Button(description='🟢 GO! (3-2-1)', layout=widgets.Layout(width='170px', height='44px'),
                          style=dict(style, button_color='#2E7D50'))
    b_door = widgets.Button(layout=widgets.Layout(width='190px', height='44px', margin='0 0 0 30px'),
                            style=dict(style, button_color='#555'))
    door = widgets.HTML()
    busy = threading.Event()
    wheel = game in WHEEL_GAMES
    what = 'check-ins' if wheel else 'submissions'
    if not wheel:
        b_door.layout.display = 'none'
        door.layout.display = 'none'

    def show():
        rec = get_light(game)
        el = _elapsed(rec)
        is_open = rec.get('teams_open', True)
        b_door.description = '🔒 Close teams' if is_open else '🔓 Let latecomers in'
        door.value = ('<span style="font-size:1.05em">🔓 <b>Teams open:</b> new students can spin. '
                      '(The wheel closes by itself at GO.)</span>' if is_open else
                      '<span style="font-size:1.05em">🔒 <b>Teams closed:</b> new students can\'t spin or check in. '
                      'Late arrivals: click <i>Let latecomers in</i>, then close again.</span>')
        if rec['state'] == 'green':
            view.value = _light_html('green', 'GO!', f'{what.capitalize()} are open · ⏱ {_clock(el)}')
        elif rec['state'] == 'yellow':
            view.value = _light_html('yellow', 'Get ready…', f'Teams together? {what.capitalize()} open on green.')
        elif el is not None:
            view.value = _light_html('red', "Time's up", f'Stopped after {_clock(el)} · {what} are closed')
        else:
            view.value = _light_html('red', 'Not started', f'{"Students spin and find their teams" if wheel else "Teams get set up"} · {what} are closed')

    def go(_):
        if busy.is_set():
            return
        busy.set()

        def countdown():
            try:
                if get_light(game)['state'] == 'red':
                    set_light(game, 'yellow')
                for n in (3, 2, 1):
                    view.value = _light_html('yellow', f'{n}…', 'Get ready!')
                    time.sleep(1)
                set_light(game, 'green')
                show()
            finally:
                busy.clear()
        threading.Thread(target=countdown, daemon=True).start()

    def to(state):
        def click(_):
            if not busy.is_set():
                set_light(game, state)
                show()
        return click

    def tick():
        while True:
            time.sleep(1)
            if not busy.is_set():
                try:
                    show()
                except Exception:
                    pass

    b_red.on_click(to('red'))
    b_yel.on_click(to('yellow'))
    b_go.on_click(go)

    def toggle_door(_):
        rec = get_light(game)
        open_teams(game, not rec.get('teams_open', True))
        show()
    b_door.on_click(toggle_door)
    show()
    threading.Thread(target=tick, daemon=True).start()
    display(widgets.VBox([view, widgets.HBox([b_red, b_yel, b_go, b_door], layout=widgets.Layout(gap='10px', margin='12px 0 0 0')), door],
                         layout=widgets.Layout(border='2px solid #E0DDD6', padding='14px')))



# ============================================================================ Neighbor Games: team members
def _clean_members(members):
    "team_members list -> clean list of names ('...' placeholders and blanks dropped, duplicates removed)."
    if isinstance(members, str):
        members = [m for m in re.split(r'[,;\n]', members)]
    if not isinstance(members, (list, tuple)):
        return []
    out, seen = [], set()
    for m in members:
        name = ' '.join(str(m).split())
        if name and name not in ('...', 'Ellipsis') and name.lower() not in seen:
            seen.add(name.lower())
            out.append(name)
    return out


def _register_team(game, team, members):
    team = str(team).strip()
    if team in ('', '...', 'Ellipsis') or not members:
        return
    path = os.path.join(_teams_dir(game), f'{_player()}.json')
    with open(path + '.tmp', 'w') as f:
        json.dump({'team': team, 'members': members, 'player': _player(),
                   'at': datetime.datetime.now().isoformat(timespec='seconds')}, f)
    os.replace(path + '.tmp', path)


def neighbor_team(game='neighbor_games'):
    """Student: register this notebook's team_name and team_members with the class scorecard.
    Works before GO (it isn't a score). Every teammate runs it in their own notebook."""
    from IPython.display import display, HTML
    ns = _user_ns()
    team = str(ns.get('team_name', '')).strip()
    raw = ns.get('team_members')
    members = _clean_members(raw)
    problem = None
    if team in ('', '...', 'Ellipsis'):
        problem = ('Type your team name between the quotes in <code>team_name</code>, e.g. '
                   '<code>team_name = "District 4: The Alkanol Alliance"</code>, and run that cell.')
    elif not isinstance(raw, (list, tuple)):
        problem = ('Make <code>team_members</code> a list: names in quotes, separated by commas, inside square brackets, '
                   'e.g. <code>team_members = ["Ada L.", "Grace H."]</code>.')
    elif not members:
        problem = 'Type a teammate\'s name between each pair of quotes in <code>team_members</code>.'
    elif any(str(m).strip() in ('', '...', 'Ellipsis') for m in raw):
        problem = (f'There\'s still an empty <code>""</code> in <code>team_members</code>. Fill it in, or delete it '
                   f'(and its comma) if your team has {len(members)} member{"s" if len(members) != 1 else ""}.')
    if problem:
        display(HTML(f'<div style="font-family:sans-serif;color:{CHERRY};font-weight:bold;padding:6px 0">⚠️ {problem}</div>'))
        return
    _register_team(game, team, members)
    chips = ''.join(f'<span style="display:inline-block;background:#fff;color:#1a1a2e;border-radius:14px;padding:3px 12px;'
                    f'margin:3px 4px 0 0;font-weight:600">{html.escape(m)}</span>' for m in members)
    display(HTML(f'<div style="font-family:sans-serif;background:linear-gradient(135deg,#1a1a2e,#2d0a16);color:#fff;'
                 f'border-radius:10px;padding:12px 16px;max-width:640px"><div style="color:#FFD700;font-size:1.25em;'
                 f'font-weight:900">🌿 {html.escape(team)}</div><div style="margin-top:4px">{chips}</div>'
                 f'<div style="color:#aaaacc;font-size:12px;margin-top:8px">✅ Registered with the class scorecard · '
                 f'{len(members)} member{"s" if len(members) != 1 else ""}. Every teammate runs this cell in their own '
                 f'notebook, with the same team name.</div></div>'))


def load_neighbor_teams(game='neighbor_games'):
    "team -> every member name any teammate listed (merged, in order of first appearance)."
    teams = {}
    for x in sorted(load_team_spins(game), key=lambda x: x.get('at', '')):
        names = teams.setdefault(x.get('team', '?'), [])
        for m in x.get('members', []):
            if m.lower() not in [n.lower() for n in names]:
                names.append(m)
    for x in load(game):                        # members sent with scores, in case a team skipped neighbor_team()
        if x.get('members'):
            names = teams.setdefault(x['team'], [])
            for m in x['members']:
                if m.lower() not in [n.lower() for n in names]:
                    names.append(m)
    return teams



# ============================================================================ saved overview page + Canvas export
def save_overview(game='neighbor_games', section=None, quiet=False):
    """Save the scoreboard as a web page to show later: neighbor_games_08.html (bootstrap_smackdown_08.html).
    It doesn't reload itself, so it keeps this class's final board. Open it from the file browser
    (right-click → Open in New Browser Tab) or download it to view in any browser."""
    section = _norm_section(section) or SECTION
    if not section:
        print("Set the class first, e.g. set_section('08').")
        return None
    if game == 'neighbor_games':
        body, title = _neighbor_html().replace('Live leaderboard', 'Final board'), f'The Neighbor Games · class {section}'
    else:
        body, title = _smackdown_html() + '<div style="height:18px"></div>' + _race_html(), f'Bootstrap Smackdown · class {section}'
    stamp = datetime.datetime.now().strftime('%A %B %d, %Y · %H:%M').replace(' 0', ' ')
    path = f'{game}_{section}.html'
    with open(path, 'w', encoding='utf-8') as f:
        f.write(f'<!DOCTYPE html><html><head><meta charset="utf-8"><title>{html.escape(title)}</title></head>'
                f'<body style="font-family:system-ui,sans-serif;background:#F7F5F0;max-width:1400px;margin:0 auto;padding:20px">'
                f'{body}<p style="color:#888;font-size:13px;margin-top:18px">Saved {stamp}</p></body></html>')
    if not quiet:
        print(f'💾 Saved {path}: the final board for class {section}. Right-click it → Open in New Browser Tab to show it.')
    return path


def _match_member(name, students):
    """A typed team-member name ('Ada L.', 'ada lovelace', 'AdaL') -> the one roster student it fits, else None."""
    from microproject_instructor import _words
    toks = _words(name)
    if not toks:
        return None
    if len(toks) == 1:                                          # 'AdaL' / 'adal': a given name, then an initial
        for st in students:
            for g in st['_given']:
                if toks[0].startswith(g) and len(toks[0]) > len(g):
                    toks = [g, toks[0][len(g):]]
                    break
            if len(toks) > 1:
                break
    hits = [st for st in students if toks[0] in st['_given']]
    if not hits and len(toks[0]) >= 4:                          # 'caleb' for a roster 'Ernestcaleb'
        hits = [st for st in students if any(len(g) > len(toks[0]) and (g.startswith(toks[0]) or g.endswith(toks[0]))
                                             for g in st['_given'])]
    if len(hits) > 1 and len(toks) > 1:
        hits = [st for st in hits if any(t in st['_last'] or t[:1] == st['_initial'] for t in toks[1:])]
    return hits[0] if len(hits) == 1 else None


def neighbor_canvas(which=None, points=1, absent=0, assignment='Neighbor Games', details=True):
    """Write a Canvas gradebook import file for the Neighbor Games: canvas_neighbor_games_08.csv.
    Each student on the roster gets `points` (1) for taking part, or `absent` (0; '' leaves Canvas unchanged).
    A student took part if their own notebook registered or submitted for a team, or a teammate listed their name.
    details=True adds their Team and the team's best score in each round (K), for your records:
    when Canvas asks about those columns on import, choose to ignore them.
    which: '08' (default: the class set with set_section) or 'all'.
    Needs the class roster(s), class_08.csv, in this folder: they hold the SIS Login IDs Canvas matches on.
    Run it before reset_game(...) clears the board."""
    from IPython.display import display, HTML
    from microproject_instructor import read_roster, _words
    sec = SECTION if which is None else (None if str(which).lower() == 'all' else _norm_section(which))
    files = sorted(glob.glob('class_[0-9]*.csv'))
    students = [st for f in files for st in read_roster(f) if sec is None or st['section'] == sec]
    if not students:
        print(f'No roster for class {sec or "(any)"} in this folder. Upload class_{sec or "08"}.csv here first '
              '(the same roster file as for the microprojects).')
        return None
    for st in students:
        st['_player'] = hashlib.sha256(('class-games:' + str(st['login']).strip().lower()).encode()).hexdigest()[:10]
        st['_given'] = set(_words(st.get('given', st['first']))) | {''.join(_words(st.get('given', st['first'])))}
        st['_last'] = set(_words(st['last'])) | {''.join(_words(st['last']))}
        st['_initial'] = (_words(st['last']) or [''])[0][:1]
    # who took part, and on which team
    by_player = {}
    for x in sorted(load_team_spins('neighbor_games') + load('neighbor_games'), key=lambda x: x.get('at', '')):
        if x.get('player') and x.get('team'):
            by_player[x['player']] = x['team']
    rosters = load_neighbor_teams()
    team_of, how = {}, {}
    for st in students:
        if st['_player'] in by_player:
            team_of[id(st)], how[id(st)] = by_player[st['_player']], 'own notebook'
    unmatched = []
    for team, members in rosters.items():
        for m in members:
            st = _match_member(m, [x for x in students if id(x) not in team_of or team_of[id(x)] == team])
            if st is None:
                st = _match_member(m, students)
            if st is None:
                unmatched.append(f'{m} ({team})')
            elif id(st) not in team_of:
                team_of[id(st)], how[id(st)] = team, 'named by a teammate'
    best = {}
    for x in load('neighbor_games'):
        key = (x['team'], x['round'])
        if key not in best or x['score'] < best[key]:
            best[key] = x['score']
    header = ['Student', 'ID', 'SIS User ID', 'SIS Login ID', 'Section', assignment]
    if details:
        header += ['Team'] + [f'{r} (K)' for r in NEIGHBOR_ROUNDS]
    rows, review = [], []
    for st in sorted(students, key=lambda x: (x['section'], x['last'].lower(), x['first'].lower())):
        team = team_of.get(id(st), '')
        row = [st['full'], '', '', st['login'], st.get('roster_section') or st['section'], points if team else absent]
        if details:
            row += [team] + [(round(best[(team, r)], 2) if (team, r) in best else '') for r in NEIGHBOR_ROUNDS]
        rows.append(row)
        review.append([st['section'], f"{st['first']} {st['last'][:1]}.", team or '—', points if team else absent,
                       how.get(id(st), 'no sign of taking part')])
    out = f'canvas_neighbor_games_{sec or "all"}.csv'
    _write_csv(out, header, rows)
    took = sum(1 for r in review if r[2] != '—')
    print(f'Class {sec or "all"}: {took} of {len(review)} students took part ({points} point'
          f'{"s" if points != 1 else ""}); {len(review) - took} get {absent if absent != "" else "no change"}.')
    display(HTML(f'<p style="font-size:1.1em">💾 Saved <b>{out}</b> — <a href="{out}" target="_blank" download>download it</a>, '
                 f'then in Canvas: <b>Grades → Import</b>. '
                 + ('When Canvas asks about the <b>Team</b> and round-score columns, choose to <b>ignore</b> them (they are '
                    'for your records). ' if details else '')
                 + '🔒 It holds names and logins: keep it off GitHub.</p>'))
    from datascience import Table
    t = Table().with_columns('class', [r[0] for r in review], 'student', [r[1] for r in review], 'team', [r[2] for r in review],
                             assignment, [r[3] for r in review], 'how we know', [r[4] for r in review])
    t.sort('team').show()
    if unmatched:
        print('⚠️ Team-member names that match no one (or more than one student) on the roster — check these students '
              'by hand: ' + '; '.join(unmatched))
    return out


# ============================================================================ Neighbor Games: Training Camp checks
def _ok(msg):
    from IPython.display import display, HTML
    display(HTML(f'<div style="font-family:sans-serif;color:#2E7D50;font-weight:bold;padding:4px 0">✅ {msg}</div>'))


def _no(msg):
    from IPython.display import display, HTML
    display(HTML(f'<div style="font-family:sans-serif;color:{CHERRY};font-weight:bold;padding:4px 0">❌ {msg}</div>'))


def _five_nearest(ns):
    feats = list(ns['features'])
    pts = [np.array(r, dtype=float) for r in ns['train'].select(feats).rows]
    d = np.array([np.sqrt(np.sum((p - np.asarray(ns['mystery'], dtype=float)) ** 2)) for p in pts])
    order = np.argsort(d, kind='stable')[:5]
    return d, order


def neighbor_check(step):
    """Student: check one Training Camp challenge. step is the name of the variable or function you just made:
    'split', 'z', 'distance', 'd0', 'all_dists', 'nearest', 'prediction', 'toolkit', 'arena', 'ipa_std', 'prize_score', 'weights'."""
    ns = _user_ns()
    try:
        _NCHECKS[step](ns)
    except KeyError as e:
        _no(f'<code>{html.escape(str(e).strip(chr(39)))}</code> isn\'t defined yet. Run your challenge cell (and the cells above it) first.')
    except Exception as e:
        text = str(e)
        if 'ellipsis' in text.lower():
            _no('There\'s still a <code>...</code> to fill in.')
        elif 'is not in the table' in text or "'train'" in text or "'test'" in text:
            _no('The standardized <code>train</code> and <code>test</code> tables aren\'t ready. Finish Challenges 1 and 2, '
                'then rerun the standard-units cells and the cells after them.')
        else:
            _no(f'Python says: {html.escape(type(e).__name__ + ": " + text)}')


def _check_split(ns):
    tr, te = ns['train_roh'], ns['test_roh']
    n = tr.num_rows + te.num_rows
    if tr.num_rows == round(0.75 * n):
        _ok(f'{tr.num_rows} training and {te.num_rows} test molecules: a 75 / 25 split.')
    elif te.num_rows == round(0.75 * n):
        _no(f'That puts {tr.num_rows} molecules in training and {te.num_rows} in test. split(k) gives k rows to the '
            'FIRST table, train_roh: training should get three quarters.')
    else:
        _no(f'You have {tr.num_rows} training molecules; three quarters of {n} is {round(0.75 * n)}.')


def _check_z(ns):
    r = np.asarray(ns['z'](np.array([10.0, 20.0]), 15.0, 5.0), dtype=float)
    if np.allclose(r, [-1, 1]):
        _ok('z([10, 20], mu=15, sigma=5) = [-1, 1]: 10 is one standard deviation below the mean, 20 is one above.')
    elif np.allclose(r, [-5, 5]):
        _no('You get [-5, 5]: divide the difference by sigma.')
    elif np.allclose(r, [25, 35]) or np.allclose(r, [5, 7]):
        _no('Subtract the mean first, then divide by sigma: (x - mu) / sigma. The parentheses matter.')
    else:
        _no(f'z([10, 20], 15, 5) should be [-1, 1]; yours gives {np.round(r, 3).tolist()}.')


def _check_distance(ns):
    d = ns['distance']
    a = float(d(np.array([0.0, 0.0]), np.array([3.0, 4.0])))
    b = float(d(np.array([1.0, 2.0, 3.0]), np.array([1.0, 2.0, 3.0])))
    if np.isclose(a, 5) and np.isclose(b, 0):
        _ok('distance([0, 0], [3, 4]) = 5, the 3-4-5 right triangle. It works for any number of features.')
    elif np.isclose(a, 25):
        _no('You get 25 for [0, 0] to [3, 4]: take the square root at the end.')
    elif np.isclose(a, 7) or np.isclose(a, -7):
        _no('You get 7: square each difference before adding them up.')
    else:
        _no(f'distance([0, 0], [3, 4]) should be 5; yours gives {a:.3f}.')


def _check_d0(ns):
    d, _ = _five_nearest(ns)
    if np.isclose(float(ns['d0']), d[0]):
        _ok(f'The first training molecule is {d[0]:.3f} standard units away from the mystery molecule.')
    else:
        _no(f'd0 should be {d[0]:.3f}. Use the mystery molecule as the second point: distance(first_row, mystery).')


def _check_all_dists(ns):
    d, order = _five_nearest(ns)
    mine = np.asarray(ns['all_dists'], dtype=float)
    if len(mine) != len(d):
        _no(f'You have {len(mine)} distances; there should be {len(d)}, one per training molecule.')
    elif np.allclose(mine, d):
        n0 = int(np.sum(np.isclose(d, 0)))
        close = (f'{n0} training molecule{"s are" if n0 > 1 else " is"} at distance 0: exactly the same '
                 f'{" and ".join(ns["features"])} as the mystery molecule (isomers!)' if n0 else
                 f'the closest is only {d[order[0]]:.3f} away')
        _ok(f'{len(d)} distances, one per training molecule. {close[0].upper() + close[1:]}; the farthest is {d.max():.2f}.')
    else:
        _no('The right number of distances, but not the right values: each one is distance(np.array(row), mystery).')


def _check_nearest(ns):
    d, order = _five_nearest(ns)
    t = ns['nearest']
    if 'Distance' not in t.labels:
        _no('nearest needs the Distance column: train.with_column(\'Distance\', all_dists) …')
    elif t.num_rows != 5:
        _no(f'nearest has {t.num_rows} rows; take(np.arange(5)) keeps the 5 closest.')
    elif not np.allclose(np.asarray(t.column('Distance'), dtype=float), d[order]):
        _no('Those aren\'t the 5 closest: sort by \'Distance\' (smallest first) before you take them.')
    else:
        _ok('These are the 5 nearest neighbors of the mystery molecule, closest first.')


def _check_prediction(ns):
    d, order = _five_nearest(ns)
    expect = float(np.average(np.asarray(ns['train'].column('bp'), dtype=float)[order]))
    mine = float(ns['prediction'])
    actual = float(ns['test'].column('bp').item(0))
    if np.isclose(mine, expect):
        _ok(f'Predicted bp = {mine:.1f} K. The actual bp is {actual:.0f} K, so you\'re off by {abs(mine - actual):.1f} K. '
            'That\'s k-nearest neighbors, done by hand!')
    else:
        _no(f'The prediction should be the average bp of your 5 neighbors, {expect:.1f} K; yours is {mine:.1f} K.')


def _check_toolkit(ns):
    p = float(ns['predict_knn'](0, 5))
    if np.isclose(p, float(ns['prediction'])):
        _ok(f'predict_knn(0, 5) = {p:.1f} K, the same as your hand-built prediction for the mystery molecule.')
    else:
        _no(f'predict_knn gives {p:.1f} K, but your hand-built prediction is {float(ns["prediction"]):.1f} K. '
            'Did you change features? Rerun the Training Camp cells.')


def _check_arena(ns):
    preds = list(ns['arena_predictions'])
    n = ns['test'].num_rows
    if len(preds) != n:
        _no(f'You have {len(preds)} predictions; you need {n}, one per test molecule. Loop over np.arange(test.num_rows).')
    elif not np.isclose(float(preds[-1]), float(ns['predict_knn'](n - 1, ns['k']))):
        _no('Use the row number i from the loop as the first argument: predict_knn(i, k).')
    else:
        _ok(f'{n} predictions, one per test molecule, with k = {ns["k"]} and features = {list(ns["features"])}.')


def _check_ipa(ns):
    raw, tr, feats = ns['ipa_raw'], ns['train_roh'], list(ns['features'])
    expect = np.array([(raw[f] - np.mean(tr.column(f))) / np.std(tr.column(f)) for f in feats])
    mine = np.asarray(ns['ipa_std'], dtype=float)
    if mine.shape == expect.shape and np.allclose(mine, expect):
        _ok('Isopropanol, standardized with the training mean and SD: ' +
            ', '.join(f'{f} = {v:.3f}' for f, v in zip(feats, mine)))
    else:
        _no('Each value goes into standard units with the training mean and SD: train_su(ipa_raw[f], f), for each feature f.')


def _check_prize(ns):
    expect = (float(ns['ethanol_error']) + float(ns['ipa_error'])) / 2
    if np.isclose(float(ns['prize_score']), expect):
        _ok(f'Prize score = {expect:.2f} K, the average of your two errors.')
    else:
        _no(f'The average of two errors divides their sum by 2: it should be {expect:.2f} K.')


def _check_weights(ns):
    t = ns['nearest']
    expect = 1 / (np.asarray(t.column('Distance'), dtype=float) + 1e-9)
    mine = np.asarray(ns['weights'], dtype=float)
    if mine.shape == expect.shape and np.allclose(mine, expect):
        shown = ' · '.join('huge (distance 0)' if w > 1e6 else f'{w:.2f}' for w in mine)
        _ok(f'Weights = 1 / distance, so the closest neighbors get the biggest say: {shown}')
    else:
        _no('weights should be 1 / (nearest.column(\'Distance\') + 1e-9), one weight per neighbor.')


_NCHECKS = {'split': _check_split, 'z': _check_z, 'distance': _check_distance, 'd0': _check_d0, 'all_dists': _check_all_dists,
            'nearest': _check_nearest, 'prediction': _check_prediction, 'toolkit': _check_toolkit,
            'arena': _check_arena, 'ipa_std': _check_ipa, 'prize_score': _check_prize, 'weights': _check_weights}


NEIGHBOR_ROUNDS = {
    'Tribute':  ('🌿', 'RMSE', '#6B6860'),
    'Arena':    ('⚔️', 'RMSE', CHERRY),
    'Prize':    ('🏆', 'Avg error', '#B8860B'),
    'Wildcard': ('🌟', 'RMSE', '#2E7D50'),
}


def _best_per_team(scores, round_name):
    best = {}
    for s in scores:
        if s.get('round') == round_name and (s['team'] not in best or s['score'] < best[s['team']]['score']):
            best[s['team']] = s
    return sorted(best.values(), key=lambda s: (s['score'], s.get('submitted', '')))


def _neighbor_html():
    scores = load('neighbor_games')
    rosters = load_neighbor_teams()
    teams = {s['team'] for s in scores} | set(rosters)
    strip, boards = '', ''
    for rnd, (emoji, label, color) in NEIGHBOR_ROUNDS.items():
        entries = _best_per_team(scores, rnd)
        leader = f'{html.escape(entries[0]["team"])}<br><b>{entries[0]["score"]:.2f} K</b>' if entries else '—'
        strip += (f'<div style="flex:1;min-width:150px;background:#fff;border-radius:10px;padding:10px;text-align:center;'
                  f'border:1px solid #E0DDD6"><div style="font-size:1.5em">{emoji}</div><b>{rnd}</b>'
                  f'<div style="font-size:12px;color:#888">{len(entries)} team{"s" if len(entries) != 1 else ""}</div>'
                  f'<div style="font-size:13px;color:#2E7D50;margin-top:4px">{leader}</div></div>')
        if entries:
            best, worst = entries[0]['score'], entries[-1]['score']
            rows = ''
            for i, e in enumerate(entries):
                medal = MEDALS[i] if i < 3 else f'<span style="color:#999">{i + 1}</span>'
                gap = '' if i == 0 else '+{:.2f}'.format(e['score'] - best)
                pct = 100 if worst == best else max(6, int(100 * (1 - (e['score'] - best) / (worst - best))))
                detail = (f'<span style="font-size:12px;color:#888;margin-left:8px">k={e.get("k")} · {", ".join(e["features"])}</span>'
                          if rnd == 'Arena' and e.get('features') else '')
                who = rosters.get(e['team'])
                who = (f'<div style="font-size:12px;color:#6B6860;margin:1px 0 3px">{html.escape(", ".join(who))}</div>'
                       if who else '')
                rows += (f'<tr><td style="padding:6px 10px;font-size:20px;text-align:center;width:40px">{medal}</td>'
                         f'<td style="padding:6px 4px"><div style="font-weight:700;font-size:15px">{html.escape(e["team"])}{detail}</div>{who}'
                         f'<div style="background:#E8E4DE;height:6px;border-radius:3px;width:260px"><div style="background:{color};'
                         f'height:6px;border-radius:3px;width:{pct}%"></div></div></td>'
                         f'<td style="padding:6px 10px;text-align:right;font-weight:800;font-size:16px">{e["score"]:.2f} K</td>'
                         f'<td style="padding:6px 10px;text-align:right;color:#999;font-size:12px">'
                         f'{gap}<br>{e.get("time", "")}</td></tr>')
            table = f'<table style="width:100%;border-collapse:collapse">{rows}</table>'
        else:
            table = '<div style="color:#999;padding:10px;font-style:italic">No submissions yet.</div>'
        boards += (f'<div style="background:#fff;border:1px solid #E0DDD6;border-radius:10px;margin-bottom:12px;overflow:hidden">'
                   f'<div style="padding:8px 14px;border-bottom:1px solid #F0EDE8;font-weight:800;font-size:16px">{emoji} {rnd} Round'
                   f'<span style="float:right;font-weight:400;color:#999;font-size:12px">{label} · lower is better</span></div>{table}</div>')
    cards = ''.join(
        f'<div style="background:#fff;border:1px solid #E0DDD6;border-radius:10px;padding:8px 12px;min-width:170px;flex:1">'
        f'<div style="font-weight:800;font-size:14px">{html.escape(t)}</div>'
        f'<div style="font-size:12px;color:#6B6860">{html.escape(", ".join(rosters.get(t, [])) or "no names yet")}</div></div>'
        for t in sorted(teams, key=str.lower))
    panel = (f'<div style="font-weight:800;font-size:14px;color:#6B6860;margin:2px 0 6px">👥 Teams</div>'
             f'<div style="display:flex;gap:8px;flex-wrap:wrap;margin-bottom:14px">{cards}</div>' if cards else '')
    return (_header('🌿 THE NEIGHBOR GAMES', f'{_light_chip("neighbor_games")} · Live leaderboard · '
                    f'{len(teams)} team{"s" if len(teams) != 1 else ""} · '
                    f'{sum(len(v) for v in rosters.values())} students')
            + panel + f'<div style="display:flex;gap:10px;flex-wrap:wrap;margin-bottom:14px">{strip}</div>' + boards)


def neighbor_scoreboard(interval=10):
    "Live Neighbor Games leaderboard: best score per team in each round."
    _game_dir('neighbor_games')
    return _live(_neighbor_html, interval, 'Neighbor Games', 'neighbor_games_scoreboard.html')


def _smackdown_html():
    scores = [s for s in load('bootstrap_smackdown') if s.get('round') == 'Smackdown']
    teams = {}
    for s in scores:
        teams.setdefault(s['team'], []).append(s)
    ranked = []
    for team, members in teams.items():
        top = max(m['score'] for m in members)
        best = min((m for m in members if m['score'] == top), key=lambda m: m.get('first_at', ''))
        first_full = best.get('first_at', '')
        finished = sorted(m.get('name') or '✓' for m in members if m['score'] >= m.get('possible', 13))
        ranked.append((top, first_full, team, len(members), finished, best))
    ranked.sort(key=lambda t: (-t[0], t[1]))
    rows = ''
    for i, (top, first, team, n, finished, best) in enumerate(ranked):
        possible = best.get('possible', 13)
        medal = MEDALS[i] if i < 3 else f'<span style="color:#999">{i + 1}</span>'
        done_at = _since_go(first) if top >= possible and first else ''
        ci = best.get('ci')
        ci_txt = f'slope {best["slope"]:.3f} · CI [{ci[0]:.3f}, {ci[1]:.3f}]' if ci else ''
        rows += (f'<tr style="border-bottom:1px solid #F0EDE8"><td style="padding:10px;font-size:26px;text-align:center;width:50px">{medal}</td>'
                 f'<td style="padding:10px 4px"><div style="font-size:19px;font-weight:800">{html.escape(team)}</div>'
                 f'<div style="font-size:12px;color:#888">{n} checked in · {len(finished)} finished{": " + ", ".join(html.escape(f) for f in finished[:8]) if finished else ""}</div>'
                 f'<div style="font-size:12px;color:#555">{ci_txt}</div></td>'
                 f'<td style="padding:10px;width:280px"><div style="background:#E8E4DE;height:12px;border-radius:6px">'
                 f'<div style="background:{CHERRY if top < possible else "#2E7D50"};height:12px;border-radius:6px;width:{100 * top / possible:.0f}%"></div></div></td>'
                 f'<td style="padding:10px;text-align:right;font-size:22px;font-weight:900">{top:g}<span style="font-size:13px;color:#888">/{possible}</span></td>'
                 f'<td style="padding:10px;text-align:right;color:#2E7D50;font-weight:700">{"⚡ " + done_at if done_at else ""}</td></tr>')
    if not rows:
        rows = '<tr><td style="padding:14px;color:#999;font-style:italic">No check-ins yet.</td></tr>'
    return (_header('🥊 BOOTSTRAP SMACKDOWN', f'{_light_chip("bootstrap_smackdown")} · Live standings · points, then fastest to finish '
                    '(⚡ = time after GO when all 13 points were first reached)')
            + f'<div style="background:#fff;border:1px solid #E0DDD6;border-radius:10px;overflow:hidden">'
              f'<table style="width:100%;border-collapse:collapse">{rows}</table></div>')


def _since_go(iso, game='bootstrap_smackdown'):
    "A finish time as minutes:seconds after GO (or the clock time if there was no GO)."
    go = get_light(game).get('go_at')
    if go and iso:
        try:
            return '+' + _clock((datetime.datetime.fromisoformat(iso) - datetime.datetime.fromisoformat(go)).total_seconds())
        except ValueError:
            pass
    return (iso or '')[11:19]


def _ts(iso):
    try:
        return datetime.datetime.fromisoformat(iso).timestamp()
    except (TypeError, ValueError):
        return 0


def smackdown_scoreboard(interval=10):
    "Live Bootstrap Smackdown standings: each team's best points, ties broken by who finished first."
    _game_dir('bootstrap_smackdown')
    return _live(_smackdown_html, interval, 'Bootstrap Smackdown', 'bootstrap_smackdown_scoreboard.html')


# ============================================================================ Smackdown: individual contributions
SMACK_STEPS = ['Data', 'Slope', 'Bootstrap', 'CI', 'Prediction', 'Figure', 'Real?']


def _smackdown_players_html():
    scores = [s for s in load('bootstrap_smackdown') if s.get('round') == 'Smackdown']
    posted = {p.get('player') for p in load_summaries('bootstrap_smackdown')}
    teams = {}
    for s in scores:
        teams.setdefault(s['team'], []).append(s)
    # order teams like the main board: best points, then first to finish
    def team_key(members):
        top = max(m['score'] for m in members)
        first = min((m.get('first_at', '') for m in members if m['score'] == top), default='')
        return (-top, first)
    sections = ''
    for team, members in sorted(teams.items(), key=lambda kv: team_key(kv[1])):
        n_steps = len(SMACK_STEPS)
        # who on this team earned each step first -> ⭐
        firsts = []
        for k in range(n_steps):
            times = [(m.get('step_times') or [''] * n_steps)[k] for m in members]
            stamped = [(t, i) for i, t in enumerate(times) if t]
            firsts.append(min(stamped)[1] if stamped else None)
        stars = {i: sum(1 for f in firsts if f == i) for i in range(len(members))}
        order = sorted(range(len(members)), key=lambda i: (-members[i]['score'], members[i].get('first_at', '')))
        head = ''.join(f'<th style="padding:6px 4px;font-size:12px;color:#888;font-weight:600;text-align:center">{lab}</th>'
                       for lab in SMACK_STEPS)
        rows = ''
        for rank, i in enumerate(order):
            m = members[i]
            steps = m.get('steps') or [0] * n_steps
            cells = ''
            for k in range(n_steps):
                if steps[k]:
                    star = '⭐' if firsts[k] == i else ''
                    cells += (f'<td style="text-align:center;padding:6px 4px"><span style="display:inline-block;min-width:34px;'
                              f'padding:3px 4px;border-radius:6px;background:#E6F2EA;color:#2E7D50;font-weight:800">✓{star}</span></td>')
                else:
                    cells += ('<td style="text-align:center;padding:6px 4px"><span style="display:inline-block;min-width:34px;'
                              'padding:3px 4px;border-radius:6px;background:#F0EDE8;color:#bbb">·</span></td>')
            name = html.escape(m.get('name') or f'student {m.get("player", "")[:4]}')
            last = str(m.get('submitted', ''))[11:16]
            done = '🏁 ' if m['score'] >= m.get('possible', 13) else ''
            done += '📝 ' if m.get('player') in posted else ''
            rows += (f'<tr style="border-top:1px solid #F0EDE8"><td style="padding:6px 10px;font-weight:700;font-size:15px;white-space:nowrap">'
                     f'{done}{name}</td>{cells}'
                     f'<td style="padding:6px 10px;text-align:right;font-weight:900;font-size:16px">{m["score"]:g}'
                     f'<span style="font-size:11px;color:#888">/{m.get("possible", 13)}</span></td>'
                     f'<td style="padding:6px 10px;text-align:center;font-size:15px">{"⭐" * stars[i] or "—"}</td>'
                     f'<td style="padding:6px 10px;text-align:right;color:#888;font-size:12px;white-space:nowrap">'
                     f'{m.get("checkins", 1)} check-in{"s" if m.get("checkins", 1) != 1 else ""}<br>last {last}</td></tr>')
        best = max(m['score'] for m in members)
        sections += (f'<div style="background:#fff;border:1px solid #E0DDD6;border-radius:10px;margin-bottom:14px;overflow:hidden">'
                     f'<div style="background:#2d0a16;color:#fff;padding:9px 14px;font-weight:800;font-size:17px">{html.escape(team)}'
                     f'<span style="float:right;color:{GOLD}">team best {best:g} · {len(members)} member{"s" if len(members) != 1 else ""}</span></div>'
                     f'<table style="width:100%;border-collapse:collapse"><tr><th></th>{head}'
                     f'<th style="padding:6px 10px;font-size:12px;color:#888;text-align:right">points</th>'
                     f'<th style="padding:6px 10px;font-size:12px;color:#888">firsts</th><th></th></tr>{rows}</table></div>')
    if not sections:
        sections = '<div style="color:#999;padding:14px;font-style:italic">No check-ins yet.</div>'
    return (_header('🥊 SMACKDOWN · PLAYERS', _light_chip('bootstrap_smackdown') + ' · Each member\'s steps · ⭐ = first on the team to earn that step · 🏁 = all 13 points · 📝 = summary posted')
            + sections)


def smackdown_players(interval=10):
    """Live board of individual contributions: every member's steps, who on each team earned each step
    first (⭐), points, and how many times they've checked in."""
    _game_dir('bootstrap_smackdown')
    return _live(_smackdown_players_html, interval, 'Smackdown Players', 'bootstrap_smackdown_players.html')



# ============================================================================ team summaries (student box + instructor board)

# ============================================================================ Smackdown: collective team race
def _team_progress(game='bootstrap_smackdown', count_late=False):
    """Each team's collective progress. Members are everyone who spun onto the team (so a teammate who hasn't
    checked in counts as 0 points). Students who joined after GO (late) are shown but don't hold their team back,
    unless count_late=True. If nobody used the wheel, members are whoever checked in."""
    n_steps = len(SMACK_STEPS)
    spin_recs = [x for x in load_team_spins(game) if x.get('player')]
    spins = {x['player']: x.get('team') for x in spin_recs}
    late = {x['player'] for x in spin_recs if x.get('late')}
    best = {}                                          # player -> their check-in for their current team
    for x in load(game):
        if x.get('round') != 'Smackdown':
            continue
        pl = x.get('player')
        if spins and pl not in spins:                  # the wheel is in use: only players who spun count
            continue
        if spins.get(pl, x['team']) != x['team']:      # an old check-in from before move_to_team
            continue
        if pl not in best or x['score'] > best[pl]['score']:
            best[pl] = x
    members = {}
    for pl, team in spins.items():
        members.setdefault(team, set()).add(pl)
    for pl, x in best.items():
        members.setdefault(x['team'], set()).add(pl)
    order = [t for t in SMACK_TEAMS if t in members] + sorted(t for t in members if t not in SMACK_TEAMS)
    out = []
    for i, team in enumerate(order):
        rows = []
        for pl in members[team]:
            x = best.get(pl, {})
            possible = x.get('possible', 13)
            score = x.get('score', 0)
            rows.append({'score': score, 'possible': possible, 'done': bool(x) and score >= possible,
                         'steps': (x.get('steps') or [0] * n_steps), 'at': x.get('first_at', ''), 'late': pl in late})
        all_rows = sorted(rows, key=lambda r: (r['late'], -r['score'], r['at']))
        rows = [r for r in all_rows if count_late or not r['late']]
        total, possible = sum(r['score'] for r in rows), sum(r['possible'] for r in rows)
        n_done = sum(r['done'] for r in rows)
        step_counts = [sum(1 for r in rows if r['steps'][k]) for k in range(n_steps)]
        out.append({'team': team, 'color': WHEEL_COLORS[SMACK_TEAMS.index(team) % len(WHEEL_COLORS)] if team in SMACK_TEAMS
                    else WHEEL_COLORS[i % len(WHEEL_COLORS)],
                    'members': all_rows, 'n_late': len(all_rows) - len(rows), 'n': len(rows), 'n_done': n_done, 'points': total, 'possible': possible,
                    'pct': 100 * total / possible if possible else 0, 'steps': step_counts,
                    'all_done_at': max(r['at'] for r in rows if r['done']) if rows and n_done == len(rows) else ''})
    out.sort(key=lambda t: (not t['all_done_at'], t['all_done_at'] or '', -t['pct'], -t['n_done']))
    return out


def _race_html(count_late=False):
    teams = _team_progress(count_late=count_late)
    winners = [t for t in teams if t['all_done_at']]
    rows = ''
    late_tip = "joined after GO: doesn't hold the team back"
    for i, t in enumerate(teams):
        c = t['color']
        rank = ('🏆' if i == 0 else MEDALS[i] if i < 3 else '✅') if t['all_done_at'] else f'<span style="color:#999">{i + 1}</span>'
        segs = ''.join(
            f'<div style="flex:1;background:#ECE8E1;border-radius:6px;height:34px;position:relative;overflow:hidden;'
            f'{"outline:2px dashed #999;outline-offset:-2px;opacity:.6" if m["late"] and not count_late else ""}" '
            f'title="{late_tip if m["late"] and not count_late else ""}">'
            f'<div style="position:absolute;left:0;top:0;bottom:0;width:{100 * m["score"] / m["possible"]:.0f}%;'
            f'background:{"#2E7D50" if m["done"] else c};opacity:{1 if m["done"] else .75}"></div>'
            f'<div style="position:absolute;inset:0;display:flex;align-items:center;justify-content:center;color:#fff;'
            f'font-weight:900;font-size:16px;text-shadow:0 0 3px #0006">{"✓" if m["done"] else "⏰" if m["late"] and not count_late else ""}</div></div>'
            for m in t['members'])
        strip = ''.join(
            f'<div style="flex:1;text-align:center;border-radius:5px;padding:3px 0;font-size:11px;'
            f'background:{"#2E7D50" if k_n == t["n"] else c if k_n else "#ECE8E1"};'
            f'opacity:{1 if k_n in (0, t["n"]) else .35 + .5 * k_n / max(t["n"], 1)};color:{"#fff" if k_n else "#999"}">'
            f'{name}<br><b style="font-size:13px">{k_n}/{t["n"]}</b></div>'
            for name, k_n in zip(SMACK_STEPS, t['steps']))
        right = (f'<div style="color:#2E7D50;font-weight:900;font-size:17px">🏁 ALL FINISHED</div>'
                 f'<div style="color:#2E7D50;font-weight:700">{_since_go(t["all_done_at"])}</div>' if t['all_done_at'] else
                 f'<div style="font-size:30px;font-weight:900;color:{c}">{t["pct"]:.0f}%</div>'
                 f'<div style="font-size:12px;color:#888">of team points</div>')
        rows += (f'<div style="display:flex;gap:14px;align-items:center;background:#fff;border:3px solid {c if not t["all_done_at"] else "#2E7D50"};'
                 f'border-radius:12px;padding:12px 16px;margin-bottom:10px">'
                 f'<div style="font-size:30px;width:44px;text-align:center">{rank}</div>'
                 f'<div style="flex:1;min-width:0"><div style="display:flex;justify-content:space-between;align-items:baseline">'
                 f'<span style="font-size:21px;font-weight:900;color:{c}">{html.escape(t["team"])}</span>'
                 f'<span style="font-size:15px;color:#444"><b>{t["n_done"]} of {t["n"]}</b> finished'
                 f'{" · +" + str(t["n_late"]) + " late ⏰" if t["n_late"] else ""}</span></div>'
                 f'<div style="display:flex;gap:5px;margin:7px 0">{segs}</div>'
                 f'<div style="display:flex;gap:4px">{strip}</div></div>'
                 f'<div style="width:150px;text-align:center">{right}</div></div>')
    if not rows:
        rows = '<div style="padding:14px;color:#999;font-style:italic">No teams yet: students spin the wheel first.</div>'
    banner = ''
    if winners:
        w = winners[0]
        banner = (f'<div style="background:#2E7D50;color:#fff;border-radius:12px;padding:14px 20px;margin-bottom:12px;'
                  f'font-size:24px;font-weight:900">🏆 {html.escape(w["team"])} wins — everyone finished, '
                  f'{_since_go(w["all_done_at"])}!</div>')
    return (_header('🤝 SMACKDOWN · TEAM RACE', f'{_light_chip("bootstrap_smackdown")} · The first team with <b>every member</b> '
                    'at 13 points wins · one block per teammate · the strip shows how many teammates have each step'
                    + ('' if count_late else ' · ⏰ = joined after GO, doesn\'t hold the team back'))
            + banner + rows)


def smackdown_team_race(interval=10, count_late=False):
    """Live collective board: each team's progress toward EVERYONE finishing, with no student names.
    One block per teammate (green ✓ = all 13 points), the share of the team's possible points earned,
    and how many teammates have each step. The first team with every member finished wins."""
    _game_dir('bootstrap_smackdown')
    return _live(lambda: _race_html(count_late), interval, 'Smackdown Team Race', 'bootstrap_smackdown_team_race.html')

SUMMARY_FIELDS = [
    ('ideas', '🔑 Key ideas about our dataset',
     'What are the variables? What do the data show? Anything surprising about this data set?'),
    ('conclusions', '📣 Our conclusions',
     'What does the slope mean in real units? What is the 95% CI? Is the slope real, and how do you know?'),
]


def _summary_dir(game):
    path = os.path.join(_game_dir(game), 'summaries')
    os.makedirs(path, exist_ok=True)
    try:
        os.chmod(path, 0o777)
    except PermissionError:
        pass
    return path


def load_summaries(game='bootstrap_smackdown'):
    out = []
    for p in glob.glob(os.path.join(GAMES_ROOT, game, 'summaries', '*.json')):
        try:
            with open(p) as f:
                out.append(json.load(f))
        except (ValueError, OSError):
            pass
    return out


def summary_box(game='bootstrap_smackdown'):
    """A box at the end of the student sheet: type the key ideas and conclusions, then Post.
    Posting again replaces your earlier summary. Uses the notebook's team_name and my_name."""
    import ipywidgets as widgets
    from IPython.display import display, HTML
    ns = _user_ns()
    team, name = str(ns.get('team_name', '') or ''), str(ns.get('my_name', '') or '')
    if team in ('', '...', 'Ellipsis'):
        display(HTML(f'<b style="color:{CHERRY}">⚠️ Run your team\'s dataset cell first, then this cell again.</b>'))
        return
    if name in ('', '...', 'Ellipsis'):
        display(HTML(f'<b style="color:{CHERRY}">⚠️ Fill in my_name at the top of the notebook, run it, then this cell again.</b>'))
        return
    folder = _summary_dir(game)
    path = os.path.join(folder, f'{_slug(team)}__{_player()}.json')
    old = {}
    for p in glob.glob(os.path.join(folder, f'*__{_player()}.json')):    # your last post, if any
        try:
            with open(p) as f:
                old = json.load(f)
        except (ValueError, OSError):
            pass
    boxes = {}
    parts = [widgets.HTML(f'<div style="background:linear-gradient(135deg,#1a1a2e,#2d0a16);color:{GOLD};padding:10px 16px;'
                          f'border-radius:10px;font-weight:900;font-size:1.25em">📝 Team summary — {html.escape(team)} · '
                          f'<span style="color:#fff">{html.escape(name)}</span></div>')]
    for key, label, hint in SUMMARY_FIELDS:
        boxes[key] = widgets.Textarea(value=old.get(key, ''), placeholder=hint,
                                      layout=widgets.Layout(width='100%', height='120px'))
        parts += [widgets.HTML(f'<div style="font-weight:800;font-size:1.1em;margin-top:8px">{label}</div>'
                               f'<div style="color:#666;font-size:.92em">{hint}</div>'), boxes[key]]
    post = widgets.Button(description='📤 Post to the class board', layout=widgets.Layout(width='260px', height='38px'),
                          style={'button_color': CHERRY, 'text_color': 'white', 'font_weight': 'bold'})
    out = widgets.Output()

    def on_post(_):
        with out:
            out.clear_output()
            gate = _gate(game, allow_after_stop=True)        # summaries may still be posted after time's up
            if gate:
                display(HTML(gate))
                return
            texts = {k: b.value.strip() for k, b in boxes.items()}
            if sum(len(t.split()) for t in texts.values()) < 10:
                display(HTML(f'<b style="color:{CHERRY}">⚠️ Write a little more in both boxes (a sentence or two each), then Post.</b>'))
                return
            for p in glob.glob(os.path.join(folder, f'*__{_player()}.json')):   # switched teams: keep only one post
                if p != path:
                    os.remove(p)
            entry = dict(texts, team=team, name=name, player=_player(),
                         submitted=datetime.datetime.now().isoformat(timespec='seconds'))
            with open(path + '.tmp', 'w') as f:
                json.dump(entry, f)
            os.replace(path + '.tmp', path)
            display(HTML(f'<div style="color:#2E7D50;font-weight:bold;padding:6px 0">✅ Posted for {html.escape(team)}! '
                         'Edit and Post again any time; the newest version replaces the old one.</div>'))

    post.on_click(on_post)
    display(widgets.VBox(parts + [post, out], layout=widgets.Layout(border='2px solid #E0DDD6', padding='10px')))


_STOP = set("""
a about above after again against all also am an and any are as at be because been before being below between both
but by can could did do does doing done down during each even every few for from further get got had has have having
he her here hers him his how i if in into is it its itself just like lot lots made make many me more most much my
myself no nor not now of off on once only or other our out over own really same she should so some something such
than that the their them then there these they thing things this those through to too under until up us very was we
were what when where which while who whom why will with would you your yours i'm it's didn't don't wasn't couldn't
think felt feel bit kind way well one two first overall able still since though data dataset shows show means
""".split())


def _cloud(texts, n_words=50):
    from collections import Counter
    words = []
    for text in texts:
        words += [w.strip("'") for w in re.findall(r"[a-zA-Z][a-zA-Z'-]+", str(text).lower())]
    top = Counter(w for w in words if len(w) > 2 and w not in _STOP).most_common(n_words)
    if not top:
        return '<div style="color:#999;font-style:italic;padding:12px">The word cloud appears as summaries come in.</div>'
    biggest = top[0][1]
    palette = [CHERRY, '#221C1E', '#7A1626', '#5B4A50', '#8A5F00', '#2F5D8A']
    rng = np.random.RandomState(7)
    spans = ''
    for i in rng.choice(np.arange(len(top)), len(top), replace=False):
        word, n = top[i]
        spans += (f'<span title="{n}" style="font-size:{16 + 50 * np.sqrt(n / biggest):.0f}px;font-weight:'
                  f'{800 if n / biggest > 0.5 else 600};color:{palette[i % len(palette)]};margin:2px 10px;'
                  f'line-height:1.1;display:inline-block">{html.escape(word)}</span>')
    return f'<div style="text-align:center;padding:10px 6px">{spans}</div>'


def _summaries_html(game='bootstrap_smackdown'):
    posts = load_summaries(game)
    texts = [p.get(k, '') for p in posts for k, _, _ in SUMMARY_FIELDS]
    teams = {}
    for p in posts:
        teams.setdefault(p['team'], []).append(p)
    body = (f'<div style="background:#fff;border:1px solid #E0DDD6;border-radius:12px;margin-bottom:16px">'
            f'<div style="padding:8px 14px;font-weight:800;color:#888;font-size:13px;letter-spacing:1px">WHAT THE CLASS IS SAYING · '
            f'{len(posts)} summar{"y" if len(posts) == 1 else "ies"} from {len(teams)} team{"" if len(teams) == 1 else "s"}</div>'
            f'{_cloud(texts)}</div>')
    for team in sorted(teams):
        cards = ''
        for p in sorted(teams[team], key=lambda q: q.get('name', '').lower()):
            fields = ''.join(f'<div style="font-weight:800;color:{CHERRY};font-size:13px;margin-top:6px">{label}</div>'
                             f'<div style="font-size:15px;line-height:1.4">{html.escape(p.get(k, "")).replace(chr(10), "<br>")}</div>'
                             for k, label, _ in SUMMARY_FIELDS)
            cards += (f'<div style="background:#fff;border:1px solid #ddd;border-left:5px solid {CHERRY};border-radius:10px;'
                      f'padding:10px 14px"><div style="font-weight:900;font-size:17px">{html.escape(p.get("name", ""))}'
                      f'<span style="float:right;color:#aaa;font-size:12px;font-weight:400">{str(p.get("submitted", ""))[11:16]}</span></div>'
                      f'{fields}</div>')
        body += (f'<div style="background:#2d0a16;color:#fff;border-radius:10px;padding:9px 14px;margin:18px 0 10px;font-weight:800;'
                 f'font-size:18px">{html.escape(team)}<span style="float:right;color:{GOLD}">{len(teams[team])} posted</span></div>'
                 f'<div style="display:grid;grid-template-columns:repeat(auto-fill,minmax(380px,1fr));gap:12px">{cards}</div>')
    return _header('📝 SMACKDOWN · TEAM SUMMARIES', 'Key ideas and conclusions, by team and name · word cloud of every summary') + body


def smackdown_summaries(interval=15):
    """Live board of the summaries students post from the end of their sheet: a word cloud of everything
    posted at the top, then each team's summaries by name."""
    _summary_dir('bootstrap_smackdown')
    return _live(_summaries_html, interval, 'Smackdown Summaries', 'bootstrap_smackdown_summaries.html')


def smackdown_summary():
    "Student side: the summary box for the Bootstrap Smackdown."
    summary_box('bootstrap_smackdown')



# ============================================================================ class section + saving results
SECTION = None


def _norm_section(which):
    if which is None:
        return None
    text = str(which).strip()
    return text.zfill(2) if text.isdigit() else text


def set_section(which):
    "Label this session's boards and saved results with a class section, e.g. set_section('08')."
    global SECTION
    SECTION = _norm_section(which)
    print(f'Class section set to {SECTION}. Boards show it, and save_results() / reset_game() label files with it.')


def _write_csv(path, header, rows):
    import csv
    def tidy(v):
        if isinstance(v, float) and v.is_integer():
            return int(v)
        return round(v, 4) if isinstance(v, float) else v
    with open(path, 'w', newline='', encoding='utf-8-sig') as f:     # -sig: Excel shows emoji and accents correctly
        w = csv.writer(f)
        w.writerow(header)
        w.writerows([[tidy(v) for v in row] for row in rows])
    return path


def save_results(game='bootstrap_smackdown', section=None):
    """Save the current boards to CSV files in this folder, labeled with the class section and date.
    bootstrap_smackdown -> ..._teams.csv, ..._players.csv, ..._roster.csv, ..._summaries.csv, bootstrap_smackdown_08.html
    neighbor_games      -> ..._scores.csv, ..._teams.csv (who was on each team), neighbor_games_08.html (the final board),
                           and canvas_neighbor_games_08.csv when the roster class_08.csv is in this folder
    Returns the list of files written."""
    section = _norm_section(section) or SECTION
    if not section:
        print("Set the class first, e.g. set_section('08') or save_results(section='08').")
        return []
    stem = f'{game}_{section}_{datetime.date.today():%Y-%m-%d}'
    written, extras = [], []
    if game == 'neighbor_games':
        scores = load(game)
        rows = []
        for rnd in NEIGHBOR_ROUNDS:
            for rank, e in enumerate(_best_per_team(scores, rnd), start=1):
                rows.append([section, rnd, rank, e['team'], round(e['score'], 3), e.get('k', ''),
                             ' '.join(e.get('features', []) or []), e.get('time', ''), 'yes' if e.get('manual') else ''])
        written.append(_write_csv(f'{stem}_scores.csv',
                                  ['section', 'round', 'rank', 'team', 'score_K', 'k', 'features', 'time', 'manual'], rows))
        rosters = load_neighbor_teams(game)
        rounds_done = {}
        for x in scores:
            rounds_done.setdefault(x['team'], set()).add(x.get('round'))
        extras.append(save_overview(game, section, quiet=True))
        if glob.glob(f'class_{section}.csv'):
            try:
                extras.append(neighbor_canvas(section))
            except Exception as e:
                print(f'(Canvas file not written: {e})')
        written.append(_write_csv(f'{stem}_teams.csv', ['section', 'team', 'members', 'n_members', 'rounds_submitted'],
                                  [[section, t, '; '.join(rosters.get(t, [])), len(rosters.get(t, [])),
                                    ' '.join(r for r in NEIGHBOR_ROUNDS if r in rounds_done.get(t, set()))]
                                   for t in sorted(set(rosters) | set(rounds_done), key=str.lower)]))
    elif game == 'bootstrap_smackdown':
        scores = [x for x in load(game) if x.get('round') == 'Smackdown']
        posts = load_summaries(game)
        posted = {p.get('player') for p in posts}
        teams = {}
        for x in scores:
            teams.setdefault(x['team'], []).append(x)
        team_rows, player_rows = [], []
        n = len(SMACK_STEPS)
        for team, members in teams.items():
            top = max(m['score'] for m in members)
            best = min((m for m in members if m['score'] == top), key=lambda m: m.get('first_at', ''))
            finished = [m for m in members if m['score'] >= m.get('possible', 13)]
            ci = best.get('ci') or ['', '']
            team_rows.append([team, top, best.get('possible', 13), best.get('first_at', '')[11:19] if finished else '',
                              len(members), len(finished), round(best.get('slope', float('nan')), 4), ci[0], ci[1]])
            firsts = []
            for k in range(n):
                stamped = [((m.get('step_times') or [''] * n)[k], i) for i, m in enumerate(members)]
                stamped = [t for t in stamped if t[0]]
                firsts.append(min(stamped)[1] if stamped else None)
            for i, m in enumerate(members):
                steps = (m.get('steps') or [0] * n)
                player_rows.append([section, team, m.get('name') or f'student {m.get("player", "")[:4]}', m['score'],
                                    *steps, sum(1 for f in firsts if f == i), m.get('checkins', 1),
                                    str(m.get('first_at', ''))[11:19], str(m.get('submitted', ''))[11:19],
                                    'yes' if m.get('player') in posted else ''])
        team_rows.sort(key=lambda r: (-r[1], r[3] or '99'))
        team_rows = [[section, rank, *r] for rank, r in enumerate(team_rows, start=1)]
        written.append(_write_csv(f'{stem}_teams.csv',
                                  ['section', 'rank', 'team', 'best_points', 'possible', 'finished_at', 'members',
                                   'members_finished', 'slope', 'ci_low', 'ci_high'], team_rows))
        player_rows.sort(key=lambda r: (r[1], -r[3], r[2]))
        written.append(_write_csv(f'{stem}_players.csv',
                                  ['section', 'team', 'name', 'points', *[f'step_{s_}' for s_ in SMACK_STEPS],
                                   'firsts', 'checkins', 'best_reached_at', 'last_checkin', 'summary_posted'], player_rows))
        race = _team_progress(game)
        written.append(_write_csv(f'{stem}_team_race.csv',
                                  ['section', 'place', 'team', 'members', 'members_finished', 'team_points', 'possible',
                                   'percent', 'all_finished_after_go'] + [f'have_{s_}' for s_ in SMACK_STEPS],
                                  [[section, i, t['team'], t['n'], t['n_done'], t['points'], t['possible'], round(t['pct'], 1),
                                    _since_go(t['all_done_at']) if t['all_done_at'] else '', *t['steps']]
                                   for i, t in enumerate(race, start=1)]))
        extras.append(save_overview(game, section, quiet=True))
        spins = load_team_spins()
        written.append(_write_csv(f'{stem}_roster.csv', ['section', 'team', 'name', 'spun_at', 'joined_after_go'],
                                  sorted([[section, x.get('team', ''), x.get('name', ''), str(x.get('at', ''))[11:16],
                                           'yes' if x.get('late') else '']
                                          for x in spins], key=lambda r: (r[1], r[2]))))
        written.append(_write_csv(f'{stem}_summaries.csv',
                                  ['section', 'team', 'name', 'key_ideas', 'conclusions', 'posted'],
                                  sorted([[section, p.get('team', ''), p.get('name', ''), p.get('ideas', ''),
                                           p.get('conclusions', ''), str(p.get('submitted', ''))[11:16]] for p in posts],
                                         key=lambda r: (r[1], r[2]))))
    else:
        print(f'Unknown game {game!r}.')
        return []
    written += [f for f in extras if f and f not in written]
    for f in written:
        if not f.startswith('canvas_'):                 # the Canvas file was announced with its download link
            print('💾 Saved', f)
    print('🔒 These files hold students\' names: download them from this folder and keep them off GitHub.')
    return written



# ============================================================================ Smackdown: team wheel
SMACK_TEAMS = ['Team Faithful 🌋', 'Team Galton 📐', 'Team Baby 👶', 'Team Census 🎓', 'Team Roads 🏎️']
WHEEL_COLORS = ['#D85A30', '#1D9E75', '#378ADD', '#BA7517', '#993556', '#534AB7', '#639922', '#A32D2D']


def _teams_dir(game='bootstrap_smackdown'):
    path = os.path.join(_game_dir(game), 'teams')
    os.makedirs(path, exist_ok=True)
    try:
        os.chmod(path, 0o777)
    except PermissionError:
        pass
    return path


def load_team_spins(game='bootstrap_smackdown'):
    out = []
    for p in glob.glob(os.path.join(GAMES_ROOT, game, 'teams', '*.json')):
        try:
            with open(p) as f:
                out.append(json.load(f))
        except (ValueError, OSError):
            pass
    return out


def _wheel_html(teams, target, name, already):
    uid = uuid_hex()
    data = json.dumps({'teams': teams, 'target': target, 'colors': (WHEEL_COLORS * 3)[:len(teams)],
                       'name': name, 'already': already}).replace('<', '\\u003c').replace('>', '\\u003e')
    return f"""
<div id="tw-{uid}" style="font-family:'Segoe UI',Arial,sans-serif;max-width:760px;border:1px solid #e2e2e2;border-radius:14px;overflow:hidden">
  <div style="background:linear-gradient(135deg,#1a1a2e,#2d0a16);color:{GOLD};padding:12px 20px;font-weight:900;font-size:20px;letter-spacing:1px">
    🎡 SPIN FOR YOUR TEAM <span style="float:right;color:#fff;font-size:14px;font-weight:600;margin-top:4px" class="tw-who"></span></div>
  <div style="display:flex;flex-wrap:wrap;background:#fff">
    <div style="padding:18px;text-align:center;flex:0 0 auto">
      <div style="position:relative;display:inline-block">
        <div style="position:absolute;top:-6px;left:50%;transform:translateX(-50%);font-size:30px;color:#222;z-index:5;line-height:1">&#9660;</div>
        <canvas class="tw-canvas" width="380" height="380" style="display:block;border-radius:50%;border:1px solid #ddd"></canvas>
      </div>
      <div style="margin-top:12px"><button class="tw-btn" style="background:{CHERRY};color:#fff;border:none;padding:11px 40px;font-size:17px;
        font-weight:800;border-radius:26px;cursor:pointer">Spin!</button></div>
    </div>
    <div style="flex:1;min-width:240px;padding:22px 20px;display:flex;flex-direction:column;justify-content:center">
      <div style="font-size:12px;color:#aaa;letter-spacing:2px;text-transform:uppercase">your team</div>
      <div class="tw-result" style="font-size:30px;font-weight:900;color:#ccc;margin:6px 0 10px">?</div>
      <div class="tw-note" style="color:#666;font-size:14px;line-height:1.4">Click <b>Spin!</b> to find out.</div>
    </div>
  </div>
</div>
<script>
(function () {{
  var D = {data};
  function init() {{
    var root = document.getElementById('tw-{uid}');
    if (!root) {{ setTimeout(init, 80); return; }}
    var canvas = root.querySelector('.tw-canvas'), ctx = canvas.getContext('2d');
    var n = D.teams.length, TWO = Math.PI * 2, slice = TWO / n, angle = 0, spinning = false;
    var cx = canvas.width / 2, cy = canvas.height / 2, R = cx - 6;
    root.querySelector('.tw-who').textContent = D.name;
    function draw(a, win) {{
      ctx.clearRect(0, 0, canvas.width, canvas.height);
      for (var i = 0; i < n; i++) {{
        var s = -Math.PI / 2 + a + i * slice;
        ctx.beginPath(); ctx.moveTo(cx, cy); ctx.arc(cx, cy, R, s, s + slice); ctx.closePath();
        ctx.fillStyle = (win !== undefined && win !== i) ? '#d9d9d9' : D.colors[i]; ctx.fill();
        ctx.strokeStyle = '#fff'; ctx.lineWidth = 3; ctx.stroke();
        ctx.save(); ctx.translate(cx, cy); ctx.rotate(s + slice / 2); ctx.textAlign = 'right';
        ctx.fillStyle = '#fff'; ctx.font = '700 17px "Segoe UI",Arial,sans-serif';
        ctx.fillText(D.teams[i].replace('Team ', ''), R - 12, 6); ctx.restore();
      }}
      ctx.beginPath(); ctx.arc(cx, cy, 20, 0, TWO); ctx.fillStyle = '#fff'; ctx.fill();
      ctx.strokeStyle = '#ccc'; ctx.lineWidth = 1; ctx.stroke();
    }}
    function reveal() {{
      draw(angle, D.target);
      var r = root.querySelector('.tw-result'); r.textContent = D.teams[D.target]; r.style.color = D.colors[D.target];
      root.querySelector('.tw-note').innerHTML = D.already
        ? 'You were already on this team. Spinning again always lands here.'
        : '🎉 Welcome to your team! Now run the cells below: your team\\'s data loads automatically.';
    }}
    function spin() {{
      if (spinning) return; spinning = true;
      var btn = root.querySelector('.tw-btn'); btn.disabled = true; btn.style.opacity = '0.4';
      var goal = -((D.target + 0.5) * slice) + (Math.random() - 0.5) * slice * 0.5;
      while (goal <= angle) goal += TWO;
      goal += (6 + Math.floor(Math.random() * 3)) * TWO;
      var a0 = angle, dur = 4200, t0 = performance.now();
      function frame(t) {{
        var p = Math.min((t - t0) / dur, 1);
        angle = a0 + (goal - a0) * (1 - Math.pow(1 - p, 5)); draw(angle);
        if (p < 1) {{ requestAnimationFrame(frame); return; }}
        spinning = false; btn.style.display = 'none'; reveal();
      }}
      requestAnimationFrame(frame);
    }}
    draw(0); root.querySelector('.tw-btn').addEventListener('click', spin);
  }}
  setTimeout(init, 50);
}})();
</script>"""


def uuid_hex():
    import uuid
    return uuid.uuid4().hex[:8]


def smackdown_spin(teams=None):
    """Student side: spin the wheel to join a team. The team is picked at random from the teams with the
    fewest members so far (so the class stays balanced) and saved; spinning again lands on the same team.
    Sets team_name in the notebook."""
    from IPython.display import display, HTML
    ns = _user_ns()
    teams = teams or SMACK_TEAMS
    name = str(ns.get('my_name', '') or '').strip()
    if name in ('', '...', 'Ellipsis'):
        display(HTML(f'<b style="color:{CHERRY}">⚠️ Fill in my_name above and run it, then spin.</b>'))
        return None
    folder = _teams_dir()
    mine = os.path.join(folder, f'{_player()}.json')
    already = False
    try:
        with open(mine) as f:
            team = json.load(f)['team']
        already = team in teams
    except (OSError, ValueError, KeyError):
        team = None
    if not already and not teams_are_open():
        display(HTML('<div style="font-family:sans-serif;border:2px solid #E0DDD6;border-radius:10px;padding:10px 14px">'
                     '<div style="font-size:1.35em;font-weight:900">🔒 Teams are closed.</div>'
                     '<div style="color:#555;margin-top:3px">The competition has started, so the wheel is closed to new players. '
                     'Ask your instructor to let you in, then run this cell again. To practice meanwhile, add a cell with '
                     '<code>team_name = \'Team Faithful 🌋\'</code> (or any team in the table below) and run the dataset cells; '
                     'your check-ins won\'t count until you\'re on a team.</div></div>'))
        return None
    if not already:
        counts = {t: 0 for t in teams}
        for x in load_team_spins():
            if x.get('team') in counts:
                counts[x['team']] += 1
        fewest = min(counts.values())
        team = str(np.random.choice([t for t in teams if counts[t] == fewest]))
        with open(mine + '.tmp', 'w') as f:
            json.dump({'team': team, 'name': name, 'player': _player(),
                       'at': datetime.datetime.now().isoformat(timespec='seconds'),
                       'late': bool(get_light().get('go_at'))}, f)
        os.replace(mine + '.tmp', mine)
    else:                                                   # keep the name current
        try:
            rec = json.load(open(mine)); rec['name'] = name
            json.dump(rec, open(mine, 'w'))
        except (OSError, ValueError):
            pass
    ns['team_name'] = team
    display(HTML(_wheel_html(teams, teams.index(team), name, already)))
    # team_name is set in the notebook; return nothing so the cell shows only the wheel


def _teams_html():
    spins = load_team_spins()
    by_team = {t: [] for t in SMACK_TEAMS}
    for x in spins:
        by_team.setdefault(x.get('team', '?'), []).append(x.get('name', '?') + (' ⏰' if x.get('late') else ''))
    cards = ''
    for i, (team, names) in enumerate(by_team.items()):
        color = WHEEL_COLORS[i % len(WHEEL_COLORS)]
        chips = ''.join(f'<div style="padding:4px 10px;border-radius:14px;background:#F7F5F0;margin:3px 0;font-size:15px">'
                        f'{html.escape(n)}</div>' for n in sorted(names, key=str.lower))
        cards += (f'<div style="min-width:0;background:#fff;border:3px solid {color};border-radius:12px;overflow:hidden">'
                  f'<div style="background:{color};color:#fff;padding:9px 12px;font-weight:900;font-size:18px">{html.escape(team)}'
                  f'<span style="float:right">{len(names)}</span></div><div style="padding:8px 10px">'
                  f'{chips or "<i style=color:#aaa>waiting for spins…</i>"}</div></div>')
    door = '🔓 teams open' if teams_are_open() else '🔒 teams closed'
    return (_header('🎡 SMACKDOWN · TEAMS', f'{_light_chip("bootstrap_smackdown")} · {door} · ⏰ = joined after GO · Who spun onto which team · '
                    f'{len(spins)} student{"s" if len(spins) != 1 else ""} so far')
            + f'<div style="display:grid;grid-template-columns:repeat(auto-fit,minmax(170px,1fr));gap:10px;align-items:start">{cards}</div>')


def smackdown_teams(interval=8):
    "Live board of the team wheel: who spun onto which team, with counts."
    _teams_dir()
    return _live(_teams_html, interval, 'Smackdown Teams', 'bootstrap_smackdown_teams.html')


def move_to_team(name, team, game='bootstrap_smackdown'):
    "Instructor: move a student (by the name they entered) to another team, e.g. move_to_team('Priya', 'Team Roads 🏎️')."
    if team not in SMACK_TEAMS:
        print('Team must be one of:', ', '.join(SMACK_TEAMS))
        return
    hits = [p for p in glob.glob(os.path.join(_teams_dir(game), '*.json'))
            if str(json.load(open(p)).get('name', '')).strip().lower() == name.strip().lower()]
    if len(hits) != 1:
        print(f'{len(hits)} students named {name!r} have spun; ask them to tell you their exact name.' if hits
              else f'Nobody named {name!r} has spun yet.')
        return
    rec = json.load(open(hits[0])); rec['team'] = team
    json.dump(rec, open(hits[0], 'w'))
    print(f'Moved {name} to {team}. They should rerun their spin cell and the cells below it.')
