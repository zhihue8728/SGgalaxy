"""Strategic-map province shapes -> direction of the SHARED BORDER CENTRE of every pair of neighbours
(user 2026-10-24 18:30: a province's gate to B sits in the direction of the centre of the A/B border).
The client draws the strategic map from nb%02d%02d.xpf / ns%02d%02d.xpf (CCRR, FUN_00463f20): every image is anchored at
the map origin, so its opaque pixels are the province at its absolute position.
border_dirs(NTF2.dat) -> {(A, B): (dx, dy)} unit vector from A's centroid to the centre of the A/B border
(x right, y down on the strategic map)."""
import os, sys, re, math
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import numpy as np
import sgdat, xpf

def shapes(ntf2, prefix="nb"):
    d = open(ntf2, "rb").read()
    out = {}
    for n, o, s in sgdat.read_index(d):
        m = re.match(prefix + r"(\d{4})\.xpf$", n, re.I)
        if m:
            im = xpf.frame(d[o:o + s], 0)
            a = np.array(im)[:, :, 3] > 0
            out[int(m.group(1))] = a
    return out

def border_dirs(ntf2, prefix="nb", reach=3):
    sh = shapes(ntf2, prefix)
    H = max(a.shape[0] for a in sh.values()); W = max(a.shape[1] for a in sh.values())
    full = {}
    for p, a in sh.items():
        f = np.zeros((H, W), bool); f[:a.shape[0], :a.shape[1]] = a; full[p] = f
    def dil(f, r):
        g = f.copy()
        for dy in range(-r, r + 1):
            for dx in range(-r, r + 1):
                if dx * dx + dy * dy <= r * r:
                    g |= np.roll(np.roll(f, dy, 0), dx, 1)
        return g
    dl = {p: dil(f, reach) for p, f in full.items()}
    cen = {p: (np.argwhere(f)[:, 1].mean(), np.argwhere(f)[:, 0].mean()) for p, f in full.items()}
    out, centre = {}, {}
    for a in full:
        for b in full:
            if a == b:
                continue
            m = full[a] & dl[b]
            if m.sum() < 3:
                continue
            ys, xs = np.nonzero(m)
            bx, by = xs.mean(), ys.mean()
            dx, dy = bx - cen[a][0], by - cen[a][1]
            n = math.hypot(dx, dy) or 1.0
            out[(a, b)] = (dx / n, dy / n)
            centre[(a, b)] = (bx, by)
    return out, cen, centre

if __name__ == "__main__":
    dirs, cen, centre = border_dirs(sys.argv[1])
    for p in (0, 800, 8, 808, 404):
        print(p, "centroid", tuple(round(v) for v in cen[p]))
        for (a, b), v in sorted(dirs.items()):
            if a == p:
                print("   ->", b, "dir", tuple(round(x, 2) for x in v), "border centre", tuple(round(x) for x in centre[(a, b)]),
                      "angle", round(math.degrees(math.atan2(v[1], v[0]))))
