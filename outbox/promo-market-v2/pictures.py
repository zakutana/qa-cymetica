"""The pictures for the Build it Better request (build-it-better/pictures/), from render.py's shots at 1920 x 1080.
WebP, 1600 px wide, so the request's folder stays small; "picture N" in the request means N-*.webp."""
from pathlib import Path

from PIL import Image

HERE = Path(__file__).resolve().parent
SHOTS = HERE / "shots"
OUT = HERE / "build-it-better" / "pictures"
PICTURES = [
    ("1-market", "sample-market"), ("2-market-empty", "live-market"), ("3-brief", "sample-brief-drawer"),
    ("4-my-products", "sample-me-products"), ("5-post-a-brief", "sample-new-chart"), ("6-brief-page", "sample-mybrief-101"),
    ("7-today", "live-me-today"), ("8-queues", "live-me-queues"), ("9-pages-links", "live-me-links"), ("10-loader", "loader"),
    ("11-briefs-i-took", "sample-me-taken"), ("12-radar-apps", "live-me-radar"), ("13-kits", "live-me-kits"),
    ("14-journalists", "live-me-journalists"), ("15-rewards", "live-me-rewards"), ("16-agent-key", "live-me-key"),
    ("17-start-a-company", "live-me-company"),
]


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    total = 0
    for name, shot in PICTURES:
        im = Image.open(SHOTS / f"{shot}.png").convert("RGB")
        w, h = im.size
        im = im.resize((1600, round(h * 1600 / w)), Image.LANCZOS)
        p = OUT / f"{name}.webp"
        im.save(p, "WEBP", quality=72, method=6)
        total += p.stat().st_size
        print(f"{name:20} {im.size[0]}x{im.size[1]} {p.stat().st_size // 1024} KB")
    print("total", total // 1024, "KB")


if __name__ == "__main__":
    main()
