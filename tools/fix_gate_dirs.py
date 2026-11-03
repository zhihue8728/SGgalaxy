#!/usr/bin/env python3
"""Province gates face their neighbours ON SCREEN (user 2026-10-22 19:40).
The original portals.por puts the gate to a neighbour by MAP axes (x = strategic columns, y = rows), so in the 45 deg
isometric view the gate to the northern province sat top-RIGHT, the eastern one bottom-right, ... (and ~15 gates were
on a wrong side altogether).  This moves every neighbour gate (type-1 record province -> adjacent province, planets
2/3/6 = vinu layout 2) to the walkable spot of its map that lies the farthest in the SCREEN direction of the neighbour
on the strategic map (N = up, NE = up-right, SE = down-right ...), and sets the arrival point of the reverse portal
to the new gate (original convention: you arrive on the return gate).
Rules for a gate rect (4x4 cells): all cells walkable (flag 0x01), reachable by a hero (2x2 clearance, main area),
>= 2 cells from the border, >= GATE_SEP cells from other gates / cave entrances of the province, >= POC_SEP cells
from its POC spots.  Capitals (Capital.nm shared): only the six drawn gates (fix_portals.CAP_GATES).
usage: fix_gate_dirs.py PAM.dat PAM3.dat PAM2_IN.dat VINU.tsv POC_SPOTS.json PAM2_OUT.dat"""
import sys, os, struct, math, json, collections
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import sgdat, fix_portals as F
GATE_SEP, POC_SEP, BORDER, MAX_DEV = 14, 10, 2, 35.0
# user 2026-10-22 23:40: a gate stood on the edge of the dark (blocked) area.  The original gates all sit in open ground
# (walkable share of the 10x10 window around the 4x4 rect: median 1.00, 10th percentile 0.94), the first version of this tool
# pushed them to the rim (median 0.90, 5x5-pad window 0.67).  CLEAR3 / CLEAR5 = required / preferred walkable share of the
# window with 3 / 5 cells of margin around the rect (the gate sprite is bigger than its rect and reaches up on screen).
CLEAR3, CLEAR5_PREF = 0.97, 0.80
# user 2026-10-22 23:44: the gate sprite must stand on the PADS drawn in the map art (dark platform with the ramp and
# machinery); the original records sit exactly there.  So the gates of a province keep the ORIGINAL pad positions and
# only the assignment pad -> neighbour changes (best assignment by screen direction, like the capitals).
FIXED_PADS = False
# user 2026-10-23 11:18: gates belong on the EDGE of every map (the pads in the middle of the capital blocked the walking
# routes).  EDGE mode: the 4x4 gate rect must lie in the outer band EDGE_MIN..EDGE_MAX cells from the map border
# (walkable, reachable, open ground), the one farthest in the screen direction of the neighbour wins; capitals too.
EDGE_GATES, EDGE_MIN, EDGE_MAX = True, 3, 9
TARGET_MODE, EDGE_TARGET = True, 5     # (2026-10-23 13:58) gate = open spot nearest to the border point facing the neighbour
CAPS = (0, 800, 8, 808)
# (user 2026-10-24 18:30) the gate to neighbour B lies in the direction of the CENTRE OF THE A/B BORDER on the strategic
# map (strat_borders.py, client province shapes nb%02d%02d.xpf), laid on the map as seen on the MINIMAP (tile x = right,
# tile y = down) - capital 00: 0100 top-right, 0101 right / lower right, 0001 bottom slightly left.  The 45 deg screen
# conversion (2026-10-22) put all three capital gates on the right of the minimap.  BORDER_DIR = False -> old rule.
BORDER_DIR, TILE_DIR = True, True
# (user 2026-10-24 18:40) a province is a HEXAGON with 6 sides (flat top: N, NE, SE, S, SW, NW).  Every neighbour
# lies on exactly one side (hex adjacency of the CCRR grid, odd columns half a row higher), and its gate goes to the
# middle of THAT side of the map as seen on the minimap: N top centre, NE upper right, SE lower right, S bottom
# centre, SW lower left, NW upper left.  Capital 00: 0100 = NE (upper right), 0101 = SE (lower right), 0001 = S.
HEX_SIDES = True
HEX_SLOT = {"N": (0.5, 0.0), "NE": (0.875, 0.25), "SE": (0.875, 0.75), "S": (0.5, 1.0), "SW": (0.125, 0.75),
            "NW": (0.125, 0.25)}
