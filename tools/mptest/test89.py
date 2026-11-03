"""test89 (user 2026-10-27 22:41, screenshot: a blue province cut off from the blue land by one province; "the blue NPCs
should attack downward like a real player so the land is not isolated"): the province between an own enclave and the
home land is a BRIDGE - candidates flag it, it scores first, NPCs whose task ends in the enclave stay there and strike
the bridge FROM the enclave (road starts in the enclave = they enter through the gate facing it)."""
import os, sys, time, random
os.chdir('/tmp/mp'); sys.path.insert(0, '/tmp/mp')
for f in ('npcs.json', 'world.json'):
    if os.path.exists(f): os.remove(f)
import sgserver as S
S.LOG = open('/tmp/mp/server89.log', 'w', encoding='utf-8')
S.save_world = lambda w: None; S.npc_save = lambda force=False: None
def chk(n, ok, i=''): print(('PASS ' if ok else 'FAIL ') + n, i, flush=True)
random.seed(9)
now = time.time()
S.npc_tick(now)
nid = 1
cap = S.CAPITALS[nid]; pl = cap // 100000
w = S.world_state()
L = lambda p: [pl * 100000 + q for q in S.PORTAL_LINKS.get(p % 100000, ())]
# home: capital + a neighbour A; bridge B next to A; enclave E next to B (not next to home land)
A = next(a for a in L(cap) if a not in S.CAPITALS.values())
w['owners'][str(A)] = nid
home = {cap, A}
found = None
for B in L(A):
    if B in home or B in S.CAPITALS.values() or S.province_owner(B):
        continue
    for E in L(B):
        if E in home or E in S.CAPITALS.values() or S.province_owner(E) or any(x in home for x in L(E)):
            continue
        found = (B, E); break
    if found: break
chk('test geometry found (home - bridge - enclave)', found is not None, found)
B, E = found
w['owners'][str(E)] = nid
S._ENCL_CACHE.clear()
chk('the cut-off province is an enclave', E in S.npc_enclaves(nid), S.npc_enclaves(nid))
chk('the province between them is a bridge', B in S.npc_bridges(nid), S.npc_bridges(nid))
c = [x for x in S.npc_candidates(nid, now) if x['pid'] == B]
chk('candidates flag the bridge', c and c[0].get('bridge'))
n = next(m for m in S.npc_of(nid) if m['state'] == 'active')
n['persona'] = 'cautious'
sc_b = S.NP.score(dict(c[0], def_power=1), n, 1000, random.Random(1))
sc_o = S.NP.score(dict(c[0], bridge=False, def_power=1), n, 1000, random.Random(1))
chk('a bridge scores far above the same province without', sc_b >= sc_o + 30, (sc_b, sc_o))
# an NPC whose task ends in the enclave stays there
n['task'] = {"kind": "attack", "target": E, "phase": "battle", "path": [E], "depart": now, "arrive": now}
S.npc_here = lambda m, now_=None, _o=S.npc_here: E if m is n and m.get('task') else _o(m, now_)
S.npc_release(n, now, 300, won=True)
chk('task over in the enclave: it stays there (post)', n.get('post') == E and not n.get('walk'), (n.get('post'), n.get('walk')))
S.npc_here = lambda m, now_=None: S.npc_location(m, now_)[0]
chk('... drawn in the enclave', S.npc_location(n, now)[0] == E)
n['rest_until'] = 0; n['task'] = None
for m in S.npc_of(nid): m['hl'] = None
S.npc_state()['gain'][str(nid)] = now + 9999          # even right after a conquest
S.npc_join_surface = lambda m, now_: False
S.npc_think(n, now)
t = n['task'] or {}
chk('it strikes the bridge from the enclave', t.get('kind') == 'attack' and t.get('target') == B and (t.get('path') or [None])[0] == E,
    (t.get('target'), t.get('path')))
chk('it comes in through the gate facing the enclave (origin = enclave)', t.get('origin') == E, t.get('origin'))
