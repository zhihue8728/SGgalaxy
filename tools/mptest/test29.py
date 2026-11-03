"""test29: Chinese nickname (/nick) shown instead of the account; Big5 receivers get it re-encoded; Chinese regiment names."""
import asyncio, struct, sys, os, time
os.chdir('/tmp/mp'); sys.path.insert(0, '/tmp/mp')
for f in ('npcs.json', 'regiments.json'):
    if os.path.exists(f): os.remove(f)
import sgserver as S
from mpclient import Client
S.REGIMENT_FILE = '/tmp/mp/regiments.json'
S.LOG = open('/tmp/mp/server29.log', 'w', encoding='utf-8')
PORT = 3995
def chk(n, ok, i=''): print(('PASS ' if ok else 'FAIL ') + n, i, flush=True)
async def main():
    accs = S.load_accounts()
    for k in ('jjjjjjjj', 'hhhhhhhh'):
        accs[k].pop('nick', None)
    S.save_accounts(accs); S.nick_rebuild(accs)
    srv = await asyncio.start_server(S.handle, '127.0.0.1', PORT)
    A = Client('jjjjjjjj'); await A.connect(PORT); await A.login(); await asyncio.sleep(1.2)
    B = Client('hhhhhhhh'); await B.connect(PORT); await B.login(); await asyncio.sleep(1.2)
    sa = next(o for o in S.ONLINE if o.acc == 'jjjjjjjj'); sb = next(o for o in S.ONLINE if o.acc == 'hhhhhhhh')
    sa.enc, sa.lang = 'gbk', 'zh-cn'; sb.enc, sb.lang = 'cp950', 'zh-tw'
    t = time.monotonic()
    S.nick_command(sa, '天狼星'); await asyncio.sleep(0.3)
    chk('nickname stored, account unchanged', S.get_account('jjjjjjjj')[1].get('nick') == '天狼星' and sa.acc == 'jjjjjjjj')
    g = '天狼星'.encode('gbk'); b5 = '天狼星'.encode('cp950')
    c15 = A.got(0x15, t)
    chk('own 0x15 keeps the ACCOUNT (client knows itself by its login name)', c15 and all(bytes([len(g)]) + g not in d for d in c15) and any(b'\x08jjjjjjjj' in d for d in c15))
    t_ = time.monotonic()
    for pk in S.put_for_others(sa):
        sa.send(pk)
    await asyncio.sleep(0.3)
    own = b''.join(A.got(0x18, t_) + A.got(0x20, t_))
    chk('own PUT_UNIT owner = account (own units stay controllable)', b'\x08jjjjjjjj' in own and g not in own)
    # B (Big5 client) sees A's hero
    t = time.monotonic()
    for pk in S.put_for_others(sa):
        sb.send(pk)
    await asyncio.sleep(0.3)
    got = b''.join(B.got(0x18, t) + B.got(0x20, t))
    chk('Big5 receiver gets the nickname in Big5', bytes([len(b5)]) + b5 in got and g not in got, got[:40])
    # B whispers to A by nickname typed in Big5
    t = time.monotonic()
    B.send(bytes([0x2A, 1]) + bytes([len(b5)]) + b5 + bytes([4]) + '你好'.encode('cp950') + bytes([255, 255, 255]))
    await asyncio.sleep(0.4)
    msgs = A.got(0x2A, t)
    chk('whisper by nickname reaches the account', any('你好'.encode('gbk') in d for d in msgs), msgs[:2])
    chk('lookup by nickname', S.find_account_by_name(b5.decode('latin-1'))[0] == 'jjjjjjjj' and S.find_online('天狼星') is sa)
    chk('nickname cannot be taken twice', (S.nick_command(sb, '天狼星'), S.get_account('hhhhhhhh')[1].get('nick'))[1] is None)
    # Chinese regiment name
    accs, a = S.get_account('jjjjjjjj'); a['resources'] = [10 ** 6] * 5; S.save_accounts(accs)
    t = time.monotonic()
    S.regiment_command(sa, '/regiment create 银河军团'); await asyncio.sleep(0.4)
    rid = S.regiment_id_of('jjjjjjjj')
    chk('Chinese regiment name accepted', rid != 0xFFFF, rid)
    la = b''.join(A.got(0x3A, t)); lb = b''.join(B.got(0x3A, t))
    chk('regiment list encoded per receiver (GBK / Big5)', '银河军团'.encode('gbk') in la and '銀河軍團'.encode('cp950') not in lb and len(lb) > 3)
    S.regiment_command(sa, '/regiment leave')
    accs = S.load_accounts(); accs['jjjjjjjj'].pop('nick', None); S.save_accounts(accs); S.nick_rebuild(accs)
    srv.close()
asyncio.run(main())
