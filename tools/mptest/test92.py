"""test92 (user 2026-10-27 23:27 "when an NPC's own province is taken, the battle should send it back to the nearest
province"): an NPC released in a province now held by the enemy falls back to the nearest province of its side next
door (one connected to its capital first) and holds it, instead of walking to the capital."""
import os, sys, time, random
os.chdir('/tmp/mp'); sys.path.insert(0, '/tmp/mp')
for f in ('npcs.json', 'world.json'):
    if os.path.exists(f): os.remove(f)
import sgserver as S
S.LOG = open('/tmp/mp/server92.log', 'w', encoding='utf-8')
S.save_world = lambda w: None; S.npc_save = lambda force=False: None
def chk(n, ok, i=''): print(('PASS ' if ok else 'FAIL ') + n, i, flush=True)
random.seed(3)
now = time.time()
S.npc_tick(now)
nid = 1
cap = S.CAPITALS[nid]; pl = cap // 100000
w = S.world_state()
P = lambda q: pl * 100000 + q
A = P(list(S.PORTAL_LINKS.get(cap % 100000, ()))[0])
w['owners'][str(A)] = nid
C = next(P(q) for q in S.PORTAL_LINKS.get(A % 100000, ()) if P(q) != cap and P(q) not in S.CAPITALS.values())
w['owners'][str(C)] = 2                                   # its province C was just taken by nation 2
S._ENCL_CACHE = {} if hasattr(S, '_ENCL_CACHE') else None
n = [m for m in S.npc_of(nid) if m['state'] == 'active'][0]
n['task'] = {'kind': 'defend', 'target': C}
real_here = S.npc_here
S.npc_here = lambda m, t: C
S.npc_release(n, now, 100, won=False)
S.npc_here = real_here
chk('falls back to the nearest own province', n.get('post') == A and n.get('post_kind') == 'fallback', (n.get('post'), A))
chk('... walks only one step there', (n.get('walk') or {}).get('path') == [C, A], (n.get('walk') or {}).get('path'))
loc = S.npc_location(n, now + 3600)
chk('... and stays there when idle (not the capital)', loc and loc[0] == A, loc)
# the province falls too -> the post is dropped, normal home behaviour
w['owners'][str(A)] = 2
loc2 = S.npc_location(n, now + 3600)
chk('lost fallback post is not used', not loc2 or loc2[0] != A, loc2)
# released in an own province -> still goes home as before
w['owners'][str(A)] = nid
m = [x for x in S.npc_of(nid) if x['state'] == 'active'][1]
m['task'] = {'kind': 'defend', 'target': A}
S.npc_here = lambda x, t: A
S.npc_release(m, now, 100, won=True)
S.npc_here = real_here
chk('own province: no fallback post', m.get('post_kind') != 'fallback', m.get('post'))
# no own neighbour -> old behaviour (capital)
w['owners'][str(A)] = 2
k = [x for x in S.npc_of(nid) if x['state'] == 'active'][2]
k['task'] = {'kind': 'defend', 'target': C}
S.npc_here = lambda x, t: C
S.npc_release(k, now, 100, won=False)
S.npc_here = real_here
chk('no own neighbour: no fallback', k.get('post_kind') != 'fallback', k.get('post'))
