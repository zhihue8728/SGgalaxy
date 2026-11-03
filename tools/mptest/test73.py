"""test73 (user 2026-10-26): BOARD + MAIL web pages (sgs/board_mail.py).  The pages are parsed here exactly like the client does it
(strstr between marker strings, SG.exe 0041bae0 / 00419150 / 005437c0 / 00540dc0), so a page that passes is a page the exe reads."""
import sys, os, urllib.parse as up
os.chdir('/tmp/mp'); sys.path.insert(0, '/tmp/mp')
import sgserver as S
S.LOG = open('/tmp/mp/t_board.log', 'w', encoding='utf-8')
S.BOARD_REQUIRE_ONLINE = False
S.BOARD_FILE = '/tmp/mp/board_t.json'
if os.path.exists(S.BOARD_FILE): os.remove(S.BOARD_FILE)
S._BOARD = None
S.BOARD_POST_GAP = 0
S.BW_IP_GAP = 0
S.BW_POSTS_HOUR = 10**6
def chk(n, ok, i=''): print(('PASS ' if ok else 'FAIL ') + n, i, flush=True)

# ---- the client's text cutter (00416730): copy between BEGIN and END, cursor stays on END ----
def cut(pg, cur, begin, end):
    i = pg.find(begin, cur)
    if i < 0: return None, cur
    i += len(begin); j = pg.find(end, i)
    if j < 0: return None, cur
    return pg[i:j], j
CEN, PLN, LNK = b'<td align=center><font size=2 color=#000000>', b'<td><font size=2 color=#000000>', b'<td><font size=2 color=#000000><a href='
K_TOTAL = S.K_TOTAL
def parse_list(pg, tab, mail=False):
    p0 = pg.find(b'<img src=../image/title0%d.gif border=0>' % tab)
    if p0 < 0: return None
    tot, cur = cut(pg, p0, K_TOTAL, b'</b>')
    if tot is None: return None
    rows = []
    id_, cur = cut(pg, cur, CEN, b'</font>')
    while id_ is not None:
        c2, cur = cut(pg, cur, PLN, b'</font>')
        if c2 is None: break
        c3 = None
        if not mail:
            c3, cur = cut(pg, cur, CEN, b'</font>')
            if c3 is None: break
        url, cur = cut(pg, cur, LNK, b'>')
        if url is None: break
        title, cur = cut(pg, cur, b'>', b'</a></font></td>')
        if title is None: break
        last, cur = cut(pg, cur, CEN, b'</font></td>')
        if last is None: break
        rows.append((id_, c2, c3, url, title, last))
        id_, cur = cut(pg, cur, CEN, b'</font>')
    pages = []
    u, cur = cut(pg, cur, b'<b><a href=', b'>')
    while u is not None:
        t, cur = cut(pg, cur, b'>', b'</a>')
        if t is None: break
        pages.append((t, u))
        u, cur = cut(pg, cur, b'<b><a href=', b'>')
    return int(tot), rows, pages
H = lambda w: b'<td width=%d><font size=2 color=#fff098><b>' % w
def parse_read(pg, tab, mail=False):
    p0 = pg.find(b'<img src=../image/title0%d.gif border=0>' % tab)
    if p0 < 0: return None
    cur = p0; r = {}
    seq = ((b'w130', 130), (b'w170', 170), (b'w250', 250)) if mail else ((b'no', 30), (b'name', 130), (b'hits', 30), (b'date', 170))
    for k, w in seq:
        r[k], cur = cut(pg, cur, H(w), b'</b>')
        if r[k] is None: return None
    r['subj'], cur = cut(pg, cur, b'<font size=3 color=#483010><b>', b'</b></font>')
    r['body'], cur = cut(pg, cur, b'<font size=2>', b'</font>')
    if r['subj'] is None or r['body'] is None: return None
    r['prev'], cur = cut(pg, cur, b'<b>' + S.K_PREV + b'</b><a href=', b'>')
    r['next'], cur = cut(pg, cur, b'<b>' + S.K_NEXT + b'</b><a href=', b'>')
    r['list'], cur = cut(pg, cur, b'<a href=lsbbs01_t.asp' if mail else b'<a href=lsbbs01.asp', b'>')
    r['own'], cur = cut(pg, cur, b'<a href=rmbbs01.asp?', b'>')
    return r
