# ---- BOARD + MAIL WEB PAGES (user 2026-10-26: "board 以及 mail 的功能沒辦法使用") -------------------------------------------
# The client's BOARD (F-key menu) and SGMAIL windows are WEB PAGES of the original site (bbs.sgalaxy.com/tc_new/gamebbs/):
# the exe downloads an ASP page with urlmon (IE stack), cuts the fields out of the HTML with plain strstr() (no HTML parser)
# and fills its own windows.  Reverse engineered from SG.exe 1.8.5 and checked against the real pages (docs/BOARD_MAIL.md):
#   base URL  = string at 0x64eae0 (<= 38 chars) -> we patch it to http://<server>:<update-port>/b/<c|t|e>/  (tools/build_i18n_exe.py)
#   board     = base + {notice|qna|free|bug|nation}/ + lsbbs01.asp (list) / atbbs01.asp (read) / inbbs02_t.asp (post) /
#               mdbbs02_t.asp (edit) / rmbbs02_t.asp (delete)
#   mail      = base + mail_box/ + lsbbs01_t.asp?server=&owner=&passwd= (list) / atbbs01.asp (read) / inbbs02.asp (send) /
#               rmbbs02.asp (delete);  owner = the LOGIN ACCOUNT (004ee140), passwd = not a secret (ignored)
# The HTML keeps the markers the client searches for (Korean cp949 byte strings baked into the exe, never translated); the
# page text is encoded for the channel in the URL (c = GBK, t = Big5, e = cp1252).  Who is who: the HTTP request carries no
# login, so who-is-who is decided by bw_auth(): (1) the PASSWORD the client sends (passwd / f_passwd1 = checked like the game
# login, strongest, any IP), else (2) an online session of X from the same IP, else (3) an online session of X from another
# IP - only for accounts that never proved their password (players behind carrier NAT leave from several IPs).  Mail read /
# delete carry only the name, so every mail link we hand out carries a signed token k= (HMAC of account + letter id).
# Details, limits and the threat model: docs/BOARD_MAIL.md (section 防护).
import urllib.parse as _up, hmac as _hmac, hashlib as _hl

BOARD_NAMES = ("notice", "qna", "free", "bug", "nation")
BOARD_PAGE = 15                    # rows per page (the real site: 15)
BOARD_MAX = 400                    # posts kept per board (oldest dropped)
BOARD_SUBJ_MAX, BOARD_BODY_MAX = 60, 1500
BOARD_FILE = os.path.join(os.path.dirname(DB_FILE), "board.json")
BOARD_REQUIRE_ONLINE = True        # tests switch it off
BOARD_POST_GAP = 10                # seconds between two posts of one player
BW_IP_GAP = 3                      # seconds between two posts from one IP address
BW_POSTS_HOUR = 20                 # board posts per account per hour
BW_MAIL_HOUR = 20                  # letters per sender per hour
BW_MAIL_PER_SENDER = 5             # letters of ONE sender that may sit in one inbox (a flood cannot push real mail out)
_BW_HIST = {}                      # (kind, key) -> [timestamps] for the hourly quotas
_BW_CTRL = dict.fromkeys(list(range(0, 10)) + [11, 12] + list(range(14, 32)) + [127], None)   # control chars (keep \n, \r)
_BOARD = None
_BOARD_LAST = {}
BW_ENC = {"c": "gbk", "t": "cp950", "e": "cp1252"}
BW_LANG = {"c": "zh-cn", "t": "zh-tw", "e": "en"}
# page markers - byte strings of the client (see the dumps in docs/BOARD_MAIL.md)
K_TOTAL = b"\xb0\xcb\xbb\xf6\xb5\xc8 \xc0\xfc\xc3\xbc \xb1\xdb \xbc\xf6  : "      # "total searched posts : "
K_PREV = b"\xc0\xcc\xc0\xfc\xb1\xdb : "                                             # "previous post : "
K_NEXT = b"\xb4\xd9\xc0\xbd\xb1\xdb : "                                             # "next post : "
BW_LABELS = {"zh-cn": ("编号", "作者", "点击", "日期", "标题", "发件人", "收件人"),
             "zh-tw": ("編號", "作者", "點擊", "日期", "標題", "寄件人", "收件人"),
             "en": ("No", "Name", "Hits", "Date", "Subject", "From", "To")}
BW_STATUS = {"zh-cn": "新", "zh-tw": "新", "en": "NEW"}

# (user 11-02 17:44 "公告欄裡面還有SG字樣要改掉") the welcome post in the game's new name; board_load renames the old one
_BW_WELCOME = {"name": "GO Team",
    "subject": {"en": "Welcome to the Galactic Overlord board", "zh-cn": "欢迎来到银河霸主公告板", "zh-tw": "歡迎來到銀河霸主公告板"},
    "body": {"en": "Notices of the game staff appear here.\nFree, Q&A and Bug boards are open to every commander (level 15 and up).\nLetters: the MAIL window.",
             "zh-cn": "游戏管理员的公告会发布在这里。\n自由板、问答板、错误回报板开放给所有 15 级以上的指挥官。\n信件：邮件窗口。",
             "zh-tw": "遊戲管理員的公告會發佈在這裡。\n自由板、問答板、錯誤回報板開放給所有 15 級以上的指揮官。\n信件：郵件視窗。"}}

def _bw_seed():
    t = time.time()
    return {"notice": [dict({"id": 1, "t": t, "acc": "", "nat": 0, "hits": 0}, **_BW_WELCOME)]}

def _bw_rename_welcome(B):
    """the seed post of an older server (author "SG Team") -> the new texts; True when changed"""
    for p in B.get("notice", []):
        if isinstance(p, dict) and not p.get("acc") and p.get("name") == "SG Team":
            p.update(_BW_WELCOME)
            return True
    return False

def board_load():
    global _BOARD
    if _BOARD is None:
        try:
            with open(BOARD_FILE, encoding="utf-8") as f:
                _BOARD = json.load(f)
        except Exception:
            _BOARD = _bw_seed()
        for b in BOARD_NAMES:
            _BOARD.setdefault(b, [])
        if _bw_rename_welcome(_BOARD):
            board_save()
    return _BOARD

def _bw_secret():
    """random key (kept in board.json, never in the repo) that signs the mail links"""
    B = board_load()
    k = B.get("_secret")
    if not isinstance(k, str) or len(k) < 32:
        k = os.urandom(16).hex(); B["_secret"] = k; board_save()
    return k.encode()

