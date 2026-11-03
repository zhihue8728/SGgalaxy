"""HD unit sprites -> .hds atlases for SGRender.dll (HD field units, plan: claude/HD_UNIT_OVERLAY_PLAN.md).
One .hds per game sprite file (g039mo.xpf -> hd/g039/g039mo.hds).  The DLL looks a recorded draw up by
    cell = (frame % frames_per_dir) * dirs + dir          (the game passes one animation counter for all layers)
and draws the cell with its pivot on the sprite's pivot, scaled from HD pixels to the screen.
Format (little endian):
  'HDS1' | u16 atlas_w, atlas_h | u16 dirs, frames_per_dir | u8 blend (0 normal, 1 add, 2 shadow) | u8 scale | u16 0
  | cells x (u16 x, y, w, h, i16 px, py)   (px, py = the pivot inside the cell, HD pixels; w = 0: empty cell)
  | atlas_w * atlas_h * BGRA, premultiplied alpha
Sources:
  --from-dat DAT[,DAT]  NAME.xpf ...    the game's own frames, scaled up (a stand-in to test positions and order)
  --from-render DIR CODE                Blender renders DIR/<action>/<pass>/dD_fFF.png (art3d/units/g039/render),
                                        supersampled frames whose canvas pivot is the xpf's pivot x the render scale
usage: python tools/hd_pack.py OUT_DIR --scale 2 --from-dat out/tc/tc2.dat,out/tc/tc.dat a008mo.xpf a008mob.xpf ..."""
import sys, os, struct, argparse, math
HERE = os.path.dirname(os.path.abspath(__file__)); REPO = os.path.dirname(HERE)
sys.path.insert(0, HERE); sys.path.insert(0, os.path.join(REPO, 'art3d'))
import numpy as np
from PIL import Image

TINT = False
GLOW_FX = True                         # --plain-glow: the rendered capsule as it is
BLEND = {'normal': 0, 'add': 1, 'shadow': 2}


def blend_of(xpf_type):
    t = xpf_type & 0xff
    if t & 0x10: return 'shadow'          # mask only (shadows, footprints)
    if t & 0x08: return 'add'             # glow layers (d, g039 b)
    return 'normal'


def premul(a):
    a = a.astype(np.float32); al = a[:, :, 3:4] / 255.0
    out = a.copy(); out[:, :, :3] *= al
    return out.clip(0, 255).astype(np.uint8)


def pack(cells, dirs, fpd, blend, scale, out):
    """cells: list (index = f * dirs + d) of (RGBA image | None, (pivot x, pivot y) in that image)"""
    crops = []
    for im, piv in cells:
        if im is None: crops.append(None); continue
        bb = im.getbbox()
        if not bb: crops.append(None); continue
        crops.append((im.crop(bb), (piv[0] - bb[0], piv[1] - bb[1])))
    W = 4096; x = y = rowh = 0; place = []
    for c in crops:                                      # shelf packing, 1 px gap
        if c is None: place.append(None); continue
        w, h = c[0].size
        if x + w > W: x = 0; y += rowh + 1; rowh = 0
        place.append((x, y)); x += w + 1; rowh = max(rowh, h)
    H = y + rowh
    aw = max(1, max((p[0] + c[0].size[0] for p, c in zip(place, crops) if p), default=1))
    at = Image.new('RGBA', (aw, max(1, H)), (0, 0, 0, 0))
    head = b'HDS1' + struct.pack('<HHHHBBH', aw, max(1, H), dirs, fpd, BLEND[blend], scale, 0)
    tab = b''
    for p, c in zip(place, crops):
        if p is None: tab += struct.pack('<HHHHhh', 0, 0, 0, 0, 0, 0); continue
        at.paste(c[0], p)
        tab += struct.pack('<HHHHhh', p[0], p[1], c[0].size[0], c[0].size[1], int(round(c[1][0])), int(round(c[1][1])))
    a = np.array(at)
    if TINT and blend == 'normal':                       # --tint (tests): HD layers show red, to see they cover the game's
        a[:, :, 0] = np.maximum(a[:, :, 0], 200); a[:, :, 1] //= 2; a[:, :, 2] //= 2
    if blend == 'shadow':                                # 50 % black where the mask is
        m = a[:, :, 3] > 0; a[:] = 0; a[m, 3] = 128
    px = premul(a)[:, :, [2, 1, 0, 3]]                   # BGRA
    os.makedirs(os.path.dirname(out), exist_ok=True)
    open(out, 'wb').write(head + tab + px.tobytes())
    return aw, H


