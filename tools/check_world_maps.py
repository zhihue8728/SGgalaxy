#!/usr/bin/env python3
"""Offline check of what the client will do on every planet / province (planets 2, 3, 6 = layout 2):
 * the map file the client loads (capital: Capital.nm + overlay 0000CCRR.nm; province: vinu name) exists and parses
 * every portal of the province (portals.por type 1, source = province) has a walkable cell that the hero can reach
   from where he appears (capital spawn (16,16) or any arrival point), and every arrival point is walkable
 * every province of the planet can be reached from every capital through portals (client BFS)
Collision: a cell is blocked if flag & 0x01 in the map (0x20 is a terrain attribute on most ground cells) (capital: base OR overlay, the pessimistic merge).
usage: check_world_maps.py GAMEDIR [PAM.dat] [PAM2.dat]"""
import sys, os, struct, collections
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import sgdat, fix_portals
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
GRID = sorted(fix_portals.GRID)
CAPS = [0, 800, 8, 808]
def dat(path):
    d = open(path, "rb").read(); return {n.lower(): d[o:o + s] for n, o, s in sgdat.read_index(d)}
def parse(b):
    w, h = struct.unpack_from("<HH", b, 1)
    q = 5 + 3 * w * h; n = struct.unpack_from("<H", b, q)[0]
    assert q + 2 + 4 * n == len(b), "bad .nm size"
    return w, h, [b[5 + 3 * i + 2] & 0x01 != 0 for i in range(w * h)]
def main():
    gd = sys.argv[1]
    pam = dat(sys.argv[2] if len(sys.argv) > 2 else os.path.join(gd, "pam.dat"))
    pam3 = dat(os.path.join(gd, "pam3.dat"))
    pam2 = dat(sys.argv[3] if len(sys.argv) > 3 else os.path.join(gd, "pam2.dat"))
    recs = [r for r in fix_portals.parse(pam2["portals.por"]) if r[0] == 1]
    vinu = {}
    for ln in open(os.path.join(ROOT, "analysis", "vinu_provinces.tsv"), encoding="utf-8").read().splitlines()[1:]:
        f = ln.split("\t")
        if f[1] == "2": vinu[int(f[0]) % 100000] = f[5].lower().replace(".nm", "") + ".nm"
    files = {**pam3, **pam}
    cache = {}
    def grid_of(prov):                     # prov = CCRR (planet independent)
        if prov in cache: return cache[prov]
        if prov in CAPS:
            w, h, base = parse(pam3["capital.nm"]); _, _, ov = parse(pam["%08d.nm" % prov])
            g = (w, h, [a or b for a, b in zip(base, ov)])
        else:
            g = parse(files[vinu[prov]])
        cache[prov] = g; return g
    errors = []; warn = 0
    for planet in (2, 3, 6):
        out = collections.defaultdict(list); inc = collections.defaultdict(list)
        for r in recs:
            if r[1] // 100000 == planet and r[1] % 100000 in GRID and (r[6] // 10000) % 10 == 0 and r[6] // 100000 == planet:
                out[r[1] % 100000].append(r); inc[r[6] % 100000].append(r)
        for prov in GRID:
            try:
                w, h, blk = grid_of(prov)
            except Exception as e:
                errors.append(f"planet {planet} prov {prov}: map load {e!r}"); continue
            free = lambda x, y: 0 <= x < w and 0 <= y < h and not blk[y * w + x]
            starts = [(16, 16)] if prov in CAPS else []
            starts += [(r[7], r[8]) for r in inc[prov]]
            for (x, y) in starts:
                if not free(x, y):
                    near = any(free(x + dx, y + dy) for dx in range(-2, 3) for dy in range(-2, 3))
                    if not near: errors.append(f"planet {planet} prov {prov}: start/arrival ({x},{y}) blocked")
            # flood from all free start cells (4-neighbour: diagonal walls are drawn as staircases, 8-neighbour leaks)
            seen = set(); st = [(x + dx, y + dy) for (x, y) in starts for dx in range(-2, 3) for dy in range(-2, 3) if free(x + dx, y + dy)]
            seen.update(st)
            while st:
                x, y = st.pop()
                for dx, dy in ((1, 0), (-1, 0), (0, 1), (0, -1)):
                        c = (x + dx, y + dy)
                        if c not in seen and free(*c): seen.add(c); st.append(c)
            if not out[prov]:
                errors.append(f"planet {planet} prov {prov}: NO portals")
            for r in out[prov]:
                cells = [(r[2] + i, r[3] + j) for i in range(r[4]) for j in range(r[5])]
                if not any(c in seen for c in cells):
                    errors.append(f"planet {planet} prov {prov}: portal -> {r[6]} rect {r[2:6]} not reachable")
        # province graph
        edges = {p: {r[6] % 100000 for r in out[p]} for p in GRID}
        for cap in CAPS:
            seen = {cap}; q = [cap]
            while q:
                p = q.pop()
                for t in edges.get(p, ()):
                    if t not in seen: seen.add(t); q.append(t)
            miss = [p for p in GRID if p not in seen]
            if miss: errors.append(f"planet {planet} capital {cap}: cannot reach {miss}")
        print(f"planet {planet}: {sum(len(v) for v in out.values())} portals checked")
    print("\n".join(errors) if errors else "ALL OK"); print(len(errors), "errors")
if __name__ == "__main__":
    main()
