"""test111 (user 2026-10-31 11:45, screenshot "NPCs must join a battle where their commander stands or at a gate near
their own nation - never through a gate that does not belong to their nation"): battle_flow.gate_starts / entry_gate:
A. the gate of the road (frm) only while that province is still of the NPC's side - an enemy frm is ignored;
B. own nation's gates first, allied gates only when it has none;
C. no gate to a province of its side: [] (no fallback to a foreign gate) and npc_spawn puts nothing on the map."""
import sys, os, time, random
os.chdir('/tmp/mp'); sys.path.insert(0, '/tmp/mp')
for f in ('npcs.json', 'world.json'):
    if os.path.exists(f): os.remove(f)
import sgserver as S
S.LOG = open('/tmp/mp/server111.log', 'w', encoding='utf-8')
def chk(n, ok, i=''): print(('PASS ' if ok else 'FAIL ') + n, i, flush=True)
caps = set(S.CAPITALS.values())
NA = 1
pl = S.CAPITALS[NA] // 100000
mid = next(p for p in S.planet_provinces(pl) if p not in caps and len(S.GATE_SPOTS.get(p % 100000, ())) >= 3
           and all(pl * 100000 + g[0] not in caps for g in S.GATE_SPOTS[p % 100000]))
gs = S.GATE_SPOTS[mid % 100000]
A, B, C = [pl * 100000 + g[0] for g in gs[:3]]
for g in gs:
    S.set_province_owner(pl * 100000 + g[0], 3)          # all neighbours: enemy nation 3
S.set_province_owner(A, NA)
spot = lambda q: next((g[1], g[2]) for g in gs if pl * 100000 + g[0] == q)
st = S.gate_starts(mid, 2, NA, frm=B)
chk('A1 came along an enemy province: not its gate, the own one', st and all(p == spot(A) for p in st), (st, spot(A), spot(B)))
st = S.gate_starts(mid, 1, NA, frm=A)
chk('A2 came from its own province: that gate', st == [spot(A)], st)
chk('A3 players too (entry_gate): enemy frm ignored', S.entry_gate(mid, NA, B) == spot(A))
ally = next((x for x in S.CAPITALS if x != NA and x != 3 and S.same_side(x, NA)), None)
if ally:
    S.set_province_owner(C, ally)
    st = S.gate_starts(mid, 3, NA)
    chk('B1 own gate before the allied one', st and all(p == spot(A) for p in st), st)
    S.set_province_owner(A, 3)
    st = S.gate_starts(mid, 2, NA)
    chk('B2 no own gate: the allied one', st and all(p == spot(C) for p in st), st)
    S.set_province_owner(C, 3)
else:
    S.set_province_owner(A, 3)
    chk('B  (no allied nation in this world - skipped)', True)
st = S.gate_starts(mid, 2, NA, frm=B)
chk('C1 no gate of its side: none at all (not a foreign gate)', st == [], st)
class G: pass
g = G(); g.targets = {}
S.npc_spawn(g, mid, NA, [n for n in S.npc_of(NA)][:2], 20, [(0x400, 0x400)] * 2, "assault", 0, 0, True, starts=st)
chk('C2 npc_spawn with no gate: no unit on the map', not g.targets, len(g.targets))
