"""Unit renders -> the game's own low-resolution sprites (.xpf) inside tc2.dat (2026-11-04, user: the deploy room
still shows the old Ghast: those screens draw the .xpf sprites, not the HD overlay).  Generalised from the deleted
art3d/units/g039/render/pack_g039.py (git fef9d98).
For CODE and every action / layer whose renders exist (FRAMES/<act>/<body|glow|shadow>/dD_fFF.png, the HD pipeline's
supersampled render canvas, pivot = the xpf pivot x SS), the original xpf is taken from the .dat, its frames replaced
(header, canvas, pivot, frame count kept) and the result written to OUT/<name>.xpf; with --dat the .dat is rebuilt with
the new files (others byte for byte).  Layers: body -> <code><act>.xpf, glow -> <code><act>b.xpf (additive),
shadow -> <code><act>s.xpf (mask).  An action without renders (e.g. da) keeps its original sprites.
usage: python tools/xpf_pack_render.py CODE FRAMES OUT [--dat SRC.dat DST.dat] [--src out/tc/tc2.dat,out/tc/tc.dat]"""
import os, sys, struct, argparse
import numpy as np
from PIL import Image
HERE = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, HERE); sys.path.insert(0, os.path.join(HERE, '..', 'art3d'))
import xpf_write, xpfx, sgdat, sgdat_add
FRAMES = {'st': 12, 'mo': 12, 'at': 14, 'da': 1}
RW = {'st': 179, 'mo': 179, 'at': 177, 'da': 179}      # xpf canvas width of each action (renders are a multiple)


def canvas(img, w, h):
    c = Image.new('RGBA', (w, h), (0, 0, 0, 0)); c.paste(img, (0, 0)); return c

