"""test47 (user 2026-10-24 12:29): every gate of a province map is bound to one neighbour province, and NPC squads
enter only through gates of their own road / own side - never through the gate of the enemy's province."""
import sys, os, json
os.chdir('/tmp/mp'); sys.path.insert(0, '/tmp/mp')
for f in ('npcs.json', 'world.json'):
    if os.path.exists(f): os.remove(f)
import sgserver as S
S.LOG = open('/tmp/mp/server47.log', 'w', encoding='utf-8')
def chk(n, ok, i=''): print(('PASS ' if ok else 'FAIL ') + n, i, flush=True)

G, L = S.GATE_SPOTS, S.PORTAL_LINKS
chk("gate data loaded", len(G) == 85 and len(L) == 85, (len(G), len(L)))
chk("each gate leads to one neighbour, gates == portal links", all(sorted(g[0] for g in G[p]) == sorted(L[p]) for p in G))
chk("portal links are two-way", all(p in L[q] for p in L for q in L[p]))

def nb_of(pid, pt):
    return next(g[0] for g in G[pid % 100000] if (g[1], g[2]) == pt)

bad, cases, came = [], 0, []
for pid in sorted(G):
    mid = 600000 + pid
    for nid in (1, 2, 3, 4):
        own = [g[0] for g in G[pid] if S.same_side(S.province_owner(600000 + g[0]), nid)]
        if not own or len(own) == len(G[pid]):
            continue
        cases += 1
        st = S.gate_starts(mid, 6, nid)
        used = {nb_of(mid, p) for p in st}
        if not used <= set(own):
            bad.append((mid, nid, used, own))
        frm = 600000 + own[-1]
        st = S.gate_starts(mid, 4, nid, frm=frm)
        if {nb_of(mid, p) for p in st} != {own[-1]}:
            came.append((mid, nid, frm))
chk("6 squads with no road: only gates to own / allied provinces", cases > 0 and not bad, (cases, bad[:3]))
chk("squads with a road: all at the gate they came from", not came, came[:3])
# avoid the player's arrival: still never a gate of the other side
pid = next(p for p in G if len(G[p]) >= 3)
mid = 600000 + pid
g0 = G[pid][0]
st = S.gate_starts(mid, 3, None, avoid=(g0[1], g0[2]), frm=600000 + g0[0])
chk("came-from gate kept even if the player stands there", {nb_of(mid, p) for p in st} == {g0[0]})
