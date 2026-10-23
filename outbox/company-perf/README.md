# Build a Company: fast on a weak computer (ready to file)

Started 2026-10-23 at the owner's word, after /company/app loaded about 70 % longer on his Ryzen 5 5500U laptop (8 GB,
Radeon graphics with 496 MB) than on his desktop and stuttered in the Universe and the office. A package for Build it
Better: the change itself, ready to apply, and what it buys, measured. On the branch `company-perf`.

- `SPEC.md`: what was found, what changes and where, the numbers before and after, how to apply it.
- `company-perf.patch`: the change against their live files (`/static/company/*?v=6adb7183`, read 2026-10-23), including
  the new `quality.js`; applied to those files it gives the measured files byte for byte. `pages.diff`: the three pages'
  edits as rendered (on their side they are templates).
- `new/`: the entry page's three pictures (`start-*.webp`), drawn by the live page's own scenes.
- `build-it-better/request.txt`: the request text the owner files. Its links open once this branch is pushed.
- `harness/`: how it was measured (an offline replay of the live page in Chrome with WebGPU, a strong and a weak machine,
  the pixel check, the chip-name test). Recordings and results stay out of git; `harness/README.md` says how to make them.
