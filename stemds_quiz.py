"""
stemds_quiz.py
==============
Self-contained quiz widget for STEMDS JupyterHub notebooks.
All lockout logic lives here — quiz notebooks stay clean (2 lines of student code).

Student notebook usage (all that students ever see or need)
────────────────────────────────────────────────────────────
    from stemds_quiz import open_quiz
    open_quiz("questions_quiz03.json", name, user)

Instructor configuration (edit this file only)
───────────────────────────────────────────────
    MAX_ATTEMPTS     — 1 (strict) or 2 (one retry per question)
    QUIZ_ID          — unique string per quiz, e.g. "Quiz03"
    INSTRUCTOR_USERS — set of hub usernames who bypass the lockout
    ATTEMPTS_DIR     — where attempt state files are stored

Instructor reset (run in any notebook or terminal on the hub)
─────────────────────────────────────────────────────────────
    from stemds_quiz import reset_attempt
    reset_attempt("jsmith", "Quiz03")     # reset one student
    reset_attempt("*",      "Quiz03")     # reset ALL students for this quiz

Returns from open_quiz()
────────────────────────
    A QuizResult object with:
        .score   — int, number correct (live, updates as student answers)
        .total   — int, total questions
        .locked  — bool, True if student was locked out before seeing quiz
    Supports tuple unpacking: score, total = open_quiz(...)
"""

import json, os, time, glob
import ipywidgets as widgets
from IPython.display import display, HTML

# ══════════════════════════════════════════════════════════════════════════════
#  INSTRUCTOR CONFIGURATION — edit these values for each quiz
# ══════════════════════════════════════════════════════════════════════════════

QUIZ_ID      = "Quiz03"   # ← unique ID for this quiz
MAX_ATTEMPTS = 1          # ← 1 = one shot; 2 = one retry per question

# Hub usernames that bypass the lockout entirely (can re-run freely)
INSTRUCTOR_USERS = {"laserchemist", "instructor", "admin"}

# Where attempt files are stored (shared-readwrite so kernel-restart-proof)
ATTEMPTS_DIR = "/home/jovyan/shared-readwrite/quiz_attempts"

# ── colours ────────────────────────────────────────────────────────────────────
_C = dict(
    cherry     = "#9B2335",
    navy       = "#1a3a5c",
    green      = "#1a6e2e",
    red        = "#c0392b",
    amber      = "#e67e22",
    blue       = "#2980b9",
    bg_q       = "#eaf4fb",
    bg_lock    = "#fdf3f3",
    bg_done    = "#f0fff0",
    pale_green = "#c8f7c5",
    white      = "#ffffff",
    light_grey = "#f5f5f5",
)

# ── persistence ────────────────────────────────────────────────────────────────

def _open_path(user, quiz_id):
    return os.path.join(ATTEMPTS_DIR, f"{user}_{quiz_id}.json")

def _state_path(user, quiz_id):
    return os.path.join(ATTEMPTS_DIR, f"{user}_{quiz_id}_state.json")

def _read_open_record(user, quiz_id):
    path = _open_path(user, quiz_id)
    if not os.path.exists(path):
        return None
    with open(path) as f:
        return json.load(f)

def _write_open_record(user, quiz_id, name):
    os.makedirs(ATTEMPTS_DIR, exist_ok=True)
    record = {"quiz_id": quiz_id, "user": user, "name": name,
              "timestamp": time.asctime()}
    with open(_open_path(user, quiz_id), "w") as f:
        json.dump(record, f, indent=2)

def _load_state(user, quiz_id):
    path = _state_path(user, quiz_id)
    if not os.path.exists(path):
        return None
    with open(path) as f:
        return json.load(f)

def _save_state(user, quiz_id, state):
    os.makedirs(ATTEMPTS_DIR, exist_ok=True)
    tmp = _state_path(user, quiz_id) + ".tmp"
    with open(tmp, "w") as f:
        json.dump(state, f, indent=2)
    os.replace(tmp, _state_path(user, quiz_id))