def get(path, q='', body=b'', ip='1.2.3.4'):
    code, data = S.board_http('GET' if not body else 'POST', path, q, body, ip)
    return code, data

# ---- board: seed notice ----
c, pg = get('c/notice/lsbbs01.asp', 'nat=1&server=1')
r = parse_list(pg, 1)
chk('notice list parses (client cutter)', c == 200 and r and r[0] == 1 and len(r[1]) == 1, r and r[:2])
chk('seed post is Chinese on the cn channel', '欢迎'.encode('gbk') in pg)
c, pgt = get('t/notice/lsbbs01.asp', 'nat=1&server=1')
chk('tw channel Big5', '歡迎'.encode('cp950') in pgt and '欢迎'.encode('gbk') not in pgt)
rd = parse_read(get('c/notice/atbbs01.asp', 'sn=1')[1], 1)
chk('read page parses', rd and rd[b'no'] == b'1' and rd['subj'] and rd['body'] and rd['list'] is not None, rd)
# ---- post as kkkkkkkk to the free board ----
def post(sect, who, subj, text, ch='c', nat=1):
    enc = S.BW_ENC[ch]
    qs = f"f_name={who}&f_subject={up.quote(subj, encoding=enc)}&f_contents={up.quote(text, encoding=enc)}&nat={nat}&server=1"
    return S.board_http('POST', f'{ch}/{sect}/inbbs02_t.asp', '', qs.encode(), '1.2.3.4')[1]
chk('post accepted', post('free', 'kkkkkkkk', '你好 世界', '第一行\n第二行 <b>x</b>') == b'OK')
chk('unknown author refused', post('free', 'nobody', 'x', 'y') == b'denied')
chk('players cannot post notices', post('notice', 'kkkkkkkk', 'x', 'y') == b'denied')
r = parse_list(get('c/free/lsbbs01.asp', 'nat=1&server=1')[1], 3)
chk('free list has the post', r and r[0] == 1 and r[1][0][4] == '你好 世界'.encode('gbk'), r)
rd = parse_read(get('c/free/atbbs01.asp', 'sn=1&nat=1')[1], 3)
chk('read: body lines + markup stripped', rd and rd['body'].count(b'<br>') >= 2 and b'<b>' not in rd['body'] and '第二行'.encode('gbk') in rd['body'])
chk('read: hits counted', rd[b'hits'] == b'1')
# 20 more posts -> paging
for i in range(20): post('free', 'kkkkkkkk', f'p{i}', 'x')
c, pg = get('c/free/lsbbs01.asp', 'nat=1&server=1'); r = parse_list(pg, 3)
chk('15 rows on page 1, total 21, page links', len(r[1]) == 15 and r[0] == 21 and [t for t, u in r[2]][:2] == [b'2', b'...'] or r[2][0][0] == b'2', r[2])
u = [u for t, u in r[2] if t == b'2'][0].decode()
c, pg = get('c/free/' + u.split('?')[0], u.split('?')[1]); r2 = parse_list(pg, 3)
chk('page 2 holds the rest (6)', r2 and len(r2[1]) == 6, r2 and len(r2[1]))
r3 = parse_list(get('c/free/lsbbs01.asp', 't=1&q=' + up.quote('你好', encoding='gbk') + '&nat=1')[1], 3)
chk('search by subject', r3 and r3[0] == 1)
# edit / delete own only
chk('other player cannot delete', S.board_http('POST', 'c/free/rmbbs02_t.asp', '', b'sn=1&f_name=llllllll', 'x')[1] == b'denied')
chk('owner deletes', S.board_http('POST', 'c/free/rmbbs02_t.asp', '', b'sn=1&f_name=kkkkkkkk', 'x')[1] == b'OK')
chk('post is gone', parse_list(get('c/free/lsbbs01.asp', 'nat=1')[1], 3)[0] == 20)
# nation board is per nation
post('nation', 'kkkkkkkk', 'nat1', 'x', nat=1)
chk('nation board filtered by nat', parse_list(get('c/nation/lsbbs01.asp', 'nat=1')[1], 5)[0] == 1 and parse_list(get('c/nation/lsbbs01.asp', 'nat=2')[1], 5)[0] == 0)
# persistence
S._BOARD = None
chk('board survives a restart', parse_list(get('c/free/lsbbs01.asp', 'nat=1')[1], 3)[0] == 20)
# ---- mail ----
accs = S.load_accounts()
for k in ('kkkkkkkk', 'llllllll'): accs[k]['mail'] = []
S.save_accounts(accs)
def send(frm, to, subj, text, ch='c'):
    enc = S.BW_ENC[ch]
    qs = f"f_sender={frm}&f_receiver={to}&f_subject={up.quote(subj, encoding=enc)}&f_contents={up.quote(text, encoding=enc)}"
    return S.board_http('GET', f'{ch}/mail_box/inbbs02.asp', qs, b'', 'x')[1]
