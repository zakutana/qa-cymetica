"""Build mockup.html (this folder): the /company owner view, redrawn.

The office is an isometric SVG drawn from world coordinates (tiles), so every room, desk,
monitor, wall screen and kanban note sits where the data puts it. Sample data, one coherent
state on the Pro plan: the turn counter, the rooms' counts and the department rows agree.
Palette: the site's navy, cyan, green, red and blue only (scanned by render.py).
"""
from __future__ import annotations

import html
import math
from pathlib import Path

HERE = Path(__file__).resolve().parent

# -- palette (theirs: company-office.js and the site rule) ------------------------------------
BG, DEEP, NAVY, NAVY2, LINE, LINE2, LINE3 = ("#0a0e17", "#06090f", "#0d1520", "#111a28",
                                             "#16233a", "#1a2a44", "#1e3050")
TEXT, DIM, DIM2 = "#E6EDF7", "#A9B8CC", "#7f93ad"
CYAN, GREEN, RED, BLUE = "#00cfff", "#00ff88", "#ff4444", "#3b82f6"
STATUS = {"working": CYAN, "idle": DIM2, "blocked": RED, "done": GREEN}

# -- isometric projection -----------------------------------------------------------------------
S, C30, S30 = 22.0, math.cos(math.radians(30)), 0.5
WORLD = 23
OX, OY = WORLD * S * C30 + 24, 74


def P(x, y, z=0.0):
    return (OX + (x - y) * S * C30, OY + (x + y) * S * S30 - z * S)


def pts(*ps):
    return " ".join(f"{a:.1f},{b:.1f}" for a, b in ps)


def poly(ps, fill, stroke="none", sw=0.8, op=1.0, extra=""):
    return (f'<polygon points="{pts(*ps)}" fill="{fill}" stroke="{stroke}" stroke-width="{sw}"'
            f'{f" opacity=\"{op}\"" if op != 1 else ""}{extra}/>')


def box(x, y, z, w, d, h, top, left, right, stroke=None, op=1.0):
    st = stroke or "none"
    return "".join([
        poly([P(x, y + d, z), P(x + w, y + d, z), P(x + w, y + d, z + h), P(x, y + d, z + h)], left, st, 0.6, op),
        poly([P(x + w, y, z), P(x + w, y + d, z), P(x + w, y + d, z + h), P(x + w, y, z + h)], right, st, 0.6, op),
        poly([P(x, y, z + h), P(x + w, y, z + h), P(x + w, y + d, z + h), P(x, y + d, z + h)], top, st, 0.6, op),
    ])


def esc(s):
    return html.escape(str(s), quote=True)


def text(x, y, s, size=9, fill=TEXT, weight=400, anchor="start", family="mono", extra=""):
    fam = "'Archivo Black',sans-serif" if family == "display" else "'JetBrains Mono',monospace"
    return (f'<text x="{x:.1f}" y="{y:.1f}" font-family="{fam}" font-size="{size}" fill="{fill}" '
            f'font-weight="{weight}" text-anchor="{anchor}"{extra}>{esc(s)}</text>')


def on_back_wall(x0, u, y_plane, z_top):
    """A transform putting local px coords on the +y-facing wall plane (y = y_plane)."""
    ox, oy = P(x0 + u, y_plane, z_top)
    return f'matrix({C30:.4f} {S30:.4f} 0 1 {ox:.1f} {oy:.1f})'


def on_side_wall(x_plane, y0, v, z_top):
    """The same for the +x-facing wall plane (x = x_plane): local +x runs along world +y."""
    ox, oy = P(x_plane, y0 + v, z_top)
    return f'matrix({-C30:.4f} {S30:.4f} 0 1 {ox:.1f} {oy:.1f})'


def avatar(sx, sy, body, label=None, ring=None, head=DIM):
    out = [f'<ellipse cx="{sx:.1f}" cy="{sy:.1f}" rx="7.5" ry="3.2" fill="{DEEP}" opacity="0.7"/>']
    if ring:
        out.append(f'<ellipse cx="{sx:.1f}" cy="{sy:.1f}" rx="11" ry="5" fill="none" stroke="{ring}" '
                   f'stroke-width="1.2" opacity="0.8" filter="url(#glow)"/>')
    out.append(f'<rect x="{sx - 6:.1f}" y="{sy - 17:.1f}" width="12" height="14" rx="5" fill="{body}"/>')
    out.append(f'<rect x="{sx - 6:.1f}" y="{sy - 9:.1f}" width="12" height="6" rx="2" fill="{DEEP}" opacity="0.28"/>')
    out.append(f'<circle cx="{sx:.1f}" cy="{sy - 21.5:.1f}" r="4.8" fill="{head}"/>')
    if label:
        w = 5.6 * len(label) + 8
        out.append(f'<rect x="{sx - w / 2:.1f}" y="{sy - 39:.1f}" width="{w:.1f}" height="11" rx="5.5" '
                   f'fill="{BG}" stroke="{body}" stroke-width="0.7" opacity="0.92"/>')
        out.append(text(sx, sy - 30.6, label, 7.6, TEXT, 500, "middle"))
    return "".join(out)


def desk(x, y, screen, lines=True):
    """A desk 1.9 x 0.9 with a monitor whose screen faces +y (the viewer and the agent)."""
    out = [box(x, y, 0, 1.9, 0.9, 0.42, LINE3, LINE, NAVY2, LINE2)]
    out.append(box(x + 0.5, y + 0.14, 0.42, 0.9, 0.08, 0.56, NAVY, screen, NAVY))
    if lines and screen not in (LINE2, NAVY2):
        tf = on_back_wall(x + 0.5, 0.12, y + 0.22, 0.42 + 0.5)
        for i, wl in enumerate((14, 9, 12, 6)):
            out.append(f'<rect transform="{tf}" x="2" y="{2 + i * 2.6:.1f}" width="{wl}" height="1.1" '
                       f'fill="{BG}" opacity="0.55"/>')
    out.append(box(x + 0.7, y + 1.08, 0, 0.5, 0.45, 0.22, NAVY2, LINE, NAVY))
    return "".join(out)


