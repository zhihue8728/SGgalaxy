"""test27: regiments in the client's directory cache (key = u16 regiment id) -> F4 'Regiment' shows the right name."""
import asyncio, struct, sys, os, time
os.chdir('/tmp/mp'); sys.path.insert(0, '/tmp/mp')
for f in ('npcs.json', 'regiments.json'):
    if os.path.exists(f): os.remove(f)
import sgserver as S
from mpclient import Client
S.REGIMENT_FILE = '/tmp/mp/regiments.json'
S.LOG = open('/tmp/mp/server27.log', 'w', encoding='utf-8')
PORT = 3993
def chk(n, ok, i=''): print(('PASS ' if ok else 'FAIL ') + n, i, flush=True)
def parse_list(d):
    n = struct.unpack_from('>H', d, 1)[0]; o = 3; out = {}
    for _ in range(n):
        i, k, nat = struct.unpack_from('>IHB', d, o); o += 7
        ln = d[o]; name = d[o + 1:o + 1 + ln].decode('latin-1'); o += 1 + ln + 2
        ln = d[o]; o += 1 + ln
        out[k] = name
    return out, o == len(d)
async def main():
    srv = await asyncio.start_server(S.handle, '127.0.0.1', PORT)
    A = Client('jjjjjjjj'); await A.connect(PORT); await A.login(); await asyncio.sleep(1.2)
    B = Client('hhhhhhhh'); await B.connect(PORT); await B.login(); await asyncio.sleep(1.2)
    sa = next(o for o in S.ONLINE if o.acc == 'jjjjjjjj')
    accs, a = S.get_account('jjjjjjjj'); a['resources'] = [10 ** 6] * 5; S.save_accounts(accs)
    t = time.monotonic()
    S.regiment_command(sa, '/regiment create Wolves'); await asyncio.sleep(0.4)
    rid = S.regiment_id_of('jjjjjjjj')
    chk('new regiment gets a small id', 1 <= rid < 65000, rid)
    lists = [d for d in B.got(0x3A, t)]
    ok = lists and parse_list(lists[-1])
    chk('everybody gets the regiment list (0x3a, key = id -> name)', bool(ok) and ok[0].get(rid) == 'Wolves' and ok[1], ok)
    c15 = A.got(0x15, t)
    chk('founder gets a new 0x15 with the regiment id', any(struct.pack('>H', rid) + bytes([0, 0]) in d for d in c15), len(c15))
    t = time.monotonic()
    B.send(bytes([0x23, 1]) + struct.pack('>I', sa.hero_uid) + b'\0'); await asyncio.sleep(0.4)
    r = B.got(0x27, t)
    hdr = r and r[-1]
    if hdr:
        o = 2 + 1 + hdr[2] + 1
        nat, k = struct.unpack_from('>IH', hdr, o)
    chk('other player profile header carries his regiment id', bool(hdr) and k == rid, hdr and (nat, k))
    t = time.monotonic()
    B.send(bytes([0x3C]) + struct.pack('>IH', 0, rid)); await asyncio.sleep(0.3)
    one = B.got(0x3B, t)
    chk('0x3c [id] -> 0x3b entry of that regiment', any(b'Wolves' in d for d in one), len(one))
    t = time.monotonic()
    B.send(bytes([0x3B, 0])); await asyncio.sleep(0.3)
    chk('0x3b [] -> full regiment list', any(b'Wolves' in d for d in B.got(0x3A, t)))
    S.regiment_command(sa, '/regiment leave'); await asyncio.sleep(0.3)
    chk('after leaving: no regiment (0xFFFF)', S.regiment_id_of('jjjjjjjj') == 0xFFFF)
    srv.close()
asyncio.run(main())
