import sys, os
os.chdir('/tmp/mp'); sys.path.insert(0, '/tmp/mp')
for f in ('npcs.json', 'world.json'):
    if os.path.exists(f): os.remove(f)
import sgserver as S
S.LOG = open('/tmp/mp/t_pull.log', 'w', encoding='utf-8')
def chk(n, ok, i=''): print(('PASS ' if ok else 'FAIL ') + n, i, flush=True)
class W:
    def is_closing(self): return False
class P:
    def __init__(s, acc, nat, m):
        s.acc, s.cmd, s.w, s.map, s.battle, s.logged_in, s.sent = acc, {'nation': nat}, W(), m, None, True, []
        s.lang, s.enc, s.hero_pos = 'zh-cn', 'gbk', (300, 300)
    def send(s, d): s.sent.append(d.render(s) if hasattr(d, 'render') else d)
entered = []
S.enter_field = lambda o, m, x, y, **k: entered.append((o.acc, m, x, y))
a = P('aaa', 1, 600005); b = P('bbb', 2, 600005); c = P('ccc', 1, 600007); d = P('ddd', 1, 600005); d.battle = {'x': 1}
S.ONLINE.clear() if hasattr(S.ONLINE, 'clear') else None
for o in (a, b, c, d): S.ONLINE.add(o) if hasattr(S.ONLINE, 'add') else S.ONLINE.append(o)
S.set_province_owner(600005, 1)
g = S.Ghost(600005, 2)
B = {'map': 600005, 'defender': 1, 'npc_attacker': 2}
n = S.pull_into_battle(B, 600005, g)
chk('players standing in the province enter the battle (both sides), others not', sorted(e[0] for e in entered) == ['aaa', 'bbb'], entered)
chk('position kept', all(e[2:] == (300, 300) for e in entered))
chk('defender elsewhere (ccc) gets the notice as a chat line, NOT 0x31 (StarCenter window)', any(p[:1] == b'*' for p in c.sent) and not any(p[:1] == bytes([0x31]) for p in c.sent), [p[:2] for p in c.sent])
chk('notice is Chinese (gbk)', any('遭到'.encode('gbk') in p for p in c.sent))
chk('attacker side (bbb) gets no defend notice', not any('遭到'.encode('gbk') in p for p in b.sent))
