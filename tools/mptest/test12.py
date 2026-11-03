import asyncio, struct, sys, os, time
os.chdir('/tmp/mp'); sys.path.insert(0, '/tmp/mp')
import sgserver as S
from mpclient import Client, s8
S.LOG = open('/tmp/mp/server12.log', 'w', encoding='utf-8')
PORT = 3996
def chk(n, ok, i=''): print(('PASS ' if ok else 'FAIL ') + n, i, flush=True)
async def main():
    srv = await asyncio.start_server(S.handle, '127.0.0.1', PORT)
    A = Client('kkkkkkkk'); await A.connect(PORT); await asyncio.sleep(0.2)
    t = time.monotonic(); A.send(bytes([7]) + s8('kkkkkkkk') + s8('wrongpass') + s8('newpass1')); await asyncio.sleep(0.3)
    g = A.got(2, t); chk('wrong old password refused', g and g[0][1] == 1, g)
    t = time.monotonic(); A.send(bytes([7]) + s8('kkkkkkkk') + s8('ji3g4go6') + s8('newpass1')); await asyncio.sleep(0.3)
    g = A.got(2, t); chk('password changed (02 00)', g and g[0] == bytes([2, 0]), g)
    chk('stored', S.load_accounts()['kkkkkkkk']['password'] == 'newpass1')
    B = Client('kkkkkkkk', pw='newpass1'); await B.connect(PORT); await asyncio.sleep(0.2)
    t = time.monotonic(); B.send(bytes([3]) + s8('kkkkkkkk') + s8('newpass1') + bytes.fromhex('010c1ee56b0002060200')); await asyncio.sleep(0.4)
    g = B.got(2, t); chk('login with the new password', g and g[0] == bytes([2, 0]), g)
    A.close(); B.close(); await asyncio.sleep(0.2)
asyncio.run(main())