chk('mail sent', send('kkkkkkkk', 'llllllll', '问候', '你好\n再见') == b'OK')
chk('mail to nobody refused', send('kkkkkkkk', 'zzzzzzzz', 'a', 'b') == b'denied')
r = parse_list(get('c/mail_box/lsbbs01_t.asp', 'server=1&owner=llllllll&passwd=x')[1], 6, mail=True)
chk('mail list parses', r and r[0] == 1 and r[1][0][1] == b'kkkkkkkk' and r[1][0][4] == '问候'.encode('gbk') and r[1][0][5] == b'NEW' or r[1][0][5] == '新'.encode('gbk'), r and r[1])
mid = int(r[1][0][0])
rd = parse_read(get('c/mail_box/atbbs01.asp', f'sn={mid}&server=1&owner=llllllll')[1], 6, mail=True)
chk('mail read parses', rd and rd[b'w130'] == b'kkkkkkkk' and '你好'.encode('gbk') in rd['body'] and rd['own'].startswith(b'sn=%d&k=' % mid), rd)
r = parse_list(get('c/mail_box/lsbbs01_t.asp', 'server=1&owner=llllllll')[1], 6, mail=True)
chk('read letter no longer NEW', r[1][0][5] not in (b'NEW', '新'.encode('gbk')), r[1][0][5])
chk('other player sees no letters', parse_list(get('c/mail_box/lsbbs01_t.asp', 'server=1&owner=kkkkkkkk')[1], 6, mail=True)[0] == 0)
chk('delete', S.board_http('GET', 'c/mail_box/rmbbs02.asp', f'sn={mid}&server=1&owner=llllllll', b'', 'x')[1] == b'OK' and
    parse_list(get('c/mail_box/lsbbs01_t.asp', 'server=1&owner=llllllll')[1], 6, mail=True)[0] == 0)
# the online check: a request from an unknown IP is nobody
S.BOARD_REQUIRE_ONLINE = True
chk('offline caller is nobody (post)', post('free', 'kkkkkkkk', 'x', 'y') == b'denied')
chk('offline caller is nobody (mail list)', parse_list(get('c/mail_box/lsbbs01_t.asp', 'server=1&owner=llllllll')[1], 6, mail=True)[0] == 0)
chk('404 for junk', get('c/zzz/x.asp')[0] == 404 and get('q/free/x.asp')[0] == 404)
# ---- through the real HTTP server (update port): GET list, POST with a body, no-cache headers ----
import asyncio, http.client, threading
S.BOARD_REQUIRE_ONLINE = False
async def _http():
    srv = S.OTA.UpdateServer('/tmp/mp/_upd', log=lambda *a: None, board=S.board_http)
    server = await srv.start('127.0.0.1', 0)
    port = server.sockets[0].getsockname()[1]
    def call():
        c = http.client.HTTPConnection('127.0.0.1', port, timeout=5)
        c.request('GET', '/b/e/free/lsbbs01.asp?nat=1&server=1'); r = c.getresponse(); a = (r.status, r.getheader('Cache-Control'), r.read())
        c.request('POST', '/b/e/free/inbbs02_t.asp', body=b'f_name=kkkkkkkk&f_subject=http+post&f_contents=hi&nat=1', headers={'Content-Type': 'application/x-www-form-urlencoded'})
        r = c.getresponse(); b = (r.status, r.read())
        c.request('GET', '/b/e/free/lsbbs01.asp?nat=1'); r = c.getresponse(); d = r.read()
        return a, b, d
    a, b, d = await asyncio.get_running_loop().run_in_executor(None, call)
    server.close()
    return a, b, d
