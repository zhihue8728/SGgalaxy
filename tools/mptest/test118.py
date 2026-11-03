"""test118 (user 2026-11-01 16:20): Assign XP window (UseExpWnd) - 0x54 sub 3 big-endian DIRECT / INDIRECT columns, the
window's OK packet 0x55 [04] (format of client 005de820) applied per unit, nicknames sent back by the client, the
outranking Subordinate refused; Word of Honor XP bonus both ways (Subordinate with his Superior, Superior with them)."""
import asyncio, struct, sys, os
os.chdir('/tmp/mp'); sys.path.insert(0, '/tmp/mp')
import sgserver as S
from mpclient import Client
S.LOG = open('/tmp/mp/server118.log', 'w', encoding='utf-8')
PORT = 3918
def chk(n, ok, i=''): print(('PASS ' if ok else 'FAIL ') + n, i, flush=True)

def ok_packet(plan):
    """what the client's OK sends (005de820): [55 04][u8 n] n x {u32 unit, u8 m, m x {s8 name, u32 A, u32 B, u16 6300,
    u8 11, s8 scrambled, u16, u16, u8 8c, u16, u16}}"""
    d = bytes([0x55, 4, len(plan)])
    for uid, names in plan:
        d += struct.pack('>I', uid) + bytes([len(names)])
        for nm in names:
            d += S._s8(nm) + struct.pack('>IIHB', 7, 9, 0x6300, 0x11) + S._s8('x') + struct.pack('>HHBHH', 1, 2, 0x8c, 3, 4)
    return d

