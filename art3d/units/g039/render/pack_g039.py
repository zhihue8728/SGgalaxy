"""Pack the Blender renders of g039 (Ghast) back into game sprites.
  python3 pack_g039.py            -> render/xpf/*.xpf, render/preview/*.png, render/tc2_g039.dat
Frame order in every file: index = frame * 8 + direction (direction 0 faces screen-right, clockwise).
Layers: body (st/mo/at/da), b = blade glow (additive), s = shadow mask (no pixel data), p = footprints (kept)."""
import os, sys, struct, shutil
import numpy as np
from PIL import Image
HERE = os.path.dirname(os.path.abspath(__file__)); REPO = os.path.abspath(os.path.join(HERE, '..', '..', '..', '..'))
sys.path.insert(0, os.path.join(REPO, 'tools')); sys.path.insert(0, os.path.join(REPO, 'art3d'))
import xpf_write, xpfx, sgdat_add
ORIG = os.path.join(HERE, 'orig_xpf'); FR = os.path.join(HERE, 'frames'); OUT = os.path.join(HERE, 'xpf'); PV = os.path.join(HERE, 'preview')
FRAMES = {'st': 12, 'mo': 12, 'at': 14, 'da': 1}
PIV = (89, 109)
RW = {'st': 179, 'mo': 179, 'at': 177, 'da': 179}   # render canvas width per action (supersampled renders are a multiple)

def canvas(img, w, h, piv_src=PIV):
    """place a render (pivot at PIV) onto a w x h canvas whose pivot is also PIV"""
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

def shadow_mask(p, w, h):
    a = np.array(Image.open(p).convert('RGBA'))
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

def frame_paths(act, ps):
    D = 1 if act == 'da' else 8
    for f in range(FRAMES[act]):
        for d in range(D):
            yield f * D + d, os.path.join(FR, act, ps, 'd%d_f%02d.png' % (d, f))

def main():
    os.makedirs(OUT, exist_ok=True); os.makedirs(PV, exist_ok=True)
    made = []
    for act in FRAMES:
        for ps, suffix in (('body', ''), ('glow', 'b'), ('shadow', 's')):
            name = 'g039%s%s.xpf' % (act, suffix)
            src = os.path.join(ORIG, name)
            if not os.path.exists(src): continue
            b = open(src, 'rb').read(); inf = xpfx.info(b); w, h = inf['w'], inf['h']
            n_orig = len(xpfx.offsets(b)) - 1
            items = list(frame_paths(act, ps))
            missing = [p for _, p in items if not os.path.exists(p)]
            if missing: print('SKIP', name, len(missing), 'renders missing'); continue
            assert len(items) == n_orig, (name, len(items), n_orig)
            if ps == 'shadow':
                nb = replace_raw(b, {k: enc_mask(shadow_mask(p, w, h)) for k, p in items})   # shadows render at 1x
            else:
                fn = body_img if ps == 'body' else glow_img
                nb = xpf_write.replace_frames(b, {k: fn(p, w, h, RW[act]) for k, p in items})
            open(os.path.join(OUT, name), 'wb').write(nb); made.append(name)
            # round-trip check
            inf2, fr2 = xpfx.frames(nb)
            print(name, 'frames', n_orig, 'decoded', len(fr2), 'bytes', len(b), '->', len(nb))
    return made

def preview():
    """side-by-side sheets: original vs new, one row per direction, for st/mo/at body+glow"""
    for act in ('st', 'mo', 'at'):
        for suffix in ('', 'b'):
            name = 'g039%s%s.xpf' % (act, suffix)
            if not os.path.exists(os.path.join(OUT, name)): continue
            sheets = []
            for path in (os.path.join(ORIG, name), os.path.join(OUT, name)):
                b = open(path, 'rb').read(); inf, fr = xpfx.frames(b); D = 8; F = FRAMES[act]
                body = None
                if suffix == 'b':
                    bb = open(path.replace('%sb.xpf' % act, '%s.xpf' % act), 'rb').read(); _, body = xpfx.frames(bb)
                cw, ch = 110, 120; x0, y0 = 89 - 55, 109 - 92
                S = Image.new('RGBA', (cw * F, ch * D), (96, 98, 110, 255))
                for k, a in fr.items():
                    f, d = divmod(k, D)
                    im = Image.fromarray(a)
                    if body is not None and k in body:
                        base = Image.fromarray(body[k]); base = base.crop((0, 0, im.width, im.height)) if base.size != im.size else base
                        c = Image.new('RGBA', im.size, (0, 0, 0, 0)); c.paste(base, (0, 0))
                        arr = np.array(c).astype(int); g = np.array(im).astype(int)
                        arr[:, :, :3] = np.clip(arr[:, :, :3] + g[:, :, :3], 0, 255); arr[:, :, 3] = np.maximum(arr[:, :, 3], g[:, :, 3])
                        im = Image.fromarray(arr.astype(np.uint8))
                    S.alpha_composite(im.crop((x0, y0, x0 + cw, y0 + ch)), (f * cw, d * ch))
                sheets.append(S)
            W = sheets[0].width; H = sheets[0].height
            C = Image.new('RGBA', (W * 2 + 20, H), (40, 40, 40, 255)); C.paste(sheets[0], (0, 0)); C.paste(sheets[1], (W + 20, 0))
            C.save(os.path.join(PV, 'cmp_%s%s.png' % (act, suffix)))

def build_dat():
    src = os.path.join(REPO, 'out', 'tc', 'tc2.dat'); dst = os.path.join(HERE, 'tc2_g039.dat')
    files = [os.path.join(OUT, f) for f in sorted(os.listdir(OUT)) if f.endswith('.xpf')]
    print('dat', sgdat_add.add(src, dst, files), len(files), 'files ->', dst)

if __name__ == '__main__':
    made = main(); preview()
    if '--dat' in sys.argv: build_dat()
