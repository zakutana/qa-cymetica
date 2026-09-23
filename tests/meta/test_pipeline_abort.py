"""PIN: the safety guard's enforcement sections are byte-identical to ca0bc45,
and a failing meta test really does abort the session before anything else.

This is phase 0 of the hardening plan and it must stay green through every
later phase. It exists because the guard is the only part of this repo that
worked as designed, and the plan touches files next to it (conftest.py loses
its Inconclusive wrapper in phase 1). If any later edit drifts into the guard
sections, this test turns red and -- via the very mechanism it pins -- stops
the session.

The hashes below were computed at commit ca0bc45 over the sections named here,
and re-derived since -- each time with its reason beside the hash:
  tests/conftest.py            lines 44-135  (markers, options, the guard
                                              self-check, collection-time
                                              enforcement, meta-first ordering,
                                              the abort hook, sessionstart)
  tests/conftest.py            lines 141-230 (session resources and fixtures)
  tests/meta/test_guard_is_real.py  whole file
Lines 233-236 of conftest.py (what is left of the Inconclusive hookwrapper,
removed in phase 1) sit deliberately outside the pinned ranges.
"""

from __future__ import annotations

import hashlib
import os
import subprocess
import sys
import textwrap
from pathlib import Path

import pytest

from qa.marks import SafetyTier, qa

REPO = Path(__file__).resolve().parents[2]
CONFTEST = REPO / "tests" / "conftest.py"
GUARD_TESTS = REPO / "tests" / "meta" / "test_guard_is_real.py"

