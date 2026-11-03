"""AI video (green screen) -> unit sprite frames for hd_pack.py (2026-11-03, user: generate the per-direction move
videos with Doubao from prompts, then turn them into frame animations).  Spec + prompts: art3d/VIDEO_SPRITES.md.

One video per direction (unit running in place, fixed high-angle camera, green background), made from the direction's
reference picture (art3d/units/<code>/video/ref/<code>_dN.png, the unit's own render or sprite at REF_SCALE x the
render canvas, pivot at REF_PIVOT).  For each video:
  1. decode (ffmpeg), key out the green (soft alpha + despill);
  2. scale + position: the first frame's figure is matched to the reference picture's figure (height, bottom centre),
     frame 0 (= the reference, image-to-video) gives the video -> render-canvas transform; camera drift over the
     clip is removed (a linear trend of the figure centre), the run's own bob is kept;
  3. loop: the period P and start s with the most similar silhouettes s / s+P (P between --min-sec and --max-sec);
  4. P frames resampled to --frames (12) evenly, written as <out>/<act>/body/dD_fFF.png on the render canvas
     (716 x 716, pivot (356, 436) = SS 4 x the xpf canvas), and a simple projected shadow <out>/<act>/shadow/.
Then: python tools/hd_pack.py OUT --from-render <out> <code>
usage: python tools/video_to_frames.py OUT CODE ACT VIDEO_DIR [--frames 12]   (VIDEO_DIR/<code>_dN.mp4, any of 0..7)"""
import sys, os, subprocess, json, argparse, math, glob
import numpy as np
from PIL import Image

CANVAS = 716; PIV = (356, 436)            # render canvas (SS 4 x 179) and pivot, as art3d/units/g039/render
REF_SCALE = 2.6; REF_PIVOT = (512, 700)   # reference pictures: render canvas x 2.6 on 1024 x 1024 green


def decode(path):
    info = json.loads(subprocess.check_output(['ffprobe', '-v', 'error', '-select_streams', 'v:0', '-show_entries',
                                               'stream=width,height,avg_frame_rate', '-of', 'json', path]))['streams'][0]
    w, h = info['width'], info['height']; n, d = info['avg_frame_rate'].split('/'); fps = float(n) / float(d or 1)
    raw = subprocess.check_output(['ffmpeg', '-v', 'error', '-i', path, '-f', 'rawvideo', '-pix_fmt', 'rgb24', '-'])
    return np.frombuffer(raw, np.uint8).reshape(-1, h, w, 3), fps


def key(rgb):
    """green screen -> RGBA float.  alpha from how much green beats red / blue; green spill removed"""
    f = rgb.astype(np.float32) / 255.0
    r, g, b = f[..., 0], f[..., 1], f[..., 2]
    m = g - np.maximum(r, b)
    a = 1.0 - np.clip((m - 0.08) / 0.22, 0, 1)
    g2 = np.minimum(g, np.maximum(r, b) * 1.05)
    return np.dstack([r, g2, b, a])


def figure(a, thr=0.5):
    ys, xs = np.nonzero(a > thr)
    if len(xs) < 20: return None
    return dict(x0=xs.min(), x1=xs.max(), y0=ys.min(), y1=ys.max(), cx=xs.mean(), cy=ys.mean())


def ref_figure(path):
    rgba = key(np.asarray(Image.open(path).convert('RGB')))
    return figure(rgba[..., 3])


def find_loop(sil, fps, min_sec, max_sec):
    n = len(sil); best = None
    pmin = max(4, int(min_sec * fps)); pmax = min(n - 1, int(max_sec * fps))
    for P in range(pmin, pmax + 1):
        for s in range(0, n - P):
            e = float(np.mean(np.abs(sil[s] - sil[s + P])))
            e += 0.0005 * P / max(pmax, 1)              # equal matches: the shorter period (one stride)
            if best is None or e < best[0]: best = (e, s, P)
    return best


