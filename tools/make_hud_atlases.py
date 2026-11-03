"""Build the HUD atlases from the game's own art (user 2026-11-01 "use the original pictures").
usage: python tools/make_hud_atlases.py GAME_DIR OUT_DIR
  SGHud-insg.png  rank insignia (NTF2 ui-insg.xpf, frame rank*8 + branch): 4 cols (inf/mob/avi/org) x 22 rows, 140 x 44,
                  (the shipped client/sgrender/art copy differs from this output in ~400 outline pixels of 50 000)
                  cut (9,4)-(149,48) of the 158 x 53 frame, the frame ornaments and stray specks (< 6 px) removed
  SGHud-dcr.png   commander medal ribbons (dcr-NNN.xpf, medal id = NNN*1000 + frame): 32 cols x 30 rows of 44 x 16
  SGHud-brn.png   the four branch pictures + INF/MOB/AVI/ORG label from the battle result frame (brw-frm.xpf frame 0),
                  4 cells 34 x 42
The HUD (client/sgrender/sghud.c atlas()) draws cells of these; they go to the player's folder by OTA (common).
Needs tools/sgdat.py, tools/xpf.py, Pillow, numpy, scipy."""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import sgdat, xpf
from PIL import Image
import numpy as np
from scipy import ndimage

def index(game):
    idx = {}
    for f in os.listdir(game):
        if f.lower().endswith('.dat'):
            d = open(os.path.join(game, f), 'rb').read()
            try:
                for name, off, ln in sgdat.read_index(d):
                    idx.setdefault(name.lower(), d[off:off + ln])
            except Exception:
                pass
    return idx

def nframes(b):
    """only the leading increasing offsets are real frames"""
    o = xpf.offsets(b); n = 0
    while n + 1 < len(o) and o[n + 1] > o[n]:
        n += 1
    return n

def main(game, out):
    idx = index(game)
    os.makedirs(out, exist_ok=True)
    # insignia: the purple background is the same in every frame -> a pixel equal to the most common value at its
    # place (over all frames) is background
    b = idx['ui-insg.xpf']; nf = nframes(b)
    cells = {}
    for r in range(22):
        for c in range(4):
            if r * 8 + c < nf:
                cells[(r, c)] = np.array(xpf.frame(b, r * 8 + c).convert('RGBA').crop((9, 4, 149, 48)))
    st = np.stack(list(cells.values())).astype(np.int64)
    key = (st[..., 0] << 24) | (st[..., 1] << 16) | (st[..., 2] << 8) | st[..., 3]
    mode = np.apply_along_axis(lambda v: np.bincount(np.unique(v, return_inverse=True)[1]).argmax(), 0, key)
    uniq = [np.unique(key[:, y, x]) for y in range(44) for x in range(140)]
    bgv = np.array([u[m] for u, m in zip(uniq, mode.ravel())]).reshape(44, 140)
    a = np.zeros((22 * 44, 560, 4), np.uint8)
    for (r, c), im in cells.items():
        k = (im.astype(np.int64)[..., 0] << 24) | (im[..., 1].astype(np.int64) << 16) | (im[..., 2].astype(np.int64) << 8) | im[..., 3]
        im = im.copy(); im[(k == bgv) | (im[..., :3].max(axis=2) < 72)] = 0      # + the dark outline
        a[r * 44:(r + 1) * 44, c * 140:(c + 1) * 140] = im
    x = np.arange(a.shape[1]) % 140
    a[:, (x < 9) | (x >= 131)] = 0                             # frame ornaments
    al = a[..., 3] > 0
    lab, n = ndimage.label(al)
    if n:
        sz = ndimage.sum(al, lab, range(1, n + 1))
        a[np.isin(lab, np.where(sz < 6)[0] + 1)] = 0
    Image.fromarray(a).save(os.path.join(out, 'SGHud-insg.png'))
    # medals
    at = Image.new('RGBA', (32 * 44, 30 * 16))
    for r in range(30):
        b = idx.get('dcr-%03d.xpf' % r)
        if not b:
            continue
        for f in range(1, min(32, nframes(b))):
            im = xpf.frame(b, f).convert('RGBA')
            at.paste(im.crop((0, 0, 44, 16)), (f * 44, r * 16))
    at.save(os.path.join(out, 'SGHud-dcr.png'))
    # branch pictures
    fr = xpf.frame(idx['brw-frm.xpf'], 0).convert('RGBA')
    bb = fr.getbbox(); fr = fr.crop(bb)                        # the same picture the tools/extract_sprites.py crop gives
    o = Image.new('RGBA', (34 * 4, 42))
    for i, t in enumerate((156, 205, 254, 303)):
        o.paste(fr.crop((89, t + 1, 123, t + 43)), (34 * i, 0))
    o.save(os.path.join(out, 'SGHud-brn.png'))
    print('atlases written to', out)

if __name__ == '__main__':
    main(sys.argv[1], sys.argv[2])
