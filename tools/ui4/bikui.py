"""i18n phase 4b: Chinese captions in the UI Bink clips (odv.dat *.bik), re-encoded with binkenc.py (lossless).
Spec (bik_labels.py): CLIPS = {clip: dict(mode=..., labels=[...], ref=frame)}
  mode 'static' : captions stay at the same place in every frame (button states / hover glow) -> relabel every frame.
  mode 'track'  : captions slide / are revealed; they are redrawn on the reference frame (where they are complete), and
                  every frame takes the redrawn pixels where it shows the reference (best horizontal/vertical shift).
  mode 'rot'    : rotated captions (deploy screen): labels = (cx, cy, w, h, angle, text, opts) in clip pixels.
labels for static/track: (rect, '繁體', opts) exactly like ui_labels.py (rect in clip pixels)."""
import numpy as np, cv2
from PIL import Image, ImageDraw, ImageFont
import opencc
import relabel, binkenc, binkrt
from build_ui import refine

T2S = opencc.OpenCC('tw2sp')


def to_rgb(fr):
    Y, U, V = fr
    return binkenc.yuv_to_rgb(Y, U, V)


def apply_rect_labels(rgb, labels, lang, cache, key):
    """rgb uint8 [h,w,3] -> new rgb (only changed pixels differ)."""
    pix = relabel.p565(rgb.astype(np.int32)); a = np.ones(pix.shape, bool); before = pix.copy()
    for li, (rect, tw, *o) in enumerate(labels):
        o = o[0] if o else {}
        txt = tw if lang == 'tw' else o.get('cn', T2S.convert(tw))
        if o.get('exact'):
            box = tuple(rect)
        else:
            box = cache.get((key, li)) or refine(pix, a, rect)
            if box is None: continue
            cache.setdefault((key, li), box)
        relabel.relabel(pix, a, box, txt, lang, align=o.get('align', 'auto'), force_ttf=o.get('ttf'),
                        color=o.get('color'), vertical=o.get('vertical', False), fill=o.get('fill'),
                        pad=o.get('pad', 2), thr=o.get('thr', 25), px=o.get('px'), keep_lines=o.get('keep_lines', True), hl=o.get('hl', False))
    out = rgb.copy(); ch = pix != before
    out[ch] = relabel.rgb_of(pix[ch]).astype(np.uint8)
    return out


TTF = relabel.TTF; TTF_INDEX = relabel.TTF_INDEX


