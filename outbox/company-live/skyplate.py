"""The flyer's deep space as two backdrops for the mock's Universe and Headquarters (?sky=flyer).

The operator, 2026-11-01: the flyer's background is "fakt husto ... vyraznejsi tmavsi", how would it look live. The flyer was the
Universe frame screened over nebula.py's plate; here the same plate is a quad drawn first, behind everything in the 3D scene
(u3d.js flyerPlate), so rooms and rock cover it. 2560 x 1440 webp, the same every time for a seed.

    python outbox/company-live/skyplate.py
"""
import os
import sys

import numpy as np
from PIL import Image

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, '..', 'revenue-share-flyer'))
import nebula  # noqa: E402

nebula.W, nebula.H = 2560, 1440

for name, seed, strength in (('uv', 7, 0.5), ('hq', 11, 0.5)):
    rgb = nebula.make(seed=seed, strength=strength, stars=0.7)   # 30 % fewer stars (the operator, 2026-11-01)
    out = os.path.join(HERE, 'sky-flyer-%s.webp' % name)
    Image.fromarray(np.clip(rgb, 0, 255).astype(np.uint8), 'RGB').save(out, quality=86, method=6)
    print(out, os.path.getsize(out) // 1024, 'KB')
