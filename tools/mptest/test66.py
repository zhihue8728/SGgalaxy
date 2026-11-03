import sys, os, struct
os.chdir('/tmp/mp'); sys.path.insert(0, '/tmp/mp')
for f in ('npcs.json', 'world.json'):
    if os.path.exists(f): os.remove(f)
import sgserver as S
S.LOG = open('/tmp/mp/t_mark.log', 'w', encoding='utf-8')
def chk(n, ok, i=''): print(('PASS ' if ok else 'FAIL ') + n, i, flush=True)
class W:
    def is_closing(self): return False
class P:
    def __init__(s, acc, nat):
        s.acc, s.cmd, s.w, s.map, s.battle, s.logged_in, s.sent = acc, {'nation': nat}, W(), 600005, None, True, []
        s.lang, s.enc = 'zh-cn', 'gbk'
    def send(s, d): s.sent.append(d.render(s) if hasattr(d, 'render') else d)
lead, mem, plain, enemy = P('mlead', 1), P('mmem', 1), P('mplain', 1), P('menemy', 2)
for o in (lead, mem, plain, enemy): S.ONLINE.add(o) if hasattr(S.ONLINE, 'add') else S.ONLINE.append(o)
regs = S.load_regiments()
for k in [k for k, g in regs.items() if 'mlead' in g['members']]: regs.pop(k)
regs['测试团'] = {'leader': 'mlead', 'members': ['mlead', 'mmem'], 'open': True, 'nation': 1}
S.save_regiments(regs); regs = S.load_regiments(); rid = regs['测试团']['id']
S.politics(1)['council'] = {}; S.politics(1)['president'] = ''
S.WORLD['markers'] = {'next': 1, 'list': {}}
def edit(o, dels, adds):
    b = bytes([0x40]) + struct.pack('>H', len(dels)) + b''.join(struct.pack('>H', d) for d in dels) + struct.pack('>H', len(adds))
    b += b''.join(struct.pack('>BIIBH', *a) for a in adds)
    for x in (lead, mem, plain, enemy): x.sent.clear()
    S._pkt_40(o, b, 0x40)
edit(lead, [], [(0, 600306, 0, 1, 0)])
chk('council (regiment leader) faction order -> 0x3f to all of nation 1', all(any(p[:1] == b'\x3f' for p in x.sent) for x in (lead, mem, plain)))
chk('enemy nation gets nothing', not enemy.sent)
pk = [p for p in plain.sent if p[:1] == b'\x3f'][0]
nd, na = struct.unpack_from('>HH', pk, 1)
mid, typ, prov, setter = struct.unpack_from('>HBII', pk, 5); ln = pk[16]; nm = pk[17:17 + ln]
scope, reg = struct.unpack_from('>BH', pk, 17 + ln)
chk('record', (nd, na, typ, prov, scope, setter, nm) == (0, 1, 0, 600306, 1, 0, b'mlead'), (nd, na, typ, prov, scope, setter, nm))
chk('packet length exact', len(pk) == 17 + ln + 3)
edit(lead, [], [(5, 600306, 0, 2, 0)])
chk('regiment order only to regiment', any(p[:1] == b'\x3f' for p in mem.sent) and not plain.sent, plain.sent)
edit(plain, [], [(1, 600307, 0, 1, 0)])
chk('plain player refused, gets full list back', any(p[:1] == b'\x3e' for p in plain.sent) and not mem.sent)
lst = S.build_marker_list(plain); chk('plain sees 1 order', struct.unpack_from('>H', lst, 1)[0] == 1)
lst = S.build_marker_list(mem); chk('member sees 2 orders', struct.unpack_from('>H', lst, 1)[0] == 2)
edit(lead, [], [(2, 600306, 0, 1, 0)])
chk('same kind replaces old one', struct.unpack_from('>H', S.build_marker_list(plain), 1)[0] == 1)
edit(plain, [mid + 2], [])
chk('plain cannot delete', struct.unpack_from('>H', S.build_marker_list(plain), 1)[0] == 1)
ids = list(S._markers()['list'].keys())
edit(lead, [int(i) for i in ids], [])
chk('leader deletes all', not S._markers()['list'] and any(p[:1] == b'\x3f' for p in mem.sent))
S._pkt_3f(plain, b'\x3f', 0x3f); chk('0x3f request -> 0x3e', plain.sent[-1][:1] == b'\x3e')

# window semantics: reopen -> client deletes its old ids and re-adds the set
edit(lead, [], [(0, 600306, 0, 1, 0), (5, 600307, 0, 1, 0)])
ids = [int(i) for i in S._markers()['list']]
edit(lead, ids, [(1, 600306, 0, 1, 0)])
L = S._markers()['list']; chk('replace-all: 1 order left, AntiGround at 600306', len(L) == 1 and list(L.values())[0]['type'] == 1, L)
