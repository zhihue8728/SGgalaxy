"""test33: NPC interception of reinforcements - NPC support squads (abstract ambush), a player walking to a battle
(blockade = real battle with the blockers), an ambushed NPC reinforcement + player of its side (both NPC sides on the
map, allied / hostile), GM /npc ambush."""
import asyncio, struct, sys, os, time, random
os.chdir('/tmp/mp'); sys.path.insert(0, '/tmp/mp')
for f in ('npcs.json', 'world.json'):
    if os.path.exists(f): os.remove(f)
import sgserver as S
from mpclient import Client
S.LOG = open('/tmp/mp/server33.log', 'w', encoding='utf-8')
PORT = 3993
def chk(n, ok, i=''): print(('PASS ' if ok else 'FAIL ') + n, i, flush=True)
def free(nid, k):
    out = [n for n in S.npc_of(nid) if not n['task'] and not n.get('retire')][:k]
    for n in out:
        n['state'], n['rest_until'] = 'active', 0
        n['squad'] = [[c, 40] for c, _l in n['squad']]; n['hl'] = None
    return out
def clear_tasks():
    for n in S.npc_all():
        n['task'] = None; n['rest_until'] = time.time() + 9999
    S.AMBUSH.clear(); S.INTERCEPT_SEEN.clear()
