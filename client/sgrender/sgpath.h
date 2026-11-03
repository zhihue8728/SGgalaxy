/* sgpath.h - part of sgrender.c: STRAIGHT PATHS (user 11-02 18:58 "开始做方案 B"; claude/UNIT_MOVEMENT_EVAL.md).
 *
 * Why units walked "on a grid": the client's A* (00415xxx, map *0x6ba834, 8 px cells) moves in 8 directions with
 * jumps of 1..4 cells (direction table 0x6a5510, cost 100 straight / 141 diagonal).  0x413c60 turns its cell list
 * into the unit's path (CPath at unit +0x7410): nodes {+8 x, +0xc y, +0x10 cell x, +0x14 cell y, +0x18 d (cost so
 * far: 100 per 8 px), +0x1c direction 0..127}.  The mover (004e42b0) advances d by the unit's speed every step and
 * 005636f0 puts the unit on the polyline at d - so the polyline itself was the zig-zag (only 0/45/90° pieces).
 *
 * F55 (tools/patch_sg_debug_f55.py) sends the 5 calls of 0x413c60 through TABLE[15]; this hook runs the original
 * and then pulls the path straight ("string pulling"):
 *   - from each kept node, the farthest later node that is in clear line of sight is kept; the nodes between are
 *     moved onto that straight line (same order, spread by their old d) - the list itself is not changed;
 *   - line of sight = every 2 px along the line, the unit's square (the A*'s own test 0041dd90: cells x-s+1..x+s-1,
 *     y-s+1..y+s-1 of the walk grid map+0x119978, s = A* +0x18) is free; a diagonal cell step also checks both
 *     corner cells; the unit's own start cell is not tested (the A* does not test it either);
 *   - d is recomputed from the real length (100 per 8 px, the same unit as before, so speed is unchanged and now the
 *     same in every direction), at least +1 per node (005636f0 divides by the difference);
 *   - the direction of every node = the true direction of its straight piece in 128 steps (was 8).
 * LOCK-STEP: every client builds the same path from the same walk grid at the same tick, so this must be identical
 * everywhere: integer arithmetic only, no option, no randomness, nothing read from this PC.  A client without F55
 * (or with another version of this hook) walks other paths = desync - publish it with -Min.  */
static const int PATH_DIRS[128][2] = { {65536,0}, {65457,3216}, {65220,6424}, {64827,9616}, {64277,12785}, {63572,15924}, {62714,19024}, {61705,22078}, {60547,25080}, {59244,28020}, {57798,30893}, {56212,33692}, {54491,36410}, {52639,39040}, {50660,41576}, {48559,44011}, {46341,46341}, {44011,48559}, {41576,50660}, {39040,52639}, {36410,54491}, {33692,56212}, {30893,57798}, {28020,59244}, {25080,60547}, {22078,61705}, {19024,62714}, {15924,63572}, {12785,64277}, {9616,64827}, {6424,65220}, {3216,65457}, {0,65536}, {-3216,65457}, {-6424,65220}, {-9616,64827}, {-12785,64277}, {-15924,63572}, {-19024,62714}, {-22078,61705}, {-25080,60547}, {-28020,59244}, {-30893,57798}, {-33692,56212}, {-36410,54491}, {-39040,52639}, {-41576,50660}, {-44011,48559}, {-46341,46341}, {-48559,44011}, {-50660,41576}, {-52639,39040}, {-54491,36410}, {-56212,33692}, {-57798,30893}, {-59244,28020}, {-60547,25080}, {-61705,22078}, {-62714,19024}, {-63572,15924}, {-64277,12785}, {-64827,9616}, {-65220,6424}, {-65457,3216}, {-65536,0}, {-65457,-3216}, {-65220,-6424}, {-64827,-9616}, {-64277,-12785}, {-63572,-15924}, {-62714,-19024}, {-61705,-22078}, {-60547,-25080}, {-59244,-28020}, {-57798,-30893}, {-56212,-33692}, {-54491,-36410}, {-52639,-39040}, {-50660,-41576}, {-48559,-44011}, {-46341,-46341}, {-44011,-48559}, {-41576,-50660}, {-39040,-52639}, {-36410,-54491}, {-33692,-56212}, {-30893,-57798}, {-28020,-59244}, {-25080,-60547}, {-22078,-61705}, {-19024,-62714}, {-15924,-63572}, {-12785,-64277}, {-9616,-64827}, {-6424,-65220}, {-3216,-65457}, {0,-65536}, {3216,-65457}, {6424,-65220}, {9616,-64827}, {12785,-64277}, {15924,-63572}, {19024,-62714}, {22078,-61705}, {25080,-60547}, {28020,-59244}, {30893,-57798}, {33692,-56212}, {36410,-54491}, {39040,-52639}, {41576,-50660}, {44011,-48559}, {46341,-46341}, {48559,-44011}, {50660,-41576}, {52639,-39040}, {54491,-36410}, {56212,-33692}, {57798,-30893}, {59244,-28020}, {60547,-25080}, {61705,-22078}, {62714,-19024}, {63572,-15924}, {64277,-12785}, {64827,-9616}, {65220,-6424}, {65457,-3216} };

