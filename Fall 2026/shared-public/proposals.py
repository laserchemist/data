"""
proposals.py — the Group Project research proposal, written by each team in GroupProject_Proposal.

Lives next to group_project.py in 'Fall 2026/shared-public/'. The team, section, members, roles and claimed
dataset come from what the team already saved in GroupProject_Teams; students write only the proposal itself.
One file per team, saved with the section's data:

    /home/jovyan/shared-public/group_project/<TERM>/proposals/<section>/<team>.json
    /home/jovyan/shared-public/group_project/<TERM>/proposals/<section>/_history/<team>__v<N>.json   (earlier versions)

Any teammate can open and edit the team's proposal. "Save draft" keeps work in progress; "Submit" checks that every
part is there. If two teammates edit at once, the second save is stopped instead of overwriting the first.

Students:   team_proposal()
Instructor: proposals_board('08')   export_proposals_html('08')   save_proposals('08')
            close_proposals('08')   open_proposals('08')   team_proposal(section='08', team='JAWN')
"""
import os, glob, html, csv, shutil, datetime

import group_project as gp
from group_project import (_dir, _read, _write, _now, _ns, _box, _show, _my_record, _team_card, _team_claim,
                           _flag, get_section, load_members, team_sheet)
from class_games import _player, _slug, _live, _norm_section, WHEEL_COLORS, CHERRY, GOLD

__all__ = ['team_proposal', 'proposals_board', 'export_proposals_html', 'save_proposals', 'close_proposals',
           'open_proposals', 'load_proposal', 'TOOLBOX']

TOOLBOX = ['🎲 Hypothesis test with a simulated p-value',
           '📈 Regression with bootstrap confidence intervals',
           '🧭 Nearest neighbors (classification or prediction)']
TOOL_SHORT = {TOOLBOX[0]: '🎲 Hypothesis test', TOOLBOX[1]: '📈 Regression + bootstrap', TOOLBOX[2]: '🧭 Nearest neighbors'}
N_SOURCES, MIN_SOURCES = 4, 1   # data: the project data set is source 1; more are optional
N_CITES, MIN_CITES = 5, 3       # literature citations
LIMIT = 4000                    # characters in one written part

# The written parts, in order: (key, heading, hint, box height)
PARTS = [
    ('question', '❓ Research question',
     'The one main question your data can answer. Make it specific: name the variables and the groups or places.', '70px'),
    ('plan', '🗺️ Research plan',
     'How will you research the topic? What background will you read, which variables will you use, what will you compare '
     'or predict, and how will your team divide the work?', '140px'),
    ('wrangling', '🧹 Data wrangling',
     'What must be done to the data before you can analyze it? For example: choosing columns, filtering rows with .where, '
     'turning dates or text into numbers, grouping, joining two tables, handling missing values.', '110px'),
    ('tests', '🔬 Planned tests',
     'For each question you will test: the null hypothesis, the alternative, and the test statistic. For a regression or '
     'nearest-neighbor question: what you will predict, from which variables, and how you will judge it.', '140px'),
]


# ============================================================================ storage
def _path(section, team):
    return os.path.join(_dir('proposals', _norm_section(section)), f'{_slug(team)}.json')


def load_proposal(section, team):
    "A team's saved proposal (None if nothing is saved yet)."
    return _read(os.path.join(gp.ROOT, gp.TERM, 'proposals', _norm_section(section), f'{_slug(team)}.json'))


def _members(section, team):
    return [{'name': m.get('name', ''), 'role': m.get('role', '')} for m in load_members(section) if m['team'] == team]


