"""A department added later appears everywhere without anybody wiring it in.

Plan v2, V9. The architect's review of 2026-09-23 counted 8-10 touchpoints to
add a department (a new product the operator wants run like the laboratory).
The shape is one: a skill, `scripts/<d>.py`, diaries `state/<d>*.jsonl` and a
report `state/<d>/report.json`; the patrol, the snapshot into audits/ and the
/lab page find it by glob. This file builds a fixture department and changes
nothing else -- if it does not show up, the shape is not real.
"""

from __future__ import annotations

import importlib
import importlib.util
import json
from pathlib import Path

from qa.marks import SafetyTier, qa

REPO = Path(__file__).resolve().parent.parent.parent


def _script(name: str):
    spec = importlib.util.spec_from_file_location(f"dept_{name}", REPO / "scripts" / f"{name}.py")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def _fixture(root: Path) -> None:
    (root / ".claude" / "skills" / "testdept").mkdir(parents=True)
    (root / ".claude" / "skills" / "testdept" / "SKILL.md").write_text(
        "---\nname: testdept\ndescription: a department added later\n---\n\nbody\n",
        encoding="utf-8")
    (root / "scripts").mkdir()
    (root / "scripts" / "testdept.py").write_text('"""tick, brief, report."""\n',
                                                  encoding="utf-8")
    state = root / "state"
    (state / "testdept").mkdir(parents=True)
    (state / "testdept" / "report.json").write_text(json.dumps({
        "title": "Testovací oddělení", "lines": ["3 pokusy, čistě +1,2 %"]}),
        encoding="utf-8")
    (state / "testdept.jsonl").write_text(
        json.dumps({"type": "tick", "at": "2026-09-24T01:00:00+00:00"}) + "\n",
        encoding="utf-8")


@qa(component="meta.pipeline", tier=SafetyTier.SAFE, surface="meta")
def test_a_department_is_found_by_the_patrol_the_archive_and_the_page(tmp_path,
                                                                     monkeypatch):
    _fixture(tmp_path)
    monkeypatch.setenv("QA_STATE_DIR", str(tmp_path / "state"))
    import qa.state

    importlib.reload(qa.state)
    from qa import departments

    importlib.reload(departments)

    # The patrol: the skill and the script as parts, and the diary as its record.
    procs = _script("processes")
    names = {p["name"] for p in procs.parts(tmp_path)}
    assert {"testdept", "testdept.py"} <= names, names
    assert procs.records_by_part(tmp_path).get("testdept.py") == [
        "2026-09-24T01:00:00+00:00"]

    # The archive: its diary is snapshotted into audits/ with the laboratory's.
    keep = _script("keep")
    assert "testdept.jsonl" in keep.snapshot()

    # The page: its report reaches /lab's data, and the page draws the list.
    found = departments.departments()
    assert [d["id"] for d in found] == ["testdept"], found
    assert found[0]["title"] == "Testovací oddělení" and found[0]["lines"]
    page = _script("lab_page")
    assert page.departments_view() == found
    assert 'id="departments"' in page.TEMPLATE and "V.departments" in page.TEMPLATE