def text_alpha(text, lang, w, h, px=None):
    """anti-aliased multi-line text fitted into w x h -> float alpha [H, W] (may be a bit smaller)"""
    lines = text.split('\n')
    size = px or max(8, int(h / len(lines) * 0.95))
    while True:
        f = ImageFont.truetype(TTF, size, index=TTF_INDEX[lang])
        boxes = [f.getbbox(l) for l in lines]
        lw = max(b[2] - b[0] for b in boxes); lh = size
        th = lh * len(lines) + (len(lines) - 1) * max(1, size // 8)
        if (lw <= w and th <= h) or size <= 8: break
        size -= 1
    im = Image.new('L', (lw + 4, th + 4)); d = ImageDraw.Draw(im); y = 2
    for l, b in zip(lines, boxes):
        d.text((2 + (lw - (b[2] - b[0])) // 2 - b[0], y - f.getbbox('國')[1]), l, font=f, fill=255)
        y += lh + max(1, size // 8)
    return np.asarray(im).astype(np.float32) / 255.0


def rot_label(rgb, cx, cy, w, h, ang, text, lang, o=None):
    o = o or {}
    H, W = rgb.shape[:2]
    pad = o.get('pad', 3)
    rect = ((cx, cy), (w + 2 * pad, h + 2 * pad), -ang)
    poly = cv2.boxPoints(rect).astype(np.int32)
    M = np.zeros((H, W), np.uint8); cv2.fillPoly(M, [poly], 1)
    ring = cv2.dilate(M, np.ones((5, 5), np.uint8)) - M
    f = rgb.astype(np.float32)
    if ring.sum() < 4 or M.sum() < 4: return rgb
    bg = np.median(f[ring > 0], 0)
    dist = np.abs(f - bg).sum(-1)
    thr = o.get('thr', 28)
    gray = cv2.cvtColor(rgb, cv2.COLOR_RGB2GRAY).astype(np.int32)
    loc = cv2.medianBlur(rgb_gray := gray.astype(np.uint8), 11).astype(np.int32)
    txt = (M > 0) & (((gray - loc) > thr) | (o.get('both', False) & ((loc - gray) > thr)))
    if txt.sum() < 3: return rgb
    lum = f[txt].sum(-1)
    tcol = np.median(f[txt][lum >= np.percentile(lum, 70)], 0) if o.get('color') is None else np.array(o['color'], np.float32)
    em = cv2.dilate(txt.astype(np.uint8) * 255, np.ones((3, 3), np.uint8)) * (M > 0)
    em = em.astype(np.uint8)
    out = cv2.inpaint(rgb[..., ::-1].copy(), em, 2, cv2.INPAINT_TELEA)[..., ::-1].astype(np.float32)
    if o.get('fill') is not None:
        out[em > 0] = np.array(o['fill'], np.float32)
    al = text_alpha(text, lang, int(w), int(h), o.get('px'))
    th, tw = al.shape
    A = cv2.getRotationMatrix2D((tw / 2.0, th / 2.0), ang, 1.0)
    A[0, 2] += cx - tw / 2.0; A[1, 2] += cy - th / 2.0
    aw = cv2.warpAffine(al, A, (W, H), flags=cv2.INTER_LINEAR)
    if o.get('glow', True):
        g = cv2.GaussianBlur(aw, (0, 0), 1.2) * 0.6
        gcol = tcol * 0.55
        out = out * (1 - g[..., None]) + gcol * g[..., None]
    out = out * (1 - aw[..., None]) + tcol * aw[..., None]
    return np.clip(np.round(out), 0, 255).astype(np.uint8)


def apply_rot_labels(rgb, labels, lang):
    for (cx, cy, w, h, ang, tw, *o) in labels:
        o = o[0] if o else {}
        txt = tw if lang == 'tw' else o.get('cn', T2S.convert(tw))
        rgb = rot_label(rgb, cx, cy, w, h, ang, txt, lang, o)
    return rgb


def track(frames_rgb, ref_i, ref_new, labels_mask, max_shift=400, tol=30, shifts_only=False, dyr=0):
    DYR = range(-dyr, dyr + 1)
    """take ref_new pixels where a frame shows the reference (searching the best shift)."""
    ref = frames_rgb[ref_i].astype(np.int32); H, W = ref.shape[:2]
    ys, xs = np.where(labels_mask)
    if len(xs) == 0: return frames_rgb
    y0, y1, x0, x1 = ys.min(), ys.max() + 1, xs.min(), xs.max() + 1
    out = []
    for f in frames_rgb:
        fi = f.astype(np.int32); best = None
        for dy in DYR:
            for dx in range(-min(W, max_shift), min(W, max_shift) + 1):
                ax0, ax1 = max(0, x0 + dx), min(W, x1 + dx); ay0, ay1 = max(0, y0 + dy), min(H, y1 + dy)
                if ax1 - ax0 < 4 or ay1 - ay0 < 2: continue
                a = fi[ay0:ay1, ax0:ax1]; r = ref[ay0 - dy:ay1 - dy, ax0 - dx:ax1 - dx]
                m = labels_mask[ay0 - dy:ay1 - dy, ax0 - dx:ax1 - dx]
                if m.sum() < 8: continue
                e = np.abs(a - r).sum(-1)[m].mean()
                if best is None or e < best[0]: best = (e, dx, dy)
        if shifts_only:
            out.append(best); continue
        g = f.copy()
        if best is not None and best[0] < 60:
            _, dx, dy = best
            for y in range(max(0, y0 + dy), min(H, y1 + dy)):
                sx0, sx1 = max(0, x0 + dx), min(W, x1 + dx)
                a = fi[y, sx0:sx1]; r = ref[y - dy, sx0 - dx:sx1 - dx]; nw = ref_new[y - dy, sx0 - dx:sx1 - dx]
                m = labels_mask[y - dy, sx0 - dx:sx1 - dx] & (np.abs(a - r).sum(-1) < tol)
                g[y, sx0:sx1][m] = nw[m]
        out.append(g)
    return out


def rgb_frames_to_yuv(orig, new_rgb, old_rgb):
    """keep the decoded YUV where nothing changed."""
    out = []
    for (Y, U, V), n, o in zip(orig, new_rgb, old_rgb):
        ch = (np.abs(n.astype(np.int32) - o.astype(np.int32)).sum(-1) > 0)
        if not ch.any():
            out.append((Y, U, V)); continue
        y2, u2, v2 = binkenc.rgb_to_yuv(n)
        Y = Y.copy(); U = U.copy(); V = V.copy()
        Y[ch] = y2[ch]
        h, w = ch.shape; ch2 = np.zeros(U.shape, bool)
        hh, ww = (h // 2) * 2, (w // 2) * 2
        blk = ch[:hh, :ww].reshape(hh // 2, 2, ww // 2, 2).any((1, 3)); ch2[:hh // 2, :ww // 2] = blk
        if h % 2: ch2[-1, :ww // 2] |= ch[-1, :ww].reshape(-1, 2).any(1)
        if w % 2: ch2[:hh // 2, -1] |= ch[:hh, -1].reshape(-1, 2).any(1)
        # chroma = average of the 2x2 new pixels
        pad = np.pad(n.astype(np.float64), ((0, h % 2), (0, w % 2), (0, 0)), mode='edge')
        avg = pad.reshape(pad.shape[0] // 2, 2, pad.shape[1] // 2, 2, 3).mean((1, 3))
        _, ua, va = binkenc.rgb_to_yuv(avg)
        U[ch2] = ua[ch2]; V[ch2] = va[ch2]
        out.append((Y, U, V))
    return out


def process_clip(path, spec, lang, cache):
    orig = binkrt.decode(path)
    rgbs = [to_rgb(f) for f in orig]
    mode = spec['mode']; key = path.split('/')[-1]
    if mode == 'static':
        # labels may name the frames they apply to (opts frames=[...]): normal vs highlighted button states
        new = [apply_rect_labels(r, [l for l in spec['labels'] if i in ((l[2] if len(l) > 2 else {}).get('frames') or [i])],
                                 lang, cache, key) for i, r in enumerate(rgbs)]
    elif mode == 'rot':
        import dp_labels
        H, W = rgbs[0].shape[:2]
        labs = spec.get('labels') or dp_labels.clip_labels(spec['dpkey'], W, H)
        new = [apply_rot_labels(r, labs, lang) for r in rgbs]
    elif mode == 'track':
        ri = spec.get('ref', len(rgbs) - 1)
        if spec.get('rot'):
            ref_new = apply_rot_labels(rgbs[ri], spec['labels'], lang)
        else:
            ref_new = apply_rect_labels(rgbs[ri], spec['labels'], lang, cache, key)
        mask = np.abs(ref_new.astype(np.int32) - rgbs[ri].astype(np.int32)).sum(-1) > 0
        mask = cv2.dilate(mask.astype(np.uint8), np.ones((3, 3), np.uint8)) > 0
        new = track(rgbs, ri, ref_new, mask, spec.get('max_shift', 400), dyr=spec.get('dyr', 0))
        new[ri] = ref_new
    elif mode == 'freeze':
        ri = spec.get('ref', len(rgbs) - 1) % len(rgbs)
        ref_new = apply_rect_labels(rgbs[ri], spec['labels'], lang, cache, key) if spec['labels'] else rgbs[ri]
        new = [ref_new.copy() for _ in rgbs]
    elif mode == 'labeltrack':
        new = process_labeltrack(rgbs, spec, lang)
    elif mode == 'trackbox':
        ri = spec.get('ref', len(rgbs) - 1)
        ref_new = apply_rect_labels(rgbs[ri], spec['labels'], lang, cache, key)
        mask = np.zeros(rgbs[ri].shape[:2], bool)
        for (r, *_x) in spec['labels']:
            x, y, w, h = r; mask[y:y + h, x:x + w] = True
        sh = track(rgbs, ri, ref_new, mask, spec.get('max_shift', 40), shifts_only=True, dyr=spec.get('dyr', 4))
        new = []
        for i, (r, b) in enumerate(zip(rgbs, sh)):
            if i == ri: new.append(ref_new); continue
            dx, dy = (b[1], b[2]) if b is not None else (0, 0)
            labs = [((x + dx, y + dy, w, h), t, *o) for ((x, y, w, h), t, *o) in spec['labels']]
            new.append(apply_rect_labels(r, labs, lang, {}, None))
    yuv = rgb_frames_to_yuv(orig, new, rgbs)
    return yuv, new


def label_shift(f, ref, box, maxs, dyr, margin=2):
    """best (score, dx, dy) placing ref's box region onto frame f (normalized correlation of luminance)"""
    H, W = ref.shape[:2]; x, y, w, h = box
    x0, y0, x1, y1 = max(0, x - margin), max(0, y - margin), min(W, x + w + margin), min(H, y + h + margin)
    g = lambda im: cv2.cvtColor(im, cv2.COLOR_RGB2GRAY).astype(np.float32)
    T = g(ref)[y0:y1, x0:x1]
    sx0, sy0 = max(0, x0 - maxs), max(0, y0 - dyr); sx1, sy1 = min(W, x1 + maxs), min(H, y1 + dyr)
    S = g(f)[sy0:sy1, sx0:sx1]
    if S.shape[0] < T.shape[0] or S.shape[1] < T.shape[1] or T.std() < 1: return None
    r = cv2.matchTemplate(S, T, cv2.TM_CCOEFF_NORMED)
    _, mx, _, loc = cv2.minMaxLoc(r)
    return (mx, sx0 + loc[0] - x0, sy0 + loc[1] - y0)


def process_labeltrack(rgbs, spec, lang):
    ri = spec.get('ref', len(rgbs) - 1); ref = rgbs[ri]
    maxs = spec.get('max_shift', 200); dyr = spec.get('dyr', 0); thr = spec.get('match', 0.6)
    out = []
    for i, f in enumerate(rgbs):
        labs = []
        for (box, t, *o) in spec['labels']:
            if i == ri:
                labs.append((box, t, *o)); continue
            b = label_shift(f, ref, box, maxs, dyr)
            if b is not None and b[0] > thr:
                x, y, w, h = box; labs.append(((x + b[1], y + b[2], w, h), t, *o))
        out.append(apply_rect_labels(f, labs, lang, {}, None) if labs else f)
    return out


def marquee(path, text, lang, px=11):
    """dp-bk-ts.bik: red LED text scrolling along the tower band -> same motion with the Chinese text."""
    orig = binkrt.decode(path)
    rg = [to_rgb(f) for f in orig]
    fl = [r.astype(np.float32) for r in rg]
    red = [np.clip(r[..., 0] - np.maximum(r[..., 1], r[..., 2]) - 40, 0, 255) for r in fl]
    steps = [0.0]
    for i in range(len(red) - 1):
        (dx, dy), resp = cv2.phaseCorrelate(red[i], red[i + 1])
        steps.append(dx if dx < -2 and resp > 0.2 else 0.0)
    cum = np.cumsum(steps)                        # negative: scrolling left
    allred = np.concatenate([fl[i][red[i] > 30] for i in range(len(fl))])
    lum = allred.sum(-1); col = np.median(allred[lum >= np.percentile(lum, 70)], 0)
    # band centre line from all frames' red pixels
    ys, xs = np.where(np.max(np.stack(red), 0) > 30)
    k, b = np.polyfit(xs, ys, 1); ang = -np.degrees(np.arctan(k))
    f = ImageFont.truetype(TTF, px, index=TTF_INDEX[lang])
    l, t, r_, bt = f.getbbox(text); tw = r_ - l; P = tw + 40
    strip = Image.new('L', (tw + 4, px + 4)); ImageDraw.Draw(strip).text((2 - l, 2 - t), text, font=f, fill=255)
    al0 = np.asarray(strip).astype(np.float32) / 255
    out = []
    H, W = rg[0].shape[:2]
    for i, rgb in enumerate(rg):
        m = cv2.dilate((red[i] > 20).astype(np.uint8) * 255, np.ones((3, 3), np.uint8))
        o = cv2.inpaint(rgb[..., ::-1].copy(), m, 3, cv2.INPAINT_TELEA)[..., ::-1].astype(np.float32)
        x0 = W - ((-cum[i]) % P)
        for xs0 in (x0 - P, x0, x0 + P):
            cx = xs0 + tw / 2.0; cy = k * cx + b
            A = cv2.getRotationMatrix2D((al0.shape[1] / 2.0, al0.shape[0] / 2.0), ang, 1.0)
            A[0, 2] += cx - al0.shape[1] / 2.0; A[1, 2] += cy - al0.shape[0] / 2.0
            aw = cv2.warpAffine(al0, A, (W, H))
            o = o * (1 - aw[..., None]) + col * aw[..., None]
        out.append(np.clip(np.round(o), 0, 255).astype(np.uint8))
    return orig, rg, out
