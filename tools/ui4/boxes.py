"""Find candidate text boxes in a sprite frame and draw a numbered, 2x annotated preview."""
import numpy as np, cv2, sys
from PIL import Image, ImageDraw
import xcodec, relabel
from sheet import E


def frame_arrays(nm, k):
    b = E[nm]; w, h, offs = xcodec.frames_meta(b)
    return xcodec.decode(b, offs[k], w, h)[:2]


def text_boxes(pix, a, vertical=False):
    rgb = relabel.rgb_of(pix).astype(np.uint8)
    g = rgb.max(-1)
    bgm = cv2.medianBlur(g, 9)
    diff = (g.astype(int) - bgm.astype(int))
    m = ((diff > 45) & (g > 110) & a).astype(np.uint8)
    if vertical:
        m = m.T.copy()
    # remove long straight lines (frames)
    hl = cv2.morphologyEx(m, cv2.MORPH_OPEN, np.ones((1, 25), np.uint8))
    vl = cv2.morphologyEx(m, cv2.MORPH_OPEN, np.ones((12, 1), np.uint8))
    m = m & ~hl & ~vl
    d = cv2.dilate(m, np.ones((3, 5), np.uint8))
    n, lab, st, _ = cv2.connectedComponentsWithStats(d)
    out = []
    for i in range(1, n):
        x, y, w, h, area = st[i]
        if 5 <= h <= 24 and w >= 8 and w / h >= 1.0:
            sub = m[y:y + h, x:x + w]
            ys, xs = np.where(sub)
            if len(xs) < 8: continue
            bx = (x + xs.min(), y + ys.min(), xs.max() - xs.min() + 1, ys.max() - ys.min() + 1)
            if vertical:
                bx = (bx[1], bx[0], bx[3], bx[2])
            out.append(tuple(int(v) for v in bx))
    out.sort(key=lambda b: (b[1] // 6, b[0]))
    return out


def preview(items, fn, scale=2, maxw=1500):
    """items: [(title, pix, a, boxes)] -> one sheet."""
    tiles = []
    for title, pix, a, boxes in items:
        rgb = relabel.rgb_of(pix).astype(np.uint8)
        im = Image.fromarray(np.dstack([rgb, a.astype(np.uint8) * 255]), 'RGBA')
        im = im.resize((im.width * scale, im.height * scale), Image.NEAREST)
        bgc = Image.new('RGBA', im.size, (70, 0, 70, 255)); bgc.alpha_composite(im); im = bgc
        d = ImageDraw.Draw(im)
        for i, (x, y, w, h) in enumerate(boxes):
            d.rectangle([x * scale - 1, y * scale - 1, (x + w) * scale, (y + h) * scale], outline=(255, 60, 60))
            d.text((x * scale, max(0, y * scale - 10)), str(i), fill=(255, 255, 0))
        tiles.append((title, im))
    x = y = rowh = 0; pos = []
    for t, im in tiles:
        if x + im.width > maxw and x > 0: x = 0; y += rowh + 16; rowh = 0
        pos.append((x, y + 14)); x += im.width + 8; rowh = max(rowh, im.height)
    S = Image.new('RGB', (maxw, y + rowh + 18), (30, 30, 30)); d = ImageDraw.Draw(S)
    for (t, im), (px, py) in zip(tiles, pos):
        S.paste(im, (px, py)); d.text((px, py - 13), t, fill=(0, 255, 255))
    S.save(fn)
    return S.size