def from_dat(dats, names, scale, outdir):
    import sgdat, xpfx
    files = {}
    for f in dats:
        d = open(f, 'rb').read()
        for n, o, l in sgdat.read_index(d): files.setdefault(n.lower(), d[o:o + l])
    for n in names:
        b = files[n.lower()]; inf, fr = xpfx.frames(b)
        ks = sorted(fr); L = xpfx.layout2([fr[k] for k in ks])
        dirs = L['dirs'] or 1; fpd = L['frames'] if L['dirs'] else len(ks)
        cells = []
        for k in range(dirs * fpd):
            if k not in fr: cells.append((None, None)); continue
            im = Image.fromarray(fr[k]).resize((inf['w'] * scale, inf['h'] * scale), Image.LANCZOS)
            cells.append((im, (inf['cx'] * scale, inf['cy'] * scale)))
        code = n[:4].lower()
        out = os.path.join(outdir, code, n.lower().replace('.xpf', '.hds'))
        aw, ah = pack(cells, dirs, fpd, blend_of(inf['type']), scale, out)
        print(f'{out}: {dirs} dirs x {fpd} frames, {blend_of(inf["type"])}, atlas {aw}x{ah}, {os.path.getsize(out) // 1024} KB')


RENDER_ACTS = {'st': (8, 12), 'mo': (8, 12), 'at': (8, 14), 'da': (1, 1)}     # g039: dirs, frames per direction
RENDER_PASS = {'body': ('', 'normal'), 'glow': ('b', 'add'), 'shadow': ('s', 'shadow')}


GLOW_COLORS = {'core': (1.0, 0.96, 1.0), 'inner': (0.66, 0.52, 1.0), 'halo': (0.48, 0.30, 1.0), 'trail': (0.80, 0.86, 1.0)}


def _segment(s):
    """blade segment (hand end, tip end) of a rendered capsule silhouette: its PCA axis, ends pulled in by the
    capsule radius; the hand end is the one nearer the body (canvas centre).  None when nothing is visible."""
    ys, xs = np.nonzero(s > 0.5)
    if len(xs) < 4: return None
    c = np.array([xs.mean(), ys.mean()], np.float32)
    if len(xs) < 10: return c, c
    w, v = np.linalg.eigh(np.cov(np.stack([xs - c[0], ys - c[1]]))); ax = v[:, 1]
    H, W = s.shape
    if np.dot(np.array([W / 2, H * 0.6]) - c, ax) > 0: ax = -ax
    proj = (xs - c[0]) * ax[0] + (ys - c[1]) * ax[1]
    rad = 2.0 * math.sqrt(max(w[0], 0.0))
    t0, t1 = proj.min() + rad * 0.8, proj.max() - rad * 0.8
    if t1 < t0: t0 = t1 = (t0 + t1) / 2
    return c + ax * t0, c + ax * t1


def _dist(gx, gy, a, b):
    """distance to segment a-b, and the position along it (0 hand .. 1 tip)"""
    d = b - a; L2 = float(d @ d)
    t = np.zeros_like(gx) if L2 < 1e-6 else (((gx - a[0]) * d[0] + (gy - a[1]) * d[1]) / L2).clip(0, 1)
    return np.hypot(gx - (a[0] + t * d[0]), gy - (a[1] + t * d[1])), t