# -- the company (sample data, one coherent state) ----------------------------------------------
ROOMS = [
    {"name": "DEVELOPMENT", "cell": (0, 0), "status": "working", "open": 2, "done": 4, "failed": 0,
     "units": 1.10, "experts": [("Developer", "working"), ("Researcher", "idle")],
     "screen": "BB request: Gem Screener logos", "kanban": {"queued": 1, "running": 1, "done": 4, "failed": 0}},
    {"name": "DESIGN STUDIO", "cell": (8, 0), "status": "idle", "open": 0, "done": 2, "failed": 0,
     "units": 0.44, "experts": [("Designer", "idle"), ("Researcher", "idle")],
     "screen": "Idle: 2 briefs shipped", "kanban": {"queued": 0, "running": 0, "done": 2, "failed": 0}},
    {"name": "TESTING", "cell": (16, 0), "status": "working", "open": 1, "done": 2, "failed": 1,
     "units": 0.66, "experts": [("QA tester", "working"), ("Auditor", "working")],
     "screen": "Doc vs behaviour: public pages", "kanban": {"queued": 0, "running": 1, "done": 2, "failed": 1}},
    {"name": "TESTING LAB", "cell": (0, 8), "status": "working", "open": 2, "done": 2, "failed": 1,
     "units": 0.66, "experts": [("Lab scientist", "working"), ("Researcher", "idle")],
     "screen": "Paper: FOMO >=70, 24h exit", "kanban": {"queued": 1, "running": 1, "done": 2, "failed": 1}},
    {"name": "TRADING DESK", "cell": (16, 8), "status": "idle", "open": 1, "done": 1, "failed": 0,
     "units": 0.22, "experts": [("Trader", "idle"), ("Researcher", "idle")],
     "screen": "Queued: basket H2 on paper", "kanban": {"queued": 1, "running": 0, "done": 1, "failed": 0}},
]
OVERLAY: list[str] = []   # name plates, drawn after every room so none is covered
KANBAN_COLOUR = {"queued": BLUE, "running": CYAN, "done": GREEN, "failed": RED}


def room_shell(x0, y0, active, size=7.0, dashed=False):
    out = []
    floor = [P(x0, y0, 0.1), P(x0 + size, y0, 0.1), P(x0 + size, y0 + size, 0.1), P(x0, y0 + size, 0.1)]
    if dashed:
        out.append(poly(floor, NAVY, BLUE, 1.0, 0.55, ' stroke-dasharray="5 5"'))
        return "".join(out)
    out.append(box(x0, y0, 0, size, size, 0.1, "#101b2d", NAVY2, NAVY, LINE))
    for i in range(1, int(size)):
        out.append(f'<line x1="{P(x0 + i, y0, 0.1)[0]:.1f}" y1="{P(x0 + i, y0, 0.1)[1]:.1f}" '
                   f'x2="{P(x0 + i, y0 + size, 0.1)[0]:.1f}" y2="{P(x0 + i, y0 + size, 0.1)[1]:.1f}" '
                   f'stroke="{LINE}" stroke-width="0.6"/>')
        out.append(f'<line x1="{P(x0, y0 + i, 0.1)[0]:.1f}" y1="{P(x0, y0 + i, 0.1)[1]:.1f}" '
                   f'x2="{P(x0 + size, y0 + i, 0.1)[0]:.1f}" y2="{P(x0 + size, y0 + i, 0.1)[1]:.1f}" '
                   f'stroke="{LINE}" stroke-width="0.6"/>')
    if active:
        cx, cy = P(x0 + size / 2, y0 + size / 2, 0.1)
        out.append(f'<ellipse cx="{cx:.1f}" cy="{cy:.1f}" rx="{size * S * 0.95:.1f}" ry="{size * S * 0.55:.1f}" '
                   f'fill="url(#floorglow)"/>')
    # glass back walls
    out.append(box(x0, y0, 0.1, size, 0.12, 1.15, LINE3, LINE2, NAVY, None, 0.62))
    out.append(box(x0, y0, 0.1, 0.12, size, 1.15, LINE3, NAVY, LINE2, None, 0.62))
    a, b, c = P(x0, y0 + size, 1.25), P(x0, y0, 1.25), P(x0 + size, y0, 1.25)
    out.append(f'<polyline points="{pts(a, b, c)}" fill="none" stroke="{BLUE}" stroke-width="1" opacity="0.55"/>')
    # front edge: a lit sill with a door gap facing the corridor
    for (p, q) in (((x0 + size, y0), (x0 + size, y0 + size)), ((x0, y0 + size), (x0 + size, y0 + size))):
        out.append(f'<line x1="{P(*p, 0.12)[0]:.1f}" y1="{P(*p, 0.12)[1]:.1f}" x2="{P(*q, 0.12)[0]:.1f}" '
                   f'y2="{P(*q, 0.12)[1]:.1f}" stroke="{BLUE if not active else CYAN}" stroke-width="1.1" '
                   f'opacity="{0.35 if not active else 0.7}"/>')
    return "".join(out)


def wall_screen(x0, y0, u0, u1, title, colour, bars=None):
    """A screen on the back wall: a lit panel with a skewed caption, or a bar chart."""
    out = [poly([P(x0 + u0, y0 + 0.13, 0.42), P(x0 + u1, y0 + 0.13, 0.42), P(x0 + u1, y0 + 0.13, 1.06),
                 P(x0 + u0, y0 + 0.13, 1.06)], DEEP, colour, 0.9)]
    tf = on_back_wall(x0, u0, y0 + 0.13, 1.06)
    width = (u1 - u0) * S
    if bars:
        top = max(v for _, v in bars) or 1
        bw = (width - 10) / len(bars)
        for i, (c, v) in enumerate(bars):
            h = 9 * v / top
            out.append(f'<rect transform="{tf}" x="{5 + i * bw:.1f}" y="{12.5 - h:.1f}" width="{bw - 2:.1f}" '
                       f'height="{h:.1f}" fill="{c}" opacity="0.9"/>')
    out.append(f'<text transform="{tf}" x="5" y="{(10 if not bars else 4.3) + (0 if bars else 0):.1f}" '
               f'font-family="\'JetBrains Mono\',monospace" font-size="{6.6 if not bars else 4.8}" '
               f'fill="{colour}" font-weight="600">{esc(title[: int(width / 4.1)])}</text>')
    return "".join(out)


def kanban(x0, y0, counts):
    """Sticky notes on the side wall: one column per state, one note per task."""
    out = [poly([P(x0 + 0.13, y0 + 1.0, 0.38), P(x0 + 0.13, y0 + 5.9, 0.38), P(x0 + 0.13, y0 + 5.9, 1.06),
                 P(x0 + 0.13, y0 + 1.0, 1.06)], DEEP, LINE3, 0.8)]
    for col, state in enumerate(("queued", "running", "done", "failed")):
        v = 1.15 + col * 1.2
        for k in range(min(counts.get(state, 0), 4)):
            z = 0.9 - k * 0.15
            out.append(poly([P(x0 + 0.14, y0 + v, z), P(x0 + 0.14, y0 + v + 0.95, z),
                             P(x0 + 0.14, y0 + v + 0.95, z + 0.12), P(x0 + 0.14, y0 + v, z + 0.12)],
                            KANBAN_COLOUR[state], "none", 0, 0.85))
    return "".join(out)


