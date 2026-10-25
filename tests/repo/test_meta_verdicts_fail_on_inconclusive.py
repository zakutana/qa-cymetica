"""A meta test that drives a check whole fails loudly where an Inconclusive took a verdict's place.

Deep pass 2026-10-25, C01 and C02 (3/3 each). tests/meta/test_pipeline_check_subjects.py and
tests/meta/test_pipeline_build_it_better.py drive vendor checks whole on stub clients and expect a
FAIL (`pytest.raises(AssertionError)`) or a pass (a bare call). An `Inconclusive` raised where a
verdict was due is neither: it slips past `pytest.raises(AssertionError)`, and qa/report_plugin.py
records a test that raises one as SKIPPED, exit 0. `test_a_card_that_is_closed_on_rest_and_open_on_mcp_fails`
hosts every `_the_*_readings()` helper, so one such site skipped every reading after it -- a green
suite over readings that never ran. Commit 82ad8f20 wrapped three expected passes and left the rest.

So every such site sits inside `qa.marks.verdict_due()`, which turns an Inconclusive into a failure.
Measured, not read off the source: each call a test makes to a check's `test_*` function is replayed
with an Inconclusive in its place, one call at a time. Where that call gave a verdict (it returned,
or raised AssertionError) the test must now FAIL through verdict_due -- not skip, not pass, and not
with an AssertionError, which a bare `pytest.raises(AssertionError)` around the site would swallow.
Where the call was itself expected to be inconclusive, its own `pytest.raises(Inconclusive)` is the
reading and nothing more is asked.
"""

from __future__ import annotations

import importlib.util
import inspect
from pathlib import Path

import pytest

from qa.marks import Inconclusive, SafetyTier, qa

REPO = Path(__file__).resolve().parent.parent.parent
FILES = ["tests/meta/test_pipeline_check_subjects.py", "tests/meta/test_pipeline_build_it_better.py"]
INJECTED = "injected in place of a verdict by tests/repo/test_meta_verdicts_fail_on_inconclusive.py"
_RAISED = (Exception, pytest.fail.Exception, pytest.skip.Exception)


def _module(relative: str):
    spec = importlib.util.spec_from_file_location("verdict_sites_" + Path(relative).stem,
                                                  REPO / relative)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _drive(module, test_name: str, inject_at: int | None = None):
    """Run one test of the file with every call to a check's `test_*` function counted, and the
    call numbered `inject_at` (from 1) answered with an Inconclusive instead of run. Returns
    (calls, raised): calls is [check function, how it ended], raised what the test raised or None.
    Every file drives its checks through its own `_load`; that is where the count is put."""
    calls: list[list] = []
    real_load = module._load

    def counted(fn, name):
        def call(*args, **kwargs):
            calls.append([name, "raised something else"])
            if len(calls) == inject_at:
                calls[-1][1] = "injected"
                raise Inconclusive(INJECTED)
            try:
                out = fn(*args, **kwargs)
            except AssertionError:
                calls[-1][1] = "failed"
                raise
            except Inconclusive:
                calls[-1][1] = "inconclusive"
                raise
            calls[-1][1] = "passed"
            return out
        return call

    def load(*args, **kwargs):
        check = real_load(*args, **kwargs)
        for name in dir(check):
            fn = getattr(check, name)
            if name.startswith("test_") and inspect.isfunction(fn):
                setattr(check, name, counted(fn, name))
        return check

    module._load = load
    try:
        test = getattr(module, test_name)
        with pytest.MonkeyPatch.context() as patch:
            wanted = inspect.signature(test).parameters
            test(**({"monkeypatch": patch} if "monkeypatch" in wanted else {}))
    except _RAISED as exc:
        return calls, exc
    finally:
        module._load = real_load
    return calls, None


@qa(component="meta.pipeline", tier=SafetyTier.SAFE, surface="meta")
@pytest.mark.parametrize("relative", FILES)
def test_an_inconclusive_where_a_verdict_was_due_fails_the_meta_test(relative):
    module = _module(relative)
    tests = sorted(name for name, fn in vars(module).items()
                   if name.startswith("test_") and inspect.isfunction(fn))
    escaped, swallowed, sites = [], [], 0
    for name in tests:
        calls, raised = _drive(module, name)
        assert raised is None, f"{name} does not pass before anything is injected: {raised!r}"
        for at, (check, ended) in enumerate(calls, start=1):
            if ended not in ("passed", "failed"):
                continue
            sites += 1
            _, raised = _drive(module, name, inject_at=at)
            if isinstance(raised, pytest.fail.Exception) and INJECTED in str(raised):
                continue
            where = (f"{name}, call {at} to {check} (it {ended}): "
                     f"{type(raised).__name__ if raised is not None else 'the test passed'}")
            (escaped if isinstance(raised, Inconclusive) else swallowed).append(where)
    assert sites, f"no call to a check gave a verdict in {relative}: nothing was measured"
    assert not escaped, (
        f"{len(escaped)} of {sites} sites in {relative} let an Inconclusive out of the test, which "
        f"the report plugin records as SKIPPED with exit 0 (and in the host test, every reading "
        f"after it never runs):\n  " + "\n  ".join(escaped))
    assert not swallowed, (
        f"{len(swallowed)} of {sites} sites in {relative} answered an Inconclusive with something "
        f"other than verdict_due's failure -- passed on, or an AssertionError a "
        f"pytest.raises(AssertionError) can swallow:\n  " + "\n  ".join(swallowed))