def glow_fx(sil, dirs, fpd, act, scale):
    """Laser blade (user 11-03 "光劍特效不生動"): from each rendered capsule silhouette (target resolution, 0..1)
    only the blade axis is kept (user: too thick); drawn as a thin white-hot core + violet glow + wide soft halo, with a bright
    pulse running hand -> tip, a looping flicker of brightness / halo width, and a swept afterimage between
    the last two frames' blades only while the blade moves (user: afterimage only when it moves).  Returns additive RGBA cells."""
    segs = [None if s is None else _segment(s) for s in sil]
    C = {k: np.array(v, np.float32) for k, v in GLOW_COLORS.items()}
    out = []
    for k, s in enumerate(sil):
        if s is None or segs[k] is None: out.append(None); continue
        f, d = divmod(k, dirs)
        ph = 2 * math.pi * f / fpd
        flick = 0.90 + 0.08 * math.sin(3 * ph + d) + 0.06 * math.sin(7 * ph + 2.1 * d) + 0.04 * math.sin(11 * ph + 0.7 * d)
        wid = 1.0 + 0.20 * math.sin(5 * ph + 1.3 * d)
        r = scale / 2.0
        H, W = s.shape
        gy, gx = np.mgrid[0:H, 0:W].astype(np.float32)
        a, b = segs[k]
        dist, t = _dist(gx, gy, a, b)
        core = np.exp(-(dist / (0.9 * r)) ** 2)
        inner = 1.0 / (1.0 + np.exp((dist - 2.6 * r * wid) / (0.7 * r)))   # the blade body: a soft-edged capsule
        halo = np.exp(-(dist / (5.0 * r * wid)) ** 2)
        pulse = np.zeros_like(core)
        for p0 in (0.0, 0.5):
            p = (f / fpd * 2 + p0 + 0.13 * d) % 1.0
            pulse += np.exp(-((t - p) / 0.12) ** 2)
        pulse *= inner
        tipfade = 0.75 + 0.25 * (1 - t)                      # a little brighter at the hilt
        trail = np.zeros_like(core)
        cur = (a, b)                                         # afterimage only while the blade moves (user 11-03)
        for n in (1, 2):
            if f - n < 0 or segs[k - n * dirs] is None: break
            pv = segs[k - n * dirs]
            move = max(float(np.hypot(*(pv[1] - cur[1]))), float(np.hypot(*(pv[0] - cur[0]))))
            amt = min(max((move - 4.0 * r) / (14.0 * r), 0.0), 1.0) * (0.6 if n == 1 else 0.3)
            if amt <= 0: break
            nst = max(8, int(move / (1.2 * r)) + 1)
            for j in range(1, nst):                          # sweep: a filled wedge between the two blades
                u = j / float(nst)
                sa = pv[0] * u + cur[0] * (1 - u); sb = pv[1] * u + cur[1] * (1 - u)
                dd, tt = _dist(gx, gy, sa, sb)
                trail = np.maximum(trail, amt * (1 - u * 0.75) * (0.4 + 0.6 * tt) * np.exp(-(dd / (2.0 * r)) ** 2))
            cur = pv
        rgb = ((core * 1.0 * tipfade)[:, :, None] * C['core'] + (inner * 0.45)[:, :, None] * C['inner']
               + (halo * 0.22)[:, :, None] * C['halo'] + (pulse * 0.45)[:, :, None] * C['core']
               + (trail * 0.75)[:, :, None] * C['trail'])
        rgb = (rgb * flick).clip(0, 1)
        al = np.where(rgb.max(2) > 2 / 255, 1.0, 0.0)
        out.append(Image.fromarray((np.dstack([rgb, al]) * 255 + 0.5).astype(np.uint8), 'RGBA'))
    return out