def convert(video, ref, nframes, min_sec, max_sec, log):
    rgb, fps = decode(video)
    frames = [key(f) for f in rgb]
    H, W = frames[0].shape[:2]
    # silhouettes for the loop search: alpha, downscaled, centred on the figure (drift does not break a match)
    sil = []
    for f in frames:
        im = Image.fromarray((f[..., 3] * 255).astype(np.uint8)).resize((W // 8, H // 8), Image.BOX)
        a8 = np.asarray(im, np.float32) / 255.0; g = figure(a8, 0.3)
        if g: a8 = np.roll(a8, (int(round(a8.shape[0] / 2 - g['cy'])), int(round(a8.shape[1] / 2 - g['cx']))), (0, 1))
        sil.append(a8)
    err, s, P = find_loop(sil, fps, min_sec, max_sec)
    loop = frames[s:s + P]
    figs = [figure(f[..., 3]) for f in frames]
    if any(g is None for g in figs[s:s + P]): raise SystemExit(f'{video}: figure lost in the loop')
    # transform video px -> render canvas px from frame 0, which is the reference picture (image-to-video)
    rf = ref_figure(ref); g0 = figs[0]
    k = ((rf['y1'] - rf['y0']) / REF_SCALE) / float(g0['y1'] - g0['y0'])
    ref_off = ((REF_PIVOT[0] - (rf['x0'] + rf['x1']) / 2) / REF_SCALE, (REF_PIVOT[1] - rf['y1']) / REF_SCALE)
    piv0 = ((g0['x0'] + g0['x1']) / 2 + ref_off[0] / k, g0['y1'] + ref_off[1] / k)
    # camera drift: linear trend of the figure centre over the whole clip (an in-place run keeps its place)
    ok = [i for i, g in enumerate(figs) if g]
    t = np.array(ok, np.float32)
    dx = np.polyfit(t, [figs[i]['cx'] for i in ok], 1)[0] if len(ok) > 2 else 0.0
    dy = np.polyfit(t, [figs[i]['cy'] for i in ok], 1)[0] if len(ok) > 2 else 0.0
    out = []
    for i in range(nframes):
        j = i * P / nframes; j0 = int(j); w = j - j0
        f = loop[j0] if w < 1e-3 or j0 + 1 >= P else (loop[j0] * (1 - w) + loop[j0 + 1] * w)
        px, py = piv0[0] + dx * (s + j), piv0[1] + dy * (s + j)
        # premultiply, scale about the pivot to the canvas
        pm = f.copy(); pm[..., :3] *= pm[..., 3:4]
        im = Image.fromarray((pm * 255 + 0.5).clip(0, 255).astype(np.uint8), 'RGBA')
        im = im.transform((CANVAS, CANVAS), Image.AFFINE, (1 / k, 0, px - PIV[0] / k, 0, 1 / k, py - PIV[1] / k),
                          resample=Image.BICUBIC)
        a = np.asarray(im, np.float32) / 255.0
        un = a.copy(); al = np.maximum(a[..., 3:4], 1e-6); un[..., :3] = np.where(a[..., 3:4] > 0, a[..., :3] / al, 0)
        out.append(Image.fromarray((un * 255 + 0.5).clip(0, 255).astype(np.uint8), 'RGBA'))
    log(f'{os.path.basename(video)}: {len(frames)} frames @ {fps:.1f} fps, loop {P} frames from {s} '
        f'({P / fps:.2f} s, diff {err:.3f}), scale {k:.3f}, drift {dx:+.2f},{dy:+.2f} px/frame')
    return out


def shadow(body):
    """a flat projected shadow from the body silhouette: squashed to the ground, sheared screen-right / away"""
    a = np.asarray(body, np.float32)[..., 3] / 255.0
    im = Image.fromarray((a * 255).astype(np.uint8), 'L')
    # ground projection about the pivot row: y' = piv + (y - piv) * 0.35 ; x' = x + (piv - y) * 0.45
    im = im.transform((CANVAS, CANVAS), Image.AFFINE, (1, -0.45 / 0.35, 0.45 / 0.35 * PIV[1], 0, 1 / 0.35,
                                                       PIV[1] - PIV[1] / 0.35), resample=Image.BILINEAR)
    m = (np.asarray(im, np.float32) / 255.0 > 0.4).astype(np.uint8) * 255
    out = np.zeros((CANVAS, CANVAS, 4), np.uint8); out[..., 3] = m
    return Image.fromarray(out, 'RGBA')


if __name__ == '__main__':
    ap = argparse.ArgumentParser()
    ap.add_argument('out'); ap.add_argument('code'); ap.add_argument('act'); ap.add_argument('videos')
    ap.add_argument('--frames', type=int, default=12); ap.add_argument('--ref')
    ap.add_argument('--min-sec', type=float, default=0.5); ap.add_argument('--max-sec', type=float, default=1.6)
    ap.add_argument('--no-shadow', action='store_true')
    a = ap.parse_args()
    refdir = a.ref or os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'art3d', 'units', a.code, 'video', 'ref')
    done = 0
    for d in range(8):
        vids = sorted(glob.glob(os.path.join(a.videos, f'{a.code}_d{d}.*')))
        if not vids: continue
        fr = convert(vids[0], os.path.join(refdir, f'{a.code}_d{d}.png'), a.frames, a.min_sec, a.max_sec, print)
        for ps in ('body', 'shadow'):
            os.makedirs(os.path.join(a.out, a.act, ps), exist_ok=True)
        for i, im in enumerate(fr):
            im.save(os.path.join(a.out, a.act, 'body', 'd%d_f%02d.png' % (d, i)))
            if not a.no_shadow: shadow(im).save(os.path.join(a.out, a.act, 'shadow', 'd%d_f%02d.png' % (d, i)))
        done += 1
    print(f'{done} direction(s) -> {a.out}/{a.act}/  (next: python tools/hd_pack.py OUT --from-render {a.out} {a.code})')