a, b, d = asyncio.run(_http())
chk('http GET list', a[0] == 200 and b'title03' in a[2] and 'no-cache' in a[1])
chk('http POST body used', b == (200, b'OK') and b'http post' in d)

# ---- (2026-10-26) the web request may come from ANOTHER public IP than the game connection: online-name fallback ----
class _FakeS:
    def __init__(s, acc, ip): s.acc, s.peer = acc, (ip, 1)
S.BOARD_REQUIRE_ONLINE = True
S.ONLINE.add(_FakeS('kkkkkkkk', '60.250.1.1')) if hasattr(S.ONLINE, 'add') else S.ONLINE.append(_FakeS('kkkkkkkk', '60.250.1.1'))
chk('other-IP request of an online player = him', S.bw_player('220.128.9.9', 'kkkkkkkk') == 'kkkkkkkk')
chk('same IP still works', S.bw_player('60.250.1.1', 'KKKKKKKK') == 'kkkkkkkk')
chk('offline name is nobody', S.bw_player('220.128.9.9', 'zzzz') is None)
r = S.board_http('POST', 'c/free/inbbs02_t.asp', '', b'f_name=kkkkkkkk&f_subject=hi&f_contents=x&nat=1', '220.128.9.9')
chk('post from other IP accepted', r[1] == b'OK', r)
chk('personal/ mail check route', S.board_http('GET', 'c/personal/lsbbs01_t.asp', 'owner=kkkkkkkk&passwd=1', b'', '220.128.9.9')[0] == 200)
chk('poll route', S.board_http('GET', 'c/poll/lsbbs01.asp', '', b'', 'x')[0] == 200)


