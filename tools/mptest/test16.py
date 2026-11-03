"""test16: alien plan (aliens.py) - levels by tier/distance (novice capped by branch max), squads far from the
arrival, AI aggro/leash, garrison decrease, hunting-ground waves + boss, joiner squad, raids."""
import asyncio, struct, sys, os, time, json
os.chdir('/tmp/mp'); sys.path.insert(0, '/tmp/mp')
import sgserver as S, aliens as AL
from mpclient import Client
S.LOG = open('/tmp/mp/server16.log', 'w', encoding='utf-8')
PORT = 3916; S.BATTLE_END_DELAY = 1.0; S.RESULT_SHOW_SECONDS = 1.0; S.ALIEN_DEATH_FALLBACK = 1.0; S.JOIN_TIMEOUT = 1.0
fails = 0
def chk(n, ok, info=''):
    global fails; fails += 0 if ok else 1; print(('PASS ' if ok else 'FAIL ') + n, info, flush=True)
def sess(name): return next(o for o in S.ONLINE if getattr(o, 'acc', '') == name)
def put_ids(X, t, ptype):
    out = []
    for ts, b in X.inbox:
        if ts >= t and b[0] == ptype:
            o = 5 if ptype == 0x18 else 9
            n1 = b[o - (0 if ptype == 0x18 else 0)]
            out.append(b)
    return out
async def go(X, mapid, x=0x100, y=0x100):
    t = time.monotonic(); X.send(bytes([0x2e]) + struct.pack('>IHHBB', mapid, x, y, 1, 0)); await asyncio.sleep(0.8); return t
def setnation(acc, nid, br=None):
    a = S.load_accounts(); c = a[acc]['commander']; c['nation'] = nid; c['tier'] = S.PLANET_TIER.get(S.nation_planet(nid), 1)
    if br is not None:
        for v in c['branches'].values(): v['level'] = br
    S.save_accounts(a)
