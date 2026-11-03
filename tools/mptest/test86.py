"""test86 (user 2026-10-27 22:03 "NPCs on the strategic map patrol but hardly attack"): idle NPCs reinforce comrades
already FIGHTING at their target; a border patrol attacks a conquerable province next to its post; patrols are the
last resort (lower chance, fewer, shorter); more eager personas."""
import os, sys, time, random
os.chdir('/tmp/mp'); sys.path.insert(0, '/tmp/mp')
for f in ('npcs.json', 'world.json'):
    if os.path.exists(f): os.remove(f)
import sgserver as S
S.LOG = open('/tmp/mp/server86.log', 'w', encoding='utf-8')
S.save_world = lambda w: None; S.npc_save = lambda force=False: None
def chk(n, ok, i=''): print(('PASS ' if ok else 'FAIL ') + n, i, flush=True)
random.seed(7)
now = time.time()
S.npc_tick(now)
nid = 1
act = [n for n in S.npc_of(nid) if n['state'] == 'active']
for n in act: n['task'] = None; n['rest_until'] = 0; n['think_at'] = 1e18; n['persona'] = 'warlike'
S.npc_state()['gain'][str(nid)] = 0
S.NP.PERSONAS['warlike']['stay'] = 0.0
# a comrade that is already fighting at its target
lead = act[0]
cands = S.npc_targets(nid, now)
chk('the nation has conquest targets', bool(cands), len(cands))
S.npc_send([lead], cands[0], now)
lead['task']['phase'] = 'battle'
S.NPC_JOIN_CHANCE = 1.0
_may = S.npc_may_attack
S.npc_may_attack = lambda nid_, now_: False
free = act[1]
S.npc_think(free, now)
ft = free['task'] or {}
chk('idle NPC reinforces a comrade already fighting', ft.get('target') == lead['task']['target'] and ft.get('kind') == 'attack', ft.get('target'))
chk('... marching there on its own road (phase march, arrives later)', ft.get('phase') == 'march' and ft.get('arrive', 0) > now, ft.get('phase'))
S.npc_may_attack = _may
# a patrol next to a conquerable province leaves to attack it
pat = act[2]
target = cands[0]['pid']
post = None
for k, o in S.world_state()['owners'].items():
    pid = int(k)
    if int(o) == nid and any((pid // 100000) * 100000 + q == target for q in S.PORTAL_LINKS.get(pid % 100000, ())):
        post = pid; break
chk('found an own province next to the target', post is not None, post)
S.npc_state()['gain'][str(nid)] = 0
for m in act[3:]: m['task'] = None
lead['task'] = None
pat['task'] = {"kind": "patrol", "target": post, "origin": post, "depart": now - 100, "arrive": now - 50, "phase": "patrol",
               "since": now - 100, "path": [post], "until": now + 999}
S.NPC_PATROL_STRIKE = 1.0
S.npc_here = lambda n_, now_=None: post
ok = S.npc_patrol_strike(pat, now)
chk('a border patrol attacks a province next to its post', ok and pat['task'].get('kind') == 'attack', pat['task'] and pat['task'].get('kind'))
chk('patrols are the last resort', S.NPC_PATROL_CHANCE <= 0.25 and S.NPC_PATROL_MAX <= 3 and S.NPC_PATROL_STAY[1] <= 600)
chk('more eager: campaigns 6, hunts capped 3 (22:12), warlike min_win 0.15', S.NPC_CAMPAIGNS >= 6 and S.NPC_HUNT_MAX == 3
    and S.NP.PERSONAS['warlike']['min_win'] <= 0.15 and S.NP.THINK[1] <= 120)
