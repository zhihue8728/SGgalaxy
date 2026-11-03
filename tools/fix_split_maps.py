#!/usr/bin/env python3
"""Make every exit of every province map reachable from every entry (planet layout 2 = the maps all planets use).
Some original maps are cut in two by a river / cliff (newa.nm 200105, newl.nm 200604) and a few cave exits land
on blocked ground (rm8.nm 200301, e7.nm 200704 ...): a hero that comes in on one side cannot reach the gates on
the other side.  For each map: points = every portal rect + every arrival point (portals.por type 1, layout
planet 2); every point's free component (flag 0x01 = blocked, 4-neighbour) is joined to the main one by a 3-cell
wide corridor along the shortest path (cost 1 free / 10 blocked).  Writes a new pam3.dat.
usage: fix_split_maps.py PAM3.dat OUT.dat PORTALS.por VINU.tsv"""
import sys, os, struct, heapq, collections
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import sgdat, sgdat_add, fix_portals as F
CAPS = (0, 800, 8, 808)
def main():
    pam3, out, por, tsv = sys.argv[1:5]
    d = open(pam3, "rb").read(); idx = {n.lower(): (n, o, s) for n, o, s in sgdat.read_index(d)}
    recs = [r for r in F.parse(open(por, "rb").read()) if r[0] == 1]
    vin = {}
    for ln in open(tsv, encoding="utf-8").read().splitlines()[1:]:
        f = ln.split("\t")
        if f[1] == "2": vin[int(f[0]) % 100000] = f[5].lower().replace(".nm", "") + ".nm"
    tmp = os.path.join(os.path.dirname(os.path.abspath(out)), "_splitmaps"); os.makedirs(tmp, exist_ok=True)
    files = []
    global CARVED
    CARVED = {}
    for prov, nm in sorted(vin.items()):
        if prov in CAPS: continue
        name, o, s = idx[nm]; b = bytearray(d[o:o + s])
        w, h = struct.unpack_from("<HH", b, 1)
        fl = lambda x, y: b[5 + 3 * (y * w + x) + 2]
        def clear(x, y):
            if 0 <= x < w and 0 <= y < h: b[5 + 3 * (y * w + x) + 2] &= ~0x01
        free = lambda x, y: 0 <= x < w - 1 and 0 <= y < h - 1 and not (fl(x, y) | fl(x + 1, y) | fl(x, y + 1) | fl(x + 1, y + 1)) & 1   # 2x2 clearance (hero)
        pts = []
        for r in recs:
            if r[1] == 200000 + prov: pts.append([(r[2] + i, r[3] + j) for i in range(r[4]) for j in range(r[5])])
            if r[6] == 200000 + prov:
                pts.append([(r[7] + i, r[8] + j) for i in range(-1, 2) for j in range(-1, 2)])
        changed = 0; carved = set()
        for p in pts:                                  # a point with no free cell at all: open it
            if not any(free(*c) for c in p):
                for c in p: clear(*c)
                changed += 1
        def comps():
            lab = {}; n = 0
            for y in range(h):
                for x in range(w):
                    if free(x, y) and (x, y) not in lab:
                        st = [(x, y)]; lab[(x, y)] = n
                        while st:
                            cx, cy = st.pop()
                            for dx, dy in ((1, 0), (-1, 0), (0, 1), (0, -1)):
                                q = (cx + dx, cy + dy)
                                if q not in lab and free(*q): lab[q] = n; st.append(q)
                        n += 1
            return lab
        for _ in range(30):
            lab = comps()
            pc = [{lab[c] for c in p if c in lab} for p in pts]
            size = collections.Counter(lab.values())
            main_k = max({k for s_ in pc for k in s_}, key=lambda k: size[k])
            todo = [p for p, s_ in zip(pts, pc) if main_k not in s_]
            if not todo: break
            p = todo[0]
            # REASONABLE crossing (user 2026-10-21: not simply the shortest path from the gate): multi-source search
            # from the WHOLE isolated area to the main area, so the corridor is cut where the river / cliff is
            # thinnest; carving a blocked cell costs 40, cells near the map border cost +25 (no edge-hugging tunnels)
            src_k = next((lab[c] for c in p if c in lab), None)
            starts = [c for c, k in lab.items() if k == src_k] if src_k is not None else [p[0]]
            edge = lambda q: 25 if min(q[0], q[1], w - 1 - q[0], h - 1 - q[1]) < 8 else 0
            dist = {c: 0 for c in starts}; prev = {}; pq = [(0, c) for c in starts]; heapq.heapify(pq); goal = None
            while pq:
                dd, c = heapq.heappop(pq)
                if lab.get(c) == main_k: goal = c; break
                if dd > dist[c]: continue
                for dx, dy in ((1, 0), (-1, 0), (0, 1), (0, -1)):
                    q = (c[0] + dx, c[1] + dy)
                    if not (0 <= q[0] < w - 1 and 0 <= q[1] < h - 1): continue
                    nd = dd + (1 if free(*q) else 40) + edge(q)
                    if nd < dist.get(q, 1 << 30): dist[q] = nd; prev[q] = c; heapq.heappush(pq, (nd, q))
            c = goal
            while c is not None:
                for i in (-1, 0, 1, 2):
                    for j in (-1, 0, 1, 2):
                        if 0 <= c[0] + i < w and 0 <= c[1] + j < h and fl(c[0] + i, c[1] + j) & 1:
                            carved.add((c[0] + i, c[1] + j))
                        clear(c[0] + i, c[1] + j)
                c = prev.get(c)
            changed += 1
        if changed:
            path = os.path.join(tmp, name); open(path, "wb").write(bytes(b)); files.append(path)
            print(f"{prov:5d} {nm}: {changed} fix(es), {len(carved)} blocked cells opened")
            CARVED[nm] = (w, h, carved, pts)
    print(sgdat_add.add(pam3, out, files) if files else "nothing to fix")
    import json
    json.dump({k: {"w": v[0], "h": v[1], "carved": sorted(v[2]), "points": v[3]} for k, v in CARVED.items()},
              open(os.path.join(tmp, "carved.json"), "w"))
if __name__ == "__main__":
    main()
