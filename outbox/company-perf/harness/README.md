# How the numbers were made

Python 3 with Playwright and Pillow, Google Chrome (Playwright's own Chromium has no DXC libraries on Windows, so its
WebGPU cannot make a device and three.js silently draws through WebGL2), Node for `guess_test.js`. Next to this folder:
`rec/` (the recording), `base/` (the live files) and `opt/` (the live files with `company-perf.patch` applied, plus `new/`).

1. `python rec_live.py rec`: the live pages loaded once each, signed out (`/company/app`, `#universe`, `?visit=14`,
   `/builder`); every GET answered by cymetica.com saved under `rec/http`, any other method refused. Company 14 is ours.
2. `python rec_office.py rec/auth`: one authenticated read of our own office, for the signed-in place.
3. `base/`: the company files as served (`/static/company/<name>?v=6adb7183`) and the three pages (`app.html`,
   `start.html`, `builder.html`, `recget.py` takes one out of the recording); `opt/`: a copy with the patch applied.
4. `python batch.py results`: every place (`start`, `universe`, `visit`, `ours`) before and after, at each level, on the weak
   machine (the integrated Radeon via `--force_low_power_gpu`, the page's processor slowed 3x) and the strong one, one
   after another; `python summarize.py results` makes the tables. `perf.py` is one run of one place.
5. `python pix.py rec base opt out --q high`: the pixel check (clock held, today's page twice, the changed one once).
6. `python functest.py rec opt out`: the paths no timing walks (Headquarters opened after the Universe, Add a department,
   Settings > Graphics), at each level.
7. `node guess_test.js ../../../<opt>/quality.js`: the first guess against 21 chip names.

8. `python govtest.py rec opt`: the frames' verdict run once (the weak machine with an add-in card's name for its chip:
   high from the guess, turned, then the next visit).
9. `python perf.py ... --scenario visit --init nodebuilds.js`: three.js's shader builds counted (how many, how long, how
   many different programs), printed as a console warning in the result.

Also: `census.py` (what the office draws, by kind), `profsum.py` (a CPU profile summed by function), `poster.py` (the
entry page's pictures), `make_patch.py` (the patch and `pages.diff`), `diffimg.py` (where two pictures differ), `knobs.py`
(one setting of low at a time, at high), `diag.py` (one part of the scene taken away at a time).
Every request is answered from the recording or refused: after step 1 nothing reaches cymetica.com.
