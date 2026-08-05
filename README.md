# Elements of Data Science — Undergraduate (Fall 2026 labs)

Restructured from the high-school version (`lab00_high_school.ipynb`, `lab01_high_school.ipynb`)
and the existing undergraduate probability lab, for first-year science majors.

## Repo layout

`index.html` is the **universal landing page** — it carries no semester in its title and lives
one directory *above* the semester folder, so future semesters can reuse it just by adding a new
`Season YYYY/` folder and updating the button URLs.

```
data/                              (repo root)
├── index.html                     ← "Elements of Data Science" launch page (Temple colors, nbgitpuller links)
├── submission-instructions.html   ← .ipynb download + Canvas HTML export steps, linked from lab00 onward
└── Fall 2026/
    ├── README.md                  ← pointer to this file
    ├── shared-public/             ← universal, one directory above every lab
    │   ├── init.py                ← single shared setup, imported by every lab notebook
    │   ├── lab_submit.py          ← shared submission helper (Google Sheets via gspread)
    │   └── notebook_style.py      ← shared CSS styling, incl. .challenge-box
    ├── lab00/
    │   ├── lab00_undergrad.ipynb
    │   ├── questions00.json       ← Quick Check quiz, incl. a Temple founder / Night Owl question
    │   └── tests00/               ← placeholder, see Gaps below
    ├── lab01/
    │   ├── lab01_undergrad.ipynb
    │   ├── questions01B.json, questions01C.json, questions01D.json
    │   └── tests_01/              ← placeholder, see Gaps below
    └── lab05/
        ├── lab05_undergrad.ipynb
        ├── GroundHogData/         ← placeholder, see Gaps below
        └── tests/                  ← placeholder, see Gaps below
```

Every lab notebook's first code cell reads:

```python
import sys, os
sys.path.insert(0, os.path.abspath(os.path.join(os.getcwd(), "..", "shared-public")))
from init import *
```

`init.py` installs `gspread` if missing, sets up the datascience/numpy/matplotlib stack,
applies notebook styling, and exposes `check()`, `user`, `test_open()`, `submit_lab()`.

## What changed from the high-school version

- **Directories.** Each lab now lives in its own `labNN/` folder instead of mixing lab files at
  the repo root.
- **Universal shared files.** `init.py`, `lab_submit.py`, and `notebook_style.py` are no longer
  duplicated/hard-coded per lab (the old `lab01_init.py` had `LAB_ID`/`ver` baked in). They now
  live once in `shared-public/`, and each notebook passes its own `lab_id="Lab01"` to
  `submit_lab()`.
- **`shared-readwrite/` → `shared-public/`.** Confirmed against the live hub path
  `/home/jovyan/shared-public` (already contains `submissions.json` and `submissions.json.lock`
  from `_atomic_append_json`, matching this design).
- **Challenges section.** The hardest, multi-step questions were pulled into a clearly marked
  `## 🚀 Challenges` section using a new `.challenge-box` CSS style:
  - Lab 01: average distance, seconds-since-2000, and paper-folding problems.
  - Lab 05: the individual Essex Ed / Punxsutawney Phil hypothesis tests (kept graded, same
    `check()` calls as before).
- **Tone/rigor.** Lab 00 and Lab 01 examples were rewritten from high-school framing (penguins,
  pizza slices) to first-year-science framing (density, reaction rates, reagent volumes,
  chromosome counts). Lab 05 was already at appropriate rigor and needed only structural changes.
  Year-dependent problems in Lab 01 (the "calculate the year" riddle, seconds-since-2000) were
  updated for 2026.
- **Google-Sheets submission.** `lab_submit.py` already supported Google Sheets via `gspread`;
  `init.py` now runs `pip install gspread` automatically so every lab has it without a manual
  step.
- **Branding.** `index.html` uses Temple's official palette — cherry `#A41E35`, black `#222222`,
  silver `#A7A8AA`, white — instead of the high-school page's purple/rainbow theme, and is titled
  simply "Elements of Data Science" with no semester in the header.
