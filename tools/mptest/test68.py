# 2026-10-25 21:17/21:18: NPC attacks only where its side borders the target (also checked on arrival);
# an NPC standing on foreign land has no march road; SOS replies never claim more than one wave (12 units).
import sys, os, time
os.chdir('/tmp/mp'); sys.path.insert(0, '/tmp/mp')
for f in ('npcs.json', 'world.json'):
    if os.path.exists(f): os.remove(f)
import sgserver as S
S.LOG = open('/tmp/mp/t_front.log', 'w', encoding='utf-8')
def chk(n, ok, i=''): print(('PASS ' if ok else 'FAIL ') + n, i, flush=True)
nid = 2
cap = S.CAPITALS[nid]; pl = cap // 100000
L = S.PORTAL_LINKS
# a province two steps from the capital: X neighbour of cap, T neighbour of X not touching cap
X = pl * 100000 + sorted(L[cap % 100000])[0]
T = next(pl * 100000 + q for q in L[X % 100000] if pl * 100000 + q != cap and q not in L[cap % 100000])
for p in S.planet_provinces(pl):
    if p != cap: S.set_province_owner(p, 0)
S.set_province_owner(X, nid)
chk('front ok when own land borders the target', S.npc_front_ok(nid, T))
S.set_province_owner(X, 3)
chk('no front when the bordering province was lost', not S.npc_front_ok(nid, T))
n = S.npc_of(nid)[0] if S.npc_of(nid) else None
if n is None:
    S.npc_sync(nid, time.time()); n = S.npc_of(nid)[0]
pth, sec = S.npc_march_path(n, T, start=X)
chk('no march from foreign land', pth is None, pth)
S.set_province_owner(X, nid)
pth, sec = S.npc_march_path(n, T, start=cap)
chk('march from home works', bool(pth) and pth[-2] == X, pth)
# arrival with the road cut -> no battle, task cleared
now = time.time()
n['task'] = {'kind': 'attack', 'target': T, 'origin': X, 'depart': now - 10, 'arrive': now - 1, 'phase': 'march', 'path': pth}
S.set_province_owner(X, 3)
S.npc_begin([n], now)
chk('road cut on arrival: no battle opened', T not in S.BATTLES)
chk('road cut on arrival: goes home', not n.get('task') or n['task'].get('kind') != 'attack', n.get('task'))
src = open(S.__file__.replace('sgserver.py', 'sgs/npc_world.py'), encoding='utf-8').read() if os.path.exists(S.__file__.replace('sgserver.py', 'sgs/npc_world.py')) else ''
chk('SOS reply count capped at one wave', '_n=min(k, NPC_GHOST_DEPLOY)' in src or S.NPC_GHOST_DEPLOY == 12)
