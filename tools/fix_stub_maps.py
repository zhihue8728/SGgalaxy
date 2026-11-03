#!/usr/bin/env python3
"""Replace the 10 blocked placeholder maps of pam.dat (col 8 = 000008RR, and 00000008 = col 0 row 8) with playable ones.
The original game has 8x8 planets: these files are 95% blocked stubs.  Our 9x9 layout uses them for the corner capitals
(00000800 / 00000008 / 00000808) and the neutral provinces 00000801-00000807, so heroes could not walk to the portals.
Capital stubs get the cells of 00000000.nm (the real capital overlay); province stubs get the cells of 0000070R.nm.
Every portal rectangle (source side) and arrival point (target side) of portals.por that touches such a province is carved
open and connected to the main free area.
usage: fix_stub_maps.py PAM.dat OUT.dat PORTALS.por"""
import struct, sys, os, collections
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import sgdat, sgdat_add
CAPS = {"00000800", "00000008", "00000808"}
STUBS = sorted(CAPS)   # only the capital overlays: named province maps (a1-dr.nm ...) come from the vinu table, 000008RR are unused
def por_records(path):
    d = open(path, "rb").read(); n = struct.unpack_from("<I", d, 0)[0]; v = struct.unpack("<%di" % (len(d) // 4), d)
    tb = {1: 10, 2: 7, 14: 6}; o = 1; out = []
    for _ in range(n):
        out.append(v[o:o + tb[v[o]]]); o += tb[v[o]]
    return [r for r in out if r[0] == 1]
def parse(b):
    w, h = struct.unpack_from("<HH", b, 1); p = 5
    tiles = [b[p + 3 * i:p + 3 * i + 3] for i in range(w * h)]
    q = p + 3 * w * h; n = struct.unpack_from("<H", b, q)[0]
    return w, h, [bytearray(t) for t in tiles], b[q:q + 2 + 4 * n]
def build(w, h, tiles, objs):
    return bytes([1]) + struct.pack("<HH", w, h) + b"".join(bytes(t) for t in tiles) + objs
def main():
    pam, out, por = sys.argv[1:4]
    d = open(pam, "rb").read(); idx = {n.lower(): d[o:o + s] for n, o, s in sgdat.read_index(d)}
    recs = por_records(por)
    need = collections.defaultdict(list)             # "0000CCRR" -> [(x, y, w, h)] areas to open
    for r in recs:
        src, dst = r[1] % 100000, r[6] % 100000
        if r[6] >= 210000 and (r[6] // 10000) % 10 != 0: continue
        for pid, area in ((src, (r[2] - 1, r[3] - 1, r[4] + 2, r[5] + 2)), (dst, (r[7] - 2, r[8] - 2, 5, 5))):
            need["%08d" % pid].append(area)
    tmp = os.path.join(os.path.dirname(os.path.abspath(out)) or ".", "_stubmaps"); os.makedirs(tmp, exist_ok=True)
    files = []
    for name in STUBS:
        donor = "00000000" if name in CAPS else "0000070" + name[-1]
        dw, dh, tiles, _ = parse(idx[donor + ".nm"])
        _, _, _, objs = parse(idx[name + ".nm"]) if name in CAPS else parse(idx[donor + ".nm"])
        w, h = dw, dh
        areas = need.get(name, [])
        if name in CAPS:                              # capital overlay: keep the real map's cells everywhere
            pass
        for (x, y, aw, ah) in areas:
            for j in range(max(0, y), min(h, y + ah)):
                for i in range(max(0, x), min(w, x + aw)):
                    tiles[j * w + i][2] &= ~0x21
        # connectivity: every opened cell must reach the biggest free component (carve straight lines otherwise)
        free = lambda i, j: 0 <= i < w and 0 <= j < h and not tiles[j * w + i][2] & 0x21
        comp = {}; sizes = []
        for j in range(h):
            for i in range(w):
                if free(i, j) and (i, j) not in comp:
                    k = len(sizes); st = [(i, j)]; comp[(i, j)] = k; n = 0
                    while st:
                        a, b2 = st.pop(); n += 1
                        for da in (-1, 0, 1):
                            for db in (-1, 0, 1):
                                c = (a + da, b2 + db)
                                if free(*c) and c not in comp: comp[c] = k; st.append(c)
                    sizes.append(n)
        main_k = max(range(len(sizes)), key=lambda k: sizes[k])
        mainc = [c for c, k in comp.items() if k == main_k]
        fixed = 0
        for (x, y, aw, ah) in areas:
            cx, cy = min(max(x + aw // 2, 0), w - 1), min(max(y + ah // 2, 0), h - 1)
            if comp.get((cx, cy)) == main_k: continue
            tx, ty = min(mainc, key=lambda c: abs(c[0] - cx) + abs(c[1] - cy))
            i, j = cx, cy
            while (i, j) != (tx, ty):
                for dj in (0, 1):
                    for di in (0, 1):
                        if 0 <= j + dj < h and 0 <= i + di < w: tiles[(j + dj) * w + i + di][2] &= ~0x21
                i += (tx > i) - (tx < i); j += (ty > j) - (ty < j)
            fixed += 1
        data = build(w, h, tiles, objs)
        p = os.path.join(tmp, name + ".nm"); open(p, "wb").write(data); files.append(p)
        print(f"{name}: donor {donor}, {len(areas)} areas opened, {fixed} corridors, {len(data)} bytes")
    print(sgdat_add.add(pam, out, files))
if __name__ == "__main__":
    main()