def _missing(p):
    "What a proposal still needs before it can be submitted."
    out = []
    if not p.get('title', '').strip():
        out.append('a project title')
    for key, head, _, _ in PARTS:
        if len(p.get(key, '').strip()) < 15:
            out.append(head.split(' ', 1)[1].lower())
    n = sum(1 for s in p.get('sources', []) if s.get('name', '').strip())
    if n < MIN_SOURCES:
        out.append('your project data set under data sources')
    cites = [c for c in p.get('literature', []) if c.get('citation', '').strip()]
    done = sum(1 for c in cites if len(c['citation'].strip()) >= 20 and len(c.get('why', '').strip()) >= 10)
    if done < MIN_CITES:
        out.append(f'at least {MIN_CITES} literature citations, each with how it supports your study (you have {done} complete)')
    if not p.get('toolbox'):
        out.append('at least one part of the data science toolbox')
    return out


def _save(section, team, fields, status, by, loaded_version):
    """Save a team's proposal. Returns (True, record) or (False, the newer record a teammate saved)."""
    section = _norm_section(section)
    old = load_proposal(section, team)
    if old and old.get('version', 0) != loaded_version:
        return False, old
    claim = _team_claim(section, team)
    rec = dict(fields, section=section, team=team, status=status, version=(old or {}).get('version', 0) + 1,
               dataset=claim['dataset'] if claim else '', members=_members(section, team),
               saved_by=by, saved_at=_now())
    rec['submitted_at'] = rec['saved_at'] if status == 'submitted' else ''
    if old:                                               # keep every earlier version
        hist = _dir('proposals', section, '_history')
        _write(os.path.join(hist, f'{_slug(team)}__v{old.get("version", 0)}.json'), old)
    _write(_path(section, team), rec)
    try:
        gp.save_team_sheets(section)
    except Exception:
        pass
    return True, rec


def proposal_summary(section, team):
    "A short dict for the team sheet and boards: status, title, version, who saved it and when (None if not started)."
    p = load_proposal(section, team)
    if not p:
        return None
    return {k: p.get(k) for k in ('status', 'title', 'question', 'literature', 'plan', 'sources', 'wrangling', 'tests', 'toolbox',
                                  'version', 'saved_by', 'saved_at', 'submitted_at')}


# ============================================================================ student side
_P = {}             # (section, team) -> the form's widgets, made once so re-running the cell keeps what was typed


def _when(stamp):
    return stamp[5:16].replace('T', ' ') if stamp else ''


