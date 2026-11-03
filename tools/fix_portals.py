#!/usr/bin/env python3
"""Make the Novice (6) and Elite (3) planets use the Advanced planet's (2) portal network.
All planets draw their provinces with vinu layout 2 (9x9 grid, named maps a1-l.nm, cornera.nm ...), but portals.por holds
the ORIGINAL 8x8 networks for planets 3 and 6: 21 provinces (incl. the corner capitals x00800/x00008/x00808) had no
portals at all and the rest had portal rectangles placed for other maps.  Every type-1 record whose SOURCE is a planet-3/6
province (id%100000 in the 9x9 grid, ten-thousands digit 0) is replaced by a copy of planet 2's records for that province
with the planet digit of source and target rewritten.  Cave records (x1xxxx..x3xxxx sources) are kept.
usage: fix_portals.py PAM2.dat OUT.dat"""
import struct, sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import sgdat, sgdat_add
SIZES = {1: 10, 2: 7, 14: 6}
GRID = {c * 100 + r for c in range(9) for r in range(10 if c % 2 else 9)}
def parse(d):
    n = struct.unpack_from("<I", d, 0)[0]; v = struct.unpack("<%di" % (len(d) // 4), d); o = 1; out = []
    for _ in range(n):
        t = v[o]; out.append(list(v[o:o + SIZES[t]])); o += SIZES[t]
    assert o * 4 == len(d), "trailing bytes"
    return out
def dump(recs):
    return struct.pack("<I", len(recs)) + b"".join(struct.pack("<%di" % len(r), *r) for r in recs)
def is_prov(i, p):
    return i // 100000 == p and i % 100000 in GRID
def remap(i, p):
    return p * 100000 + i % 100000 if i // 100000 == 2 else i
CORNERS = (0, 800, 8, 808)
# the six exit gates the shared base map Capital.nm was drawn for (planet 2 top-left capital 200000's portal rects)
CAP_GATES = [(65, 97), (64, 16), (110, 26), (113, 76), (15, 77), (18, 26)]
def fix_capitals(recs, planet=2):
    """2026-10-21: (a) remove the capital <-> capital teleport portals (corner to corner, incl. the diagonal one);
    (b) every capital map is Capital.nm + overlay, so put each remaining capital gate (source rect, and the arrival
    point of portals INTO a capital) exactly on the nearest of the six gates of 200000: 200808 -> 200807 sat at
    (65,17), one cell off the (64,16) gate, and the hero could not reach it."""
    caps = {planet * 100000 + c for c in CORNERS}
    snap = lambda x, y: min(CAP_GATES, key=lambda g: (g[0] - x) ** 2 + (g[1] - y) ** 2)
    out, removed, moved = [], 0, 0
    for r in recs:
        if r[0] == 1 and r[1] in caps and r[6] in caps:
            removed += 1; continue
        r = list(r)
        if r[0] == 1 and r[1] in caps and (r[6] // 10000) % 10 == 0:
            g = snap(r[2], r[3]); moved += (g != (r[2], r[3])); r[2], r[3] = g
        if r[0] == 1 and r[6] in caps:
            g = snap(r[7], r[8]); moved += (g != (r[7], r[8])); r[7], r[8] = g
        out.append(r)
    print(f"capitals: removed {removed} capital<->capital portals, moved {moved} gate rects/arrival points")
    return out

# hunting grounds ("CAVE 1/2/3" of a province = maps mon1/mon2/mon3.nm, id = province + k*10000)
CAVE_EXIT_RECT = {1: (248, 5), 2: (22, 37), 3: (240, 226)}       # exit gate in mon1/2/3 (Capital.por / original data)
CAP_CAVE_ARRIVAL = {1: (73, 96), 2: (65, 101), 3: (57, 36)}      # where a capital's own cave exits land (Capital.por)
FIXED_ENTRANCES = {(200203, 220203): (123, 77)}                  # newn.nm cave-2 entrance was at x=154 on a 128 map
def fix_caves(recs, planet=2):
    """2026-10-21:
    * 200303 had its cave-3 entrance pointing to 240303 (mon4.nm does not exist) -> 230303;
    * newn.nm (200203) cave-2 entrance rect was outside the 128x128 map -> moved inside;
    * exits: caves 1 and 2 had NO way back and the 64 cave-3 exits were the old 8x8 data (arrivals on the wrong
      maps, 21 provinces without any).  All exit records of the planet are rebuilt: for every province and cave
      k, exit gate in monK.nm -> back to the province, arriving on the cave entrance (capital: Capital.por spot)."""
    base = planet * 100000
    isprov = lambda i: i // 100000 == planet and (i // 10000) % 10 == 0
    out, entr = [], {}
    for r in recs:
        r = list(r)
        if r[0] == 1 and isprov(r[1]) and (r[6] // 10000) % 10 == 4 and r[6] // 100000 == planet:
            r[6] = base + 30000 + r[6] % 10000
        if r[0] == 1 and (r[1], r[6]) in FIXED_ENTRANCES:
            r[2], r[3] = FIXED_ENTRANCES[(r[1], r[6])]
        if r[0] == 1 and r[1] // 100000 == planet and (r[1] // 10000) % 10 in (1, 2, 3) and isprov(r[6]):
            continue                                            # old exit, rebuilt below
        if r[0] == 1 and isprov(r[1]) and r[6] // 100000 == planet and (r[6] // 10000) % 10 in (1, 2, 3):
            entr[(r[1], (r[6] // 10000) % 10)] = r
        out.append(r)
    caps = {base + c for c in CORNERS}
    added = 0
    for (prov, k), e in sorted(entr.items()):
        ex, ey = CAVE_EXIT_RECT[k]
        ax, ay = CAP_CAVE_ARRIVAL[k] if prov in caps else (e[2], e[3])
        out.append([1, prov + k * 10000, ex, ey, 4, 4, prov, ax, ay, 50 + k]); added += 1
    print(f"caves: {added} exit portals (re)built")
    return out
def fix(por, planets=(3, 6)):
    recs = fix_caves(fix_capitals(parse(por)))
    keep = [r for r in recs if not (r[0] == 1 and any(is_prov(r[1], p) for p in planets))]
    src2 = [r for r in recs if r[0] == 1 and is_prov(r[1], 2)]
    add = []
    for p in planets:
        for r in src2:
            q = list(r); q[1] = remap(q[1], p); q[6] = remap(q[6], p); add.append(q)
    allr = sorted(keep + add, key=lambda r: r[1])     # the original file is sorted by source id; keep it that way
    return allr, len(recs) - len(keep), len(add)
def main():
    src, out = sys.argv[1:3]
    d = open(src, "rb").read(); idx = {n.lower(): (n, o, s) for n, o, s in sgdat.read_index(d)}
    name, o, s = idx["portals.por"]
    recs, removed, added = fix(d[o:o + s])
    tmp = os.path.join(os.path.dirname(os.path.abspath(out)), "_portals"); os.makedirs(tmp, exist_ok=True)
    p = os.path.join(tmp, name); open(p, "wb").write(dump(recs))
    print(f"portals.por: removed {removed} planet-3/6 province records, added {added} copies of planet 2 -> {len(recs)} records")
    print(sgdat_add.add(src, out, [p]))
if __name__ == "__main__":
    main()