def nameplate(cx, cy, title, colour, line2, w=168):
    out = [f'<rect x="{cx - w / 2:.1f}" y="{cy - 17:.1f}" width="{w}" height="34" rx="6" fill="{BG}" '
           f'stroke="{colour}" stroke-width="0.9" opacity="0.94"/>',
           f'<circle cx="{cx - w / 2 + 11:.1f}" cy="{cy - 6:.1f}" r="3.4" fill="{colour}" filter="url(#glow)"/>',
           text(cx - w / 2 + 20, cy - 2.4, title, 10.2, TEXT, 400, "start", "display")]
    x = cx - w / 2 + 9
    for s, c in line2:
        out.append(text(x, cy + 11.5, s, 8.6, c, 600))
        x += 6.0 * len(s) + 7
    return "".join(out)


def dept_room(r):
    x0, y0 = r["cell"]
    active = r["status"] == "working"
    colour = STATUS[r["status"]]
    out = [room_shell(x0, y0, active)]
    out.append(wall_screen(x0, y0, 1.1, 6.2, r["screen"], colour if active else DIM2))
    out.append(kanban(x0, y0, r["kanban"]))
    for i, (role, st) in enumerate(r["experts"]):
        dx = x0 + 1.0 + i * 2.75
        screen = {"working": CYAN, "idle": LINE2, "blocked": RED}[st]
        out.append(desk(dx, y0 + 1.75, screen))
        sx, sy = P(dx + 0.95, y0 + 3.05, 0.1)
        out.append(avatar(sx, sy, STATUS[st] if st != "idle" else BLUE, role,
                          ring=CYAN if st == "working" else None))
    cx, cy = P(x0 + 4.6, y0 + 5.55, 0.1)
    line2 = [(f"{r['open']} open", CYAN), (f"{r['done']} done", GREEN)]
    if r["failed"]:
        line2.append((f"{r['failed']} failed", RED))
    OVERLAY.append(nameplate(cx, cy, r["name"], colour, line2))
    if r["name"] == "TESTING":   # the selection ring the detail view (?dept) shows
        ring = [P(x0 - 0.15, y0 - 0.15, 0.12), P(x0 + 7.15, y0 - 0.15, 0.12), P(x0 + 7.15, y0 + 7.15, 0.12),
                P(x0 - 0.15, y0 + 7.15, 0.12)]
        OVERLAY.append(poly(ring, "none", CYAN, 2.4, 1.0, ' class="sel" filter="url(#glow)"'))
    return "".join(out)


