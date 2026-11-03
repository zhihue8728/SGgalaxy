"""test77 (user 2026-10-26 23:33): mark over the commander's head - regiment leader = 2 (ui-cabi silver emblem),
faction president = 1 (ui-pres gold); seen by himself and by other players in town; moves to the new leader."""
import asyncio, struct, sys, os, time
os.chdir('/tmp/mp'); sys.path.insert(0, '/tmp/mp')
import sgserver as S
from mpclient import Client
S.LOG = open('/tmp/mp/server77.log', 'w', encoding='utf-8')
PORT = 3977
def chk(n, ok, i=''): print(('PASS ' if ok else 'FAIL ') + n, i, flush=True)
def marks(cl, uid, since):
    """(mark, rank) of every 0x20 hero put for uid"""
    out = []
    for b in cl.got(0x20, since):
        o = 3; o += 1 + b[o]; o += 1 + b[o]
        if struct.unpack_from('>I', b, o)[0] == uid:
            out.append((b[-2], b[-1]))
    return out
async def main():
    S.ensure_unique_unit_ids()
    srv = await asyncio.start_server(S.handle, '127.0.0.1', PORT)
    A = Client('jjjjjjjj'); await A.connect(PORT); await A.login(); await asyncio.sleep(1.2)
    B = Client('hhhhhhhh'); await B.connect(PORT); await B.login(); await asyncio.sleep(1.2)
    sa = next(o for o in S.ONLINE if o.acc == 'jjjjjjjj'); sb = next(o for o in S.ONLINE if o.acc == 'hhhhhhhh')
    accs, a = S.get_account('jjjjjjjj'); a['resources'] = [10 ** 6] * 5; S.save_accounts(accs)
    _b, b = S.get_account('hhhhhhhh'); b['commander']['nation'] = a['commander']['nation']; _b['hhhhhhhh'] = b; S.save_accounts(_b)
    sb.cmd['nation'] = a['commander']['nation']
    for p in S.politics(a['commander']['nation']), :
        p['president'] = ''
    chk('nobody has a mark at first', S.hero_mark('jjjjjjjj') == 0)
    t = time.monotonic()
    S.regiment_command(sa, '/regiment create Wolves'); await asyncio.sleep(0.5)
    chk('founder = leader -> mark 2', S.hero_mark('jjjjjjjj') == 2)
    ma = marks(A, sa.hero_uid, t)
    chk('the leader sees his own mark (0x20 mark byte 2)', ma and ma[-1][0] == 2, ma)
    same_map = getattr(sa, 'map', None) == getattr(sb, 'map', None)
    mb = marks(B, sa.hero_uid, t)
    chk('another player on the map sees it', (not same_map) or (mb and mb[-1][0] == 2), (same_map, mb))
    chk('put_for_others carries the mark', any(p[0] == 0x20 and p[-2] == 2 for p in S.put_for_others(sa)))
    S.regiment_command(sb, '/regiment join Wolves'); await asyncio.sleep(0.3)
    chk('a member has no mark', S.hero_mark('hhhhhhhh') == 0)
    t = time.monotonic()
    S.regiment_command(sa, '/regiment leave'); await asyncio.sleep(0.5)
    chk('leader left -> heir gets mark 2, old leader 0', S.hero_mark('hhhhhhhh') == 2 and S.hero_mark('jjjjjjjj') == 0)
    mh = marks(B, sb.hero_uid, t)
    chk('the heir is told (0x20 with mark 2)', mh and mh[-1][0] == 2, mh)
    S.politics(a['commander']['nation'])['president'] = 'hhhhhhhh'
    chk('president beats regiment leader -> mark 1', S.hero_mark('hhhhhhhh') == 1)
    srv.close()
asyncio.run(main())
