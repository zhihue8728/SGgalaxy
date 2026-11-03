"""test49 (user 2026-10-24 12:46 / 12:48):
- COMBAT RANKING (TAB, 0xFC): header = attacker / defender NATION ids (the client counts the rows of each nation for
  TOTAL ATTACKER / DEFENDER, 004b46a0), NPC commanders of the battle get rows with their kills.
- F6 who-list (0x12 kind 1): row u32 = nation id (FACTION column, 00551ec0), u16 = regiment key, p5 = level."""
import sys, os, struct, time
os.chdir('/tmp/mp'); sys.path.insert(0, '/tmp/mp')
for f in ('npcs.json', 'world.json'):
    if os.path.exists(f): os.remove(f)
import sgserver as S
S.LOG = open('/tmp/mp/server49.log', 'w', encoding='utf-8')
def chk(n, ok, i=''): print(('PASS ' if ok else 'FAIL ') + n, i, flush=True)
S.npc_tick(time.time())
npcs = S.npc_all()

def parse_fc(d):
    att, dfd, n = d[1], d[2], d[3]
    o, rows = 4, []
    for _ in range(n):
        L = d[o]; nm = d[o + 1:o + 1 + L]; o += 1 + L
        fac = d[o]; pts, kills = struct.unpack_from('>HH', d, o + 1); avg, poc, reins = d[o + 5], d[o + 6], d[o + 7]
        o += 8
        rows.append((nm, fac, pts, kills, avg, poc, reins))
    return att, dfd, rows, len(d) - o

class W:
    def is_closing(self): return False
class Pl:
    def __init__(s, acc, nat):
        s.acc = acc; s.cmd = {'nation': nat}; s.w = W(); s.spectator = False; s.battle_stats = {}
        s.alive_units = set(); s.unit_pos = {}; s.sent = []
    def send(s, d): s.sent.append(d)

a_npc = next(n for n in npcs if not S.same_side(n['nation'], 2))
d_npc = next(n for n in npcs if n['nation'] == 2)
p1 = Pl('jjjjjjjj', a_npc['nation']); p2 = Pl('hhhhhhhh', 2)
targets = {60001: {'npc': a_npc['id'], 'nation': a_npc['nation'], 'hp': 100, 'pos': (100, 100), 'level': 10},
           60002: {'npc': d_npc['id'], 'nation': 2, 'hp': 100, 'pos': (900, 900), 'level': 12, 'target': 1033},
           60003: {'npc': None, 'hp': 50, 'level': 5}}
b = {'map': 600003, 'defender': 2, 'members': {p1, p2}, 'targets': targets}
for p in (p1, p2):
    p.battle = b; p.targets = targets
p1.battle_stats = {'kills': {1032: 2}, 'kill_lv': 30}
p2.unit_pos = {1033: (880, 880)}; p2.alive_units = {1033, 1034}

# NPC kills: an alien killed by the attacker NPC's unit, a player unit killed by the defender NPC's unit
p1.last_kill_level = 7
chk("NPC unit kill credited to its commander", S.npc_score_kill(p1, 60001, 7) and not S.npc_score_kill(p1, 1032, 7))
chk("killer of a player unit = NPC unit attacking it", S.npc_killer_of(p2, 1033) == 60002)
S.npc_score_kill(p2, S.npc_killer_of(p2, 1033), 15)

att, dfd, rows, rest = parse_fc(S.build_score_table(p1))
chk("0xFC parses exactly", rest == 0, rest)
chk("header = attacker / defender nation ids", (att, dfd) == (a_npc['nation'], 2), (att, dfd))
names = {r[0].decode('latin-1'): r for r in rows}
chk("players and both NPC commanders listed", {'jjjjjjjj', 'hhhhhhhh', a_npc['name'], d_npc['name']} <= set(names), list(names))
chk("NPC rows carry their kills", names[a_npc['name']][3] == 1 and names[a_npc['name']][2] == 7
    and names[d_npc['name']][3] == 1 and names[d_npc['name']][2] == 15, (names[a_npc['name']], names[d_npc['name']]))
# what the client shows (004b46a0): rows of each header nation
ta = sum(1 for r in rows if r[1] == att); td = sum(1 for r in rows if r[1] == dfd)
chk("client totals: 2 attackers, 2 defenders", (ta, td) == (2, 2), (ta, td))

# who-list rows
r = S.hof_row(1, d_npc['name'], S.npc_cmd(d_npc))
L = r[0]; o = 1 + L
nat, rid, p5, p6, p7, p8 = struct.unpack_from('>IHBBBI', r, o)
lv = max(v['level'] for v in S.npc_cmd(d_npc)['branches'].values())
chk("who-list: u32 = nation id, no regiment", nat == 2 and rid == S.NO_REGIMENT, (nat, rid))
chk("who-list: LEVEL = top branch level, branch index", p5 == min(lv, 255) and 0 <= p7 < 4, (p5, p7, lv))
d = S.build_hof(1)
chk("hall of fame kind 1 still builds", d[:2] == bytes([0x12, 1]) and len(d) > 10)
# Hall of Fame pages 2 / 3 / 4 = Novice / Advanced / Elite planet (players and NPCs of that tier)
for kind in (2, 3, 4):
    d = S.build_hof(kind); n = struct.unpack_from('>H', d, 2)[0]; o = 4; nats = set()
    for _ in range(n):
        L = d[o]; o += 1 + L; nats.add(struct.unpack_from('>I', d, o)[0]); o += 4 + 2 + 3 + 8 + 1 + 4
    tiers = {S.PLANET_TIER.get(S.nation_planet(x), 1) for x in nats}
    chk(f"HOF page {kind}: only tier {kind - 1} commanders, NPCs included", n > 1 and tiers == {kind - 1} and o == len(d),
        (n, sorted(nats)))
