"""test81 (user 2026-10-27 18:59): original POC rulesets (All or Nothing / Standard / Standard Enhanced / Victory),
Max Power Rating, BATTLE tab text."""
import sys, os, time, collections
os.chdir('/tmp/mp'); sys.path.insert(0, '/tmp/mp')
import sgserver as S
BF = S.BF
S.LOG = open('/tmp/mp/server81.log', 'w', encoding='utf-8')
def chk(n, ok, i=''): print(('PASS ' if ok else 'FAIL ') + n, i, flush=True)
same = lambda a, b: a == b
def view(rule, ev, pocs, dfd=1, vp=None, elapsed=0):
    return {"kind": "province", "event": ev, "same": same, "members": [("A", 2, False), ("D", 1, False)],
            "defender": dfd, "enemies": 3, "pocs": pocs, "rule": rule, "vp": vp, "elapsed": elapsed}
W = lambda r: (r or {}).get("won")
# All or Nothing
chk('AoN: attackers take all -> win at once', W(BF.judge(view("all_or_nothing", "poc", [2, 2, 2]))) == {"A": True, "D": False})
chk('AoN: time, attackers 2 of 3 -> defenders win', W(BF.judge(view("all_or_nothing", "time", [2, 2, 1]))) == {"A": False, "D": True})
chk('Standard: time, attackers 2 of 3 -> attackers win', W(BF.judge(view("standard", "time", [2, 2, 1]))) == {"A": True, "D": False})
chk('Standard: time, 2 of 4 tie -> defenders', W(BF.judge(view("standard", "time", [2, 2, 1, 1]))) == {"A": False, "D": True})
chk('Enhanced: no POC before 5 min -> goes on', BF.judge(view("standard_enhanced", "poc", [1, 1, 1], elapsed=200)) is None)
chk('Enhanced: no POC after 5 min -> attackers lose', W(BF.judge(view("standard_enhanced", "poc", [1, 1, 1], elapsed=301))) == {"A": False, "D": True})
chk('Enhanced: one POC after 5 min -> goes on', BF.judge(view("standard_enhanced", "poc", [2, 1, 1], elapsed=400)) is None)
chk('Victory: points left -> goes on', BF.judge(view("victory", "poc", [1, 2], vp={"att": 300, "def": 10})) is None)
chk('Victory: defenders at 0 -> attackers win', W(BF.judge(view("victory", "poc", [1, 2], vp={"att": 300, "def": 0}))) == {"A": True, "D": False})
chk('Victory: time -> more points wins', W(BF.judge(view("victory", "time", [1, 1], vp={"att": 500, "def": 400}))) == {"A": True, "D": False})
chk('Victory: time tie -> defenders', W(BF.judge(view("victory", "time", [2, 2], vp={"att": 400, "def": 400}))) == {"A": False, "D": True})
chk('alien province (defender 0): AoN time -> players lose', W(BF.judge(view("all_or_nothing", "time", [2, 0, 0], dfd=0))) == {"A": False, "D": False})
# rule per province
nid = S.NATIONS[0][0]
novice = [p for p in S.planet_provinces(6) if p not in S.CAPITALS.values()]
adv = [p for p in S.planet_provinces(2) if p not in S.CAPITALS.values()]
chk('novice planet: Standard', all(S.poc_rule(p) == "standard" for p in novice))
c = collections.Counter(S.poc_rule(p) for p in adv)
chk('advanced planet: all four rulesets used', set(c) == set(BF.RULES), dict(c))
chk('rule fixed per province', all(S.poc_rule(p) == S.poc_rule(p) for p in adv))
chk('All or Nothing provinces have 3 POCs', all(S.poc_count(p) == 3 for p in adv if S.poc_rule(p) == "all_or_nothing"))
chk('capital / cave: no rule', S.poc_rule(S.CAPITALS[nid]) is None and S.poc_rule(adv[0] + 10000) is None)
chk('max PR by tier', S.province_max_pr(novice[0]) == 40 and S.province_max_pr(adv[0]) == 100)
# BATTLE tab
t = S.battle_info_text(adv[0], "zh-cn")
chk('BATTLE tab: ruleset name + max PR', S.BF.rule_name(S.poc_rule(adv[0]), "zh-cn") in t and "每方最高战力总和：100" in t, t)
# Victory points step
class O: pass
def sess(acc, nat, units):
    o = O(); o.acc, o.cmd, o.alive_units, o.spectator = acc, {"nation": nat}, set(units), False
    o.w = type("W", (), {"is_closing": lambda self: False})(); o.out = []; o.send = o.out.append; o.lang = "en"
    return o
a1, d1 = sess("jjjjjjjj", 2, [1, 2, 3]), sess("llllllll", 1, [7, 8])
b = {"map": adv[0], "defender": 1, "rule": "victory", "vp": {"att": 800.0, "def": 800.0}, "t0": time.monotonic(),
     "pocs": {1: {"owner": 1}, 2: {"owner": 1}}, "targets": {}, "members": {a1, d1}}
S.victory_points_step(b, [a1, d1])
a1.alive_units = {1}                                 # two attacker units lost
S.victory_points_step(b, [a1, d1])
chk('Victory: lost units + POC minority cost points', b["vp"]["att"] < 800 - 2 * BF.VP_UNIT_LOSS + 1 and b["vp"]["def"] > b["vp"]["att"], b["vp"])
x = sess("kkkkkkkk", 2, [5]); S.victory_points_step(b, [a1, d1, x])
chk('Victory: a joining player adds points', b["vp"]["att"] > 800 - 2 * BF.VP_UNIT_LOSS - 5, b["vp"])
# Max Power Rating: side sum
B = {"members": {a1, x}, "defender": 1}
chk('side_pr counts the side only (at least 1 each)', S.side_pr(B, 2) >= 2 and S.side_pr(B, 1) == 0)
