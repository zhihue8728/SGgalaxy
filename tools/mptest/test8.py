import asyncio, struct, sys, os, time
os.chdir('/tmp/mp'); sys.path.insert(0, '/tmp/mp')
import sgserver as S
from mpclient import Client, s8
S.LOG = open('/tmp/mp/server8.log', 'w', encoding='utf-8')
PORT = 3994
def chk(n, ok, i=''): print(('PASS ' if ok else 'FAIL ') + n, i, flush=True)
def lines(X, since, sub):
    out = []
    for b in X.got(0x2a, since):
        if b[1] == sub: out.append(b[3:3 + b[2]].decode('latin-1'))
    return out
async def main():
    S.ensure_unique_unit_ids()
    srv = await asyncio.start_server(S.handle, '127.0.0.1', PORT)
    A, B, C = Client('jjjjjjjj'), Client('kkkkkkkk'), Client('llllllll')
    for X in (A, B, C):
        await X.connect(PORT); await X.login()
    rgb = bytes([255, 255, 255])
    t = time.monotonic()
    A.send(bytes([0x2a, 0]) + s8('hello all') + rgb); await asyncio.sleep(0.5)
    chk('public chat reaches same-map B and echoes to A', lines(B, t, 3) == ['jjjjjjjj: hello all'] and lines(A, t, 3) == ['jjjjjjjj: hello all'], (lines(A, t, 3), lines(B, t, 3)))
    chk('other nation capital (C) does not hear it', not lines(C, t, 3))
    t = time.monotonic()
    A.send(bytes([0x2a, 4]) + s8('llllllll') + s8('psst') + rgb); await asyncio.sleep(0.5)
    chk('whisper reaches C as Sender>text', lines(C, t, 1) == ['jjjjjjjj>psst'], lines(C, t, 1))
    chk('whisper not seen by B', not lines(B, t, 1) and not lines(B, t, 3))
    chk('sender gets a (to ...) echo', lines(A, t, 3) == ['(to llllllll) psst'], lines(A, t, 3))
    t = time.monotonic()
    A.send(bytes([0x2a, 4]) + s8('nobody') + s8('x') + rgb); await asyncio.sleep(0.5)
    chk('offline whisper gives a system line', lines(A, t, 10) == ['nobody is not online.'], lines(A, t, 10))
    t = time.monotonic()
    C.send(bytes([0x2a, 2]) + s8('nation 2 only') + rgb); await asyncio.sleep(0.5)
    chk('ally chat stays within the side', lines(C, t, 3) == ['[Allies] llllllll: nation 2 only'] and not lines(A, t, 3) and not lines(B, t, 3), (lines(C, t, 3), lines(A, t, 3)))
    t = time.monotonic()
    A.send(bytes([0x2a, 5, 2]) + s8('kkkkkkkk') + s8('llllllll') + s8('group msg') + rgb); await asyncio.sleep(0.5)
    chk('group chat reaches both', lines(B, t, 1) == ['jjjjjjjj>group msg'] and lines(C, t, 1) == ['jjjjjjjj>group msg'])
    t = time.monotonic()
    A.send(bytes([0x2a, 0]) + s8('/stats') + rgb); await asyncio.sleep(0.5)
    chk('GM command not broadcast', not lines(B, t, 3))
    for X in (A, B, C): X.close()
    await asyncio.sleep(0.3)
asyncio.run(main())
