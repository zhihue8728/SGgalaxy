import asyncio, struct, sys, os, time
os.chdir('/tmp/mp'); sys.path.insert(0, '/tmp/mp')
import sgserver as S
from mpclient import Client, s8
S.LOG = open('/tmp/mp/server5.log', 'w', encoding='utf-8')
PORT = 3995
def chk(name, ok, info=''): print(('PASS ' if ok else 'FAIL ') + name, info, flush=True)
def sess(name): return next(o for o in S.ONLINE if getattr(o, 'acc', '') == name)

async def goto(X, MAP):
    t = time.monotonic()
    X.send(bytes([0x2e]) + struct.pack('>IHHBB', MAP, 0x100, 0x1c0, 2, 0)); await asyncio.sleep(0.6)
    if X.got(0x1e, t):
        X.send(bytes([0x1b, 1]) + struct.pack('>IHH', MAP, 0x100, 0x1c0)); await asyncio.sleep(0.8)
    await asyncio.sleep(0.6)
    return t

async def main():
    S.ensure_unique_unit_ids()
    srv = await asyncio.start_server(S.handle, '127.0.0.1', PORT)
    A, B, C = Client('jjjjjjjj'), Client('kkkkkkkk'), Client('llllllll')
    for X in (A, B, C):
        await X.connect(PORT); await X.login()
    # ---------- case 1: attacker captures the POC
    P1 = 600300; S.set_province_owner(P1, 1)
    t = time.monotonic()
    tc = await goto(C, P1)
    b = S.BATTLES.get(P1)
    chk('C (nation 2) starts a battle in a nation-1 province', b is not None and b['defender'] == 1)
    chk('no aliens in an owned province', b is not None and not b['targets'], len(b['targets']) if b else None)
    chk('C sees no aliens', not any(p[2] == 'Alien' for p in C.puts(tc)))
    chk('defenders A and B notified (0x31)', bool(A.got(0x31, t)) and bool(B.got(0x31, t)),
        A.got(0x31, t)[0][4:60] if A.got(0x31, t) else None)
    chk('attacker C not notified', not C.got(0x31, t))
    ta = await goto(A, P1)
    chk('A was not asked/needs no permission (enemy side)', not C.got(0x24, ta))
    sa = sess('jjjjjjjj')
    chk('A entered the battle in battle mode', getattr(sa, 'battle', None) is b and any(x[9] == 1 for x in A.got(0x17, ta)),
        [x[:12].hex() for x in A.got(0x17, ta)])
    chk('A sees C units, C sees A units', any(p[2] == 'llllllll' for p in A.puts(ta)) and any(p[2] == 'jjjjjjjj' for p in C.puts(ta)))
    chk('POC belongs to the defender', all(p['owner'] == 1 for p in b['pocs'].values()))
    await asyncio.sleep(1.2)
    chk('no instant victory for the defender holding the POC', not b.get('won'))
    t5 = time.monotonic()
    C.send(bytes([0x5a]) + struct.pack('>IBIB', 1, 2, P1, 1)); await asyncio.sleep(S.BATTLE_END_DELAY + 2.5)
    rc, ra = C.got(0x25, t5), A.got(0x25, t5)
    chk('attacker C wins', rc and rc[0][1] == 0, [r[:2].hex() for r in rc])
    chk('defender A loses', ra and ra[0][1] == 1, [r[:2].hex() for r in ra])
    chk('province now nation 2', S.province_owner(P1) == 2, S.province_owner(P1))
    await asyncio.sleep(S.RESULT_SHOW_SECONDS + 1)
    # ---------- case 2: attacker leaves -> defenders win
    P2 = 600400; S.set_province_owner(P2, 1)
    await goto(C, P2); b2 = S.BATTLES.get(P2)
    ta = await goto(A, P2)
    chk('A defends P2', sess('jjjjjjjj') in b2['members'])
    t6 = time.monotonic()
    for uid in list(sess('llllllll').alive_units):                 # every unit retreats -> attacker leaves the field
        C.send(bytes([0x2f]) + struct.pack('>IHIiHHHH', uid, 0, 0, -1, 0x80, 0x80, 0x80, 0x80))
    await asyncio.sleep(S.BATTLE_END_DELAY + 2.5)
    ra = A.got(0x25, t6)
    chk('defender A wins when the attacker leaves', ra and ra[0][1] == 0, [r[:2].hex() for r in ra])
    chk('province still nation 1', S.province_owner(P2) == 1)
    await asyncio.sleep(S.RESULT_SHOW_SECONDS + 1)
    # ---------- case 3: time up -> defenders win
    S.BATTLE_SECONDS = 4
    P3 = 600500; S.set_province_owner(P3, 1)
    await goto(C, P3); b3 = S.BATTLES.get(P3)
    await goto(A, P3)
    t7 = time.monotonic(); await asyncio.sleep(4 + S.BATTLE_END_DELAY + 2.5)
    ra, rc = A.got(0x25, t7), C.got(0x25, t7)
    chk('time up: defender A wins', ra and ra[0][1] == 0, [r[:2].hex() for r in ra])
    chk('time up: attacker C loses', rc and rc[0][1] == 1, [r[:2].hex() for r in rc])
    for X in (A, B, C): X.close()
    await asyncio.sleep(1); srv.close()
asyncio.run(main())
