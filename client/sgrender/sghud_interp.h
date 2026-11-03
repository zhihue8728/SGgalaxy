/* sghud_interp.h - part of sghud.c: smooth unit movement on screen (user 11-02 18:33 "开始做方案 A").
 *
 * The battle simulation is lock-step and moves a unit once per step (5 ticks = 50 ms, whole pixels), but the frame is
 * drawn ~62 times a second (F46): a moving unit stood still for ~3 frames and then jumped.  Measured 11-02 18:30
 * (claude/UNIT_MOVEMENT_EVAL.md).
 *
 * The unit's draw (CGCtrlUnit vtable slot 6 = 004ce920) places the sprite at +0x4bc4 / +0x4bc8 (the display point,
 * minus the camera); the simulation's own position is +0x944c / +0x9450 and is never touched here.  For the map
 * draw only (replay_draw -> 0049ba40) every unit's display point is set to a point between its last two simulated
 * positions, by the real time since the last step, and put back right after the draw.  Nothing the simulation
 * reads changes, so the lock-step stays in sync; the picture is at most one step (~50 ms) behind.
 *   - a jump of more than INTERP_SNAP px (teleport, gate, deploy, a big rollback) is shown at once;
 *   - the time a step takes is learned per unit from the real time between its steps (replay x2 works too);
 *   - when frames come slower than steps (a slow PC) the unit is shown where it is: no smoothing, no lag;
 *   - [display] unit_interp=0 in GORender.ini switches it off (A/B).
 * Units: CUnitMan (*0x6ba7d4) +0xa0 count / +0xa8 array - the same list the map draw walks (0049bb30). */
#ifndef IP_UNITMAN
#define IP_UNITMAN (*(char **)0x6ba7d4)                 /* (a test harness puts its own here) */
#endif
#define INTERP_N 4096
#define INTERP_SNAP 48
typedef struct {
    char *u;                     /* the unit (NULL = free) */
    unsigned id;                 /* its id (+4): a reused object starts over */
    int px, py, cx, cy;          /* the step before and the last step (display point) */
    double t, step, dur;         /* real time (ms) of the last step, learned step length (ms), glide time (ms) */
    double seen;                 /* last draw that saw it */
    int sx, sy;                  /* what we wrote this draw (put back only if the draw left it) */
} InterpU;
static InterpU g_ip[INTERP_N];
static int g_ip_on = -1;
static char **g_ip_list; static int g_ip_n;

#ifndef IP_TEST
static double ip_now(void)
{
    static LARGE_INTEGER f; LARGE_INTEGER q;
    if (!f.QuadPart) QueryPerformanceFrequency(&f);
    QueryPerformanceCounter(&q);
    return (double)q.QuadPart * 1000.0 / (double)f.QuadPart;
}
#endif
static InterpU *ip_find(char *u)
{
    unsigned h = ((unsigned)(size_t)u >> 4) * 2654435761u;
    for (int k = 0; k < 16; k++) { InterpU *e = &g_ip[(h + k) & (INTERP_N - 1)]; if (e->u == u) return e; }
    return NULL;
}
static InterpU *ip_slot(char *u, double now)
{
    unsigned h = ((unsigned)(size_t)u >> 4) * 2654435761u;
    InterpU *fr = NULL;
    for (int k = 0; k < 16; k++) {
        InterpU *e = &g_ip[(h + k) & (INTERP_N - 1)];
        if (e->u == u) return e;
        if (!fr && (!e->u || now - e->seen > 3000)) fr = e;     /* free, or a unit not drawn for 3 s */
    }
    if (fr) { memset(fr, 0, sizeof *fr); fr->u = u; }
    return fr;
}
/* before the map draw: put every unit's display point between its last two steps */
static void interp_begin(void)
{
    g_ip_n = 0;
    if (g_ip_on < 0) g_ip_on = GetPrivateProfileIntA("display", "unit_interp", 1, ".\\GORender.ini") != 0;
    if (!g_ip_on) return;
    char *um = IP_UNITMAN;
    if (!rd(um, 0xb0)) return;
    int n = *(int *)(um + 0xa0); char **a = *(char ***)(um + 0xa8);
    if (n <= 0 || !rd(a, 4)) return;
    if (n > 0xc80) n = 0xc80;
    if (!rd(a, n * 4)) return;
    double now = ip_now();
    for (int i = 0; i < n; i++) {
        char *u = a[i];
        if (!u) continue;
        InterpU *e = ip_slot(u, now);
        if (!e) continue;
        int x = *(int *)(u + 0x4bc4), y = *(int *)(u + 0x4bc8);
        unsigned id = *(unsigned *)(u + 4);
        if (e->id != id || !e->seen) {                          /* new (or reused) unit: no history yet */
            e->id = id; e->px = e->cx = x; e->py = e->cy = y; e->t = now; e->step = 50; e->dur = 57;
        } else if (x != e->cx || y != e->cy) {                  /* it stepped since the last draw */
            int jx = x - e->cx, jy = y - e->cy;
            double gap = now - e->t;
            if (gap >= 15 && gap <= 200) e->step = e->step * 0.7 + gap * 0.3;   /* the step length it really has */
            e->dur = e->step * 1.15;                    /* +15 %: a step seen one frame late does not stop the unit */
            if (jx > INTERP_SNAP || jx < -INTERP_SNAP || jy > INTERP_SNAP || jy < -INTERP_SNAP) {
                e->px = x; e->py = y;                           /* teleport / big correction: shown at once */
            } else {                                            /* from where it is shown now, so no jump back */
                double f = e->dur > 1 ? (now - e->t) / e->dur : 1; if (f > 1) f = 1; if (f < 0) f = 0;
                e->px = e->px + (int)lround((e->cx - e->px) * f);
                e->py = e->py + (int)lround((e->cy - e->py) * f);
            }
            e->cx = x; e->cy = y; e->t = now;
        }
        double f = e->dur > 1 ? (now - e->t) / e->dur : 1; if (f > 1) f = 1; if (f < 0) f = 0;
        if (now - e->seen >= e->step * 0.9) f = 1;               /* frames slower than steps: nothing to smooth, no lag */
        e->seen = now;
        int dx = e->px + (int)lround((e->cx - e->px) * f), dy = e->py + (int)lround((e->cy - e->py) * f);
        e->sx = dx; e->sy = dy;
        if (dx != x || dy != y) { *(int *)(u + 0x4bc4) = dx; *(int *)(u + 0x4bc8) = dy; }
    }
    g_ip_list = a; g_ip_n = n;
}
/* after the map draw: the simulated display points back (unless the draw itself changed one) */
static void interp_end(void)
{
    if (!g_ip_n) return;
    char *um = IP_UNITMAN;
    if (!rd(um, 0xb0) || *(char ***)(um + 0xa8) != g_ip_list) { g_ip_n = 0; return; }
    int n = *(int *)(um + 0xa0); if (n > g_ip_n) n = g_ip_n;
    for (int i = 0; i < n; i++) {
        char *u = g_ip_list[i];
        if (!u) continue;
        InterpU *e = ip_find(u);
        if (!e) continue;
        if (*(int *)(u + 0x4bc4) == e->sx && *(int *)(u + 0x4bc8) == e->sy) { *(int *)(u + 0x4bc4) = e->cx; *(int *)(u + 0x4bc8) = e->cy; }
    }
    g_ip_n = 0;
}
