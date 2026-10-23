"""A picture of where two screenshots differ: the second one dimmed, every pixel off by more than a level in red
(brighter the more), and a crop of the worst region side by side.  python diffimg.py <a.png> <b.png> <out.png>"""
import sys
from PIL import Image, ImageChops

a, b, out = Image.open(sys.argv[1]).convert("RGB"), Image.open(sys.argv[2]).convert("RGB"), sys.argv[3]
d = ImageChops.difference(a, b).convert("L")
mask = d.point(lambda v: 255 if v > 8 else (110 if v > 0 else 0))
base = b.point(lambda v: v // 3)
red = Image.new("RGB", a.size, (255, 40, 40))
img = Image.composite(red, base, mask)
img.save(out)
bb = d.point(lambda v: 255 if v > 8 else 0).getbbox()
print("over-8 bbox", bb)
if bb:
    x0, y0, x1, y1 = bb
    cx, cy = (x0 + x1) // 2, (y0 + y1) // 2
    box = (max(0, cx - 200), max(0, cy - 150), min(a.width, cx + 200), min(a.height, cy + 150))
    pair = Image.new("RGB", ((box[2] - box[0]) * 2 + 10, box[3] - box[1]), (0, 0, 0))
    pair.paste(a.crop(box), (0, 0)); pair.paste(b.crop(box), (box[2] - box[0] + 10, 0))
    pair = pair.resize((pair.width * 2, pair.height * 2), Image.NEAREST)
    pair.save(out.replace(".png", "-crop.png"))
