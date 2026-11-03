"""test15: every nation of every planet can leave its capital through each portal, capture a neutral neighbour,
re-enter it as its owner (no battle) and start a battle in the next neutral province.
Portal data = the patched portals.por (out/pam2_fixed.dat -> /tmp/mp/portals.por), exactly what the client sends:
0x2e [u32 target][u16 x*32][u16 y*32][u8 route distance][u8 0]."""
import asyncio, struct, sys, os, time, json, shutil
os.chdir('/tmp/mp'); sys.path.insert(0, '/tmp/mp')
import sgserver as S, fix_portals as F
from mpclient import Client
S.LOG = open('/tmp/mp/server15.log', 'w', encoding='utf-8')
PORT = 3915
S.BATTLE_END_DELAY = 1.0; S.RESULT_SHOW_SECONDS = 1.0
recs = [r for r in F.parse(open('/tmp/mp/portals.por', 'rb').read()) if r[0] == 1]
OUT = {}
for r in recs:
    if (r[6] // 10000) % 10 == 0: OUT.setdefault(r[1], []).append(r)
fails = 0
def chk(name, ok, info=''):
    global fails
    fails += 0 if ok else 1
    print(('PASS ' if ok else 'FAIL ') + name, info, flush=True)
def sess(name): return next(o for o in S.ONLINE if getattr(o, 'acc', '') == name)
def last17(X, t):
    m = [struct.unpack_from('>I', b, 1)[0] for b in X.got(0x17, t)]
    return m[-1] if m else None
async def portal(X, r):
    t = time.monotonic()
    X.send(bytes([0x7b]) + struct.pack('>IB', 0x137f, 0))
    X.send(bytes([0x2e]) + struct.pack('>IHHBB', r[6], r[7] * 32, r[8] * 32, 1, 0)); await asyncio.sleep(0.5)
    return t
async def main():
    accs = json.load(open('accounts.json'))
    S.ensure_unique_unit_ids()
    srv = await asyncio.start_server(S.handle, '127.0.0.1', PORT)
    only = [int(x) for x in sys.argv[1:]]
    for nid, name, *_ in S.NATIONS:
        if only and nid not in only: continue
        cap = S.CAPITALS[nid]; pl = cap // 100000
        # default world: only capitals owned
        for p in S.planet_provinces(pl):
            S.set_province_owner(p, nid if p == cap else (n2 if (n2 := next((n for n, c in S.CAPITALS.items() if c == p), 0)) else 0))
        a = S.load_accounts(); c = a['jjjjjjjj'].setdefault('commander', {})
        c['nation'] = nid; c['tier'] = S.PLANET_TIER.get(pl, 1); c.pop('cur_province', None); S.save_accounts(a)
        X = Client('jjjjjjjj'); await X.connect(PORT); t0 = time.monotonic(); await X.login(); await asyncio.sleep(0.3)
        chk(f'[{name}] spawns in capital {cap}', last17(X, t0) == cap, last17(X, t0))
        outs = OUT.get(cap, [])
        chk(f'[{name}] capital has portals', len(outs) >= 3, [r[6] for r in outs])
        # every portal of the capital leads into the field of that neighbour
        bad = []
        for r in outs:
            t = await portal(X, r); got = last17(X, t)
            if got != r[6]: bad.append((r[6], got))
            S_ = sess('jjjjjjjj')
            if getattr(S_, 'battle', None):         # leave the battle again: back to the capital
                S.BATTLES.pop(r[6], None); S_.battle = None
            t = time.monotonic(); S.enter_field(S_, cap, 0x200, 0x200, capital=True); await asyncio.sleep(0.2)
        chk(f'[{name}] each capital portal enters its province', not bad, bad)
        # capture a neutral neighbour
        tgt = next((r for r in outs if S.province_owner(r[6]) == 0), None)
        if tgt is None:
            chk(f'[{name}] has a neutral neighbour', False); X.close(); await asyncio.sleep(0.5); continue
        t = await portal(X, tgt); s = sess('jjjjjjjj')
        b = S.BATTLES.get(tgt[6])
        chk(f'[{name}] battle in neutral {tgt[6]}', b is not None and getattr(s, 'battle', None) is b)
        for pid in list(getattr(s, 'pocs', {}) or {}):
            X.send(bytes([0x5a]) + struct.pack('>IBIB', pid, nid & 0xff, tgt[6], 1)); await asyncio.sleep(0.15)
        t5 = time.monotonic(); await asyncio.sleep(S.BATTLE_END_DELAY + S.RESULT_SHOW_SECONDS + 2.5)
        chk(f'[{name}] captured {tgt[6]}', S.province_owner(tgt[6]) == nid, S.province_owner(tgt[6]))
        # walk into the captured province again: own province, no battle
        S.enter_field(sess('jjjjjjjj'), cap, 0x200, 0x200, capital=True); await asyncio.sleep(0.3)
        t = await portal(X, tgt); s = sess('jjjjjjjj')
        chk(f'[{name}] re-enter own province {tgt[6]} without battle', last17(X, t) == tgt[6] and not S.BATTLES.get(tgt[6]),
            (last17(X, t), bool(S.BATTLES.get(tgt[6]))))
        # onwards from there to a neutral province
        nxt = next((r for r in OUT.get(tgt[6], []) if S.province_owner(r[6]) == 0), None)
        if nxt:
            t = await portal(X, nxt)
            chk(f'[{name}] onward {tgt[6]} -> {nxt[6]} starts a battle', last17(X, t) == nxt[6] and S.BATTLES.get(nxt[6]) is not None)
            S.BATTLES.pop(nxt[6], None)
        X.close(); await asyncio.sleep(0.8)
    srv.close()
    print('FAILS', fails)
asyncio.run(main())