PINNED = {
    # Re-derived 2026-09-07, and the ranges moved with it (42-117 -> 44-135,
    # 123-212 -> 141-230), for one edit that adds enforcement:
    # pytest_configure now calls assert_client_guard_blocks() straight after
    # install_client_guard(). The ordering pinned here aborts a session whose
    # guard tests FAIL; a selector that never collects them aborts nothing,
    # and live requests have gone out exactly that way. The self-check closes
    # the case the ordering cannot see. Section two's hash is unchanged, which
    # is the evidence that only section one moved.
    "conftest.py:44-135": "e29df32b2ce0afd02c2fd309f0d45647192380e696fe345dcb41aab4ab2c1184",
    "conftest.py:141-230": "d81006935096100794735750341c49d76393dd82d2f224dd55a9a0ce874e7454",
    # Re-derived 2026-09-06, deliberately, for two edits that go the way this
    # pin exists to protect:
    #
    #   * the money-loop endpoints gained `probe_only: true` in
    #     components.yaml, which made test_mutate_against_unlisted_host_is_
    #     blocked raise on the floor instead of the host allowlist -- so it
    #     was moved onto the bounty filing channel, which is deliberately not
    #     probe_only and therefore actually reaches the allowlist. The old
    #     subject tested the floor twice and the allowlist never.
    #   * test_the_money_loop_is_behind_the_probe_only_floor was added, so
    #     the floor cannot quietly come off again.
    #
    # Both add enforcement. A future re-derivation that removes any is the
    # thing this pin is for: check what changed before recomputing.
    #
    # Re-derived again the same day, for the reason this pin would most want
    # to hear about. Every negative control in that file asked the guard to
    # refuse something, and its only protection against actually doing it was
    # the code under test. Mutating the probe_only floor off -- to check this
    # suite could feel it -- sent a real POST to /api/v1/funding/withdraw with
    # {"amount": "1"}; anonymous, refused 401, nothing moved, and it left the
    # machine. The clients there now carry a transport that cannot send. The
    # mutation is still caught, the message now reads THE GUARD LET IT
    # THROUGH, and no evidence file is written because nothing is sent.
    # Re-derived 2026-09-07, deep pass, and the pin earned its keep: it fired
    # on the change described below rather than letting it through.
    #
    # WHAT CHANGED AND WHY: the four MCP negative controls were moved off the
    # live transport onto _Unsendable, via a new _deaf_mcp_client, and the
    # fifth (test_request_without_tier_context_is_denied) onto _deaf_client.
    # build_mcp_client took no `inner`, so the 2026-09-06 remediation had never
    # reached them: one of those tests sets mutate_enabled, allows
    # cymetica.com and raises the tier to MUTATE before asking the guard to
    # refuse place_order. This change can only REMOVE reach, never add it --
    # which is the direction a re-derivation is allowed to go.
    #
    # Re-derived 2026-09-10, and only by ADDING two controls -- no existing
    # line moved. WHAT CHANGED AND WHY: `paper` was declared inert on the three
    # event-card orders and enforced nowhere, because inert_params is read at
    # PROBE and the MUTATE branch never looked at a body. An order carrying
    # amount_usdc and no paper would have gone live, since the platform
    # resolves an absent flag against the account's simulation_mode, which is
    # False. The two new controls assert the refusal and assert that it does
    # NOT widen to the writers that merely declare inert params -- caught by
    # this pin's sibling assertion when the first attempt hung the rule on
    # inert_params and would have refused the a2a writer. Both run through
    # _Unsendable, so a broken refusal reaches a transport that carries
    # nothing rather than the live platform.
    #
    # Re-derived again 2026-09-10, later the same day, for the second half of
    # the same argument. Their release made trade_event_card paper by default
    # and CloneBotRequest publish `paper`, so three floors written for a world
    # without that flag were lowered: the two clone routes to
    # `required_flags: [paper]`, and trade_event_card into a new
    # `mcp_tools.paper_gated` map that the RPC classifier consults before its
    # blanket trade refusal. Three controls added here, all through
    # _Unsendable, and one existing guard -- the money-loop floor -- taught
    # that there are two floors rather than one, since what it must forbid is
    # an endpoint standing behind NEITHER. place_order is deliberately not
    # gated: the CLOB has no paper book and refuses paper=true outright.
    #
    # Re-derived a THIRD time, 2026-09-10, by the deep pass -- and this one is
    # the guard's own hole rather than a new floor. `_check_rpc` raised for
    # `trade` and `provision` and then fell off the end of the function, so an
    # MCP tool in none of components.yaml's lists was PERMITTED at MUTATE with
    # full arguments: the one tier that can spend, while SAFE refuses it by
    # name and PROBE forces empty arguments. Found by the xhigh review and
    # independently by a check-auditor; all three triage readers reached the
    # transport with a tool that does not exist. Two changes: a control that
    # calls an unknown tool at MUTATE and asserts the refusal, and the
    # money-loop floor taught to read the flag NAME rather than only that the
    # set is non-empty -- renaming agents.clone's required_flags from [paper]
    # to [confirm] had left all three sibling guards green while a MUTATE POST
    # carrying `confirm: true` and no paper key satisfied the transport. That
    # second one ships with a negative control, because an assertion that is
    # green on today's file whatever it checks is one nobody has watched fire.
    #
    # Re-derived a FOURTH time, 2026-09-10, by the sweep after that deep pass,
    # and this one is about WHERE a floor points rather than whether it holds.
    # `test_cloning_a_bot_needs_its_paper_flag_too` exercised
    # /api/v1/bots/clone. That path is in no openapi document they publish --
    # it is our own reported 404, #49 -- and /api/v1/agents/* is absent
    # entirely. The route that clones is /api/v1/cloned-bots/clone, and it
    # stood behind NO rule at all, so the paper floor was guarding two doors
    # nobody opens. Default-deny held the real one, which is why nothing could
    # have been spent; but a floor aimed at the wrong door is
    # indistinguishable from a floor until somebody declares the endpoint to
    # make their own request work, and then they inherit whatever they wrote
    # in that commit.
    #
    # Two changes, both adding enforcement: the control now iterates all three
    # routes, and it asserts `paper: false` is refused as well as absent --
    # their schema documents false as a LIVE clone, so a reading that only
    # asked whether the key exists would wave through the one body on that
    # endpoint that spends. Deep-pass finding A06 said this test named "both
    # clone paths" and exercised one; this is the sharper version of the same
    # sentence.
    #
    # Re-derived a FIFTH time, deep pass of 2026-09-11, finding T03 (triage
    # 3/3), and again only adding enforcement. The money-loop floor's `must`
    # never named the event-card orders -- the ones this repository actually
    # places -- so `named_wrong` never read their flag: event_cards.short
    # moved to required_flags [confirm] passed a MUTATE POST with no `paper`
    # and every guard stayed green. buy, sell and short are in `must` now; all
    # three stand on [paper], and short on [confirm] is refused. The file
    # differs from the pinned one by those five lines only. Changing a guard is
    # a rule change for the pass, so three readers voted on it first: 3/3 that
    # it weakens nothing and touches no operator decision (RC1, DEEP-PASS.md).
    #
    # Re-derived a SIXTH time, 2026-09-20, and again only adding enforcement.
    # The architecture audit found the one call site in the tree that built an
    # httpx client outside qa/client.py, holding the guard's private sentinel:
    # qa/fingerprint.py, so the platform corpus was read every session with no
    # SafetyTransport under it. The fix is a factory
    # (qa/client.py::build_fingerprint_client); the new test here proves the
    # transport is really underneath it -- no tier in scope must still refuse
    # -- and pins the two request properties the factory may not normalise,
    # Accept: */* and follow_redirects, because the fingerprint is a hash of
    # response bytes and tidying either one would demote every GREEN row to
    # AMBER. Nothing existing was weakened: the file differs by one added
    # test. Measured after the change: 9 of 9 corpus parts hash exactly as the
    # last run record holds them.
    #
    # Re-derived a SEVENTH time, 2026-09-22, and again only adding
    # enforcement. The paper gate on MCP tools read `not args.get(gate)` --
    # present and truthy -- so `paper: "false"` passed it, and
    # place_arena_order, whose stop is `mode: 'paper'` against a truthy
    # `'live'`, could not be gated at all. A flag gate now needs `True` itself
    # and a value gate the exact value (components.yaml:
    # `place_arena_order: {mode: paper}`). The file differs by one added test,
    # which went red against a mutant restoring the truthy reading.
    #
    # Re-derived an EIGHTH time, 2026-09-22 evening, by the deep pass (C01,
    # 3/3), and again only adding enforcement: the REST floor's
    # `required_flags` read the same truthy `not payload.get(flag)` the MCP
    # gate had just stopped reading, and `_check_rpc` returned unread on a
    # JSON-RPC body that was a list, so a batch carried a live
    # place_arena_order past it. One added test, red on the string flag and,
    # with that fixed, red against a mutant that skipped the batch again.
    #
    # Re-derived a NINTH time, 2026-09-23 (B1 of the whole-project review,
    # 3/3), and again only adding enforcement: PROBE read a JSON body alone,
    # so `toggle-trading?enabled=true` with an empty body -- the parameter
    # rides in the query -- and a form body both passed as inert. One added
    # test, red on the query string before the fix.
    "test_guard_is_real.py": "0ac8b845c5c7b9a00875bb86bd1d8e95005cc5be7fa54368e000e368df6a3f47",
}


