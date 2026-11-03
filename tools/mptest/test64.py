"""test64 (user 2026-10-25 20:16): grid-cell talk with the NPC team mates in battle - 侦察 D2 / E3 有飞机 / A2 有敌人 /
救 C3, NPC reports of enemy aircraft and enemy groups, scout results - and that every line goes to the players of that
side IN that battle (several clients), the orders into the battle's shared brain."""
import sys, os, time, struct, asyncio
os.chdir('/tmp/mp'); sys.path.insert(0, '/tmp/mp')
import sgserver as S
S.LOG = open('/tmp/mp/server64.log', 'w', encoding='utf-8')
def chk(n, ok, i=''): print(('PASS ' if ok else 'FAIL ') + n, i, flush=True)
nid = 1
S.npc_ensure_roster(nid)
pid = next(p for p in S.planet_provinces(S.nation_planet(nid)) if p not in S.CAPITALS.values())
g = S.Ghost(pid, nid)
B = S.BF.new_battle(map=pid, t0=g.t0, targets=g.targets, pocs={}, members=set(), owner=g, ghost=g, defender=0,
                    npc_attacker=nid, opened=time.time())
g.battle = B
for n in S.npc_of(nid)[3:5]:
    S.NPC_RT.pop(n["id"], None)
    S._npc_put_squad(g, nid, n, 0, (1000, 1000), "assault")
    S.NPC_RT[n["id"]]["B"] = B
class W:
    def is_closing(self): return False
class P:
    def __init__(s, acc, nat, units):
        s.acc = acc; s.cmd = {'nation': nat}; s.w = W(); s.battle = B; s.map = pid; s.lang = 'zh-cn'; s.enc = 'gbk'
        s.alive_units = set(units); s.unit_pos = dict(units); s.put_args = {}; s.logged_in = True
        s.targets = g.targets; s.spectator = False; s.sent = []
    def send(s, d, **k): s.sent.append(d.render(s) if hasattr(d, "render") else d)   # like Session.send
p = P('jjjjjjjj', nid, {5001: (1200, 1200)})
p2 = P('llllllll', nid, {5011: (1300, 1200)})          # second client of the same side
q = P('kkkkkkkk', 2, {6001: (3000, 3000)})             # enemy client in the same battle
far = P('mmmmmmmm', nid, {}); far.battle = None        # same nation, NOT in this battle
B["members"] = {p, p2, q}
S.ONLINE.clear() if hasattr(S.ONLINE, 'clear') else None
for o in (p, p2, q, far):
    S.ONLINE.add(o) if hasattr(S.ONLINE, 'add') else S.ONLINE.append(o)
now = time.time()
S.npc_step(g, B, now)
br = B["brains"][nid]
def chat_of(o):
    return [d for d in o.sent if d[:1] == b"*"]
def clear():
    for o in (p, p2, q, far): o.sent.clear()
    S._TALK_T.clear(); br.orders.clear(); S.NPC_CHAT_T.clear()
async def main():
    clear()
    r = S.npc_battle_hear(p, "侦察 D2")
    d2 = S.grid_point(p, "D2")
    mv = [o for o in br.orders.values() if o["kind"] == "move" and S.grid_label(p, o["point"]) == "D2"]
    chk("'侦察 D2' -> one platoon moves to D2, a scout job is kept", r and len(mv) == 1 and len(B.get("_scouts") or []) == 1)
    chk("... the answer reaches BOTH players of the side in this battle", chat_of(p) and chat_of(p2), (len(chat_of(p)), len(chat_of(p2))))
    chk("... not the enemy in the battle, not the same-nation player elsewhere", not chat_of(q) and not chat_of(far))
    # the scouts arrive; an enemy aircraft + 2 ground units in D2
    job = B["_scouts"][0]
    for _t, tg in S._side_platoons(g, nid)[job["key"]]["units"]:
        tg["pos"], tg["mv"] = d2, None
    q.alive_units |= {6002, 6003, 6004}
    q.unit_pos.update({6002: (d2[0] + 50, d2[1]), 6003: (d2[0] - 60, d2[1] + 30), 6004: (d2[0], d2[1] - 40)})
    q.put_args = {6002: {"kind": 2, "st9": (1,) * 9}, 6003: {"kind": 0, "st9": (1,) * 9}, 6004: {"kind": 0, "st9": (1,) * 9}}
    clear()
    S.npc_scout_reports(g, B, time.time())
    txt = b"".join(chat_of(p)).decode("gbk", "replace")
    chk("scout result: enemies counted, aircraft named", "D2" in txt and "3" in txt and "飞机" in txt, txt[-60:])
    chk("... to both players of the side, job done", chat_of(p2) and not B.get("_scouts"))
    clear()
    r = S.npc_battle_hear(p2, "E3有飞机")
    od = [o for o in br.orders.values() if o["kind"] == "engage" and S.grid_label(p, o["point"]) == "E3"]
    has_aa = bool(S._aa_platoons(S._side_platoons(g, nid)))
    chk("'E3有飞机' from the 2nd client -> anti-air platoons to E3 (or: no anti-air, ask)", r and (bool(od) == has_aa),
        (has_aa, len(od)))
    clear()
    r = S.npc_battle_hear(p, "A2有敌人")
    od = [o for o in br.orders.values() if o["kind"] == "engage" and S.grid_label(p, o["point"]) == "A2"]
    chk("'A2有敌人' -> up to 2 nearest platoons engage in A2", r and 1 <= len(od) <= 2, len(od))
    clear()
    r = S.npc_battle_hear(p, "救命 C3")
    od = [o for o in br.orders.values() if o["kind"] == "engage" and S.grid_label(p, o["point"]) == "C3"]
    chk("'救 C3' -> up to 3 platoons to C3, and the off-map call goes on too (False)", r is False and 1 <= len(od) <= 3, len(od))
    clear()
    chk("plain talk is still no order", not S.npc_battle_hear(p, "大家加油"))
    # NPC reports: enemy aircraft and an enemy group near the NPC units
    ex = S._npc_est_pos(next(tg for tg in g.targets.values() if tg.get("npc") is not None), time.time())
    q.unit_pos.update({6002: (ex[0] + 200, ex[1]), 6003: (ex[0] + 100, ex[1] + 20), 6004: (ex[0] + 120, ex[1] - 20)})
    q.alive_units |= {6005, 6006}
    q.unit_pos.update({6005: (ex[0] + 140, ex[1]), 6006: (ex[0] + 90, ex[1] + 40)})
    q.put_args.update({6005: {"kind": 0, "st9": (1,) * 9}, 6006: {"kind": 0, "st9": (1,) * 9}})
    clear()
    S.npc_spot_reports(g, B, [p, p2, q], time.time() + 30)
    lg = (S.LOG.flush(), open('/tmp/mp/server64.log', encoding='utf-8').read())[1]
    chk("enemy aircraft reported with the cell", "sees air" in lg)
    chk("enemy group reported", "sees group" in lg)
    txt = b"".join(chat_of(p)).decode("gbk", "replace")
    chk("... the lines reach the side's players in this battle only", chat_of(p) and chat_of(p2) and not chat_of(q) and not chat_of(far),
        txt[-80:])
asyncio.run(main())