# ── public instructor tool ─────────────────────────────────────────────────────

def reset_attempt(user, quiz_id=None):
    """
    Remove attempt lock and state for one student or all students.

        reset_attempt("jsmith")          # reset jsmith for QUIZ_ID
        reset_attempt("jsmith", "Quiz03")
        reset_attempt("*", "Quiz03")     # reset everyone for Quiz03
    """
    quiz_id = quiz_id or QUIZ_ID
    removed = []

    if user == "*":
        pattern = os.path.join(ATTEMPTS_DIR, f"*_{quiz_id}.json")
        targets = glob.glob(pattern)
        targets += glob.glob(os.path.join(ATTEMPTS_DIR, f"*_{quiz_id}_state.json"))
    else:
        targets = [_open_path(user, quiz_id), _state_path(user, quiz_id)]

    for path in targets:
        if os.path.exists(path):
            os.remove(path)
            removed.append(os.path.basename(path))

    if removed:
        print(f"✅ Removed: {', '.join(removed)}")
    else:
        print(f"ℹ️  No attempt files found for user='{user}' quiz='{quiz_id}'")


# ══════════════════════════════════════════════════════════════════════════════
#  Question widget (internal)
# ══════════════════════════════════════════════════════════════════════════════

class _QuestionWidget:

    def __init__(self, idx, q_data, max_attempts, on_change, init_state=None):
        self.idx          = idx
        self.data         = q_data
        self.max_attempts = max_attempts
        self._on_change   = on_change

        self.attempts_used      = 0
        self.locked             = False
        self.answered_correctly = False

        if init_state:
            self.attempts_used      = init_state.get("attempts_used", 0)
            self.locked             = init_state.get("locked", False)
            self.answered_correctly = init_state.get("answered_correctly", False)

        self._build()

    def _build(self):
        answers   = self.data["answers"]
        remaining = self.max_attempts - self.attempts_used

        if self.locked and self.answered_correctly:
            hdr_bg, hdr_icon = _C["green"], "✅"
        elif self.locked:
            hdr_bg, hdr_icon = _C["red"],   "🔒"
        else:
            hdr_bg, hdr_icon = _C["cherry"], f"Q{self.idx + 1}"

        header = widgets.HTML(
            f'<div style="background:{hdr_bg};color:{_C["white"]};'
            f'border-radius:6px 6px 0 0;padding:8px 14px;font-weight:700;">'
            f'{hdr_icon} &nbsp; {self.data["question"]}</div>'
        )

        self._attempt_label = widgets.HTML(self._attempt_html(remaining))
        self._feedback      = widgets.Output()
        self._answer_btns   = []   # list of (html_widget, click_btn)
        btn_children        = []

        for i, ans in enumerate(answers):
            if self.locked and ans["correct"]:
                bg, fg, cursor = _C["pale_green"], "#1a3a2e", "default"
            elif self.locked:
                bg, fg, cursor = _C["light_grey"], "#888", "default"
            else:
                bg, fg, cursor = _C["light_grey"], "#222", "pointer"

            # HTML widget renders <code>, <em>, <b> etc. correctly
            html_w = widgets.HTML(
                f'<div style="background:{bg};color:{fg};'
                f'border-radius:6px;padding:9px 16px;'
                f'font-size:0.97em;font-weight:500;cursor:{cursor};'
                f'border:1px solid #ddd;line-height:1.4;">'
                f'{ans["answer"]}</div>'
            )
            html_w._ans_index = i
            html_w._bg_default = bg
            html_w._fg_default = fg

            # Narrow click button sits to the left; acts as the event source
            # Label is an arrow so the row still looks like a choice
            click_btn = widgets.Button(
                description = "▶",
                tooltip     = "Select this answer",
                layout      = widgets.Layout(width="44px", height="40px",
                                             margin="0px 4px 0px 0px"),
                style       = {"button_color": bg, "font_weight": "700"},
            )
            click_btn._ans_index = i
            click_btn._html_w    = html_w

            if not self.locked:
                click_btn.on_click(self._on_click)
            else:
                click_btn.disabled = True

            row = widgets.HBox(
                [click_btn, html_w],
                layout=widgets.Layout(width="96%", margin="2px 0",
                                      align_items="center")
            )
            self._answer_btns.append((html_w, click_btn))
            btn_children.append(row)

        btn_area = widgets.VBox(btn_children,
                                layout=widgets.Layout(padding="4px 10px"))

        if self.locked and self.answered_correctly:
            border = _C["green"]
        elif self.locked:
            border = _C["red"]
        else:
            border = _C["blue"]

        self.widget = widgets.VBox(
            [header, self._attempt_label, btn_area, self._feedback],
            layout=widgets.Layout(border=f"1px solid {border}",
                                  border_radius="8px", margin="10px 0")
        )

    def _attempt_html(self, remaining):
        if self.locked and self.answered_correctly:
            txt = f'<span style="color:{_C["green"]};font-size:0.88em;">✅ Correct!</span>'
        elif self.locked:
            txt = f'<span style="color:{_C["red"]};font-size:0.88em;">🔒 No attempts remaining</span>'
        else:
            txt = (f'<span style="color:{_C["blue"]};font-size:0.88em;">'
                   f'Attempts remaining: <b>{remaining}</b> of {self.max_attempts}</span>')
        return f'<div style="padding:4px 14px 2px 14px;">{txt}</div>'

    def _on_click(self, btn):
        if self.locked:
            return

        i          = btn._ans_index
        html_w     = btn._html_w
        ans        = self.data["answers"][i]
        is_correct = ans["correct"]
        feedback   = ans.get("feedback", "")

        self.attempts_used += 1
        remaining = self.max_attempts - self.attempts_used

        # Colour the clicked row
        row_bg = _C["green"] if is_correct else _C["red"]
        row_fg = _C["white"]
        html_w.value = (
            f'<div style="background:{row_bg};color:{row_fg};'
            f'border-radius:6px;padding:9px 16px;'
            f'font-size:0.97em;font-weight:600;cursor:default;'
            f'border:1px solid {row_bg};line-height:1.4;">'
            f'{ans["answer"]}</div>'
        )
        btn.style.button_color = row_bg
        btn.style.text_color   = row_fg
        if not is_correct:
            btn.disabled = True

        if is_correct:
            self.answered_correctly = True
            self.locked = True
            fb = (f'<div style="background:{_C["bg_done"]};border-left:5px solid {_C["green"]};'
                  f'padding:10px 14px;border-radius:6px;margin:6px 0;">'
                  f'✅ <b>Correct!</b>'
                  + (f' &nbsp;— {feedback}' if feedback else '') + '</div>')
        elif remaining > 0:
            fb = (f'<div style="background:#fff8f8;border-left:5px solid {_C["red"]};'
                  f'padding:10px 14px;border-radius:6px;margin:6px 0;">'
                  f'❌ <b>Not quite.</b>'
                  + (f' &nbsp;— {feedback}' if feedback else '')
                  + f' <i>({remaining} attempt{"s" if remaining!=1 else ""} left)</i></div>')
        else:
            self.locked = True
            correct_ans = next(a for a in self.data["answers"] if a["correct"])
            fb = (f'<div style="background:{_C["bg_lock"]};border-left:5px solid {_C["red"]};'
                  f'padding:10px 14px;border-radius:6px;margin:6px 0;">'
                  f'❌ <b>No attempts remaining.</b>'
                  + (f' &nbsp;— {feedback}' if feedback else '')
                  + f'<br><br>✅ <b>Correct answer:</b> {correct_ans["answer"]}'
                  + (f'<br><i>{correct_ans.get("feedback","")}</i>' if correct_ans.get("feedback") else '')
                  + '</div>')

        with self._feedback:
            self._feedback.clear_output(wait=True)
            display(HTML(fb))

        if self.locked:
            for html_w2, btn2 in self._answer_btns:
                btn2.disabled = True
                ans2 = self.data["answers"][btn2._ans_index]
                if ans2["correct"]:
                    # Highlight correct answer in pale green if not already green
                    if not self.answered_correctly or btn2._ans_index != i:
                        html_w2.value = (
                            f'<div style="background:{_C["pale_green"]};color:#1a3a2e;'
                            f'border-radius:6px;padding:9px 16px;'
                            f'font-size:0.97em;font-weight:600;cursor:default;'
                            f'border:1px solid {_C["green"]};line-height:1.4;">'
                            f'{ans2["answer"]}</div>'
                        )
                    btn2.style.button_color = _C["pale_green"]

        self._attempt_label.value = self._attempt_html(remaining)
        self._on_change()

    def get_state(self):
        return {"attempts_used": self.attempts_used,
                "locked": self.locked,
                "answered_correctly": self.answered_correctly}


