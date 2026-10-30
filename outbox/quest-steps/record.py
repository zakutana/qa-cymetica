"""The clips for the Quest steps page, into clips/ (not in git: ~30 MB that record.py makes again), and a poster of
each into pics/ (kept: what the page shows before a clip plays, or if it is missing).

Fifth take (the operator, 2026-10-30): "v kazdem kroku musi byt top animace".

  clip            what moves                                              from
  station.webm    the company's station (Rift Hold, gold) turning         LIVE builder, its first step
  office.webm     the HQ coming in once, then its astronauts at work      LIVE builder, its Start, 1920 x 1080 laid out
  workshop.webm   the arms take the idea and build the product, 10 s      scenes/tools.html, frame by frame: a true loop
  farmer.webm     the Airdrop Farmer turning and blinking, the gem turning our Universe mock, a still camera (capture.py)
  universe.webm   the whole Universe: every company on its orbit          LIVE cymetica.com/company/app#universe

    python outbox/quest-steps/record.py                  # every one
    python outbox/quest-steps/record.py office farmer    # some

Real-time scenes are recorded where they are drawn: the canvas's own stream (captureStream) through MediaRecorder,
then remuxed by Playwright's own ffmpeg so the file knows its length (a MediaRecorder WebM does not, and a page
cannot cross-fade a clip whose length is Infinity). The workshop is drawn frame by frame and encoded by that ffmpeg.
Chrome with a real GPU, as capture.py. Live pages are read anonymously (GET, no cookies, no key); the builder is typed
into (a name) and never submitted.
"""
import base64
import glob
import io
import os
import subprocess
import sys
import tempfile
import time
from pathlib import Path

from PIL import Image
from playwright.sync_api import sync_playwright

sys.path.insert(0, str(Path(__file__).resolve().parent))
import capture  # noqa: E402  (its server, its Universe and its farmer's composition)

HERE = Path(__file__).resolve().parent
CLIPS = HERE / 'clips'
W, H = 1440, 810
FFMPEG = (glob.glob(os.path.expandvars(r'%LOCALAPPDATA%\ms-playwright\ffmpeg-*\ffmpeg-win64.exe'))
          or glob.glob(os.path.expanduser('~/.cache/ms-playwright/ffmpeg-*/ffmpeg-linux')) or [None])[0]

# the canvas's own stream for `ms` milliseconds, as a WebM, back to Python in base64
RECORD = """async ([sel, ms, bps]) => {
  const c = document.querySelector(sel), s = c.captureStream(30);
  // VP8: Playwright's ffmpeg has no vp9_superframe filter, so a VP9 recording could not be remuxed to know its length
  const mime = 'video/webm;codecs=vp8';
  const rec = new MediaRecorder(s, { mimeType: mime, videoBitsPerSecond: bps }), parts = [];
  rec.ondataavailable = (e) => { if (e.data.size) parts.push(e.data); };
  const done = new Promise((r) => { rec.onstop = r; });
  rec.start(1000); await new Promise((r) => setTimeout(r, ms)); rec.stop(); await done;
  const buf = new Uint8Array(await new Blob(parts, { type: mime }).arrayBuffer());
  let bin = ''; for (let i = 0; i < buf.length; i += 0x8000) bin += String.fromCharCode.apply(null, buf.subarray(i, i + 0x8000));
  return { mime, w: c.width, h: c.height, b64: btoa(bin) }; }"""


def ffmpeg(*args, stdin=None):
    assert FFMPEG, "Playwright's ffmpeg is missing: python -m playwright install ffmpeg"
    subprocess.run([FFMPEG, '-hide_banner', '-loglevel', 'error', '-y', *args], input=stdin, check=True)


def record(page, sel, seconds, name, bps=8_000_000):
    """the canvas `sel` for `seconds`, kept as clips/<name>.webm (remuxed, so it knows its length), and its first
    frame as pics/<name>.webp"""
    CLIPS.mkdir(exist_ok=True)
    r = page.evaluate(RECORD, [sel, int(seconds * 1000), bps])
    fd, tmp = tempfile.mkstemp(suffix='.webm')
    os.close(fd)
    raw = Path(tmp)
    raw.write_bytes(base64.b64decode(r['b64']))
    out = CLIPS / f'{name}.webm'
    ffmpeg('-i', str(raw), '-c', 'copy', str(out))
    raw.unlink()
    print(f'{out.name} {r["w"]}x{r["h"]} {r["mime"]} {out.stat().st_size // 1024} KB')
    return out