- **Lab 00 now teaches the submission workflow, not just Python.** Two of its three questions
  (name, reagent-volume calculation) are now `check()`-graded like every other lab, followed by
  a `## 📝 Quick Check` `jupyterquiz` (two Python-concept questions, plus two Temple-history
  questions on Russell Conwell and the "night owl" mascot origin — facts verified against
  Temple's official [Temple Traditions](https://www.temple.edu/about/history/temple-traditions)
  page). The lab ends with the same run-all-tests → `submit_lab(lab_id="Lab00")` pattern as
  every other lab, so students hit the full submission routine on day one.
- **Submission instructions page.** `submission-instructions.html` (repo root) walks through
  downloading the `.ipynb` and exporting an HTML copy for Canvas, with `#ipynb` / `#html` anchor
  links. This was written fresh since no existing instructions page was provided — swap in your
  official one if you already have one, or edit this one to match.
- **Submission order, all three labs.** Every lab's final section now spells out three ordered
  steps: (1) run the test cell and check your score, (2) download the `.ipynb` and export/upload
  the HTML copy to Canvas, (3) only then run the final cell and click **Submit Lab** — so the
  gradebook submission is a confirmation that Canvas is already done, not a substitute for it.

## Before this goes live — gaps to fill in

The uploaded material didn't include a few files this restructuring references. Nothing will run
end-to-end until these are added:

1. **gofer test scripts** — `lab00/tests00/*.py` (`q1.py`, `q3.py`, `q2_open_ended.py` for the
   Question 2 reflection), `lab01/tests_01/*.py`, and
   `lab05/tests/*.py` (e.g. `q0.py`, `q1a.py`, … `q14_open_ended.py`). Only `check(...)`-style
   *calls* existed in/were added to the source notebooks; the test files themselves weren't part
   of the upload. Copy your existing ones in for Lab 01/05, and write two new ones for Lab 00,
   updating any that reference the changed leap-year math in Lab 01's seconds-since-2000
   challenge (now 7 leap years / 19 regular years, through 2026).
2. **Lab 05 data files** — `GroundHogData/summarizedGroundhogData_20210326.csv` and
   `darwin_origin_species.txt` (the latter goes directly in `lab05/`). Referenced by the notebook
   but not uploaded.
3. **Image assets** — `Temple_flag_morn.png` (needed in both the repo root, for `index.html`,
   and in `lab01/`) and the `intro_jupyter_images/` folder (`toolbar.png`, `typecell.png`,
   `checkpass.png`, `checkfail.png`, `error.jpg`) used in Lab 01. Copy these from the existing
   STEMDS repo.
4. **Google Sheet.** In `shared-public/lab_submit.py`, set `SHEET_ID` to this semester's sheet
   and place a service-account credentials JSON at `shared-public/service_account.json` (share
   the sheet with that service account's email). Keep that credentials file out of the public
   repo — see note below.

## Publishing to GitHub / GitHub Pages

This tree is meant to sit at `laserchemist/data`, with `index.html` at the repo root and the
labs under `Fall 2026/`.

1. Push `index.html` and the `Fall 2026/` folder into `laserchemist/data` on `main`.
2. In the repo's Settings → Pages, publish from `main` (root). `index.html` will then be served
   at the repo's GitHub Pages URL with no semester in the path.
3. Each launch button uses this pattern (already filled in for lab00/01/05):

   ```
   https://temple.2i2c.cloud/hub/user-redirect/git-pull?repo=https%3A%2F%2Fgithub.com%2Flaserchemist%2Fdata&urlpath=lab%2Ftree%2Fdata%2FFall%202026%2FlabNN%2FlabNN_undergrad.ipynb&branch=main
   ```

   nbgitpuller clones the whole `data` repo into a folder named `data` on the hub, then opens the
   file at that path. Double-check `temple.2i2c.cloud` is the correct hub for this course — that
   domain was carried over from the high-school TOC page.
4. **Next semester:** duplicate `Fall 2026/` into e.g. `Spring 2027/`, update the six `Fall%202026`
   occurrences in `index.html` to the new folder name, and re-publish. The page itself never
   needs a title change.
5. **Security note:** since `laserchemist/data` is a public repo, do not commit
   `shared-public/service_account.json` or any real `SHEET_ID`/API keys to it. Keep those on the
   hub's shared filesystem only (`/home/jovyan/shared-public/`), not in git.

## Scope note

Only Lab 00, Lab 01, and Lab 05 were built — no source material was provided for Lab 02–04
(data types, Tables, functions/visualization), so those weren't stubbed out. `index.html` only
links to the three labs that exist.
