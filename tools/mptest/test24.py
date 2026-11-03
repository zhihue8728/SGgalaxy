"""test24: attacks on an NPC nation's province make its idle NPCs sortie at random (hostile NPCs / a player battle)."""
import asyncio, struct, sys, os, time, random
os.chdir('/tmp/mp'); sys.path.insert(0, '/tmp/mp')
for f in ('npcs.json', 'world.json'):
    if os.path.exists(f): os.remove(f)
import sgserver as S
from mpclient import Client
S.LOG = open('/tmp/mp/server24.log', 'w', encoding='utf-8')
PORT = 3989
def chk(n, ok, i=''): print(('PASS ' if ok else 'FAIL ') + n, i, flush=True)
async def main():
    random.seed(11)
    S.ensure_unique_unit_ids()
    srv = await asyncio.start_server(S.handle, '127.0.0.1', PORT)
    S.npc_tick(time.time())
    now = time.time()
    NA, NB = 11, 12
    P = next(c['pid'] for c in S.npc_candidates(NA, now) if c['kind'] == 'alien')
    S.set_province_owner(P, NB)           # a province of nation 12 ...
    S.npc_state()['gain'][str(NB)] = now + 99999   # ... whose land-grab cool-down is running
    att = [n for n in S.npc_of(NA) if n['state'] == 'active' and not n['task']][:3]
    S.npc_send(att, {'pid': P, 'owner': NB, 'kind': 'enemy', 'garrison': 0.0, 'dist_cap': 2, 'def_power': 100}, now, group=True)
    sup = 0
    for i in range(80):
        S.npc_react(now + i * 10)
        sup = sum(1 for n in S.npc_of(NB) if n['task'] and n['task'].get('kind') == 'support')
        if sup: break
    chk('hostile NPC attack -> idle NPCs of the owner sortie (cool-down ignored)', sup >= 1, sup)
    d0 = S.npc_defence(P)
    for n in S.npc_of(NB):                 # 2026-10-22: supporters march first (they can be intercepted on the way)
        if n['task'] and n['task'].get('kind') == 'support': n['task']['arrive'] = 0
    S.npc_tick(now)
    d1 = S.npc_defence(P)
    chk('supporters add to the defence once they arrived', d1 > d0, (d0, d1))
    for n in att: n['task'] = None
    S.npc_tick(now + 200)
    chk('supporters return when the attack is over', all(not (n['task'] and n['task'].get('kind') == 'support') for n in S.npc_of(NB)))
    # player attacks that province: NPC reinforcements join the running battle
    A = Client('jjjjjjjj'); await A.connect(PORT); await A.login(); await asyncio.sleep(1.0)
    s = next(iter(S.ONLINE))
    S.set_province_owner(P, s.cmd['nation'] + 0 if False else NB)
    # make the player an attacker of nation NB (different nation)
    if S.same_side(s.cmd['nation'], NB):
        S.set_province_owner(P, 11 if s.cmd['nation'] != 11 else 12)
    own = S.province_owner(P)
    for q in (S._route(S.CAPITALS[own], P) or [])[1:-1]:   # 2026-10-23: the road from the capital must be friendly
        S.set_province_owner(q, own)
    for n in S.npc_of(own): n['task'] = None; n['rest_until'] = 0; n['state'] = 'active'
    t = time.monotonic()
    S.enter_field(s, P, 0x400, 0x400); await asyncio.sleep(1.5)
    B = S.BATTLES.get(P)
    n0 = sum(1 for g in s.targets.values() if g.get('npc') is not None)
    for i in range(30):
        B['reinf_at'] = 0
        S.npc_react(time.time() + i)
    for n in S.npc_of(own):                # they march first, then walk into the battle
        if n['task'] and n['task'].get('kind') == 'defend' and n['task'].get('phase') == 'march': n['task']['arrive'] = 0
    S.npc_tick(time.time())
    await asyncio.sleep(0.5)
    n1 = sum(1 for g in s.targets.values() if g.get('npc') is not None)
    chk('reinforcements walk into the running battle', n1 > n0 and B.get('reinf', 0) >= 1, (n0, n1, B.get('reinf')))
    chk('client got the PUT_UNITs of the reinforcements', len(A.puts(t)) > 0)
    chk('reinforcement cap respected', B.get('reinf', 0) <= S.NPC_REINFORCE_MAX + 3 and B.get('reinf', 0) == S.NPC_REINFORCE_MAX + int(round(3 * S.npc_closeness(P))), (B.get('reinf'), S.npc_closeness(P)))

    road = S._route(S.CAPITALS[own], P) or []
    if len(road) >= 3:
        keep = S.province_owner(road[1]); S.set_province_owner(road[1], NA if not S.same_side(NA, own) else 0)
        others = [q for q in S.PORTAL_LINKS.get(P % 100000, ()) if S.same_side(S.province_owner(P // 100000 * 100000 + q), own)]
        for q in others: S.set_province_owner(P // 100000 * 100000 + q, NA)
        chk('cut off: no reinforcement road through an enemy province', S.npc_reinf_task('defend', own, P, time.time()) is None)
        S.set_province_owner(road[1], keep)
    S.leave_map(s, 'test'); await asyncio.sleep(0.3)
    srv.close()
asyncio.run(main())
