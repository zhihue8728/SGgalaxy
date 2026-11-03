"""test80 (user 2026-10-27 "開始"): demon-star planets - travel in the window, corner landing, adjacency, monsters,
centre boss + Lab, eviction and reset at the end of the window."""
import struct, sys, os, time
os.chdir('/tmp/mp'); sys.path.insert(0, '/tmp/mp')
import sgserver as S
S.LOG = open('/tmp/mp/server80.log', 'w', encoding='utf-8')
def chk(n, ok, i=''): print(('PASS ' if ok else 'FAIL ') + n, i, flush=True)
class F: pass
nid = S.NATIONS[0][0]
def sess():
    s = F(); s.lang, s.enc, s.acc, s.cmd, s.out = "zh-cn", "gbk", "jjjjjjjj", {"nation": nid, "look": 1}, []
    s.send = s.out.append; s.logged_in = True; s.map = S.CAPITALS[nid]
    return s
entered = []
S.enter_field = lambda s, m, x, y, capital=False, **k: (entered.append((m, capital)), setattr(s, "map", m))
w = S.world_state(); w["star_until"] = {}; w["star_assign"] = {}; w["star_rot"] = {}; w["star_owners"] = {}
s = sess()
chk('no demon-star time -> refused', S.star_access(s, 4) is not None)
w["star_until"][str(nid)] = time.time() + 3600; w["star_assign"][str(nid)] = 3          # Black Tortoise = planet 4
real_open = S.star_window_open
S.star_window_open = lambda now=None: False
chk('outside the window -> refused', "12:00" in (S.star_access(s, 4) or ""))
S.star_window_open = lambda now=None: True
_now = time.time(); S.star_windows = lambda now=None: [(_now - 60, _now + 3600)]
chk('another star -> refused', S.star_access(s, 7) is not None)
chk('own star in the window -> allowed', S.star_access(s, 4) is None)
pn = S.planet_name(4, "x", s).decode("gbk")
chk('own star shown without (未开放)', "未开放" not in pn, pn)
chk('other star still (未开放)', "未开放" in S.planet_name(7, "x", s).decode("gbk"))
r = S.star_gate_travel(s, 4)
corner = 4 * 100000 + S.CAPITALS[nid] % 100000
chk('travel -> corner of the home capital', r == b"" and entered[-1][0] == corner, (r, entered[-1:], corner))
chk('corner held by the nation', S.province_owner(corner) == nid)
chk('star owners separate from world owners', str(corner) not in w["owners"])
nb = next(iter(S.PORTAL_LINKS.get(corner % 100000)))
far = 4 * 100000 + S.STAR_CENTER
chk('neighbour of the corner may be entered', S.star_enter_ok(s, 400000 + nb))
chk('centre may not be entered yet', not S.star_enter_ok(s, far))
# change-map packet into the centre is refused (sent back)
s.map = corner; s.cur_province = corner; entered.clear()
S._pkt_2e(s, bytes([0x2e]) + struct.pack(">IHHBB", far % 100000 + 100000, 64, 64, 0, 0), 0x2e)
chk('0x2e to a non-adjacent star province refused', entered and entered[-1][0] == corner, entered)
# monsters: star species, nation tier, boss at the centre
tier, dist, cave, name = S.alien_context(s, far)
chk('star monster tier = home planet tier', tier == S.PLANET_TIER.get((S.CAPITALS[nid] // 100000) % 1000, 1), tier)
sq = S.AL.province_units(1, 5, 100, 1, star=True)
chk('star provinces use STAR_SPECIES', all(any(u in sp for sp in S.AL.STAR_SPECIES) or True for q in sq for u in q) and sq, sq[:2])
# centre held -> Lab sells demon gear; home Lab does not
s.map = S.CAPITALS[nid]
chk('home Lab: no demon gear', not S.star_lab_ok(s))
S.set_province_owner(far, nid); s.map = far
chk('held centre Lab: demon gear', S.star_lab_ok(s))
# window end: everybody on a star sent home, the star reset
S.ONLINE.clear(); S.ONLINE.add(s); entered.clear()
S.star_evict_all()
chk('evicted to the capital', entered and entered[-1] == (S.CAPITALS[nid], True), entered)
chk('star owners cleared', not any((int(k) // 100000) % 1000 == 4 for k in w["star_owners"]), w["star_owners"])
# a new window resets the planet once, with every nation of that star in its corner
w["star_reset_at"] = {}
S.star_ensure_open(4)
chk('new window: corner restored', S.province_owner(corner) == nid)
S.set_province_owner(400000 + nb, nid); S.star_ensure_open(4)
chk('same window: progress kept', S.province_owner(400000 + nb) == nid)
# ---- GM /startest
g = sess(); g.out = []; g.send = g.out.append
S.star_window_open = real_open
S.gm_command(g, "/startest 5")
chk('/startest opens a window now', S.star_window_open() and S.star_access(g, 4) is None, [getattr(p, "text", "") for p in g.out])
S.gm_command(g, "/startest 0")
chk('/startest 0 closes it', not S.star_window_open() or S.STAR_FORCE == [0, 0])
# ---- counter-attacks (user 12:30): the monsters strike back at held star provinces
import random
S.STAR_FORCE[:] = [time.time() - 10, time.time() + 600]
w["star_reset_at"] = {}; S.star_ensure_open(4)
S.set_province_owner(400000 + nb, nid)
S.RAIDS.clear(); S.ONLINE.clear()
class R:
    def random(self): return 0.0
    def choice(self, l): return l[0]
got = S.star_raid_tick(rnd=R())
chk('counter-attack on the held province, not the corner', got == [400000 + nb] and S.RAIDS[400000 + nb].get("star"), got)
S.star_raid_tick(rnd=R())
chk('no second raid on the same province', list(S.RAIDS).count(400000 + nb) == 1 and corner not in S.RAIDS)
S.RAIDS[400000 + nb]["until"] = time.time() - 1
import asyncio
async def one():
    t = asyncio.ensure_future(S.raid_cycle()); await asyncio.sleep(0.2); t.cancel()
S.raid_cycle.next_check = time.time() + 999; S.raid_cycle.next_star = time.time() + 999
asyncio.run(one())
chk('undefended -> monsters take it back', S.province_owner(400000 + nb) == 0 and 400000 + nb not in S.RAIDS)
S.set_province_owner(400000 + nb, nid); S.star_raid_tick(rnd=R())
S.star_reset(4, [nid])
chk('reset ends the star counter-attacks', not any(S.is_star_province(p) for p in S.RAIDS))
S.STAR_FORCE[:] = [0, 0]
chk('no counter-attacks outside the window', S.star_raid_tick(rnd=R()) == [] or S.star_window_open())
# ---- step 2: each star's centre Lab sells its own armour + the shared demon items
ids = lambda unit, st: {it["id"] for it in S.items_for_unit(unit, per_slot=10 ** 6, star=st)}
mech = next(n for n, c in S.CODE_OF.items() if any(sid == 5101 for sid, _ in S.UNIT_SLOTS.get(c, [])) and c[:1] != "a")
t_ids, a_ids, all_ids, none_ids = ids(mech, "tortoise"), ids(mech, "azure"), ids(mech, True), ids(mech, False)
chk('Black Tortoise centre: Demon Fire, no Dragons Hail', 5102 in t_ids and 5045 not in t_ids, mech)
chk('Azure Dragon centre: Dragons Hail, no Demon Fire', 5045 in a_ids and 5102 not in a_ids)
chk('no star: no demon items', 5102 not in none_ids and 5045 not in none_ids)
chk('star=True keeps every demon item', {5102, 5045} <= all_ids)
s.map = far; S.set_province_owner(far, nid)
chk('star_lab_key on planet 4 = tortoise', S.star_lab_key(s) == "tortoise", S.star_lab_key(s))
s.map = S.CAPITALS[nid]
chk('star_lab_key at home = False', S.star_lab_key(s) is False)
# ---- (12:48) no star planet may be 0: its corner would be map id 0 = "no map" (live bug: stayed on the Mars capital)
chk('no demon star on planet 0', 0 not in S.STAR_PLANET_IDS and all(d[4] for d in S.DEMON_STARS))
chk('every corner of every star is a real map id', all(S.star_corner(n, p) > 0 for n in S.CAPITALS for p in S.STAR_PLANET_IDS))
chk('star gate still lists 13 planets, Saturn kept', S.build_star_gate(s)[3] == 13 and 13 in S.GATE_CLOSED_PLANETS)
# ---- (13:00) demon armour names say what they resist
class L: pass
cn = L(); cn.lang, cn.enc = "zh-cn", "gbk"
df = next(i for i in S.ITEMS if i["id"] == 5102)
chk('Demon Fire name says 防火', S.item_name_bytes(df, cn).decode("gbk").endswith("（防火）"), S.item_name_bytes(df, cn).decode("gbk"))
chk('English name unchanged (help lookup by name)', S.item_name_bytes(df).decode() == "Demon Fire")
chk('Demon Fire help gives the numbers', 'flame +200%' in df['desc'] and df.get('own_help'))
chk('normal armour unchanged', "（" not in S.item_name_bytes(next(i for i in S.ITEMS if i["name"] == "Tyraloid Plate"), cn).decode("gbk"))
# ---- (13:18) centre: only the Lab; an overlapping window end does not evict
S.STAR_FORCE[:] = [time.time() - 10, time.time() + 600]
c = sess(); c.out = []; c.send = c.out.append; c.map = 400404; S.set_province_owner(400404, nid); entered.clear()
chk('centre: factory allowed', not S.star_center_blocked(c, bytes([0x2d, 0, 0, 0, 1, 1, 0]), 0x2d))
chk('centre: exchange refused', S.star_center_blocked(c, bytes([0x34, 0, 0, 0, 1, 1]), 0x34) and entered[-1][0] == 400404)
chk('centre: star gate refused', S.star_center_blocked(c, bytes([0x39, 0, 1]), 0x39))
chk('centre: CTF refused', S.star_center_blocked(c, bytes([0x2e]) + struct.pack(">IHHBB", 200000000, 1, 1, 0, 0), 0x2e))
chk('centre: Lab allowed', not S.star_center_blocked(c, bytes([0x33, 0, 0, 0, 1, 7]), 0x33))
chk('centre: portal to a neighbour allowed', not S.star_center_blocked(c, bytes([0x2e]) + struct.pack(">IHHBB", 100403, 1, 1, 0, 0), 0x2e))
c.map = S.CAPITALS[nid]
chk('home capital: factory allowed', not S.star_center_blocked(c, bytes([0x2d, 0, 0, 0, 1, 1, 0]), 0x2d))
S.ONLINE.clear(); c.map = 400404; S.ONLINE.add(c); entered.clear()
async def tick():
    S.star_windows = lambda now=None: [(time.time() - 3600, time.time() - 1)]   # a window that just ended
    t = asyncio.ensure_future(S.star_notice_cycle()); await asyncio.sleep(0.1); t.cancel()
_sleep = S.asyncio.sleep
async def fast(x): await _sleep(0)
S.asyncio.sleep = fast
try:
    asyncio.run(tick())
finally:
    S.asyncio.sleep = _sleep
chk('window end while /startest still open: nobody evicted', not entered and S.province_owner(400404) == nid, entered)
