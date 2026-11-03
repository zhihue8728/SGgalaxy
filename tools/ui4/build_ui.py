"""i18n phase 4: redraw the English captions painted into UI sprites (NTF2.dat / NTFB.dat) in Chinese.
Spec: ui_labels.py  LABELS = {sprite: [(rect or None, '繁體', opts), ...]}
  rect = (x, y, w, h) approximate area that holds ONE English caption (None = the whole frame minus its border);
  the caption's exact box is found inside it (pixels clearly brighter than the area's border colour).
  opts: dict(frames=[...], vertical=True, ttf=True/False, align='center'|'left', color=(r,g,b))
Simplified = OpenCC tw2sp of the Traditional text (or opts['cn']).
usage: build_ui.py [preview|build] [sprite ...]"""
import sys, io, numpy as np, cv2
from PIL import Image
import opencc
import xcodec, relabel, dat
from sheet import E, frames
from ui_labels import LABELS

T2S = opencc.OpenCC('tw2sp')


def refine(pix, a, rect):
    H, W = a.shape
    if rect is None:
        m = 3; rect = (m, m, W - 2 * m, H - 2 * m)
    x, y, w, h = rect
    x0, y0, x1, y1 = max(0, x), max(0, y), min(W, x + w), min(H, y + h)
    rgb = relabel.rgb_of(pix).astype(np.int32)
    g = rgb.max(-1)
    sub = g[y0:y1, x0:x1]; asub = a[y0:y1, x0:x1]
    if sub.size == 0: return None
    border = np.concatenate([sub[0], sub[-1], sub[:, 0], sub[:, -1]])
    ref = np.median(border) if len(border) else 0
    t = (sub > ref + 50) & asub
    # drop long straight lines (the frame of a button)
    t8 = t.astype(np.uint8)
    hl = cv2.morphologyEx(t8, cv2.MORPH_OPEN, np.ones((1, max(12, (x1 - x0) * 3 // 4)), np.uint8))
    vl = cv2.morphologyEx(t8, cv2.MORPH_OPEN, np.ones((max(10, (y1 - y0) * 3 // 4), 1), np.uint8))
    t = t & ~(hl > 0) & ~(vl > 0)
    ys, xs = np.where(t)
    if len(xs) < 4:
        return None
    return (x0 + int(xs.min()), y0 + int(ys.min()), int(xs.max() - xs.min() + 1), int(ys.max() - ys.min() + 1))


BOXCACHE = {}
def apply_label(pix, a, rect, text, lang, opts, key=None):
    box = tuple(rect) if opts.get('exact') else (BOXCACHE.get(key) or refine(pix, a, rect))
    if key is not None and box is not None: BOXCACHE.setdefault(key, box)
    if box is None:
        return False
    return relabel.relabel(pix, a, box, text, lang, align=opts.get('align', 'auto'),
                           force_ttf=opts.get('ttf'), color=opts.get('color'),
                           vertical=opts.get('vertical', False), fill=opts.get('fill'), pad=opts.get('pad', 2), thr=opts.get('thr', 25), px=opts.get('px'), keep_lines=opts.get('keep_lines', True), hl=opts.get('hl', False))


def process(nm, lang):
    """-> new sprite bytes and the list of (frame, pix, a) after editing"""
    b = E[nm]; out = []
    if nm.lower().endswith('.jpg'):
        im = np.asarray(Image.open(io.BytesIO(b)).convert('RGB')).astype(np.int32)
        pix = relabel.p565(im); a = np.ones(pix.shape, bool)
        for li, (rect, tw, *o) in enumerate(LABELS[nm]):
            o = o[0] if o else {}
            apply_label(pix, a, rect, tw if lang == 'tw' else o.get('cn', T2S.convert(tw)), lang, o, key=(nm, li, 0))
        rgb = relabel.rgb_of(pix).astype(np.uint8)
        bio = io.BytesIO(); Image.fromarray(rgb).save(bio, 'JPEG', quality=93)
        return bio.getvalue(), [(0, pix, a)]
    w, h, offs = xcodec.frames_meta(b)
    new = {}
    seen = set()
    for k, o in enumerate(offs):
        if o in seen or o + 2 >= len(b): continue
        seen.add(o)
        pix, a, _ = xcodec.decode(b, o, w, h)
        if not a.any(): continue
        changed = False
        for li, (rect, tw, *opt) in enumerate(LABELS[nm]):
            opt = opt[0] if opt else {}
            if 'frames' in opt and k not in opt['frames']: continue
            txt = tw if lang == 'tw' else opt.get('cn', T2S.convert(tw))
            changed |= bool(apply_label(pix, a, rect, txt, lang, opt, key=(nm, li, opt.get('group', 0))))
        if changed:
            new[o] = xcodec.encode(pix, a); out.append((k, pix, a))
    return xcodec.rebuild(b, new), out


if __name__ == '__main__':
    mode = sys.argv[1]; names = sys.argv[2:] or list(LABELS)
    if mode == 'preview':
        import boxes
        items = []
        for nm in names:
            for k, pix, a in process(nm, 'tw')[1][:4]:
                items.append((f'{nm}#{k}', pix, a, []))
        print(boxes.preview(items, 'view/after.png', scale=int(__import__('os').environ.get('SC','2'))))
    elif mode == 'build':
        import os
        for lang in ('tw', 'cn'):
            os.makedirs(f'out/{lang}', exist_ok=True)
            for nm in names:
                data, _ = process(nm, lang)
                open(f'out/{lang}/{nm}', 'wb').write(data)
            print(lang, len(names))
        import fix_f4_colon            # 2026-10-22: F4 '轉生' colon aligned with '榮譽' (art post-fix)
        for lang in ('tw', 'cn'):
            for nm in ('f4-bk-mi.xpf', 'f4-bk-nm.xpf'):
                if os.path.exists(f'out/{lang}/{nm}'):
                    print(lang, fix_f4_colon.fix(f'out/{lang}/{nm}'))
