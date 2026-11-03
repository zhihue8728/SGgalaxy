"""test78 (user 2026-10-26 23:37): presidential election - 7-day term (3 days registration, 4 days voting), division
level 30 to run / 10 to vote, one vote per IP, citizens only, winner announced and gets the gold mark."""
import struct, sys, os, time
os.chdir('/tmp/mp'); sys.path.insert(0, '/tmp/mp')
import sgserver as S
S.LOG = open('/tmp/mp/server78.log', 'w', encoding='utf-8')
def chk(n, ok, i=''): print(('PASS ' if ok else 'FAIL ') + n, i, flush=True)
class W:
    def is_closing(self): return False
class F:
    def __init__(s, acc, nat, ip):
        s.acc, s.cmd, s.peer, s.out, s.logged_in, s.w = acc, {"nation": nat}, (ip, 1), [], True, W()
        s.lang, s.enc = "en", "latin-1"
    def send(s, p):
        s.out.append(p)
def said(s):
    return [getattr(p, "text", "") for p in s.out if hasattr(p, "text")]
def lvl(acc, n):
    accs, a = S.get_account(acc)
    a.setdefault("commander", {}).setdefault("branches", {})["inf"] = {"level": n, "xp": 0}
    accs[acc] = a; S.save_accounts(accs)
N = 1
for acc in ("jjjjjjjj", "hhhhhhhh", "kkkkkkkk"):
    accs, a = S.get_account(acc); a["commander"]["nation"] = N; accs[acc] = a; S.save_accounts(accs)
lvl("jjjjjjjj", 35); lvl("hhhhhhhh", 12); lvl("kkkkkkkk", 5)
p = S.politics(N); p["president"] = ""; p["candidates"] = {}; p["vote_ip"] = {}
p["election_end"] = time.time() + S.ELECTION_SECONDS; S.save_politics()
J, H, K = F("jjjjjjjj", N, "1.1.1.1"), F("hhhhhhhh", N, "2.2.2.2"), F("kkkkkkkk", N, "2.2.2.2")
X = F("hhhhhhhh", N + 1, "9.9.9.9")
def req(s, op, arg=b""):
    S.fhq_request(s, bytes([0x36]) + struct.pack(">IBB", N, 0, op) + arg)
stmt = "for the people".encode()
chk('term is 7 days', S.ELECTION_SECONDS == 7 * 86400 and S.NOMINATION_SECONDS == 3 * 86400)
req(H, 1, struct.pack(">H", len(stmt)) + stmt)
chk('level 12 cannot run', "hhhhhhhh" not in p["candidates"] and any("level 30" in t for t in said(H)), said(H))
req(J, 1, struct.pack(">H", len(stmt)) + stmt)
chk('level 35 registers', "jjjjjjjj" in p["candidates"])
req(H, 6, S._s8("jjjjjjjj"))
chk('no voting during registration', not p["candidates"]["jjjjjjjj"]["votes"] and any("not started" in t for t in said(H)))
req(X, 6, S._s8("jjjjjjjj"))
chk('other faction refused', any("citizens" in t for t in said(X)))
p["election_end"] = time.time() + S.ELECTION_SECONDS - S.NOMINATION_SECONDS - 60      # voting days
chk('voting phase', S.election_voting(p))
req(H, 1, struct.pack(">H", len(stmt)) + stmt)
chk('registration closed in the voting days', any("closed" in t for t in said(H)))
req(H, 6, S._s8("jjjjjjjj"))
chk('level 12 votes', p["candidates"]["jjjjjjjj"]["votes"] == ["hhhhhhhh"])
req(K, 6, S._s8("jjjjjjjj"))
chk('level 5 cannot vote', len(p["candidates"]["jjjjjjjj"]["votes"]) == 1)
lvl("kkkkkkkk", 20)
req(K, 6, S._s8("jjjjjjjj"))
chk('same IP as another voter refused', len(p["candidates"]["jjjjjjjj"]["votes"]) == 1 and any("network" in t for t in said(K)))
req(H, 6, S._s8("jjjjjjjj"))
chk('the same voter may vote again (no double count)', p["candidates"]["jjjjjjjj"]["votes"] == ["hhhhhhhh"])
S.ONLINE.clear(); S.ONLINE.update({J, H})
p["election_end"] = time.time() - 1
S.resolve_election(N)
chk('winner = president, new 7-day term', p["president"] == "jjjjjjjj" and p["election_end"] > time.time() + 6 * 86400 and not p["candidates"])
chk('citizens told the result', any("new president" in t for t in said(H)), said(H)[-2:])
chk('winner gets the gold mark', S.hero_mark("jjjjjjjj") == 1)
# ---- Vote window packet layout = client parser 005e7770 (every byte consumed, statement s16)
def parse_vote(pk):
    assert pk[0] == 0x37 and pk[1] == 0
    o = 6; sub = pk[o]; o += 1; mins = struct.unpack_from(">I", pk, o)[0]; o += 4
    def rec(o):
        out = []
        for kind in ("s8", "s8", "u8", "u8", "s8", "u8", "u32", "u8", "u8", "u8", "u8", "u16", "u16", "s16"):
            if kind == "s8": n = pk[o]; out.append(pk[o + 1:o + 1 + n]); o += 1 + n
            elif kind == "u8": out.append(pk[o]); o += 1
            elif kind == "u16": out.append(struct.unpack_from(">H", pk, o)[0]); o += 2
            elif kind == "u32": out.append(struct.unpack_from(">I", pk, o)[0]); o += 4
            else: n = struct.unpack_from(">H", pk, o)[0]; out.append(pk[o + 2:o + 2 + n]); o += 2 + n
        return out, o
    recs = []
    if sub == 0:
        r, o = rec(o); recs.append(r)
    else:
        n = pk[o]; o += 1
        for _ in range(n):
            r, o = rec(o); recs.append(r)
    return sub, mins, recs, o == len(pk)
