"""test42: NPC aggression / cooperation (patch_npc_aggr): an NPC that looks for a target rallies idle comrades (one group,
combined power), idle NPCs of a nation whose campaigns are capped join a marching comrade, campaigns allowed up to 3."""
import os, sys, time, random
os.chdir('/tmp/mp'); sys.path.insert(0, '/tmp/mp')
for f in ('npcs.json', 'world.json'):
    if os.path.exists(f): os.remove(f)
import sgserver as S
S.LOG = open('/tmp/mp/server42.log', 'w', encoding='utf-8')
S.save_world = lambda w: None; S.npc_save = lambda force=False: None
def chk(n, ok, i=''): print(('PASS ' if ok else 'FAIL ') + n, i, flush=True)
random.seed(11)
S.ensure_unique_unit_ids() if hasattr(S, 'ensure_unique_unit_ids') else None
now = time.time()
S.npc_tick(now)
nid = 1
act = [n for n in S.npc_of(nid) if n['state'] == 'active']
for n in act: n['task'] = None; n['rest_until'] = 0; n['think_at'] = 1e18; n['persona'] = 'warlike'
chk('nation has 20 active NPCs', len(act) >= 15, len(act))
S.npc_state()['gain'][str(nid)] = 0
S.NPC_RALLY_CHANCE = 1.0
S.NP.PERSONAS['warlike']['stay'] = 0.0
tries = 0
while not act[0]['task'] and tries < 30:
    tries += 1; S.npc_think(act[0], now)
t = act[0]['task']
chk('the NPC marched', bool(t), t and t.get('target'))
mates = [n for n in act if n['task'] and n is not act[0] and n['task'].get('target') == t['target']]
chk('idle comrades were rallied into the same group', len(mates) >= 1 and all(m['task'].get('group') == t.get('group') for m in mates), len(mates))
chk('group id set', t.get('group') is not None)
# capped campaigns: another idle NPC joins a marching comrade
S.NPC_JOIN_CHANCE = 1.0
free = next(n for n in act if not n['task'])
S.npc_may_attack = lambda nid_, now_: False
S.npc_think(free, now)
chk('capped nation: idle NPC joins the marching comrades', bool(free['task']) and free['task'].get('target') == t['target'], free['task'] and free['task'].get('target'))
chk('conquest mode (2026-10-27): NPC_CAMPAIGNS campaigns, no size cap', S.NPC_CAMPAIGNS >= 6 and S.NPC_MAX_SHARE >= 50 and S.NPC_LEADER_PENALTY == 0)
