"""test70 (user 2026-10-26 12:29): NPC names show Chinese AND English to Chinese clients (chat speaker, battle dialog
lists); the wire name of the NPC itself is unchanged."""
import sys, os
os.chdir('/tmp/mp'); sys.path.insert(0, '/tmp/mp')
for f in ('npcs.json', 'world.json'):
    if os.path.exists(f): os.remove(f)
import sgserver as S
S.LOG = open('/tmp/mp/t_names.log', 'w', encoding='utf-8')
def chk(n, ok, i=''): print(('PASS ' if ok else 'FAIL ') + n, i, flush=True)
chk('cn', S.NP.disp('BrandtVane', 'zh-cn') == '放鸽土拨鼠')
chk('tw is traditional', S.NP.disp('KaelRhodes', 'zh-tw') == '暴躁蘿蔔頭', S.NP.disp('KaelRhodes', 'zh-tw'))
chk('en unchanged', S.NP.disp('BrandtVane', 'en') == 'BrandtVane')
chk('player names unchanged', S.NP.disp('哈哈', 'zh-cn') == '哈哈' and S.NP.disp('Hans', 'zh-cn') == 'Hans')
chk('every generated part has a Chinese form', all(f in S.NP.FIRST_ZH for f in S.NP.FIRST) and all(l in S.NP.LAST_ZH for l in S.NP.LAST))
class W:
    def is_closing(self): return False
class P:
    def __init__(s, lang, enc):
        s.acc, s.cmd, s.w, s.logged_in, s.sent, s.lang, s.enc, s.acp = 'x' + lang, {'nation': 1}, W(), True, [], lang, enc, 936
    def send(s, d, **k): s.sent.append(d.render(s) if hasattr(d, 'render') else d)
cn, tw, en = P('zh-cn', 'gbk'), P('zh-tw', 'big5'), P('en', 'latin-1')
S.ONLINE.clear() if hasattr(S.ONLINE, 'clear') else None
for o in (cn, tw, en): S.ONLINE.add(o) if hasattr(S.ONLINE, 'add') else S.ONLINE.append(o)
S.npc_ally_chat(1, 'BrandtVane', lambda lg: 'hi')
chk('chat speaker bilingual for the Chinese client', any('放鸽土拨鼠'.encode('gbk') in p for p in cn.sent))
chk('traditional client gets traditional', any('放鴿土撥鼠'.encode('big5') in p for p in tw.sent))
chk('English client plain', any(b'BrandtVane' in p for p in en.sent) and not any('布'.encode('gbk', 'ignore') and b'\xb2\xbc' in p for p in en.sent))
r = S._npc_row_name(cn, 'BrandtVane')
chk('dialog row bytes in the client code page', isinstance(r, bytes) and r == '放鸽土拨鼠'.encode('gbk'), r)
chk('English client row = plain str', S._npc_row_name(en, 'BrandtVane') == 'BrandtVane')

# ---- (2026-10-26 14:2x) every place: packets (Session.send), text lines (TextPkt), names coming back from the client ----
nm = 'BrandtVane'
pk = bytes([0x20]) + b'\0' * 6 + bytes([len(nm)]) + nm.encode() + b'\0' * 4
z = S.NP.zh_bytes(pk, 'zh-cn', 'gbk')
chk('binary packet: length-prefixed name -> GBK Chinese, length byte fixed', bytes([10]) + '放鸽土拨鼠'.encode('gbk') in z and nm.encode() not in z, z)
chk('binary packet: Big5 for the traditional client', bytes([10]) + '放鴿土撥鼠'.encode('cp950') in S.NP.zh_bytes(pk, 'zh-tw', 'cp950'))
chk('English client packet untouched', S.NP.zh_bytes(pk, 'en', 'latin-1') == pk)
chk('a name without the matching length byte is not touched', S.NP.zh_bytes(bytes([0x20]) + b'\0' * 6 + bytes([3]) + nm.encode() + b'\0' * 4, 'zh-cn', 'gbk').count(nm.encode()) == 1)
chk('name coming back from the Chinese client = English again', S.NP.en_bytes(z, 'zh-cn') == pk)
chk('traditional name coming back', S.NP.en_bytes(S.NP.zh_bytes(pk, 'zh-tw', 'cp950'), 'zh-tw') == pk)
chk('every one of the 1520 names round-trips (gbk / big5)', all(
    S.NP.en_bytes(S.NP.zh_bytes(bytes([0x20, 1, 2, 3, 4, 5, 6, len(f + l)]) + (f + l).encode() + b'\0\0', lg, e), lg) == bytes([0x20, 1, 2, 3, 4, 5, 6, len(f + l)]) + (f + l).encode() + b'\0\0'
    for f in S.NP.FIRST for l in S.NP.LAST for lg, e in (('zh-cn', 'gbk'), ('zh-tw', 'cp950'))))
t = S.chat_line(3, 'BrandtVane captured province 06! xBrandtVane', (255, 255, 255)); t.tr = False
cn_line = t.render(cn); tw_line = t.render(tw); en_line = t.render(en)
chk('text line: Chinese name for zh clients', '放鸽土拨鼠'.encode('gbk') in cn_line and '放鴿土撥鼠'.encode('cp950') in tw_line.replace(b'', b'') or '放鴿土撥鼠'.encode('big5') in tw_line, tw_line)
chk('text line: English client unchanged, glued words untouched', b'BrandtVane captured' in en_line and b'xBrandtVane' in cn_line)
# the real Session.send path
sess = S.Session.__new__(S.Session)
class _W:
    def is_closing(s): return False
sess.w, sess.lang, sess.enc, sess.acc, sess.peer = _W(), 'zh-cn', 'gbk', 'nobody', ('x', 1)
got = []
sess._q = lambda data, t: got.append(data)
sess.cipher = type('C', (), {'encode': staticmethod(lambda b: b)})()
try:
    sess.send(pk, quiet=True)
    chk('Session.send applies it', any('放鸽土拨鼠'.encode('gbk') in g for g in got) and not any(nm.encode() in g for g in got), got[:1])
except Exception as e:
    chk('Session.send applies it', False, repr(e))
