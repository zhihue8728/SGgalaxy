import sys, os, struct
os.chdir('/tmp/mp'); sys.path.insert(0, '/tmp/mp')
for f in ('npcs.json', 'world.json'):
    if os.path.exists(f): os.remove(f)
import sgserver as S
S.LOG = open('/tmp/mp/t_fo.log', 'w', encoding='utf-8')
def chk(n, ok, i=''): print(('PASS ' if ok else 'FAIL ') + n, i, flush=True)
class W:
    def is_closing(self): return False
class P:
    def __init__(s, acc, nat):
        s.acc, s.cmd, s.w, s.map, s.battle, s.logged_in, s.sent = acc, {'nation': nat}, W(), 600005, None, True, []
        s.lang, s.enc, s.join_mode = 'zh-cn', 'gbk', 2
    def send(s, d): s.sent.append(d.render(s) if hasattr(d, 'render') else d)
lead, cmdr, joiner, plain = P('flead', 1), P('fcmdr', 1), P('fjoin', 1), P('fplain', 1)
for o in (lead, cmdr, joiner, plain): S.ONLINE.add(o) if hasattr(S.ONLINE, 'add') else S.ONLINE.append(o)
regs = S.load_regiments()
regs['开放团'] = {'leader': 'flead', 'members': ['flead'], 'open': True, 'nation': 1}
S.save_regiments(regs)
S.politics(1)['council'] = {}
entered = []
S.enter_field = lambda o, m, x, y, **k: entered.append((o.acc, m))
S.build_strategic_map = lambda s: b'\x2d'
B = {'map': 600005, 'members': {cmdr}, 'owner': cmdr, 't0': 0}
S.BATTLES[600005] = B
r = S.request_join(joiner, 600005, 10, 10)
chk('before: commander refuses (Ctrl+F7 refuse all) -> handled by permission', r is True and not entered)
S._pkt_56(plain, b'\x56' + struct.pack('>I', 600005) + b'\x01', 0x56)
chk('plain player cannot force open', not B.get('force_open'))
S._pkt_56(lead, b'\x56' + struct.pack('>I', 600005) + b'\x01', 0x56)
chk('council member forces open', B.get('force_open') == 'flead')
chk('faction notified', any('强制开放'.encode('gbk') in p for p in plain.sent))
chk('map refreshed for requester', b'\x2d' in lead.sent)
r = S.request_join(joiner, 600005, 10, 10)
chk('after: join needs no permission', r is False)
S._pkt_56(lead, b'\x56' + struct.pack('>I', 600005) + b'\x00', 0x56)
chk('undo', not B.get('force_open'))
S.BATTLES.pop(600005, None)
