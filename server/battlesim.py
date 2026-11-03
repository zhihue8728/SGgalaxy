"""Server-side battle simulation (user 2026-10-22 21:29: "全部NPC都保持真实战斗" - every NPC battle is a REAL battle, also
while no player is on the map, so the units' positions and HP are right the moment a player enters).

While players are on the map their clients simulate the battle (lock-step) and the server only relays / estimates.  While
NO player is there the server moves and fights every server-owned unit itself, once per second, with this module:
  * movement on the map's 32-px walk grid (server/walk_grids.json from tools/gen_walk_grids.py): straight when the line is
    free, else down a cached BFS distance field toward the goal cell;
  * target choice like the AIs: nearest enemy inside the aggro radius, at most FOCUS units on one enemy; aliens go home
    when pulled beyond the leash; NPC units without an enemy in reach walk to the nearest enemy POC (capturers stand on
    it -> the server's poc_loop captures it) or, with no POC to take, to the nearest enemy anywhere;
  * damage = the client formula (passed in), weapon range st9[4] px, cooldown st9[5] / 100 s.
Pure logic over the server's target dicts; the server passes a Ctx with its rules and callbacks."""
import base64, math, collections

CELL = 32
FIELD_CACHE = 64            # distance fields kept per map
FIELDS_PER_SECOND = 8       # new distance fields ALL simulated battles may compute per second (CPU guard; the server
                            # resets Grid.spent once per cycle)


def dist(a, b):
    return math.hypot(a[0] - b[0], a[1] - b[1])


FIELDS_PER_STEP = 2         # ... and one battle per step (a step never blocks the server for long)