def team_proposal(section=None, team=None):
    """Student: your team's research proposal. Team, members, roles and your claimed data set are filled in for you;
    write the rest together. Save a draft any time; Submit when every part is done. Any teammate can edit it.
    Instructor: team_proposal(section='08', team='JAWN') opens a team's form, to enter or fix it for them."""
    import ipywidgets as widgets
    from IPython.display import display, HTML, clear_output
    if section and team:
        section, me = _norm_section(section), 'instructor'
        if team not in (get_section(section) or {}).get('teams', []):
            print(f'Class {section} teams are:', ', '.join((get_section(section) or {}).get('teams', [])) or '(none)')
            return
    else:
        rec = _my_record()
        if not rec or not rec.get('team'):
            _show(_box('🎡 You are not on a team yet.', 'Open GroupProject_Teams, sign in and spin first; then run this cell again.', CHERRY))
            return
        section, team, me = rec['section'], rec['team'], rec.get('name', '')
    claim = _team_claim(section, team)
    if not claim:
        _show(_team_card(section, team, me) + _box('📂 Your team has not chosen its project yet.',
              'Choose it in GroupProject_Teams (Step 4) first; then run this cell again.', CHERRY))
        return
    key = (section, team)
    if key not in _P:
        w = {'title': widgets.Text(placeholder='e.g. Does fertilizer use explain stream nitrate levels in Pennypack Creek?',
                                   layout=widgets.Layout(width='780px'))}
        for k, _, _, h in PARTS:
            w[k] = widgets.Textarea(layout=widgets.Layout(width='780px', height=h))
        w['literature'] = [(widgets.Textarea(placeholder=f'Citation {i + 1}: Author, A. B., & Author, C. (Year). Title of the article. '
                                                         'Journal Name, volume(issue), pages.', layout=widgets.Layout(width='780px', height='48px')),
                            widgets.Text(placeholder='Link or DOI', layout=widgets.Layout(width='300px')),
                            widgets.Text(placeholder='How it supports our study (one line)', layout=widgets.Layout(width='472px')))
                           for i in range(N_CITES)]
        w['sources'] = [(widgets.Text(placeholder='What it is: another data set you will use, and who publishes it', layout=widgets.Layout(width='400px')),
                         widgets.Text(placeholder='Link (https://…)', layout=widgets.Layout(width='370px'))) for _ in range(N_SOURCES)]
        w['toolbox'] = [widgets.Checkbox(value=False, description=t, indent=False, layout=widgets.Layout(width='520px')) for t in TOOLBOX]
        w['version'] = 0
        _P[key] = w
        _fill(w, load_proposal(section, team), claim)
    w = _P[key]
    head, status, out = widgets.HTML(), widgets.HTML(), widgets.Output()
    save = widgets.Button(description='💾 Save draft', layout=widgets.Layout(width='150px', height='38px'))
    submit = widgets.Button(description='🚀 Submit proposal', layout=widgets.Layout(width='190px', height='38px'),
                            style={'button_color': CHERRY, 'text_color': 'white', 'font_weight': 'bold'})
    latest = widgets.Button(description='⬇️ Load the latest saved version', layout=widgets.Layout(width='260px', height='38px'))

    def fields():
        return {'title': ' '.join(w['title'].value.split())[:200],
                **{k: w[k].value.strip()[:LIMIT] for k, _, _, _ in PARTS},
                'literature': [{'citation': ' '.join(a.value.split())[:600], 'link': b.value.strip()[:500], 'why': ' '.join(c.value.split())[:400]}
                               for a, b, c in w['literature'] if a.value.strip() or b.value.strip() or c.value.strip()],
                'sources': [{'name': a.value.strip()[:300], 'link': b.value.strip()[:500]} for a, b in w['sources']
                            if a.value.strip() or b.value.strip()],
                'toolbox': [c.description for c in w['toolbox'] if c.value]}

    def show_status():
        p = load_proposal(section, team)
        head.value = _team_card(section, team, me)
        if not p:
            text = '📝 Nothing saved yet. Write together, and save a draft as you go.'
        elif p['status'] == 'submitted':
            text = (f'✅ <b>Submitted</b> by {html.escape(p.get("saved_by", ""))} on {_when(p.get("submitted_at"))} '
                    f'(version {p.get("version")}). You can still improve it and submit again.')
        else:
            text = (f'📝 <b>Draft</b> saved by {html.escape(p.get("saved_by", ""))} on {_when(p.get("saved_at"))} '
                    f'(version {p.get("version")}). Not submitted yet.')
        if p and p.get('version', 0) != w['version']:
            text += (f'<br><b style="color:{CHERRY}">⚠️ A teammate saved a newer version. Click "Load the latest saved version" '
                     'to see it (copy anything you typed that you want to keep first).</b>')
        is_open = (get_section(section) or {}).get('proposals_open', True)
        if not is_open:
            text += f'<br><b style="color:{CHERRY}">🔒 Proposals are closed. Ask your instructor if you need to make a change.</b>'
        save.disabled = submit.disabled = not is_open and me != 'instructor'
        status.value = f'<div style="font-family:sans-serif;font-size:14px;margin:8px 0;max-width:780px">{text}</div>'

    def say(text, good):
        with out:
            clear_output(wait=True)
            display(HTML(f'<div style="font-family:sans-serif;font-weight:bold;max-width:780px;color:{"#2E7D50" if good else CHERRY}">{text}</div>'))

    def store(state):
        if not (get_section(section) or {}).get('proposals_open', True) and me != 'instructor':
            say('🔒 Proposals are closed.', False)
            return show_status()
        f = fields()
        need = _missing(f) if state == 'submitted' else []
        if need:
            state = 'draft'
        if state == 'draft' and not any([f['title'], f['sources'][1:], f['literature'], f['toolbox']] + [f[k] for k, _, _, _ in PARTS]):
            say('Nothing to save yet.', False)
            return show_status()
        was = (load_proposal(section, team) or {}).get('status')
        ok, rec = _save(section, team, f, state, me, w['version'])
        if not ok:
            say(f'⚠️ Not saved: {html.escape(rec.get("saved_by", "a teammate"))} saved a newer version on {_when(rec.get("saved_at"))}. '
                'Copy anything you typed that you want to keep, click "Load the latest saved version", then add it back.', False)
        else:
            w['version'] = rec['version']
            if need:
                say('⚠️ Not submitted yet. Still needed: ' + html.escape('; '.join(need))
                    + f'. Your work was saved as a draft (version {rec["version"]}).', False)
            elif state == 'submitted':
                say(f'🚀 Submitted! {html.escape(team)}\'s proposal is in (version {rec["version"]}).', True)
            elif was == 'submitted':
                say(f'💾 Saved as a draft (version {rec["version"]}). It is no longer marked as submitted: '
                    'click Submit proposal when your changes are done.', False)
            else:
                say(f'💾 Draft saved (version {rec["version"]}).', True)
        show_status()

    def on_latest(_):
        _fill(w, load_proposal(section, team), claim)
        say('⬇️ Loaded the latest saved version.', True)
        show_status()

    save.on_click(lambda _: store('draft'))
    submit.on_click(lambda _: store('submitted'))
    latest.on_click(on_latest)
    show_status()

    def label(title, hint):
        return widgets.HTML(f'<div style="font-family:sans-serif;max-width:780px;margin-top:12px"><div style="font-weight:800;'
                            f'color:{CHERRY};font-size:15px">{title}</div><div style="color:#666;font-size:13px">{hint}</div></div>')

    data_line = widgets.HTML(f'<div style="font-family:sans-serif;font-size:14px;margin-top:4px">📂 Your project data set: '
                             f'<b>{html.escape(claim["dataset"])}</b> (source 1 below)</div>')
    items = [head, data_line,
             label('📌 Project title', 'Short and specific: a reader should know what you are studying.'), w['title'],
             label(*PARTS[0][1:3]), w['question'],
             label(f'📖 Literature (at least {MIN_CITES} citations)', 'Published work that your study builds on: peer-reviewed '
                   'articles, scientific reports, or government studies on your topic. Give the full citation, a link or DOI, '
                   'and one line on how it supports your question, your methods, or what you expect to find.')]
    for a, b, c in w['literature']:
        items += [a, widgets.HBox([b, c], layout=widgets.Layout(gap='8px', margin='0 0 8px 0'))]
    items += [label(*PARTS[1][1:3]), w['plan'],
              label('📊 Data sources', 'Your project data set is filled in. Add any other data you plan to use '
                    '(another data set, an agency\'s measurements), saying what it is and linking it.')]
    items += [widgets.HBox([a, b], layout=widgets.Layout(gap='8px')) for a, b in w['sources']]
    items += [label(*PARTS[2][1:3]), w['wrangling'], label(*PARTS[3][1:3]), w['tests'],
              label('🧰 Data science toolbox', 'Which tools from the course will you use? Tick every one that applies.')]
    items += w['toolbox']
    items += [status, widgets.HBox([save, submit, latest], layout=widgets.Layout(gap='10px')), out]
    display(widgets.VBox(items))


