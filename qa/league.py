"""Agent League: what we answer by arithmetic, and the refusals around it.

Cymetica's Agent League (llms.txt, "## Agent League"; their X post of 2026-10-09) sets puzzles
every two hours, each with a right answer, and pays 1,000 / 2,500 / 10,000 ET10 a puzzle by
tier -- Phase 1, no user deposits. [operator 2026-10-09] "Ucastni se", and, asked why the writes
were closed, "Proc by mely byt zamcete? Normalne se povoluji".

Only two families are answered, because only two are exact arithmetic on the puzzle's own
snapshot (the "simple" tier, 1,000 ET10 each):

  sequence_similarity   the Levenshtein distance of two nucleotide sequences
  cex_dex_arb           the net edge, DEX minus CEX in bps of the CEX price, minus gas (and any
                        bridge cost) in bps of the notional

A forecast (attention, unlock, funding) or a 10,000-tier family (constrained portfolio,
liquidity range) takes a judgement this repository does not have, and a reasoning written to
please the scorer would be decoration, not an answer: `refusal` leaves them alone.

The reasoning is the computation. Their rule for an EXPLAINED answer is all three of
`data_used` (non-empty), two or more `factors`, and at least one `rejected_options`;
`explained` is that rule, and every figure a factor quotes is the one computed here.
"""

from __future__ import annotations

from datetime import datetime, timezone

COMPUTABLE = ("sequence_similarity", "cex_dex_arb")


class Unsolvable(ValueError):
    """The snapshot does not hold what the arithmetic needs."""


def levenshtein(a: str, b: str) -> int:
    """Insertions + deletions + substitutions, each 1 (the classic dynamic programme)."""
    if a == b:
        return 0
    if not a or not b:
        return len(a) + len(b)
    previous = list(range(len(b) + 1))
    for i, left in enumerate(a, 1):
        row = [i]
        for j, right in enumerate(b, 1):
            row.append(min(previous[j] + 1, row[j - 1] + 1, previous[j - 1] + (left != right)))
        previous = row
    return previous[-1]


def _num(value) -> bool:
    return isinstance(value, (int, float)) and not isinstance(value, bool)


def _edge_parts(snapshot: dict) -> tuple[float, float, float]:
    """(price gap, gas, bridge), each in bps; gas and bridge are costs, positive."""
    need = ("cex_px", "dex_px", "gas_gwei", "eth_usd", "gas_units", "notional_usd")
    if not all(_num((snapshot or {}).get(key)) for key in need) or snapshot["cex_px"] <= 0 \
            or snapshot["notional_usd"] <= 0:
        raise Unsolvable(f"the snapshot lacks one of {need}")
    bridge_usd = snapshot.get("bridge_cost_usd") or 0.0
    if not _num(bridge_usd):
        raise Unsolvable("bridge_cost_usd is not a number")
    gap = (snapshot["dex_px"] - snapshot["cex_px"]) / snapshot["cex_px"] * 1e4
    gas_usd = snapshot["gas_gwei"] * 1e-9 * snapshot["gas_units"] * snapshot["eth_usd"]
    return gap, gas_usd / snapshot["notional_usd"] * 1e4, bridge_usd / snapshot["notional_usd"] * 1e4


def net_edge_bps(snapshot: dict) -> float:
    gap, gas, bridge = _edge_parts(snapshot)
    return gap - gas - bridge


def explained(reasoning) -> bool:
    """Their rule: data_used non-empty, two or more factors, at least one rejected option."""
    return (isinstance(reasoning, dict)
            and bool(reasoning.get("data_used"))
            and len(reasoning.get("factors") or []) >= 2
            and len(reasoning.get("rejected_options") or []) >= 1)


def _sequence(puzzle: dict) -> tuple[float, dict]:
    snap = puzzle.get("snapshot") or {}
    a, b = snap.get("seq_a"), snap.get("seq_b")
    if not isinstance(a, str) or not isinstance(b, str) or not a or not b:
        raise Unsolvable("the snapshot carries no seq_a and seq_b")
    forward, back = levenshtein(a, b), levenshtein(b, a)
    if forward != back:
        raise Unsolvable(f"the distance is not symmetric ({forward} against {back})")
    hamming = sum(x != y for x, y in zip(a, b)) + abs(len(a) - len(b)) if len(a) == len(b) else None
    return float(forward), {
        "data_used": ["seq_a", "seq_b"],
        "factors": [
            {"name": f"exact Levenshtein distance by dynamic programming over the two sequences "
                     f"({len(a)} and {len(b)} bases; insertion, deletion and substitution cost 1): {forward}",
             "weight": 0.9},
            {"name": f"cross-check: the distance is the same read from either sequence ({back}) "
                     f"and lies inside the stated range", "weight": 0.1}],
        "rejected_options": [
            f"the snapshot's naive value ({snap.get('naive')}): a heuristic, not the distance",
            "Hamming distance (substitutions only): the puzzle also counts insertions and deletions"
            + (f", and here it would read {hamming}" if hamming is not None else "")]}


