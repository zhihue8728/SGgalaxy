#!/usr/bin/env python3
"""unit checks of server/battlefield.py: every kind of battle, every way it ends (no server needed)"""
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "server"))
import battlefield as BF
ok = True
def chk(n, c, i=""):
    global ok
    ok &= bool(c); print(("PASS " if c else "FAIL ") + n, "" if c else i)
same = lambda a, b: a == b
def V(kind, ev="death", members=(("p1", 1, False),), **kw):
    v = {"kind": kind, "event": ev, "same": same, "members": list(members), "defender": 0, "enemies": 0, "pocs": []}
    v.update(kw); return v
M2 = (("p1", 1, False), ("p2", 2, False), ("spec", 1, True))
# hive cave
chk("hive: hives left -> goes on", BF.judge(V("hive", hives=1)) is None)
r = BF.judge(V("hive", hives=0, enemies=5)); chk("hive: every hive down -> victory (aliens left do not matter)", r and r["won"]["p1"])
r = BF.judge(V("hive", ev="poc", hives=2, pocs=[1]))
chk("hive: every POC held also wins (cave objective)", r and r["tag"] == "pocs_held", r)
# waves
chk("waves: wave cleared, more to come -> goes on", BF.judge(V("field", waves=2)) is None)
# ambush
r = BF.judge(V("ambush", members=M2, blocker=2))
chk("ambush: ambushers gone -> ambushed side wins, blockers lose", r and r["tag"] == "ambush_cleared" and r["won"]["p1"] and not r["won"]["p2"], r)
r = BF.judge(V("ambush", defender=1, blocker=2))
chk("ambush in an own province: attackers gone -> defenders", r and r["tag"] == "attackers_gone" and r["won"]["p1"], r)
chk("ambush: an ambusher alive -> goes on", BF.judge(V("ambush", enemies=1, blocker=2)) is None)
# raid
r = BF.judge(V("raid", defender=1, pocs=[1, 1]))
chk("raid: every raider dead -> repelled", r and r["tag"] == "raid_repelled", r)
r = BF.judge(V("raid", ev="poc", members=M2, defender=1, pocs=[2, 2], npc_side=2, enemies=3))
chk("raid: NPC raiders hold every POC -> they win", r and r["tag"] == "npc_raid_won" and r["won"]["p2"] and not r["won"]["p1"], r)
# province
chk("province: enemies dead but POCs not held -> goes on", BF.judge(V("province", pocs=[0, 2])) is None)
r = BF.judge(V("province", ev="poc", members=M2, defender=2, pocs=[1, 1], enemies=2))
chk("province: attackers hold every POC -> attackers win", r and r["won"]["p1"] and not r["won"]["p2"] and not r["won"]["spec"], r)
chk("province: defenders holding every POC is no win (they win by time)",
    BF.judge(V("province", ev="poc", members=M2, defender=2, pocs=[2, 2])) is None)
r = BF.judge(V("province", ev="leave", members=(("p2", 2, False),), defender=2, pocs=[2, 1]))
chk("province: last attacker left -> defenders win", r and r["tag"] == "attackers_gone" and r["won"]["p2"], r)
chk("province: an attacker still there -> goes on", BF.judge(V("province", ev="leave", members=M2, defender=2, pocs=[2])) is None)
r = BF.judge(V("province", ev="time", members=M2, defender=2, pocs=[1, 2]))
chk("province: TIME UP tie -> defender", r and r["won"]["p2"] and not r["won"]["p1"], r)
r = BF.judge(V("province", ev="time", members=M2, defender=2, pocs=[1, 1, 2]))
chk("province: TIME UP majority -> attacker", r and r["won"]["p1"] and not r["won"]["p2"], r)
# NPC battles (P3)
N = dict(npc_attacker=3, att_alive=4, def_alive=4)
chk("NPC battle: both sides fighting -> goes on", BF.judge(V("npc", ev="tick", members=(), pocs=[0, 2], **N)) is None)
r = BF.judge(V("npc", ev="tick", members=(), pocs=[3, 3], **N))
chk("NPC battle: attackers hold every POC -> attackers win", r and r["tag"] == "npc_battle" and r["att_won"], r)
r = BF.judge(V("npc", ev="poc", members=(("p1", 1, False),), defender=2, pocs=[1, 1], **N))
chk("NPC battle: a third side holds every POC -> attackers lose, the player wins", r and not r["att_won"] and r["won"]["p1"], r)
r = BF.judge(V("npc", ev="tick", members=(), pocs=[2], **dict(N, att_alive=0)))
chk("NPC battle: attackers wiped out, no reserve -> lost", r and not r["att_won"], r)
chk("NPC battle: attackers wiped out but a wave left -> goes on",
    BF.judge(V("npc", ev="tick", members=(), pocs=[2], **dict(N, att_alive=0, att_reserve=True))) is None)
r = BF.judge(V("npc", ev="tick", members=(), **dict(N, def_alive=0)))
chk("NPC battle without POCs: every defender dead -> won", r and r["att_won"], r)
r = BF.judge(V("npc", ev="time", members=(("p2", 2, False),), pocs=[3, 2, 2], **N))
chk("NPC battle: TIME UP, defenders hold the majority -> attackers lose", r and not r["att_won"] and r["won"]["p2"], r)
r = BF.judge(V("npc", ev="time", members=(), **dict(N, att_loss=0.2, def_loss=0.6)))
chk("NPC battle: TIME UP without POCs -> fewer losses wins", r and r["att_won"], r)
# field (no POC)
r = BF.judge(V("field")); chk("field: every enemy dead -> victory", r and r["tag"] == "field_cleared", r)
chk("field: an enemy alive -> goes on", BF.judge(V("field", enemies=1)) is None)
# reinforcements
chk("NPC wiped out cannot reinforce", not BF.may_reinforce(0, "npc"))
chk("NPC with units may reinforce", BF.may_reinforce(3, "npc"))
print("ALL OK" if ok else "SOME FAILED")