# ══════════════════════════════════════════════════════════════════════════════
#  Public API
# ══════════════════════════════════════════════════════════════════════════════

def open_quiz(questions_source, name, user,
              quiz_id=None, max_attempts=None, n_questions=None):
    """
    The only function students ever call.

    Parameters
    ──────────
    questions_source : str — path to JSON file
    name             : str — student's name (entered in notebook)
    user             : str — JupyterHub username (from lab_init: user)
    quiz_id          : str — overrides module-level QUIZ_ID if given
    max_attempts     : int — overrides module-level MAX_ATTEMPTS if given
    n_questions      : int — if set, randomly select this many questions
                             from the full bank. Each student gets the same
                             subset every time (seeded by username + quiz_id)
                             so kernel restarts restore correctly.

    Returns a QuizResult with .score, .total, .locked
    Supports tuple unpacking: score, total = open_quiz(...)
    """
    qid  = quiz_id      or QUIZ_ID
    mxa  = max_attempts or MAX_ATTEMPTS

    # ── instructor bypass ──────────────────────────────────────────────────
    is_instructor = (user in INSTRUCTOR_USERS)
    if is_instructor:
        display(HTML(
            f'<div style="background:{_C["amber"]};color:{_C["white"]};'
            f'border-radius:8px;padding:10px 16px;margin:8px 0;font-weight:700;">'
            f'🧪 Instructor mode — lockout bypassed for user <code>{user}</code>'
            f'</div>'
        ))

    # ── lockout check (skip for instructors) ──────────────────────────────
    if not is_instructor:
        rec = _read_open_record(user, qid)
        if rec:
            display(HTML(
                f'<div style="background:{_C["bg_lock"]};'
                f'border-left:6px solid {_C["red"]};'
                f'border-radius:8px;padding:16px 20px;margin:12px 0;">'
                f'<b style="font-size:1.1em;">🔒 Quiz already opened</b><br><br>'
                f'This quiz was opened by <b>{rec["name"]}</b> '
                f'on {rec["timestamp"]}.<br>'
                f'Only one attempt is allowed. '
                f'Contact your instructor if this is an error.'
                f'</div>'
            ))

            class _Locked:
                score  = 0
                total  = 0
                locked = True
                def __iter__(self): yield 0; yield 0
            return _Locked()

        # Record the opening — from this point the quiz is locked
        _write_open_record(user, qid, name)

    # ── load questions ─────────────────────────────────────────────────────
    if isinstance(questions_source, str):
        with open(questions_source, encoding="utf-8") as f:
            all_questions = json.load(f)
    else:
        all_questions = list(questions_source)

    # ── random subset (seeded per user so restarts give same questions) ────
    if n_questions and n_questions < len(all_questions):
        import random as _random
        _rng = _random.Random(f"{user}:{qid}")   # deterministic per student
        questions = _rng.sample(all_questions, n_questions)
    else:
        questions = all_questions

    total     = len(questions)
    q_widgets = []

    # Restore per-question state (kernel-restart-proof)
    persisted = _load_state(user, qid) if not is_instructor else None

    # ── score + completion ─────────────────────────────────────────────────
    score_bar  = widgets.HTML()
    finish_out = widgets.Output()

    def _update():
        score    = sum(1 for qw in q_widgets if qw.answered_correctly)
        answered = sum(1 for qw in q_widgets if qw.locked)
        pct      = score / total * 100 if total else 0

        score_bar.value = (
            f'<div style="background:{_C["navy"]};color:{_C["white"]};'
            f'border-radius:8px;padding:10px 18px;margin:8px 0;font-weight:600;">'
            f'Score: {score} / {total} &nbsp;'
            f'<span style="opacity:0.82;">({pct:.0f}%)</span>'
            f'&nbsp;—&nbsp; {answered} of {total} completed'
            f'</div>'
        )

        # Save state
        if not is_instructor:
            try:
                _save_state(user, qid, {
                    "quiz_id": qid, "user": user, "timestamp": time.asctime(),
                    "score": score, "total": total,
                    "questions": [qw.get_state() for qw in q_widgets],
                })
            except Exception:
                pass

        # Completion banner
        if answered == total:
            grade_col = (_C["green"] if pct >= 80 else
                         _C["amber"] if pct >= 60 else _C["red"])
            grade_msg = ("Excellent! 🌟"       if pct >= 90 else
                         "Well done! ✅"        if pct >= 80 else
                         "Good effort — review what you missed." if pct >= 60 else
                         "Review the material and speak with your instructor.")
            with finish_out:
                finish_out.clear_output(wait=True)
                display(HTML(
                    f'<div style="background:{grade_col};color:{_C["white"]};'
                    f'border-radius:8px;padding:14px 20px;margin:8px 0;'
                    f'font-weight:700;font-size:1.1em;">'
                    f'🎉 Quiz complete! &nbsp; {score}/{total} ({pct:.0f}%) &nbsp;— {grade_msg}'
                    f'</div>'
                    f'<div style="padding:4px 0;color:{_C["navy"]};font-size:0.92em;">'
                    f'Your score (<b>{score}</b>) has been recorded. '
                    f'Click <b>Submit Quiz</b> in the next cell.'
                    f'</div>'
                ))

    # ── header ─────────────────────────────────────────────────────────────
    att_str = (f"{mxa} attempt per question" if mxa == 1
               else f"{mxa} attempts per question")
    header = widgets.HTML(
        f'<div style="background:{_C["cherry"]};color:{_C["white"]};'
        f'border-radius:10px 10px 0 0;padding:14px 20px;'
        f'font-size:1.2em;font-weight:800;">'
        f'📝 {qid} &nbsp;'
        f'<span style="font-size:0.78em;font-weight:400;opacity:0.9;">'
        f'{total} questions · {att_str} · feedback shown immediately'
        f'</span></div>'
    )

    # ── build questions ────────────────────────────────────────────────────
    for i, q in enumerate(questions):
        init = None
        if persisted and i < len(persisted.get("questions", [])):
            init = persisted["questions"][i]
        qw = _QuestionWidget(i, q, mxa, _update, init)
        q_widgets.append(qw)

    _update()   # initial render

    display(widgets.VBox(
        [header, score_bar] + [qw.widget for qw in q_widgets] + [finish_out],
        layout=widgets.Layout(width="100%", max_width="820px")
    ))

    # ── result object ──────────────────────────────────────────────────────
    class _Result:
        def __init__(self, qws, n):
            self._qws   = qws
            self._total = n
            self.locked = False
        @property
        def score(self):
            return sum(1 for qw in self._qws if qw.answered_correctly)
        @property
        def total(self):
            return self._total
        def __iter__(self):
            yield self.score
            yield self.total
        def __repr__(self):
            return f"QuizResult({self.score}/{self.total})"

    return _Result(q_widgets, total)
