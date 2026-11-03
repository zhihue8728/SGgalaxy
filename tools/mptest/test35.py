"""test35: NPC battles are always REAL - server-simulated without players (ghost battles): neutral assault (aliens on the
map, units walk on the walk grid, fight, capture, result), player joins (sees every unit where the simulation has it),
leaves (simulation goes on), owned province with NPC defenders, hunt never captures, NPC-vs-NPC ambush."""
import asyncio, struct, sys, os, time, random
os.chdir('/tmp/mp'); sys.path.insert(0, '/tmp/mp')
for f in ('npcs.json', 'world.json'):
    if os.path.exists(f): os.remove(f)
import sgserver as S
from mpclient import Client
S.LOG = open('/tmp/mp/server35.log', 'w', encoding='utf-8')
PORT = 3995
def chk(n, ok, i=''): print(('PASS ' if ok else 'FAIL ') + n, i, flush=True)
def free(nid, k, lv=40):
    out = [n for n in S.npc_of(nid) if not n['task'] and not n.get('retire')][:k]
    for n in out:
        n['state'], n['rest_until'] = 'active', 0
        n['squad'] = [[c, lv] for c, _l in n['squad']]; n['hl'] = None
    return out
def run(B, secs, t0):
    for k in range(secs):
        if B.get('won'): return k
        S.BSIM.Grid.spent = 0
        S.ghost_step(B, t0 + k)
        S.npc_fresh_wave(B['ghost'], B, t0 + k)
    return secs