def _bw_tok(acc, sn):
    return _hmac.new(_bw_secret(), f"{acc}|{sn}".encode("latin-1", "replace"), _hl.sha256).hexdigest()[:16]

def _bw_tok_ok(acc, sn, k):
    return bool(k) and _hmac.compare_digest(str(k), _bw_tok(acc, sn))

def _bw_quota(key, limit, window=3600):
    """True and counted while the key has fewer than `limit` events in the last `window` seconds"""
    now = time.time()
    h = [t for t in _BW_HIST.get(key, ()) if now - t < window]
    if len(h) >= limit:
        _BW_HIST[key] = h
        return False
    h.append(now); _BW_HIST[key] = h
    if len(_BW_HIST) > 4000:
        for k in [k for k, v in _BW_HIST.items() if not v or now - v[-1] > window]:
            _BW_HIST.pop(k, None)
    return True

def board_save():
    try:
        tmp = BOARD_FILE + ".tmp"
        with open(tmp, "w", encoding="utf-8") as f:
            json.dump(_BOARD, f, ensure_ascii=False)
        os.replace(tmp, BOARD_FILE)
    except Exception as e:
        log(f"   board save error: {e!r}")

def _bw_txt(v, lang):
    if isinstance(v, dict):
        return v.get(lang) or v.get("en") or next(iter(v.values()), "")
    return v or ""

def _bw_name(rec, lang):
    if rec.get("acc"):
        return display_name(rec["acc"]) or rec["acc"]
    return rec.get("name", "?")

def _bw_clean(s, cjk, one_line=False):
    s = str(s).replace("\r", "")
    s = s.replace("<", "＜" if cjk else "(").replace(">", "＞" if cjk else ")")
    if one_line:
        s = " ".join(s.split())
    return s

def _bw_body(s, cjk):
    return "<br>\r\n".join(_bw_clean(l, cjk) for l in str(s).split("\n"))

def _bw_online(ip):
    return [s.acc for s in list(ONLINE) if getattr(s, "acc", None) and (getattr(s, "peer", None) or ("",))[0] == ip]

def _bw_all():
    return [s.acc for s in list(ONLINE) if getattr(s, "acc", None)]

def _bw_pw(q):
    """the password the client puts in its web requests (list: passwd, post/edit: f_passwd1, send: f_passwd)"""
    for k in ("passwd", "f_passwd", "f_passwd1"):
        v = q.get(k)
        if v:
            return v
    return ""

def bw_auth(ip, raw, pw=""):
    """-> (account key, how) or (None, ''); how = pw | ip | name | test.  raw = the name bytes as latin-1 str"""
    n = (raw or "").strip().lower()
    if not n or len(n) > 64:
        return None, ""
    accs = load_accounts()
    key = next((k for k in accs if k.lower() == n and "commander" in accs[k]), None)
    if not BOARD_REQUIRE_ONLINE:
        return (key, "test") if key else (None, "")
    if not key:
        return None, ""
    rec = accs[key]
    try:
        if pw and STORE.pw_check(rec, pw):
            if not rec.get("web_pw"):                       # from now on a bare name is no proof for this account
                rec["web_pw"] = True; accs[key] = rec; save_accounts(accs)
            return key, "pw"
    except Exception:
        pass
    mine = [x for x in list(ONLINE) if getattr(x, "acc", None) and str(x.acc).lower() == key.lower()]
    if not mine:
        return None, ""
    tag = _hl.sha256(pw.encode("latin-1", "replace")).hexdigest() if pw else ""
    def bind():                                         # remember the client's passwd of this account (SHA-256, not the value)
        accs2 = load_accounts()
        if key in accs2 and tag:
            accs2[key]["web_tag"] = tag; save_accounts(accs2)
    if any((getattr(x, "peer", None) or ("",))[0] == ip for x in mine):
        if tag and rec.get("web_tag") != tag:           # same IP as the game session: legitimate, (re)learn the value
            bind()
        return key, "ip"
    # The web request and the game connection of one player can leave from DIFFERENT public IPs (user log 2026-10-26: game
    # 60.250.152.229, requests from 60.250.152.229 / 220.128.128.151 / 220.128.135.193 / 60.250.80.130 - carrier NAT), so the
    # IP match alone refused every post.  The client's `passwd` is NOT the login password but a value that stayed the same
    # across sessions (same SHA-256 tag in two sessions): trust-on-first-use - the first request of an online account fixes it
    # (`web_tag`), after that a request from another IP must repeat it.  A stranger who only knows the name cannot.
    # (Residual risk: someone who reaches the server before the owner's first web request.)
    if rec.get("web_pw"):
        return None, ""
    bound = rec.get("web_tag")
    if bound:
        return (key, "tag") if tag and _hmac.compare_digest(bound, tag) else (None, "")
    if tag:
        bind()
        log(f"   BOARD web tag learned for {key!r} ({tag[:8]}) ip={ip}")
    return key, "name"

def bw_player(ip, raw, pw=""):
    return bw_auth(ip, raw, pw)[0]

def _bw_params(query, body):
    out = {}
    for part in (query or "").split("&") + ((body or b"").decode("latin-1")).split("&"):
        if "=" in part:
            k, v = part.split("=", 1)
            out[k.strip()] = _up.unquote_to_bytes(v.replace("+", " ")).decode("latin-1")
    return out

def _bw_dec(raw, enc):
    """text typed by the player: bytes of the client code page (latin-1 str) -> Unicode"""
    b = raw.encode("latin-1", "replace")
    for e in (enc, "utf-8"):
        try:
            return b.decode(e).translate(_BW_CTRL)
        except Exception:
            pass
    return b.decode("latin-1", "replace").translate(_BW_CTRL)

class _Page:
    def __init__(self, enc, lang):
        self.enc, self.lang, self.cjk = enc, lang, lang != "en"
        self.out = []
    def raw(self, b):
        self.out.append(b if isinstance(b, bytes) else b.encode("latin-1"))
    def t(self, s):
        b = str(s).encode(self.enc, "replace")
        for m in (K_TOTAL, K_PREV, K_NEXT):           # a player must not be able to type the page markers the client searches for
            if m in b:
                b = b.replace(m, b"?" * len(m))
        self.out.append(b)
    def done(self):
        return b"".join(self.out)

