"""test110 (user 2026-10-31 11:21 "loosen no_target"): an idle NPC whose nation has no free province to conquer (all
taken by its own campaigns / battles / truce) does not stand at home:
A. it joins the nearest running attack of a comrade (same target, same group, its own road);
B. a full attack (NPC_NT_JOIN_MAX) is not joined - the NPC moves up to a border post instead (cap NPC_STAGE_MAX > patrols);
C. through npc_think: no candidates -> a task, not an idle 'no_target'; the idle report shows the fallback counts."""
import sys, os, time, random
os.chdir('/tmp/mp'); sys.path.insert(0, '/tmp/mp')
for f in ('npcs.json', 'world.json'):
    if os.path.exists(f): os.remove(f)
import sgserver as S
import npc as NP
import battle_ai as BAI
S.LOG = open('/tmp/mp/server110.log', 'w', encoding='utf-8')
def chk(n, ok, i=''): print(('PASS ' if ok else 'FAIL ') + n, i, flush=True)
random.seed(10)
now = time.time()
S.npc_tick(now)
NA = 1
cap = S.CAPITALS[NA]
pl = cap // 100000
nbr = lambda p: [pl * 100000 + q for q in S.PORTAL_LINKS.get(p % 100000, ())]
caps = set(S.CAPITALS.values())
# a target with at least 3 neighbours: all but the target ours, target enemy
tgt = next(p for p in S.planet_provinces(pl) if p not in caps and len([q for q in nbr(p) if q not in caps]) >= 3
           and all(q not in caps for q in nbr(p)))
for q in nbr(tgt):
    S.set_province_owner(q, NA)
    for r in nbr(q):                                   # a road from the capital: make the neighbours' neighbours ours too
        if r not in caps and r != tgt:
            S.set_province_owner(r, NA)
S.set_province_owner(tgt, 3)
# own land connected to the capital: walk outward from the capital
S.set_province_owner(cap, NA)
fr = [cap]; seen = {cap}
while fr:
    p = fr.pop()
    for q in nbr(p):
        if q not in seen and q not in caps and q != tgt:
            seen.add(q); S.set_province_owner(q, NA); fr.append(q)
for m in S.npc_of(NA):
    m['task'] = None; m['walk'] = None; m.pop('post', None); m['rest_until'] = 0; m['state'] = 'active'
    for i in range(len(NP.health(m))): m['hl'][i] = 1.0
act = [m for m in S.npc_of(NA)]
lead, n = act[0], act[1]
c = {'pid': tgt, 'owner': 3, 'kind': 'enemy', 'garrison': 0, 'dist_cap': 2, 'def_power': 10.0}
S.npc_send([lead], c, now)
chk('0  the leader marches on the target', lead.get('task') and lead['task']['target'] == tgt, lead.get('task'))
ok = S.npc_no_target(n, now)
chk('A1 no target: joins the comrade attack', ok and n['task']['target'] == tgt and n['task']['kind'] == 'attack', n.get('task'))
chk('A2 same group as the leader, its own road', n['task'].get('group') == lead['task'].get('group') and n['task']['path'][-1] == tgt)
# B: fill the attack up
for m in act[2:S.NPC_NT_JOIN_MAX]:
    S.npc_follow(m, lead, now)
k = act[S.NPC_NT_JOIN_MAX]
chk('B0 attack is full', sum(1 for m in act if m.get('task') and m['task'].get('target') == tgt) >= S.NPC_NT_JOIN_MAX)
S.NPC_NT_STAGE = 1.0
ok = S.npc_no_target(k, now)
chk('B1 full attack not joined: moves up to a border post', ok and k['task']['kind'] == 'patrol' and k['task']['target'] != tgt, k.get('task'))
chk('B2 front posts may exceed the patrol cap', S.NPC_STAGE_MAX > S.NPC_PATROL_MAX)
# C: through npc_think
j = act[S.NPC_NT_JOIN_MAX + 1]
for m in act[2:S.NPC_NT_JOIN_MAX]:
    m['task'] = None
real_t, real_s = S.npc_targets, S.npc_join_surface
S.npc_targets = lambda nid, now: []
S.npc_join_surface = lambda n, now, force=None: False
S.NPC_IDLE_WHY.clear(); S.NPC_FALLBACK.clear()
pf = NP.PERSONAS[j['persona']]['follow']
NP.PERSONAS[j['persona']]['follow'] = 0       # (not the random 'follow' of its persona)
S.npc_think(j, now)
NP.PERSONAS[j['persona']]['follow'] = pf
chk('C1 npc_think with no candidates: the NPC gets a task', bool(j.get('task')), j.get('task'))
chk('C2 not counted as idle no_target', S.NPC_IDLE_WHY.get(NA, {}).get('no_target', 0) == 0, S.NPC_IDLE_WHY)
S.NPC_IDLE_LOG[0] = 0
S.npc_idle_report(now + 1)
S.LOG.flush()
lg = open('/tmp/mp/server110.log', encoding='utf-8').read()
chk('C3 idle report shows the fallback', 'no-target fallback join' in lg)
S.npc_targets, S.npc_join_surface = real_t, real_s
