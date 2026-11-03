#!/usr/bin/env python3
"""Alien spawn spots for every map aliens can appear on (layout-2 province maps + mon1/mon2/mon3 hunting grounds +
cave1): walkable for a hero-size unit (2x2, flag 0x01 = blocked), >= 3 cells from any wall, CONNECTED (4-neighbour)
to the map's entry points (portal rects / arrival points of portals.por), spread by farthest-point sampling.
Output: server/spawn_spots.json  {map name: [[x_px, y_px], ...]} (cell*32+16).
usage: gen_spawn_spots.py PAM.dat PAM3.dat PORTALS.por VINU.tsv OUT.json"""
import sys, os, struct, json, collections
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import sgdat, fix_portals as F
N_SPOTS = 40
def main():
    pam, pam3, por, tsv, out = sys.argv[1:6]
    files = {}
    for p in (pam, pam3):
        d = open(p, "rb").read()
        for n, o, s in sgdat.read_index(d):
            if n.lower().endswith(".nm"): files[n.lower()[:-3]] = d[o:o + s]
    recs = [r for r in F.parse(open(por, "rb").read()) if r[0] == 1]
    vin = {}
    for ln in open(tsv, encoding="utf-8").read().splitlines()[1:]:
        f = ln.split("\t")
        if f[1] == "2": vin[int(f[0]) % 100000] = f[5].lower().replace(".nm", "")
    entries = collections.defaultdict(list)
    for r in recs:
        if r[1] // 100000 != 2: continue
        k = (r[1] // 10000) % 10
        src = vin.get(r[1] % 100000) if k == 0 else (f"mon{k}" if k in (1, 2, 3) else None)
        if src: entries[src].append((r[2] + 1, r[3] + 1))
        k2 = (r[6] // 10000) % 10
        dst = vin.get(r[6] % 100000) if k2 == 0 else (f"mon{k2}" if k2 in (1, 2, 3) else None)
        if dst: entries[dst].append((r[7], r[8]))
    res = {}
    for name in sorted(set(vin.values()) | {"mon1", "mon2", "mon3", "cave1"}):
        b = files.get(name)
        if b is None: print("missing", name); continue
        w, h = struct.unpack_from("<HH", b, 1)
        blk = [b[5 + 3 * i + 2] & 1 for i in range(w * h)]
        free = lambda x, y: 0 <= x < w - 1 and 0 <= y < h - 1 and not (blk[y*w+x] | blk[y*w+x+1] | blk[(y+1)*w+x] | blk[(y+1)*w+x+1])
        # wall distance (chebyshev) by multi-source BFS
        dist = [99] * (w * h); dq = collections.deque()
        for y in range(h):
            for x in range(w):
                if blk[y*w+x] or x in (0, w-1) or y in (0, h-1): dist[y*w+x] = 0; dq.append((x, y))
        while dq:
            x, y = dq.popleft(); dv = dist[y*w+x]
            for dx in (-1, 0, 1):
                for dy in (-1, 0, 1):
                    nx, ny = x + dx, y + dy
                    if 0 <= nx < w and 0 <= ny < h and dist[ny*w+nx] > dv + 1: dist[ny*w+nx] = dv + 1; dq.append((nx, ny))
        starts = [(x, y) for (ex, ey) in entries.get(name, []) for x in range(ex - 3, ex + 4) for y in range(ey - 3, ey + 4) if free(x, y)]
        if not starts:                                   # no entry info: biggest free area
            starts = [max(((x, y) for y in range(h) for x in range(w)), key=lambda c: dist[c[1]*w+c[0]])]
        seen = set(starts); st = list(starts)
        while st:
            x, y = st.pop()
            for dx, dy in ((1, 0), (-1, 0), (0, 1), (0, -1)):
                q = (x + dx, y + dy)
                if q not in seen and free(*q): seen.add(q); st.append(q)
        cand = [c for c in seen if dist[c[1]*w+c[0]] >= 3 and 6 <= c[0] < w - 6 and 6 <= c[1] < h - 6]
        if not cand: cand = list(seen)
        pts = [max(cand, key=lambda c: dist[c[1]*w+c[0]])]
        md = {c: abs(c[0]-pts[0][0]) + abs(c[1]-pts[0][1]) for c in cand}
        while len(pts) < min(N_SPOTS, len(cand)):
            c = max(md, key=md.get); pts.append(c)
            for q in md: md[q] = min(md[q], abs(q[0]-c[0]) + abs(q[1]-c[1]))
        res[name] = [[x * 32 + 16, y * 32 + 16] for x, y in pts]
        print(f"{name}: {w}x{h}, reachable {len(seen)}, spots {len(pts)}")
    json.dump(res, open(out, "w"))
if __name__ == "__main__":
    main()
