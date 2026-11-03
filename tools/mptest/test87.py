"""test87 (user 2026-10-27 22:06 "NPCs must use aircraft"): most NPC commanders have an aviation branch, every NPC
that can field armed aircraft has an AIR platoon in its roster, and the air platoon goes into battles (more so
against an enemy without anti-air)."""
import os, sys, time, random
os.chdir('/tmp/mp'); sys.path.insert(0, '/tmp/mp')
for f in ('npcs.json', 'world.json'):
    if os.path.exists(f): os.remove(f)
import sgserver as S
S.LOG = open('/tmp/mp/server87.log', 'w', encoding='utf-8')
S.save_world = lambda w: None; S.npc_save = lambda force=False: None
def chk(n, ok, i=''): print(('PASS ' if ok else 'FAIL ') + n, i, flush=True)
random.seed(3)
now = time.time()
S.npc_tick(now)
allm = [n for nid in range(1, 13) for n in S.npc_of(nid)]
for nid in range(1, 13):
    S.npc_ensure_roster(nid)
avi = [n for n in allm if S.npc_profile(n)["br"].get("avi", 1) > 1]
chk('most NPC commanders have an aviation branch', len(avi) >= 0.6 * len(allm), f'{len(avi)}/{len(allm)}')
pool = {p["code"]: p for p in S.npc_pool()}
can = [n for n in allm if any(p.get("air") and S.npc_can_field(n, p) for p in S.npc_pool())]
withair = [n for n in can if any(pool.get(c, {}).get("air") for c, _l in n["squad"])]
chk('NPCs that can field aircraft carry them', can and len(withair) >= 0.9 * len(can), f'{len(withair)}/{len(can)}')
chk('there are such NPCs on every planet tier', len(can) >= 0.3 * len(allm), f'{len(can)}/{len(allm)}')
roles = [r for n in withair for r, _k, _i in S.npc_platoons(n)]
chk('they have an AIR platoon', 'air' in roles)
air_k = [S.npc_platoons(n) for n in withair[:30]]
ok = all(any(r == 'air' and pool.get(k, {}).get('air') for r, k, _i in pl) for pl in air_k)
chk('the air platoon really is aircraft', ok)
# picked for a battle against an enemy without anti-air
n = withair[0]
th = {"air": 0.0, "aa": 0.0, "rows": {0: 1.0}, "armor": 5, "n": 10}
S.battle_threat = lambda ctx, nid: th
got = 0
for _ in range(10):
    pk = S.npc_pick_platoons(n, n["nation"], 4, ctx={})
    got += any(r == 'air' for _k, r, _i in pk)
chk('the air platoon goes into battle (enemy without anti-air)', got >= 8, got)
