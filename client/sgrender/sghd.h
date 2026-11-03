/* sghd.h - part of sgrender.c: HD field units, step 1 = record how the game draws a unit's sprites
 * (user 11-03 "原型先做g039 / 预设开启 / 目标1080p"; plan: Claude Docs "HD 戰場單位疊加：g039 原型規劃",
 * project doc claude/HD_UNIT_OVERLAY_PLAN.md).
 *
 * F58 (tools/patch_sg_debug_f58.py) sends the seven sprite draws of the unit animation draw 0x5f59d0 through TABLE
 * slot 17.  hd_record() gets (site, Cxpf, file name, args) where args = the draw's stack arguments
 *     [0] CGraph*  [1] x  [2] y  (viewport coordinates of the pivot)  [3] direction index  [4] frame  [5..6] blend data
 * and the game then draws the sprite as before (the stub jumps to the original), so nothing changes on screen yet.
 * Each frame (on_frame) starts a new list; only sprites of the HD art codes ([display] hd_codes, default g039) are kept.
 * The frame position = viewport origin (CGraph +0x64 / +0x68) + x / y.
 *   [display] hd_units=0   -> slot 17 stays 0: the exe never calls in (default 1)
 *   [display] hd_debug=1   -> every 2 s the HD sprites of the last frame go to GORender.log
 *   GORender_hd.req        -> once: EVERY sprite drawn by 0x5f59d0 in one frame goes to the log (all units) */
#define TBL_HDREC 17
#define HD_MAXREC 2048
#define HD_MAXCODES 32
typedef struct {
    unsigned char site;          /* F58 site 0..6: 0 normal, 1 alpha, 2/4/5 add, 3 tint, 6 Cxpf::Draw dispatch */
    char name[15];               /* sprite file, lower case ("g039mo.xpf") */
    void *cxpf;
    int fx, fy;                  /* frame position of the pivot */
    int dir, frame, a5, a6;
    unsigned seq;                /* draw order in the frame (all sprites, HD or not) */
} HdRec;
static HdRec g_hd[2][HD_MAXREC];
static int g_hd_n[2], g_hd_cur;
static unsigned g_hd_seq, g_hd_frames;
static char g_hd_codes[HD_MAXCODES][8]; static int g_hd_ncodes;
static int g_hd_on = -1, g_hd_dbg, g_hd_dump;
static DWORD g_hd_tlog;
static const char *HD_SITE[7] = {"normal", "alpha", "add", "tint", "add2", "add3", "draw"};

static int hd_is_code(const char *n)
{
    for (int i = 0; i < g_hd_ncodes; i++) { size_t l = strlen(g_hd_codes[i]); if (!_strnicmp(n, g_hd_codes[i], l)) return 1; }
    return 0;
}

static void __cdecl hd_record(int site, void *cxpf, const char *name, DWORD *args)
{
    unsigned seq = g_hd_seq++;
    if (!name || IsBadReadPtr(name, 4) || !args) return;
    int keep = hd_is_code(name);
    if (!keep && !g_hd_dump) return;
    const int *cg = (const int *)args[0];
    int vx = 0, vy = 0;
    if (cg && !IsBadReadPtr(cg, 0x70)) { vx = cg[0x64 / 4]; vy = cg[0x68 / 4]; }
    if (g_hd_dump == 2) {                  /* dumping this frame: everything to the log */
        logf_("hd dump #%u %-14.14s site %d %-6s cxpf %p xy %d,%d vp %d,%d dir %d frame %d a5 %08x a6 %08x",
              seq, name, site, HD_SITE[site % 7], cxpf, (int)args[1], (int)args[2], vx, vy,
              (int)args[3], (int)args[4], (unsigned)args[5], (unsigned)args[6]);
    }
    if (!keep || g_hd_n[g_hd_cur] >= HD_MAXREC) return;
    HdRec *r = &g_hd[g_hd_cur][g_hd_n[g_hd_cur]++];
    r->site = (unsigned char)site; r->cxpf = cxpf;
    int i = 0; for (; i < 14 && name[i]; i++) r->name[i] = (char)(name[i] | 0x20 * (name[i] >= 'A' && name[i] <= 'Z')); r->name[i] = 0;
    r->fx = vx + (int)args[1]; r->fy = vy + (int)args[2];
    r->dir = (int)args[3]; r->frame = (int)args[4]; r->a5 = (int)args[5]; r->a6 = (int)args[6];
    r->seq = seq;
}

static void hd_init(volatile DWORD *table)
{
    char buf[256];
    g_hd_on = GetPrivateProfileIntA("display", "hd_units", 1, ".\\GORender.ini") != 0;
    g_hd_dbg = GetPrivateProfileIntA("display", "hd_debug", 0, ".\\GORender.ini") != 0;
    GetPrivateProfileStringA("display", "hd_codes", "g039", buf, sizeof buf, ".\\GORender.ini");
    g_hd_ncodes = 0;
    for (char *t = strtok(buf, " ,;"); t && g_hd_ncodes < HD_MAXCODES; t = strtok(NULL, " ,;")) {
        strncpy(g_hd_codes[g_hd_ncodes], t, 7); g_hd_codes[g_hd_ncodes][7] = 0; g_hd_ncodes++;
    }
    if (g_hd_on) table[TBL_HDREC] = (DWORD)hd_record;
    logf_("hd units %s (codes: %s%s)", g_hd_on ? "on" : "off", g_hd_ncodes ? g_hd_codes[0] : "-", g_hd_ncodes > 1 ? ", ..." : "");
}

/* frame begin: the list just finished becomes "last frame"; a debug line every 2 s */
static void hd_frame(void)
{
    if (g_hd_on <= 0) return;
    int last = g_hd_cur;
    if (g_hd_dump == 2) { logf_("hd dump end (%u sprites)", g_hd_seq); g_hd_dump = 0; }
    g_hd_cur ^= 1; g_hd_n[g_hd_cur] = 0; g_hd_seq = 0; g_hd_frames++;
    if (g_hd_dump == 1) g_hd_dump = 2;
    if (GetFileAttributesA("GORender_hd.req") != INVALID_FILE_ATTRIBUTES) { DeleteFileA("GORender_hd.req"); g_hd_dump = 1; logf_("hd dump next frame"); }
    if (g_hd_dbg && g_hd_n[last]) {
        DWORD now = GetTickCount();
        if (now - g_hd_tlog >= 2000) {
            g_hd_tlog = now;
            logf_("hd frame %u: %d HD sprites", g_hd_frames, g_hd_n[last]);
            for (int i = 0; i < g_hd_n[last] && i < 16; i++) {
                const HdRec *r = &g_hd[last][i];
                logf_("  #%u %-14s %-6s at %d,%d dir %d frame %d a5 %08x a6 %08x", r->seq, r->name, HD_SITE[r->site % 7],
                      r->fx, r->fy, r->dir, r->frame, (unsigned)r->a5, (unsigned)r->a6);
            }
        }
    }
}
