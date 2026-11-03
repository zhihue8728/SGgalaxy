import asyncio, struct, sys, os, time
os.chdir('/tmp/mp'); sys.path.insert(0, '/tmp/mp')
import sgserver as S
from mpclient import Client, s8
S.LOG = open('/tmp/mp/server10.log', 'w', encoding='utf-8')
PORT = 3994
def chk(n, ok, i=''): print(('PASS ' if ok else 'FAIL ') + n, i, flush=True)
def r8(b, o): n = b[o]; return b[o+1:o+1+n].decode('gbk', 'replace'), o+1+n      # (11-03) the test client is zh-cn
def council_rows(b):
    o = 6 + 6 + 20 + 8 + 1 + 6 + 1
    n = b[o]; o += 1; out = []
    for _ in range(n):
        slot = struct.unpack_from('>H', b, o)[0]; o += 2
        a, o = r8(b, o); b2, o = r8(b, o); c2, o = r8(b, o); v = struct.unpack_from('>I', b, o)[0]; o += 4
        if a.strip(" \xa0\u3000"):                       # (11-03) free seats = invisible fillers
            out.append((slot, a, b2, c2, v))
    assert o == len(b); return out
async def main():
    S.ensure_unique_unit_ids()
    srv = await asyncio.start_server(S.handle, '127.0.0.1', PORT)
    for _n in ('jjjjjjjj', 'kkkkkkkk'):                  # (11-03) both citizens of nation 1 (the fixture moved jjjjjjjj)
        S.load_accounts()[_n]['commander']['nation'] = 1
    A, B = Client('jjjjjjjj'), Client('kkkkkkkk')
    for X in (A, B):
        await X.connect(PORT); await X.login()
    N = 1; rgb = bytes([255, 255, 255])
    def save(X, rows):
        body = bytes([0x36]) + struct.pack('>IBB', N, 1, 1) + bytes([len(rows)])
        for slot, a, b2, c2, v in rows:
            body += struct.pack('>H', slot) + s8(a) + s8(b2) + s8(c2) + struct.pack('>I', v)
        X.send(body)
    # (11-03) the council = the faction's regiments; the president sets only their POWERS (typed names are ignored)
    R = S.load_regiments(); R['TestReg'] = {'id': 9001, 'nation': N, 'leader': 'kkkkkkkk', 'members': ['kkkkkkkk']}
    for k_ in [k_ for k_, g_ in R.items() if k_ != 'TestReg' and int(g_.get('nation', 0) or 0) == N]: R.pop(k_)
    S.politics(N)['council'] = {}; S.politics(N).pop('council_powers', None)
    want0 = [(1, 'TestReg', '团长', 'kkkkkkkk', 0)]
    rows = [(1, 'TestReg', 'typed title', 'typed name', 5), (2, 'NoSuchReg', 'x', 'y', 3)]
    t = time.monotonic(); save(A, rows); await asyncio.sleep(0.4)
    raw = A.got(0x37, t)[0]
    chk('council has 100 records (client 0047c860 / 0047b7e0)', raw[6 + 6 + 20 + 8 + 1 + 6 + 1] == 100)
    chk('non-president cannot save council', council_rows(raw) == want0, council_rows(raw))
    def client_ok(b):                                   # 0047b7e0: every record trimmed non-empty, regiments / names unique
        o = 6 + 6 + 20 + 8 + 1 + 6 + 1; n = b[o]; o += 1; regs, names = set(), set()
        for _ in range(n):
            o += 2; f = []
            for _k in range(3):
                L = b[o]; f.append(b[o + 1:o + 1 + L].strip(b' \t\r\n')); o += 1 + L
            o += 4
            if not all(f) or f[0] in regs or f[2] in names: return False
            regs.add(f[0]); names.add(f[2])
        return True
    chk('the client would accept the council (no empty / repeated record)', client_ok(raw))
    A.send(bytes([0x2a, 0]) + s8('/president') + rgb); await asyncio.sleep(0.4)
    chk('/president makes me president', S.politics(N)['president'] == 'jjjjjjjj', S.politics(N)['president'])
    t = time.monotonic(); save(A, rows); await asyncio.sleep(0.4)
    got = council_rows(A.got(0x37, t)[0])
    want = [(1, 'TestReg', '团长', 'kkkkkkkk', 5)]
    chk('president saves the powers only (names stay, unknown regiment ignored)', got == want, got)
    rows = want
    t = time.monotonic(); B.send(bytes([0x36]) + struct.pack('>IBB', N, 1, 0)); await asyncio.sleep(0.4)
    chk('other member sees the council', council_rows(B.got(0x37, t)[0]) == rows)
    t = time.monotonic(); A.send(bytes([0x2a, 0]) + s8('/ally 2') + rgb); await asyncio.sleep(0.5)
    rel = B.got(0x05, t)
    chk('/ally pushes 0x05 to online players', len(rel) == 1 and struct.pack('>I', 2) in rel[0], [r.hex() for r in rel])
    chk('alliance applied + persisted', S.same_side(1, 2) and [1, 2] in S.WORLD.get('allies', []), S.WORLD.get('allies'))
    A.send(bytes([0x2a, 0]) + s8('/ally 2') + rgb); await asyncio.sleep(0.4)
    chk('/ally again breaks it', not S.same_side(1, 2) and S.WORLD.get('allies') == [], S.WORLD.get('allies'))
    for X in (A, B): X.close()
    await asyncio.sleep(0.3)
asyncio.run(main())