_HEAD = ("<html>\r\n<head>\r\n<style>\r\n<!--\r\nbody, input, select, textarea { font-size:9pt; font-family:Tahoma, Verdana, Arial; }\r\n"
         "-->\r\n</style>\r\n</head>\r\n<body bgcolor=#000000 text=#805820 link=#0000ff vlink=#000099 >\r\n<center>\r\n")

def _bw_list_page(P, title_no, rows, total, links, mail):
    """rows: [(id, date, name, subject, url, last)]   (mail: date column is the sender, last = NEW / date)"""
    L = BW_LABELS[P.lang]
    P.raw(_HEAD); P.raw(f"<img src=../image/title0{title_no}.gif border=0><p>\r\n")
    P.raw("<table border=0 width=600 cellspacing=0 cellpadding=2>\r\n<tr>\r\n<td width=300>\r\n<font size=2 color=#805820><b>")
    P.raw(K_TOTAL); P.raw(f"{total}</b></font>\r\n</td>\r\n<td width=300 align=right>\r\n</td>\r\n</tr>\r\n</table>\r\n")
    P.raw("<table border=0 width=600 cellspacing=0 cellpadding=2>\r\n<tr bgcolor=#805820>\r\n")
    heads = (L[0], L[5] if mail else L[3], L[1], L[4], L[2]) if not mail else (L[0], L[5], L[4], "")
    for h, w in zip(heads, (40, 80, 100, 340, 40)):
        P.raw(f"<td width={w} align=center><font size=2 color=#fff098><b>"); P.t(h); P.raw("</b></font></td>\r\n")
    P.raw("</tr>\r\n")
    for i, (rid, date, name, subj, url, last) in enumerate(rows):
        P.raw(f"<tr bgcolor={'#ffffff' if i % 2 == 0 else '#eeeeee'}>\r\n")
        P.raw(f"<td align=center><font size=2 color=#000000>{rid}</font></td>\r\n")
        P.raw("<td><font size=2 color=#000000>"); P.t(date); P.raw("</font></td>\r\n")
        if not mail:
            P.raw("<td align=center><font size=2 color=#000000>"); P.t(name); P.raw("</font></td>\r\n")
        P.raw(f"<td><font size=2 color=#000000><a href={url}>"); P.t(subj); P.raw("</a></font></td>\r\n")
        P.raw("<td align=center><font size=2 color=#000000>"); P.t(last); P.raw("</font></td>\r\n</tr>\r\n")
    if links:
        P.raw("<tr>\r\n<td colspan=5 align=center bgcolor=#ffffff>\r\n<font size=2 color=#000000>\r\n| ")
        for text, url in links:
            if url:
                P.raw(f"<b><a href={url}>"); P.t(text); P.raw("</a></b> | \r\n")
            else:
                P.raw(f"<font color=#000000><b>{text}</b></font> | \r\n")
        P.raw("</font>\r\n</td>\r\n</tr>\r\n")
    P.raw("</table>\r\n</body>\r\n</html>\r\n")
    return P.done()

def _bw_read_page(P, title_no, number, name_b, hits, date, subject, body, prev, nxt, list_url, own_q, mail_rcpt=None):
    L = BW_LABELS[P.lang]
    P.raw(_HEAD); P.raw(f"<img src=../image/title0{title_no}.gif border=0><p>\r\n")
    P.raw("<table border=0 width=600 cellspacing=0 cellpadding=2>\r\n<tr bgcolor=#805820>\r\n")
    def cell(w, label, val_b=None, val=None):
        P.raw(f"<td width={w + 10}><font size=2 color=#fff098>["); P.t(label); P.raw("]</font></td>\r\n")
        P.raw(f"<td width={w}><font size=2 color=#fff098><b>")
        P.raw(val_b) if val_b is not None else P.t(val)
        P.raw("</b></font></td>\r\n")
    if mail_rcpt is None:
        cell(30, L[0], val=str(number)); cell(130, L[1], val_b=name_b); cell(30, L[2], val=str(hits)); cell(170, L[3], val=date)
    else:
        cell(130, L[5], val_b=name_b); cell(170, L[3], val=date)
        P.raw("<td width=60><font size=2 color=#fff098>["); P.t(L[6]); P.raw("]</font></td>\r\n")
        P.raw("<td width=250><font size=2 color=#fff098><b>"); P.t(mail_rcpt); P.raw("</b></font></td>\r\n")
    P.raw("</tr>\r\n<tr>\r\n<td colspan=8 align=center bgcolor=#ffffff>\r\n<br>\r\n<font size=3 color=#483010><b>")
    P.t(_bw_clean(subject, P.cjk, True)); P.raw("</b></font>\r\n<p>\r\n")
    P.raw("<table border=0 width=550 cellspacing=0 cellpadding=0>\r\n<tr><td>\r\n<font size=2>\r\n")
    P.t(_bw_body(body, P.cjk)); P.raw("<br>\r\n</font>\r\n<p>\r\n</td></tr>\r\n</table>\r\n</td>\r\n</tr>\r\n")
    P.raw("<tr>\r\n<td colspan=8 bgcolor=#ffffff>\r\n&nbsp;<br>\r\n</td>\r\n</tr>\r\n")
    for mark, item in ((K_PREV, prev), (K_NEXT, nxt)):
        if item:
            P.raw("<tr bgcolor=#eeeeee>\r\n<td colspan=8>\r\n<font size=2>\r\n<b>"); P.raw(mark)
            P.raw(f"</b><a href={item[0]}>"); P.t(_bw_clean(item[1], P.cjk, True)); P.raw("</a>\r\n</font>\r\n</td>\r\n</tr>\r\n")
    P.raw(f"<tr>\r\n<td colspan=8 align=center>\r\n&nbsp;<br>\r\n<font size=2>\r\n<a href={list_url}><img src=../image/list.gif border=0></a>\r\n")
    if own_q:
        P.raw(f"<a href=rmbbs01.asp?{own_q}> </a>\r\n")
    P.raw("</font>\r\n</td>\r\n</tr>\r\n</table>\r\n<p>\r\n</center>\r\n</body>\r\n</html>\r\n")
    return P.done()

def _bw_fmt(ts, full=False):
    return time.strftime("%Y/%m/%d, %H:%M:%S" if full else "%Y/%m/%d", time.localtime(ts))

