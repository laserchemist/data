"""
class_games.py — live class competitions (Neighbor Games, Bootstrap Smackdown).

Lives in the course repo at 'Fall 2026/shared-public/' (delivered by nbgitpuller).
Scores are written to the hub folder every student can write:
    /home/jovyan/shared-public/games/<game>/
one small file per student per round, so simultaneous submissions never overwrite each other.

Students:   submit_button('Arena', 'arena_rmse')          (Neighbor Games)
            smackdown_check_in()   smackdown_summary()     (Bootstrap Smackdown)
Instructor: neighbor_scoreboard()   smackdown_scoreboard()   smackdown_players()   smackdown_summaries()   manual_score(...)   reset_game(...)
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


def reset_game(game):
    "Clear a game's scoreboard (and posted summaries). Everything is moved to an archive folder, not deleted."
    folder = os.path.join(GAMES_ROOT, game)
    files = glob.glob(os.path.join(folder, '*.json'))
    posts = glob.glob(os.path.join(folder, 'summaries', '*.json'))
    if not files and not posts:
        print(f'{game}: nothing to clear.')
        return
    archive = os.path.join(GAMES_ROOT, '_archive', f"{game}_{datetime.datetime.now():%Y%m%d-%H%M%S}")
    os.makedirs(os.path.join(archive, 'summaries'), exist_ok=True)
    for p in files:
        shutil.move(p, archive)
    for p in posts:
        shutil.move(p, os.path.join(archive, 'summaries'))
    print(f'{game}: cleared {len(files)} scores and {len(posts)} summaries (saved in {archive}).')


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
    return (f'<div style="background:linear-gradient(135deg,#1a1a2e 0%,#2d0a16 100%);padding:18px 24px;border-radius:12px;'
            f'margin-bottom:14px"><div style="color:{GOLD};font-size:2em;font-weight:900;letter-spacing:2px">{title}</div>'
            f'<div style="color:#ddd">{subtitle}</div></div>')


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
        done_at = first[11:19] if top >= possible and first else ''
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
    return (_header('🥊 BOOTSTRAP SMACKDOWN', 'Live standings · points, then fastest to finish (⚡ = time all 13 points were first reached)')
            + f'<div style="background:#fff;border:1px solid #E0DDD6;border-radius:10px;overflow:hidden">'
              f'<table style="width:100%;border-collapse:collapse">{rows}</table></div>')


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
    return (_header('🥊 SMACKDOWN · PLAYERS', 'Each member\'s steps · ⭐ = first on the team to earn that step · 🏁 = all 13 points · 📝 = summary posted')
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