def _fill(w, p, claim):
    "Put a saved proposal (or a blank one, with the claimed data set as source 1) into the form."
    p = p or {}
    w['title'].value = p.get('title', '')
    for (a, b, c), x in zip(w['literature'], list(p.get('literature') or []) + [{}] * N_CITES):
        a.value, b.value, c.value = x.get('citation', ''), x.get('link', ''), x.get('why', '')
    for k, _, _, _ in PARTS:
        w[k].value = p.get(k, '')
    sources = list(p.get('sources') or [{'name': f'{claim["dataset"]} (Group_Project_Datasets notebook)', 'link': ''}])
    for (a, b), s in zip(w['sources'], sources + [{}] * N_SOURCES):
        a.value, b.value = s.get('name', ''), s.get('link', '')
    for c in w['toolbox']:
        c.value = c.description in (p.get('toolbox') or [])
    w['version'] = p.get('version', 0)


# ============================================================================ instructor
def close_proposals(section):
    "Instructor: stop teams from saving or submitting proposals (for a deadline). Their work stays saved."
    _flag(section, 'proposals_open', False, 'proposals are CLOSED. Teams can read theirs but not change it.')


def open_proposals(section):
    "Instructor: let teams save and submit proposals again (they are open unless you close them)."
    _flag(section, 'proposals_open', True, 'proposals are OPEN.')