from PIL import ImageFilter
def down(im, w0=None):
    """supersampled render -> canvas size (Lanczos on premultiplied alpha)"""
    if w0 is None: return im
    f = im.width // w0
    if f <= 1: return im
    return im.resize((im.width // f, im.height // f), Image.LANCZOS)

def body_img(p, w, h, ref_w=None):
    im = down(Image.open(p).convert('RGBA'), ref_w)
    rgb = im.convert('RGB').filter(ImageFilter.UnsharpMask(radius=1.0, percent=140, threshold=1))
    a = np.array(im); c = np.array(rgb).astype(np.float32)
    m = a[:, :, 3] >= 100
    if m.any():                                   # stretch contrast of the character pixels (sprite look)
        lum = c[m].mean(1); lo, hi = np.percentile(lum, 3), np.percentile(lum, 99.5)
        c = np.clip((c - lo) / max(1.0, hi - lo), 0, 1) ** 0.9 * 245 + 6
    out = np.zeros(a.shape, np.uint8); out[:, :, :3] = c.astype(np.uint8); out[:, :, 3] = np.where(m, 255, 0)
    return canvas(Image.fromarray(out), w, h)

def glow_img(p, w, h, ref_w=None):
    a = np.array(down(Image.open(p).convert('RGBA'), ref_w)).astype(np.float32)
    rgb = a[:, :, :3] * (a[:, :, 3:4] / 255.0)              # additive: premultiplied colour, black = no change
    keep = rgb.max(2) > 10
    out = np.zeros(a.shape, np.uint8); out[:, :, :3] = np.clip(rgb, 0, 255); out[:, :, 3] = np.where(keep, 255, 0)
    return canvas(Image.fromarray(out), w, h)

def shadow_mask(p, w, h, ref_w=None):
    im = Image.open(p).convert('RGBA')
    if ref_w and im.width // ref_w > 1:                      # shadows rendered supersampled: area-average first
        f = im.width // ref_w; im = im.resize((im.width // f, im.height // f), Image.BOX)
    a = np.array(im)
    m = a[:, :, 3] >= 70
    c = np.zeros((h, w), bool); hh, ww = m.shape; c[:min(h, hh), :min(w, ww)] = m[:min(h, hh), :min(w, ww)]
    return c

def enc_mask(m):
    h, w = m.shape
    rows = [y for y in range(h) if m[y].any()]
    if not rows: return b'\0\0'
    top, bot = rows[0], h - 1 - rows[-1]
    out = bytearray([top, bot])
    for y in range(top, h - bot):
        x = 0
        while x < w:
            s = 0
            while x + s < w and not m[y, x + s] and s < 255: s += 1
            if x + s >= w: out += bytes([s]); x += s; break
            if s == 255 and not m[y, x + s]: out += bytes([255, 0]); x += 255; continue
            n = 0
            while x + s + n < w and m[y, x + s + n] and n < 255: n += 1
            out += bytes([s, n]); x += s + n
    return bytes(out)

def replace_raw(b, datas_new):
    """like xpf_write.replace_frames but takes already-encoded frame bytes (for mask layers)"""
    offs = xpfx.offsets(b); base = offs[0]; m = len(offs)
    datas = [b[offs[k]:offs[k + 1]] for k in range(m - 1)]
    for k, d in datas_new.items(): datas[k] = d
    new = []; p = base
    for d in datas: new.append(p); p += len(d)
    new.append(p)
    hdr = bytearray(b[:base]); struct.pack_into('<%dI' % len(new), hdr, 14, *new)
    return bytes(hdr) + b''.join(datas)


GLOW_FX = True
GLOW_SCALE = 2.4      # hd_pack.glow_fx widths x this at 1x: ~2 px white core, ~6 px violet body, soft ~12 px halo


def glow_layer(items, w, h, act):
    """the original b layer look (user 11-04 "原版的光刀还有光影的效果"): a soft wide violet glow round a bright core,
    a light pulse along the blade and the swept afterimage while it moves -- hd_pack.glow_fx at sprite size"""
    import hd_pack
    D = 1 if act == 'da' else 8; fpd = len(items) // D
    sil = [None] * len(items)
    for k, p in items:
        im = Image.open(p).convert('RGBA'); f = max(1, im.width // RW[act])
        a = np.asarray(im, np.float32); m = (a[:, :, :3].max(2) * a[:, :, 3] / 255.0 > 6).astype(np.uint8) * 255
        s = np.asarray(Image.fromarray(m, 'L').resize((im.width // f, im.height // f), Image.BOX), np.float32) / 255.0
        c = np.zeros((h, w), np.float32); hh, ww = min(h, s.shape[0]), min(w, s.shape[1]); c[:hh, :ww] = s[:hh, :ww]
        sil[k] = c if c.max() > 0.3 else None
    out = {}
    for k, im in enumerate(hd_pack.glow_fx(sil, D, fpd, act, GLOW_SCALE)):
        if im is None: im = Image.new('RGBA', (w, h), (0, 0, 0, 0))
        a = np.asarray(im).copy(); a[..., 3] = np.where(a[..., :3].max(2) > 10, 255, 0)   # additive: dark = no change
        out[k] = Image.fromarray(a, 'RGBA')
    return out


def frame_paths(fr, act, ps):
    D = 1 if act == 'da' else 8
    for f in range(FRAMES[act]):
        for d in range(D):
            yield f * D + d, os.path.join(fr, act, ps, 'd%d_f%02d.png' % (d, f))


def build(code, fr, out, srcs):
    files = {}
    for s in srcs:
        b = open(s, 'rb').read()
        for n, o, l in sgdat.read_index(b): files.setdefault(n.lower(), b[o:o + l])
    os.makedirs(out, exist_ok=True); made = []
    for act in FRAMES:
        for ps, suffix in (('body', ''), ('glow', 'b'), ('shadow', 's')):
            name = '%s%s%s.xpf' % (code, act, suffix)
            if name not in files: continue
            items = list(frame_paths(fr, act, ps))
            if any(not os.path.exists(p) for _, p in items): continue
            b = files[name]; inf = xpfx.info(b); w, h = inf['w'], inf['h']
            n_orig = len(xpfx.offsets(b)) - 1
            if len(items) != n_orig: print('SKIP', name, 'frames', len(items), '!=', n_orig); continue
            if ps == 'shadow':
                nb = replace_raw(b, {k: enc_mask(shadow_mask(p, w, h, RW[act])) for k, p in items})
            elif ps == 'glow' and GLOW_FX:
                nb = xpf_write.replace_frames(b, glow_layer(items, w, h, act))
            else:
                fn = body_img if ps == 'body' else glow_img
                nb = xpf_write.replace_frames(b, {k: fn(p, w, h, RW[act]) for k, p in items})
            inf2, fr2 = xpfx.frames(nb)
            assert (inf2['w'], inf2['h'], inf2['cx'], inf2['cy']) == (w, h, inf['cx'], inf['cy'])
            open(os.path.join(out, name), 'wb').write(nb); made.append(name)
            print(f'{name}: {n_orig} frames, {len(b)} -> {len(nb)} bytes (decoded {len(fr2)})')
    return made


if __name__ == '__main__':
    ap = argparse.ArgumentParser()
    ap.add_argument('code'); ap.add_argument('frames'); ap.add_argument('out')
    ap.add_argument('--src', default='out/tc/tc2.dat,out/tc/tc.dat'); ap.add_argument('--dat', nargs=2, metavar=('SRC', 'DST'))
    a = ap.parse_args()
    made = build(a.code.lower(), a.frames, a.out, a.src.split(','))
    if a.dat:
        print('dat', sgdat_add.add(a.dat[0], a.dat[1], [os.path.join(a.out, m) for m in made]), len(made), 'files ->', a.dat[1])
