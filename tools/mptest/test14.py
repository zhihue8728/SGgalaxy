import asyncio, struct, sys, os, json
os.chdir('/tmp/mp'); sys.path.insert(0, '/tmp/mp'); sys.path.insert(0, '/tmp/mp/tools')
import sgserver as S
S.LOG = open('/tmp/mp/server14.log', 'w', encoding='utf-8')
def chk(n, ok, i=''): print(('PASS ' if ok else 'FAIL ') + n, i, flush=True)
# --- counts / times / strengths
adv = [200000 + c * 100 + r for c in range(8) for r in range(8)]            # planet 2 (tier 2)
nov = [600000 + c * 100 + r for c in range(8) for r in range(8)]            # planet 6 (tier 1)
cnt = {len(S.province_pocs(p)) for p in adv}
chk('advanced provinces have 2..5 POCs', cnt <= {2, 3, 4, 5} and len(cnt) > 1, cnt)
chk('novice provinces have 1 POC / 30 s', all(len(S.province_pocs(p)) == 1 and S.province_pocs(p)[0][3] == 15000 for p in nov))
for p in adv[:40]:
    pc = S.province_pocs(p)
    if pc[0][3] != S.POC_SECONDS[len(pc)] * 500:
        chk('strength = seconds*500', False, (p, len(pc), pc[0][3])); break
else:
    chk('strength = seconds*500 (1:50 2:40 3:30 4:25 5:20 s)', True)
chk('same province -> same POCs', S.province_pocs(200105) == S.province_pocs(200105))
# --- positions are on free cells of the real map, inside the map
import struct as st, sgdat
gd = '/tmp/mp/pam.dat'
if os.path.exists(gd):
    d = open(gd, 'rb').read(); names = {n.lower(): (o, s) for n, o, s in sgdat.read_index(d)}
    bad = 0
    for p in adv[:30]:
        key = '000%05d.nm' % (p % 100000)
        if key not in names: continue
        o, s = names[key]; b = d[o:o + s]; w, h = st.unpack_from('<HH', b, 1)
        for _i, x, y, _st, _t, _ow in S.province_pocs(p):
            tx, ty = x // 32, y // 32
            if not (10 <= tx < w - 10 and 10 <= ty < h - 10) or b[5 + 3 * (ty * w + tx) + 2] & 0x21: bad += 1
    chk('POC cells are inside the map and not blocked', bad == 0, bad)
else:
    print('SKIP map check (copy pam.dat to /tmp/mp)')
# --- time-up rule
class W:
    def is_closing(self): return False
class M:
    def __init__(s, nation): s.cmd = {'nation': nation}; s.w = W(); s.battle_gen = 1; s.acc = 'x%d' % nation
res = {}
async def fake_end(m, gen, won): res[m.acc] = won
S.end_battle = fake_end
S.side_nation = lambda m: m.cmd['nation']
async def run(owners, dfd, attackers_nation=2):
    res.clear()
    a, dm = M(attackers_nation), M(1)
    b = {'map': 999, 'pocs': {i: {'owner': o} for i, o in enumerate(owners)}, 'members': {a, dm}, 'defender': dfd, 'won': False}
    S.BATTLES[999] = b; S.BATTLE_SECONDS = 0
    await S.battle_timer(b); await asyncio.sleep(0.05)
    return res.get('x%d' % attackers_nation), res.get('x1')
async def main():
    r = await run([2, 2, 1], 1); chk('attacker holds majority (2 of 3) -> attacker wins', r == (True, False), r)
    r = await run([2, 1, 1], 1); chk('defender holds majority -> defender wins', r == (False, True), r)
    r = await run([2, 1], 1); chk('equal count -> defender wins', r == (False, True), r)
    r = await run([0, 0, 2], 0); chk('aliens: attacker 1 of 3 -> defeat', (r[0] is False), r)
    r = await run([0, 2, 2], 0); chk('aliens: attacker 2 of 3 -> victory', (r[0] is True), r)
asyncio.run(main())
