"""
class_games.py — live class competitions (Neighbor Games, Bootstrap Smackdown).

Lives in the course repo at 'Fall 2026/shared-public/' (delivered by nbgitpuller).
Scores are written to the hub folder every student can write:
    /home/jovyan/shared-public/games/<game>/
one small file per student per round, so simultaneous submissions never overwrite each other.

Students:   submit_button('Arena', 'arena_rmse')          (Neighbor Games)
            smackdown_spin()   smackdown_check_in()   smackdown_summary()     (Bootstrap Smackdown)
Instructor: stoplight()   neighbor_scoreboard()   smackdown_teams()   smackdown_scoreboard()   smackdown_players()   smackdown_summaries()   manual_score(...)   reset_game(...)
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
          f'Boards are empty and the start light is back to its starting state (🔴 for the Smackdown), '
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
                gate = _gate(game)
                if gate:
                    display(HTML(gate))
                    return
                score = ns.get(score_var)
                if score is None or score is Ellipsis:
                    raise ValueError(f'Run the {round_name} cells first — {score_var} has no value yet.')
                team = ns.get('team_name', '')
                submit(game, team, round_name, score, extra_fn() if extra_fn else None)
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
GATED_GAMES = {'bootstrap_smackdown'}     # these start on red: no submissions until the instructor turns the light green


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
        rec.setdefault('go_at', now)
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


def _gate(game, allow_after_stop=False):
    "None if students may submit now; otherwise the message to show them."
    rec = get_light(game)
    if rec['state'] == 'green':
        return None
    if rec['state'] == 'red' and rec.get('go_at'):
        if allow_after_stop:
            return None
        msg = ('🛑', "Time's up — the competition has stopped.",
               'Your last check-in stays on the board. Your instructor can turn the light green again.')
    elif rec['state'] == 'yellow':
        msg = ('🟡', 'Get ready — almost time!', 'Nothing is submitted until the light turns green. Run this cell again after GO.')
    else:
        msg = ('🔴', "The competition hasn't started yet.",
               'Find your teammates and look over your data. Nothing is submitted until your instructor turns the light '
               'green; your work stays in your notebook. Run this cell again after GO.')
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
    Back to 🔴 after GO = time's up: no more check-ins. The light is saved, so every notebook sees the same state."""
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
    busy = threading.Event()

    def show():
        rec = get_light(game)
        el = _elapsed(rec)
        if rec['state'] == 'green':
            view.value = _light_html('green', 'GO!', f'Check-ins are open · ⏱ {_clock(el)}')
        elif rec['state'] == 'yellow':
            view.value = _light_html('yellow', 'Get ready…', 'Teams together? Check-ins open on green.')
        elif el is not None:
            view.value = _light_html('red', "Time's up", f'Stopped after {_clock(el)} · check-ins are closed')
        else:
            view.value = _light_html('red', 'Not started', 'Students spin and find their teams · check-ins are closed')

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
    show()
    threading.Thread(target=tick, daemon=True).start()
    display(widgets.VBox([view, widgets.HBox([b_red, b_yel, b_go], layout=widgets.Layout(gap='10px', margin='12px 0 0 0'))],
                         layout=widgets.Layout(border='2px solid #E0DDD6', padding='14px')))


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
    teams = {s['team'] for s in scores}
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
                rows += (f'<tr><td style="padding:6px 10px;font-size:20px;text-align:center;width:40px">{medal}</td>'
                         f'<td style="padding:6px 4px"><div style="font-weight:700;font-size:15px">{html.escape(e["team"])}{detail}</div>'
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
    return (_header('🌿 THE NEIGHBOR GAMES', f'Live leaderboard · {len(teams)} team{"s" if len(teams) != 1 else ""} on the board')
            + f'<div style="display:flex;gap:10px;flex-wrap:wrap;margin-bottom:14px">{strip}</div>' + boards)


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
    bootstrap_smackdown -> ..._teams.csv, ..._players.csv, ..._roster.csv, ..._summaries.csv
    neighbor_games      -> ..._scores.csv
    Returns the list of files written."""
    section = _norm_section(section) or SECTION
    if not section:
        print("Set the class first, e.g. set_section('08') or save_results(section='08').")
        return []
    stem = f'{game}_{section}_{datetime.date.today():%Y-%m-%d}'
    written = []
    if game == 'neighbor_games':
        scores = load(game)
        rows = []
        for rnd in NEIGHBOR_ROUNDS:
            for rank, e in enumerate(_best_per_team(scores, rnd), start=1):
                rows.append([section, rnd, rank, e['team'], round(e['score'], 3), e.get('k', ''),
                             ' '.join(e.get('features', []) or []), e.get('time', ''), 'yes' if e.get('manual') else ''])
        written.append(_write_csv(f'{stem}_scores.csv',
                                  ['section', 'round', 'rank', 'team', 'score_K', 'k', 'features', 'time', 'manual'], rows))
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
        spins = load_team_spins()
        written.append(_write_csv(f'{stem}_roster.csv', ['section', 'team', 'name', 'spun_at'],
                                  sorted([[section, x.get('team', ''), x.get('name', ''), str(x.get('at', ''))[11:16]]
                                          for x in spins], key=lambda r: (r[1], r[2]))))
        written.append(_write_csv(f'{stem}_summaries.csv',
                                  ['section', 'team', 'name', 'key_ideas', 'conclusions', 'posted'],
                                  sorted([[section, p.get('team', ''), p.get('name', ''), p.get('ideas', ''),
                                           p.get('conclusions', ''), str(p.get('submitted', ''))[11:16]] for p in posts],
                                         key=lambda r: (r[1], r[2]))))
    else:
        print(f'Unknown game {game!r}.')
        return []
    for f in written:
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
    if not already:
        counts = {t: 0 for t in teams}
        for x in load_team_spins():
            if x.get('team') in counts:
                counts[x['team']] += 1
        fewest = min(counts.values())
        team = str(np.random.choice([t for t in teams if counts[t] == fewest]))
        with open(mine + '.tmp', 'w') as f:
            json.dump({'team': team, 'name': name, 'player': _player(),
                       'at': datetime.datetime.now().isoformat(timespec='seconds')}, f)
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
        by_team.setdefault(x.get('team', '?'), []).append(x.get('name', '?'))
    cards = ''
    for i, (team, names) in enumerate(by_team.items()):
        color = WHEEL_COLORS[i % len(WHEEL_COLORS)]
        chips = ''.join(f'<div style="padding:4px 10px;border-radius:14px;background:#F7F5F0;margin:3px 0;font-size:15px">'
                        f'{html.escape(n)}</div>' for n in sorted(names, key=str.lower))
        cards += (f'<div style="min-width:0;background:#fff;border:3px solid {color};border-radius:12px;overflow:hidden">'
                  f'<div style="background:{color};color:#fff;padding:9px 12px;font-weight:900;font-size:18px">{html.escape(team)}'
                  f'<span style="float:right">{len(names)}</span></div><div style="padding:8px 10px">'
                  f'{chips or "<i style=color:#aaa>waiting for spins…</i>"}</div></div>')
    return (_header('🎡 SMACKDOWN · TEAMS', f'{_light_chip("bootstrap_smackdown")} · Who spun onto which team · '
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