async def main():
    random.seed(11)
    S.ensure_unique_unit_ids()
    srv = await asyncio.start_server(S.handle, '127.0.0.1', PORT)
    S.npc_tick(time.time())
    A = Client('jjjjjjjj'); await A.connect(PORT); await A.login(); await asyncio.sleep(1.0)
    s = next(iter(S.ONLINE)); HN = s.cmd['nation']
    pl = S.nation_planet(HN)
    NA, ND = [n[0] for n in S.NATIONS if S.nation_planet(n[0]) == pl and n[0] != HN][:2]
    for n in S.npc_all(): n['rest_until'] = time.time() + 99999
    # ---- 1. neutral province: assault opens a real battle ----
    cand = [c for c in S.npc_candidates(NA, time.time()) if c['kind'] == 'alien']
    P = cand[0]['pid']
    team = free(NA, 2, 45)
    S.npc_send(team, cand[0], time.time(), group=True)
    for n in team: n['task']['arrive'] = time.time() - 1
    g0 = S.AL.garrison(S.world_state(), P)
    S.npc_tick(time.time())
    B = S.BATTLES.get(P)
    chk('assault -> real battle in BATTLES (ghost)', bool(B) and B.get('ghost') is not None and B['owner'] is B['ghost'])
    ali = [g for g in B['targets'].values() if g.get('npc') is None]
    npcs = [g for g in B['targets'].values() if g.get('npc') is not None]
    chk('aliens AND NPC units on the map', len(ali) >= 3 and len(npcs) >= 6, (len(ali), len(npcs)))
    chk('NPC tasks in battle phase', all(n['task']['phase'] == 'battle' for n in team))
    grid = S._walk_grid(S.alien_context(B['ghost'], P)[3])
    p0 = {k: g['pos'] for k, g in B['targets'].items()}
    t0 = time.time()
    run(B, 40, t0)
    moved = sum(1 for k, g in B['targets'].items() if k in p0 and S.BSIM.dist(p0[k], g['pos']) > 30)
    chk('units walk (simulated)', moved >= 3, moved)
    chk('every unit on walkable ground', all(grid.ok(*grid.cell(g['pos'])) for g in B['targets'].values()),
        [g['pos'] for g in B['targets'].values() if not grid.ok(*grid.cell(g['pos']))][:3])
    # ---- 2. a player joins the simulated battle ----
    t = time.monotonic()
    pos_sim = {k: (g['x'], g['y']) for k, g in B['targets'].items()}
    S.enter_field(s, P, 0x400, 0x400); await asyncio.sleep(1.5)
    chk('player JOINS the simulated battle', s.battle is B and s in B['members'], s.battle is B)
    puts = {p[0]: p for p in A.puts(t)}
    same = [k for k in pos_sim if k in puts]
    chk('the client gets every unit (PUT)', len(same) >= len(pos_sim) - 1, (len(same), len(pos_sim)))
    chk('units appear where the simulation had them (PUT x/y = simulated position)',
        all((B['targets'][k]['x'], B['targets'][k]['y']) == pos_sim[k] for k in same if k in B['targets']))
    chk('player is the commander now', B['owner'] is s)
    await asyncio.sleep(2.0)
    S.leave_map(s, 'test'); await asyncio.sleep(0.3)
    chk('player left: battle goes on, simulated', S.BATTLES.get(P) is B and B['owner'] is B['ghost'] and not B.get('won'))
    n_before = len(B['targets'])
    run(B, 400, time.time())
    caps = [p['owner'] for p in B['pocs'].values()]
    chk('they fight / capture: units die or POCs change hands', len(B['targets']) < n_before or NA in caps or B.get('won'), (n_before, len(B['targets']), caps))
    run(B, 1700, time.time())
    if not B.get('won'):
        S.ghost_time_up(B)
    chk('battle ends with a result', B.get('won') and P not in S.BATTLES and P in S.NPC_RESULT, S.NPC_RESULT.get(P))
    won = S.NPC_RESULT.get(P)
    chk('result applied (won = owner changed)', (S.province_owner(P) == NA) == bool(won), (won, S.province_owner(P)))
    S.npc_tick(time.time())
    chk('NPC tasks finished', all(not n['task'] for n in team))
    # ---- 3. owned province of ND: ND NPCs defend ----
    path = S._route(S.CAPITALS[ND], S.CAPITALS[NA])
    P2 = path[2]
    S.set_province_owner(P2, ND)
    for n in S.npc_of(ND): n['rest_until'] = 0
    free(ND, 3, 30)
    team2 = free(NA, 2, 45)
    S.npc_send(team2, {'pid': P2, 'owner': ND, 'kind': 'enemy', 'garrison': 0, 'dist_cap': 1, 'def_power': 10}, time.time(), group=True)
    for n in team2: n['task']['arrive'] = time.time() - 1
    S.npc_tick(time.time())
    B2 = S.BATTLES.get(P2)
    dn = {g['nation'] for g in (B2 or {}).get('targets', {}).values() if g.get('npc') is not None}
    chk('owned province: attackers and the owner\'s NPC defenders on the map', bool(B2) and dn == {NA, ND}, dn)
    chk('no aliens in an owned province', B2 and not any(g.get('npc') is None for g in B2['targets'].values()))
    # 2026-10-23: NPC units ENTER at a gate: none stands on a POC at the start, and every unit starts at a gate of the map
    gates = S.GATE_SPOTS.get(P2 % 100000, [])
    chk('province has gates', bool(gates), P2)
    near_gate = lambda tg: any(S.AL.dist((tg['home0'] if 'home0' in tg else tg['pos']), (gx, gy)) < 200 for _n, gx, gy in gates)
    st_units = [tg for tg in B2['targets'].values() if tg.get('npc') is not None]
    on_poc = [tg for tg in st_units if any(abs(tg['pos'][0] - p['x']) < 120 and abs(tg['pos'][1] - p['y']) < 120 for p in B2['pocs'].values())]
    chk('NPC units start at a gate, not on a POC', not on_poc and all(near_gate(tg) for tg in st_units), (len(on_poc), len(st_units)))
    # 2026-10-23: a second force of the attackers arriving while the battle runs ENTERS it through a gate
    team3 = free(NA, 1, 45)
    S.npc_send(team3, {'pid': P2, 'owner': ND, 'kind': 'enemy', 'garrison': 0, 'dist_cap': 1, 'def_power': 10}, time.time(), group=True)
    for n in team3: n['task']['arrive'] = time.time() - 1
    S.npc_tick(time.time())
    in_b = {g.get('npc') for g in B2['targets'].values()}
    chk('a later attacking force enters the running battle', all(n['id'] in in_b for n in team3) and all(n['task'] and n['task'].get('phase') == 'battle' for n in team3), (in_b, [n['task'] for n in team3]))
    run(B2, 1800, time.time())
    if not B2.get('won'): S.ghost_time_up(B2)
    chk('owned-province battle decided', B2.get('won') and P2 not in S.BATTLES, S.NPC_RESULT.get(P2))
    # ---- 4. hunt never captures ----
    cand = [c for c in S.npc_candidates(NA, time.time()) if c['kind'] == 'alien' and c['pid'] not in S.BATTLES]
    P3 = cand[0]['pid']
    h = free(NA, 1, 60)
    S.npc_send(h, cand[0], time.time()); h[0]['task']['hunt'] = True; h[0]['task']['arrive'] = time.time() - 1
    S.npc_tick(time.time())
    B3 = S.BATTLES.get(P3)
    chk('hunt = real battle', bool(B3) and B3.get('hunt'))
    for p in B3['pocs'].values(): p['owner'] = NA
    S.ghost_check_end(B3, time.time())
    chk('hunt "won" but the province is not taken', B3.get('won') and S.province_owner(P3) == 0, S.province_owner(P3))
    # ---- 5. NPC-vs-NPC ambush on the road ----
    S.AMBUSH.clear()
    R = path[4] if path[4] not in S.BATTLES else path[5]
    sup = free(ND, 1, 30)[0]
    sup['task'] = {'kind': 'support', 'target': P2, 'since': time.time(), 'phase': 'march', 'route': R, 'arrive': time.time() + 500}
    icp = free(NA, 1, 45)
    for n in icp:
        n['task'] = {'kind': 'intercept', 'target': R, 'origin': R, 'depart': time.time(), 'arrive': time.time() - 1, 'phase': 'march',
                     'since': time.time(), 'group': 77, 'vs': ND, 'P': P2, 'ref': [sup['id']], 'acc': None}
    S.npc_tick(time.time())
    B5 = S.BATTLES.get(R)
    side = {g['nation'] for g in (B5 or {}).get('targets', {}).values() if g.get('npc') is not None}
    chk('ambush = real battle with both NPC sides', bool(B5) and side == {NA, ND} and not B5['pocs'], side)
    run(B5, 1800, time.time())
    if not B5.get('won'): S.ghost_time_up(B5)
    S.npc_tick(time.time())
    chk('ambush decided, blockade gone', R not in S.AMBUSH and R not in S.BATTLES)
    chk('reinforcement either cut off or marching on', sup['task'] is None or sup['task'].get('phase') == 'march', sup['task'])
    srv.close()
asyncio.run(main())
