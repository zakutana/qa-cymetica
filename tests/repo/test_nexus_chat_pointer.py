"""A pointer to an answer is not an answer: `ask_chat` must wait for the job it names (T-0048).

2026-10-12, read live through our client. `nexus.py ask_chat` (the NEXUS bar, MCP `ask_nexus`) writes whatever
text comes back as `type: answer`. Four of the four chat rows in state/nexus_shallow.jsonl are not answers but
a pointer to one:

    NEX-0119  10-03 06:43  "NEXUS is investigating this now ... answers/<id>?token=.. (GET it; usually 1-5 minutes)"
    NEX-0120  10-03 07:29  "Your question is in the queue and will be answered at .../answers/<id>?token=.."
    NEX-0121  10-03 19:45  "NEXUS is investigating this now ..."
    NEX-0140  10-12 20:42  "NEXUS is investigating this now ..."   (confidence 0.5, 378 chars)

GET of each pointer, SAFE, today: 0119, 0120, 0121 answer 200 `status: answered`, 4842, 5359 and 4092 chars,
finished 2 to 17 minutes after we asked, and nothing ever fetched them. 0140 answers 200 `status: failed`,
`error: "The investigation exceeded its time budget - retry with a narrower question."`. The lab holds that row
as guidance (lab.outstanding calls it finished, board/brief count an answer), so it never polls, never retries.

The fix is the session's (scripts/ and qa/ are closed to workers). What it must do:

  * `ask_chat`: a reply whose `sources` hold a `/api/v1/support/ai-agent/answers/` URL (or whose text does)
    writes `{"id", "type": "pending", "at", "lane": "chat", "url": <that URL>, "job_id": <the uuid>}` and NO
    answer. The question row stays without a terminal row, so `lab.outstanding` already lists it.
  * `poll_once(question_id)` (what `lab.py cycle` calls) looks in the shallow diary too: a pending chat row is
    one GET of its url. `answered` writes `type: answer` with their `answer` as text (lane chat, same id);
    `failed` writes `type: gave_up` with status `failed: <their error>`; anything else, and any read that does
    not answer 200, writes nothing (rule 8: a failed read is not an empty read).

Strict xfail: each fails on an ASSERTION today and turns red the day the fix lands, and the markers must go
then. The control passes now and must keep passing: an answer that is an answer is still written as one.
"""

from __future__ import annotations

import importlib
import importlib.util
import json
from pathlib import Path

import pytest

from qa import lab
from qa.marks import SafetyTier, qa

REPO = Path(__file__).resolve().parent.parent.parent
JOB = "2c7c1992-a280-4f17-86bd-7b1db744b094"
PATH = f"/api/v1/support/ai-agent/answers/{JOB}?token=tok"
URL = "https://cymetica.com" + PATH

RUNNING = ("NEXUS is investigating this now: it checks the live platform, its data and how the site actually "
           f"behaves before it answers. The answer will be at {URL} (GET it; usually 1-5 minutes). "
           "No need to ask again.")
QUEUED = (f"Your question is in the queue and will be answered at {URL} (GET it; it runs automatically, no "
          "need to ask again). Paying subscribers are served first.")