static int path_blocked(const unsigned char *grid, int cx, int cy, int s)
{
    if (cx < 0 || cy < 0 || cx >= 0x428 || cy >= 0x428) return 1;
    for (int y = cy - s + 1; y <= cy + s - 1; y++) {
        if (y < 0 || y >= 0x428) return 1;
        const unsigned char *r = grid + y * 0x428;
        for (int x = cx - s + 1; x <= cx + s - 1; x++) {
            if (x < 0 || x >= 0x428) return 1;
            if (r[x]) return 1;
        }
    }
    return 0;
}
static int path_los(const unsigned char *grid, int ax, int ay, int bx, int by, int s)
{
    int dx = bx - ax, dy = by - ay, adx = dx < 0 ? -dx : dx, ady = dy < 0 ? -dy : dy;
    int n = (adx > ady ? adx : ady) / 2 + 1;
    int scx = ax >> 3, scy = ay >> 3, pcx = scx, pcy = scy;
    for (int i = 1; i <= n; i++) {
        int x = ax + dx * i / n, y = ay + dy * i / n, cx = x >> 3, cy = y >> 3;
        if (cx == pcx && cy == pcy) continue;
        if (!(cx == scx && cy == scy) && path_blocked(grid, cx, cy, s)) return 0;
        if (cx != pcx && cy != pcy && (path_blocked(grid, cx, pcy, s) || path_blocked(grid, pcx, cy, s))) return 0;
        pcx = cx; pcy = cy;
    }
    return 1;
}
static unsigned path_isqrt(unsigned long long v)
{
    unsigned long long r = 0, b = 1ULL << 62;
    while (b > v) b >>= 2;
    while (b) { if (v >= r + b) { v -= r + b; r = (r >> 1) + b; } else r >>= 1; b >>= 2; }
    return (unsigned)r;
}
static int path_dir(int dx, int dy)
{
    long long best = -(1LL << 62); int k = 0;
    for (int i = 0; i < 128; i++) {
        long long v = (long long)dx * PATH_DIRS[i][0] + (long long)dy * PATH_DIRS[i][1];
        if (v > best) { best = v; k = i; }
    }
    return k;
}
#define PATH_MAX_NODES 512
static unsigned g_path_n, g_path_pulled;
static void path_straighten(char *path, int s)
{
    char *map = *(char **)0x6ba834;
    if (!map || s < 1 || s > 8) return;
    const unsigned char *grid = (const unsigned char *)map + 0x119978;
    char *ent = *(char **)(path + 0x408 + 4 * *(unsigned short *)(path + 0x80a));
    if (!ent) return;
    char *head = *(char **)(ent + 8);
    if (!head) return;
    int *nd[PATH_MAX_NODES]; int n = 0;
    for (char *p = *(char **)head; p && p != head; p = *(char **)p) {
        if (n >= PATH_MAX_NODES) return;                     /* (never seen; left as the game made it) */
        nd[n++] = (int *)(p + 8);                           /* [0] x [1] y [2] cell x [3] cell y [4] d [5] dir byte */
    }
    if (n < 2) return;
    int od[PATH_MAX_NODES]; unsigned char sd[PATH_MAX_NODES];
    for (int i = 0; i < n; i++) { od[i] = nd[i][4]; sd[i] = *((unsigned char *)nd[i] + 0x14); }
    g_path_n++;
    for (int a = 0; a < n - 1; ) {
        int b = a + 1;
        while (b + 1 < n && path_los(grid, nd[a][0], nd[a][1], nd[b + 1][0], nd[b + 1][1], s)) b++;
        int ax = nd[a][0], ay = nd[a][1], bx = nd[b][0], by = nd[b][1], span = od[b] - od[a];
        if (bx != ax || by != ay) { int dd = path_dir(bx - ax, by - ay); for (int k = a; k < b; k++) sd[k] = (unsigned char)dd; }
        for (int k = a + 1; k < b; k++) {                   /* onto the straight line a -> b */
            int f = od[k] - od[a];
            if (span > 0) { nd[k][0] = ax + (int)((long long)(bx - ax) * f / span); nd[k][1] = ay + (int)((long long)(by - ay) * f / span); }
            else { nd[k][0] = ax; nd[k][1] = ay; }
        }
        if (b > a + 1) g_path_pulled++;
        a = b;
    }
    sd[n - 1] = sd[n - 2];                                  /* the last point: the direction it arrives in */
    for (int i = 0; i < n; i++) {
        nd[i][2] = nd[i][0] >> 3; nd[i][3] = nd[i][1] >> 3;
        *((unsigned char *)nd[i] + 0x14) = sd[i];           /* node +0x1c: its straight piece's direction (0..127) */
        if (i > 0) {
            long long dx = (long long)(nd[i][0] - nd[i - 1][0]) * 100, dy = (long long)(nd[i][1] - nd[i - 1][1]) * 100;
            int step = (int)((path_isqrt((unsigned long long)(dx * dx + dy * dy)) + 4) / 8);
            nd[i][4] = nd[i - 1][4] + (step > 0 ? step : 1);
        }
    }
}
typedef void (__attribute__((thiscall)) *pathbuild_fn)(void *astar, void *list, void *path, int x, int y);
static void __attribute__((thiscall)) path_build(char *astar, void *list, char *path, int x, int y)
{
    ((pathbuild_fn)0x413c60)(astar, list, path, x, y);
    path_straighten(path, *(int *)(astar + 0x18));
}
