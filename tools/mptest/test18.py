"""test18: Acid Bura - a dying unit with the item bursts (lump 0x30 [uid][25] before 0x23) + alien weapon fx codes."""
import asyncio, struct, sys, os, time
os.chdir('/tmp/mp'); sys.path.insert(0, '/tmp/mp')
import sgserver as S
from mpclient import Client, s8
S.LOG = open('/tmp/mp/server18.log', 'w', encoding='utf-8')
PORT = 3987
def chk(n, ok, i=''): print(('PASS ' if ok else 'FAIL ') + n, i, flush=True)

async def main():
    S.ensure_unique_unit_ids()
    srv = await asyncio.start_server(S.handle, '127.0.0.1', PORT)
    accs, a = S.get_account('jjjjjjjj')
    a['units'][0].setdefault('items', []).append(S.ACID_BURA_ID)
    accs['jjjjjjjj'] = a; S.save_accounts(accs)
    A = Client('jjjjjjjj')
    await A.connect(PORT); await A.login(); await asyncio.sleep(1.0)
    A.send(bytes([0x2b, 1, 0])); await asyncio.sleep(0.3)
    caps = set(S.CAPITALS.values())
    prov = next(p for p in S.planet_provinces(S.current_planet(next(iter(S.ONLINE)))) if p not in caps)
    t = time.monotonic(); A.send(bytes([0x20, 8]) + struct.pack('>I', prov)); await asyncio.sleep(1.5)
    puts = [b for b in A.got(0x18, t)]
    codes = {struct.unpack_from('>I', b, 1)[0]: b for b in puts}
    sess = next(iter(S.BATTLES[prov]['members']))
    al = [tid for tid in sess.targets]
    chk('aliens put', len(al) > 0)
    st9s = [sess.targets[t]['put']['st9'][2] for t in al]
    chk('alien weapon codes are acid missiles (2xx)', all(200 < c < 300 for c in st9s if c) and any(st9s), st9s[:6])
    uid = sorted(sess.alive_units)[0]
    accs, a = S.get_account('jjjjjjjj')
    next(u for u in a['units'] if u['uid'] == uid).setdefault('items', []).append(S.ACID_BURA_ID)
    accs['jjjjjjjj'] = a; S.save_accounts(accs)
    chk('unit with Acid Bura is fighting', uid in sess.alive_units, uid)
    # move an alien next to the unit so the burst hits it
    t0 = al[0]; sess.targets[t0]['x'], sess.targets[t0]['y'] = sess.unit_pos[uid]
    hp0 = sess.targets[t0]['hp']
    t = time.monotonic(); A.lumps(bytes([0x1e]) + struct.pack('>I', uid)); await asyncio.sleep(1.5)
    msgs = [m for _tk, m in A.lump_msgs(t)]
    i30 = next((i for i, m in enumerate(msgs) if m[0] == 0x30 and m[5] == 25), None)
    i23 = next((i for i, m in enumerate(msgs) if m[0] == 0x23 and struct.unpack_from('>I', m, 1)[0] == uid), None)
    chk('burst lump 0x30 [uid][25] relayed before the death 0x23', i30 is not None and i23 is not None and i30 < i23,
        [m.hex() for m in msgs][:4])
    chk('server damaged the alien next to it', sess.targets.get(t0, {'hp': -1})['hp'] < hp0 or t0 not in sess.targets)
    chk('unit lost', uid not in sess.alive_units)
    A.close(); await asyncio.sleep(0.5); srv.close()
asyncio.run(main())