def _nexus(tmp_path, monkeypatch):
    monkeypatch.setenv("QA_STATE_DIR", str(tmp_path))
    import qa.state

    importlib.reload(qa.state)
    spec = importlib.util.spec_from_file_location("nexus_chat_pointer", REPO / "scripts" / "nexus.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _says(monkeypatch, nexus, text, sources=None):
    class Client:
        http = type("H", (), {"close": lambda self: None})()

        def call(self, tool, arguments=None):
            return {"success": True, "tool": "ask_nexus", "result": {
                "answer": text, "confidence": 0.5, "sources": sources if sources is not None else [URL],
                "session_id": "s-1"}}

    monkeypatch.setattr(nexus, "_client", lambda: Client())


class _Response:
    def __init__(self, status, body):
        self.status_code, self._body = status, body

    def json(self):
        return self._body


def _theirs(monkeypatch, nexus, status, body):
    """Their answer URL, read through `_rest_client().get`. The GET is recorded."""
    gets = []

    class Rest:
        def get(self, path, **kwargs):
            gets.append(path)
            return _Response(status, body)

        def close(self):
            pass

    monkeypatch.setattr(nexus, "_rest_client", lambda: Rest())
    return gets


def _pending(nexus):
    """The diary as the fix must leave it after ask_chat met a pointer: a question and a pending row."""
    nexus._append_shallow({"id": "NEX-0001", "type": "question", "at": nexus._now(), "question": "q?",
                           "tool": "ask_nexus", "lane": "chat"})
    nexus._append_shallow({"id": "NEX-0001", "type": "pending", "at": nexus._now(), "lane": "chat",
                           "url": URL, "job_id": JOB})
    return "NEX-0001"


@pytest.mark.xfail(strict=True, reason="ask_chat records a pointer to an answer as the answer (T-0048, "
                   "NEX-0119/0120/0121/0140)")
@pytest.mark.parametrize("pointer", [RUNNING, QUEUED], ids=["investigating", "queued"])
@qa(component="meta.pipeline", tier=SafetyTier.SAFE, surface="meta")
def test_a_pointer_is_held_as_pending_not_written_as_an_answer(tmp_path, monkeypatch, pointer):
    nexus = _nexus(tmp_path, monkeypatch)
    _says(monkeypatch, nexus, pointer)
    said = nexus.ask_chat("what would you change?")
    rows = nexus.load_shallow()
    assert [r["type"] for r in rows] == ["question", "pending"], [r["type"] for r in rows]
    assert rows[1]["id"] == said["id"] and rows[1]["lane"] == "chat"
    assert rows[1]["url"] == URL and rows[1]["job_id"] == JOB
    assert lab.outstanding(nexus.load_all()) == [said["id"]], "the lab must still be waiting for it"


@pytest.mark.xfail(strict=True, reason="nexus.poll_once reads the deep diary alone, so a chat question that "
                   "waits at its answer URL is 'no question' to it (T-0048)")
@pytest.mark.parametrize("status, body, ends", [
    (200, {"job_id": JOB, "status": "answered", "answer": "Set min_ai_confidence 0.5.",
           "finished_at": "2026-10-12T20:50:00+00:00"}, "answer"),
    (200, {"job_id": JOB, "status": "failed",
           "error": "The investigation exceeded its time budget - retry with a narrower question.",
           "retry": "Ask again on the same door; NEXUS starts a fresh investigation."}, "gave_up"),
    (200, {"job_id": JOB, "status": "running"}, None),
    (502, None, None),
], ids=["answered", "failed", "still-running", "unread"])
@qa(component="meta.pipeline", tier=SafetyTier.SAFE, surface="meta")
def test_the_tick_picks_a_pending_chat_answer_up_by_its_url(tmp_path, monkeypatch, status, body, ends):
    nexus = _nexus(tmp_path, monkeypatch)
    question = _pending(nexus)
    gets = _theirs(monkeypatch, nexus, status, body)
    outcome = None
    try:
        nexus.poll_once(question)
    except SystemExit as exc:  # today: "no question NEX-0001", it only reads the deep diary
        outcome = f"refused: {exc}"
    assert outcome is None, outcome
    assert [g for g in gets if g.endswith(PATH)] == gets and len(gets) == 1, gets
    rows = [r for r in nexus.load_shallow() if r["id"] == question]
    last = rows[-1]
    if ends is None:  # theirs still working, or our read failed: nothing terminal is written
        assert [r["type"] for r in rows] == ["question", "pending"]
        assert lab.outstanding(nexus.load_all()) == [question]
        return
    assert last["type"] == ends and last["lane"] == "chat"
    assert lab.outstanding(nexus.load_all()) == []
    if ends == "answer":
        assert last["text"] == body["answer"] and "investigating" not in last["text"]
    else:
        assert last["status"].startswith("failed") and "time budget" in last["status"], last


@qa(component="meta.pipeline", tier=SafetyTier.SAFE, surface="meta")
def test_an_answer_that_is_an_answer_is_still_written_as_one(tmp_path, monkeypatch):
    """The control: the fix must not turn every chat reply into a pending job."""
    nexus = _nexus(tmp_path, monkeypatch)
    _says(monkeypatch, nexus, "Set min_ai_confidence 0.5 and max_position_pct 10.", sources=["faq-1"])
    said = nexus.ask_chat("what would you change?")
    rows = nexus.load_shallow()
    assert [r["type"] for r in rows] == ["question", "answer"], json.dumps(rows)[:300]
    assert rows[1]["id"] == said["id"] and rows[1]["text"].startswith("Set min_ai_confidence")