def board_http(method, path, query, body, ip):
    """one request below /b/ ; returns (status, bytes).  path = '<c|t|e>/<dir>/<file>'"""
    parts = [p for p in path.split("/") if p]
    if len(parts) < 3 or parts[0] not in BW_ENC:
        return 404, b"not found"
    ch, sect, fname = parts[0], parts[1], parts[2].lower()
    enc, lang = BW_ENC[ch], BW_LANG[ch]
    q = _bw_params(query, body)
    P = _Page(enc, lang)
    try:
        if sect in ("mail_box", "personal"):           # "personal/" = the client's new-mail check after login (same page)
            return 200, _mail_http(P, ch, fname, q, ip)
        if sect == "honor":                             # (10-31) the HUD's unit honor page (SGRender fetches it)
            if fname.startswith("report"):              # (15:01) the last battle report
                return 200, report_page(ch, q, ip)
            if fname.startswith("cmd"):                 # (10-31 17:31) the HUD's commander info (F4)
                return 200, cmd_page(ch, q, ip)
            if fname.startswith("user"):                # (11-01 14:17) another commander's info (public lines)
                return 200, user_page(ch, q, ip)
            return 200, honor_page(ch, q, ip)
        if sect == "poll":                              # vote pages of the original site: not used, an empty list
            return 200, _bw_list_page(P, 1, [], 0, [], False)
        if sect in BOARD_NAMES:
            return 200, _board_page(P, ch, sect, fname, q, ip)
    except Exception as e:
        log(f"   board/mail page error {path}: {e!r}")
        return 500, b"error"
    return 404, b"not found"

def _int(v, d=0):
    try:
        return int(v)
    except Exception:
        return d