def _sha_lines(path: Path, first: int, last: int) -> str:
    lines = path.read_text(encoding="utf-8").splitlines(keepends=True)
    return hashlib.sha256("".join(lines[first - 1:last]).encode("utf-8")).hexdigest()


@qa(component="meta.pipeline", tier=SafetyTier.SAFE, surface="meta")
def test_guard_sections_are_byte_identical_to_ca0bc45():
    actual = {
        "conftest.py:44-135": _sha_lines(CONFTEST, 44, 135),
        "conftest.py:141-230": _sha_lines(CONFTEST, 141, 230),
        "test_guard_is_real.py": hashlib.sha256(GUARD_TESTS.read_bytes()).hexdigest(),
    }
    drifted = {k: (PINNED[k][:12], v[:12]) for k, v in actual.items() if v != PINNED[k]}
    assert not drifted, (
        "\nThe safety guard's pinned sections changed. If that was intended, "
        "re-derive the hashes deliberately and say why in the commit; if not, "
        "revert.\n" + "\n".join(f"  {k}: pinned {a}… now {b}…" for k, (a, b) in drifted.items())
    )


@qa(component="meta.pipeline", tier=SafetyTier.SAFE, surface="meta")
def test_no_guard_self_test_can_skip_itself():
    """A skipped guard is exactly as unproven as a failed one, and quieter.

    The session aborts when a meta test FAILS. Nothing notices a skip, so a
    `skipif` on one of these would retire a safety proof while leaving the
    suite green -- the relaxation CLAUDE.md names ("a red test here is the
    system working; do not fix it by relaxing the rule") in its least visible
    form.

    One skip is legitimate and stays: `importorskip("requests")`, because the
    ban it proves is itself conditional -- qa/client.py only bans
    requests.Session when requests can be imported, and requests is not a
    declared dependency. There is nothing to prove when there is nothing to
    ban. Every other way out is refused.
    """
    source = GUARD_TESTS.read_text(encoding="utf-8")

    for forbidden in ("skipif", "mark.skip", "xfail", "pytest.skip("):
        assert forbidden not in source, (
            f"{forbidden} appears in the guard self-tests. A guard that can "
            f"excuse itself proves nothing, and the session only aborts on a "
            f"failure -- a skip passes in silence."
        )

    allowed = 'pytest.importorskip("requests")'
    assert source.count("importorskip") == source.count(allowed) == 1, (
        "the only conditional skip permitted here is the requests import, "
        "whose ban is conditional too"
    )


