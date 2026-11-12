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

🃏 P-value Poker: the instructor deals a round (a null histogram with the observed statistic marked), each team
bets on the p-value, then the reveal: the closest bets take the points. Five rounds are ready; stop whenever you like.
State and bets live in .../challenges/pvalue_poker/<section>/ (state.json and bets/<round>__<team>.json).

    Students:   poker_hand()     poker_data(3)
    Instructor: poker_control('08')   poker_board('08')   poker_reset('08', confirm='08')

team_scores('08') gives each team's one-line game summary, shown in small print on the team boards.
"""
import os, glob, html, shutil, datetime, io, base64, functools

import numpy as np

import class_games as cg
import group_project as gp
from group_project import _dir, _read, _write, _now, _ns, _box, _show, _my_record, load_members, get_section
from class_games import _slug
from class_games import _player, _live, _norm_section, WHEEL_COLORS, CHERRY, GOLD, MEDALS

__all__ = ['bug_data', 'bug_check', 'bug_light', 'bug_board', 'bug_reset', 'BUGS',
           'poker_hand', 'poker_data', 'poker_control', 'poker_board', 'poker_reset', 'team_scores']

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


# ============================================================================ 🃏 P-value Poker
REPS = 10000                 # simulations behind each round's "true" p-value
POINTS = [5, 3, 2]           # closest bet, second, third; every other team that bet gets 1
BULLSEYE = 1.0               # a bet within this many percentage points earns +1


def _plants():
    from datascience import Table
    control = [18.2, 20.1, 19.4, 21.0, 17.8, 20.6, 19.0, 18.7]
    fertilizer = [19.9, 19.1, 21.8, 21.2, 18.6, 22.4, 20.5, 19.4]
    return Table().with_columns('Group', np.array(['Control'] * 8 + ['Fertilizer'] * 8), 'Height', np.array(control + fertilizer))


def _permuted_differences(values, is_first, rng):
    "Differences of means (first group − other group) after shuffling the group labels REPS times."
    out = np.empty(REPS)
    for i in range(REPS):
        mix = rng.permutation(is_first)
        out[i] = values[mix].mean() - values[~mix].mean()
    return out


@functools.lru_cache(maxsize=1)
def _rounds():
    "The five rounds. Each null distribution is simulated once, with a fixed seed, so every notebook agrees."
    rng = np.random.RandomState(2026)
    plants, genes = _plants(), bug_data()
    h, g = plants.column('Height'), plants.column('Group') == 'Fertilizer'
    e, t = genes.column('Expression'), genes.column('Tissue') == 'Tumor'
    rounds = [
        dict(title='The suspicious die 🎲',
             story='A die is rolled <b>60</b> times and lands on six <b>16</b> times. '
                   '<b>Null hypothesis:</b> the die is fair (chance of a six = 1/6).',
             stat='Number of sixes in 60 rolls', tail='16 or more sixes',
             observed=16, null=rng.binomial(60, 1 / 6, REPS).astype(float), bins=np.arange(-0.5, 25.5, 1),
             code="""model = make_array(1/6, 5/6)                     # six, not a six
sixes = make_array()
for i in np.arange(5000):
    sixes = np.append(sixes, round(60 * sample_proportions(60, model).item(0)))

p_value = np.count_nonzero(sixes >= 16) / 5000
p_value"""),
        dict(title="Mendel's peas 🌸",
             story='Mendel\'s model says <b>75%</b> of pea plants should have purple flowers. Of <b>929</b> plants, '
                   '<b>705</b> were purple (75.9%). <b>Null hypothesis:</b> the model is good; the gap is just chance.',
             stat='Distance between the sample % purple and 75', tail='a distance of 0.89 or more',
             observed=abs(100 * 705 / 929 - 75), null=np.abs(100 * rng.binomial(929, 0.75, REPS) / 929 - 75),
             bins=np.arange(0, 5.01, 0.25),
             code="""model = make_array(0.75, 0.25)                   # purple, white
