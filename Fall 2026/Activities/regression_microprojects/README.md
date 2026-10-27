# Regression Microprojects (after Lab 8)

Five short, lightly scaffolded notebooks where students apply their Lab 8 regression toolbox
(`standard_units`, `correlation`, `slope`, `intercept`) to a new real data set and submit one figure
to a shared class gallery.

## Install on the hub
1. Copy `shared-public/microproject_tools.py` to `/home/jovyan/shared-public/` (next to `init.py`).
2. Distribute the five `mp*.ipynb` notebooks **with their CSV files in the same folder** (like the labs).
3. Keep `instructor_microprojects.ipynb`, `class_list.csv`, and `keys/` out of the student distribution.

## Instructor demo (run before students start)
`instructor_demo_auto_mpg.ipynb` (with `auto_mpg.csv` and `anscombe.csv`) is a fully worked example on car
weight vs fuel economy that walks through every part of a microproject and ten "tricks": Anscombe's quartet,
guessing r, unit choice, swapped x/y, regression to the mean, error plots and transforming mpg to gallons per
100 miles, splitting by group, influential points, `np.polyfit`, and bad-vs-good final figures. It submits its
figure to the gallery under the id `DEMO`.

## In class
1. Instructor: put the roster in `class_list.csv` (`first_name`, optional `last_name`), run
   `instructor_microprojects.ipynb` Parts 1–2 → writes `shared-public/microprojects/assignments.csv`.
2. Students: open their notebook, set `name`, run `my_project(name)` to confirm, work Parts 1–7,
   then `submit_plot(...)` → `shared-public/microprojects/submissions/MP#_FirstL.png` + `.json`.
3. Instructor: rerun Part 3 for the live status table and gallery; Part 4 for discussion.

| Notebook | Data (file) | Source |
|---|---|---|
| mp1_co2_mauna_loa | co2_mauna_loa.csv | NOAA GML Mauna Loa annual means 1959–2025 |
| mp2_galton_heights | galton_heights.csv | Galton (1886), via data-8/textbook |
| mp3_births | births.csv | Child Health and Development Studies, via data-8/textbook |
| mp4_penguins | penguins.csv | Gorman et al. 2014 / palmerpenguins (CC0) |
| mp5_periodic_trends | elements.csv | Periodic-Table-JSON (CC BY-SA) |

Submissions are keyed by first name + last initial; resubmitting replaces the old figure.
If a student cannot write to `shared-public`, `submit_plot` saves the PNG in their own folder and says so.
To test without the hub, set the environment variable `MICRO_ROOT` to any writable folder.