def _rows(section):
    "[(team, color, proposal or None, members)] for one class, in team order."
    section = _norm_section(section)
    cfg = get_section(section) or {'teams': []}
    return [(t, WHEEL_COLORS[i % len(WHEEL_COLORS)], load_proposal(section, t), _members(section, t))
            for i, t in enumerate(cfg['teams'])]


def _text(s):
    return html.escape(s or '').replace('\n', '<br>')


def _cite(c):
    link = c.get('link', '').strip()
    if link.lower().startswith('10.'):
        link = 'https://doi.org/' + link
    shown = (f' <a href="{html.escape(link, quote=True)}" target="_blank">{html.escape(link)}</a>'
             if link.lower().startswith(('http://', 'https://')) else (f' {html.escape(link)}' if link else ''))
    why = f'<br><span style="color:#555555;font-style:italic">↳ {html.escape(c["why"])}</span>' if c.get('why') else ''
    return html.escape(c.get('citation', '')) + shown + why


def _link(s):
    name, link = html.escape(s.get('name', '')), s.get('link', '').strip()
    if link.lower().startswith(('http://', 'https://')):
        return f'{name} — <a href="{html.escape(link, quote=True)}" target="_blank">{html.escape(link)}</a>'
    return name + (f' — {html.escape(link)}' if link else '')