observed = abs(100 * 705 / 929 - 75)
distances = make_array()
for i in np.arange(5000):
    purple = round(929 * sample_proportions(929, model).item(0))      # number of purple plants
    distances = np.append(distances, abs(100 * purple / 929 - 75))

p_value = np.count_nonzero(distances >= observed) / 5000
p_value"""),
        dict(title='Does the fertilizer work? 🌱',
             story='<b>8</b> plants got fertilizer and <b>8</b> did not. The fertilized plants averaged '
                   f'<b>{h[g].mean() - h[~g].mean():.2f} cm</b> taller. <b>Null hypothesis:</b> fertilizer makes no difference, '
                   'so the group labels could be shuffled.',
             stat='Fertilizer mean − control mean (cm), labels shuffled', tail=f'a difference of {h[g].mean() - h[~g].mean():.2f} cm or more',
             observed=h[g].mean() - h[~g].mean(), null=_permuted_differences(h, g, rng), bins=np.arange(-3, 3.01, 0.25),
             code="""plants = poker_data(3)

def difference(table, label):
    fert = table.where(label, 'Fertilizer').column('Height')
    ctrl = table.where(label, 'Control').column('Height')
    return np.mean(fert) - np.mean(ctrl)

observed = difference(plants, 'Group')
diffs = make_array()
for i in np.arange(2000):
    shuffled = plants.with_column('Shuffled', plants.sample(with_replacement=False).column('Group'))
    diffs = np.append(diffs, difference(shuffled, 'Shuffled'))

p_value = np.count_nonzero(diffs >= observed) / 2000
p_value"""),
        dict(title='Is the coin fair? 🪙',
             story='A coin is flipped <b>100</b> times and lands heads <b>57</b> times. <b>Null hypothesis:</b> the coin is fair. '
                   'Too many heads <i>or</i> too few would both be evidence against it.',
             stat='Distance between the number of heads and 50', tail='a distance of 7 or more (either direction)',
             observed=7, null=np.abs(rng.binomial(100, 0.5, REPS) - 50).astype(float), bins=np.arange(-0.5, 20.5, 1),
             code="""model = make_array(0.5, 0.5)                     # heads, tails
distances = make_array()
for i in np.arange(5000):
    heads = round(100 * sample_proportions(100, model).item(0))     # number of heads
    distances = np.append(distances, abs(heads - 50))

p_value = np.count_nonzero(distances >= 7) / 5000
p_value"""),
        dict(title='Tumor vs. normal tissue 🧬 — the final hand',
             story='In the <code>genes</code> table from Fix the Bug (60 tumor and 60 normal samples), the tumor samples average '
                   f'<b>{e[t].mean() - e[~t].mean():.2f}</b> higher in expression. <b>Null hypothesis:</b> tissue type makes no difference.',
             stat='Tumor mean − normal mean, labels shuffled', tail=f'a difference of {e[t].mean() - e[~t].mean():.2f} or more',
             observed=e[t].mean() - e[~t].mean(), null=_permuted_differences(e, t, rng), bins=np.arange(-1.2, 2.01, 0.1),
             code="""genes = poker_data(5)

def difference(table, label):
    tumor = table.where(label, 'Tumor').column('Expression')
    normal = table.where(label, 'Normal').column('Expression')
    return np.mean(tumor) - np.mean(normal)

observed = difference(genes, 'Tissue')
diffs = make_array()
for i in np.arange(2000):
    shuffled = genes.with_column('Shuffled', genes.sample(with_replacement=False).column('Tissue'))
    diffs = np.append(diffs, difference(shuffled, 'Shuffled'))

