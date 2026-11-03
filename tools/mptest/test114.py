"""test114 (user 2026-10-31 14:07 / 14:10): unit STARS and the unit HONOR record.
A. a unit reaching UNIT_MAX_LEVEL rises a star: level 1, XP 0, peak kept; at STAR_MAX it stays at the max level;
B. the peak level counts for tech level / unit quality (equipment and Lab chassis kept), and climbing again gives
   division XP again;
C. each star +3 % HP and damage; the unit's name shows "*N " (roster record, battle PUT); a rename strips it;
D. the honor record: lifetime kills and stars per unit (hall id kept through a Lab upgrade's new uid), marks at
   100 / 500 / 1000 / 3000 kills and five stars, each adding commander honor once; star / mark news for the player;
E. the HUD page /b/c/honor/list.txt lists my units (I / M lines) and the server top (T lines)."""
import sys, os, time
os.chdir('/tmp/mp'); sys.path.insert(0, '/tmp/mp')
import sgserver as S
import progression as PG
S.LOG = open('/tmp/mp/server114.log', 'w', encoding='utf-8')
def chk(n, ok, i=''): print(('PASS ' if ok else 'FAIL ') + n, i, flush=True)
cmd = PG.ensure_commander({"attrs": [20, 20, 20, 0], "tier": 2})
cmd["branches"]["inf"]["level"] = 80
u = {"uid": 5001, "chassis": "Phantom", "level": 59, "xp": 0, "kills": 0, "items": []}
ev = PG.add_unit_xp(cmd, u, "inf", PG.unit_xp_need(59) + 50)
chk('A1 level 60 -> star 1, back to level 1, XP 0', u["star"] == 1 and u["level"] == 1 and u["xp"] == 0 and u["peak"] == 60, u)
chk('A2 star news for the player', any(n[0] == "star" and n[2] == 1 for n in cmd.get("star_news", [])), cmd.get("star_news"))
v = dict(u, star=PG.STAR_MAX, level=59, xp=0)
PG.add_unit_xp(cmd, v, "inf", PG.unit_xp_need(59) + 5)
chk('A3 at the top star it stays at level 60', v["level"] == 60 and v["star"] == PG.STAR_MAX)
chk('B1 tech level / unit quality from the peak (equipment and chassis kept)',
    PG.tech_level(cmd, u) == 60 + 10 and PG.unit_quality(cmd, u) == 60 + 10, (PG.tech_level(cmd, u), PG.unit_quality(cmd, u)))
bx0 = cmd["branches"]["inf"]["xp"] + sum(PG.branch_xp_need(l) for l in range(1, cmd["branches"]["inf"]["level"]))
PG.add_unit_xp(cmd, u, "inf", PG.unit_xp_need(1) + PG.unit_xp_need(2))
bx1 = cmd["branches"]["inf"]["xp"] + sum(PG.branch_xp_need(l) for l in range(1, cmd["branches"]["inf"]["level"]))
chk('B2 climbing again gives division XP again', u["level"] == 3 and bx1 > bx0, (u["level"], bx0, bx1))
u0 = dict(u, star=0)
hp0, hp1 = S.hp_battle({}, u0)[1], S.hp_battle({}, u)[1]
d0, d1 = S.unit_stats9(dict(u0, items=[])), S.unit_stats9(dict(u, items=[]))
chk('C1 +3 % HP per star', abs(hp1 / hp0 - 1.03) < 0.01, (hp0, hp1))
chk('C2 +3 % damage per star (when it has a weapon)', d0[3] == 0 or abs(d1[3] / d0[3] - 1.03) < 0.02, (d0[3], d1[3]))
chk('C3 name shows *N (roster / battle)', S.roster_rec(u)[2].startswith("*1 ") and S.battle_unit_name(u).startswith("*1 "),
    (S.roster_rec(u)[2], S.battle_unit_name(u)))
chk('C4 a rename strips the shown tag', PG.strip_star_tag("*1 Ace") == "Ace" and PG.strip_star_tag("Ace*1") == "Ace*1")
# D: honor record
cmd2 = PG.ensure_commander({"attrs": [0, 0, 0, 0]})
w = {"uid": 7001, "chassis": "Hawk", "level": 10, "xp": 0, "kills": 98, "items": [], "label": "Ace"}
h0 = cmd2.get("honor", 0)
PG.award_kill(cmd2, w, "avi", 1, 0.0); PG.award_kill(cmd2, w, "avi", 1, 0.0)
r = cmd2["unit_hall"][str(w["hid"])]
chk('D1 lifetime kills on the record, bronze mark at 100 kills, honor once', r["kills"] == 100 and "bronze" in r["marks"]
    and cmd2["honor"] - h0 == 1000, (r, cmd2["honor"]))
PG.award_kill(cmd2, w, "avi", 1, 0.0)
chk('D2 the mark is given once', r["marks"].count("bronze") == 1 and cmd2["honor"] - h0 == 1000)
w["uid"] = 7002                                    # a Lab upgrade gives the unit a new uid
PG.award_kill(cmd2, w, "avi", 1, 0.0)
chk('D3 the record follows the unit through a new uid', len(cmd2["unit_hall"]) == 1 and r["kills"] == 102, list(cmd2["unit_hall"]))
w["star"] = PG.STAR_MAX
PG.hall_note(cmd2, w)
chk('D4 five stars: a legend mark', "fivestar" in r["marks"] and r["star"] == PG.STAR_MAX)
# E: page
accs = S.load_accounts()
key = next(iter(accs))
a = accs[key]
a["commander"] = cmd2
a["units"] = [w]
S.save_accounts(accs)
S.BOARD_REQUIRE_ONLINE = False
st, body = S.board_http("GET", "c/honor/list.txt", "acc=" + key, b"", "127.0.0.1")
txt = body.decode("gbk")
lines = [l.split("\t") for l in txt.strip().split("\n") if l]
chk('E1 the page answers', st == 200 and lines, txt[:200])
me = [l for l in lines if l[0] == "M"]
top = [l for l in lines if l[0] == "T"]
chk('E2 my unit with stars, kills, marks, still owned', me and me[0][4] == "5" and me[0][5] == "102" and "bronze:1" in me[0][7] and me[0][8] == "1", me[:1])
chk('E3 in the server top', any(l[6] == "5" and l[7] == "102" for l in top), top[:2])