async def main():
    S.ensure_unique_unit_ids()
    if S.WORLD is None: S.WORLD = S.load_world()
    for pl in (6, 2, 3):
        for p in S.planet_provinces(pl):
            if p not in S.CAPITALS.values(): S.set_province_owner(p, 0)
    S.WORLD['garrison'] = {}; S.save_world(S.WORLD)
    srv = await asyncio.start_server(S.handle, '127.0.0.1', PORT)
    # ---- 1. novice province: levels capped by branch max, squads far from the arrival
    setnation('jjjjjjjj', 4, br=6)
    X = Client('jjjjjjjj'); await X.connect(PORT); await X.login(); await asyncio.sleep(0.3)
    await go(X, 600708); s = sess('jjjjjjjj')
    lv = [t['level'] for t in s.targets.values()]
    chk('novice province has squads', len(s.targets) >= 6, len(s.targets))
    chk('novice levels <= branch max 6', max(lv) <= 6, lv)
    d = [AL.dist(t['home'], s.alien_meta['arrival']) for t in s.targets.values()]
    chk('aliens spawn >= 20 cells from the arrival', min(d) >= 640, [int(x) for x in d])
    chk('no ground-only rule broken: no air aliens on novice', all(not AL.ROLES[t['name']]['air'] for t in s.targets.values()))
    await asyncio.sleep(2.5)
    t0 = time.monotonic(); await asyncio.sleep(1.5)
    atk = [m for tk, m in X.lump_msgs(t0) if m[0] == 0x2B]
    chk('no instant map-wide aggro', not atk, len(atk))
    # aggro: put a player unit next to alien A
    aid, ag = next(iter(s.targets.items())); u = next(iter(s.alive_units))
    s.unit_pos[u] = (int(ag['pos'][0]) + 40, int(ag['pos'][1]))
    t1 = time.monotonic(); await asyncio.sleep(1.6)
    atk = [struct.unpack_from('>II', m, 1) for tk, m in X.lump_msgs(t1) if m[0] == 0x2B]
    sq = [k for k, v in s.targets.items() if v['squad'] == ag['squad']]
    chk('aggro + squad called for help', {a for a, _ in atk} >= set(sq), (atk, sq))
    # leash: target far away
    s.unit_pos[u] = (int(ag['home'][0]) + 3000, int(ag['home'][1]))
    t2 = time.monotonic(); await asyncio.sleep(2.2)
    mv = [struct.unpack_from('>I', m, 1)[0] for tk, m in X.lump_msgs(t2) if m[0] == 0x1A]
    chk('leash: alien walks back home', aid in mv, mv)
    # kills lower the garrison
    g0 = AL.garrison(S.WORLD, 600708)
    for tid in list(s.targets)[:3]:
        X.lumps(bytes([0x1e]) + struct.pack('>I', tid)); await asyncio.sleep(0.2)
    await asyncio.sleep(0.5)
    g1 = AL.garrison(S.WORLD, 600708)
    chk('kills lower the garrison', g1 < g0, (g0, round(g1, 1)))
    X.close(); await asyncio.sleep(1.5)
    # re-enter: fewer aliens
    AL_g = AL.garrison(S.WORLD, 600708); AL.set_garrison(S.WORLD, 600708, 20); S.save_world(S.WORLD)
    X = Client('jjjjjjjj'); await X.connect(PORT); await X.login(); await asyncio.sleep(0.3)
    S.BATTLES.pop(600708, None)
    await go(X, 600708); s = sess('jjjjjjjj')
    chk('garrison 20% -> 1 squad', len({t['squad'] for t in s.targets.values()}) == 1, len(s.targets))
    X.close(); await asyncio.sleep(1.5)
    # ---- 2. advanced: air squads possible, level range
    setnation('jjjjjjjj', 14, br=40)
    import random; random.seed(3)
    names = set(); lvs = []
    for k in range(6):
        sq = AL.province_units(2, 3, 100, 1)
        for q in sq: names |= set(q)
    chk('advanced planet can have air aliens', names & {'Oizys', 'Manta', 'Mamos'}, names)
    # ---- 3. hunting ground: waves + boss + no win before the last wave
    X = Client('jjjjjjjj'); await X.connect(PORT); await X.login(); await asyncio.sleep(0.3)
    await go(X, 210808); s = sess('jjjjjjjj')
    # (2026-10-24 18:05) caves have no waves / hives any more: aliens appear at random places until the run budget
    # is used up; victory = the whole run appeared and died (the demon star keeps the 3 waves + boss: test50)
    chk('cave run started (aliens + budget still to appear)', len(s.targets) > 0 and s.alien_meta.get('budget', 0) > 0,
        (len(s.targets), s.alien_meta.get('budget')))
    _ids = list(s.targets)
    for tid in _ids[:len(_ids) // 2]:
        X.lumps(bytes([0x1e]) + struct.pack('>I', tid)); await asyncio.sleep(0.05)
    await asyncio.sleep(1.5)
    chk('no victory while aliens are still to appear', not X.got(0x25))
    s.alien_meta['budget'] = 0; s.alien_meta['next_spawn'] = 10 ** 12
    for tid in list(s.targets):
        X.lumps(bytes([0x1e]) + struct.pack('>I', tid)); await asyncio.sleep(0.05)
    await asyncio.sleep(2.0)
    r = X.got(0x25)
    chk('victory when the whole run is dead', bool(r), len(r))
    X.close(); await asyncio.sleep(2.0)
    # ---- 4. joiner brings one more squad
    setnation('jjjjjjjj', 14, br=40); setnation('kkkkkkkk', 14, br=40)
    X = Client('jjjjjjjj'); Y = Client('kkkkkkkk')
    for C in (X, Y): await C.connect(PORT); await C.login()
    await asyncio.sleep(0.3)
    S.BATTLES.pop(200807, None)
    await go(X, 200807); s = sess('jjjjjjjj'); n0 = len(s.targets)
    ty = time.monotonic(); Y.send(bytes([0x2e]) + struct.pack('>IHHBB', 200807, 0x100, 0x100, 1, 0)); await asyncio.sleep(0.6)
    if Y.got(0x1e, ty):
        Y.send(bytes([0x1b, 2]) + struct.pack('>IHH', 200807, 0x100, 0x100)); await asyncio.sleep(0.4)
    await asyncio.sleep(2.0)
    chk('joiner -> +1 squad', len(s.targets) > n0, (n0, len(s.targets)))
    d50 = [b for ts, b in X.inbox if ts >= ty and b[0] == 0x50]
    chk('new squad sent as delayed put (0x50) to the first player', len(d50) >= 1, len(d50))
    X.close(); Y.close(); await asyncio.sleep(2.0)
    # ---- 5. raid: undefended -> lost; defended -> repelled
    AL.RAID_DEFEND_SECONDS = 3
    S.set_province_owner(200708, 14); AL.set_garrison(S.WORLD, 200707, 100)
    S.RAIDS.clear(); S.RAIDS[200708] = {"nation": 14, "until": time.time() + 2, "from": 200707}
    task = asyncio.get_event_loop().create_task(S.raid_cycle())
    await asyncio.sleep(32)
    chk('undefended raid -> province lost', S.province_owner(200708) == 0, S.province_owner(200708))
    S.set_province_owner(200708, 14)
    S.RAIDS[200708] = {"nation": 14, "until": time.time() + 120, "from": 200707}
    X = Client('jjjjjjjj'); await X.connect(PORT); await X.login(); await asyncio.sleep(0.3)
    S.BATTLES.pop(200708, None)
    await go(X, 200708); s = sess('jjjjjjjj')
    chk('defender meets raid aliens', len(s.targets) > 0 and all(t.get('raid') for t in s.targets.values()), len(s.targets))
    for tid in list(s.targets):
        X.lumps(bytes([0x1e]) + struct.pack('>I', tid)); await asyncio.sleep(0.05)
    await asyncio.sleep(2.5)
    chk('raid repelled -> province kept, raid over', S.province_owner(200708) == 14 and 200708 not in S.RAIDS,
        (S.province_owner(200708), list(S.RAIDS)))
    task.cancel(); X.close(); srv.close()
    print('FAILS', fails)
asyncio.run(main())