def _card(team, color, p, members, section, simple=False):
    """One team's proposal. simple=True uses only plain tables and inline styles (for the HTML file / Canvas)."""
    people = ', '.join(html.escape(m['name']) + (f' <span style="color:#777777">({html.escape(m["role"])})</span>' if m['role'] else '')
                       for m in sorted(members, key=lambda m: m['name'].lower())) or '<em>no members</em>'
    if not p:
        state, title = '<span style="color:#999999">⬜ not started</span>', '<em style="color:#999999">no proposal yet</em>'
    else:
        state = ('<span style="color:#2E7D50;font-weight:bold">✅ submitted ' + _when(p.get('submitted_at')) + '</span>'
                 if p['status'] == 'submitted' else '<span style="color:#B26A00;font-weight:bold">📝 draft ' + _when(p.get('saved_at')) + '</span>')
        title = html.escape(p.get('title') or 'untitled')
    claim = _team_claim(section, team)
    head = (f'<tr><td colspan="2" style="background-color:{color};color:#ffffff;padding:10px 12px;font-size:17px;font-weight:bold">'
            f'{html.escape(team)} <span style="font-weight:normal;font-size:13px">· section {section}</span></td></tr>'
            f'<tr><td colspan="2" style="padding:10px 12px 4px;font-size:18px;font-weight:bold;color:#1A1226">{title}</td></tr>'
            f'<tr><td colspan="2" style="padding:0 12px 8px;font-size:13px">{state} &nbsp;·&nbsp; 📂 '
            f'{html.escape(claim["dataset"]) if claim else "<em>no project chosen</em>"}</td></tr>')
    rows = [('👥 Team', people)]
    if p:
        rows.append((PARTS[0][1], _text(p.get('question'))))
        rows.append(('📖 Literature', '<ol style="margin:0;padding-left:20px">' + ''.join(f'<li style="margin-bottom:4px">{_cite(c)}</li>'
                     for c in p.get('literature', [])) + '</ol>' if p.get('literature') else '<em>none yet</em>'))
        rows.append((PARTS[1][1], _text(p.get('plan'))))
        rows.append(('📊 Data sources', '<ol style="margin:0;padding-left:20px">' + ''.join(f'<li>{_link(s)}</li>' for s in p.get('sources', []))
                     + '</ol>' if p.get('sources') else '<em>none yet</em>'))
        rows += [(head_text, _text(p.get(k))) for k, head_text, _, _ in PARTS[2:]]
        rows.append(('🧰 Toolbox', ' &nbsp; '.join(html.escape(TOOL_SHORT.get(t, t)) for t in p.get('toolbox', [])) or '<em>none ticked</em>'))
        need = _missing(p)
        if need and p['status'] != 'submitted':
            rows.append(('⚠️ Still needed', f'<span style="color:{CHERRY}">' + html.escape('; '.join(need)) + '</span>'))
    body = ''.join(f'<tr><td style="padding:6px 12px;vertical-align:top;font-weight:bold;font-size:13px;color:#555555;width:150px;'
                   f'border-top:1px solid #eeeeee">{k}</td><td style="padding:6px 12px;vertical-align:top;font-size:14px;'
                   f'border-top:1px solid #eeeeee">{v}</td></tr>' for k, v in rows)
    return (f'<table style="border-collapse:collapse;width:100%;border:2px solid {color};margin:0 0 18px 0;'
            f'background-color:#ffffff;font-family:Arial,sans-serif">{head}{body}</table>')


def _board_html(section):
    section = _norm_section(section)
    rows = _rows(section)
    cfg = get_section(section) or {}
    n_sub = sum(1 for _, _, p, _ in rows if p and p['status'] == 'submitted')
    n_draft = sum(1 for _, _, p, _ in rows if p and p['status'] != 'submitted')
    tools = {}
    for _, _, p, _ in rows:
        for t in (p or {}).get('toolbox', []):
            tools[TOOL_SHORT.get(t, t)] = tools.get(TOOL_SHORT.get(t, t), 0) + 1
    chips = ''.join(f'<span style="display:inline-block;margin:6px 6px 0 0;padding:6px 14px;border-radius:16px;background:#fff;'
                    f'font-size:14px;color:#222"><b>{html.escape(t)}</b> {n}</span>' for t, n in tools.items())
    status = ''.join(f'<span style="display:inline-block;margin:4px 6px 0 0;padding:4px 11px;border-radius:14px;font-size:13px;'
                     f'background:{"#2E7D50" if p and p["status"] == "submitted" else "#F0C27A" if p else "#ECE8E1"};'
                     f'color:{"#fff" if p and p["status"] == "submitted" else "#222" if p else "#888"}">{html.escape(t)}</span>'
                     for t, _, p, _ in rows)
    head = (f'<div style="background:linear-gradient(135deg,#1a1a2e 0%,#2d0a16 100%);padding:18px 24px;border-radius:12px;'
            f'margin-bottom:14px"><div style="color:{GOLD};font-size:2em;font-weight:900;letter-spacing:2px">📝 PROJECT PROPOSALS'
            f'<span style="float:right;color:#fff;font-size:.6em;margin-top:10px">Class {section}</span></div>'
            f'<div style="color:#ddd">✅ {n_sub} submitted · 📝 {n_draft} drafts · ⬜ {len(rows) - n_sub - n_draft} not started · '
            f'{"🔓 open" if cfg.get("proposals_open", True) else "🔒 closed"}</div>{status}<div>{chips}</div></div>')
    return f'<div style="font-family:system-ui,sans-serif">{head}' + ''.join(_card(t, c, p, m, section) for t, c, p, m in rows) + '</div>'


