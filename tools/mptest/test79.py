"""test79 (user 2026-10-27 00:26): WAR tab = national power / 40000, strategic map title = current planet."""
import struct, sys, os
os.chdir('/tmp/mp'); sys.path.insert(0, '/tmp/mp')
import sgserver as S
S.LOG = open('/tmp/mp/server79.log', 'w', encoding='utf-8')
def chk(n, ok, i=''): print(('PASS ' if ok else 'FAIL ') + n, i, flush=True)
class F: pass
s = F(); s.lang, s.enc, s.acc, s.cmd = "zh-cn", "gbk", "jjjjjjjj", {"nation": 1}
chk('POWER_FULL 40000', S.POWER_FULL == 40000)
w = S.world_state(); w.setdefault("power", {})["1"] = 12345
nid = S.NATIONS[0][0]; w["power"][str(nid)] = 12345
pl = S.nation_planet(nid)
t = S.map_title(s, pl)
chk('title = planet name only (zh-cn, 地球)', t[1:].decode("gbk") == "地球" and len(t) == t[0] + 1, t[1:].decode("gbk"))
pk = S.build_war_tally(s, pl, struct.pack(">H", 0))
o = 2 + 6 + 2
o += 1 + pk[o]
n = pk[o]; o += 1
recs = [struct.unpack_from(">IHHH", pk, o + 10 * i) for i in range(n)]
chk('tally +0x150 = national power', any(r[0] == nid and r[1] == 12345 for r in recs), recs)
chk('tally parses to the end', o + 10 * n + 2 == len(pk))
d = S.build_nations(neutral=True, s=s)
chk('0x0F carries power / 40000', struct.pack(">HH", 12345, 40000) in d)
# ---- name line (user 2026-10-27 00:46): rank badge = military rank, stars = reincarnations
accs, a = S.get_account("jjjjjjjj")
a["commander"]["reincarnations"] = 3
a["commander"].setdefault("branches", {})["inf"] = {"level": 50, "xp": 0}
accs["jjjjjjjj"] = a; S.save_accounts(accs)
pk = S.build_hero(7, "jjjjjjjj", 1, 2, 0, 1, 1, 100, S.hero_mark("jjjjjjjj"), S.hero_rank("jjjjjjjj"), S.hero_title("jjjjjjjj"))
o = 3; o += 1 + pk[o]; tl = pk[o]; title = pk[o + 1:o + 1 + tl]; o += 1 + tl
chk('title = copper tier + 3 stars (GBK)', title[0] == 1 and title[1:].decode("gbk") == "★★★", title)
chk('0x20 parses to the end', o + 4 + 4 + 6 + 4 == len(pk), (o, len(pk)))
chk('rank badge = PRESTIGE', pk[-1] == min(S.pr_of(S.get_account('jjjjjjjj')[1]['commander']), 30), pk[-1])
class V: pass
tw, en = V(), V(); tw.enc, en.enc = "cp950", "latin-1"
chk('title Big5 for a Traditional viewer', S.hero_title("jjjjjjjj", tw)[1:].decode("cp950") == "★★★")
chk('title GBK stars for an English viewer (F43)', S.hero_title("jjjjjjjj", en)[1:].decode("gbk") == "★★★")
def stars(n):
    accs, a = S.get_account("jjjjjjjj"); a["commander"]["reincarnations"] = n; accs["jjjjjjjj"] = a; S.save_accounts(accs)
    t = S.hero_title("jjjjjjjj", en); return (t[0], (len(t) - 1) // 2) if t else (0, 0)
chk('copper / silver / gold', [stars(n) for n in (0, 1, 5, 6, 10, 11, 15, 20)] == [(0, 0), (1, 1), (1, 5), (2, 1), (2, 5), (3, 1), (3, 5), (3, 5)])
# ---- /powerall (2026-10-27): every nation's power line
class G:
    pass
g = G(); g.acc, g.lang, g.enc, g.cmd, g.out = "jjjjjjjj", "zh-cn", "gbk", {"nation": nid}, []
g.send = g.out.append
S.gm_command(g, "/powerall")
lines = [getattr(p, "text", "") for p in g.out if hasattr(p, "text")]
chk('/powerall lists every nation + next settlement', len(lines) >= len(S.NATIONS) + 1 and "12345" in " ".join(lines), lines[:2])
# ---- demon star (2026-10-27 option A + notices)
import time as _t
w = S.world_state(); w.setdefault("star_until", {})[str(nid)] = _t.time() + 5 * 3600; w["power"][str(nid)] = 214
chk('WAR bar full during demon-star time', S.war_power(nid) == S.POWER_FULL)
pk = S.build_war_tally(s, pl, struct.pack(">H", 0))
chk('tally sends 40000 during demon-star time', struct.pack(">IH", nid, 40000) in pk)
txt = S.star_status_text(nid)
chk('status text (open now / opens at)', txt and ("OPEN until" in txt or "opens at" in txt or "no demon-star window" in txt), txt)
o2 = F(); o2.acc, o2.lang, o2.enc, o2.cmd, o2.logged_in, o2.out = "kkkkkkkk", "zh-cn", "gbk", {"nation": nid}, True, []
class WW:
    def is_closing(self): return False
o2.w = WW(); o2.send = o2.out.append
S.ONLINE.clear(); S.ONLINE.add(o2)
S.star_announce(nid)
said = [getattr(p, "text", "") for p in o2.out if hasattr(p, "text")]
chk('full notice to the nation', any("National power is FULL" in t for t in said), said)
import i18n as _I
_full = next(t for t in said if "National power is FULL" in t)
chk('notices are translated', "国力已满" in _I.translate(_full, "zh-cn") and "魔星现在开放" in _I.translate(
    "Your faction has demon-star time (4h05m left). The demon star is OPEN until 13:00 - type /star to enter.", "zh-cn"),
    _I.translate(_full, "zh-cn"))
w["star_until"][str(nid)] = 0
chk('WAR bar back to the real power after it', S.war_power(nid) == 214)
# ---- closed planets in the Dimensional Matrix (2026-10-27 10:59)
pk = S.build_star_gate(s)
chk('star gate lists 13 planets (9 solar + 4 demon stars)', pk[3] == 13, pk[3])
chk('closed planet named (未开放)', "玄武魔星（未开放）".encode("gbk") in pk and "冥王星（未开放）".encode("gbk") in pk)
r = S.star_gate_travel(s, 8)
chk('travel to a closed planet refused in Chinese', "尚未开放".encode("gbk") in r, r)
# ---- star rotation (user 11:05: nations take turns on the four stars)
w = S.world_state(); w["star_until"] = {}; w["star_assign"] = {}; w["star_rot"] = {}
n1, n2 = S.NATIONS[0][0], S.NATIONS[1][0]
seq = []
for _ in range(5):
    w["power"][str(n1)] = S.POWER_FULL - 1
    S.add_nation_power(n1, 5)
    seq.append(S.nation_star(n1))
chk('one nation rotates through the four stars', seq[:4] == [ (seq[0] + k) % 4 for k in range(4)] and seq[4] == seq[0], seq)
w["power"][str(n2)] = S.POWER_FULL - 1
w["star_rot"][str(n2)] = S.nation_star(n1)          # its rotation would pick n1's star ...
S.add_nation_power(n2, 5)
chk('a star held by another nation is skipped', S.nation_star(n2) != S.nation_star(n1), (S.nation_star(n1), S.nation_star(n2)))
chk('map title on planet 4 = 魔星 玄武', S.map_title(s, 4)[1:].decode("gbk") == "魔星 玄武", S.map_title(s, 4)[1:].decode("gbk"))
# ---- New-commander FRIEND ID (user 11:35): 0x57 before the field -> 0x55 [found][u32 nation]
fr = F(); fr.acc, fr.lang, fr.enc, fr.cmd, fr.out = "x", "zh-cn", "gbk", {}, []; fr.send = fr.out.append; fr.field_sent = False
_ac, _a = S.get_account("jjjjjjjj"); _a["commander"]["nation"] = S.NATIONS[0][0]; _ac["jjjjjjjj"] = _a; S.save_accounts(_ac)
S.handle_player_search(fr, bytes([0x57]) + S._s8("jjjjjjjj"))
pk55 = fr.out[-1]
nat = S.get_account("jjjjjjjj")[1]["commander"]["nation"]
chk('friend found -> 0x55 1 + nation', pk55[:2] == bytes([0x55, 1]) and struct.unpack(">I", pk55[2:6])[0] == nat, pk55)
S.handle_player_search(fr, bytes([0x57]) + S._s8("nobody_here"))
chk('unknown friend -> 0x55 0', fr.out[-1] == bytes([0x55, 0]), fr.out[-1])
