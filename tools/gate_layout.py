#!/usr/bin/env python3
"""GATE LAYOUT DATA (user 2026-10-24 18:58: keep the gate <-> province-map relation as data so it can be adjusted fast).
  export  PAM2.dat VINU.tsv OUT.json         -> one record per province map (planets 2/3/6 share the same plan):
            {"CCRR": {"map": "rm3.nm", "w": 128, "h": 128,
                      "gates": {"NEIGHBOUR CCRR": {"side": "NE", "x": 106, "y": 30}, ...}}, ...}
            x, y = top-left cell of the 4x4 gate rect (tiles, as on the minimap: x right, y down); side = the hexagon side
            of the neighbour (N / NE / SE / S / SW / NW) - fix_gate_dirs.py HEX_SIDES.
  apply   PAM2_IN.dat LAYOUT.json PAM2_OUT.dat  -> writes the rects of LAYOUT into every planet's portals.por (and the
            arrival point of each reverse portal = the new gate), keeps everything else.
To move one gate: edit its x / y in tools/gate_layout.json, then
  python tools/gate_layout.py apply out/pam2_fixed.dat tools/gate_layout.json out/pam2_fixed.dat
  python tools/check_world_maps.py GAMEDIR out/pam_fixed.dat out/pam2_fixed.dat      (reachability)
  extract portals.por + gen_gate_spots / gen_spawn_spots / gen_walk_grids (see docs/05_GATES_MAPS.md), publish + deploy."""
import sys, os, json
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import sgdat, fix_portals as F, fix_gate_dirs as G

def _por(pam2_d):
    for n, o, s in sgdat.read_index(pam2_d):
        if n.lower() == "portals.por":
            return o, s
    raise SystemExit("no portals.por")

def nb(r):
    return (r[0] == 1 and r[1] // 100000 in (2, 3, 6) and r[1] // 100000 == r[6] // 100000 and (r[1] // 10000) % 10 == 0
            and (r[6] // 10000) % 10 == 0 and r[1] % 100000 in F.GRID and r[6] % 100000 in F.GRID)

def export(pam2_p, tsv, out_p):
    d = open(pam2_p, "rb").read(); o, s = _por(d)
    recs = F.parse(d[o:o + s])
    vinu = {}
    for ln in open(tsv, encoding="utf-8").read().splitlines()[1:]:
        f = ln.split("\t")
        if f[1] == "2": vinu[int(f[0]) % 100000] = f[5].lower().replace(".nm", "") + ".nm"
    lay = {}
    for r in recs:
        if nb(r) and r[1] // 100000 == 2:
            p, q = r[1] % 100000, r[6] % 100000
            e = lay.setdefault("%04d" % p, {"map": "capital.nm + %08d.nm" % p if p in G.CAPS else vinu.get(p), "gates": {}})
            e["gates"]["%04d" % q] = {"side": G.hex_side(p, q), "x": r[2], "y": r[3]}
    lay = {k: dict(v, gates=dict(sorted(v["gates"].items(), key=lambda kv: list(G.HEX_SLOT).index(kv[1]["side"]))))
           for k, v in sorted(lay.items())}
    json.dump(lay, open(out_p, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    print(f"{len(lay)} provinces, {sum(len(v['gates']) for v in lay.values())} gates -> {out_p}")

def apply(pam2_p, lay_p, out_p):
    d = open(pam2_p, "rb").read(); o, s = _por(d)
    recs = F.parse(d[o:o + s])
    lay = json.load(open(lay_p, encoding="utf-8"))
    plan = {(int(p), int(q)): (g["x"], g["y"]) for p, v in lay.items() for q, g in v["gates"].items()}
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
    new = F.dump(recs)
    assert len(new) == s, "size changed"
    out = bytearray(d); out[o:o + s] = new
    open(out_p, "wb").write(out)
    print(f"{len(plan)} gates from {lay_p}: {moved} records moved -> {out_p}")

if __name__ == "__main__":
    cmd = sys.argv[1]
    (export if cmd == "export" else apply)(*sys.argv[2:5])