# ---- (2026-10-26) hardening: password auth, mail tokens, quotas, sanitising, nation board, flood guard ----
accs = S.load_accounts()
S.STORE.pw_set(accs['kkkkkkkk'], 'secret-pw'); accs['kkkkkkkk'].pop('web_pw', None); S.save_accounts(accs)
S.ONLINE.clear() if hasattr(S.ONLINE, 'clear') else None
S.ONLINE.add(_FakeS('kkkkkkkk', '60.250.1.1')); S.ONLINE.add(_FakeS('llllllll', '60.250.2.2'))
accs = S.load_accounts(); accs['kkkkkkkk'].pop('web_tag', None); S.save_accounts(accs)
chk('name-only from another IP (account never proved its password)', S.bw_auth('9.9.9.9', 'kkkkkkkk')[1] == 'name')
chk('right password = pw, any IP', S.bw_auth('9.9.9.9', 'kkkkkkkk', 'secret-pw') == ('kkkkkkkk', 'pw'))
chk('web_pw flag stored', S.load_accounts()['kkkkkkkk'].get('web_pw') is True)
chk('after that a bare name from another IP is refused', S.bw_auth('9.9.9.9', 'kkkkkkkk') == (None, ''))
chk('wrong password, other IP: refused', S.bw_auth('9.9.9.9', 'kkkkkkkk', 'nope') == (None, ''))
chk('same IP as the game session still ok', S.bw_auth('60.250.1.1', 'kkkkkkkk')[1] == 'ip')
chk('unknown / offline name', S.bw_auth('9.9.9.9', 'jjjjjjjj', 'x') == (None, ''))
# nation board: nat comes from the account, not from the request
S.board_http('POST', 'c/nation/inbbs02_t.asp', '', b'f_name=kkkkkkkk&f_passwd1=secret-pw&f_subject=forged&f_contents=x&nat=2', '9.9.9.9')
B = S.board_load(); chk('nation post stored with the poster nation, not the forged nat', B['nation'][-1]['nat'] == 1, B['nation'][-1])
# sanitising: control chars out, page markers cannot be typed
S.board_http('POST', 'c/free/inbbs02_t.asp', '', b'f_name=kkkkkkkk&f_passwd1=secret-pw&f_subject=a%01b%00c&f_contents=x&nat=1', '9.9.9.9')
chk('control chars removed', B['free'][-1]['subject'] == 'abc', B['free'][-1]['subject'])
Pg = S._Page('gbk', 'zh-cn'); Pg.t(S.K_TOTAL.decode('cp949') + 'x')
chk('page marker in text is scrubbed', S.K_TOTAL not in Pg.done())
# quotas
S.BW_POSTS_HOUR = 3; S._BW_HIST.clear()
res = [S.board_http('POST', 'c/free/inbbs02_t.asp', '', b'f_name=kkkkkkkk&f_passwd1=secret-pw&f_subject=q%d&f_contents=x&nat=1' % i, '9.9.9.9')[1] for i in range(5)]
chk('hourly post limit', res == [b'OK', b'OK', b'OK', b'too many', b'too many'], res)
S.BW_POSTS_HOUR = 10**6
S.BW_IP_GAP = 60; S.BOARD_POST_GAP = 0; S._BOARD_LAST.clear()
r1 = S.board_http('POST', 'c/free/inbbs02_t.asp', '', b'f_name=kkkkkkkk&f_passwd1=secret-pw&f_subject=g1&f_contents=x&nat=1', '7.7.7.7')[1]
r2 = S.board_http('POST', 'c/free/inbbs02_t.asp', '', b'f_name=kkkkkkkk&f_passwd1=secret-pw&f_subject=g2&f_contents=x&nat=1', '7.7.7.7')[1]
chk('per-IP post gap', (r1, r2) == (b'OK', b'too fast'), (r1, r2)); S.BW_IP_GAP = 0
# mail: tokens, per-sender cap, hourly cap
accs = S.load_accounts(); accs['llllllll']['mail'] = []; S.save_accounts(accs)
S._BW_HIST.clear()
def send(i): return S.board_http('GET', 'c/mail_box/inbbs02.asp', f'f_sender=kkkkkkkk&f_passwd=secret-pw&f_receiver=llllllll&f_subject=s{i}&f_contents=hi', b'', '9.9.9.9')[1]
sent = [send(i) for i in range(7)]
chk('per-sender mail cap in one inbox', sent[:5] == [b'OK'] * 5 and sent[5] == b'full', sent)
lst = S.board_http('GET', 'c/mail_box/lsbbs01_t.asp', 'server=1&owner=llllllll', b'', '60.250.2.2')[1]   # llllllll never proved a pw: ip match ok
import re as _re
links = _re.findall(rb'atbbs01\.asp\?sn=(\d+)&k=([0-9a-f]{16})', lst)
chk('mail list links carry a signed token', len(links) == 5, links[:2])
sn, k = links[0]
rd = S.board_http('GET', 'c/mail_box/atbbs01.asp', f'sn={int(sn)}&server=1&owner=llllllll&k={k.decode()}', b'', '5.5.5.5')[1]
chk('read with the token from another IP works', b's' in rd and K_TOTAL not in rd and b'hi' in rd)
accs = S.load_accounts(); accs['llllllll']['web_pw'] = True; S.save_accounts(accs)
bad = S.board_http('GET', 'c/mail_box/atbbs01.asp', f'sn={int(sn)}&server=1&owner=llllllll', b'', '5.5.5.5')[1]
chk('read without token / proof from a stranger: empty', b'hi' not in bad)
bad2 = S.board_http('GET', 'c/mail_box/rmbbs02.asp', f'sn={int(sn)}&server=1&owner=llllllll&k=0000000000000000', b'', '5.5.5.5')[1]
chk('delete with a forged token refused', bad2 != b'OK')
ok2 = S.board_http('GET', 'c/mail_box/rmbbs02.asp', f'sn={int(sn)}&server=1&owner=llllllll&k={k.decode()}', b'', '5.5.5.5')[1]
chk('delete with the real token', ok2 == b'OK')
S._BW_HIST.clear(); S.BW_MAIL_HOUR = 2
accs = S.load_accounts(); accs['llllllll']['mail'] = []; S.save_accounts(accs)
s3 = [send(i) for i in range(4)]
chk('hourly mail limit', s3 == [b'OK', b'OK', b'too many', b'too many'], s3)
# trust-on-first-use of the client's passwd value (it is NOT the login password but stable per account)
S.ONLINE.add(_FakeS('jjjjjjjj', '60.250.3.3'))
r = S.bw_auth('9.1.1.1', 'jjjjjjjj', '99248101250'); chk('first request from another IP learns the tag', r == ('jjjjjjjj', 'name'), r)
chk('tag stored as a hash, not the value', S.load_accounts()['jjjjjjjj'].get('web_tag') and '99248101250' not in str(S.load_accounts()['jjjjjjjj']))
r = S.bw_auth('9.2.2.2', 'jjjjjjjj', '99248101250'); chk('same value from yet another IP = tag', r == ('jjjjjjjj', 'tag'), r)
chk('stranger with only the name: refused', S.bw_auth('9.3.3.3', 'jjjjjjjj') == (None, '') and S.bw_auth('9.3.3.3', 'jjjjjjjj', 'guess') == (None, ''))
r = S.bw_auth('60.250.3.3', 'jjjjjjjj', 'newvalue'); chk('same IP as the game session relearns a changed value', r == ('jjjjjjjj', 'ip'), r)
chk('then the new value works elsewhere, the old one not', S.bw_auth('9.4.4.4', 'jjjjjjjj', 'newvalue')[1] == 'tag' and S.bw_auth('9.4.4.4', 'jjjjjjjj', '99248101250')[0] is None)
# HTTP flood guard + log redaction + long URL (real HTTP server)
logs = []
async def _flood():
    srv = S.OTA.UpdateServer('/tmp/mp/_upd', log=lambda *a: logs.append(' '.join(map(str, a))), board=S.board_http)
    server = await srv.start('127.0.0.1', 0)
    port = server.sockets[0].getsockname()[1]
    def call():
        codes = []
        c = http.client.HTTPConnection('127.0.0.1', port, timeout=5)
        c.request('GET', '/b/c/personal/lsbbs01_t.asp?owner=kkkkkkkk&passwd=SUPERSECRET'); r = c.getresponse(); r.read()
        for i in range(45):
            c.request('GET', '/b/e/free/lsbbs01.asp?nat=1'); r = c.getresponse(); r.read(); codes.append(r.status)
            if r.status == 429: c = http.client.HTTPConnection('127.0.0.1', port, timeout=5)
        c2 = http.client.HTTPConnection('127.0.0.1', port, timeout=5)
        c2.request('GET', '/b/e/free/lsbbs01.asp?x=' + 'a' * 5000); r = c2.getresponse(); long_ = r.status; r.read()
        return codes, long_
    out = await asyncio.get_running_loop().run_in_executor(None, call)
    server.close()
    return out
codes, long_ = asyncio.run(_flood())
chk('flood guard: 429 after 40 requests / 10 s', 429 in codes and codes.index(429) <= 40, codes[-6:])
chk('too long URL refused', long_ in (414, 429), long_)
chk('password never logged', not any('SUPERSECRET' in l for l in logs) and any('passwd=***' in l for l in logs), [l for l in logs if 'passwd' in l][:1])
