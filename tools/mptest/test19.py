import asyncio, struct, sys, os, time
os.chdir('/tmp/mp'); sys.path.insert(0, '/tmp/mp')
import sgserver as S
from mpclient import Client
S.LOG = open('/tmp/mp/server19.log', 'w', encoding='utf-8')
def chk(n, ok, i=''): print(('PASS ' if ok else 'FAIL ') + n, i, flush=True)
async def main():
    S.ensure_unique_unit_ids()
    srv = await asyncio.start_server(S.handle, '127.0.0.1', 3986)
    A = Client('jjjjjjjj'); await A.connect(3986); await A.login(); await asyncio.sleep(1)
    sess = next(iter(S.ONLINE))
    cap = S.CAPITALS[sess.cmd['nation']]
    prov = next(p for p in S.planet_provinces(S.current_planet(sess)) if p not in S.CAPITALS.values())
    t = time.monotonic(); S.enter_field(sess, prov + 10000, 0x400, 0x400); await asyncio.sleep(1.5)
    e = A.got(0x17, t)[-1]; n = e[22]
    objs = [struct.unpack_from('>IHHHBI', e, 23 + 15 * i) for i in range(n)]
    # (18:05) no hive nests: no minimap markers, the aliens appear at random places until the run budget is used up
    hives = [t_ for t_, g in sess.targets.items() if g.get('hive')]
    chk('cave: no hive nests and no hive markers', not hives and not objs, (objs, len(hives)))
    sq = {}
    for g in sess.targets.values():
        sq.setdefault(g.get('squad'), set()).add(g['name'])
    chk('squads are one species', all(len(v) == 1 for v in sq.values()), sq)
    # (2026-10-27 14:05) half the cave squads hunt, the others patrol (or wander when the map has no spawn spots)
    _modes = {g.get('squad'): g.get('mode') for g in sess.targets.values()}
    chk('cave squads: hunters and patrols', 'hunt' in _modes.values() and set(_modes.values()) & {'patrol', 'wander'}
        and all(g.get('hunter') == (g.get('mode') == 'hunt') for g in sess.targets.values()), _modes)
    chk('cave: more aliens at the start (60 % of x1.5)', len(sess.targets) >= int(S.AL.CAVE_TOTAL[1][1] * 0.5 * 0.6), len(sess.targets))
    meta = sess.alien_meta; n0 = len(sess.targets); b0 = meta['budget']
    meta['next_spawn'] = 0
    for _ in range(30):
        await asyncio.sleep(0.2)
        if len(sess.targets) > n0: break
    chk('cave: more aliens appear at random places (budget goes down)', len(sess.targets) > n0 and meta['budget'] < b0,
        (n0, len(sess.targets), b0, meta['budget']))
    import battlefield as BF
    v = dict(kind='hive', event='death', same=lambda a, b: a == b, members=[('k', 1, False)], enemies=0, hives=0)
    chk('cave victory only when the whole run appeared and died',
        BF.judge(dict(v, budget=5)) is None and BF.judge(dict(v, budget=0, enemies=3)) is None
        and (BF.judge(dict(v, budget=0)) or {}).get('tag') == 'hive')
    # province: modes
    t = time.monotonic(); S.enter_field(sess, prov, 0x400, 0x400); await asyncio.sleep(1.5)
    modes = {}
    for g in sess.targets.values(): modes.setdefault(g.get('squad'), (g['name'], g.get('mode')))
    chk('province squads guard/patrol/hunt', modes and list(modes.values())[0][1] == 'guard', modes)
    A.close(); await asyncio.sleep(0.3); srv.close()
asyncio.run(main())