p["election_end"] = time.time() + S.ELECTION_SECONDS              # fresh term: nomination days
p["candidates"] = {}
req(J, 1, struct.pack(">H", len(stmt)) + stmt)
pk = S.build_vote_info(N, J)
sub0, m0, r0, ok0 = parse_vote(pk[0]); sub1, m1, r1, ok1 = parse_vote(pk[1])
chk('vote packets parse to the last byte (s16 statement)', ok0 and ok1, (ok0, ok1))
chk('nomination days -> sub 1 with minutes until the vote', sub1 == 1 and abs(m1 - 3 * 24 * 60) <= 2, (sub1, m1))
chk('Overlord record = president with his statement', r0[0][0] == b"jjjjjjjj", r0[0][:3])
chk('candidate record: name, level, attributes, statement', r1[0][0] == b"jjjjjjjj" and r1[0][5] >= 35 and r1[0][13] == stmt, r1[0])
S.VOTE_DEBUG = True
sd, md, rd, okd = parse_vote(S.build_vote_info(N, J)[0])
S.VOTE_DEBUG = False
chk('debug markers parse', okd and rd[0][0] == b"NAME_A" and rd[0][6] == 444444)
p["election_end"] = time.time() + 60 * 30                          # voting days, no candidate
p["candidates"] = {}
pk = S.build_vote_info(N, J)
chk('voting days without candidates -> only sub 0', len(pk) == 1 and parse_vote(pk[0])[0] == 0 and parse_vote(pk[0])[1] in (29, 30))
req(H, 3, S._s8("jjjjjjjj"))
req(H, 4, S._s8("jjjjjjjj"))
chk('Overlord support once per day', list(p.get("pres_support", {})) == ["hhhhhhhh"] and not p.get("pres_oppose") and any("once per day" in t for t in said(H)))
# ---- Chinese statement (user 23:55) + portrait number
p["election_end"] = time.time() + S.ELECTION_SECONDS; p["candidates"] = {}
J.enc, J.lang = "gbk", "zh-cn"
zh = "为人民服务，统一银河".encode("gbk")
req(J, 1, struct.pack(">H", len(zh)) + zh)
T = F("hhhhhhhh", N, "3.3.3.3"); T.enc, T.lang = "cp950", "zh-tw"
_s, _m, rr, okr = parse_vote(S.build_vote_info(N, T)[1])
chk('Chinese statement: GBK in, Big5 out', okr and rr[0][13].decode("cp950") == "為人民服務，統一銀河" or rr[0][13].decode("cp950") == "为人民服务，统一银河".encode("cp950", "replace").decode("cp950"), rr[0][13])
_s, _m, rr, okr = parse_vote(S.build_vote_info(N, J)[1])
chk('same code page: exact text back', rr[0][13] == zh, rr[0][13])
chk('old raw-byte statements are repaired', S.stmt_text(zh.decode("latin-1")) == "为人民服务，统一银河")
look = S.get_account("jjjjjjjj")[1]["commander"].get("look", 1)
chk('1st u8 = portrait number (Hero-%02d)', rr[0][2] == max(1, min(int(look or 1), 11)), (rr[0][2], look))
# ---- recall (user 2026-10-27): same-day opposition >= 5 and >= 2 x support removes the Overlord
p["president"] = "jjjjjjjj"; p["candidates"] = {}
today = time.strftime("%Y-%m-%d")
p["pres_support"] = {"a1": today, "a2": today, "a3": "2000-01-01"}
p["pres_oppose"] = {"b%d" % i: today for i in range(4)}
chk('4 oppose: no recall', not S.recall_check(N, p) and p["president"] == "jjjjjjjj")
p["pres_oppose"]["b4"] = today
chk('5 oppose vs 2 support today -> recall', S.recall_check(N, p) and p["president"] == "" and not p["pres_oppose"]
    and p["election_end"] > time.time() + 6.9 * 86400 and not S.election_voting(p))
chk('recall announced, mark cleared', any("recalled" in t for t in said(H)) and S.hero_mark("jjjjjjjj") != 1)
p["president"] = "jjjjjjjj"
p["pres_support"] = {"a%d" % i: today for i in range(3)}
p["pres_oppose"] = {"b%d" % i: today for i in range(5)}
chk('5 oppose vs 3 support: no recall', not S.recall_check(N, p) and p["president"] == "jjjjjjjj")
# ---- STATEMENT -> DONE (op 7) saves a candidate's statement (user 2026-10-27 00:06)
p["president"] = "jjjjjjjj"; p["election_end"] = time.time() + S.ELECTION_SECONDS
p["candidates"] = {"jjjjjjjj": {"statement": "old", "support": ["x"], "oppose": [], "votes": []},
                   "hhhhhhhh": {"statement": "", "support": [], "oppose": [], "votes": []}}
J.enc = "gbk"; t7 = "你好".encode("gbk")
req(J, 7, struct.pack(">H", len(t7)) + t7)
chk('op 7: candidate + Overlord statement saved', p["candidates"]["jjjjjjjj"]["statement"] == "你好" and p["statement"] == "你好")
H.enc = "latin-1"; t7 = b"hello"
req(H, 7, struct.pack(">H", len(t7)) + t7)
chk('op 7: plain candidate statement saved', p["candidates"]["hhhhhhhh"]["statement"] == "hello" and p["statement"] == "你好")
req(J, 1, struct.pack(">H", 3) + b"new")
chk('op 1 again keeps support', p["candidates"]["jjjjjjjj"]["support"] == ["x"] and p["candidates"]["jjjjjjjj"]["statement"] == "new")