def from_render(rdir, code, scale, outdir, pivot=(89, 109), base=179):
    """Blender renders (art3d/units/<code>/render/frames): body / glow at SS x the xpf canvas, shadow at 1x.
    The render canvas has the xpf pivot at PIV x SS; cells are scaled to `scale` x the game's pixels."""
    for act, (dirs, fpd) in RENDER_ACTS.items():
        for ps, (suf, blend) in RENDER_PASS.items():
            d0 = os.path.join(rdir, act, ps)
            if not os.path.isdir(d0): continue
            cells = []
            if blend == 'add' and GLOW_FX:                           # laser blade effect from the silhouettes
                sil, canv = [], None
                for k in range(dirs * fpd):
                    f, d = divmod(k, dirs)
                    p = os.path.join(d0, 'd%d_f%02d.png' % (d, f))
                    if not os.path.exists(p): sil.append(None); continue
                    im = Image.open(p).convert('RGBA'); ss = max(1, round(im.width / base))
                    tw, th = round(im.width * scale / ss), round(im.height * scale / ss)
                    a = np.asarray(im, np.float32); m = (a[:, :, :3].max(2) * a[:, :, 3] / 255.0 > 6).astype(np.uint8) * 255
                    sil.append(np.asarray(Image.fromarray(m, 'L').resize((tw, th), Image.BOX), np.float32) / 255.0)
                for im in glow_fx(sil, dirs, fpd, act, scale):
                    cells.append((im, (pivot[0] * scale, pivot[1] * scale)) if im is not None else (None, None))
                out = os.path.join(outdir, code, f'{code}{act}{suf}.hds')
                aw, ah = pack(cells, dirs, fpd, blend, scale, out)
                print(f'{out}: {dirs} dirs x {fpd} frames, {blend} (laser fx), atlas {aw}x{ah}, {os.path.getsize(out) // 1024} KB')
                continue
            for k in range(dirs * fpd):
                f, d = divmod(k, dirs)
                p = os.path.join(d0, 'd%d_f%02d.png' % (d, f))
                if not os.path.exists(p): cells.append((None, None)); continue
                im = Image.open(p).convert('RGBA')
                ss = max(1, round(im.width / base))                   # 4 for body / glow, 1 for shadow (canvas 179 / 177)
                tw, th = round(im.width * scale / ss), round(im.height * scale / ss)
                if blend == 'add':                                   # additive: colour x alpha, kept where it shows
                    a = np.array(im).astype(np.float32); a[:, :, :3] *= a[:, :, 3:4] / 255.0
                    a[:, :, 3] = np.where(a[:, :, :3].max(2) > 6, 255, 0); im = Image.fromarray(a.clip(0, 255).astype(np.uint8))
                im = im.resize((tw, th), Image.LANCZOS if ss >= scale else Image.BILINEAR)
                cells.append((im, (pivot[0] * scale, pivot[1] * scale)))
            out = os.path.join(outdir, code, f'{code}{act}{suf}.hds')
            aw, ah = pack(cells, dirs, fpd, blend, scale, out)
            print(f'{out}: {dirs} dirs x {fpd} frames, {blend}, atlas {aw}x{ah}, {os.path.getsize(out) // 1024} KB')


if __name__ == '__main__':
    ap = argparse.ArgumentParser()
    ap.add_argument('out'); ap.add_argument('--scale', type=int, default=2)
    ap.add_argument('--from-dat'); ap.add_argument('--from-render', nargs=2, metavar=('DIR', 'CODE'))
    ap.add_argument('--tint', action='store_true'); ap.add_argument('--plain-glow', action='store_true'); ap.add_argument('names', nargs='*')
    a = ap.parse_args()
    TINT = a.tint; GLOW_FX = not a.plain_glow
    if a.from_dat:
        from_dat(a.from_dat.split(','), a.names, a.scale, a.out)
    elif a.from_render:
        from_render(a.from_render[0], a.from_render[1], a.scale, a.out)
    else:
        sys.exit(__doc__)