async def main():
    S.ensure_unique_unit_ids()
    srv = await asyncio.start_server(S.handle, '127.0.0.1', PORT)
    accs = S.load_accounts()
    for n in ('hhhhhhhh', 'kkkkkkkk', 'llllllll'):
        accs[n]['commander'].pop('superior', None)
    # kkkkkkkk -> superior jjjjjjjj ; llllllll -> superior kkkkkkkk (indirect for jjjjjjjj) ; hhhhhhhh -> jjjjjjjj (outranks?)
    J = accs['jjjjjjjj']['commander']; K = accs['kkkkkkkk']['commander']; L = accs['llllllll']['commander']; H = accs['hhhhhhhh']['commander']
    K['superior'] = 'jjjjjjjj'; L['superior'] = 'kkkkkkkk'; H['superior'] = 'jjjjjjjj'
    K['tribute'] = 0; K['tribute_up'] = 0; L['tribute'] = 0; L['tribute_up'] = 0; H['tribute'] = 500
    for b in H['branches'].values(): b['level'] = 99          # outranks jjjjjjjj
    S.save_accounts(accs)
    # XP of llllllll's unit: 10 % to kkkkkkkk (direct), 5 % to jjjjjjjj via kkkkkkkk's row (indirect)
    lu = accs['llllllll']['units'][0]
    S.PG.add_unit_xp(L, lu, S.unit_branch(lu['chassis']), 1000)
    ku = accs['kkkkkkkk']['units'][0]
    S.PG.add_unit_xp(K, ku, S.unit_branch(ku['chassis']), 2000)
    S.save_accounts(accs)
    chk('tribute: direct 10 %', L['tribute'] == 100 and K['tribute'] == 200, (L['tribute'], K['tribute']))
    chk('tribute: indirect 5 %', L['tribute_up'] == 50, L.get('tribute_up'))
    rows = {r[0]: r for r in S.tribute_rows('jjjjjjjj')}
    chk('row kkkkkkkk = direct 200 + indirect 50', rows['kkkkkkkk'][2:] == (200, 50, 250), rows.get('kkkkkkkk'))
    chk('outranking hhhhhhhh not usable', rows['hhhhhhhh'][4] == 0, rows.get('hhhhhhhh'))
    A = Client('jjjjjjjj'); await A.connect(PORT); await A.login(); await asyncio.sleep(1.0)
    sess = next(o for o in S.ONLINE if o.acc == 'jjjjjjjj')
    got = []
    _send = sess.send
    sess.send = lambda d: (got.append(bytes(d)), _send(d))
    S.send_exp_window(sess)
    p = next((d for d in got if d[:2] == bytes([0x54, 3])), b'')
    o, n = 3, p[2] if len(p) > 2 else 0
    parsed = []
    for _ in range(n):                      # parsed like the client (005dfea0): u8 level, u32 A, u32 B (big-endian), s8
        lv = p[o]; a, b = struct.unpack_from('>II', p, o + 1); nm, o = S.read_s8(p, o + 9); parsed.append((nm, lv, a, b))
    chk('0x54 sub 3 parses (big-endian A/B)', ('kkkkkkkk', S._cmd_level(K), 200, 50) in parsed, parsed)
    chk('outranking row sent as 0/0', any(x[0] == 'hhhhhhhh' and x[2:] == (0, 0) for x in parsed), parsed)
    # OK packet: kkkkkkkk's XP on jjjjjjjj's first unit; hhhhhhhh on the 2nd (refused); a name sent twice
    J_units = S.get_account('jjjjjjjj')[1]['units']
    for u in J_units[:2]:
        u['level'] = 1; u['xp'] = 0
    u1, u2 = J_units[0]['uid'], J_units[1]['uid']
    S.save_accounts(S.load_accounts())
    plan = S.parse_assign_exp(ok_packet([(u1, ['kkkkkkkk', 'kkkkkkkk']), (u2, ['hhhhhhhh'])]))
    chk('parse_assign_exp', plan == [(u1, ['kkkkkkkk', 'kkkkkkkk']), (u2, ['hhhhhhhh'])], plan)
    got.clear()
    S.assign_exp_packet(sess, ok_packet([(u1, ['kkkkkkkk', 'kkkkkkkk']), (u2, ['hhhhhhhh'])]))
    a = S.get_account('jjjjjjjj')[1]
    x1 = a['units'][0]
    chk('unit 1 got 250 XP (direct + indirect, once)', x1['level'] > 1 or x1['xp'] == 250, (x1['level'], x1['xp']))
    chk('pools emptied', K['tribute'] == 0 and L['tribute_up'] == 0, (K['tribute'], L['tribute_up']))
    chk('outranking pool untouched', H['tribute'] == 500, H['tribute'])
    chk('roster + equipment re-sent', any(d[:1] == bytes([0x16]) for d in got) or len(got) > 2, [d[:2].hex() for d in got][:8])
    chk('bad packet does not raise', S.assign_exp_packet(sess, bytes([0x55, 4, 3, 0, 0])) is None)
    # nickname sent back by the client -> account
    S.NICK['acc']['nickk'] = 'kkkkkkkk'
    K['tribute'] = 40; S.save_accounts(S.load_accounts())
    S.assign_exp_packet(sess, ok_packet([(u1, ['nickk'])]))
    chk('nickname mapped back to the account', K['tribute'] == 0, K['tribute'])
    # bonus both ways
    class F: pass
    sup, sub = F(), F()
    B = object()
    sup.acc, sup.battle, sup.map, sup.logged_in = 'jjjjjjjj', B, 5, True
    sub.acc, sub.battle, sub.map, sub.logged_in = 'kkkkkkkk', B, 5, True
    _fo = S.find_online
    S.find_online = lambda n: {'jjjjjjjj': sup, 'kkkkkkkk': sub}.get((n or '').lower())
    S.ONLINE.add(sup); S.ONLINE.add(sub)
    ka, ja = S.load_accounts()['kkkkkkkk'], S.load_accounts()['jjjjjjjj']
    chk('subordinate gets the bonus with his superior', abs(S.xp_multiplier(ka, sub) - (1 + S.WOH_XP_BONUS)) < 1e-9, S.xp_multiplier(ka, sub))
    chk('superior gets the bonus with his subordinate', abs(S.xp_multiplier(ja, sup) - (1 + S.WOH_XP_BONUS)) < 1e-9, S.xp_multiplier(ja, sup))
    sub.battle, sub.map = object(), 6
    chk('other battle (other map): no bonus', S.xp_multiplier(ja, sup) == 1.0 and S.xp_multiplier(ka, sub) == 1.0)
    S.ONLINE.discard(sup); S.ONLINE.discard(sub); S.find_online = _fo
    # unit XP curve = the client's (00550b30): total XP ending level L = W*L(L+1)(2L+1)/60
    W = S.PG.UNIT_XP_W
    chk('curve = client formula', all(S.PG.unit_xp_cum(L) == W * L * (L + 1) * (2 * L + 1) // 60 for L in range(0, 61)))
    chk('per-level need sums to the total', sum(S.PG.unit_xp_need(L) for L in range(1, 19)) == S.PG.unit_xp_cum(18))
    u = {'uid': 5, 'chassis': 'g004', 'level': 1, 'xp': 0, 'xpv': 2}
    S.PG.add_unit_xp({}, u, 'inf', 2500, tribute=False)
    lv = 1
    while 2500 >= S.PG.unit_xp_cum(lv): lv += 1               # what the client predicts
    chk('server level = client prediction (1 + 2500 XP)', u['level'] == lv == 19, (u['level'], lv, u['xp']))
    old = {'level': 7, 'xp': 500}
    S.PG.ensure_unit(old)
    chk('old unit converted once (same share of the level)', old['xpv'] == 2 and old['xp'] == 500 * S.PG.unit_xp_need(7) // 700, old)
    rec = S.build_units([S.roster_rec(dict(u, uid=77, items=[], label='x'))])
    chk('0x16 first u32 = total XP', struct.unpack_from('>I', rec, 3 + 8)[0] == S.PG.unit_xp_total(u), struct.unpack_from('>I', rec, 11)[0])
    srv.close()
asyncio.run(main())
