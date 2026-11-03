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
import sys, os, struct, argparse
HERE = os.path.dirname(os.path.abspath(__file__)); REPO = os.path.dirname(HERE)
sys.path.insert(0, HERE); sys.path.insert(0, os.path.join(REPO, 'art3d'))
import numpy as np
from PIL import Image

TINT = False
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


def from_render(rdir, code, scale, outdir, pivot=(89, 109), base=179):
    """Blender renders (art3d/units/<code>/render/frames): body / glow at SS x the xpf canvas, shadow at 1x.
    The render canvas has the xpf pivot at PIV x SS; cells are scaled to `scale` x the game's pixels."""
    for act, (dirs, fpd) in RENDER_ACTS.items():
        for ps, (suf, blend) in RENDER_PASS.items():
            d0 = os.path.join(rdir, act, ps)
            if not os.path.isdir(d0): continue
            cells = []
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
    ap.add_argument('--tint', action='store_true'); ap.add_argument('names', nargs='*')
    a = ap.parse_args()
    TINT = a.tint
    if a.from_dat:
        from_dat(a.from_dat.split(','), a.names, a.scale, a.out)
    elif a.from_render:
        from_render(a.from_render[0], a.from_render[1], a.scale, a.out)
    else:
        sys.exit(__doc__)
