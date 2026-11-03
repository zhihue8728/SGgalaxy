"""2026-10-22 12:18 (user): the Lab view tabs must look exactly like the translated slide-in strip and must not
animate; the selected / hovered tab is just brighter.  After iu-3b-si.bik ends the client draws the three button
sprites iu-b-su / iu-b-vs / iu-b-sl (4 frames each) over the strip -> rebuild every frame from the translated
strip (last frame of out/bik/<lang>/iu-3b-si.bik) cut at the sprite's place (template-matched: x 0 / 76 / 149),
keeping the sprite's own alpha.  Frames 0, 2 = normal, 1, 3 = bright text."""
import numpy as np, xcodec, relabel, binkrt, bikui
from sheet import E
POS = {'iu-b-su.xpf': 0, 'iu-b-vs.xpf': 76, 'iu-b-sl.xpf': 149}

def build(lang):
    fin = bikui.to_rgb(binkrt.decode(f'out/bik/{lang}/iu-3b-si.bik')[-1]).astype(np.float32)
    out = {}
    for nm, dx in POS.items():
        b = E[nm]; w, h, offs = xcodec.frames_meta(b)
        new = {}
        for k, o in enumerate(offs):
            if o >= len(b) or o in new:
                continue
            pix0, a, _ = xcodec.decode(b, o, w, h)
            org = relabel.rgb_of(pix0).astype(np.float32)
            crop = org.copy()
            hh = min(h, fin.shape[0]); ww = min(w, fin.shape[1] - dx)
            crop[:hh, :ww] = fin[:hh, dx:dx + ww]
            if k in (1, 3):
                L = crop.max(-1)
                txt = np.zeros(L.shape, bool); txt[3:15, 6:w - 6] = True
                txt &= L > 110
                crop[txt] = np.clip(crop[txt] * 1.45 + np.array([0, 25, 30]), 0, 255)
            new[o] = xcodec.encode(relabel.p565(crop.astype(np.int32)), a)
        out[nm] = xcodec.rebuild(b, new)
    return out

if __name__ == '__main__':
    import os
    for lang in ('tw', 'cn'):
        for nm, data in build(lang).items():
            open(f'out/{lang}/{nm}', 'wb').write(data)
        print(lang, 'ok')