def proposals_board(section, interval=15):
    "Instructor: the live proposals board for one class: every team's proposal, with drafts and submissions as they come in."
    section = _norm_section(section)
    _live(lambda: _board_html(section), interval, f'Project Proposals · class {section}', f'group_project_proposals_{section}_live.html')


def export_proposals_html(section, title=None):
    """Instructor: save one class's proposals as an HTML file: group_project_proposals_<section>.html.
    Open it in a browser to read or print, or paste its contents into a Canvas page (HTML editor): it uses only
    plain tables and inline styles, which Canvas keeps."""
    section = _norm_section(section)
    rows = _rows(section)
    if not rows:
        print(f'Class {section} has no teams yet.')
        return
    title = title or f'Group Project Proposals · Section {section}'
    n_sub = sum(1 for _, _, p, _ in rows if p and p['status'] == 'submitted')
    body = (f'<h2>{html.escape(title)}</h2>\n<p style="color:#555555">{n_sub} of {len(rows)} teams submitted · '
            f'updated {datetime.datetime.now():%B %d, %Y at %H:%M}</p>\n'
            + '\n'.join(_card(t, c, p, m, section, simple=True) for t, c, p, m in rows))
    path = f'group_project_proposals_{section}.html'
    with open(path, 'w', encoding='utf-8') as f:
        f.write(f'<!DOCTYPE html><html><head><meta charset="utf-8"><title>{html.escape(title)}</title></head>'
                f'<body style="font-family:Arial,sans-serif;max-width:960px;margin:24px auto;padding:0 16px">{body}</body></html>')
    print(f'💾 Saved {path}: {len(rows)} teams, {n_sub} submitted.')
    print('   Open it in a new browser tab to read or print it. For Canvas: open the file in the Editor, copy everything '
          'between <body> and </body>, and paste it into the page\'s HTML editor (</>).')
    print('   🔒 It holds students\' names: fine inside your Canvas course, but keep it off GitHub.')


def save_proposals(section):
    "Instructor: one class's proposals as a spreadsheet: group_project_proposals_<section>.csv (one row per team)."
    section = _norm_section(section)
    path = f'group_project_proposals_{section}.csv'
    with open(path, 'w', newline='', encoding='utf-8-sig') as f:
        w = csv.writer(f)
        w.writerow(['section', 'team', 'status', 'title', 'dataset', 'members', 'research question', 'literature', 'research plan',
                    'data sources', 'data wrangling', 'planned tests', 'toolbox', 'saved by', 'saved at', 'version'])
        for team, _, p, members in _rows(section):
            claim = _team_claim(section, team)
            p = p or {}
            w.writerow([section, team, p.get('status', 'not started'), p.get('title', ''), claim['dataset'] if claim else '',
                        '; '.join(m['name'] + (f' ({m["role"]})' if m['role'] else '') for m in members),
                        p.get('question', ''),
                        '\n'.join(f'{i}. ' + c.get('citation', '') + (f' <{c["link"]}>' if c.get('link') else '')
                                  + (f' — {c["why"]}' if c.get('why') else '') for i, c in enumerate(p.get('literature', []), 1)),
                        p.get('plan', ''),
                        ' | '.join(s.get('name', '') + (f' <{s["link"]}>' if s.get('link') else '') for s in p.get('sources', [])),
                        p.get('wrangling', ''), p.get('tests', ''), '; '.join(TOOL_SHORT.get(t, t) for t in p.get('toolbox', [])),
                        p.get('saved_by', ''), p.get('saved_at', '').replace('T', ' '), p.get('version', '')])
    print(f'💾 Saved {path}. 🔒 It holds students\' names: keep it off GitHub.')