def _board_page(P, ch, sect, fname, q, ip):
    B = board_load()
    posts = B[sect]
    bi = BOARD_NAMES.index(sect)
    nat = _int(q.get("nat"), 0)
    visible = [r for r in posts if sect != "nation" or r.get("nat", 0) == nat]
    lang = P.lang
    if fname.startswith("inbbs02"):                     # post
        who, how = bw_auth(ip, q.get("f_name"), _bw_pw(q))
        if not who or (sect == "notice" and not is_gm(who)):
            log(f"   BOARD post denied: sect={sect} ip={ip} f_name={q.get('f_name')!r} online={_bw_all()!r} pw={'yes' if _bw_pw(q) else 'no'} keys={sorted(q)!r}")
            return b"denied"
        now = time.time()
        if now - _BOARD_LAST.get(who, 0) < BOARD_POST_GAP or now - _BOARD_LAST.get(("ip", ip), 0) < BW_IP_GAP:
            log(f"   BOARD too fast: {who!r}")
            return b"too fast"
        if not _bw_quota(("p", who), BW_POSTS_HOUR):
            log(f"   BOARD hourly post limit: {who!r}")
            return b"too many"
        subj = _bw_dec(q.get("f_subject", ""), P.enc).strip()[:BOARD_SUBJ_MAX]
        text = _bw_dec(q.get("f_contents", ""), P.enc).strip()[:BOARD_BODY_MAX]
        if not subj:
            log(f"   BOARD empty subject: {who!r} keys={sorted(q)!r}")
            return b"empty"
        _BOARD_LAST[who] = now; _BOARD_LAST[("ip", ip)] = now
        if sect == "nation":                             # the nation board of the poster's OWN nation (the client sends nat=, forgeable)
            nat = _int(((load_accounts().get(who) or {}).get("commander") or {}).get("nation"), nat)
        nid = max([r["id"] for r in posts] + [0]) + 1
        posts.append({"id": nid, "t": now, "acc": who, "nat": nat, "hits": 0, "subject": subj, "body": text})
        del posts[:-BOARD_MAX]
        board_save(); log(f"   BOARD {sect}: #{nid} by {who!r} ({how}): {subj[:30]!r}")
        return b"OK"
    if fname.startswith(("mdbbs02", "rmbbs02")):        # edit / delete: own posts only (GM: any)
        who, how = bw_auth(ip, q.get("f_name"), _bw_pw(q))
        rec = next((r for r in posts if r["id"] == _int(q.get("sn"))), None)
        if not who or not rec or not (rec.get("acc") == who or is_gm(who)):
            log(f"   BOARD edit/delete denied: sect={sect} ip={ip} f_name={q.get('f_name')!r} online={_bw_online(ip)!r} sn={q.get('sn')!r}")
            return b"denied"
        if fname.startswith("rmbbs02"):
            posts.remove(rec)
        else:
            subj = _bw_dec(q.get("f_subject", ""), P.enc).strip()[:BOARD_SUBJ_MAX]
            if subj:
                rec["subject"] = subj
            rec["body"] = _bw_dec(q.get("f_contents", ""), P.enc).strip()[:BOARD_BODY_MAX]
        board_save(); log(f"   BOARD {sect}: {'deleted' if fname.startswith('rmbbs02') else 'edited'} #{rec['id']} by {who!r}")
        return b"OK"
    if fname.startswith("lsbbs01"):                     # list (+ search t=1 subject / 2 text / 3 author)
        t, sq = _int(q.get("t")), (q.get("q") or "")
        key = _bw_dec(sq, P.enc).strip().lower()
        rows = sorted(visible, key=lambda r: -r["id"])
        if t and key:
            def hit(r):
                if t == 1:
                    return key in _bw_txt(r["subject"], lang).lower()
                if t == 2:
                    return key in _bw_txt(r["body"], lang).lower()
                return key in str(_bw_name(r, lang)).lower()
            rows = [r for r in rows if hit(r)]
        pages = max(1, (len(rows) + BOARD_PAGE - 1) // BOARD_PAGE)
        p = min(max(0, _int(q.get("p"))), pages - 1)
        extra = f"&nat={nat}" if sect == "nation" else ""
        out = [(r["id"], _bw_fmt(r["t"]), _bw_clean(_bw_name(r, lang), P.cjk, True), _bw_clean(_bw_txt(r["subject"], lang), P.cjk, True)[:50],
                f"atbbs01.asp?sn={r['id']}{extra}", r.get("hits", 0)) for r in rows[p * BOARD_PAGE:(p + 1) * BOARD_PAGE]]
        links = []
        qs = f"t={t}&q={_up.quote_from_bytes(sq.encode('latin-1', 'replace'))}" if t and key else "t=0&q="
        if len(qs) > 24:
            qs = "t=0&q="
        lo, hi = max(0, p - 5), min(pages, p + 6)
        if lo > 0:
            links.append(("...", None))
        for i in range(lo, hi):
            links.append((str(i + 1), None if i == p else f"lsbbs01.asp?{qs}&p={i}{extra}"))
        if hi < pages:
            links.append(("...", None))
        return _bw_list_page(P, bi + 1, out, len(rows), links, False)
    # read
    sn = _int(q.get("sn"))
    rec = next((r for r in visible if r["id"] == sn), None)
    if not rec:
        return _bw_list_page(P, bi + 1, [], 0, [], False)
    rec["hits"] = rec.get("hits", 0) + 1
    ids = sorted(r["id"] for r in visible)
    i = ids.index(sn)
    byid = {r["id"]: r for r in visible}
    extra = f"&nat={nat}" if sect == "nation" else ""
    link = lambda k: (f"atbbs01.asp?sn={k}{extra}", _bw_txt(byid[k]["subject"], lang))
    me = {a.lower() for a in _bw_online(ip)} if BOARD_REQUIRE_ONLINE else set()
    mine = bool(rec.get("acc")) and rec["acc"].lower() in me
    name_b = rec["acc"].encode("latin-1", "replace") if mine else str(_bw_name(rec, lang)).encode(P.enc, "replace")
    return _bw_read_page(P, bi + 1, rec["id"], name_b, rec["hits"], _bw_fmt(rec["t"], True), _bw_txt(rec["subject"], lang),
                         _bw_txt(rec["body"], lang), link(ids[i - 1]) if i > 0 else None,
                         link(ids[i + 1]) if i + 1 < len(ids) else None, f"lsbbs01.asp?t=0&q=&p=0",
                         # (user 2026-10-26 20:56 log: DELETE went out with NO sn - the page had no own link because the reader's
                         # web IP differs from his game IP.)  The link only carries the public post number; whether the request may
                         # delete is decided by bw_auth (owner / GM) when it arrives, so every reader of a board post gets it.
                         f"sn={sn}{extra}")

# ---- mail ---------------------------------------------------------------------------------------------------------------
def _mail_acc(ip, q, need_pw_or_tok=False):
    """the mailbox owner of a request: password / IP / name (bw_auth), or - for read and delete, which carry only the
    name - the signed token k= of the link we gave out"""
    raw = q.get("owner") or q.get("f_sender")
    who, how = bw_auth(ip, raw, _bw_pw(q))
    if who or not need_pw_or_tok:
        return who
    n = (raw or "").strip().lower()
    key = next((k for k in load_accounts() if k.lower() == n), None)
    return key if key and _bw_tok_ok(key, _int(q.get("sn")), q.get("k")) else None

def _mail_find(raw, enc):
    """recipient: login account, or the nickname (GBK / Big5 bytes) -> (acc key, account) of a real player"""
    accs = load_accounts()
    n = (raw or "").strip()
    for k, a in accs.items():
        if k.lower() == n.lower() and "commander" in a:
            return k, a
    uni = _bw_dec(n, enc)
    k = nick_account(uni)
    if k and k in accs and "commander" in accs[k]:
        return k, accs[k]
    for k2, a in accs.items():
        if k2.lower() == str(k).lower() and "commander" in a:
            return k2, a
    return None, None

def _mail_http(P, ch, fname, q, ip):
    lang = P.lang
    accs = load_accounts()
    if fname.startswith("inbbs02"):                       # send
        who, how = bw_auth(ip, q.get("f_sender"), _bw_pw(q))
        rk, ra = _mail_find(q.get("f_receiver"), P.enc)
        if not who or not ra:
            log(f"   MAIL send denied: ip={ip} f_sender={q.get('f_sender')!r} online={_bw_all()!r} pw={'yes' if _bw_pw(q) else 'no'}")
            return b"denied"
        if not _bw_quota(("m", who), BW_MAIL_HOUR):
            log(f"   MAIL hourly limit: {who!r}")
            return b"too many"
        if rk != who and sum(1 for m in ra.get("mail", []) if m.get("sender") == who) >= BW_MAIL_PER_SENDER:
            return b"full"
        subj = _bw_dec(q.get("f_subject", ""), P.enc).strip()[:BOARD_SUBJ_MAX] or "(no subject)"
        text = _bw_dec(q.get("f_contents", ""), P.enc).strip()[:BOARD_BODY_MAX]
        mail_add(ra, "player", sender=who, subject={"en": subj}, body={"en": text.split("\n")})
        accs[rk] = ra; save_accounts(accs)
        log(f"   MAIL {who!r} ({how}) -> {rk!r}: {subj[:30]!r}")
        for s in list(ONLINE):                             # tell the receiver at once
            if getattr(s, "acc", None) == rk:
                try:
                    mail_say(s, MAIL_UI[_mail_lang(s)][0].format(n=1), popup=True)
                except Exception:
                    pass
        return b"OK"
    who = _mail_acc(ip, q, need_pw_or_tok=not fname.startswith("lsbbs01"))
    if not who:
        return _bw_list_page(P, 6, [], 0, [], True)
    a = accs.get(who, {})
    box = a.get("mail", [])
    if fname.startswith("rmbbs02"):                        # delete
        n = _int(q.get("sn"))
        keep = [m for m in box if m.get("id") != n]
        if len(keep) != len(box):
            a["mail"] = keep; accs[who] = a; save_accounts(accs)
        return b"OK"
    def sender(m):
        s = m.get("sender")
        return (display_name(s) or s) if s else {"zh-cn": "系统", "zh-tw": "系統", "en": "System"}[lang]
    if fname.startswith("lsbbs01"):                        # list (search: t=1 subject / 2 sender)
        t, key = _int(q.get("t")), _bw_dec(q.get("q") or "", P.enc).strip().lower()
        rows = []
        for m in reversed(box):
            subj = mail_text(m, lang)[0]
            if t and key and key not in (subj if t == 1 else str(sender(m))).lower():
                continue
            rows.append((m["id"], _bw_clean(sender(m), P.cjk, True), "", _bw_clean(subj, P.cjk, True)[:50], f"atbbs01.asp?sn={m['id']}&k={_bw_tok(who, m['id'])}",
                         BW_STATUS[lang] if not m.get("read") else _bw_fmt(m["t"]).replace("20", "", 1)))
        return _bw_list_page(P, 6, rows, len(rows), [], True)
    m = next((m for m in box if m.get("id") == _int(q.get("sn"))), None)   # read
    if not m:
        return _bw_list_page(P, 6, [], 0, [], True)
    if not m.get("read"):
        m["read"] = True; accs[who] = a; save_accounts(accs)
    subj, lines = mail_text(m, lang)
    ids = [x["id"] for x in box]
    i = ids.index(m["id"])
    link = lambda k: (f"atbbs01.asp?sn={k}&k={_bw_tok(who, k)}", mail_text(box[ids.index(k)], lang)[0])
    return _bw_read_page(P, 6, m["id"], str(sender(m)).encode(P.enc, "replace"), 0, _bw_fmt(m["t"], True), subj, "\n".join(lines),
                         link(ids[i - 1]) if i > 0 else None, link(ids[i + 1]) if i + 1 < len(ids) else None,
                         "lsbbs01_t.asp", f"sn={m['id']}&k={_bw_tok(who, m['id'])}", mail_rcpt=str(display_name(who) or who))


# ---- UNIT HONOR PAGE (user 2026-10-31 14:10) -----------------------------------------------------------------------------
# "a page that keeps the highest-star units and the lifetime kills; past a number a special mark and honor".  SGRender's
# HUD fetches  <board base>/honor/list.txt  (base = the board URL patched into the exe) and draws the page.  Plain text in
# the channel's code page, one record per line, tab separated:
#   I <account> <commander honor x100>
#   M <hall id> <name> <chassis> <stars> <lifetime kills> <peak level> <marks,> <1 = unit still owned>      my units
#   T <rank> <commander> <nation> <name> <chassis> <stars> <kills> <marks,>                               server top
#   (14:36) both followed by: <battles> <wins> <best battle kills> <longest survival run> <captures> <defences won>
#   <first seen (unix)> <history "time:star:N;time:medal:code;...">;  marks = "code:times,..." (14:44)
# Who is asking: acc= when that account is online from this IP, else the account online from this IP (like the mail).
HONOR_TOP = 20
HONOR_MINE = 40
HONOR_HIST_SEND = 12

def _honor_disp(chassis, lang):
    try:
        d = DISPLAY.get(chassis, chassis)
        return UN.name_out(str(d), lang) if lang != "en" else str(d)
    except Exception:
        return str(chassis)

def marks_of(r):
    """(14:44) "code:count,..." - how many times each medal was earned."""
    mc = r.get("mcount") or {}
    return ",".join(f"{m}:{int(mc.get(m, 1))}" for m in r.get("marks", []))

def honor_page(ch, q, ip):
    enc, lang = BW_ENC[ch], BW_LANG[ch]
    want = (q.get("acc") or "").strip().lower()
    here = _bw_online(ip) if BOARD_REQUIRE_ONLINE else _bw_all()
    acc = next((a for a in here if a.lower() == want), None)
    if not acc and want:                                   # (16:10) the client names its login account: online is enough
        acc = next((a for a in _bw_all() if a.lower() == want), None)   # (its HTTP may come from another address)
    acc = acc or (here[0] if here else None)
    accs = load_accounts()
    if not BOARD_REQUIRE_ONLINE and want:                  # (tests)
        acc = next((k for k in accs if k.lower() == want), acc)
    rows = []
    def extra(r):
        h = ";".join(f"{int(t)}:{k}:{v}" for t, k, v in (r.get("hist") or [])[-HONOR_HIST_SEND:])
        return [str(int(r.get(k, 0) or 0)) for k in ("bt", "bw", "bk", "sv", "cap", "dw", "t0")] + [h]
    def cell(v):
        return str(v).replace("\t", " ").replace("\n", " ")
    def name_of(r):
        nm = r.get("name") or ""
        try:
            return nm.encode("latin-1").decode(enc)          # wire bytes of the owner's client
        except Exception:
            return nm
    top = []
    for key, a in accs.items():
        if not isinstance(a, dict):
            continue
        c = a.get("commander") or {}
        owned = {str(u.get("hid", u.get("uid"))) for u in a.get("units", [])}
        for hid, r in (c.get("unit_hall") or {}).items():
            if r.get("star", 0) <= 0 and r.get("kills", 0) <= 0:
                continue
            top.append((r.get("star", 0), r.get("kills", 0), key, c.get("nation", 0), r, hid in owned))
    top.sort(key=lambda t: (-t[0], -t[1]))
    if acc and acc in accs:
        c = accs[acc].get("commander") or {}
        rows.append("\t".join(["I", cell(wire_name(acc) if "wire_name" in globals() else acc), str(int(c.get("honor", 0) or 0))]))
        owned = {str(u.get("hid", u.get("uid"))) for u in accs[acc].get("units", [])}
        mine = sorted((c.get("unit_hall") or {}).items(), key=lambda kv: (-kv[1].get("star", 0), -kv[1].get("kills", 0)))
        for hid, r in mine[:HONOR_MINE]:
            rows.append("\t".join(["M", hid, cell(name_of(r) or _honor_disp(r.get("chassis"), lang)), cell(_honor_disp(r.get("chassis"), lang)),
                                   str(r.get("star", 0)), str(r.get("kills", 0)), str(r.get("peak", 0)),
                                   marks_of(r), "1" if hid in owned else "0"] + extra(r)))
    for i, (st, k, key, nat, r, alive) in enumerate(top[:HONOR_TOP]):
        own = wire_name(key) if "wire_name" in globals() else key
        try:
            own = str(own).encode("latin-1").decode(enc)
        except Exception:
            pass
        rows.append("\t".join(["T", str(i + 1), cell(own), str(nat), cell(name_of(r) or _honor_disp(r.get("chassis"), lang)),
                               cell(_honor_disp(r.get("chassis"), lang)), str(st), str(k), marks_of(r)] + extra(r)))
    return ("\n".join(rows) + "\n").encode(enc, "replace")


# ---- BATTLE REPORT for the HUD's result panel (user 2026-10-31 15:01) ----------------------------------------------------
#   R <report id> <age s> <result 1 win / 0 defeat / 2 retreat> <bonuses x100 ,> <province name>
#   U <hall id> <name> <chassis> <stars> <stars before> <kills> <1 alive> <level before> <level> <XP> <1 MVP> <medals code:n,>
#     <XP in the level> <XP the level needs> <peak level>                                                     (15:27)
#   C <commander> <honor before> <honor now> <resources gained ,>                                            (15:27)
#   B <inf|mob|avi|org> <level before> <level> <XP in the level> <XP the level needs> <rank before> <rank>  (15:27/15:45)
def report_page(ch, q, ip):
    enc, lang = BW_ENC[ch], BW_LANG[ch]
    want = (q.get("acc") or "").strip().lower()
    here = _bw_online(ip) if BOARD_REQUIRE_ONLINE else _bw_all()
    acc = next((a for a in here if a.lower() == want), None)
    if not acc and want:                                   # (16:10) the client names its login account: online is enough
        acc = next((a for a in _bw_all() if a.lower() == want), None)   # (its HTTP may come from another address)
    acc = acc or (here[0] if here else None)
    accs = load_accounts()
    if not BOARD_REQUIRE_ONLINE and want:
        acc = next((k for k in accs if k.lower() == want), acc)
    rep = (accs.get(acc) or {}).get("last_report") if acc else None
    if not rep:
        return b"\n"
    def cell(v):
        return str(v).replace("\t", " ").replace("\n", " ")
    try:
        pl = province_label_lang(rep.get("map"), lang) if rep.get("map") else ""
    except Exception:
        pl = ""
    rows = ["\t".join(["R", str(rep.get("id", 0)), str(int(time.time() - rep.get("t", 0))), str(rep.get("res", 0)),
                       ",".join(str(int(round(float(x) * 100))) for x in rep.get("bon") or []), cell(pl)])]
    for u in rep.get("units") or []:
        nm = u.get("name") or ""
        try:
            nm = nm.encode("latin-1").decode(enc)
        except Exception:
            pass
        rows.append("\t".join(["U", cell(u.get("hid")), cell(nm or _honor_disp(u.get("chassis"), lang)), cell(_honor_disp(u.get("chassis"), lang)),
                               str(u.get("star", 0)), str(u.get("star0", 0)), str(u.get("kills", 0)), "1" if u.get("alive") else "0",
                               str(u.get("lv0", 1)), str(u.get("lv", 1)), str(u.get("xp", 0)), "1" if u.get("mvp") else "0",
                               ",".join(f"{k}:{v}" for k, v in (u.get("medals") or {}).items()),
                               str(u.get("uxp", 0)), str(u.get("need", 1)), str(u.get("peak", 0))]))
    c = rep.get("cmd") or {}
    if c:
        nm = str(c.get("name", ""))
        try:
            nm = nm.encode("latin-1").decode(enc)
        except Exception:
            pass
        try:
            _x = _cmd_extra(acc, PG.ensure_commander((accs.get(acc) or {}).setdefault("commander", {})), lang, rep.get("map"))
        except Exception:
            _x = ["", "", "", "0", "0"]
        rows.append("\t".join(["C", cell(nm), str(c.get("honor0", 0)), str(c.get("honor", 0)), ",".join(str(int(x)) for x in rep.get("gain") or [])]
                               + [cell(x) for x in _x]))      # (17:44) + planet nation regiment rank reinc
    for k in ("inf", "mob", "avi", "org"):
        b = (rep.get("br") or {}).get(k)
        if b:
            # (15:45) the rank name of the level before / now (the game's own branch box shows "Rank : 新兵")
            _rs = type("_L", (), {"lang": lang})()
            rows.append("\t".join(["B", k] + [str(int(x)) for x in b[:4]]
                                   + [cell(rank_for(_rs, int(b[0]), short=True)), cell(rank_for(_rs, int(b[1]), short=True)),
                                      str(rank_index(int(b[1])))]))      # (18:04) + rank index (the HUD's insignia)
    return ("\n".join(rows) + "\n").encode(enc, "replace")


def _planet_txt(pid, lang):
    """planet name in the page's language (str)."""
    try:
        if lang in ("zh-tw", "zh-cn") and pid in PLANET_ZH:
            return PLANET_ZH[pid][0 if lang == "zh-tw" else 1]
        for p in PLANETS:
            if p[0] == pid:
                return p[1]
        g = GATE_CLOSED_PLANETS.get(pid)
        if g:
            return {"zh-tw": g[1], "zh-cn": g[2]}.get(lang, g[0])
    except Exception:
        pass
    return ""

def _cmd_extra(acc, cmd, lang, mapid=None):
    """(17:44) planet, nation, regiment and the top rank index (0..20, the HUD's frame tier) of a commander."""
    nid = int(cmd.get("nation", 1) or 1)
    try:
        reg, _r = regiment_of(acc)
    except Exception:
        reg = None
    m = mapid or CAPITALS.get(nid, 600000)
    top = max(int(v.get("level", 1)) for v in (cmd.get("branches") or {"x": {"level": 1}}).values())
    return [_planet_txt((int(m) // 100000) % 1000, lang), nation_name(nid, lang), reg or "", str(rank_index(top)),
            str(int(cmd.get("reincarnations", 0) or 0))]

# ---- COMMANDER INFO (user 10-31 17:14 "the commander info HUD - plan what else it can show", plan confirmed 17:31) ------
# GET /b/<c|t|e>/honor/cmd.txt?acc=  (SGRender draws it over the game's F4 window CUserInfoWnd).  Lines (tab separated):
#   I name title nation regiment superior reinc honor prestige wins losses look president council
#   B inf|mob|avi|org level xp need rank next_rank_level next_rank          (4 lines)
#   A tactics clout education mech points
#   R money ore silicon uranium sulfur
#   U deploy_limit roster_cap units best_star best_unit total_kills battles battles_won
#   N allies(,) provinces
#   L result province honor_gain age_s                                       (last battle, if any)
#   M id text                                                                (commander medals)
def cmd_page(ch, q, ip):
    enc, lang = BW_ENC[ch], BW_LANG[ch]
    want = (q.get("acc") or "").strip().lower()
    here = _bw_online(ip) if BOARD_REQUIRE_ONLINE else _bw_all()
    acc = next((a for a in here if a.lower() == want), None)
    if not acc and want:
        acc = next((a for a in _bw_all() if a.lower() == want), None)
    acc = acc or (here[0] if here else None)
    accs = load_accounts()
    if not BOARD_REQUIRE_ONLINE and want:
        acc = next((k for k in accs if k.lower() == want), acc)
    a = accs.get(acc) if acc else None
    if not a:
        return b"\n"
    return _cmd_rows(acc, a, enc, lang)

# GET /b/<c|t|e>/honor/user.txt?name=  (user 11-01 14:17: another commander's info in the HUD's look).  name = the shown
# name (nickname, client code page) as the game's CUserInfoWnd holds it (+0x80d); players and NPC commanders
# (find_account_by_name).  Only the public lines: I, B (4), N, M - no attributes, resources, units or last battle.
def user_page(ch, q, ip):
    enc, lang = BW_ENC[ch], BW_LANG[ch]
    if BOARD_REQUIRE_ONLINE and not _bw_online(ip):
        return b"\n"
    raw = (q.get("name") or "").strip()
    acc, a = None, None
    try:                                                # an NPC's Chinese name (GBK / Big5 bytes) -> its real name
        if not NP._REV:
            NP._rev_build()
        rb = raw.encode("latin-1")
        en = NP._REV.get(bytes([len(rb)]) + rb)
        if en:
            raw = en[1:].decode("latin-1")
    except Exception:
        pass
    for e2 in (enc, "gbk", "big5", "latin-1"):          # the client's code page (an English channel may still send GBK)
        try:
            name = raw.encode("latin-1").decode(e2)
            acc, a = find_account_by_name(name)
        except Exception:
            acc, a = None, None
        if acc and a:
            break
    if not acc or not a:
        return b"\n"
    out = _cmd_rows(acc, a, enc, lang).decode(enc, "replace").split("\n")
    keep = [r for r in out if r[:2] in ("I\t", "B\t", "N\t", "M\t")]
    if a.get("npc") and keep and keep[0][:2] == "I\t":   # an NPC: its name as this language shows it (单身土拨鼠)
        f = keep[0].split("\t")
        try:
            f[1] = NP.disp(acc, lang)
        except Exception:
            pass
        keep[0] = "\t".join(f)
    return ("\n".join(keep) + "\n").encode(enc, "replace")

def _cmd_rows(acc, a, enc, lang):
    def cell(v):
        return str(v).replace("\t", " ").replace("\n", " ")
    _rs = type("_L", (), {"lang": lang})()
    cmd = PG.ensure_commander(a.setdefault("commander", {}))
    nid = int(cmd.get("nation", 1) or 1)
    br = cmd["branches"]
    top = max(int(v.get("level", 1)) for v in br.values())
    reinc = int(cmd.get("reincarnations", 0) or 0)
    try:
        reg, _r = regiment_of(acc)
    except Exception:
        reg = None
    try:
        pres = 1 if str(politics(nid).get("president", "")).lower() == acc.lower() else 0
        coun = 1 if (not pres and is_council_member(acc, nid)) else 0
    except Exception:
        pres = coun = 0
    try:
        nm = display_name(acc)
    except Exception:
        nm = acc
    rows = ["\t".join(["I", cell(nm), cell(rank_for(_rs, top, reinc)), cell(nation_name(nid, lang)), cell(reg or ""),
                        cell(cmd.get("superior", "") or ""), str(reinc), str(int(cmd.get("honor", 0) or 0)),
                        str(int(pr_of(cmd))), str(int(cmd.get("wins", 0) or 0)), str(int(cmd.get("losses", 0) or 0)),
                        str(max(1, min(int(cmd.get("look", 1) or 1), 11))), str(pres), str(coun)]
                       + [cell(x) for x in _cmd_extra(acc, cmd, lang, a.get("map") or None)][0:1] + [str(rank_index(top))])]
    for k in ("inf", "mob", "avi", "org"):
        v = br.get(k) or {"level": 1, "xp": 0}
        lv = int(v.get("level", 1))
        ri = rank_index(lv)
        nl = next((L for L in range(lv + 1, 400) if rank_index(L) > ri), 0)
        rows.append("\t".join(["B", k, str(lv), str(int(v.get("xp", 0))), str(PG.branch_xp_need(lv)),
                                cell(rank_for(_rs, lv, short=True)), str(nl), cell(rank_for(_rs, nl, short=True) if nl else ""), str(ri)]))
    at = (list(cmd.get("attrs") or [0, 0, 0, 0]) + [0, 0, 0, 0])[:4]
    rows.append("\t".join(["A"] + [str(int(x)) for x in at] + [str(int(cmd.get("points", 0) or 0))]))
    res = (list(a.get("resources") or []) + [0] * 5)[:5]
    rows.append("\t".join(["R"] + [str(int(x)) for x in res]))
    units = a.get("units") or []
    hall = cmd.get("unit_hall") or {}
    best, bname, kills, bt, bw = -1, "", 0, 0, 0
    for r in sorted(hall.values(), key=lambda r: (-int(r.get("star", 0) or 0), -int(r.get("kills", 0) or 0))):
        if best < 0:
            best = int(r.get("star", 0) or 0)
            # (11-01 02:39) the unit's own name (a renamed unit, wire bytes of the owner's code page) or its chassis in the
            # page's language ("Arbalest" -> 弩砲): the default label is the English chassis name
            raw = PG.strip_star_tag(str(r.get("name") or ""))
            eng = str(DISPLAY.get(r.get("chassis"), r.get("chassis") or ""))
            if not raw or raw == eng or raw == str(r.get("chassis") or ""):
                bname = _honor_disp(r.get("chassis"), lang)
            else:
                try:
                    bname = raw.encode("latin-1").decode(enc)
                except Exception:
                    bname = raw
    for r in hall.values():
        kills += int(r.get("kills", 0) or 0)
        bt += int(r.get("bt", 0) or 0)
        bw += int(r.get("bw", 0) or 0)
    try:
        dl = PG.deploy_limit(cmd)
    except Exception:
        dl = 0
    try:
        cap = roster_cap(cmd)
    except Exception:
        cap = 0
    rows.append("\t".join(["U", str(dl), str(cap), str(len(units)), str(max(best, 0)), cell(bname), str(kills), str(bt), str(bw)]))
    try:
        allies = [nation_name(b if a2 == nid else a2, lang) for a2, b in NATION_ALLIES if nid in (a2, b)]
    except Exception:
        allies = []
    try:
        provs = owned_provinces(nid)
    except Exception:
        provs = 0
    rows.append("\t".join(["N", cell(",".join(allies)), str(provs)]))
    rep = a.get("last_report")
    if rep:
        try:
            pl = province_label_lang(rep.get("map"), lang) if rep.get("map") else ""
        except Exception:
            pl = ""
        c = rep.get("cmd") or {}
        rows.append("\t".join(["L", str(int(rep.get("res", 0))), cell(pl), str(int(c.get("honor", 0)) - int(c.get("honor0", 0))),
                                str(int(time.time() - float(rep.get("t", time.time()))))]))
    fix_medal_ids(cmd)
    for mid, txt in (cmd.get("medals") or [])[:40]:
        rows.append("\t".join(["M", str(int(mid)), cell(medal_text(txt, lang))]))
    return ("\n".join(rows) + "\n").encode(enc, "replace")