@qa(component="meta.pipeline", tier=SafetyTier.SAFE, surface="meta")
def test_meta_tests_are_ordered_guard_first():
    """Within the meta block, the guard's own tests must precede the pipeline's.

    Alphabetical collection gives test_guard_is_real < test_pipeline_*, and the
    conftest sorts every /meta/ item ahead of everything else. Assert both so a
    rename cannot silently move the pipeline tests ahead of the guard.
    """
    names = sorted(p.name for p in (REPO / "tests" / "meta").glob("test_*.py"))
    assert names[0] == "test_guard_is_real.py", names
    assert all(n.startswith("test_pipeline_") for n in names[1:]), names


@qa(component="meta.pipeline", tier=SafetyTier.SAFE, surface="meta")
def test_the_configure_time_self_check_feels_each_layer_coming_off(monkeypatch):
    """Negative controls for the check that runs before every session.

    The ordering pinned above stops a session whose guard tests FAIL. It stops
    nothing when the selector never collects them, and that has happened: live
    requests went out with the guard unproven. So `pytest_configure` now calls
    `assert_client_guard_blocks()` on every invocation, however narrow.

    A self-check that cannot fail is worse than none, because it reads like
    proof. Take each layer off and require the check to name the one that let
    go. Nothing here can send: every client it builds sits on a transport that
    raises instead of carrying, which is why breaking the probe_only floor
    below produces a message rather than a POST to /api/v1/funding/withdraw.
    """
    from dataclasses import replace

    from qa.client import (GuardBreached, assert_client_guard_blocks,
                           install_client_guard, remove_client_guard)
    from qa.safety import EndpointRegistry, SafetyTransport

    assert "assert_client_guard_blocks()" in CONFTEST.read_text(encoding="utf-8"), \
        "pytest_configure no longer runs the self-check; the layers below are " \
        "proven for nothing if nothing calls them"

    # Unbroken, it passes. Otherwise the controls below prove only that a
    # thrower throws.
    assert_client_guard_blocks()

    # Layer 1 -- the construction ban.
    remove_client_guard()
    try:
        with pytest.raises(GuardBreached, match="layer 1"):
            assert_client_guard_blocks()
    finally:
        install_client_guard()

    # Layer 2 -- the transport stops enforcing at all.
    with monkeypatch.context() as m:
        m.setattr(SafetyTransport, "handle_request",
                  lambda self, request: self.inner.handle_request(request))
        with pytest.raises(GuardBreached, match="layer 2"):
            assert_client_guard_blocks()

    # Layer 3 -- the tier ladder goes, the no-tier check stays.
    with monkeypatch.context() as m:
        m.setattr(SafetyTransport, "_check", lambda self, *a, **k: None)
        with pytest.raises(GuardBreached, match="layer 3"):
            assert_client_guard_blocks()

    # Layer 4 -- the probe_only floor comes off, which is the one that has.
    #
    # At ENFORCEMENT, not in the corpus: the check picks its subject from the
    # rules that declare probe_only, so emptying that list makes it report
    # "nothing to test" instead of exercising the floor -- a control that
    # passes on the precondition and proves nothing about the transport.
    # Patching match() leaves the subject declared and takes the floor off the
    # rule the transport actually consults.
    real_match = EndpointRegistry.match

    with monkeypatch.context() as m:
        m.setattr(EndpointRegistry, "match",
                  lambda self, path, method: (
                      replace(rule, probe_only=False)
                      if (rule := real_match(self, path, method)) else None))
        with pytest.raises(GuardBreached, match="layer 4.*let it through"):
            assert_client_guard_blocks()

    # And the precondition has its own control, since it is now the thing that
    # would stop every session if the corpus lost its floors altogether.
    real_load = EndpointRegistry.load  # bound before the patch, or it recurses

    def _floorless(*args, **kwargs):
        reg = real_load()
        reg.rules = [replace(r, probe_only=False) for r in reg.rules]
        return reg

    with monkeypatch.context() as m:
        m.setattr(EndpointRegistry, "load", _floorless)
        with pytest.raises(GuardBreached, match="layer 4 has nothing to test"):
            assert_client_guard_blocks()

    # And it is whole again afterwards -- a control that leaves the guard off
    # would hand every later test in this session a live client.
    assert_client_guard_blocks()