def poster(page, sel, name):
    """what the canvas shows now, as the clip's poster"""
    data = page.evaluate("(sel) => document.querySelector(sel).toDataURL('image/jpeg', 0.92)", sel)
    img = Image.open(io.BytesIO(base64.b64decode(data.split(',', 1)[1]))).convert('RGB')
    capture.save(img, f'{name}.webp', quality=82)


def office(b, seconds=16):
    """the live builder's Start in 3D at 1920 x 1080 (its card's place), drawn at 1440 x 810, its astronauts walking"""
    page = b.new_page(viewport={'width': 1920, 'height': 1080}, device_scale_factor=0.75)
    page.goto('https://cymetica.com/company/app/builder', wait_until='domcontentloaded', timeout=60000)
    time.sleep(12)
    page.fill('#f-name', 'Moonshot Labs')          # typed, never submitted
    page.click('#b-next')
    time.sleep(14)
    assert page.evaluate("() => document.getElementById('stage').classList.contains('is3d')"), 'the builder drew its flat office, not 3D'
    sel = '#office3d canvas'
    # the office's canvas runs wider than the stage (it is shifted right of the card): the page crops it to the stage,
    # by these numbers (quest.css #s1 .crop)
    print('office: canvas in the stage:', page.evaluate("""() => { const s = document.getElementById('stage').getBoundingClientRect(),
      c = document.querySelector('#office3d canvas').getBoundingClientRect(), k = document.querySelector('section.bz-card').getBoundingClientRect();
      const f = (v, d) => +(v / d * 100).toFixed(2);
      return { left: f(c.left - s.left, s.width), top: f(c.top - s.top, s.height), width: f(c.width, s.width), height: f(c.height, s.height),
               card: [f(k.left - s.left, s.width), f(k.top - s.top, s.height), f(k.width, s.width)] }; }"""))
    poster(page, sel, 'office')
    # in once, only as far as the whole company still shows ("staci jedna animace ze se to priblizi jen na uroven ze jde
    # videt cela firma"; 0.85 of the way: at 0.8 its rooms touch the stage's edges, which the page fades), then still,
    # its astronauts at work; the page plays the way in once and repeats only the still part (data-loop-from)
    page.evaluate("""() => { const o = CO.builder.office;
      const p0 = o.camera.position.clone(), t0 = o.controls.target.clone();
      o.tween(t0.clone().add(p0.clone().sub(t0).multiplyScalar(0.85)), t0, 3500); }""")
    record(page, sel, seconds, 'office')
    page.close()


def station(b, seconds=6):
    """step 1's way in ("aby to zacinalo takto ... a ten zoom by sel dovnitr a pak by zobrazil ty headquarters"): the
    LIVE builder's first step, the company's station turning in its space, before the name is typed; the page zooms
    into it and on into the office clip"""
    page = b.new_page(viewport={'width': 1920, 'height': 1080}, device_scale_factor=0.75)
    page.goto('https://cymetica.com/company/app/builder', wait_until='domcontentloaded', timeout=60000)
    page.wait_for_function("() => { const e = document.getElementById('b-prev'); return e && e.classList.contains('has3d') && e.querySelector('canvas'); }", timeout=90000)
    # the look he showed (2026-10-30): Rift Hold, the split asteroid with the bridge of light; the builder opens on a
    # look of its own, so its arrow is pressed until that one stands
    for _ in range(20):
        if page.evaluate("() => CO.builder.o.skin") == 'rift':
            break
        page.click('#lk-next')
        time.sleep(0.4)
    # and its warm light, as in his picture: the builder's own gold accent, if it has one
    acc = page.evaluate("() => (CO.ACCENTS || []).map(a => a.key).find(k => /gold|amber|yellow|sun/.test(k)) || null")
    if acc:
        page.click(f'#lk-acc .acc[data-k="{acc}"]')
    print('station: look', page.evaluate("() => CO.builder.o.skin"), 'accent', acc)
    time.sleep(5)
    sel = '#b-prev canvas'
    print('station: canvas', page.evaluate("(s) => { const c = document.querySelector(s); return [c.width, c.height]; }", sel))
    poster(page, sel, 'station')
    record(page, sel, seconds, 'station')
    page.close()


