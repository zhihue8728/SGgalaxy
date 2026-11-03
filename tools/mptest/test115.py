"""test115 (user 2026-10-31 14:36 / 14:44): unit battle records and medals.
A. unit_battle_end: battles, wins, best battle kills, survival run (reset by a death), captures, defences won;
B. milestone medals once (veteran 30 / 100 battles, three stars); battle medals judged at EVERY settlement, at most once
   per battle and counted: one against a thousand (15 kills), best of the battle (most kills of his units, 3+), phoenix
   (alive although half his units died), conqueror (won and took the province), guardian (won a defence);
C. history lines; the page sends "code:times" and the stats + history after the old fields;
D. end of a battle (results_field.units_battle_end): every unit that fought gets its battle, MVP = his best unit."""
import sys, os, time
os.chdir('/tmp/mp'); sys.path.insert(0, '/tmp/mp')
import sgserver as S
import progression as PG
S.LOG = open('/tmp/mp/server115.log', 'w', encoding='utf-8')
def chk(n, ok, i=''): print(('PASS ' if ok else 'FAIL ') + n, i, flush=True)
cmd = PG.ensure_commander({"attrs": [0, 0, 0, 0]})
u = {"uid": 8001, "chassis": "Hawk", "level": 10, "xp": 0, "kills": 0, "items": [], "label": "Falcon"}
PG.unit_battle_end(cmd, u, True, True, 16, mvp=True)
r = cmd["unit_hall"][str(u["hid"])]
chk('A1 battle, win, best battle kills', r["bt"] == 1 and r["bw"] == 1 and r["bk"] == 16, r)
chk('B1 15 kills and the best of his units: ace + mvp, once each in this battle', r["mcount"].get("ace") == 1 and r["mcount"].get("mvp") == 1)
PG.unit_battle_end(cmd, u, True, True, 20, mvp=True)
chk('B2 the next settlement gives them again: counted x2', r["mcount"]["ace"] == 2 and r["mcount"]["mvp"] == 2 and r["marks"].count("ace") == 1)
PG.unit_battle_end(cmd, u, True, True, 2, mvp=True)
chk('B3 mvp needs 3 kills, ace 15', r["mcount"]["mvp"] == 2 and r["mcount"]["ace"] == 2)
PG.unit_battle_end(cmd, u, False, True, 0, heavy_loss=True)
PG.unit_battle_end(cmd, u, False, False, 0, heavy_loss=True)
chk('B4 phoenix: alive although half his units died (not when it died itself)', r["mcount"].get("survivor") == 1)
chk('A2 a death ends the survival run (best kept)', u["rec"]["cs"] == 0 and r["sv"] == 4, r["sv"])
for i in range(3):
    PG.unit_battle_end(cmd, u, True, True, 0, captured=True)
PG.unit_battle_end(cmd, u, True, True, 0, defended=True)
PG.unit_battle_end(cmd, u, False, True, 0, defended=True)
chk('B5 conqueror x3, guardian x1 (a lost defence gives nothing)', r["mcount"].get("conqueror") == 3 and r["mcount"].get("guardian") == 1, r["mcount"])
for i in range(20):
    PG.unit_battle_end(cmd, u, False, True, 0)
chk('B6 veteran once at 30 battles', "vet30" in r["marks"] and r["mcount"]["vet30"] == 1, r["bt"])
for i in range(30):
    PG.unit_battle_end(cmd, u, False, True, 0)
chk('B7 milestones are not given again', r["mcount"]["vet30"] == 1)
h0 = cmd["honor"]
for i in range(50):
    PG.unit_battle_end(cmd, u, False, True, 0)
chk('B8 a hundred battles: once, +30 honor', r["mcount"].get("vet100") == 1 and cmd["honor"] - h0 == 3000, cmd["honor"] - h0)
u["star"] = 3
PG.hall_note(cmd, u, star_up=True)
chk('B9 three stars', "star3" in r["marks"] and "fivestar" not in r["marks"])
hist = r.get("hist") or []
chk('C1 history: medals and the star-up', any(k == "medal" and v == "star3" for _t, k, v in hist) and any(k == "star" and v == 3 for _t, k, v in hist), hist[-4:])
news = cmd.get("star_news") or []
chk('C2 medal news with the count', any(n[0] == "mark" and n[2] == "ace" and n[5] == 2 for n in news))
accs = S.load_accounts(); key = next(iter(accs)); a = accs[key]
a["commander"] = cmd; a["units"] = [u]; S.save_accounts(accs)
S.BOARD_REQUIRE_ONLINE = False
st, body = S.board_http("GET", "c/honor/list.txt", "acc=" + key, b"", "127.0.0.1")
m = [l.split("\t") for l in body.decode("gbk").split("\n") if l.startswith("M\t")]
chk('C3 page: "code:times", stats and history', m and "ace:2" in m[0][7] and "conqueror:3" in m[0][7] and m[0][9] == str(r["bt"])
    and m[0][11] == "20" and ":medal:" in m[0][16], m[:1])
# D: end of battle
class W:
    def is_closing(self): return False
class P:
    acc = key; w = W(); sim_snap = None
    def send(s, *a, **k): pass
v = {"uid": 8002, "chassis": "Hawk", "level": 5, "xp": 0, "kills": 0, "items": []}
a = S.load_accounts()[key]; a["units"] = [u, v]; accs = S.load_accounts(); accs[key] = a; S.save_accounts(accs)
bt_before = r["bt"]
p = P()
p.battle_stats = {"units": [8001, 8002], "kills": {8001: 2, 8002: 5}}
p.lost_units = {8001}
S.units_battle_end(p, True)
c2 = S.load_accounts()[key]["commander"]["unit_hall"]
chk('D1 end of battle: both units get their battle', c2[str(u["hid"])]["bt"] == bt_before + 1 and c2["8002"]["bt"] == 1)
chk('D2 MVP = his unit with the most kills; phoenix = the survivor of a battle that cost half his units',
    c2["8002"]["mcount"].get("mvp") == 1 and c2["8002"]["mcount"].get("survivor") == 1 and c2[str(u["hid"])]["mcount"].get("mvp") == 2)
