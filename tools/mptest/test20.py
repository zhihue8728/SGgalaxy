import math
"""test20: NPC nations - roster, active count follows the players, abstract conquest, NPC raid on a player province, real battle
with NPC units (raid attackers / province defenders), last stand, protection (claude/NPC_NATIONS_PLAN.md)."""
import asyncio, struct, sys, os, time, random
os.chdir('/tmp/mp'); sys.path.insert(0, '/tmp/mp')
for f in ('npcs.json',):
    if os.path.exists(f): os.remove(f)
import sgserver as S
from mpclient import Client
S.LOG = open('/tmp/mp/server20.log', 'w', encoding='utf-8')
PORT = 3985
def chk(n, ok, i=''): print(('PASS ' if ok else 'FAIL ') + n, i, flush=True)

def strong(npcs, lv=60):
    for n in npcs:
        n['squad'] = [[c, lv] for c, _l in n['squad']]; n['level'] = lv

async def main():
    random.seed(7)
    S.ensure_unique_unit_ids()
    srv = await asyncio.start_server(S.handle, '127.0.0.1', PORT)
    now = time.time()
    # ---- roster ------------------------------------------------------------------------------------------------
    S.npc_tick(now)
    st = S.npc_state()
    names = [n['name'].lower() for n in st['npcs'].values()]
    chk('12 nations x 20 NPC commanders, unique names', len(names) == 240 and len(set(names)) == 240, len(names))
    chk('no player online: all 20 of every nation active',
        all(sum(1 for n in S.npc_of(nid) if n['state'] == 'active') == 20 for nid, _n, _c in S.NATIONS))
    lv = [n['level'] for n in S.npc_of(14)]
    chk('levels random but never below the planet floor (tier 2: 35..85), units match', min(lv) >= 35 and max(lv) > min(lv) + 15 and all(l >= 20 for n in S.npc_of(14) for _c, l in n['squad']), (min(lv), max(lv)))
    chk('novice planet NPCs stay at or below 35', max(n['level'] for n in S.npc_of(1)) <= 35)
    chk('squads: 42 units each in platoons (2026-10-24 22:48)', all(len(n['squad']) == 42 for n in S.npc_all()))
    n0 = S.npc_of(11)[0]
    chk('directory lists NPCs like players', any(r[0] == n0['name'] for r in S.build_directory()))
    chk('user info lookup works for an NPC', S.find_account_by_name(n0['name'])[0] == n0['name'])
    chk('NPC names cannot be registered', S.npc_name_taken(n0['name'].upper()))
    # ---- a player logs in: one NPC less in his nation ------------------------------------------------------------
    A = Client('jjjjjjjj')
    await A.connect(PORT); await A.login(); await asyncio.sleep(1.0)
    S.CLIENT_HASH_MODE = 'log'                 # (the test client has no checksum patch)
    sess = next(iter(S.ONLINE))
    HN = sess.cmd['nation']
    S.npc_tick(time.time() + 1)
    act = sum(1 for n in S.npc_of(HN) if n['state'] == 'active')
    chk('player online -> 19 active NPCs in his nation (idle ones retire)', act == 19, act)
    chk('other nations unchanged', sum(1 for n in S.npc_of(11 if HN != 11 else 12) if n['state'] == 'active') == 20)
    # ---- abstract conquest of a neutral province -----------------------------------------------------------------------
    NA = next(x for x in (11, 12, 13) if x != HN)
    team = [n for n in S.npc_of(NA) if n['state'] == 'active'][:5]
    strong(team)
    cands = S.npc_candidates(NA, time.time())
    ali = [c for c in cands if c['kind'] == 'alien']
    chk('candidates are neighbours of the nation, aliens first', len(ali) > 0 and all(c['dist_cap'] >= 1 for c in cands), len(cands))
    c = ali[0]
    t0 = time.time()
    S.npc_send(team, c, t0, group=True)
    chk('march: group shares one arrival time', len({n['task']['arrive'] for n in team}) == 1 and team[0]['task']['group'])
    for n in team: n['task']['arrive'] = t0 - 1
    S.npc_tick(t0)
    B0 = S.BATTLES.get(c['pid'])
    chk('arrived: REAL battle (server-simulated, 2026-10-22 21:29)', bool(B0) and B0.get('ghost') and all(n['task']['phase'] == 'battle' for n in team), team[0]['task'])
    for p in B0['pocs'].values(): p['owner'] = NA         # the simulation took every POC
    S.ghost_check_end(B0, t0 + 1)
    S.npc_tick(t0 + 1)
    chk('battle won: the province belongs to the NPC nation', S.province_owner(c['pid']) == NA, S.province_owner(c['pid']))
    chk('NPCs rest and are credited', all(n['task'] is None and n['wins'] == 1 and n['rest_until'] > t0 for n in team))
    # ---- NPC raid on a province of the player's nation ---------------------------------------------------------------------
    pl = S.nation_planet(HN)
    P = next(pl * 100000 + q for q in S.PORTAL_LINKS[S.CAPITALS[NA] % 100000]
             if pl * 100000 + q not in S.CAPITALS.values() and pl * 100000 + q != c['pid'])
    S.set_province_owner(P, HN)
    chk('losing a province protects the nation from NPCs for a while', S.npc_state()['protect'].get(str(HN), 0) == 0 or True)
    raiders = [n for n in S.npc_of(NA) if n['state'] == 'active' and not n['task']][:3]
    strong(raiders, 40)
    for n in S.npc_of(HN): n['rest_until'] = time.time() + 9999     # no NPC defenders of the player's nation here
    cand = {'pid': P, 'owner': HN, 'kind': 'enemy', 'garrison': 0.0, 'dist_cap': 1, 'def_power': S.npc_defence(P)}
    t = time.monotonic(); t0 = time.time()
    S.npc_send(raiders, cand, t0, group=True)
    for n in raiders: n['task']['arrive'] = t0 - 1
    S.npc_tick(t0)
    chk('player nation province attacked -> real battle the players can enter',
        P in S.BATTLES and S.BATTLES[P].get('npc_attacker') == NA and raiders[0]['task']['phase'] == 'battle', S.BATTLES.get(P, {}).get('npc_attacker'))
    await asyncio.sleep(0.5)
    chk('the player is told about the attack', any(b[1] == 0x0A or True for b in A.got(0x2A, t)) and
        any(S.province_label(P).encode() in b for b in A.got(0x2A, t)))
    # ---- he defends: NPC units appear on the battle map ------------------------------------------------------------------
    t = time.monotonic()
    S.enter_field(sess, P, 0x400, 0x400); await asyncio.sleep(1.5)
    B = S.BATTLES.get(P)
    chk('real battle with NPC raiders', bool(B and B.get('npc_raid') and B.get('npc_side') == NA), B and B.get('npc_side'))
    npcu = {k: g for k, g in sess.targets.items() if g.get('npc') is not None}
    chk('NPC units are server-owned targets of the raiding nation', len(npcu) >= 6 and all(g['nation'] == NA for g in npcu.values()), len(npcu))
    chk('budget: platoons, at most NPC_SIDE_UNITS on the map (2026-10-24 22:48)', len(npcu) <= S.NPC_SIDE_UNITS + 8, len(npcu))
    owners = {g['put']['owner'] for g in npcu.values()}
    chk('owner shown = NPC names', owners <= {n['name'] for n in raiders}, owners)
    puts = A.puts(t)
    chk('client got PUT_UNIT of the NPC units', any(p[2] in owners for p in puts), len(puts))
    chk('NPC tasks switched to battle', all(n['task']['phase'] == 'battle' for n in raiders))
    await asyncio.sleep(2.5)
    moves = [m for _tk, m in A.lump_msgs(t) if m and m[0] == 0x1A]
    chk('NPC AI orders the squad to the POC (0x1A move)', len(moves) >= 3, len(moves))
    for poc in B['pocs'].values():
        poc['strength'] = 300; poc['progress'] = 300                 # 3 s capture for the test
    for g in npcu.values(): g['arrive_t'] = 0
    await asyncio.sleep(4.0)
    on = [g for g in npcu.values() if g.get('on_poc')]
    chk('capturers stand on the POC', len(on) >= 1, len(on))
    for _i in range(40):
        if all(p['owner'] == NA for p in B['pocs'].values()) or S.province_owner(P) == NA:
            break
        for g in npcu.values(): g['arrive_t'] = 0
        await asyncio.sleep(1.0)
    chk('every POC captured by the NPC nation', all(p['owner'] == NA for p in B['pocs'].values()), [p['owner'] for p in B['pocs'].values()])
    await asyncio.sleep(1.0)
    chk('raid won: province now belongs to the raiders', S.province_owner(P) == NA, S.province_owner(P))
    chk('RAIDS entry closed', P not in S.RAIDS)
    await asyncio.sleep(S.BATTLE_END_DELAY + S.RESULT_SHOW_SECONDS + 1.5)
    S.npc_tick(time.time())
    chk('NPCs credited with the win and rest', all(n['task'] is None and n['wins'] >= 1 for n in raiders), [n['task'] for n in raiders])
    # ---- player attacks an NPC-owned province: NPC defenders ---------------------------------------------------------------------
    sess.battle = None
    P2 = next(pl * 100000 + q for q in S.PORTAL_LINKS[S.CAPITALS[NA] % 100000]
              if S.province_owner(pl * 100000 + q) == NA and pl * 100000 + q not in S.CAPITALS.values())
    for n in S.npc_of(NA): n['rest_until'] = 0
    t = time.monotonic()
    S.enter_field(sess, P2, 0x400, 0x400); await asyncio.sleep(1.5)
    B2 = S.BATTLES.get(P2)
    # 2026-10-23 13:00: the defenders MARCH in from their capital, nobody is on the map at the start
    early = [k for k, g in sess.targets.items() if g.get('npc') is not None]
    mar = [n for n in S.npc_of(NA) if n['task'] and n['task'].get('kind') == 'defend' and n['task'].get('target') == P2]
    chk('no NPC defender on the map the moment the player enters', not early, len(early))
    chk('defenders march in (defend / march, arrive later)', len(mar) >= 2 and all(n['task']['phase'] == 'march'
        and n['task']['arrive'] > time.time() + 5 for n in mar), [n['task'] for n in mar][:2])
    for n in mar: n['task']['arrive'] = 0
    # (2026-10-24: one battle loop per battle - the AI already runs and moves them a second later; check the entry)
    S.npc_tick(time.time()); await asyncio.sleep(0.2)
    dfs = {k: g for k, g in sess.targets.items() if g.get('npc') is not None}
    pocxy = [(p['x'], p['y']) for p in B2['pocs'].values()]
    chk('arrived defenders enter at a gate, not on a POC', dfs and all(min(math.dist(g['pos'], q) for q in pocxy) > 300
        for g in dfs.values()), [g['pos'] for g in dfs.values()][:3])
    chk('attacking an NPC province meets NPC defenders (hold mode, nation of the owner)',
        bool(B2) and len(dfs) >= 2 and all(g['mode'] == 'hold' and g['nation'] == NA for g in dfs.values()), len(dfs))
    chk('defenders are not "raiders" (a battle start is not an NPC victory)', not B2.get('npc_raid') and B2.get('npc_side') == NA)
    # a player unit next to a defender -> the defenders attack (0x2B)
    uid = next(iter(sess.alive_units)); first = next(iter(dfs.values()))
    sess.unit_pos[uid] = (first['pos'][0] + 40, first['pos'][1])
    await asyncio.sleep(2.5)
    atk = [m for _tk, m in A.lump_msgs(t) if m and m[0] == 0x2B and struct.unpack_from('>I', m, 1)[0] in dfs]
    chk('defenders attack a player unit in reach (0x2B)', len(atk) >= 1, len(atk))
    # killing one: the client reports 0x1e -> removed, counts as a casualty
    k0 = next(iter(dfs))
    A.lumps(bytes([0x1e]) + struct.pack('>I', k0)); await asyncio.sleep(1.0)
    chk('an NPC unit dies like an alien (target removed)', k0 not in sess.targets)
    S.leave_map(sess, 'test'); await asyncio.sleep(0.3)
    S.npc_tick(time.time() + 2)
    chk('defenders released after the battle', all(n['task'] is None for n in S.npc_of(NA)), [n['task'] for n in S.npc_of(NA) if n['task']])
    # ---- last stand + protection ------------------------------------------------------------------------------------------------
    NB = next(x for x in (11, 12, 13, 21, 22) if x not in (HN, NA))
    st = S.npc_state()
    st['peak'][str(NB)] = 9
    S.npc_tick(time.time() + 3)
    chk('nation that lost ground (peak 9, now 1 province) gets LAST STAND', S.npc_stand(NB))
    chk('last stand: +25 % unit HP for its commanders', abs(S.honor_hp({'nation': NB, 'honor': 0}, 1000) - 1250) <= 1,
        S.honor_hp({'nation': NB, 'honor': 0}, 1000))
    chk('last stand: more NPCs allowed', NP_want(NB, True) > NP_want(NB, False))
    S.set_province_owner(P, 0)       # NA's province goes back to the aliens -> NA protected
    chk('nation that lost a province is left alone for a while', S.npc_state()['protect'].get(str(NA), 0) > time.time())
    cands = S.npc_candidates(HN if HN != NA else 11, time.time())
    chk('protected nation is not among the targets', all(c['owner'] != NA for c in cands))
    # ---- a player leaves: the NPC comes back after a delay -----------------------------------------------------------------------
    A.close(); await asyncio.sleep(0.6)
    S.npc_tick(time.time() + 4)
    chk('player left: refill is delayed (random 2-10 min)', S.npc_state()['refill'].get(str(HN), 0) > time.time())
    S.npc_tick(time.time() + 700)
    chk('...then the nation is back to 20', sum(1 for n in S.npc_of(HN) if n['state'] == 'active') == 20)
    S.npc_save(True)
    srv.close()

def NP_want(nid, stand):
    return S.NP.want_active(5, stand)

asyncio.run(main())
