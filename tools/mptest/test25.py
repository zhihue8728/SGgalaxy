"""test25: clicking an NPC / another player's hero shows his profile; walking speed slow for free, fast for paid / boost."""
import asyncio, struct, sys, os, time
os.chdir('/tmp/mp'); sys.path.insert(0, '/tmp/mp')
for f in ('npcs.json',):
    if os.path.exists(f): os.remove(f)
import sgserver as S
from mpclient import Client
S.LOG = open('/tmp/mp/server25.log', 'w', encoding='utf-8')
PORT = 3991
def chk(n, ok, i=''): print(('PASS ' if ok else 'FAIL ') + n, i, flush=True)
async def main():
    S.ensure_unique_unit_ids()
    srv = await asyncio.start_server(S.handle, '127.0.0.1', PORT)
    S.npc_tick(time.time())
    A = Client('jjjjjjjj'); await A.connect(PORT); await A.login(); await asyncio.sleep(1.5)
    s = next(iter(S.ONLINE)); nid = s.cmd['nation']
    n0 = next(iter(s.npc_town)); npc = next(n for n in S.npc_of(nid) if n['id'] == n0)
    t = time.monotonic()
    A.send(bytes([0x23, 1]) + struct.pack('>I', S.NPC_TOWN_BASE + n0) + b'\0'); await asyncio.sleep(0.5)
    r = A.got(0x27, t)
    chk('click on a walking NPC -> 0x27 profile with his name', any(npc['name'].encode('latin-1') in b or S.NP.name_zh(npc['name']).encode('gbk') in b for b in r), len(r))
    # the second player's hero id
    B = Client('hhhhhhhh'); await B.connect(PORT); await B.login(); await asyncio.sleep(1.5)
    sb = next(o for o in S.ONLINE if o.acc == 'hhhhhhhh')
    t = time.monotonic()
    A.send(bytes([0x23, 1]) + struct.pack('>I', sb.hero_uid) + b'\0'); await asyncio.sleep(0.5)
    r = A.got(0x27, t)
    chk('click on another player hero id -> his profile', any(b'hhhhhhhh' in b for b in r), len(r))
    # speed
    chk('free account walks slow', S.town_speed({}) == S.TOWN_SPEED_SLOW < S.TOWN_SPEED_FAST)
    chk('paid account walks fast', S.town_speed({'paid': True}) == S.TOWN_SPEED_FAST)
    chk('boost walks fast, expired boost slow', S.town_speed({'speed_boost_until': time.time() + 60}) == S.TOWN_SPEED_FAST
        and S.town_speed({'speed_boost_until': time.time() - 1}) == S.TOWN_SPEED_SLOW)
    accs, a = S.get_account('jjjjjjjj'); a['paid'] = False; a.pop('speed_boost_until', None); a['resources'][3] = 100
    S.save_accounts(accs)
    t = time.monotonic()
    A.send(bytes([0x0A, 0]) + b'')  # noop
    S.speed_command(s); await asyncio.sleep(0.3)
    accs, a = S.get_account('jjjjjjjj')
    chk('/speed buys the boost for Ura', a.get('speed_boost_until', 0) > time.time() + 3 * 3600 - 60 and a['resources'][3] == 100 - S.SPEED_BOOST_URA, a['resources'])
    a.pop('speed_boost_until'); S.save_accounts(accs)
    srv.close()
asyncio.run(main())