HEX_ANGLE = {"N": -90, "NE": -30, "SE": 30, "S": 90, "SW": 150, "NW": -150}

def hex_side(p, q):
    sx, sy = strat(p); tx, ty = strat(q)
    a = math.degrees(math.atan2(ty - sy, tx - sx))
    return min(HEX_ANGLE, key=lambda k: abs((a - HEX_ANGLE[k] + 180) % 360 - 180))
NO_SPLIT = True          # a gate (rect + 1 cell) must not cut the hero-walkable area in two (it must not block a route)
NTF2 = os.environ.get("SG_NTF2") or os.path.expanduser("~/mnt/Shattered Galaxy/NTF2.dat")

def dat(p):
    d = open(p, "rb").read()
    return d, {n.lower(): (n, o, s) for n, o, s in sgdat.read_index(d)}

def parse_nm(b):
    w, h = struct.unpack_from("<HH", b, 1)
    return w, h, [b[5 + 3 * i + 2] & 0x01 != 0 for i in range(w * h)]

def strat(p):                       # strategic-map position of CCRR (odd columns hold 10 rows, half a row higher)
    c, r = p // 100, p % 100
    return c * 0.866, r - 0.5 * (c % 2)

def main():
    pam_p, pam3_p, pam2_p, tsv, pocs_p, out_p = sys.argv[1:7]
    pam_d, pam = dat(pam_p); pam3_d, pam3 = dat(pam3_p); pam2_d, pam2 = dat(pam2_p)
    get = lambda d, idx, n: d[idx[n][1]:idx[n][1] + idx[n][2]]
    vinu = {}
    for ln in open(tsv, encoding="utf-8").read().splitlines()[1:]:
        f = ln.split("\t")
        if f[1] == "2": vinu[int(f[0]) % 100000] = f[5].lower().replace(".nm", "") + ".nm"
    pocs = json.load(open(pocs_p))
    recs = F.parse(get(pam2_d, pam2, "portals.por"))
    bdirs = {}
    if BORDER_DIR:
        import strat_borders
        bdirs = strat_borders.border_dirs(NTF2)[0]
        print(f"border directions: {len(bdirs)} province pairs from {NTF2}")
    def direction(p, q):
        if (p, q) in bdirs:
            return bdirs[(p, q)]
        sx, sy = strat(p); tx, ty = strat(q)
        dx, dy = tx - sx, ty - sy; n = math.hypot(dx, dy); return dx / n, dy / n
    grids = {}
    def grid(p):
        if p not in grids:
            if p in CAPS:
                w, h, a = parse_nm(get(pam3_d, pam3, "capital.nm")); _, _, b = parse_nm(get(pam_d, pam, "%08d.nm" % p))
                grids[p] = (w, h, [x or y for x, y in zip(a, b)])
            else:
                n = vinu[p]
                src = (pam3_d, pam3) if n in pam3 else (pam_d, pam)
                grids[p] = parse_nm(get(src[0], src[1], n))
        return grids[p]
    nb = lambda r: (r[0] == 1 and r[1] // 100000 in (2, 3, 6) and r[1] // 100000 == r[6] // 100000 and (r[1] // 10000) % 10 == 0
                    and (r[6] // 10000) % 10 == 0 and r[1] % 100000 in F.GRID and r[6] % 100000 in F.GRID)
    # one plan per province CCRR (planet 2 records), applied to every planet
    plan, report = {}, []
    by_prov = collections.defaultdict(list)
    for r in recs:
        if nb(r) and r[1] // 100000 == 2:
            by_prov[r[1] % 100000].append(r)
    for p in sorted(by_prov):
        w, h, blk = grid(p)
        free = lambda x, y: 0 <= x < w and 0 <= y < h and not blk[y * w + x]
        f2 = lambda x, y: free(x, y) and free(x + 1, y) and free(x, y + 1) and free(x + 1, y + 1)
        def clear(c, pad):                       # walkable share of the (4 + 2 pad)^2 window around the rect
            n = f = 0                            # (cells outside the map count as open: gates sit at the rim)
            for yy in range(c[1] - pad, c[1] + 4 + pad):
                for xx in range(c[0] - pad, c[0] + 4 + pad):
                    n += 1; f += 1 if (free(xx, yy) or not (0 <= xx < w and 0 <= yy < h)) else 0
            return f / n
        # main hero area
        comp, best = {}, None
        for y in range(h):
            for x in range(w):
                if f2(x, y) and (x, y) not in comp:
                    cid = len(comp) and (x, y); st = [(x, y)]; cells = [(x, y)]; comp[(x, y)] = (x, y)
                    while st:
                        a, b = st.pop()
                        for dx, dy in ((1, 0), (-1, 0), (0, 1), (0, -1)):
                            c = (a + dx, b + dy)
                            if c not in comp and f2(*c): comp[c] = (x, y); st.append(c); cells.append(c)
                    if best is None or len(cells) > len(best): best = cells
        main = set(best or [])
        # fixed obstacles: cave entrances / other non-neighbour records of this province, POC spots
        fixed = [(r[2] + 2, r[3] + 2) for r in recs if r[0] == 1 and r[1] // 100000 == 2 and r[1] % 100000 == p and not nb(r)]
        pts = []
        for key in (vinu.get(p, "")[:-3], "%08d" % p):
            for lst in (pocs.get(key) or {}).values():
                pts += [(px // 32, py // 32) for px, py in lst]
        placed = []
        cx0, cy0 = w / 2, h / 2
        cands = []
        if p in CAPS and not EDGE_GATES:
            cands = [(gx, gy) for gx, gy in F.CAP_GATES]
        elif FIXED_PADS:
            cands = [(r[2], r[3]) for r in by_prov[p]]
        else:
            allc = [(gx, gy) for gy in range(BORDER, h - BORDER - 4 + 1) for gx in range(BORDER, w - BORDER - 4 + 1)
                    if all(free(gx + i, gy + j) for i in range(4) for j in range(4)) and
                    any((gx + i, gy + j) in main for i in range(3) for j in range(3))]
            bands = (EDGE_MAX, 16, 32, 999) if EDGE_GATES else (999,)
            ring = lambda c: min(c[0], c[1], w - 4 - c[0], h - 4 - c[1])
        gates = sorted(by_prov[p], key=lambda r: r[6])
        if (p in CAPS and not EDGE_GATES) or FIXED_PADS:         # fixed pads: best overall assignment (all permutations)
            import itertools
            def dev_of(r, c):
                sx, sy = strat(p); tx, ty = strat(r[6] % 100000)
                dx, dy = tx - sx, ty - sy; n = math.hypot(dx, dy); dx, dy = dx / n, dy / n
                rx, ry = c[0] + 2 - cx0, c[1] + 2 - cy0
                scx, scy = rx - ry, (rx + ry) / 2; L = math.hypot(scx, scy) or 1e-9
                return math.degrees(math.acos(max(-1, min(1, (scx * dx + scy * dy) / L))))
            bestp = min(itertools.permutations(cands, len(gates)),
                        key=lambda perm: sum(dev_of(r, c) ** 2 for r, c in zip(gates, perm)))
            for r, c in zip(gates, bestp):
                plan[(p, r[6] % 100000)] = c
                d_ = dev_of(r, c)
                if d_ > MAX_DEV: report.append(f"{'capital ' if p in CAPS else ''}{p}->{r[6] % 100000}: {d_:.0f} deg off (fixed pads)")
            continue
        def splits(extra):
            """True if the gates placed so far + extra (rect corners) cut the main hero area (2x2 cells) apart."""
            if not NO_SPLIT:
                return False
            bl = set()
            for gx, gy in [(q[0] - 2, q[1] - 2) for q in placed] + [extra]:
                for yy in range(gy - 2, gy + 5):
                    for xx in range(gx - 2, gx + 5):
                        bl.add((xx, yy))
            rest = [c for c in main if c not in bl]
            if not rest:
                return True
            seen = {rest[0]}; st = [rest[0]]; rs = set(rest)
            while st:
                a, b = st.pop()
                for ddx, ddy in ((1, 0), (-1, 0), (0, 1), (0, -1)):
                    c2 = (a + ddx, b + ddy)
                    if c2 in rs and c2 not in seen:
                        seen.add(c2); st.append(c2)
            return len(rs) - len(seen) > 40          # more than a few stray cells cut off = a blocked route
        for r in gates:
            dx, dy = direction(p, r[6] % 100000)
            if HEX_SIDES:
                side = hex_side(p, r[6] % 100000)
                fx, fy = HEX_SLOT[side]
                slot = (fx * w - 2, fy * h - 2)                   # rect corner of the side's middle
                vx_, vy_ = fx * w - cx0, fy * h - cy0
                L_ = math.hypot(vx_, vy_); dx, dy = vx_ / L_, vy_ / L_
            def score(c):
                rx, ry = c[0] + 2 - cx0, c[1] + 2 - cy0
                scx, scy = (rx, ry) if TILE_DIR else (rx - ry, (rx + ry) / 2)     # minimap (tile) / iso screen
                L = math.hypot(scx, scy) or 1e-9
                dev = math.degrees(math.acos(max(-1, min(1, (scx * dx + scy * dy) / L))))
                return dev, scx * dx + scy * dy
            # user 2026-10-22 22:37: never two gates in the same square of the 5 x 5 minimap grid
            sector = lambda q: (min(4, int(q[0] * 5 / w)), min(4, int(q[1] * 5 / h)))
            used = {sector(q) for q in placed}
            for band in bands:
                if not EDGE_GATES or FIXED_PADS or (p in CAPS and False):
                    cands_b = cands
                else:
                    cands_b = [c for c in allc if EDGE_MIN <= ring(c) <= band]
                ok = []
                for c in cands_b:
                    cc = (c[0] + 2, c[1] + 2)
                    if any(math.dist(cc, q) < GATE_SEP for q in fixed + placed): continue
                    if p not in CAPS and any(math.dist(cc, q) < POC_SEP for q in pts): continue
                    dev, along = score(c)
                    ok.append((dev, along, c, sector(cc) not in used, clear(c, 3), clear(c, 5)))
                # (18:30) the DIRECTION comes first: stop widening the band once there is open ground in direction
                if HEX_SIDES:
                    # widen until there is open ground NEAR THE MIDDLE OF THE SIDE (not just somewhere in its
                    # direction - 202's NW / SW / SE gates went to the corners)
                    near = max(w, h) * 0.16
                    if any(x[4] >= 0.9 and math.dist(x[2], slot) <= near for x in ok):
                        break
                elif any(x[4] >= 0.9 and x[0] <= MAX_DEV for x in ok):
                    break
            if EDGE_GATES and band != EDGE_MAX:
                report.append(f"{p}->{r[6] % 100000}: edge band widened to {band}")
            # direction first (35 / 60 / 90 deg), then the most open ground inside it, then a free minimap square
            # (before: the most open ground of the whole map first -> 202->201 ended on the opposite side)
            good = []
            for lim in (MAX_DEV, 60.0, 90.0, 181.0):
                within = [x for x in ok if x[0] <= lim]
                if not within:
                    continue
                # (18:40) open enough (0.9) is enough - the spot nearest to the side's middle wins (CLEAR3 first pushed
                # NW / SW / SE gates into the corners)
                for need in ((0.9, 0.0) if HEX_SIDES else (CLEAR3, 0.9, 0.0)):
                    open_ = [x for x in within if x[4] >= need]
                    if open_: break
                if lim > MAX_DEV:
                    report.append(f"{p}->{r[6] % 100000}: nothing usable within {MAX_DEV:.0f} deg of its side, {lim:.0f}")
                if need < 0.9:
                    report.append(f"{p}->{r[6] % 100000}: no open ground in its direction (clearance {need})")
                ok_sec = [x for x in open_ if x[3]] or open_
                good = [x[:3] + (x[5],) for x in ok_sec]
                break
            if not good:
                report.append(f"{p}->{r[6] % 100000}: NO spot, kept {r[2], r[3]}"); placed.append((r[2] + 2, r[3] + 2)); continue
            if EDGE_GATES and TARGET_MODE:
                # user 2026-10-23 13:58: the gate to B must sit where A's map meets B on the strategic map, so the two
                # gates of a border face each other.  Target = where the ray from the map centre in the SCREEN
                # direction of B leaves the inner square at ring EDGE_TARGET (iso screen (sx, sy) -> tile x = sy + sx/2,
                # y = sy - sx/2); the open spot nearest to it (screen distance) wins - no more clustering in the corners.
                vx, vy = (dx, dy) if TILE_DIR else (dy + dx / 2, dy - dx / 2)
                lo_x, hi_x, lo_y, hi_y = EDGE_TARGET, w - 4 - EDGE_TARGET, EDGE_TARGET, h - 4 - EDGE_TARGET
                ox, oy = cx0 - 2, cy0 - 2
                ts = []
                if vx > 1e-9: ts.append((hi_x - ox) / vx)
                if vx < -1e-9: ts.append((lo_x - ox) / vx)
                if vy > 1e-9: ts.append((hi_y - oy) / vy)
                if vy < -1e-9: ts.append((lo_y - oy) / vy)
                t = min(ts)
                T = (ox + vx * t, oy + vy * t)
                if HEX_SIDES:
                    T = (max(lo_x, min(hi_x, slot[0])), max(lo_y, min(hi_y, slot[1])))
                def sdist(c):
                    ddx, ddy = c[0] - T[0], c[1] - T[1]
                    return math.hypot(ddx, ddy) if TILE_DIR else math.hypot(ddx - ddy, (ddx + ddy) / 2)
                ranked = sorted(good, key=lambda x: sdist(x[2]) + 30 * (1.0 - min(x[3], 1.0)))
                pick = next((x for x in ranked[:60] if not splits(x[2])), None)
                if pick is None:
                    report.append(f"{p}->{r[6] % 100000}: every near spot cuts a route - took the best one")
                    pick = ranked[0]
                dev, along, c, _c5 = pick
            else:
                dev, along, c, _c5 = max(good, key=lambda x: x[1] - 0.6 * x[0] + 25 * min(x[3], 1.0))
            plan[(p, r[6] % 100000)] = c
            placed.append((c[0] + 2, c[1] + 2))
            if dev > MAX_DEV: report.append(f"{p}->{r[6] % 100000}: best only {dev:.0f} deg off")
    # apply to every planet's copy: gate rects, then arrival points of the reverse portals
    moved = 0
    for r in recs:
        if nb(r):
            k = (r[1] % 100000, r[6] % 100000)
            if k in plan and (r[2], r[3]) != plan[k]:
                r[2], r[3] = plan[k]; moved += 1
    for r in recs:
        if nb(r):
            back = (r[6] % 100000, r[1] % 100000)
            if back in plan:
                r[7], r[8] = plan[back]
    out = bytearray(pam2_d)
    n, o, s = pam2["portals.por"]
    newpor = F.dump(recs)
    assert len(newpor) == s, "size changed"
    out[o:o + s] = newpor
    open(out_p, "wb").write(out)
    print(f"{len(plan)} gate positions planned, {moved} records moved (planets 2, 3, 6)")
    for x in report: print("  ", x)

if __name__ == "__main__":
    main()