def _arb(puzzle: dict) -> tuple[float, dict]:
    snap = puzzle.get("snapshot") or {}
    gap, gas, bridge = _edge_parts(snap)
    net = gap - gas - bridge
    return net, {
        "data_used": ["cex_px", "dex_px", "gas_gwei", "eth_usd", "gas_units", "notional_usd",
                      "bridge_cost_usd"],
        "factors": [
            {"name": f"price gap, (DEX - CEX) / CEX in bps: {snap['dex_px']:.4f} against "
                     f"{snap['cex_px']:.4f} is {gap:.2f} bps", "weight": 0.7},
            {"name": f"gas: {snap['gas_gwei']:g} gwei x {snap['gas_units']:g} units x ETH "
                     f"{snap['eth_usd']:.2f} is {gas:.2f} bps of the {snap['notional_usd']:g} USD "
                     f"notional", "weight": 0.25},
            {"name": f"bridge cost {bridge:.2f} bps ({snap.get('chain') or 'same chain'})",
             "weight": 0.05}],
        "rejected_options": [
            f"the snapshot's naive edge ({snap.get('naive')} bps): the price gap alone, it ignores gas",
            "CEX minus DEX: the puzzle defines the edge as DEX minus CEX, so the sign would flip"]}


_SOLVERS = {"sequence_similarity": _sequence, "cex_dex_arb": _arb}


def solve(puzzle: dict) -> tuple[float, dict]:
    """(the value, its reasoning) for a puzzle of a family we compute; Unsolvable otherwise."""
    solver = _SOLVERS.get((puzzle or {}).get("family"))
    if solver is None:
        raise Unsolvable(f"no arithmetic for the family {(puzzle or {}).get('family')!r}")
    return solver(puzzle)


def _moment(value):
    try:
        moment = datetime.fromisoformat(str(value).replace("Z", "+00:00"))
    except ValueError:
        return None
    return moment if moment.tzinfo else moment.replace(tzinfo=timezone.utc)


def refusal(puzzle: dict, answered: set, now: datetime | None = None) -> str | None:
    """Why this puzzle is not answered now, or None. Checked before any body exists."""
    now = now or datetime.now(timezone.utc)
    if not isinstance(puzzle, dict) or puzzle.get("id") is None:
        return "not a puzzle"
    if puzzle.get("status") != "open":
        return f"the puzzle is not open (status {puzzle.get('status')!r})"
    closes = _moment(puzzle.get("closes_at"))
    if closes is None or closes <= now:
        return f"the puzzle is closed (closes_at {puzzle.get('closes_at')})"
    if puzzle.get("family") not in COMPUTABLE:
        return f"family {puzzle.get('family')!r} is not exact arithmetic on its snapshot"
    if puzzle.get("answer_type") != "number" or puzzle.get("kind") != "deterministic":
        return f"the puzzle asks for a {puzzle.get('answer_type')}, not a number"
    if puzzle["id"] in answered:
        return "already answered: one answer per player per puzzle"
    try:
        value, _ = solve(puzzle)
    except Unsolvable as exc:
        return f"cannot be computed: {exc}"
    span = (puzzle.get("snapshot") or {}).get("range")
    if isinstance(span, dict) and _num(span.get("lo")) and _num(span.get("hi")) \
            and not span["lo"] <= value <= span["hi"]:
        return (f"the computed {value:.2f} lies outside the puzzle's stated range "
                f"{span['lo']:g}..{span['hi']:g}: a snapshot we misread is not sent")
    return None


def answer_body(puzzle: dict, player_id: int) -> dict:
    """The POST body for a puzzle `refusal` let through."""
    value, reasoning = solve(puzzle)
    return {"player_id": player_id, "answer": {"value": value}, "reasoning": reasoning}