@qa(component="meta.pipeline", tier=SafetyTier.SAFE, surface="meta")
def test_failing_meta_test_aborts_session_before_later_tests(pytester, tmp_path):
    """The abort is real: a red meta test stops the run; nothing after it runs.

    A subprocess pytest with the REAL conftest, a deliberately failing canary
    in tests/meta/, and a passing test in tests/x/. Offline and redirected so
    the inner session touches neither the network nor the committed state/.
    """
    pytester.makefile(".toml", pyproject=(REPO / "pyproject.toml").read_text(encoding="utf-8"))
    pytester.mkpydir("tests")
    (pytester.path / "tests" / "conftest.py").write_text(
        CONFTEST.read_text(encoding="utf-8"), encoding="utf-8")
    meta = pytester.path / "tests" / "meta"
    meta.mkdir()
    (meta / "test_zz_canary.py").write_text(textwrap.dedent("""
        from qa.marks import SafetyTier, qa

        @qa(component="meta.pipeline", tier=SafetyTier.SAFE, surface="meta")
        def test_canary_fails_on_purpose():
            assert False, "canary"
    """), encoding="utf-8")
    later = pytester.path / "tests" / "x"
    later.mkdir()
    (later / "test_later.py").write_text(textwrap.dedent("""
        from qa.marks import SafetyTier, qa

        @qa(component="meta.pipeline", tier=SafetyTier.SAFE, surface="meta")
        def test_must_never_run():
            assert True
    """), encoding="utf-8")

    env = dict(os.environ)
    env["PYTHONPATH"] = str(REPO)
    env["QA_OFFLINE"] = "1"
    env["QA_STATE_DIR"] = str(tmp_path / "state")
    env["PYTHONIOENCODING"] = "utf-8"

    real_runs_before = sorted(p.name for p in (REPO / "state" / "runs").glob("run-*.json"))

    proc = subprocess.run(
        [sys.executable, "-m", "pytest", "tests", "-q", "-p", "no:cacheprovider"],
        cwd=pytester.path, env=env, capture_output=True, text=True, encoding="utf-8", errors="replace", timeout=180,
    )
    out = proc.stdout + proc.stderr
    # With -q the final line is the bare summary, e.g. "1 failed in 0.19s".
    summary = [line for line in out.splitlines() if line.strip()][-1]

    assert "SAFETY GUARD SELF-TEST FAILED" in out, out
    assert "test_canary_fails_on_purpose" in out, out
    assert summary.startswith("1 failed"), f"expected exactly the canary to fail:\n{out}"
    assert "passed" not in summary, f"the later test ran despite the abort:\n{out}"

    # The inner session's run record went to the temp dir, never to the repo.
    inner_runs = list((tmp_path / "state" / "runs").glob("run-*.json"))
    assert len(inner_runs) == 1, inner_runs
    real_runs_after = sorted(p.name for p in (REPO / "state" / "runs").glob("run-*.json"))
    assert real_runs_after == real_runs_before, \
        "the inner session wrote into the committed state/runs/"
