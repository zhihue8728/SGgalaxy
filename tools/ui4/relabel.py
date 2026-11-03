"""Erase an English label inside a UI sprite frame and draw a Chinese one in the same colours.
Small labels (box height < 14) use the game's 12 px bitmap CJK font (glyph.py); bigger titles use Noto Sans CJK Bold."""
import numpy as np, cv2
from PIL import Image, ImageDraw, ImageFont
import glyph

TTF = '/usr/share/fonts/opentype/noto/NotoSansCJK-Bold.ttc'
TTF_INDEX = {'tw': 3, 'cn': 2}       # Bold.ttc faces: 0 JP, 1 KR, 2 SC, 3 TC, 4 HK


def rgb_of(p):
    p = p.astype(np.int32)
    return np.stack([((p >> 11) & 31) * 255 // 31, ((p >> 5) & 63) * 255 // 63, (p & 31) * 255 // 31], -1)


def p565(rgb):
    rgb = np.clip(np.asarray(rgb), 0, 255).astype(np.int32)
    return ((rgb[..., 0] * 31 + 127) // 255 << 11 | (rgb[..., 1] * 63 + 127) // 255 << 5 |
            (rgb[..., 2] * 31 + 127) // 255).astype(np.uint16)


def ttf_mask(text, lang, px):
    f = ImageFont.truetype(TTF, px, index=TTF_INDEX[lang])
    l, t, r, b = f.getbbox(text)
    im = Image.new('L', (r - l + 2, b - t + 2)); ImageDraw.Draw(im).text((1 - l, 1 - t), text, font=f, fill=255)
    return np.asarray(im).astype(np.float32) / 255.0


def bitmap_mask(text, lang, bold=False, vertical=False):
    if '\n' in text and not vertical:
        ls = [bitmap_mask(s, lang, bold) for s in text.split('\n')]
        W = max(l.shape[1] for l in ls); parts = []
        for l in ls:
            p = np.zeros((12, W), np.float32); o = (W - l.shape[1]) // 2
            p[:l.shape[0], o:o + l.shape[1]] = l; parts += [p, np.zeros((1, W), np.float32)]
        return np.concatenate(parts[:-1], 0)
    if vertical:
        parts = []
        for ch in text:
            m = bitmap_mask(ch, lang, bold)
            pad = np.zeros((m.shape[0], 13), np.float32); off = (13 - m.shape[1]) // 2
            pad[:, max(0, off):max(0, off) + m.shape[1]] = m[:, :13]
            parts += [pad, np.zeros((2, 13), np.float32)]
        return np.concatenate(parts[:-1], 0)
    cols = []
    for ch in text:
        if ch == ' ':
            cols.append(np.zeros((12, 4), bool)); continue
        m, wd = glyph.glyph(ch, lang)
        if ord(ch) < 128:
            cols.append(m[:, :max(wd, 5)]); cols.append(np.zeros((12, 1), bool)); continue
        # CJK: uniform 12 px cell, the glyph's ink centred in it (even spacing, user 2026-10-22 02:21)
        ink = np.where(m.any(0))[0]
        cell = np.zeros((12, 12), bool)
        if len(ink):
            g = m[:, ink[0]:ink[-1] + 1]; o = (12 - g.shape[1]) // 2
            cell[:, o:o + g.shape[1]] = g[:, :12 - o]
        cols.append(cell)
    m = np.concatenate(cols, 1) if cols else np.zeros((12, 1), bool)
    rows = np.where(m.any(1))[0]; cs = np.where(m.any(0))[0]
    if len(rows): m = m[rows[0]:rows[-1] + 1, :cs[-1] + 1]
    if bold:
        b = m.copy(); b[:, 1:] |= m[:, :-1]; m = np.concatenate([b, np.zeros((m.shape[0], 0), bool)], 1)
    return m.astype(np.float32)


def relabel(pix, a, box, text, lang, align='auto', force_ttf=None, color=None, vertical=False, fill=None, pad=2, thr=25, px=None, keep_lines=True, hl=False):
    """pix uint16 [h,w] RGB565, a bool [h,w]; box = (x, y, w, h) of the English text.  Modifies in place."""
    H, W = a.shape
    x, y, bw, bh = box
    px_, py_ = pad if isinstance(pad, (tuple, list)) else (pad, pad)
    x0, y0, x1, y1 = max(0, x - px_), max(0, y - py_), min(W, x + bw + px_), min(H, y + bh + py_)
    rgb = rgb_of(pix).astype(np.float32)
    # background = median of the ring just outside the box
    ring = np.zeros((H, W), bool)
    rx0, ry0, rx1, ry1 = max(0, x0 - 2), max(0, y0 - 2), min(W, x1 + 2), min(H, y1 + 2)
    ring[ry0:ry1, rx0:rx1] = True; ring[y0:y1, x0:x1] = False; ring &= a
    if ring.sum() > 4:
        # ignore thin frame lines in the ring (a pixel that differs from both neighbours 2 px away)
        L = rgb.sum(-1); P = np.pad(L, 2, mode='edge')
        up, dn, lf, rt = P[:-4, 2:-2], P[4:, 2:-2], P[2:-2, :-4], P[2:-2, 4:]
        thin = ((np.abs(L - up) > 60) & (np.abs(L - dn) > 60)) | ((np.abs(L - lf) > 60) & (np.abs(L - rt) > 60))
        rr = ring & ~thin
        if rr.sum() < 4: rr = ring
        bg = np.median(rgb[rr], 0)
    else:
        bg = np.zeros(3)
    inside = np.zeros((H, W), bool); inside[y0:y1, x0:x1] = True; inside &= a
    dist = np.abs(rgb - bg).sum(-1)
    txt = inside & (dist > 70)
    if txt.sum() < 3:
        return False
    # text colour = the brightest third of the text pixels; glow = the dimmer differing pixels
    lum = rgb[txt].sum(-1)
    core = rgb[txt][lum >= np.percentile(lum, 66)]
    tcol = np.median(core, 0) if color is None else np.array(color, np.float32)
    glow_px = inside & (dist > thr) & ~txt
    has_glow = glow_px.sum() > 0.6 * txt.sum()
    gcol = np.median(rgb[glow_px], 0) if has_glow else None
    if gcol is not None and gcol.sum() < bg.sum() + 30:      # a dark outline is not a glow -> no dark halo
        gcol = None
    # erase: inpaint the text + its glow, but keep straight frame lines (user: black blocks over the border lines)
    diff8 = (inside & (dist > thr)).astype(np.uint8)
    lines = np.zeros((H, W), bool)
    for kern in ((1, 14), (9, 1)):
        lm = cv2.morphologyEx(diff8, cv2.MORPH_OPEN, np.ones(kern, np.uint8))
        n_, lab, st, _ = cv2.connectedComponentsWithStats(lm)
        for i in range(1, n_):
            lx, ly, lw, lh, _a = st[i]
            # a frame line runs past the caption's own box; a letter stroke does not
            # a frame line is thin and crosses the whole erase area (letter strokes / glow rows do not)
            if kern[0] == 1:
                is_line = lh <= 3 and lw >= (x1 - x0) - 1
            else:
                is_line = lw <= 3 and lh >= (y1 - y0) - 1 and lh >= 12
            if is_line and keep_lines:
                lines |= lab == i
    if hl:
        # HIGHLIGHTED button state (2026-10-22 10:55): the text glows and the glow fills most of the box, so the
        # ring/inpaint estimate smeared white blobs.  Flat-fill the padded box with the button colour under the
        # glow (dimmer 25 % of its pixels), feathered 2 px at the edges; text = brightest 4 %, glow = 60-90 %.
        reg = rgb[y0:y1, x0:x1].reshape(-1, 3); Lr = reg.sum(-1)
        fillc = np.median(reg[Lr <= np.percentile(Lr, 25)], 0)
        tcol = np.mean(reg[Lr >= np.percentile(Lr, 96)], 0) if color is None else np.array(color, np.float32)
        gsel = reg[(Lr >= np.percentile(Lr, 60)) & (Lr <= np.percentile(Lr, 90))]
        gcol = np.median(gsel, 0) if len(gsel) else None
        if gcol is not None and gcol.sum() < fillc.sum() + 40:
            gcol = None
        wgt = np.zeros((H, W), np.float32); wgt[max(0, y0 - 2):y1 + 2, max(0, x0 - 2):x1 + 2] = 1.0
        wgt = cv2.blur(wgt, (5, 5)); wgt[y0:y1, x0:x1] = 1.0; wgt *= a      # full inside, feathered outside
        if keep_lines:
            wgt[lines] = 0
        canvas = rgb * (1 - wgt[..., None]) + fillc * wgt[..., None]
        m = (wgt > 0).astype(np.uint8) * 255
    else:
        canvas = None
    m = (inside & (dist > thr) & ~lines).astype(np.uint8) * 255 if canvas is None else m
    m = cv2.dilate(m, np.ones((3, 3), np.uint8))
    m &= (a.astype(np.uint8) * 255)
    m[lines] = 0
    if canvas is None:
        img8 = rgb.astype(np.uint8)[..., ::-1].copy()
        fillc0 = fill
        fill = cv2.inpaint(img8, m, 3, cv2.INPAINT_TELEA)[..., ::-1].astype(np.float32)
        # where the background ring is nearly flat, a flat fill looks cleaner than inpainting
        if ring.sum() > 4 and np.abs(rgb[ring] - bg).sum(-1).mean() < 18:
            fill[m > 0] = bg
        if fillc0 is not None:
            fillc = fillc0
            fill = np.zeros_like(rgb); fill[:] = fillc
        canvas = rgb.copy(); canvas[m > 0] = fill[m > 0]
    # Chinese text mask
    if not text:
        changed = (np.abs(canvas - rgb).sum(-1) > 0.5) & a
        pix[changed] = p565(canvas[changed]); return True
    small = bw if vertical else bh
    use_ttf = bool(force_ttf)
    if vertical:
        tm = bitmap_mask(text, lang, bold=False, vertical=True)
    elif use_ttf:
        px = px or max(12, int(bh * 1.05))
        tm = ttf_mask(text, lang, px)
        while tm.shape[1] > W - 4 and px > 11:
            px -= 1; tm = ttf_mask(text, lang, px)
    else:
        tm = bitmap_mask(text, lang, bold=False)
    if tm.shape[0] > H or tm.shape[1] > W:
        oy = max(0, (tm.shape[0] - H) // 2); tm = tm[oy:oy + H, :W]
    th, tw = tm.shape
    cx = x + bw / 2.0; cy = y + bh / 2.0
    if align == 'auto':
        align = 'center' if (vertical or abs(cx - W / 2.0) < max(4, W * 0.08)) else 'left'
    tx = int(round(cx - tw / 2.0)) if align == 'center' else x
    tx = max(1, min(tx, W - tw - 1)); ty = int(round(cy - th / 2.0)); ty = max(0, min(ty, H - th))
    sub = (slice(ty, ty + th), slice(tx, tx + tw))
    region_a = a[sub]
    if gcol is not None:
        gm = cv2.dilate((tm > 0.3).astype(np.uint8), np.ones((3, 3), np.uint8)).astype(np.float32) * 0.55
        gm = np.maximum(gm, 0) * region_a
        canvas[sub] = canvas[sub] * (1 - gm[..., None]) + gcol * gm[..., None]
    tmm = tm * region_a
    canvas[sub] = canvas[sub] * (1 - tmm[..., None]) + tcol * tmm[..., None]
    canvas[lines] = rgb[lines]
    changed = (np.abs(canvas - rgb).sum(-1) > 0.5) & a
    pix[changed] = p565(canvas[changed])
    return True
