"""scripts/company.py refuses a bad body and reads a sparse answer without a traceback (deep pass 2026-10-15,
R02 and R07). Nothing here touches the network: the transport is a MockTransport."""

import json

import httpx

from qa.marks import SafetyTier, qa
from scripts import company


@qa(component="meta.pipeline", tier=SafetyTier.SAFE, surface="meta")
def test_a_body_without_departments_is_refused_not_a_traceback(tmp_path, capsys):
    body = tmp_path / "body.json"
    body.write_text(json.dumps({"name": "Acme Labs", "mission": "a mission of ten+"}), encoding="utf-8")
    assert company.main(["create", "--body-file", str(body)]) == 2
    assert "refused, nothing sent" in capsys.readouterr().out


@qa(component="meta.pipeline", tier=SafetyTier.SAFE, surface="meta")
def test_read_prints_a_message_without_a_role_and_a_task_without_a_status(monkeypatch, capsys):
    def answer(request):
        path = request.url.path
        if path.endswith("/messages"):
            return httpx.Response(200, json={"messages": [{"created_at": None, "role": None, "text": "hi"}]})
        if path.endswith("/tasks"):
            return httpx.Response(200, json={"tasks": [{"id": 1, "status": None, "title": None, "brief": None}]})
        return httpx.Response(200, json={"budget": None, "departments": [], "approvals": []})

    monkeypatch.setattr(company, "INNER", httpx.MockTransport(answer))
    assert company.main(["read", "--company", "13"]) == 0
    out = capsys.readouterr().out
    assert "hi" in out and "task 1" in out