class Grid:
    spent = 0                   # fields computed in the current cycle (all maps)
    step_spent = 0              # fields computed in the current battle step

    def __init__(self, w, h, bits):
        self.w, self.h, self.bits = w, h, bits
        self.fields = collections.OrderedDict()
        # one byte per cell (+ a blocked border) for a fast BFS; index = (y + 1) * (w + 2) + x + 1
        W = w + 2
        self.W = W
        wk = bytearray(W * (h + 2))
        for y in range(h):
            for x in range(w):
                i = y * w + x
                if bits[i >> 3] >> (i & 7) & 1:
                    wk[(y + 1) * W + x + 1] = 1
        self.wk = wk

    @classmethod
    def from_entry(cls, e):
        return cls(int(e[0]), int(e[1]), base64.b64decode(e[2]))

    def ok(self, cx, cy):
        if not (0 <= cx < self.w and 0 <= cy < self.h):
            return False
        i = cy * self.w + cx
        return bool(self.bits[i >> 3] >> (i & 7) & 1)

    def cell(self, p):
        return int(p[0]) // CELL, int(p[1]) // CELL

    def centre(self, c):
        return c[0] * CELL + CELL // 2, c[1] * CELL + CELL // 2

    def snap(self, p, rmax=16):
        """p itself when walkable, else the centre of the nearest walkable cell (None if none near)."""
        cx, cy = self.cell(p)
        if self.ok(cx, cy):
            return (float(p[0]), float(p[1]))
        for r in range(1, rmax + 1):
            best = None
            for dx in range(-r, r + 1):
                for dy in (-r, r) if abs(dx) != r else range(-r, r + 1):
                    if self.ok(cx + dx, cy + dy):
                        c = self.centre((cx + dx, cy + dy))
                        d = dist(c, p)
                        if best is None or d < best[0]:
                            best = (d, c)
            if best:
                return (float(best[1][0]), float(best[1][1]))
        return None

    def line_free(self, a, b):
        n = int(dist(a, b) // 12) + 1
        for k in range(n + 1):
            f = k / n
            if not self.ok(int(a[0] + (b[0] - a[0]) * f) // CELL, int(a[1] + (b[1] - a[1]) * f) // CELL):
                return False
        return True

    def field(self, goal):
        f = self.fields.get(goal)
        if f is not None:
            self.fields.move_to_end(goal)
            return f
        if Grid.spent >= FIELDS_PER_SECOND or Grid.step_spent >= FIELDS_PER_STEP:
            return None
        Grid.spent += 1
        Grid.step_spent += 1
        W, wk = self.W, self.wk
        f = [-1] * len(wk)
        g = (goal[1] + 1) * W + goal[0] + 1
        f[g] = 0
        q = collections.deque([g])
        orth = (1, -1, W, -W)
        diag = ((1 + W, 1, W), (1 - W, 1, -W), (-1 + W, -1, W), (-1 - W, -1, -W))
        pop, push = q.popleft, q.append
        while q:
            i = pop()
            d = f[i] + 1
            for o in orth:
                j = i + o
                if wk[j] and f[j] < 0:
                    f[j] = d
                    push(j)
            for o, a1, a2 in diag:
                j = i + o
                if wk[j] and f[j] < 0 and wk[i + a1] and wk[i + a2]:
                    f[j] = d
                    push(j)
        self.fields[goal] = f
        while len(self.fields) > FIELD_CACHE:
            self.fields.popitem(last=False)
        return f

    def next_point(self, pos, goal, coarse=False):
        """the next way point from pos toward goal (pixels), None = no way known (yet)."""
        g = self.cell(goal)
        if coarse:
            c2 = (g[0] & ~1, g[1] & ~1)
            if self.ok(*c2):
                g = c2
        if not self.ok(*g):
            s = self.snap(goal)
            if s is None:
                return None
            g = self.cell(s)
        f = self.field(g)
        if f is None:
            return None
        cx, cy = self.cell(pos)
        W = self.W
        cur = f[(cy + 1) * W + cx + 1] if self.ok(cx, cy) else -1
        best = None
        for dx in (-1, 0, 1):
            for dy in (-1, 0, 1):
                nx, ny = cx + dx, cy + dy
                if (dx or dy) and self.ok(nx, ny):
                    v = f[(ny + 1) * W + nx + 1]
                    if v >= 0 and (best is None or v < best[0]):
                        best = (v, (nx, ny))
        if best is None or (cur >= 0 and best[0] >= cur):
            return None if cur != 0 else goal
        return self.centre(best[1])


    # ---- WAY POINTS for live battles (user 2026-10-24 22:48: NPC path finding) ------------------------------------
    # The clients find the path of every NPC move themselves; long moves across a map with water / cliffs made units
    # stick at obstacles, and the server estimated them on the straight line.  path() gives the server a corridor:
    # A* on a 2 x 2 coarse grid (64 px, a coarse cell is open when 2 of its 4 cells are), smoothed with line_free, so
    # the NPC units get short legs the client walks easily and the server knows where they really go.
    def coarse(self):
        c = getattr(self, "_coarse", None)
        if c is None:
            cw, ch = (self.w + 1) // 2, (self.h + 1) // 2
            c = bytearray(cw * ch)
            for y in range(ch):
                for x in range(cw):
                    k = sum(1 for dx in (0, 1) for dy in (0, 1) if self.ok(2 * x + dx, 2 * y + dy))
                    c[y * cw + x] = 1 if k >= 2 else 0
            self._coarse, self._cw, self._ch = c, cw, ch
            c = self._coarse
        return c

    def path(self, a, b, max_nodes=4000):
        """way points (pixels) from a to b, b last; [b] when the line is free; None when no way was found."""
        import heapq
        if self.line_free(a, b):
            return [b]
        c = self.coarse()
        cw, ch = self._cw, self._ch
        C = CELL * 2
        def open_(x, y):
            return 0 <= x < cw and 0 <= y < ch and c[y * cw + x]
        def near_open(p):
            x, y = int(p[0]) // C, int(p[1]) // C
            if open_(x, y):
                return (x, y)
            for r in (1, 2, 3):
                for dx in range(-r, r + 1):
                    for dy in range(-r, r + 1):
                        if open_(x + dx, y + dy):
                            return (x + dx, y + dy)
            return None
        s, g = near_open(a), near_open(b)
        if s is None or g is None:
            return None
        if s == g:
            return [b]
        h = lambda q: max(abs(q[0] - g[0]), abs(q[1] - g[1])) + 0.414 * min(abs(q[0] - g[0]), abs(q[1] - g[1]))
        best = {s: 0.0}
        prev = {}
        heap = [(h(s), 0.0, s)]
        n = 0
        while heap:
            _f, d, q = heapq.heappop(heap)
            if q == g:
                break
            if d > best.get(q, 1e18):
                continue
            n += 1
            if n > max_nodes:
                return None
            for dx in (-1, 0, 1):
                for dy in (-1, 0, 1):
                    if not (dx or dy):
                        continue
                    nx, ny = q[0] + dx, q[1] + dy
                    if not open_(nx, ny) or (dx and dy and not (open_(q[0] + dx, q[1]) and open_(q[0], q[1] + dy))):
                        continue
                    nd = d + (1.414 if dx and dy else 1.0)
                    if nd < best.get((nx, ny), 1e18):
                        best[(nx, ny)] = nd
                        prev[(nx, ny)] = q
                        heapq.heappush(heap, (nd + h((nx, ny)), nd, (nx, ny)))
        if g not in prev:
            return None
        cells = [g]
        while cells[-1] != s:
            cells.append(prev[cells[-1]])
        cells.reverse()
        pts = [(x * C + C // 2, y * C + C // 2) for x, y in cells[1:-1]] + [tuple(b)]
        # smoothing: from the current point keep only the farthest way point in a free straight line
        out, cur, i = [], tuple(a), 0
        while i < len(pts):
            j = i
            while j + 1 < len(pts) and self.line_free(cur, pts[j + 1]):
                j += 1
            q = pts[j]
            if j < len(pts) - 1:
                q = self.snap(q, 2) or q
            out.append((float(q[0]), float(q[1])))
            cur, i = q, j + 1
        return out


class Ctx:
    """what the server tells the simulation (rules + callbacks)."""
    grid = None
    now = 0.0
    aggro = 300.0
    leash = 600.0
    focus = 3
    poc_radius = 48
    hunt_from = 0.0
    brain = False                 # NPC sides decided by battle_ai (the same brain as in live battles)
    tier = 1
    side_of = staticmethod(lambda tg: 0)
    same_side = staticmethod(lambda a, b: a == b)
    damage = staticmethod(lambda dmg, armor, row, col: max(1, int(dmg - armor)))
    on_death = staticmethod(lambda tid, tg: None)


def _is_air(tg):
    return (tg.get("put") or {}).get("kind") == 2

def _can_hit(tg, o):
    """the attacker has a weapon for this kind of target: air damage vs aircraft, ground damage vs everything else"""
    return _weapon(tg, _is_air(o))[0] > 0


def _weapon(tg, air=False):
    """(damage, range px, cooldown s, damage class) against a ground (or air) target; damage 0 = cannot hit it."""
    st9 = (tg.get("put") or {}).get("st9") or [0] * 9
    if air:
        return st9[6], max(40, st9[7]), max(0.2, st9[8] / 100.0), st9[2] // 100
    return st9[3], max(40, st9[4]), max(0.2, st9[5] / 100.0), st9[2] // 100


def _brain_orders(units, side, pocs, ctx):
    """battle_ai for the NPC sides of a simulated battle: attack orders become the units' combat target here, move
    orders their goal (returned).  Stateless per step (the worker has no memory), no reaction limits (2 s steps)."""
    import battle_ai as BA
    U = {}
    for tid, tg in units:
        st9 = list((tg.get("put") or {}).get("st9") or ()) + [0] * 9
        npc = tg.get("npc") is not None
        role = "support" if tg.get("urole") == "support" else BA.unit_role("", st9, (), 500)
        U[tid] = BA.U(tid, side[tid], tg["pos"], tg["hp"], tg.get("max") or tg["hp"], False, st9[3], st9[6], st9[4],
                      st9[7], max(st9[5], st9[8], 20) / 100.0, (tg.get("put") or {}).get("spd") or 10, role,
                      squad=("n", tg.get("npc"), tg.get("plt", 0)) if npc else ("a", tg.get("squad")), ai=npc, home=tg.get("home"),
                      mode=tg.get("mode", "assault"), poc=tg.get("poc"), gate=tg.get("gate"),
                      capt=tg.get("role") == "capturer")
    br = BA.Brain(tier=ctx.tier, seed=int(ctx.now))
    br.p.update(react=(0.0, 0.0), apm=9999, mistake=br.p["mistake"] / 2)
    P = {k: {"x": p["x"], "y": p["y"], "owner": p["owner"]} for k, p in pocs.items()}
    goals, byid = {}, dict(units)
    for kind, uid, arg in br.decide(U, P, ctx.same_side, ctx.now):
        tg = byid.get(uid)
        if tg is None:
            continue
        if kind == "skill":
            continue                                  # (support skills are not simulated here)
        if kind == "attack":
            tg["state"], tg["target"] = "combat", arg
        else:
            if tg.get("state") == "combat":
                tg["state"], tg["target"] = "idle", None
            goals[uid] = arg
    return goals


def move(tg, goal, budget, grid, stop=0.0, coarse=False):
    """walk tg toward goal by up to budget px (stopping `stop` px before it).  True = moved."""
    pos = tg["pos"]
    moved = False
    for _ in range(12):
        d = dist(pos, goal)
        if d <= stop + 1 or budget <= 0.5:
            break
        if grid is None or grid.line_free(pos, goal):
            wp = goal
        else:
            wp = grid.next_point(pos, goal, coarse)
            if wp is None:
                break
        dd = dist(pos, wp)
        if wp is goal:
            dd = max(0.0, dd - stop)
        if dd < 0.5:
            break
        k = min(dd, budget)
        pos = (pos[0] + (wp[0] - pos[0]) / dist(pos, wp) * k, pos[1] + (wp[1] - pos[1]) / dist(pos, wp) * k)
        budget -= k
        moved = True
    tg["pos"] = (pos[0], pos[1])
    tg["x"], tg["y"] = int(pos[0]), int(pos[1])
    tg["mv"] = None
    return moved


def step(targets, pocs, ctx, dt=1.0):
    """one simulation step for every server-owned unit of one battle."""
    Grid.step_spent = 0
    units = [(tid, tg) for tid, tg in targets.items()
             if tg.get("hp", 0) > 0 and tg.get("pos") and not tg.get("hive")
             and ((tg.get("put") or {}).get("abil", 2) or tg.get("urole") == "support")]
    by = dict(units)
    side = {tid: ctx.side_of(tg) for tid, tg in units}
    brain_goal = {}
    if ctx.brain:
        try:
            brain_goal = _brain_orders(units, side, pocs, ctx)
        except Exception:
            brain_goal = {}
    busy = collections.Counter(tg.get("target") for _t, tg in units if tg.get("state") == "combat")
    dead = []
    for tid, tg in units:
        if tg["hp"] <= 0:
            continue
        me = side[tid]
        npc = tg.get("npc") is not None
        dmg, rng, cd, col = _weapon(tg)              # every simulated unit is a ground unit
        if tg.get("urole") == "support":
            dmg = 0                                  # NPC support units never attack (2026-10-23 14:01)
        spd = max(5.0, float((tg.get("put") or {}).get("spd") or tg.get("spd") or 10)) * 2.0
        tg["cd"] = tg.get("cd", 0.0) - dt          # may go below 0: a long step (dt > cooldown) fires several shots
        home = tg.get("home") or tg["pos"]
        tgt = tg.get("target") if tg.get("state") == "combat" else None
        if tgt is not None and (tgt not in by or by[tgt]["hp"] <= 0):
            tgt = None
        if tgt is not None and not npc and not tg.get("hunter") and dist(tg["pos"], home) > ctx.leash:
            tgt = None                                               # alien pulled too far: back home
            tg["state"], tg["target"] = "return", None
        if tgt is None and tg.get("state") != "return" and (dmg > 0 or _weapon(tg, True)[0] > 0) and tid not in brain_goal:
            R = ctx.aggro * (0.6 if tg.get("role") == "capturer" else 1.0) * (1.2 if npc else 1.0)
            best = None
            for oid, o in units:
                if o["hp"] <= 0 or ctx.same_side(me, side[oid]) or busy[oid] >= ctx.focus or not _can_hit(tg, o):
                    continue
                d = dist(tg["pos"], o["pos"])
                if d <= max(R, rng + 20) and (best is None or d < best[0]):
                    best = (d, oid)
            if best:
                tgt = best[1]
                busy[tgt] += 1
        if tgt is not None and not _can_hit(tg, by[tgt]):
            tgt = None                                   # (a brain order on a target its weapons cannot reach)
            tg["state"], tg["target"] = "idle", None
        if tgt is not None:
            tg["state"], tg["target"] = "combat", tgt
            o = by[tgt]
            dmg, rng, cd, col = _weapon(tg, _is_air(o))  # (user 2026-10-23 15:11: tanks do not shoot aircraft)
            d = dist(tg["pos"], o["pos"])
            if d <= rng + 16:
                while tg["cd"] <= 0 and dmg > 0 and o["hp"] > 0:
                    o["hp"] -= ctx.damage(dmg, o.get("armor", 0), o.get("arow", 0), col)
                    o["last_hitter"] = tid
                    tg["cd"] += cd
                    if o["hp"] <= 0:
                        dead.append(tgt)
                        busy[tgt] = 0
                tg["cd"] = max(tg["cd"], -cd)
            else:
                tg["cd"] = max(tg["cd"], 0.0)
                move(tg, o["pos"], spd * dt, ctx.grid, stop=rng * 0.8, coarse=True)
            continue
        tg["cd"] = max(tg["cd"], 0.0)
        if tg.get("state") == "combat":
            tg["state"], tg["target"] = "idle", None
        goal, poc_id = None, None
        if npc and tid in brain_goal:
            goal = brain_goal[tid]
            for k_, p_ in pocs.items():                  # standing on a POC: a capturer takes it
                if dist(goal, (p_["x"], p_["y"])) < 40 and not ctx.same_side(me, p_["owner"]):
                    poc_id = k_
        elif npc:
            enemy = {k: p for k, p in pocs.items() if not ctx.same_side(me, p["owner"])}
            # SEARCH (user 2026-10-23): fighters hunt the nearest enemy (holders: near their post), capturers take the POC
            _foes = [o["pos"] for oid, o in units if o["hp"] > 0 and not ctx.same_side(me, side[oid]) and _can_hit(tg, o)] \
                if tg.get("role") != "capturer" else []          # only enemies its weapons reach (no tank vs aircraft)
            _near = min(_foes, key=lambda q: dist(tg["pos"], q)) if _foes else None
            if _near is not None and (tg.get("mode") == "assault" or dist(_near, home) <= ctx.leash * 2):
                goal = _near
            elif tg.get("mode") == "assault" and enemy:
                poc_id = min(enemy, key=lambda k: dist(tg["pos"], (enemy[k]["x"], enemy[k]["y"])))
            elif tg.get("mode") == "hold" and tg.get("poc") in enemy:
                poc_id = tg["poc"]
            if goal is not None:
                pass
            elif poc_id is not None:
                off = tg.get("off") or (0, 0)
                goal = (enemy[poc_id]["x"] + off[0], enemy[poc_id]["y"] + off[1])
            elif tg.get("mode") == "hold":
                goal = home
            else:
                foes = [o["pos"] for oid, o in units if o["hp"] > 0 and not ctx.same_side(me, side[oid]) and _can_hit(tg, o)]
                goal = min(foes, key=lambda q: dist(tg["pos"], q)) if foes else None
        else:
            if tg.get("hunter") and ctx.now >= ctx.hunt_from and tg.get("state") != "return":
                foes = [o["pos"] for oid, o in units if o["hp"] > 0 and not ctx.same_side(me, side[oid])]
                goal = min(foes, key=lambda q: dist(tg["pos"], q)) if foes else home
            else:
                goal = home
                if tg.get("state") == "return" and dist(tg["pos"], home) < 40:
                    tg["state"] = "idle"
        if goal is not None:
            move(tg, goal, spd * dt, ctx.grid, stop=0.0 if poc_id is not None else 8.0)
        tg["on_poc"] = poc_id if (poc_id is not None and tg.get("role") == "capturer"
                                  and abs(tg["pos"][0] - pocs[poc_id]["x"]) <= ctx.poc_radius
                                  and abs(tg["pos"][1] - pocs[poc_id]["y"]) <= ctx.poc_radius) else None
    for tid in dead:
        tg = targets.get(tid)
        if tg is not None and tg["hp"] <= 0:
            ctx.on_death(tid, tg)
    return len(dead)


# ---- running a step in a WORKER PROCESS (user 2026-10-22 22:26: NPC work must never slow the players down) ---------------
# Python threads share one interpreter lock, so CPU work in a thread would still hold up the game loop.  The server
# therefore sends each battle's units to a pool of worker PROCESSES (concurrent.futures), which run step() on a copy and
# send back the new positions / HP / states; the game loop only packs and applies them (about a millisecond).
IN_FIELDS = ("hp", "pos", "hive", "put", "npc", "nation", "state", "target", "home", "mode", "poc", "off", "role",
             "hunter", "cd", "armor", "arow", "spd", "urole", "max", "gate", "name")
OUT_FIELDS = ("pos", "x", "y", "state", "target", "cd", "on_poc", "hp", "last_hitter", "mv")
_WORKER = {"grids": {}, "walk": None}


def pack(targets, pocs, side_of, params):
    """the payload of one step (plain data, picklable)."""
    t = {}
    for tid, tg in targets.items():
        if tg.get("hp", 0) > 0 and tg.get("pos"):
            d = {k: tg[k] for k in IN_FIELDS if k in tg}
            d["put"] = {k: v for k, v in (tg.get("put") or {}).items() if k in ("st9", "spd", "abil", "kind")}
            d["_side"] = side_of(tg)
            t[tid] = d
    return {"targets": t, "pocs": {k: {"x": p["x"], "y": p["y"], "owner": p["owner"]} for k, p in pocs.items()},
            "params": params}


def _worker_grid(walk_path, name):
    if _WORKER["walk"] is None:
        import json
        try:
            _WORKER["walk"] = json.load(open(walk_path))
        except Exception:
            _WORKER["walk"] = {}
    g = _WORKER["grids"].get(name)
    if g is None and name in _WORKER["walk"]:
        g = _WORKER["grids"][name] = Grid.from_entry(_WORKER["walk"][name])
    return g


def step_remote(payload):
    """runs in a worker process: one step on the packed battle, returns {"units": {tid: fields}, "dead": [tid]}."""
    p = payload["params"]
    allies = {tuple(x) for x in p.get("allies", ())}
    import damage_types as DT
    _dt_on = bool(p.get("damage_types"))

    def damage(dmg, armor, row, col):
        return DT.hit_damage(dmg, armor, row, col if _dt_on else -1)      # (damage_types: the one formula)

    ctx = Ctx()
    ctx.grid = _worker_grid(p["walk_path"], p["map"])
    ctx.now, ctx.aggro, ctx.leash, ctx.focus = p["now"], p["aggro"], p["leash"], p["focus"]
    ctx.poc_radius, ctx.hunt_from = p["poc_radius"], p["hunt_from"]
    ctx.brain, ctx.tier = p.get("brain", False), p.get("tier", 1)
    ctx.side_of = lambda tg: tg["_side"]
    ctx.same_side = lambda a, b: a == b or (a, b) in allies or (b, a) in allies
    ctx.damage = damage
    dead = []
    ctx.on_death = lambda tid, tg: dead.append(tid)
    Grid.spent = 0
    targets = payload["targets"]
    step(targets, payload["pocs"], ctx, p["dt"])
    return {"units": {tid: {k: tg.get(k) for k in OUT_FIELDS} for tid, tg in targets.items()}, "dead": dead}