def farmer(b, seconds=12):
    """our Universe mock, capture.py's composition (the farmer near, the gem behind it), the camera still while the
    farmer turns and blinks and the gem turns; where the two names stand, for the page's own labels over the clip"""
    page = capture.universe(b, viewport={'width': 1600, 'height': 1000}, dsf=1)
    page.evaluate(capture.FARMER_SHOT)
    time.sleep(3)
    sel = '#uv3d canvas'
    print('farmer: names over the canvas (left, top %):', page.evaluate("""() => { const c = document.querySelector('#uv3d canvas').getBoundingClientRect();
      return ['ad-farmer', 'ad-gem'].map(id => { const e = CO.uv.items.find(x => x.c.id === id).el.getBoundingClientRect();
        return [id, +((e.left + e.width / 2 - c.left) / c.width * 100).toFixed(1), +((e.top - c.top) / c.height * 100).toFixed(1)]; }); }"""))
    poster(page, sel, 'farmer')
    record(page, sel, seconds, 'farmer')
    page.close()


def universe(b, seconds=20):
    """the LIVE Universe, read anonymously: every company on its orbit round Cymetica's sun, the camera where the page
    puts it, after its flight in"""
    page = b.new_page(viewport={'width': 1920, 'height': 1080}, device_scale_factor=0.75)
    page.goto('https://cymetica.com/company/app#universe', wait_until='domcontentloaded', timeout=60000)
    page.wait_for_function("() => window.CO && CO.uv && CO.uv.camera && document.getElementById('uvstage').classList.contains('is3d')", timeout=90000)
    time.sleep(14)
    print('universe: companies on the map:', page.evaluate("() => CO.uv.items.filter(it => !it.kind).length"))
    sel = '#uv3d canvas'
    poster(page, sel, 'universe')
    record(page, sel, seconds, 'universe')
    page.close()


def workshop(b, fps=30, at=None):
    """scenes/tools.html drawn frame by frame through its PERIOD (render(t) is a function of t alone, so the last frame
    leads into the first), encoded to VP8 by Playwright's ffmpeg; `at` (seconds) only pictures those moments"""
    base = capture.serve(HERE)
    page = b.new_page(viewport={'width': W, 'height': H})
    page.goto(base + f'scenes/tools.html?w={W}&h={H}&frames', wait_until='load', timeout=60000)
    page.wait_for_function('window.READY === true', timeout=60000)
    grab = "(t) => { window.render(t); return document.querySelector('canvas').toDataURL('image/jpeg', 0.93); }"
    if at:
        for t in at:
            Image.open(io.BytesIO(base64.b64decode(page.evaluate(grab, t).split(',', 1)[1]))).save(HERE / f'workshop-{t}.png')
        page.close()
        return
    period = page.evaluate('window.PERIOD')
    frames = [base64.b64decode(page.evaluate(grab, i / fps).split(',', 1)[1]) for i in range(int(period * fps))]
    CLIPS.mkdir(exist_ok=True)
    out = CLIPS / 'workshop.webm'
    # Playwright's ffmpeg has no pipe protocol: the frames go through a file of JPEGs one after another
    fd, tmp = tempfile.mkstemp(suffix='.mjpeg')
    os.close(fd)
    Path(tmp).write_bytes(b''.join(frames))
    ffmpeg('-f', 'image2pipe', '-c:v', 'mjpeg', '-framerate', str(fps), '-i', tmp, '-c:v', 'libvpx', '-b:v', '8M', '-crf', '8',
           '-qmin', '2', '-qmax', '30', '-auto-alt-ref', '0', '-g', str(fps), '-pix_fmt', 'yuv420p', str(out))
    Path(tmp).unlink()
    capture.save(Image.open(io.BytesIO(base64.b64decode(page.evaluate(grab, 7.4).split(',', 1)[1]))).convert('RGB'), 'workshop.webp', quality=82)
    print(f'{out.name} {W}x{H} {len(frames)} frames {out.stat().st_size // 1024} KB')
    page.close()


SHOTS = {'station': station, 'office': office, 'farmer': farmer, 'universe': universe, 'workshop': workshop}


def main(names):
    with sync_playwright() as p:
        b = p.chromium.launch(channel='chrome', args=capture.GPU)
        for name in names:
            SHOTS[name](b)
        b.close()


if __name__ == '__main__':
    main(sys.argv[1:] or list(SHOTS))
