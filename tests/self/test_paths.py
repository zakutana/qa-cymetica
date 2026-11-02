"""The journal as a plain log and filed.json under a lock: what a vendor's text or a killed process must not break."""

from __future__ import annotations

from qa import paths
from qa.paths import append_event, journal_path, load_filed, read_events, save_filed, updating_filed


def test_a_line_separator_inside_a_message_stays_one_event():
    append_event({"type": "message", "msg_id": "a", "text": "one two\x85three four"})
    events = read_events()
    assert [e["msg_id"] for e in events] == ["a"]
    assert events[0]["text"] == "one two\x85three four"


def test_an_old_line_written_raw_with_a_separator_still_reads_as_one():
    target = journal_path()
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text('{"msg_id": "old", "text": "a b"}\n', encoding="utf-8", newline="\n")
    assert [e["msg_id"] for e in read_events()] == ["old"]


def test_a_lone_surrogate_from_their_json_does_not_crash_the_journal():
    append_event({"type": "message", "msg_id": "a", "text": "half an emoji \ud83d"})
    assert read_events()[0]["text"] == "half an emoji \ud83d"


def test_a_cut_last_line_does_not_eat_the_next_event():
    target = journal_path()
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text('{"msg_id": "whole"}\n{"msg_id": "cu', encoding="utf-8", newline="\n")
    append_event({"msg_id": "next"})
    assert [e["msg_id"] for e in read_events()] == ["whole", "next"]


def test_an_id_is_taken_under_the_lock():
    append_event({"msg_id": "MSG-0001"})
    event = {"type": "telegram_sent"}
    append_event(event, make_id=lambda events: f"MSG-{len(events) + 1:04d}")
    assert event["msg_id"] == "MSG-0002"
    assert [e["msg_id"] for e in read_events()] == ["MSG-0001", "MSG-0002"]


def test_updating_filed_saves_what_the_caller_changed_on_a_fresh_read():
    save_filed({"rows": [{"key": "a"}]})
    with updating_filed() as filed:
        filed["rows"].append({"key": "b"})
    assert [r["key"] for r in load_filed()["rows"]] == ["a", "b"]


def test_a_replace_refused_by_windows_is_tried_again(tmp_path, monkeypatch):
    target = tmp_path / "x.json"
    real, tries = paths.Path.replace, []

    def refused_twice(self, other):
        tries.append(1)
        if len(tries) < 3:
            raise PermissionError("held open by another process")
        return real(self, other)

    monkeypatch.setattr(paths.Path, "replace", refused_twice)
    monkeypatch.setattr(paths.time, "sleep", lambda _: None)
    paths.atomic_write(target, "whole")
    assert target.read_text(encoding="utf-8") == "whole" and len(tries) == 3
    assert list(tmp_path.glob("*.tmp")) == []
