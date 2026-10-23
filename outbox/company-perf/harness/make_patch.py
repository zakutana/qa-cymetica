"""The change as one patch against the live files: every static file (JS, CSS) that differs, as `static/company/<name>`,
applicable with `git apply` or `patch -p1` from the folder that holds `static/`. The three pages are served from your
templates (their nonces differ per request), so their diff goes in a file of its own as a reference for the template.
  python make_patch.py <before dir> <after dir> <out dir>"""
import difflib, sys
from pathlib import Path

A, B, OUT = Path(sys.argv[1]), Path(sys.argv[2]), Path(sys.argv[3])
OUT.mkdir(parents=True, exist_ok=True)
static, pages = [], []
for f in sorted(B.iterdir()):
    if f.suffix not in (".js", ".css", ".html"):
        continue
    old = A / f.name
    a = old.read_text(encoding="utf-8").splitlines(keepends=True) if old.exists() else []
    b = f.read_text(encoding="utf-8").splitlines(keepends=True)
    if a == b:
        continue
    pa = f"a/static/company/{f.name}" if old.exists() else "/dev/null"
    if f.suffix == ".html":
        pa, pb = (f"a/company/app/{f.stem}.html" if old.exists() else "/dev/null"), f"b/company/app/{f.stem}.html"
        pages.append("".join(difflib.unified_diff(a, b, pa, pb, n=2)))
    else:
        pb = f"b/static/company/{f.name}"
        static.append("".join(difflib.unified_diff(a, b, pa, pb, n=3)))
for name, parts in (("company-perf.patch", static), ("pages.diff", pages)):
    text = "".join(p if p.endswith("\n") else p + "\n" for p in parts)
    (OUT / name).write_text(text, encoding="utf-8", newline="\n")
    print(name, len(parts), "files", len(text), "bytes")
