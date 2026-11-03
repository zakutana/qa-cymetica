"""Slim a Quest clip without losing what the eye sees. Same size, same frame times, same alpha; only the bits per frame go down.
  python slim.py test <name> <crf> [<crf> ...]      encode into slim/<name>-crf<N>.webm and print size, bitrate, luma SSIM / PSNR against the original (sampled at 5 fps)
Originals are read from clips/orig/ when it exists, else clips/."""
import re
import subprocess
import sys
from pathlib import Path

import numpy as np

QS = Path(r'C:\Users\adamz\Documents\Projects\cymetica-qa-agent\qa-cymetica\outbox\quest-steps')
CLIPS = QS / 'clips'
ORIG = CLIPS / 'orig'
OUT = Path(__file__).resolve().parent / 'slim'
OUT.mkdir(exist_ok=True)
FF = r'C:\Users\adamz\AppData\Roaming\Python\Python313\site-packages\imageio_ffmpeg\binaries\ffmpeg-win-x86_64-v9.0.2.exe'
ALPHA = {'door-room', 'door-universe', 'farmer'}
GOP = {'workshop': 30}


def run(*a):
    r = subprocess.run([FF, '-hide_banner', '-y', *map(str, a)], capture_output=True, text=True)
    if r.returncode:
        raise SystemExit(r.stderr[-800:])
    return r.stderr


def probe(f):
    s = subprocess.run([FF, '-hide_banner', '-i', str(f)], capture_output=True, text=True).stderr
    m = re.search(r'(\d{3,5})x(\d{3,5})', s.split('Video:')[1])
    return int(m.group(1)), int(m.group(2))


def src(name):
    return (ORIG / f'{name}.webm') if (ORIG / f'{name}.webm').exists() else (CLIPS / f'{name}.webm')


def encode(name, spec, out):
    """spec is 'vp9:34' or 'x264:21' (codec:crf)"""
    codec, crf = spec.split(':')
    alpha = name in ALPHA
    g = GOP.get(name, 60)
    dec = ['-c:v', 'libvpx'] if alpha else []   # the native VP8 decoder drops the alpha plane
    if codec == 'vp9':
        args = [*dec, '-i', src(name), '-c:v', 'libvpx-vp9', '-crf', crf, '-b:v', 0, '-deadline', 'good', '-cpu-used', 2, '-row-mt', 1,
                '-g', g, '-pix_fmt', 'yuva420p' if alpha else 'yuv420p', '-auto-alt-ref', 0 if alpha else 1, '-fps_mode', 'passthrough', '-an', out]
    else:
        args = ['-i', src(name), '-c:v', 'libx264', '-crf', crf, '-preset', 'slow', '-g', g, '-pix_fmt', 'yuv420p', '-movflags', '+faststart',
                '-fps_mode', 'passthrough', '-an', out]
    run(*args)


def luma(f, w, h):
    import shutil
    from PIL import Image
    d = OUT / 'frames'
    shutil.rmtree(d, ignore_errors=True)
    d.mkdir()
    run('-i', f, '-r', 5, '-pix_fmt', 'rgb24', d / '%04d.png')
    fr = [np.asarray(Image.open(p).convert('L'), dtype=np.float32) for p in sorted(d.glob('*.png'))]
    shutil.rmtree(d, ignore_errors=True)
    return np.stack(fr)


def box(x, k=7):
    c = np.cumsum(np.cumsum(np.pad(x.astype(np.float64), ((1, 0), (1, 0))), 0), 1)
    return (c[k:, k:] - c[:-k, k:] - c[k:, :-k] + c[:-k, :-k]) / (k * k)


def ssim(a, b):
    c1, c2 = 6.5025, 58.5225
    ma, mb = box(a), box(b)
    va, vb, cov = box(a * a) - ma * ma, box(b * b) - mb * mb, box(a * b) - ma * mb
    return float(((2 * ma * mb + c1) * (2 * cov + c2) / ((ma * ma + mb * mb + c1) * (va + vb + c2))).mean())


def compare(name, f):
    w, h = probe(src(name))
    A, B = luma(src(name), w, h), luma(f, w, h)
    n = min(len(A), len(B))
    s = [ssim(A[i], B[i]) for i in range(n)]
    mse = [float(((A[i] - B[i]) ** 2).mean()) for i in range(n)]
    psnr = [99.0 if m == 0 else 10 * np.log10(255 ** 2 / m) for m in mse]
    return np.mean(s), np.min(s), np.mean(psnr), np.min(psnr), n, len(A), len(B)


def dur_of(name):
    s = subprocess.run([FF, '-hide_banner', '-i', str(src(name))], capture_output=True, text=True).stderr
    h, m, sec = re.search(r'Duration: (\d+):(\d+):([\d.]+)', s).groups()
    return int(h) * 3600 + int(m) * 60 + float(sec)


def final(names):
    """each clip: VP9 (and, without alpha, H.264) at the first crf of a ladder whose luma SSIM stays >= 0.985 mean and >= 0.97 worst frame"""
    fin = OUT / 'final'
    fin.mkdir(exist_ok=True)
    for name in names:
        d = dur_of(name)
        for codec, ladder, ext in (('vp9', (33, 30, 27, 24), 'webm'), ('x264', (22, 20, 18, 16), 'mp4')):
            if codec == 'x264' and name in ALPHA:
                continue
            for crf in ladder:
                out = fin / f'{name}.{ext}'
                encode(name, f'{codec}:{crf}', out)
                m = compare(name, out)
                ok = m[0] >= 0.985 and m[1] >= 0.97
                print(f'{name:16} {codec:5} crf {crf}: {out.stat().st_size / 1048576:5.1f} MB (was {src(name).stat().st_size / 1048576:.1f})  {out.stat().st_size * 8 / d / 1e6:4.1f} Mbps  '
                      f'ssim {m[0]:.4f}/{m[1]:.4f}  psnr {m[2]:.1f}/{m[3]:.1f}  {"OK" if ok else "too lossy, lower crf"}', flush=True)
                if ok:
                    break


if __name__ == '__main__' and sys.argv[1] == 'all':
    final(sys.argv[2:] or sorted(p.stem for p in ORIG.glob('*.webm')))
    sys.exit()

if __name__ == '__main__':
    mode, name, crfs = sys.argv[1], sys.argv[2], sys.argv[3:]
    dur = float(re.search(r'Duration: (\d+):(\d+):([\d.]+)', subprocess.run([FF, '-hide_banner', '-i', str(src(name))], capture_output=True, text=True).stderr).groups()[2]) \
        + 60 * int(re.search(r'Duration: (\d+):(\d+)', subprocess.run([FF, '-hide_banner', '-i', str(src(name))], capture_output=True, text=True).stderr).group(2))
    print(f'{name}: original {src(name).stat().st_size / 1048576:.1f} MB, {dur:.1f} s')
    for crf in crfs:
        out = OUT / f"{name}-{crf.replace(':', '')}.{'mp4' if crf.startswith('x264') else 'webm'}"
        encode(name, crf, out)
        m = compare(name, out)
        print(f'  crf {crf:>2}: {out.stat().st_size / 1048576:5.1f} MB  {out.stat().st_size * 8 / dur / 1e6:4.1f} Mbps  ssim mean {m[0]:.4f} min {m[1]:.4f}  psnr mean {m[2]:.1f} min {m[3]:.1f} dB  (frames {m[5]} -> {m[6]})')
