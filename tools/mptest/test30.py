"""test30: welcome letter (/mail) and tutorial only on the first login (0x15 wins gate)."""
import asyncio, struct, sys, os, time
os.chdir('/tmp/mp'); sys.path.insert(0, '/tmp/mp')
for f in ('npcs.json',):
    if os.path.exists(f): os.remove(f)
import sgserver as S
from mpclient import Client
S.LOG = open('/tmp/mp/server30.log', 'w', encoding='utf-8')
PORT = 3996
def chk(n, ok, i=''): print(('PASS ' if ok else 'FAIL ') + n, i, flush=True)
def wins_in(d):
    # 0x15: type, III, u8, 6I, 6 bytes, then u16 wins
    return struct.unpack_from('>H', d, 1 + 12 + 1 + 24 + 6)[0]
async def main():
    accs = S.load_accounts(); a = accs['jjjjjjjj']
    a.pop('tutorial_seen', None); a['mail'] = []; a['commander']['wins'] = 0
    S.mail_add(a, 'welcome'); S.save_accounts(accs)
    srv = await asyncio.start_server(S.handle, '127.0.0.1', PORT)
    t = time.monotonic()
    A = Client('jjjjjjjj'); await A.connect(PORT); await A.login(); await asyncio.sleep(1.2)
    c = A.got(0x15, t)
    chk('first login: wins 0 in 0x15 (tutorial may start)', c and wins_in(c[0]) == 0, c and wins_in(c[0]))
    chk('first login marks the tutorial as seen', bool(S.get_account('jjjjjjjj')[1].get('tutorial_seen')))
    s = next(o for o in S.ONLINE if o.acc == 'jjjjjjjj'); s.lang, s.enc = 'zh-cn', 'gbk'
    t2 = time.monotonic()
    S.build_commander('jjjjjjjj')
    chk('same session: resend keeps wins 0', wins_in(S.build_commander('jjjjjjjj')) == 0)
    S.mail_command(s, ''); await asyncio.sleep(0.2)
    lst = b''.join(A.got(0x2A, t2))
    chk('/mail lists the unread welcome letter', '欢迎'.encode('gbk') in lst and '未读'.encode('gbk') in lst)
    t3 = time.monotonic()
    S.mail_command(s, '1'); await asyncio.sleep(0.2)
    txt = b''.join(A.got(0x2A, t3))
    chk('/mail 1 shows the commands (nick, regiment)', b'/nick' in txt and b'/regiment create' in txt and len(A.got(0x2A, t3)) >= 9)
    chk('letter marked read', all(m['read'] for m in S.get_account('jjjjjjjj')[1]['mail']))
    A.close(); await asyncio.sleep(0.5)
    t = time.monotonic()
    A = Client('jjjjjjjj'); await A.connect(PORT); await A.login(); await asyncio.sleep(1.2)
    c = A.got(0x15, t)
    chk('second login: wins >= 1 -> tutorial skipped', c and wins_in(c[0]) == 1, c and wins_in(c[0]))
    accs = S.load_accounts(); accs['jjjjjjjj']['commander']['wins'] = 7; S.save_accounts(accs)
    chk('real wins shown when not 0', wins_in(S.build_commander('jjjjjjjj')) == 7)
    accs['jjjjjjjj']['commander']['wins'] = 0; S.save_accounts(accs)
    srv.close()
asyncio.run(main())