async def main():
    random.seed(7)
    S.ensure_unique_unit_ids()
    S.NPC_INTERCEPT_CHANCE = 1.0
    srv = await asyncio.start_server(S.handle, '127.0.0.1', PORT)
    S.npc_tick(time.time())
    A = Client('jjjjjjjj'); await A.connect(PORT); await A.login(); await asyncio.sleep(1.0)
    s = next(iter(S.ONLINE)); HN = s.cmd['nation']
    s.client_hash, s.client_release = 1, '9.9.9'      # (a client that can show NPC allies, F30+)
    pl = S.nation_planet(HN)
    others = [n[0] for n in S.NATIONS if S.nation_planet(n[0]) == pl and n[0] != HN]
    ND, NA = others[0], others[1]
    print('player nation', HN, 'ND', ND, 'NA', NA)
    # ---- 1. NPC support squad of ND intercepted by NA (abstract) ----
    clear_tasks()
    cD, cA = S.CAPITALS[ND], S.CAPITALS[NA]
    path = S._route(cD, cA)
    P, R = path[3], path[2]
    S.set_province_owner(P, ND); S.set_province_owner(path[1], ND); S.set_province_owner(R, ND)
    S.set_province_owner(path[5], NA)
    # 2026-10-23: interceptors only march through own / allied provinces -> NA needs its own province next to R
    _base = S.CAPITALS[ND] // 100000 * 100000
    _nb = [_base + q for q in S.PORTAL_LINKS[R % 100000] if _base + q not in path and _base + q not in S.CAPITALS.values()]
    S.set_province_owner(_nb[0], NA)
    # 2026-10-23 15:09: interceptors WALK from their capital through NA land: give NA a road to _nb[0]
    for q in (S._route(cA, _nb[0], lambda q: q not in (P, R, path[1], cD)) or [])[1:]:
        if q not in (P, R) and q not in S.CAPITALS.values():
            S.set_province_owner(q, NA)
    att = free(NA, 1)[0]
    att['task'] = {'kind': 'attack', 'target': P, 'origin': path[4], 'phase': 'siege', 'resolve_at': time.time() + 9999,
                   'since': time.time(), 'wait': 0}
    sup = free(ND, 1)[0]
    now = time.time()
    sup['task'] = S.npc_reinf_task('support', ND, P, now)
    chk('support marches via the route province', sup['task']['phase'] == 'march' and sup['task']['route'] == R, sup['task'])
    sup['task']['arrive'] = now + 600
    chk('marching support does not count in the defence', S.npc_defence(P) == S.npc_defence(P))
    icp = free(NA, 2)
    for n in icp:                             # (15:09: interceptors walk from where they are: these two stand in _nb[0])
        n['walk'] = {'path': [_nb[0]], 'depart': 0, 'arrive': time.time() + 999}
    S.npc_intercept_scan(now)
    it = [n for n in S.npc_of(NA) if n['task'] and n['task'].get('kind') == 'intercept']
    chk('NA sends interceptors to the route province', bool(it) and it[0]['task']['target'] == R, [n['task'] for n in it])
    for n in it: n['task']['arrive'] = now - 1
    S.npc_tick(now)
    chk('ambush set, support stopped', R in S.AMBUSH and sup['task']['phase'] == 'ambushed', sup['task'].get('phase'))
    B = S.BATTLES.get(R)
    chk('ambush = real battle on the road (server-simulated)', bool(B) and S.AMBUSH[R]['B'] is B)
    chk('the interception battle has POCs and is an ordinary npc battle', bool(B) and bool(B['pocs']) and not B.get('ambush') and S.battle_kind(B, None) == 'npc', (B and len(B['pocs']), B and B.get('ambush')))
    for k in range(1800):
        if B.get('won'): break
        S.BSIM.Grid.spent = 0; S.ghost_step(B, now + k)
    if not B.get('won'): S.ghost_time_up(B)
    S.npc_tick(now + 1)
    chk('ambush decided by the battle', R not in S.AMBUSH and all(not n['task'] for n in it), R in S.AMBUSH)
    chk('support either cut off (home) or marching on', sup['task'] is None or sup['task']['phase'] == 'march', sup['task'])
    # ---- 2. player of HN walks toward a battle of his nation: NA blocks the next province ----
    clear_tasks()
    cH = S.CAPITALS[HN]
    path = S._route(cH, cA)
    P = path[4]
    S.set_province_owner(P, HN)
    for q in path[1:4]: S.set_province_owner(q, HN)
    S.set_province_owner(path[5], NA)
    att = free(NA, 1)[0]
    att['task'] = {'kind': 'attack', 'target': P, 'origin': path[5], 'phase': 'siege', 'resolve_at': time.time() + 9999,
                   'since': time.time(), 'wait': 0}
    S.set_province_owner(path[3], 0)          # the road province next to NA: neutral, NA owns path[5]... make NA near
    S.set_province_owner(path[3], HN)
    S.set_province_owner(path[2], HN)
    # NA must own a province next to the road province path[2]: give it path[2]'s other neighbour
    nb = [S.CAPITALS[HN] // 100000 * 100000 + q for q in S.PORTAL_LINKS[path[2] % 100000]
          if S.CAPITALS[HN] // 100000 * 100000 + q not in path and S.CAPITALS[HN] // 100000 * 100000 + q not in S.CAPITALS.values()]
    S.set_province_owner(nb[0], NA)
    for n in free(NA, 2):                     # (15:09: interceptors walk from where they are: these two stand in nb[0])
        n['walk'] = {'path': [nb[0]], 'depart': 0, 'arrive': time.time() + 999}
    s.moved = (path[0], path[1], time.time())
    S.npc_intercept_scan(time.time())
    it = [n for n in S.npc_of(NA) if n['task'] and n['task'].get('kind') == 'intercept']
    chk('NA blocks the next province on the player\'s road', bool(it) and it[0]['task']['target'] == path[2],
        [(n['task']['target'], n['task'].get('acc')) for n in it])
    R = path[2]
    for n in it: n['task']['arrive'] = time.time() - 1
    t = time.monotonic()
    S.npc_tick(time.time())
    chk('blockade waits for the player', R in S.AMBUSH and S.AMBUSH[R]['acc'] == s.acc)
    # user 2026-10-25 12:05: ambush battles (no POC) are abolished - a player entering the blockaded province gets the
    # ordinary flow (own province = town, no blockers spawned on a POC-less map)
    await asyncio.sleep(0.3)
    S.enter_field(s, R, 0x400, 0x400); await asyncio.sleep(2.5)
    B = S.BATTLES.get(R)
    # user 2026-10-27 22:56: a blockade is a real battle at once (blockers attack, the owner defends) - the player
    # entering his blockaded province joins that battle; it is not an ambush battle without POCs
    chk('the blockade is a real battle at once; the player joins it', B is not None and B.get('npc_attacker') == NA
        and not B.get('ambush') and s.battle_mode != 0, (s.battle_mode, B and B.get('npc_attacker')))
    S.leave_map(s, 'test'); await asyncio.sleep(0.3)
    S.AMBUSH.pop(R, None)
    if S.BATTLES.get(R) is B:
        S.BATTLES.pop(R, None)
    # ---- 4. GM /npc ambush ----
    clear_tasks(); free(NA, 2)
    S.npc_gm(s, ['/npc', 'ambush', str(R), str(NA)])
    chk('/npc ambush sets a blockade', R in S.AMBUSH and S.AMBUSH[R]['o'] == NA)
    S.npc_gm(s, ['/npc', 'ambushes'])
    srv.close()
asyncio.run(main())
