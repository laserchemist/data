"""
pool_quiz.py: recorded quiz drawn from a question pool.

Each student gets a fixed, personal set of questions:
  * Attempt 1: n questions (default 12) from the pool, at least `per_topic` from every topic
  * Attempt 2: n NEW questions, chosen only from questions not used in Attempt 1

Selection is seeded by the student's login (`user`) and the quiz id, so re-running a
cell shows the same questions (no re-rolling for easier ones), while different
students get different sets. Each attempt is recorded by stemds_quiz.open_quiz
under its own quiz id: f"{quiz_id}_A1" and f"{quiz_id}_A2".
"""
import datetime
import hashlib
import json
import os

import numpy as np


def _rng(user, quiz_id):
    key = f"{str(user).strip().lower()}|{quiz_id}".encode()
    return np.random.default_rng(int(hashlib.sha256(key).hexdigest()[:12], 16))


def pick_questions(pool, user, quiz_id, attempt, n=12, per_topic=2):
    """The questions for one attempt. Deterministic for a given (user, quiz_id, attempt)."""
    rng = _rng(user, quiz_id)
    topics = sorted({qn["topic"] for qn in pool})
    # one personal shuffle of each topic, fixed for this student
    order = {t: [i for i in rng.permutation(len(pool)) if pool[i]["topic"] == t] for t in topics}
    used = set()
    chosen = []
    for _ in range(attempt):
        chosen = []
        for t in topics:                                   # guaranteed coverage of every topic
            fresh = [i for i in order[t] if i not in used]
            chosen += fresh[:per_topic]
        leftovers = [i for i in rng.permutation(len(pool)) if i not in used and i not in chosen]
        chosen += leftovers[:n - len(chosen)]              # fill the rest at random
        if len(chosen) < n:
            raise ValueError("Pool is too small for this many attempts.")
        used.update(chosen)
    chosen = [chosen[i] for i in rng.permutation(len(chosen))]   # mix topics together
    return [{k: v for k, v in pool[i].items() if k != "topic"} for i in chosen]


def in_window(opens, closes, now=None):
    now = now or datetime.datetime.now()
    return datetime.datetime.fromisoformat(opens) <= now <= datetime.datetime.fromisoformat(closes)


def open_pool_quiz(pool_file, name, user, quiz_id, attempt, n=12, per_topic=2,
                   opens=None, closes=None):
    """Write this student's questions for `attempt` to a file and open the recorded quiz."""
    if opens and closes and not in_window(opens, closes):
        print(f"⏰ This quiz is open from {opens} to {closes}. It is not open right now.")
        return None
    if name is ... or not str(name).strip():
        print("✋ Enter your name in the cell near the top of the notebook first.")
        return None
    with open(pool_file) as f:
        pool = json.load(f)
    questions = pick_questions(pool, user, quiz_id, attempt, n=n, per_topic=per_topic)
    path = os.path.join(os.path.dirname(os.path.abspath(pool_file)), f".{quiz_id}_A{attempt}.json")
    with open(path, "w") as f:
        json.dump(questions, f, indent=1)
    from stemds_quiz import open_quiz
    return open_quiz(path, name, user, quiz_id=f"{quiz_id}_A{attempt}", max_attempts=1)
