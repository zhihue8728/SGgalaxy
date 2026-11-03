import asyncio, struct, sys, os, time
os.chdir('/tmp/mp'); sys.path.insert(0, '/tmp/mp')
import sgserver as S
from mpclient import Client, s8
S.LOG = open('/tmp/mp/server11.log', 'w', encoding='utf-8')
PORT = 3995
def chk(n, ok, i=''): print(('PASS ' if ok else 'FAIL ') + n, i, flush=True)
def r8(b, o): n = b[o]; return b[o+1:o+1+n].decode('latin-1'), o+1+n
# mirrors FUN_004f8820 (payload after the type byte)
def p_hof(b):
    assert b[0] == 0x12
    kind = b[1]; n = struct.unpack_from('>H', b, 2)[0]; o = 4; rows = []
    if kind in (1, 2, 3, 4):
        size = 24 if kind == 1 else 22
        for _ in range(n):
            nm, o = r8(b, o); assert len(nm) <= 20
            rows.append((nm,) + struct.unpack_from('>IHBBBIIBHH', b, o)); o += size
        if kind == 1: o += 2
    assert o == len(b), (kind, o, len(b)); return kind, rows
def p_entry(b, o):
    uid, k, a = struct.unpack_from('>IHB', b, o); o += 7
    name, o = r8(b, o); bb = struct.unpack_from('>H', b, o)[0]; o += 2
    c, o = r8(b, o); return (uid, k, a, name, bb, c), o
async def main():
    S.ensure_unique_unit_ids()
    srv = await asyncio.start_server(S.handle, '127.0.0.1', PORT)
    A = Client('jjjjjjjj'); await A.connect(PORT); await A.login()
    for kind in (1, 2, 3, 4, 5, 6):
        t = time.monotonic(); A.send(bytes([0x12, kind])); await asyncio.sleep(0.3)
        got = A.got(0x12, t)
        chk(f'hof kind {kind} parses like the client', len(got) == 1 and p_hof(got[0])[0] == kind, p_hof(got[0])[1][:1] if got else None)
    t = time.monotonic(); A.send(bytes([0x12, 1])); await asyncio.sleep(0.3)
    _, rows = p_hof(A.got(0x12, t)[0]); uid = rows[0][1]
    chk('kind 1 has real players, uid stable', len(rows) > 1 and rows[0][0] != '', rows[:2])
    t = time.monotonic(); A.send(bytes([0x3C]) + struct.pack('>IH', S.uid_of('jjjjjjjj'), 0)); await asyncio.sleep(0.3)
    g = A.got(0x3B, t); e, o = p_entry(g[0], 1) if g else (None, 0)
    chk('0x3c -> 0x3b name lookup', g and e[3] == 'jjjjjjjj' and o == len(g[0]), e)
    t = time.monotonic(); A.send(bytes([0x3B, 0])); await asyncio.sleep(0.3)
    g = A.got(0x3A, t); n = struct.unpack_from('>H', g[0], 1)[0]; o = 3; names = []
    for _ in range(n):
        e, o = p_entry(g[0], o); names.append(e[3])
    chk('0x3b -> 0x3a full list parses', o == len(g[0]) and 'jjjjjjjj' in names, names[:5])
    A.close(); await asyncio.sleep(0.3)
asyncio.run(main())
