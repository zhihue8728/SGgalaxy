"""test116 (user 2026-10-31 15:01 "the battle result must show more than XP for the units"): the battle report.
A. battle_report stores per unit: kills, alive / destroyed, level before -> after, XP (kill + bonus), stars before / now,
   medals earned in THIS battle (difference to the snapshot at the battle's start), MVP;
B. /b/c/honor/report.txt sends it (R line + U lines) for the HUD's result panel."""
import sys, os, time
os.chdir('/tmp/mp'); sys.path.insert(0, '/tmp/mp')
import sgserver as S
import progression as PG
S.LOG = open('/tmp/mp/server116.log', 'w', encoding='utf-8')
def chk(n, ok, i=''): print(('PASS ' if ok else 'FAIL ') + n, i, flush=True)
accs = S.load_accounts(); key = next(iter(accs)); a = accs[key]
cmd = PG.ensure_commander(a.setdefault("commander", {}))
u = {"uid": 9101, "chassis": "Hawk", "level": 59, "xp": 0, "kills": 0, "items": [], "label": "Ace"}
v = {"uid": 9102, "chassis": "Imp", "level": 3, "xp": 0, "kills": 0, "items": []}
a["units"] = [u, v]; cmd["unit_hall"] = {}
PG.unit_battle_end(cmd, u, True, True, 16)               # an earlier battle: ace x1
S.save_accounts(accs)
class W:
    def is_closing(self): return False
class P:
    acc = key; w = W(); sim_snap = None; map = 600003
    def send(s, *a, **k): pass
p = P()
p.battle_stats = {"units": [9101, 9102], "kills": {9101: 17, 9102: 1}, "xp_gain": {9101: PG.unit_xp_need(59) + 10, 9102: 40},
                  "xp0": {9101: (59, 0), 9102: (3, 0)}, "rec0": S.battle_rec0(a), "bonuses": [0, 0, 5.0, 0, 10.0, 0]}
p.lost_units = {9102}
PG.add_unit_xp(cmd, u, "avi", PG.unit_xp_need(59) + 10)   # star-up during the battle
S.units_battle_end(p, True)
S.battle_report(p, 1)
rep = S.load_accounts()[key]["last_report"]
ru = {x["hid"]: x for x in rep["units"]}
A = ru[str(u["hid"])]; B = ru[str(v["hid"])]
chk('A1 kills, alive, MVP', A["kills"] == 17 and A["alive"] and A["mvp"] and not B["mvp"] and not B["alive"], A)
chk('A2 star-up seen: stars before 0, now 1; level 59 -> 1', A["star0"] == 0 and A["star"] == 1 and A["lv0"] == 59 and A["lv"] == 1, A)
chk('A3 medals of THIS battle only (ace once more, mvp)', A["medals"].get("ace") == 1 and A["medals"].get("mvp") == 1, A["medals"])
chk('A4 XP gained', A["xp"] == PG.unit_xp_need(59) + 10 and B["xp"] == 40)
S.BOARD_REQUIRE_ONLINE = False
st, body = S.board_http("GET", "c/honor/report.txt", "acc=" + key, b"", "127.0.0.1")
lines = [l.split("\t") for l in body.decode("gbk").split("\n") if l]
R = [l for l in lines if l[0] == "R"]; U = [l for l in lines if l[0] == "U"]
chk('B1 R line: result, bonuses (percent x100 like the result packet)', R and R[0][3] == "1" and R[0][4] == "0,0,500,0,1000,0", R)
chk('B2 U lines: name, stars, kills, alive, levels, XP, MVP, medals', any(l[2] == "Ace" and l[4] == "1" and l[5] == "0" and l[6] == "17"
    and l[7] == "1" and l[8] == "59" and l[9] == "1" and l[11] == "1" and "ace:1" in l[12] for l in U), U)
# C (15:27) the growth data for the left half
S.battle_report(p, 1, [100, 50, 0, 0, 0])
st, body = S.board_http("GET", "c/honor/report.txt", "acc=" + key, b"", "127.0.0.1")
lines = [l.split("\t") for l in body.decode("gbk").split("\n") if l]
C = [l for l in lines if l[0] == "C"]; Bl = [l for l in lines if l[0] == "B"]; U = [l for l in lines if l[0] == "U"]
chk('C1 commander line: honor before / now, resources incl. the reward', C and C[0][4].split(",")[:2] == ["100", "50"], C)
chk('C2 the four branches: level before / now, XP / need', len(Bl) == 4 and all(len(l) == 9 and l[6] and l[7] for l in Bl), Bl)
chk('C3 units: XP in the level, need, peak', all(len(l) >= 16 and int(l[14]) > 0 for l in U), [l[13:] for l in U])
