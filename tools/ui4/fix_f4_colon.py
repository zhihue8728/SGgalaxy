"""F4 window (own f4-bk-mi / other player's f4-bk-nm): move the colon after '轉生/转生' to the same x as the colon after
'榮譽/荣誉' (user 2026-10-22 15:01: not aligned).  The colons are painted in the art; the number is drawn by the client.
Edits out/ui_tw and out/ui_cn in place; safe to run twice.  Run after build_ui.py build, before build_i18n_dats.py."""
import os, sys
import numpy as np
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import xcodec

HERE = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', '..', 'out')

def bright(pix):
    p = pix.astype(np.int32)
    return np.maximum.reduce([((p >> 11) & 31) * 8, ((p >> 5) & 63) * 4, (p & 31) * 8])

def colon_x(g, ys, x0, x1):
    xs = [x for x in range(x0, x1) if all(g[y, x] > 150 for y in ys)]
    return xs[0] if xs else None

def fix(path):
    b = open(path, 'rb').read()
    w, h, offs = xcodec.frames_meta(b)
    pix, a, _ = xcodec.decode(b, offs[0], w, h)
    g = bright(pix)
    honor = colon_x(g, (321, 326), 100, 200)
    reinc = colon_x(g, (300, 305), 100, 200)
    if honor is None or reinc is None:
        return f'{os.path.basename(path)}: colons not found ({honor}, {reinc})'
    if honor == reinc:
        return f'{os.path.basename(path)}: already aligned at x={honor}'
    rows = [y for y in range(296, 311) if g[y, reinc] > 150]
    col = pix[rows[0], reinc]
    for y in rows:
        for dx in (0, 1):
            pix[y, reinc + dx] = pix[y, reinc + 4 + dx]          # erase: background two pixels to the right
            a[y, reinc + dx] = a[y, reinc + 4 + dx]
            pix[y, honor + dx] = col
            a[y, honor + dx] = True
    open(path, 'wb').write(xcodec.rebuild(b, {offs[0]: xcodec.encode(pix, a)}))
    return f'{os.path.basename(path)}: colon {reinc} -> {honor}'

if __name__ == '__main__':
    for lang in ('tw', 'cn'):
        for nm in ('f4-bk-mi.xpf', 'f4-bk-nm.xpf'):
            p = os.path.join(HERE, f'ui_{lang}', nm)
            if os.path.exists(p):
                print(lang, fix(p))