p_value = np.count_nonzero(diffs >= observed) / 2000
p_value"""),
    ]
    for r in rounds:
        r['p'] = 100 * float(np.count_nonzero(r['null'] >= r['observed'] - 1e-9)) / REPS      # in percent
    return rounds


@functools.lru_cache(maxsize=16)
def _hand_image(k, reveal):
    "The round's null histogram as an <img> tag; at the reveal, the tail is shaded."
    from matplotlib.figure import Figure
    r = _rounds()[k - 1]
    fig = Figure(figsize=(7.2, 3.3), dpi=100)
    ax = fig.subplots()
    counts, edges = np.histogram(r['null'], bins=r['bins'])
    pct = 100 * counts / REPS
    in_tail = edges[1:] > r['observed'] + 1e-9            # the bars at or beyond the observed value
    colors = ['#F0A500' if (reveal and tail) else '#4A78B0' for tail in in_tail]
    ax.bar(edges[:-1], pct, width=np.diff(edges), align='edge', color=colors, edgecolor='white', linewidth=0.6)
    ax.axvline(r['observed'], color='#C8102E', linewidth=2.5)
    ax.annotate(f'observed = {r["observed"]:.3g}', xy=(r['observed'], ax.get_ylim()[1]), xytext=(4, -12),
                textcoords='offset points', color='#C8102E', fontsize=10, fontweight='bold',
                ha='left' if r['observed'] < np.mean(ax.get_xlim()) else 'right')
    ax.set_xlabel(r['stat'], fontsize=10)
    ax.set_ylabel('% of simulations', fontsize=10)
    ax.set_title(f'What the null hypothesis predicts ({REPS:,} simulations)', fontsize=11)
    ax.grid(axis='y', alpha=0.3)
    for side in ('top', 'right'):
        ax.spines[side].set_visible(False)
    fig.tight_layout()
    buf = io.BytesIO()
    fig.savefig(buf, format='png')
    return (f'<img alt="null distribution histogram" style="max-width:100%;border:1px solid #E0DDD6;border-radius:8px" '
            f'src="data:image/png;base64,{base64.b64encode(buf.getvalue()).decode()}">')


# ---------------------------------------------------------------------------- state, bets, scores
def _poker_dir(section, *more):
    return _dir('challenges', 'pvalue_poker', _norm_section(section), *more)


def _poker_state(section):
    st = _read(os.path.join(gp.ROOT, gp.TERM, 'challenges', 'pvalue_poker', _norm_section(section), 'state.json'))
    return st if st and 'round' in st else {'round': 0, 'phase': 'waiting'}


def _set_poker_state(section, rnd, phase):
    _write(os.path.join(_poker_dir(section), 'state.json'), {'round': rnd, 'phase': phase, 'at': _now()})


def _bets(section, k):
    "team -> the bet record for round k."
    out = {}
    for p in glob.glob(os.path.join(gp.ROOT, gp.TERM, 'challenges', 'pvalue_poker', _norm_section(section), 'bets', f'{k}__*.json')):
        rec = _read(p)
        if rec and 'bet' in rec:
            out[rec['team']] = rec
    return out


def _revealed(section):
    st = _poker_state(section)
    return list(range(1, st['round'] + (1 if st['phase'] in ('reveal', 'over') else 0)))


def _round_results(section, k):
    "Round k, closest bet first: [{'team', 'bet', 'by', 'off', 'points', 'bullseye'}, ...]."
    truth = _rounds()[k - 1]['p']
    rows = sorted(({'team': t, 'bet': b['bet'], 'by': b.get('by', ''), 'off': round(abs(b['bet'] - truth), 2)}
                   for t, b in _bets(section, k).items()), key=lambda r: (r['off'], r['team']))
    for i, r in enumerate(rows):
        place = next(j for j, x in enumerate(rows) if x['off'] == r['off'])          # ties share the better place
        r['bullseye'] = r['off'] <= BULLSEYE
        r['points'] = (POINTS[place] if place < len(POINTS) else 1) + (1 if r['bullseye'] else 0)
    return rows


def _poker_totals(section):
    "[(team, points, rounds played)], best first, over the rounds revealed so far."
    cfg = get_section(section) or {'teams': []}
    total = {t: [0, 0] for t in cfg['teams']}
    for k in _revealed(section):
        for r in _round_results(section, k):
            got = total.setdefault(r['team'], [0, 0])
            got[0] += r['points']
            got[1] += 1
    return sorted(((t, p, n) for t, (p, n) in total.items()), key=lambda x: (-x[1], x[0]))


def _ordinal(n):
    return f'{n}{"th" if 10 <= n % 100 <= 20 else {1: "st", 2: "nd", 3: "rd"}.get(n % 10, "th")}'


def team_scores(section):
    "team -> one short line of game results, e.g. '🐛 Fix the Bug 7/7 (1st) · 🃏 P-value Poker 9 pts (2nd)'."
    section = _norm_section(section)
    out = {}
    bugs = [t for t in _team_progress(section) if t['n']]
    for i, t in enumerate(bugs):
        place = next(j for j, x in enumerate(bugs) if (x['n'], x['reached']) == (t['n'], t['reached'])) + 1
        out.setdefault(t['team'], []).append(f'🐛 Fix the Bug {t["n"]}/{len(BUGS)} ({_ordinal(place)})')
    poker = [x for x in _poker_totals(section) if x[2]]
    for team, pts, _ in poker:
        place = next(j for j, x in enumerate(poker) if x[1] == pts) + 1
        out.setdefault(team, []).append(f'🃏 P-value Poker {pts} pt{"" if pts == 1 else "s"} ({_ordinal(place)})')
    return {team: ' · '.join(lines) for team, lines in out.items()}


def _pct(x):
    return f'{x:.1f}%'


def _results_html(section, k, me=None):
    r = _rounds()[k - 1]
    rows = ''
    for i, x in enumerate(_round_results(section, k)):
        rows += (f'<tr style="{"background:#FDF3D7;font-weight:700" if x["team"] == me else ""}">'
                 f'<td style="padding:4px 10px">{MEDALS[i] if i < 3 else ""}</td>'
                 f'<td style="padding:4px 10px">{html.escape(x["team"])}</td>'
                 f'<td style="padding:4px 10px;text-align:right">{_pct(x["bet"])}</td>'
                 f'<td style="padding:4px 10px;text-align:right;color:#888">off by {x["off"]:.1f}</td>'
                 f'<td style="padding:4px 10px;font-weight:800;color:{CHERRY}">+{x["points"]}{" 🎯" if x["bullseye"] else ""}</td></tr>')
    n_tail = int(round(r['p'] * REPS / 100))
    return (f'<div style="font-size:1.25em;font-weight:900;color:#2E7D50;margin:8px 0 2px">🃏 The p-value is about {_pct(r["p"])}</div>'
            f'<div style="color:#555;margin-bottom:6px">{n_tail:,} of the {REPS:,} simulations showed {r["tail"]} '
            f'(the gold bars). Your own simulation will land close to this, not exactly on it.</div>'
            f'<table style="border-collapse:collapse;font-size:15px">{rows or "<tr><td><i>no bets this round</i></td></tr>"}</table>')


def _standings_html(section, me=None):
    rows = ''.join(f'<span style="display:inline-block;margin:3px 6px 0 0;padding:4px 11px;border-radius:14px;'
                   f'background:{"#FDF3D7" if t == me else "#F7F5F0"};font-size:14px"><b>{html.escape(t)}</b> {p}</span>'
                   for t, p, n in _poker_totals(section))
    return f'<div style="margin-top:10px"><span style="font-size:11px;color:#999;letter-spacing:1px">STANDINGS</span><br>{rows}</div>'


# ---------------------------------------------------------------------------- student side
def poker_data(k):
    "Student: the data table for a round (rounds 3 and 5 use one). It unlocks at that round's reveal."
    rec = _my_record()
    if rec and k not in _revealed(rec['section']):
        _show(_box(f'🔒 Round {k}\'s data unlocks at the reveal.', 'Place your bet first!'))
        return None
    if k == 3:
        return _plants()
    if k == 5:
        return bug_data()
    print(f'Round {k} has no data table: everything you need is in the story.')


def poker_hand():
    """Student: your team's seat at the table. Shows the round your instructor has dealt, takes your team's bet on the
    p-value, and shows the reveal. Click Refresh (or run the cell again) when your instructor moves on."""
    import ipywidgets as widgets
    from IPython.display import display
    rec = _my_record()
    if not rec or not rec.get('team'):
        _show(_box('🎡 You are not on a team yet.', 'Open GroupProject_Teams, sign in and spin first; then run this cell again.', CHERRY))
        return
    section, team, name = rec['section'], rec['team'], rec.get('name', '')
    view, note = widgets.HTML(), widgets.HTML()
    bet = widgets.BoundedFloatText(value=5.0, min=0, max=100, step=0.1, description='Our bet (%):',
                                   style={'description_width': '90px'}, layout=widgets.Layout(width='200px'))
    place = widgets.Button(description='💰 Place our bet', layout=widgets.Layout(width='170px', height='36px'),
                           style={'button_color': CHERRY, 'text_color': 'white', 'font_weight': 'bold'})
    again = widgets.Button(description='🔄 Refresh', layout=widgets.Layout(width='110px', height='36px'))
    betting = widgets.HBox([bet, place, note], layout=widgets.Layout(gap='10px', align_items='center'))
    wrap = '<div style="font-family:sans-serif;max-width:780px">%s</div>'

    def head(k, r):
        return (f'<div style="background:linear-gradient(135deg,#1a1a2e,#2d0a16);color:{GOLD};padding:10px 16px;border-radius:10px;'
                f'font-weight:900;font-size:18px">🃏 Round {k} of {len(_rounds())} · {r["title"]}'
                f'<span style="float:right;color:#fff;font-size:13px;font-weight:600;margin-top:3px">{html.escape(team)}</span></div>'
                f'<div style="font-size:15px;margin:10px 0;line-height:1.45">{r["story"]}</div>')

    def refresh(_=None):
        st = _poker_state(section)
        k, phase = st['round'], st['phase']
        betting.layout.display = 'flex' if phase == 'bet' else 'none'
        if phase == 'waiting' or k == 0:
            view.value = wrap % _box('🃏 Waiting for the dealer…', 'When your instructor deals the first round, click Refresh.')
            return
        r = _rounds()[k - 1]
        if phase == 'bet':
            mine = _bets(section, k).get(team)
            note.value = (f'<span style="font-family:sans-serif;color:#2E7D50;font-weight:700">Your team\'s bet: {_pct(mine["bet"])} '
                          f'(placed by {html.escape(mine.get("by", ""))}). You can change it until the reveal.</span>' if mine else
                          '<span style="font-family:sans-serif;color:#888">No bet yet. Agree as a team, then one of you places it.</span>')
            view.value = wrap % (head(k, r) + _hand_image(k, False) +
                                 f'<div style="font-size:15px;margin-top:8px">🤔 <b>What is the p-value?</b> The chance, if the null '
                                 f'hypothesis is true, of seeing <b>{r["tail"]}</b>. Bet a percent from 0 to 100.</div>')
        else:
            code = html.escape(r['code'])
            done = phase == 'over'
            view.value = wrap % (
                head(k, r) + _hand_image(k, True) + _results_html(section, k, team) + _standings_html(section, team)
                + f'<div style="margin-top:12px;font-weight:800">🔬 Check it yourself: copy this into the Round {k} cell below and run it.</div>'
                  f'<pre style="background:#F7F5F0;border-radius:8px;padding:10px 12px;font-size:13px;line-height:1.35;overflow-x:auto">{code}</pre>'
                + (f'<div style="font-size:1.2em;font-weight:900;color:{CHERRY}">🏁 Game over! Final standings are above.</div>' if done
                   else '<div style="color:#888">Click Refresh when your instructor deals the next round.</div>'))

    def on_place(_):
        st = _poker_state(section)
        if st['phase'] == 'bet':
            _write(os.path.join(_poker_dir(section, 'bets'), f'{st["round"]}__{_slug(team)}.json'),
                   {'team': team, 'round': st['round'], 'bet': round(float(bet.value), 1), 'by': name, 'at': _now()})
        refresh()

    place.on_click(on_place)
    again.on_click(refresh)
    refresh()
    display(widgets.VBox([view, betting, again]))


# ---------------------------------------------------------------------------- instructor
def poker_control(section):
    "Instructor: the dealer's buttons for one class — deal a round (opens betting), reveal it, or end the game."
    import ipywidgets as widgets
    from IPython.display import display
    section = _norm_section(section)
    n = len(_rounds())
    deal = widgets.Button(layout=widgets.Layout(width='240px', height='42px'),
                          style={'button_color': '#2E7D50', 'text_color': 'white', 'font_weight': 'bold'})
    show = widgets.Button(description='🃏 Reveal the p-value', layout=widgets.Layout(width='200px', height='42px'),
                          style={'button_color': CHERRY, 'text_color': 'white', 'font_weight': 'bold'})
    end = widgets.Button(description='⏹ End game', layout=widgets.Layout(width='120px', height='42px'))
    status = widgets.HTML()

    def refresh():
        st = _poker_state(section)
        k, phase = st['round'], st['phase']
        deal.description = f'▶ Deal round {k + 1} (open betting)' if k < n else 'No more rounds'
        deal.disabled = phase in ('bet', 'over') or k >= n
        show.disabled = phase != 'bet'
        end.disabled = phase in ('over', 'waiting')
        said = {'waiting': 'Not started. Deal round 1 when the teams are ready.',
                'bet': f'Round {k}: betting is OPEN ({len(_bets(section, k))} bets in). Reveal when the teams have bet.',
                'reveal': f'Round {k}: revealed.' + (' Deal the next round, or end the game.' if k < n else ' That was the last round: end the game.'),
                'over': 'Game over. Final standings are on the board.'}[phase]
        status.value = f'<div style="font-family:system-ui,sans-serif;font-size:15px;margin-left:8px"><b>Class {section}</b> · {said}</div>'

    def on_deal(_):
        st = _poker_state(section)
        if st['phase'] in ('waiting', 'reveal') and st['round'] < n:
            _set_poker_state(section, st['round'] + 1, 'bet')
        refresh()

    def on_show(_):
        st = _poker_state(section)
        if st['phase'] == 'bet':
            _set_poker_state(section, st['round'], 'reveal')
        refresh()

    def on_end(_):
        st = _poker_state(section)
        if st['phase'] in ('bet', 'reveal'):
            _set_poker_state(section, st['round'] if st['phase'] == 'reveal' else st['round'] - 1, 'over')
        refresh()

    deal.on_click(on_deal)
    show.on_click(on_show)
    end.on_click(on_end)
    refresh()
    display(widgets.HBox([deal, show, end, status], layout=widgets.Layout(align_items='center', gap='10px')))


def _poker_board_html(section):
    section = _norm_section(section)
    st = _poker_state(section)
    k, phase = st['round'], st['phase']
    cfg = get_section(section) or {'teams': []}
    chip = {'waiting': '⏳ waiting for the first deal', 'bet': f'💰 Round {k}: place your bets!',
            'reveal': f'🃏 Round {k}: the reveal', 'over': '🏁 Game over'}[phase]
    head = (f'<div style="background:linear-gradient(135deg,#1a1a2e 0%,#2d0a16 100%);padding:18px 24px;border-radius:12px;'
            f'margin-bottom:14px"><div style="color:{GOLD};font-size:2em;font-weight:900;letter-spacing:2px">🃏 P-VALUE POKER'
            f'<span style="float:right;color:#fff;font-size:.6em;margin-top:10px">Class {section}</span></div>'
            f'<div style="color:#ddd"><b>{chip}</b> · closest bet {POINTS[0]} pts, then {POINTS[1]}, {POINTS[2]}, and 1 for every '
            f'other bet · 🎯 +1 within {BULLSEYE:g} point</div></div>')
    body = ''
    if phase == 'over':
        totals = _poker_totals(section)
        if totals and totals[0][1]:
            body = (f'<div style="background:#2E7D50;color:#fff;border-radius:12px;padding:14px 20px;margin-bottom:12px;font-size:24px;'
                    f'font-weight:900">🏆 {html.escape(totals[0][0])} wins with {totals[0][1]} points!</div>')
    if k:
        r = _rounds()[k - 1]
        if phase == 'bet':
            bets = _bets(section, k)
            chips = ''.join(f'<span style="display:inline-block;margin:3px 6px 0 0;padding:5px 12px;border-radius:14px;font-size:15px;'
                            f'background:{"#2E7D50" if t in bets else "#ECE8E1"};color:{"#fff" if t in bets else "#999"}">'
                            f'{"✔" if t in bets else "…"} {html.escape(t)}</span>' for t in cfg['teams'])
            side = (f'<div style="font-size:17px;margin-bottom:8px">🤔 <b>What is the p-value?</b><br>The chance, if the null hypothesis '
                    f'is true, of seeing <b>{r["tail"]}</b>.</div><div style="font-size:11px;color:#999;letter-spacing:1px">'
                    f'BETS IN: {len(bets)} of {len(cfg["teams"])}</div>{chips}')
        else:
            side = _results_html(section, k)
        body += (f'<div style="background:#fff;border:1px solid #E0DDD6;border-radius:12px;padding:14px 18px">'
                 f'<div style="font-size:20px;font-weight:900;color:{CHERRY}">Round {k} of {len(_rounds())} · {r["title"]}</div>'
                 f'<div style="font-size:16px;margin:8px 0 12px;line-height:1.45">{r["story"]}</div>'
                 f'<div style="display:flex;flex-wrap:wrap;gap:20px;align-items:flex-start"><div style="flex:1 1 480px;min-width:0">'
                 f'{_hand_image(k, phase != "bet")}</div><div style="flex:1 1 300px;min-width:0">{side}</div></div></div>')
    return f'<div style="font-family:system-ui,sans-serif">{head}{body}{_standings_html(section) if cfg["teams"] else ""}</div>'


def poker_board(section, interval=4):
    "Instructor: the live P-value Poker board for one class: the round on the table, who has bet, the reveal, and standings."
    section = _norm_section(section)
    _poker_dir(section, 'bets')
    _live(lambda: _poker_board_html(section), interval, f'P-value Poker · class {section}', f'pvalue_poker_{section}.html')


def poker_reset(section, confirm=''):
    "Instructor: clear one class's P-value Poker game to play again. Files are archived, not deleted."
    section = _norm_section(section)
    if confirm != section:
        print(f"Nothing changed. To clear class {section}, run poker_reset('{section}', confirm='{section}').")
        return
    folder = _poker_dir(section)
    files = glob.glob(os.path.join(folder, 'state.json')) + glob.glob(os.path.join(folder, 'bets', '*.json'))
    archive = os.path.join(_dir('_archive'), f'pvalue_poker_{section}_{datetime.datetime.now():%Y%m%d-%H%M%S}')
    os.makedirs(archive, exist_ok=True)
    for p in files:
        shutil.move(p, archive)
    print(f'Class {section}: P-value Poker cleared ({len(files)} files archived in {archive}).')
