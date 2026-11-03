import asyncio, struct, sys, os, time
os.chdir('/tmp/mp'); sys.path.insert(0, '/tmp/mp')
import sgserver as S
from mpclient import Client, s8
S.LOG = open('/tmp/mp/server2.log', 'w', encoding='utf-8')
PORT = 3998; MAP = 600200
def say(*a): print('>>', *a, flush=True)
def chk(name, ok, info=''): print(('PASS ' if ok else 'FAIL ') + name, info, flush=True)

async def main():
    S.ensure_unique_unit_ids()
    srv = await asyncio.start_server(S.handle, '127.0.0.1', PORT)
    A, B = Client('jjjjjjjj'), Client('kkkkkkkk')
    await A.connect(PORT); await A.login(); await B.connect(PORT); await B.login()
    await asyncio.sleep(0.5)
    # A starts a province battle
    t = time.monotonic()
    A.send(bytes([0x2e]) + struct.pack('>IHHBB', MAP, 0x100, 0x1c0, 2, 0))
    await asyncio.sleep(1.0)
    Bt = S.BATTLES.get(MAP)
    chk('battle created by A', Bt is not None and Bt['owner'].acc == 'jjjjjjjj')
    aliens = [p for p in A.puts(t) if p[2] == 'Alien']
    chk('A sees aliens', len(aliens) > 0, aliens)
    # B tries to enter the same province -> commander A must be asked
    t2 = time.monotonic()
    B.send(bytes([0x2e]) + struct.pack('>IHHBB', MAP, 0x100, 0x1c0, 2, 0))
    await asyncio.sleep(0.6)
    chk('B gets battle control dialog 0x1e', len(B.got(0x1e, t2)) == 1)
    B.send(bytes([0x1b, 1]) + struct.pack('>IHH', MAP, 0x100, 0x1c0))   # ATTACK
    await asyncio.sleep(0.6)
    req = A.got(0x24, t2)
    chk('A receives join request 0x24', len(req) == 1, [r.hex() for r in req])
    A.send(bytes([0x20, 3]) + s8('kkkkkkkk'))                      # accept (type 1 + 2)
    await asyncio.sleep(1.5)
    chk('B entered battle map (0x17)', any(struct.unpack_from('>I', b, 1)[0] == MAP for b in B.got(0x17, t2)))
    bp = B.puts(t2)
    chk('B sees aliens', any(p[2] == 'Alien' for p in bp), len(bp))
    chk('B sees A units', any(p[2] == 'jjjjjjjj' for p in bp))
    chk('A sees B units', any(p[2] == 'kkkkkkkk' for p in A.puts(t2)))
    chk('both in battle members', {o.acc for o in Bt['members']} == {'jjjjjjjj', 'kkkkkkkk'})
    chk('shared clock', abs(S.game_time(Bt['owner']) - S.game_time(next(o for o in Bt['members'] if o.acc == 'kkkkkkkk'))) <= 2,
        (S.game_time(Bt['owner']), S.game_time(next(o for o in Bt['members'] if o.acc == 'kkkkkkkk'))))
    # orders of B reach A at the same tick
    ua = [p[0] for p in A.puts(t) if p[2] == 'jjjjjjjj' and p[0] > 1000]
    ub = [p[0] for p in B.puts(t2) if p[2] == 'kkkkkkkk' and p[0] > 1000]
    say('units A', ua[:4], 'units B', ub[:4])
    t3 = time.monotonic()
    B.lumps(bytes([0x16]) + struct.pack('>IHHHB', ub[0], 0x500, 0x500, 0, 0))
    await asyncio.sleep(0.6)
    la = [(tk, m.hex()) for tk, m in A.lump_msgs(t3) if m[0] == 0x1a]
    lb = [(tk, m.hex()) for tk, m in B.lump_msgs(t3) if m[0] == 0x1a]
    chk('B move relayed to A', len(la) == 1, la)
    chk('same execution tick on A and B', la and lb and la[0][0] == lb[0][0], (la, lb))
    # both attack the aliens; make them weak to keep the test short
    tg = Bt['targets']; ids = list(tg)
    for i in ids: tg[i]['hp'] = 100
    t4 = time.monotonic()
    A.lumps(*[bytes([0x29]) + struct.pack('>II', ua[k % len(ua)], ids[k]) for k in range(0, len(ids), 2)])
    B.lumps(*[bytes([0x29]) + struct.pack('>II', ub[k % len(ub)], ids[k]) for k in range(1, len(ids), 2)])
    await asyncio.sleep(6)
    da = sorted({struct.unpack_from('>I', m, 1)[0] for tk, m in A.lump_msgs(t4) if m[0] == 0x23})
    db = sorted({struct.unpack_from('>I', m, 1)[0] for tk, m in B.lump_msgs(t4) if m[0] == 0x23})
    chk('all aliens dead (server)', not tg, list(tg))
    chk('A received every death', da == sorted(ids), da)
    chk('B received every death', db == sorted(ids), db)
    chk('no victory without POC', not Bt.get('won'))
    # B captures the POC (client report)
    t5 = time.monotonic()
    B.send(bytes([0x5a]) + struct.pack('>IBIB', 1, 1, MAP, 1))
    await asyncio.sleep(1.5)
    chk('victory after POC capture', Bt.get('won') is True)
    await asyncio.sleep(S.BATTLE_END_DELAY + 1.5)
    ra, rb = A.got(0x25, t5), B.got(0x25, t5)
    chk('A battle result 0x25', len(ra) >= 1, [r[:3].hex() for r in ra])
    chk('B battle result 0x25', len(rb) >= 1, [r[:3].hex() for r in rb])
    chk('result = victory for both', ra and rb and ra[0][1] == 0 and rb[0][1] == 0)
    chk('province now owned by nation 1', S.province_owner(MAP) == 1, S.province_owner(MAP))
    A.close(); B.close(); await asyncio.sleep(0.5); srv.close()
asyncio.run(main())