def hq():
    x0, y0 = 8, 8
    out = [room_shell(x0, y0, True)]
    turns = [(GREEN, 5), (CYAN, 2), (GREEN, 3), (RED, 3), (BLUE, 1), (CYAN, 2)]
    out.append(wall_screen(x0, y0, 3.0, 6.4, "TURNS BY DEPT TODAY", CYAN, bars=turns))
    for i in range(3):   # server racks with LEDs
        rx = x0 + 0.45 + i * 0.85
        out.append(box(rx, y0 + 0.3, 0.1, 0.7, 0.6, 1.55, LINE3, LINE, NAVY2, LINE2))
        for k in range(6):
            lx, ly = P(rx + 0.12 + (k % 2) * 0.3, y0 + 0.9, 0.35 + (k // 2) * 0.42)
            c = (GREEN, CYAN, BLUE)[(i + k) % 3]
            out.append(f'<rect x="{lx:.1f}" y="{ly:.1f}" width="3.2" height="1.6" fill="{c}" opacity="0.9"/>')
    out.append(kanban(x0, y0, {"queued": 2, "running": 3, "done": 4, "failed": 1}))
    # round table and hologram
    cx, cy = P(11.6, 11.4, 0.1)
    rx, ry = 1.2247 * 1.55 * S, 0.7071 * 1.55 * S
    out.append(f'<ellipse cx="{cx:.1f}" cy="{cy:.1f}" rx="{rx:.1f}" ry="{ry:.1f}" fill="{DEEP}" opacity="0.6"/>')
    tz = 0.45 * S
    out.append(f'<path d="M{cx - rx:.1f},{cy - tz:.1f} L{cx - rx:.1f},{cy:.1f} A{rx:.1f},{ry:.1f} 0 0 0 '
               f'{cx + rx:.1f},{cy:.1f} L{cx + rx:.1f},{cy - tz:.1f} Z" fill="{NAVY2}" stroke="{LINE2}"/>')
    out.append(f'<ellipse cx="{cx:.1f}" cy="{cy - tz:.1f}" rx="{rx:.1f}" ry="{ry:.1f}" fill="{LINE3}" '
               f'stroke="{CYAN}" stroke-width="0.9" opacity="0.95"/>')
    out.append(f'<rect x="{cx - 9:.1f}" y="{cy - tz - 64:.1f}" width="18" height="64" fill="url(#beam)"/>')
    for k, z in enumerate((26, 42, 58)):
        out.append(f'<ellipse cx="{cx:.1f}" cy="{cy - tz - z:.1f}" rx="{rx * (0.75 - k * 0.15):.1f}" '
                   f'ry="{ry * (0.75 - k * 0.15):.1f}" fill="none" stroke="{CYAN}" stroke-width="1" '
                   f'opacity="{0.75 - k * 0.2:.2f}"/>')
    out.append(f'<rect x="{cx - 52:.1f}" y="{cy - tz - 100:.1f}" width="104" height="30" rx="6" fill="{BG}" '
               f'stroke="{CYAN}" stroke-width="0.9" opacity="0.94"/>')
    out.append(text(cx, cy - tz - 81.5, "6 OPEN", 12.5, CYAN, 400, "middle", "display"))
    out.append(text(cx, cy - tz - 73.5, "2 wait for you", 7.6, RED, 600, "middle"))
    for (u, v, role, body) in ((10.0, 13.3, None, BLUE), (13.25, 13.1, None, BLUE)):
        sx, sy = P(u, v, 0.1)
        out.append(avatar(sx, sy, body, role))
    sx, sy = P(11.7, 13.9, 0.1)
    out.append(avatar(sx, sy, CYAN, "Manager", ring=CYAN, head=TEXT))
    nx, ny = P(12.9, 14.25, 0.1)
    OVERLAY.append(nameplate(nx + 30, ny + 8, "MANAGER", CYAN, [("routes 6", CYAN), ("2 for you", RED)], w=150))
    return "".join(out)


def owner_room():
    x0, y0 = 8, 16
    out = [room_shell(x0, y0, False)]
    out.append(wall_screen(x0, y0, 1.1, 6.2, "2 approvals waiting", RED))
    out.append(desk(x0 + 2.4, y0 + 1.8, BLUE))
    out.append(box(x0 + 3.95, y0 + 1.95, 0.42, 0.42, 0.42, 0.14, RED, NAVY2, NAVY))
    bx, by = P(x0 + 4.15, y0 + 2.15, 0.6)
    out.append(f'<circle cx="{bx:.1f}" cy="{by - 12:.1f}" r="8" fill="{RED}" filter="url(#glow)"/>')
    out.append(text(bx, by - 8.6, "2", 10, BG, 700, "middle", "display"))
    sx, sy = P(x0 + 3.35, y0 + 3.1, 0.1)
    out.append(avatar(sx, sy, BLUE, "You", head=TEXT))
    cx, cy = P(x0 + 4.6, y0 + 5.55, 0.1)
    OVERLAY.append(nameplate(cx, cy, "YOU", BLUE, [("2 to approve", RED)], w=140))
    return "".join(out)


def audit_room():
    x0, y0 = 0, 16
    out = [room_shell(x0, y0, False)]
    out.append(wall_screen(x0, y0, 1.1, 6.2, "Weekly audit: next in 6d", DIM2))
    out.append(desk(x0 + 2.2, y0 + 1.8, LINE2, lines=False))
    sx, sy = P(x0 + 3.15, y0 + 3.1, 0.1)
    out.append(avatar(sx, sy, BLUE, "Supervisor"))
    cx, cy = P(x0 + 4.6, y0 + 5.55, 0.1)
    OVERLAY.append(nameplate(cx, cy, "WEEKLY AUDIT", DIM2, [("next 6d", DIM), ("0 findings", GREEN)], w=150))
    return "".join(out)


def add_room():
    x0, y0 = 16, 16
    out = [room_shell(x0, y0, False, dashed=True)]
    cx, cy = P(x0 + 3.5, y0 + 3.5, 0.1)
    out.append(f'<circle cx="{cx:.1f}" cy="{cy - 6:.1f}" r="14" fill="none" stroke="{CYAN}" stroke-width="1.2" '
               f'opacity="0.8"/>')
    out.append(text(cx, cy - 0.6, "+", 18, CYAN, 400, "middle", "display"))
    out.append(text(cx, cy + 22, "ADD DEPARTMENT", 8.6, CYAN, 600, "middle"))
    return "".join(out)


CONDUITS = [  # world polylines from a room's door to the Manager's, with packets on them
    ([(3.5, 7.0), (3.5, 7.5), (7.5, 7.5), (7.5, 10.5), (8.0, 10.5)], [(0.35, CYAN), (0.7, GREEN)]),
    ([(11.5, 7.0), (11.5, 8.0)], []),
    ([(19.5, 7.0), (19.5, 7.5), (15.5, 7.5), (15.5, 10.5), (15.0, 10.5)], [(0.25, RED), (0.62, CYAN)]),
    ([(7.0, 12.5), (8.0, 12.5)], []),
    ([(16.0, 12.5), (15.0, 12.5)], []),
    ([(3.5, 16.0), (3.5, 15.5), (10.0, 15.5), (10.0, 15.0)], [(0.5, BLUE)]),
    ([(11.5, 16.0), (11.5, 15.0)], [(0.5, RED)]),
    ([(0.0 + 3.5, 8.0 + 7.0), (3.5, 15.5)], []),
]


def along(path, f):
    seg = [(a, b, math.dist(a, b)) for a, b in zip(path, path[1:])]
    total = sum(s[2] for s in seg)
    d = f * total
    for a, b, l in seg:
        if d <= l:
            t = d / l if l else 0
            return (a[0] + (b[0] - a[0]) * t, a[1] + (b[1] - a[1]) * t)
        d -= l
    return path[-1]


def conduits():
    out = []
    for path, packets in CONDUITS:
        p2 = [P(x, y, 0.03) for x, y in path]
        out.append(f'<polyline points="{pts(*p2)}" fill="none" stroke="{LINE3}" stroke-width="4.5" '
                   f'stroke-linejoin="round"/>')
        out.append(f'<polyline points="{pts(*p2)}" fill="none" stroke="{CYAN}" stroke-width="1.2" '
                   f'stroke-dasharray="3 5" opacity="0.6" stroke-linejoin="round"/>')
        for f, c in packets:
            x, y = along(path, f)
            sx, sy = P(x, y, 0.03)
            out.append(f'<circle cx="{sx:.1f}" cy="{sy:.1f}" r="4" fill="{c}" filter="url(#glow)"/>')
    return "".join(out)


def office_svg():
    lo, hi = P(0, 0), P(WORLD, WORLD)
    width, height = 2 * OX, hi[1] + 26
    parts = [f'<svg class="office" viewBox="0 0 {width:.0f} {height:.0f}" xmlns="http://www.w3.org/2000/svg" '
             f'preserveAspectRatio="xMidYMid meet">',
             '<defs>'
             f'<filter id="glow" x="-80%" y="-80%" width="260%" height="260%"><feGaussianBlur stdDeviation="2.2" '
             'result="b"/><feMerge><feMergeNode in="b"/><feMergeNode in="SourceGraphic"/></feMerge></filter>'
             f'<radialGradient id="floorglow"><stop offset="0" stop-color="{CYAN}" stop-opacity="0.16"/>'
             f'<stop offset="1" stop-color="{CYAN}" stop-opacity="0"/></radialGradient>'
             f'<linearGradient id="beam" x1="0" y1="1" x2="0" y2="0"><stop offset="0" stop-color="{CYAN}" '
             f'stop-opacity="0.45"/><stop offset="1" stop-color="{CYAN}" stop-opacity="0"/></linearGradient>'
             '</defs>']
    # the floor plate
    parts.append(box(-0.6, -0.6, -0.45, WORLD + 1.2, WORLD + 1.2, 0.45, "#0c1422", NAVY2, DEEP, LINE))
    for i in range(0, WORLD + 1):
        a, b = P(i, -0.6), P(i, WORLD + 0.6)
        parts.append(f'<line x1="{a[0]:.1f}" y1="{a[1]:.1f}" x2="{b[0]:.1f}" y2="{b[1]:.1f}" stroke="{NAVY2}" '
                     f'stroke-width="0.6"/>')
        a, b = P(-0.6, i), P(WORLD + 0.6, i)
        parts.append(f'<line x1="{a[0]:.1f}" y1="{a[1]:.1f}" x2="{b[0]:.1f}" y2="{b[1]:.1f}" stroke="{NAVY2}" '
                     f'stroke-width="0.6"/>')
    parts.append(conduits())
    by_depth = {(0, 0): dept_room(ROOMS[0]), (8, 0): dept_room(ROOMS[1]), (16, 0): dept_room(ROOMS[2]),
                (0, 8): dept_room(ROOMS[3]), (8, 8): hq(), (16, 8): dept_room(ROOMS[4]),
                (0, 16): audit_room(), (8, 16): owner_room(), (16, 16): add_room()}
    for cell in sorted(by_depth, key=lambda c: (c[0] + c[1], c[0])):
        parts.append(by_depth[cell])
    parts.extend(OVERLAY)
    parts.append("</svg>")
    return "".join(parts)


# -- the page around it -------------------------------------------------------------------------
DEPT_ROWS = [  # name, status, open, done, failed, units 7d, memory, experts
    ("Development", "working", 2, 4, 0, 1.10, 12, "Developer · Researcher"),
    ("Design studio", "idle", 0, 2, 0, 0.44, 5, "Designer · Researcher"),
    ("Testing", "working", 1, 2, 1, 0.66, 6, "QA tester · Auditor"),
    ("Testing lab", "working", 2, 2, 1, 0.66, 9, "Lab scientist · Researcher"),
    ("Trading desk", "idle", 1, 1, 0, 0.22, 4, "Trader · Researcher"),
]
TURNS_TODAY = ["d"] * 5 + ["r"] * 1 + ["d"] * 2 + ["f"] * 1 + ["d"] * 4 + ["f"] * 1 + ["d"] * 1 + ["r"] * 1


def dept_rows():
    out = []
    for name, st, op, dn, fl, u, mem, ex in DEPT_ROWS:
        out.append(f"""
      <div class="dept {st}{' pick' if name == 'Testing' else ''}">
        <div class="d1"><i class="dot"></i><b>{esc(name)}</b><span class="u">{u:.2f}<small>u</small></span></div>
        <div class="d2"><span class="c">{op}<small>open</small></span><span class="g">{dn}<small>done</small></span>
          <span class="{'r' if fl else 'z'}">{fl}<small>failed</small></span><span class="m">{mem}<small>mem</small></span></div>
        <div class="d3">{esc(ex)}</div>
      </div>""")
    return "".join(out)


def cells():
    cls = {"d": "cd", "r": "cr", "f": "cf"}
    used = "".join(f'<i class="{cls[t]}"></i>' for t in TURNS_TODAY)
    return used + '<i></i>' * (40 - len(TURNS_TODAY))


FEED = [("g", "Testing", "finished “Inventory testable surface”", "19:20"),
        ("r", "Testing", "“Doc vs behaviour” failed, retrying", "19:27"),
        ("c", "Lab", "opened paper: FOMO ≥70, 24h exit", "19:31"),
        ("x", "Development", "asks approval: BB request", "19:38"),
        ("x", "Testing", "asks approval: bug report", "19:41")]


def feed():
    return "".join(f'<li class="{k}"><b>{esc(d)}</b> {esc(t)}<em>{esc(w)}</em></li>' for k, d, t, w in FEED)


PAGE = """<!doctype html>
<html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>Build a Company: office</title>
<link href="https://fonts.googleapis.com/css2?family=Archivo+Black&family=JetBrains+Mono:wght@400;500;600;700&display=swap" rel="stylesheet">
<style>
:root{--bg:#0a0e17;--deep:#06090f;--navy:#0d1520;--navy2:#111a28;--line:#16233a;--line2:#1a2a44;--line3:#1e3050;
--text:#E6EDF7;--dim:#A9B8CC;--dim2:#7f93ad;--cyan:#00cfff;--green:#00ff88;--red:#ff4444;--blue:#3b82f6}
*{box-sizing:border-box;margin:0;padding:0}
html,body{background:var(--bg);color:var(--text);font-family:'JetBrains Mono',monospace;font-size:13px}
body{display:flex;flex-direction:column;height:100vh}
.site{height:48px;display:flex;align-items:center;gap:22px;padding:0 20px;border-bottom:1px solid var(--line)}
.site .logo{font-family:'Archivo Black';font-size:16px}.site .logo i{color:var(--green);font-style:normal}
.site nav{display:flex;gap:18px;color:var(--dim2);font-size:12px}.site nav b{color:var(--text);font-weight:600}
.site .sp{flex:1}
.cobar{display:grid;grid-template-columns:minmax(0,1fr) auto minmax(0,1fr);align-items:center;gap:20px;padding:10px 20px;
 border-bottom:1px solid var(--line);background:linear-gradient(180deg,#0d1520,#0a0e17)}
.who{display:flex;align-items:center;gap:12px;min-width:0}
.mark{width:40px;height:40px;border-radius:9px;background:var(--line3);border:1px solid var(--cyan);display:grid;place-items:center;
 font-family:'Archivo Black';color:var(--cyan);font-size:15px;flex:none}
.who h1{font-family:'Archivo Black';font-size:21px;font-weight:400;white-space:nowrap}
.pill{font-size:10.5px;font-weight:700;letter-spacing:.08em;padding:3px 9px;border-radius:99px;border:1px solid}
.pill.on{color:var(--green);border-color:var(--green);background:rgba(0,255,136,.08)}
.btn{font:600 12px 'JetBrains Mono';padding:7px 12px;border-radius:7px;border:1px solid var(--line3);background:var(--navy2);color:var(--text);white-space:nowrap}
.btn.cy{border-color:var(--cyan);color:var(--cyan)}.btn.gr{background:var(--green);border-color:var(--green);color:var(--bg)}
.btn.rd{border-color:var(--red);color:var(--red)}
.fuel{display:flex;align-items:center;gap:16px;padding:7px 16px;border:1px solid var(--line3);border-radius:12px;background:var(--deep)}
.fuel .k{font-size:10px;letter-spacing:.12em;color:var(--dim2);line-height:1.35}
.fuel .k b{display:block;color:var(--text);font-size:11px}
.fuel .n{display:flex;flex-direction:column;align-items:center;min-width:54px}
.fuel .n b{font-family:'Archivo Black';font-size:30px;line-height:1;font-weight:400}
.fuel .n span{font-size:10px;color:var(--dim2);margin-top:3px}
.fuel .n.low b{color:var(--red)}.fuel .n.wk b{color:var(--cyan)}.fuel .n.ex b{color:var(--blue)}
.fuel .vs{width:1px;height:38px;background:var(--line3)}
.bars{display:grid;gap:6px;min-width:250px}
.bar{display:grid;grid-template-columns:56px 1fr auto;align-items:center;gap:8px;font-size:10.5px;color:var(--dim)}
.bar label{color:var(--dim2);letter-spacing:.08em}
.track{height:7px;border-radius:4px;background:var(--line);overflow:hidden}.track i{display:block;height:100%;border-radius:4px}
.bar em{font-style:normal;white-space:nowrap}.bar em b{color:var(--text)}
.then{font-size:10px;color:var(--dim2)}.then b{color:var(--blue)}
.right{display:flex;justify-content:flex-end;align-items:center;gap:10px}
.appr{display:flex;align-items:center;gap:8px;padding:7px 12px;border-radius:8px;border:1px solid var(--red);color:var(--red);font-weight:700;font-size:12px;background:rgba(255,68,68,.07)}
.appr b{background:var(--red);color:var(--bg);border-radius:99px;padding:0 7px;font-family:'Archivo Black';font-weight:400}
.tabs{display:flex;gap:2px;padding:0 20px;border-bottom:1px solid var(--line);overflow-x:auto}
.tabs a{padding:10px 14px;color:var(--dim2);font-size:12px;font-weight:600;white-space:nowrap;border-bottom:2px solid transparent}
.tabs a.on{color:var(--text);border-color:var(--cyan)}.tabs a sup{color:var(--cyan);font-size:10px;margin-left:3px}
.tabs a sup.r{color:var(--red)}.tabs .sp{flex:1}
.main{display:grid;grid-template-columns:290px minmax(0,1fr) 370px;gap:14px;padding:14px 20px;flex:1;min-height:0}
.panel{background:var(--navy);border:1px solid var(--line);border-radius:12px;padding:12px;min-height:0}
.h{display:flex;align-items:center;justify-content:space-between;font-size:10.5px;letter-spacing:.12em;color:var(--dim2);font-weight:700;margin-bottom:10px}
.h b{color:var(--text)}
.left{display:flex;flex-direction:column;gap:12px;min-height:0}
.depts{display:flex;flex-direction:column;gap:8px}
.dept{border:1px solid var(--line);border-left:3px solid var(--dim2);border-radius:9px;padding:8px 10px;background:var(--navy2)}
.dept.working{border-left-color:var(--cyan)}.dept.blocked{border-left-color:var(--red)}
.d1{display:flex;align-items:center;gap:8px}.d1 b{font-size:13px;flex:1}
.dot{width:8px;height:8px;border-radius:50%;background:var(--dim2)}.working .dot{background:var(--cyan);box-shadow:0 0 8px var(--cyan)}
.u{font-weight:700;color:var(--text)}.u small,.d2 small{color:var(--dim2);font-weight:500;margin-left:3px;font-size:10px}
.d2{display:flex;gap:12px;margin-top:5px;font-weight:700;font-size:13px}
.d2 .c{color:var(--cyan)}.d2 .g{color:var(--green)}.d2 .r{color:var(--red)}.d2 .z{color:var(--dim2)}.d2 .m{color:var(--dim)}
.d3{font-size:10.5px;color:var(--dim2);margin-top:4px}
.mini{display:grid;grid-template-columns:1fr 1fr;gap:8px}
.mini div{background:var(--navy2);border:1px solid var(--line);border-radius:9px;padding:8px 10px}
.mini b{display:block;font-family:'Archivo Black';font-size:18px;font-weight:400}.mini span{font-size:10px;color:var(--dim2)}
.stage{position:relative;display:flex;flex-direction:column;padding:0;overflow:hidden;background:radial-gradient(ellipse at 50% 45%,#101b2d,#0a0e17 70%)}
.stage .top{position:absolute;top:10px;left:12px;right:12px;display:flex;justify-content:space-between;align-items:center;z-index:2}
.live{font-size:11px;font-weight:700;color:var(--green);display:flex;align-items:center;gap:6px;letter-spacing:.1em}
.live i{width:7px;height:7px;border-radius:50%;background:var(--green);box-shadow:0 0 8px var(--green)}
.seg{display:flex;border:1px solid var(--line3);border-radius:8px;overflow:hidden}
.seg a{padding:5px 11px;font-size:11px;font-weight:700;color:var(--dim2);background:var(--deep)}.seg a.on{background:var(--line3);color:var(--cyan)}
.zoom{display:flex;gap:6px}.zoom a{width:28px;height:28px;display:grid;place-items:center;border:1px solid var(--line3);border-radius:7px;background:var(--deep);color:var(--dim)}
.office{flex:1;width:100%;min-height:0;display:block;margin-top:8px}
.strip{display:flex;align-items:center;gap:14px;padding:9px 12px;border-top:1px solid var(--line);background:rgba(6,9,15,.7)}
.strip .lab{font-size:10.5px;letter-spacing:.1em;color:var(--dim2);font-weight:700;white-space:nowrap}.strip .lab b{color:var(--text);font-size:13px}
.cells{display:grid;grid-template-columns:repeat(40,1fr);gap:2px;flex:1}
.cells i{height:12px;border-radius:2px;background:var(--line)}
.cells i.cd{background:var(--green)}.cells i.cr{background:var(--cyan)}.cells i.cf{background:var(--red)}
.legend{display:flex;gap:10px;font-size:10.5px;color:var(--dim2);white-space:nowrap}
.legend i{display:inline-block;width:8px;height:8px;border-radius:50%;margin-right:4px;vertical-align:0}
.rightcol{display:flex;flex-direction:column;gap:12px;min-height:0}
.ap{border-top:2px solid var(--red)}
.ai{border:1px solid var(--line);border-radius:9px;padding:9px;background:var(--navy2);margin-bottom:8px}
.ai .t{display:flex;gap:6px;align-items:center;font-size:10.5px;color:var(--dim2)}
.tag{padding:1px 7px;border-radius:5px;border:1px solid var(--line3);color:var(--dim)}.tag.k{border-color:var(--blue);color:var(--blue)}
.ai p{margin:6px 0 8px;font-size:12.5px;font-weight:600;line-height:1.35}
.ai .bt{display:flex;gap:6px}.ai .bt .btn{padding:5px 10px;font-size:11px}
.chat{flex:1;display:flex;flex-direction:column}
.msgs{flex:1;display:flex;flex-direction:column;justify-content:flex-end;gap:8px;overflow:hidden;min-height:0}
.msg{max-width:88%;padding:8px 10px;border-radius:10px;font-size:12px;line-height:1.4;background:var(--navy2);border:1px solid var(--line)}
.msg.me{align-self:flex-end;background:rgba(0,207,255,.08);border-color:rgba(0,207,255,.35)}
.msg em{display:block;font-style:normal;font-size:10px;color:var(--dim2);margin-bottom:3px}
.compose{display:flex;gap:8px;margin-top:10px}.compose div{flex:1;border:1px solid var(--line3);border-radius:8px;padding:8px 10px;color:var(--dim2);background:var(--deep);font-size:12px}
.feed{list-style:none;display:flex;flex-direction:column;gap:5px}
.nx{display:flex;flex-direction:column;gap:5px}.nx .h{margin-bottom:4px}
.nr{display:grid;grid-template-columns:18px minmax(0,1fr) auto;gap:8px;align-items:center;background:var(--navy2);border:1px solid var(--line);border-radius:8px;padding:6px 8px}
.nr .n{color:var(--cyan);font-weight:700;text-align:center}.nr b{display:block;font-size:11.5px;white-space:nowrap;overflow:hidden;text-overflow:ellipsis}
.nr em{display:block;font-style:normal;font-size:10px;color:var(--dim2)}.nr .ic{color:var(--dim);font-size:12px;letter-spacing:.1em}
.feed li:nth-child(n+4){display:none}
.feed li{font-size:11.5px;padding:5px 8px;border-left:3px solid var(--dim2);background:var(--navy2);border-radius:0 6px 6px 0;display:flex;gap:6px}
.feed li b{color:var(--text)}.feed li em{margin-left:auto;font-style:normal;color:var(--dim2)}
.feed li.g{border-color:var(--green)}.feed li.r{border-color:var(--red)}.feed li.c{border-color:var(--cyan)}.feed li.x{border-color:var(--red);color:var(--red)}
body.dept .dept.pick{border-color:var(--cyan);background:rgba(0,207,255,.08)}
.sel,.drawer{display:none}body.dept .sel{display:inline}body.dept .drawer{display:flex}
.drawer{position:absolute;z-index:3;left:12px;top:48px;bottom:52px;width:min(560px,52%);flex-direction:column;gap:10px;
 background:var(--navy);border:1px solid var(--cyan);border-radius:12px;padding:14px;box-shadow:0 0 40px rgba(0,207,255,.18);overflow:hidden}
.dh{display:flex;align-items:center;gap:10px}.dh h2{font-family:'Archivo Black';font-weight:400;font-size:20px}
.dh .x{margin-left:auto;display:flex;gap:6px}
.chips{display:flex;gap:6px;flex-wrap:wrap}.chip{font-size:11px;padding:3px 9px;border-radius:99px;border:1px solid var(--line3);color:var(--dim)}
.kp{display:grid;grid-template-columns:repeat(5,1fr);gap:6px}
.kp div{background:var(--navy2);border:1px solid var(--line);border-radius:8px;padding:7px 9px}
.kp b{display:block;font-family:'Archivo Black';font-weight:400;font-size:20px;line-height:1.1}.kp span{font-size:10px;color:var(--dim2)}
.now{border:1px solid rgba(0,207,255,.45);border-radius:9px;padding:9px 11px;background:rgba(0,207,255,.06)}
.now .t1{font-size:10px;letter-spacing:.1em;color:var(--cyan);font-weight:700}.now p{font-weight:700;margin:4px 0}
.now .t2{font-size:11px;color:var(--dim2)}.now .t2 b{color:var(--red)}
.sec{font-size:10.5px;letter-spacing:.12em;color:var(--dim2);font-weight:700;display:flex;justify-content:space-between}
.sec a{color:var(--cyan);letter-spacing:0;font-weight:600}
.trow{display:grid;grid-template-columns:62px 1fr 44px;gap:8px;align-items:start;padding:7px 9px;background:var(--navy2);border:1px solid var(--line);border-radius:8px}
.trow .st{font-size:10px;font-weight:700;padding:2px 0;text-align:center;border-radius:5px;border:1px solid}
.st.dn{color:var(--green);border-color:var(--green)}.st.rt{color:var(--red);border-color:var(--red)}
.trow b{font-size:12px;display:block}.trow em{font-style:normal;font-size:11px;color:var(--dim2);display:block;margin-top:2px;white-space:nowrap;overflow:hidden;text-overflow:ellipsis}
.trow i{font-style:normal;font-size:10.5px;color:var(--dim2);text-align:right}
.mem{display:grid;grid-template-columns:52px 1fr;gap:8px;font-size:11.5px;padding:5px 0;border-bottom:1px solid var(--line)}
.mem span{font-size:9.5px;font-weight:700;color:var(--blue);border:1px solid var(--blue);border-radius:5px;text-align:center;height:17px;line-height:15px}
.cht{border:1px solid var(--cyan);border-radius:10px;padding:9px 10px;background:rgba(0,207,255,.05);display:flex;flex-direction:column;gap:7px}
.cht .ta{font-size:11.5px;line-height:1.45;color:var(--text);background:var(--deep);border:1px solid var(--line3);border-radius:7px;padding:8px 9px;max-height:92px;overflow:hidden}
.cht .cb{display:flex;align-items:center;gap:6px}.cht .cb .d{flex:1}.cht .cb .btn{padding:4px 10px;font-size:11px}
.charter{display:flex;justify-content:space-between;align-items:center;gap:10px;font-size:11.5px;color:var(--dim);padding:8px 10px;background:var(--navy2);border:1px solid var(--line);border-radius:8px}
.charter b{color:var(--text)}
@media (max-width:1600px){.main{grid-template-columns:250px minmax(0,1fr) 320px}.bars{min-width:210px}.fuel{gap:12px}
 .cobar{grid-template-columns:auto auto minmax(0,1fr)}.who h1{font-size:18px}.site nav{display:none}.mini{display:none}
 .feed li:nth-child(n+3){display:none}.chat{min-height:150px}.nr:nth-of-type(n+4){display:none}.ai p{margin:4px 0 6px}}
@media (max-width:700px){
 .site nav,.site .sp+span{display:none}
 .cobar{grid-template-columns:1fr;gap:10px;padding:10px 12px}.right{justify-content:space-between}
 .fuel{flex-wrap:wrap;justify-content:space-between;gap:10px}.fuel .k{width:100%}.fuel .vs{display:none}.bars{width:100%;min-width:0}
 .tabs{padding:0 8px}
 body{height:auto}
 .main{display:flex;flex-direction:column;padding:12px}
 .stage{order:-1;height:430px}.office{width:200%;max-width:none;margin:40px 0 0 -50%}.strip{flex-wrap:wrap}.legend{display:none}
 .zoom{display:none}.live{font-size:10px;white-space:nowrap}.seg a{padding:5px 8px;font-size:10px;white-space:nowrap}
 .left,.rightcol{display:contents}.mini{display:none}
}
</style></head><body>
<header class="site"><span class="logo">Event<i>Trader</i></span>
 <nav><span>Markets</span><span>Agents</span><span>Build it Better</span><b>Company</b><span>Usage</span></nav><span class="sp"></span>
 <span class="btn">expire76</span></header>

<section class="cobar">
 <div class="who"><div class="mark">CQ</div><h1>Cymetica QA</h1><span class="pill on">ACTIVE</span><span class="btn">Pause</span></div>
 <div class="fuel" title="Turns left = plan units left / your average units per turn (last 20 turns: 0.22). Updates after every turn.">
  <div class="k"><b>TURNS LEFT</b>on Pro · 0.22 u/turn</div>
  <div class="n low"><b>1</b><span>this session</span></div>
  <div class="n wk"><b>4</b><span>this week</span></div>
  <div class="vs"></div>
  <div class="n ex"><b>+21</b><span>extra usage</span></div>
  <div class="bars">
   <div class="bar"><label>SESSION</label><div class="track"><i style="width:78%;background:var(--red)"></i></div><em><b>0.78</b>/1.00 · 4h 28m</em></div>
   <div class="bar"><label>WEEK</label><div class="track"><i style="width:85%;background:var(--cyan)"></i></div><em><b>5.12</b>/6.00 · Sat 16:00</em></div>
   <div class="then">At 0: keeps running on <b>extra usage (on)</b></div>
  </div>
 </div>
 <div class="right"><span class="appr"><b>2</b> waiting for you</span><span class="btn cy">Upgrade</span></div>
</section>

<nav class="tabs"><a class="on">Office</a><a>Tasks<sup>6</sup></a><a>Approvals<sup class="r">2</sup></a><a>Memory</a><a>Audit</a>
 <span class="sp"></span><a>Investable</a><a>Legal entity</a><a>Token</a><a>Settings</a></nav>

<main class="main">
 <aside class="left">
  <section class="panel"><div class="h">DEPARTMENTS <b>5</b><span class="btn cy" style="padding:3px 8px;font-size:10.5px">+ Add</span></div>
   <div class="depts">__DEPTS__</div></section>
  <section class="mini"><div><b style="color:var(--green)">11</b><span>tasks done · 7d</span></div><div><b style="color:var(--red)">2</b><span>failed · 7d</span></div>
   <div><b>3.52<small style="font-size:11px;color:var(--dim2)">u</small></b><span>company · 7d</span></div><div><b style="color:var(--cyan)">0</b><span>approved · 7d</span></div></section>
 </aside>

 <section class="panel stage">
  <div class="top"><span class="live"><i></i>LIVE · 2 WORKING</span>
   <div class="seg"><a class="on">2D OFFICE</a><a>3D NETWORK</a></div>
   <div class="zoom"><a>+</a><a>−</a><a>⤢</a></div></div>
  __OFFICE__
  <div class="drawer">
   <div class="dh"><i class="dot" style="background:var(--cyan);box-shadow:0 0 8px var(--cyan)"></i><h2>Testing</h2><span class="pill on" style="color:var(--cyan);border-color:var(--cyan);background:rgba(0,207,255,.08)">WORKING</span>
    <span class="x"><span class="btn">Edit</span><span class="btn">×</span></span></div>
   <div class="chips"><span class="chip">QA tester</span><span class="chip">Auditor</span><span class="chip" style="color:var(--red);border-color:var(--red)">1 waiting for you</span></div>
   <div class="cht"><div class="sec">CHARTER · EVERY TASK STARTS HERE <a>1,449 / 2,000 · saved Tue 19:14</a></div>
    <div class="ta">Goal: real, reproducible defects in what Cymetica's platform shows or documents TODAY, drafted as bug-bounty reports.<br>- Test only what is visible and documented now (llms.txt, /openapi-public.json, the live pages).<br>- A finding is one defect with the exact request or page, what their docs say, what happens instead, and the evidence…</div>
    <div class="cb"><span class="d" style="font-size:10.5px">next task starts from the saved text</span><span class="btn">Discard</span><span class="btn gr">Save charter</span></div></div>
   <div class="kp"><div><b style="color:var(--cyan)">1</b><span>open</span></div><div><b style="color:var(--green)">2</b><span>done</span></div>
    <div><b style="color:var(--red)">1</b><span>failed</span></div><div><b>0.66<small style="font-size:11px;color:var(--dim2)">u</small></b><span>7 days</span></div><div><b>6</b><span>memory</span></div></div>
   <div class="now"><div class="t1">NOW · ATTEMPT 2</div><p>Find doc-vs-behavior mismatches on public pages</p>
    <div class="t2">QA tester · started 19:25 · last try: <b>no answer</b></div></div>
   <div class="sec">TASKS <a>All 3 →</a></div>
   <div class="trow"><span class="st rt">RETRY</span><div><b>Find doc-vs-behavior mismatches</b><em>no answer · attempt 2 of 3</em></div><i>19:27</i></div>
   <div class="trow"><span class="st dn">DONE</span><div><b>Inventory testable surface from llms.txt</b><em>Public no-auth GETs for read-only tests: /gem-screener/picks, /prop/config…</em></div><i>19:20</i></div>
   <div class="trow"><span class="st dn">DONE</span><div><b>Read bug bounty scope and rules</b><em>In scope: contracts, web UI, REST API, data accuracy, mobile, docs…</em></div><i>19:18</i></div>
   <div class="sec">MEMORY <a>All 6 →</a></div>
   <div class="mem"><span>KNOWS</span><div>Bounty pays a flat 1,000 ET10 per verified, non-duplicate bug.</div></div>
   <div class="mem"><span>KNOWS</span><div>In scope: contracts, web UI, REST API, data accuracy, mobile, docs.</div></div>
  </div>
  <div class="strip"><span class="lab">TURNS TODAY <b>16</b> / 40</span><div class="cells">__CELLS__</div>
   <span class="legend"><span><i style="background:var(--cyan)"></i>running</span><span><i style="background:var(--green)"></i>done</span><span><i style="background:var(--red)"></i>failed</span><span><i style="background:var(--blue)"></i>queued</span></span></div>
 </section>

 <aside class="rightcol">
  <section class="panel ap"><div class="h">WAITING FOR YOU <b style="color:var(--red)">2</b></div>
   <div class="ai"><div class="t"><span class="tag">Testing</span><span class="tag k">bug report</span>2 min</div>
    <p>/api/v1/company routes missing from /openapi-public.json</p>
    <div class="bt"><span class="btn gr">Approve</span><span class="btn rd">Reject</span><span class="btn">Read</span></div></div>
   <div class="ai" style="margin-bottom:0"><div class="t"><span class="tag">Development</span><span class="tag k">BB request</span>5 min</div>
    <p>Gem Screener: parent-app logos</p>
    <div class="bt"><span class="btn gr">Approve</span><span class="btn rd">Reject</span><span class="btn">Read</span></div></div></section>
  <section class="panel nx"><div class="h">NEXT UP · THE MANAGER'S PLAN <b style="color:var(--cyan)">3</b></div>
   <div class="nr"><span class="n">1</span><div><b>Testing: Chart Analyzer score vs its study</b><em>you asked for it at 19:30 · ~2 turns</em></div><span class="ic">↑↓ ✕</span></div>
   <div class="nr"><span class="n">2</span><div><b>Lab: FOMO ≥70, 24h exit, verdict</b><em>its window closed · ~1 turn</em></div><span class="ic">↑↓ ✕</span></div>
   <div class="nr"><span class="n">3</span><div><b>Development: Gem Screener logos request</b><em>waits on your approval first · ~1 turn</em></div><span class="ic">↑↓ ✕</span></div></section>
  <section class="panel chat"><div class="h">MANAGER</div>
   <div class="msgs">
    <div class="msg"><em>Manager · 19:16</em>Starting with scope and surface mapping; nothing is submitted until you approve.</div>
    <div class="msg me"><em>You · 19:30</em>Chart Analyzer and Gem Screener first.</div>
    <div class="msg"><em>Manager · 19:31</em>Queued 2 tasks for Testing, 1 for the Lab.</div>
   </div>
   <div class="compose"><div>Message the Manager…</div><span class="btn gr">Send</span></div></section>
  <section class="panel"><div class="h">LIVE FEED</div><ul class="feed">__FEED__</ul></section>
 </aside>
</main>
<script>if (location.search.indexOf('dept') >= 0) document.body.classList.add('dept');</script>
</body></html>
"""


def main():
    page = (PAGE.replace("__DEPTS__", dept_rows()).replace("__OFFICE__", office_svg())
            .replace("__CELLS__", cells()).replace("__FEED__", feed()))
    (HERE / "mockup.html").write_text(page, encoding="utf-8")
    print("mockup.html", len(page))


if __name__ == "__main__":
    main()
