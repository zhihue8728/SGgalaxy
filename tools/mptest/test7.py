import asyncio, struct, sys, os, time
os.chdir('/tmp/mp'); sys.path.insert(0, '/tmp/mp')
import sgserver as S
from mpclient import Client, s8
S.LOG = open('/tmp/mp/server7.log', 'w', encoding='utf-8')
PORT = 3997
def chk(n, ok, i=''): print(('PASS ' if ok else 'FAIL ') + n, i, flush=True)
def sess(n): return next(o for o in S.ONLINE if getattr(o, 'acc', '') == n)

async def goto(X, MAP):
    t = time.monotonic()
    X.send(bytes([0x2e]) + struct.pack('>IHHBB', MAP, 0x100, 0x1c0, 2, 0)); await asyncio.sleep(0.6)
    return t

async def main():
    S.ensure_unique_unit_ids()
    srv = await asyncio.start_server(S.handle, '127.0.0.1', PORT)
    # (11-01) the fixture's nations changed: A,B nation 1, C nation 2 here; the provinces are neighbours of A's
    # capital (the old fixed 600800 / 600600 became a capital / not a neighbour)
    S.BF.MAX_PR_BY_TIER.update({1: 999, 2: 999, 3: 999})   # the PR cap (a later rule) is not what this test checks
    for acc, na in (('jjjjjjjj', 1), ('kkkkkkkk', 1), ('llllllll', 2)):
        accs, a = S.get_account(acc); a.setdefault('commander', {})['nation'] = na
        a['commander'].pop('mercenary', None); accs[acc] = a; S.save_accounts(accs)
    A, B, C = Client('jjjjjjjj'), Client('kkkkkkkk'), Client('llllllll')       # A,B nation 1; C nation 2
    for X in (A, B, C):
        await X.connect(PORT); await X.login()
    home = sess('jjjjjjjj').map; pl = home // 100000; caps = set(S.CAPITALS.values())
    nb = [pl * 100000 + q for q in S.PORTAL_LINKS.get(home % 100000, ()) if pl * 100000 + q not in caps]
    # ---- not a mercenary -> offer refused
    P = nb[0]; S.set_province_owner(P, 0)
    ta = await goto(A, P); b = S.BATTLES.get(P)
    tc = time.monotonic()
    C.send(bytes([0x20, 4]) + struct.pack('>II', P, 1)); await asyncio.sleep(0.6)
    chk('non-mercenary offer refused (no request to commander)', not A.got(0x24, tc) and sess('llllllll') not in b['members'])
    # ---- C becomes a mercenary and offers service to nation 1
    C.send(bytes([0xd6, 1])); await asyncio.sleep(0.5)
    chk('C is a mercenary', S.get_account('llllllll')[1].get('commander', {}).get('mercenary') is True)
    tc = time.monotonic()
    C.send(bytes([0x20, 4]) + struct.pack('>II', P, 1)); await asyncio.sleep(0.6)
    req = A.got(0x24, tc)
    chk('commander A gets mercenary request (type 4)', len(req) == 1 and req[0][1] == 4, [r.hex() for r in req])
    A.send(bytes([0x20, 6]) + s8('llllllll')); await asyncio.sleep(1.5)     # accept = type 4 + 2
    sc = sess('llllllll')
    chk('mercenary entered the battle on side 1', sc in b['members'] and S.side_nation(sc) == 1 and sc.cmd['nation'] == 2,
        (S.side_nation(sc), sc.cmd['nation']))
    cp = [p for p in A.puts(tc) if p[2] == 'llllllll']
    chk('A sees the mercenary units with nation 1', cp and all(p[3] == 1 for p in cp), [p[3] for p in cp][:3])
    chk('C sees A units as friendly (nation 1) and aliens', any(p[2] == 'jjjjjjjj' and p[3] == 1 for p in C.puts(tc))
        and any(p[2] == 'Alien' for p in C.puts(tc)))
    # ---- mercenary kills the aliens and captures the POC for side 1
    ids = list(b['targets'])
    for i in ids: b['targets'][i]['hp'] = 100
    uc = [p[0] for p in C.puts(tc) if p[2] == 'llllllll' and p[0] > 1000]
    t4 = time.monotonic()
    C.lumps(*[bytes([0x29]) + struct.pack('>II', uc[k % len(uc)], ids[k]) for k in range(len(ids))])
    await asyncio.sleep(6)
    chk('aliens dead via mercenary orders', not b['targets'], list(b['targets']))
    res0 = list(S.get_account('llllllll')[1]['resources'])
    xp0 = S.get_account('llllllll')[1]['commander'].get('honor', 0)
    t5 = time.monotonic()
    C.send(bytes([0x5a]) + struct.pack('>IBIB', 1, 1, P, 1)); await asyncio.sleep(S.BATTLE_END_DELAY + 2.5)
    chk('victory', b.get('won') is True)
    chk('province goes to the nation served (1), not the mercenary home (2)', S.province_owner(P) == 1, S.province_owner(P))
    rc, ra = C.got(0x25, t5), A.got(0x25, t5)
    chk('mercenary and commander get a win result', rc and ra and rc[0][1] == 0 and ra[0][1] == 0)
    res1 = S.get_account('llllllll')[1]['resources']
    chk('mercenary paid a bonus', sum(res1) > sum(res0), (res0, res1))
    await asyncio.sleep(S.RESULT_SHOW_SECONDS + 1.5)
    chk('contract ended after the battle (side reset)', getattr(sc, 'side_nation', None) is None)
    chk('nation of C unchanged', S.get_account('llllllll')[1]['commander'].get('nation', 2) == 2 or sc.cmd['nation'] == 2)
    # ---- mercenary serves the DEFENDER of an owned province (nation 1 owns P): B (nation 1) defends with C
    t6 = time.monotonic()
    D = Client('mmmmmmmm') if False else None
    # attacker = C on its own (nation 2 vs owner 1), A+B defend
    await goto(A, home); Q = nb[1]; S.set_province_owner(Q, 2)           # owned by nation 2 -> attacker A (nation 1)
    ta = await goto(A, Q); bq = S.BATTLES.get(Q)
    chk('A attacks nation 2 province, no aliens', bq and not bq['targets'] and bq['defender'] == 2)
    # mercenary C wanders in as a defender's ally? C belongs to nation 2 = the defender: enters directly (enemy side)
    tq = await goto(C, Q)
    chk('defender C (nation 2) enters without permission', sess('llllllll') in bq['members'] and not A.got(0x24, tq))
    # B (nation 1) now offers mercenary service?  B is not a mercenary -> refused
    tb = time.monotonic()
    B.send(bytes([0x20, 4]) + struct.pack('>II', Q, 2)); await asyncio.sleep(0.5)
    chk('non-mercenary B cannot serve nation 2', sess('kkkkkkkk') not in bq['members'])
    for X in (A, B, C): X.close()
    await asyncio.sleep(0.5)
asyncio.run(main())
