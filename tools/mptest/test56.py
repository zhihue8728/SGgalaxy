"""test56 (user 2026-10-24 23:31): players <-> NPCs in battle - chat orders to the allied NPC platoons (佔點 / 集合 /
打 B3 / 守), NPC reports of enemy artillery / cloaked units / mines with the minimap cell, and the counter platoon."""
import sys, os, time, struct, collections
os.chdir('/tmp/mp'); sys.path.insert(0, '/tmp/mp')
import sgserver as S
S.LOG = open('/tmp/mp/server56.log', 'w', encoding='utf-8')
def chk(n, ok, i=''): print(('PASS ' if ok else 'FAIL ') + n, i, flush=True)
nid = 1
S.npc_ensure_roster(nid)
pid = next(p for p in S.planet_provinces(S.nation_planet(nid)) if p not in S.CAPITALS.values())
g = S.Ghost(pid, nid)
B = S.BF.new_battle(map=pid, t0=g.t0, targets=g.targets, pocs={}, members=set(), owner=g, ghost=g, defender=0,
                    npc_attacker=nid, opened=time.time())
g.battle = B
n = S.npc_of(nid)[3]
S.NPC_RT.pop(n["id"], None)
S._npc_put_squad(g, nid, n, 0, (1000, 1000), "assault")
S.NPC_RT[n["id"]]["B"] = B
B["pocs"].update({1: {"x": 3000, "y": 600, "owner": 0, "strength": 100, "progress": 100, "capturing": False},
                  2: {"x": 600, "y": 3000, "owner": 0, "strength": 100, "progress": 100, "capturing": False}})
class W:
    def is_closing(self): return False
class P:
    def __init__(s):
        s.acc = 'jjjjjjjj'; s.cmd = {'nation': nid}; s.w = W(); s.battle = B; s.map = pid; s.lang = 'zh-cn'; s.enc = 'gbk'
        s.alive_units = {5001, 5002}; s.unit_pos = {5001: (1200, 1200), 5002: (1230, 1200)}; s.put_args = {}
        s.targets = g.targets; s.spectator = False; s.sent = []
    def send(s, d, **k): s.sent.append(d)
p = P()
B["members"] = {p}
chk("minimap cells: A1 top left, E5 bottom right", S.grid_label(p, (10, 10)) == "A1" and S.grid_label(p, (4090, 4090)) == "E5"
    and S.grid_label(p, S.grid_point(p, "B3")) == "B3", (S.grid_label(p, (10, 10)), S.grid_label(p, (4090, 4090))))
chk("cell read from the chat", S._grid_in("大家打 B3！") == "B3" and S._grid_in("attack d4 now") == "D4" and S._grid_in("我在14号省") is None)
now = time.time()
S.npc_step(g, B, now)                          # brain exists
br = B["brains"][nid]
chk("'佔點' -> capture order for the capturer platoon", S.npc_battle_hear(p, "快去佔點") and
    any(o["kind"] == "capture" for o in br.orders.values()), [o["kind"] for o in br.orders.values()])
S._TALK_T.clear(); br.orders.clear()
chk("'集合' -> every platoon closes up on the player", S.npc_battle_hear(p, "大家集合") and
    len(br.orders) >= 1 and all(o["kind"] == "move" for o in br.orders.values()), len(br.orders))
S._TALK_T.clear(); br.orders.clear()
chk("'打 C2' -> engage in C2", S.npc_battle_hear(p, "打 C2") and all(o["kind"] == "engage" and S.grid_label(p, o["point"]) == "C2"
                                                                    for o in br.orders.values()))
S._TALK_T.clear()
chk("ordinary chat is not an order", not S.npc_battle_hear(p, "大家好"))
mv0 = sum(1 for tg in g.targets.values() if tg.get("npc") == n["id"])
sent = []
_og = S.order_gate
S.order_gate = lambda s_, b_, msgs, now_, who="AI": (sent.extend(msgs), _og(s_, b_, msgs, now_, who))[1]
for k in range(3):
    S.npc_step(g, B, now + 1 + k)
c2 = S.grid_point(p, "C2")
moves = [struct.unpack_from(">IHH", m, 1) for m in sent if m[:1] == b"\x1a"]
chk("the platoons move towards C2", moves and sum(1 for _u, x, y in moves if abs(x - c2[0]) + abs(y - c2[1]) < 900) >= len(moves) // 2,
    len(moves))
chk("NPC answers in the ally channel", "收到" in (S.LOG.flush(), open('/tmp/mp/server56.log', encoding='utf-8').read())[1])
# ---- spot: an enemy self-propelled gun next to the NPC units
br.orders.clear()
arty = next(c for c in S.npc_pool() if c.get("arty") and not c.get("air"))
st9 = S.unit_stats9(S.npc_unit(arty["code"], 30))
ex = next(iter(g.targets.values()))["pos"]
g.targets[88001] = {"hp": 900, "max": 900, "npc": 999999, "nation": 2, "pos": (ex[0] + 300, ex[1]), "name": arty["code"],
                    "put": {"st9": st9, "kind": 0}}
S.npc_spot_reports(g, B, [p], now + 10)
od = [o for o in br.orders.values() if o["kind"] == "attack" and o.get("target") == 88001]
chk("enemy artillery spotted -> a fast / line platoon is sent at it", len(od) == 1, [o["kind"] for o in br.orders.values()])
lg = (S.LOG.flush(), open('/tmp/mp/server56.log', encoding='utf-8').read())[1]
chk("... reported with the cell", "自走炮" in lg and S.grid_label(p, (ex[0] + 300, ex[1])) in lg)
# ---- cloaked unit and mines
S.CLOAKED[5002] = {15}
q = P(); q.acc = 'kkkkkkkk'; q.cmd = {'nation': 2}; q.alive_units = {6001}; q.unit_pos = {6001: (ex[0] + 100, ex[1] + 50)}
S.CLOAKED[6001] = {15}
S.note_mine(q, (ex[0] + 150, ex[1] + 80), 2)
S.npc_spot_reports(g, B, [p, q], now + 20)
lg = (S.LOG.flush(), open('/tmp/mp/server56.log', encoding='utf-8').read())[1]
chk("cloaked enemy noticed and reported", "隐形" in lg)
chk("enemy mines reported", "地雷" in lg)
chk("same thing in the same cell is not repeated at once", S.npc_spot_reports(g, B, [p, q], now + 21) is None and
    (S.LOG.flush(), open('/tmp/mp/server56.log', encoding='utf-8').read())[1].count("地雷") == lg.count("地雷"))
