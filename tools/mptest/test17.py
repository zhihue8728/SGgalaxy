"""test17: Battle Simulation Center - sim board 0x2d, sim join, aliens, nothing permanent (2026-10-22)."""
import asyncio, struct, sys, os, time
os.chdir('/tmp/mp'); sys.path.insert(0, '/tmp/mp')
import sgserver as S
from mpclient import Client, s8
S.LOG = open('/tmp/mp/server17.log', 'w', encoding='utf-8')
PORT = 3988
def chk(n, ok, i=''): print(('PASS ' if ok else 'FAIL ') + n, i, flush=True)

def parse_2d(b):
    o = 1; n = struct.unpack_from('>H', b, o)[0]; o += 4; out = []
    for _ in range(n):
        pid = struct.unpack_from('>I', b, o)[0]; o += 5; ln = b[o]; o += 1 + ln + 1
        own = struct.unpack_from('>I', b, o)[0]; o += 5
        fl = b[o]; o += 1; st = None
        if fl:
            st = b[o]; o += 4
        k = b[o]; o += 1; nats = []
        for _k in range(k):
            nats.append(struct.unpack_from('>I', b, o)[0]); o += 6
        out.append((pid, own, fl, st, nats))
    nb = struct.unpack_from('>H', b, o)[0]; o += 2
    assert nb == 0, nb
    if o != len(b):                       # 0x2c sub 0 tail: s8, u8 n {u32, 3 x u16}, u16 seconds
        o += 1 + b[o]; n2 = b[o]; o += 1 + 10 * n2 + 2
    assert o == len(b), (o, len(b))
    return out

async def main():
    S.ensure_unique_unit_ids()
    srv = await asyncio.start_server(S.handle, '127.0.0.1', PORT)
    A = Client('jjjjjjjj')
    await A.connect(PORT); await A.login(); await asyncio.sleep(1.0)
    _accs, a0 = S.get_account('jjjjjjjj')
    res0 = list(a0['resources']); units0 = [(u['uid'], u.get('hp'), u.get('xp')) for u in a0['units']]
    nat = a0['commander']['nation']
    t = time.monotonic(); A.send(bytes([0x2b, 1, 0])); await asyncio.sleep(0.5)
    m = A.got(0x2d, t)
    chk('sim board answers 0x2d', len(m) == 1)
    recs = parse_2d(m[0])
    caps = set(S.CAPITALS.values())
    chk('every non-capital province has an open battle', all(r[2] == 1 and r[3] == 1 for r in recs if r[0] not in caps)
        and all(r[2] == 0 for r in recs if r[0] in caps), recs[:3])
    chk('player nation listed (client offers JOIN)', all(nat in r[4] for r in recs))
    prov = next(r[0] for r in recs if r[0] not in caps)
    t = time.monotonic(); A.send(bytes([0x20, 8]) + struct.pack('>I', prov)); await asyncio.sleep(1.5)
    e = A.got(0x17, t)
    chk('sim join enters the province map in battle mode', e and struct.unpack_from('>I', e[-1], 1)[0] == S.SIM_BASE + prov and e[-1][10] == 1,
        e[-1].hex()[:40] if e else None)
    B = S.BATTLES.get(S.SIM_BASE + prov)        # (2026-10-27 19:59) simulations run on their own map id
    chk('battle registered as simulation', bool(B and B.get('sim') and B.get('defender') == 0))
    chk('aliens spawned', len(B['targets']) > 0 if B else False, len(B['targets']) if B else 0)
    chk('POCs held by the aliens', all(p['owner'] == 0 for p in B['pocs'].values()) if B else False)
    sess = next(iter(B['members']))
    # simulate permanent effects during the battle
    accs, a = S.get_account('jjjjjjjj')
    a['resources'] = [r + 999 for r in a['resources']]
    for u in a['units']:
        u['hp'] = 0; u['xp'] = u.get('xp', 0) + 5000
    accs['jjjjjjjj'] = a; S.save_accounts(accs)
    t = time.monotonic(); A.send(bytes([0x2b, 0, 1])); await asyncio.sleep(0.3)
    chk('normal map hides the simulation', all(not (r[2] and r[0] == prov) for r in parse_2d((A.got(0x2d, t) or [b'\x2d' + m[2:] for m in A.got(0x2c, t)])[0])))
    asyncio.get_event_loop().create_task(S.end_battle(sess, sess.battle_gen, True))
    await asyncio.sleep(S.BATTLE_END_DELAY + S.RESULT_SHOW_SECONDS + 1.0)
    _accs, a1 = S.get_account('jjjjjjjj')
    chk('resources restored', a1['resources'] == res0, (a1['resources'], res0))
    chk('units / HP / XP restored', [(u['uid'], u.get('hp'), u.get('xp')) for u in a1['units']] == units0)
    chk('province owner unchanged', S.province_owner(prov) == recs[[r[0] for r in recs].index(prov)][1])
    chk('back in the capital', sess.map == S.CAPITALS.get(nat), sess.map)
    chk('battle closed', S.SIM_BASE + prov not in S.BATTLES)
    # disconnect in the middle of a simulation also restores
    t = time.monotonic(); A.send(bytes([0x2b, 1, 0])); await asyncio.sleep(0.3)
    A.send(bytes([0x20, 8]) + struct.pack('>I', prov)); await asyncio.sleep(1.2)
    accs, a = S.get_account('jjjjjjjj'); a['resources'] = [0] * 5; accs['jjjjjjjj'] = a; S.save_accounts(accs)
    A.close(); await asyncio.sleep(0.8)
    chk('disconnect restores', S.get_account('jjjjjjjj')[1]['resources'] == res0)
    srv.close()
asyncio.run(main())
