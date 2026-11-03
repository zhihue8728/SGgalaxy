import asyncio, struct, sys, os, time
os.chdir('/tmp/mp'); sys.path.insert(0, '/tmp/mp')
import sgserver as S
from mpclient import Client, s8
S.LOG = open('/tmp/mp/server9.log', 'w', encoding='utf-8')
PORT = 3993
def chk(n, ok, i=''): print(('PASS ' if ok else 'FAIL ') + n, i, flush=True)
def r8(b, o): n = b[o]; return b[o+1:o+1+n].decode('latin-1'), o+1+n
def r16(b, o): n = struct.unpack_from('>H', b, o)[0]; return b[o+2:o+2+n].decode('latin-1'), o+2+n
# parsers mirror the client's read order (FUN_005e7770 / FUN_0047c640 / FUN_004ba060)
def p_vote(b):
    assert b[0] == 0x37 and b[1] == 0
    nat = struct.unpack_from('>I', b, 2)[0]; o = 6; sub = b[o]; o += 1
    recs = []
    def rec(o, first_nat):
        if first_nat: o += 4
        name, o = r8(b, o); _, o = r8(b, o); o += 2; _, o = r8(b, o); o += 1
        votes = struct.unpack_from('>I', b, o)[0]; o += 4; o += 4
        sup, opp = struct.unpack_from('>HH', b, o); o += 4
        st, o = r8(b, o)
        return (name, votes, sup, opp, st), o
    if sub == 0:
        r, o = rec(o, True); recs.append(r)
    else:
        o += 4; n = b[o]; o += 1
        for _ in range(n):
            r, o = rec(o, False); recs.append(r)
    assert o == len(b), (o, len(b))
    return sub, recs
def p_dom(b):
    assert b[0] == 0x37 and b[1] == 1
    o = 6 + 6 + 20 + 8 + 1 + 6 + 1
    n = b[o]; o += 1; out = []
    for _ in range(n):
        slot = struct.unpack_from('>H', b, o)[0]; o += 2
        a, o = r8(b, o); _, o = r8(b, o); _, o = r8(b, o); o += 4; out.append((slot, a))
    assert o == len(b), (o, len(b)); return out
def p_for(b):
    assert b[0] == 0x37 and b[1] == 2
    o = 6; assert b[o] == 0; n = b[o+1]; o += 2; out = []
    for _ in range(n):
        nat = struct.unpack_from('>I', b, o)[0]; o += 4 + 2 + 1 + 16
        t, o = r16(b, o); out.append(nat)
    assert o == len(b), (o, len(b)); return out
async def main():
    S.ensure_unique_unit_ids()
    srv = await asyncio.start_server(S.handle, '127.0.0.1', PORT)
    A, B, C = Client('jjjjjjjj'), Client('kkkkkkkk'), Client('llllllll')
    for X in (A, B, C):
        await X.connect(PORT); await X.login()
    N = 1
    def req(X, kind, op, extra=b''): X.send(bytes([0x36]) + struct.pack('>IBB', N, kind, op) + extra)
    t = time.monotonic(); req(A, 0, 0); await asyncio.sleep(0.4)
    got = A.got(0x37, t)
    chk('no candidates: only the president packet', len(got) == 1, len(got))
    s0, r0 = p_vote(got[0])
    chk('president packet parses exactly as the client reads it', s0 == 0 and r0[0][0] == '', (s0, r0))
    t = time.monotonic(); req(A, 0, 1, struct.pack('>H', 7) + b'Vote me'); await asyncio.sleep(0.4)
    _, rr = p_vote(A.got(0x37, t)[1]); chk('A campaigns', [r[0] for r in rr] == ['jjjjjjjj'] and rr[0][4] == 'Vote me', rr)
    req(B, 0, 3, s8('jjjjjjjj')); req(B, 0, 6, s8('jjjjjjjj')); await asyncio.sleep(0.4)
    t = time.monotonic(); req(A, 0, 0); await asyncio.sleep(0.4)
    _, rr = p_vote(A.got(0x37, t)[1]); chk('B support + vote counted', rr[0][1] == 1 and rr[0][2] == 1, rr)
    t = time.monotonic(); req(C, 0, 1, struct.pack('>H', 1) + b'x'); await asyncio.sleep(0.4)
    chk('foreign nation member cannot campaign', not S.politics(N)['candidates'].get('llllllll') and not C.got(0x37, t))
    S.politics(N)['election_end'] = time.time() - 1
    t = time.monotonic(); req(A, 0, 0); await asyncio.sleep(0.4)
    s0, r0 = p_vote(A.got(0x37, t)[0]); chk('election resolved: A is president', r0[0][0] == 'jjjjjjjj' and r0[0][4] == 'Vote me', r0)
    t = time.monotonic(); req(A, 2, 2, struct.pack('>H', 5) + b'peace'); await asyncio.sleep(0.4)
    fo = p_for(A.got(0x37, t)[0]); chk('foreign policy rows parse', len(fo) >= 1 and N not in fo, fo)
    raw = A.got(0x37, t)[0]; row = struct.unpack_from('>IHB8H', raw, 8)
    st = S.nation_stats(fo[0])
    chk('foreign row carries real data', row[0] == fo[0] and row[1] == st['members'] and row[2] == S.nation_planet(fo[0]) and row[3] == st['provinces'], (row, st))
    t = time.monotonic(); req(A, 1, 0); await asyncio.sleep(0.4)
    chk('domestic policy parses', p_dom(A.got(0x37, t)[0]) == [], p_dom(A.got(0x37, t)[0]))
    for X in (A, B, C): X.close()
    await asyncio.sleep(0.3)
asyncio.run(main())
