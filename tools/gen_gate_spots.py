#!/usr/bin/env python3
"""server/gate_spots.json: where the neighbour gates of every province map are (pixels), for NPC units that ENTER a battle
through a gate (user 2026-10-23: NPC units must not stand on the POCs when a player enters, reinforcements come in at a
gate).  {CCRR: [[neighbour CCRR, x_px, y_px], ...]} from portals.por (planet 2 records; planets 3/6 are copies).
usage: gen_gate_spots.py PORTALS.por OUT.json"""
import sys, os, json
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import fix_portals as F
recs = F.parse(open(sys.argv[1], "rb").read())
out = {}
for r in recs:
    if r[0] == 1 and r[1] // 100000 == 2 and r[6] // 100000 == 2 and (r[1] // 10000) % 10 == 0 and (r[6] // 10000) % 10 == 0 \
            and r[1] % 100000 in F.GRID and r[6] % 100000 in F.GRID:
        out.setdefault(str(r[1] % 100000), []).append([r[6] % 100000, (r[2] + 2) * 32, (r[3] + 2) * 32])
json.dump(out, open(sys.argv[2], "w"))
print(len(out), "provinces,", sum(len(v) for v in out.values()), "gates")
