/* sghd.h - part of sgrender.c: HD field units (user 11-03 "原型先做g039 / 预设开启 / 目标1080p"; plan: Claude Docs
 * "HD 戰場單位疊加：g039 原型規劃", project doc claude/HD_UNIT_OVERLAY_PLAN.md).
 *
 * F58 (tools/patch_sg_debug_f58.py, v2) sends the seven sprite draws of the unit animation draw 0x5f59d0 through TABLE
 * slot 17: hd_record(site, Cxpf, file name, args) with args = the draw's stack arguments
 *     [0] CGraph*  [1] x  [2] y  (viewport coordinates of the pivot)  [3] direction index  [4] frame  [5..6] blend data
 * Return 0 = the game draws the sprite as always; nonzero = the stub returns without drawing (the draw's arguments
 * popped).  Every sprite of an HD art code ([display] hd_codes, default g039) is recorded for sgd3d9.c, which draws its
 * HD picture over the frame at screen resolution.  The frame position = viewport origin (CGraph +0x64 / +0x68) + x / y.
 *
 * STEP 3 (11-03): occlusion and fog.  When the D3D9 presenter is drawing HD units (sgr_hd_gpu in the last frames) and
 * the sprite has an HD cell, site 6 (Cxpf::Draw 0x4032a0, the only site the game uses for unit layers - measured):
 *   - normal layer: hd_record draws it ITSELF (calls 0x4032a0) and keeps the box of frame pixels as they are right
 *     after it (the reference);
 *   - glow (add) / shadow layer: NOT drawn (the HD picture replaces it, no double glow); the reference is the box as
 *     it is before.
 * At present time sgd3d9.c compares the final frame with each reference: unchanged -> the HD picture shows; the same
 * colour darker -> fog, the HD picture is darkened as much; anything else -> something was drawn over the unit later
 * (selection marks, bars, effects, windows): the HD picture is cut out there.
 *   [display] hd_units=0   -> slot 17 stays 0: the exe never calls in (default 1)
 *   [display] hd_debug=1   -> every 2 s the HD sprites of the last frame go to GORender.log
 *   GORender_hd.req        -> once: EVERY sprite drawn by 0x5f59d0 in one frame goes to the log (all units) */
#define TBL_HDREC 17
#define HD_MAXREC 2048
#define HD_MAXCODES 32
#define HD_MAXASSETS 96
#define HD_POOL (4 * 1024 * 1024)            /* reference pixels per frame (8 MB) */
typedef SGHdRec HdRec;
static HdRec g_hd[2][HD_MAXREC];
static int g_hd_n[2], g_hd_cur;
static unsigned g_hd_seq, g_hd_frames, g_hd_gpu_frame;
static char g_hd_codes[HD_MAXCODES][8]; static int g_hd_ncodes;
static int g_hd_on = -1, g_hd_dbg, g_hd_dump;
static DWORD g_hd_tlog;
static unsigned short *g_hd_pool; static unsigned g_hd_pool_n;
static SGHdAsset g_hda[HD_MAXASSETS]; static int g_hda_n;
static const char *HD_SITE[7] = {"normal", "alpha", "add", "tint", "add2", "add3", "draw"};
typedef void (__attribute__((thiscall)) *HdDraw7)(void *, DWORD, DWORD, DWORD, DWORD, DWORD, DWORD, DWORD);

static int hd_is_code(const char *n)
{
    for (int i = 0; i < g_hd_ncodes; i++) { size_t l = strlen(g_hd_codes[i]); if (!_strnicmp(n, g_hd_codes[i], l)) return 1; }
    return 0;
}

/* hd\<code>\<file>.hds: header + cells now, the pixels when the presenter makes the texture (sgr_hd_pixels) */
static SGHdAsset *hd_asset(const char *xpf)
{
    char base[16]; int i = 0;
    for (; xpf[i] && xpf[i] != '.' && i < 15; i++) base[i] = xpf[i];
    base[i] = 0;
    for (int k = 0; k < g_hda_n; k++) if (!strcmp(g_hda[k].name, base)) return g_hda[k].state > 0 ? &g_hda[k] : NULL;
    if (g_hda_n >= HD_MAXASSETS || i < 4) return NULL;
    SGHdAsset *a = &g_hda[g_hda_n++]; memset(a, 0, sizeof *a); strcpy(a->name, base); a->state = -1;
    char code[5]; memcpy(code, base, 4); code[4] = 0;
    wsprintfA(a->path, "hd\\%s\\%s.hds", code, base);
    HANDLE f = CreateFileA(a->path, GENERIC_READ, FILE_SHARE_READ, NULL, OPEN_EXISTING, 0, NULL);
    if (f == INVALID_HANDLE_VALUE) return NULL;
    unsigned char h[16]; DWORD got = 0, sz = GetFileSize(f, NULL);
    ReadFile(f, h, 16, &got, NULL);
    if (got == 16 && !memcmp(h, "HDS1", 4)) {
        const unsigned short *u = (const unsigned short *)(h + 4);
        a->aw = u[0]; a->ah = u[1]; a->dirs = u[2]; a->fpd = u[3]; a->blend = h[12]; a->scale = h[13] ? h[13] : 1;
        size_t nc = (size_t)a->dirs * a->fpd;
        a->pix_off = (unsigned)(16 + nc * sizeof(SGHdCell));
        if (a->dirs && a->fpd && a->pix_off + (size_t)a->aw * a->ah * 4 == sz && (a->cells = (SGHdCell *)malloc(nc * sizeof(SGHdCell)))) {
            ReadFile(f, a->cells, (DWORD)(nc * sizeof(SGHdCell)), &got, NULL);
            if (got == nc * sizeof(SGHdCell)) a->state = 1;
        }
    }
    CloseHandle(f);
    if (a->state < 0) logf_("hd: %s unreadable", a->path);
    return a->state > 0 ? a : NULL;
}

unsigned char *sgr_hd_pixels(const SGHdAsset *a)
{
    size_t n = (size_t)a->aw * a->ah * 4; DWORD got = 0;
    HANDLE f = CreateFileA(a->path, GENERIC_READ, FILE_SHARE_READ, NULL, OPEN_EXISTING, 0, NULL);
    if (f == INVALID_HANDLE_VALUE) return NULL;
    unsigned char *b = (unsigned char *)malloc(n);
    SetFilePointer(f, (LONG)a->pix_off, NULL, FILE_BEGIN);
    if (b) ReadFile(f, b, (DWORD)n, &got, NULL);
    CloseHandle(f);
    if (got != n) { free(b); return NULL; }
    return b;
}
int sgr_hd_assets(SGHdAsset **arr) { *arr = g_hda; return g_hda_n; }

/* the box of frame pixels (lb..) the HD cell covers, with a 1 px margin, clipped to the W x H frame */
static int hd_box(const SGHdAsset *a, const SGHdCell *c, int fx, int fy, int *bx, int *by, int *bw, int *bh)
{
    int s = a->scale;
    int x0 = fx - (c->px + s - 1) / s - 1, y0 = fy - (c->py + s - 1) / s - 1;
    int x1 = fx + (c->w - c->px + s - 1) / s + 1, y1 = fy + (c->h - c->py + s - 1) / s + 1;
    if (x0 < 0) x0 = 0;
    if (y0 < 0) y0 = 0;
    if (x1 > g_disp.gw) x1 = g_disp.gw;
    if (y1 > g_disp.gh) y1 = g_disp.gh;
    if (x1 <= x0 || y1 <= y0) return 0;
    *bx = x0; *by = y0; *bw = x1 - x0; *bh = y1 - y0;
    return 1;
}

static void hd_snap(const int *cg, HdRec *r)
{
    const unsigned short *bits = (const unsigned short *)(size_t)cg[0x34 / 4];
    int pitch = cg[0x60 / 4];
    if (!bits || pitch < g_disp.gw) { r->bw = 0; return; }
    unsigned short *d = g_hd_pool + r->ref;
    for (int y = 0; y < r->bh; y++) memcpy(d + y * r->bw, bits + (size_t)(r->by + y) * pitch + r->bx, (size_t)r->bw * 2);
}

static int __cdecl hd_record(int site, void *cxpf, const char *name, DWORD *args)
{
    unsigned seq = g_hd_seq++;
    if (!name || IsBadReadPtr(name, 4) || !args) return 0;
    int keep = hd_is_code(name);
    if (!keep && !g_hd_dump) return 0;
    const int *cg = (const int *)args[0];
    int vx = 0, vy = 0;
    if (cg && !IsBadReadPtr(cg, 0x70)) { vx = cg[0x64 / 4]; vy = cg[0x68 / 4]; } else cg = NULL;
    if (g_hd_dump == 2) {                  /* dumping this frame: everything to the log */
        logf_("hd dump #%u %-14.14s site %d %-6s cxpf %p xy %d,%d vp %d,%d dir %d frame %d a5 %08x a6 %08x",
              seq, name, site, HD_SITE[site % 7], cxpf, (int)args[1], (int)args[2], vx, vy,
              (int)args[3], (int)args[4], (unsigned)args[5], (unsigned)args[6]);
    }
    if (!keep || g_hd_n[g_hd_cur] >= HD_MAXREC) return 0;
    HdRec *r = &g_hd[g_hd_cur][g_hd_n[g_hd_cur]++];
    memset(r, 0, sizeof *r);
    r->site = (unsigned char)site; r->cxpf = cxpf;
    int i = 0; for (; i < 14 && name[i]; i++) r->name[i] = (char)(name[i] | 0x20 * (name[i] >= 'A' && name[i] <= 'Z')); r->name[i] = 0;
    r->fx = vx + (int)args[1]; r->fy = vy + (int)args[2];
    r->dir = (int)args[3]; r->frame = (int)args[4]; r->a5 = (int)args[5]; r->a6 = (int)args[6];
    r->seq = seq; r->cell = -1;
    SGHdAsset *a = hd_asset(r->name);
    if (!a || r->dir < 0 || r->dir >= a->dirs || r->frame < 0) return 0;
    int ci = (r->frame % a->fpd) * a->dirs + r->dir;
    if (!a->cells[ci].w) return 0;                      /* no HD picture for this cell: the game's own */
    r->asset = a; r->cell = ci;
    /* occlusion needs the presenter (D3D9) drawing HD, site 6, the frame bits and room in the pool */
    if (site != 6 || !cg || g_hd_frames - g_hd_gpu_frame > 3 || !g_hd_pool) return 0;
    if (!hd_box(a, &a->cells[ci], r->fx, r->fy, &r->bx, &r->by, &r->bw, &r->bh)) return a->blend ? 1 : 0;
    if (g_hd_pool_n + (unsigned)(r->bw * r->bh) > HD_POOL) { r->bw = 0; return 0; }
    r->ref = g_hd_pool_n; g_hd_pool_n += (unsigned)(r->bw * r->bh);
    if (a->blend) { hd_snap(cg, r); return 1; }         /* glow / shadow: replaced by the HD picture */
    ((HdDraw7)0x4032a0)(cxpf, args[0], args[1], args[2], args[3], args[4], args[5], args[6]);
    hd_snap(cg, r);
    return 1;
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
    if (g_hd_on) {
        g_hd_pool = (unsigned short *)malloc((size_t)HD_POOL * 2);
        g_hd_gpu_frame = (unsigned)-100;
        table[TBL_HDREC] = (DWORD)hd_record;
    }
    logf_("hd units %s (codes: %s%s)", g_hd_on ? "on" : "off", g_hd_ncodes ? g_hd_codes[0] : "-", g_hd_ncodes > 1 ? ", ..." : "");
}

/* frame begin: the list just finished becomes "last frame"; a debug line every 2 s */
static void hd_frame(void)
{
    if (g_hd_on <= 0) return;
    int last = g_hd_cur;
    if (g_hd_dump == 2) { logf_("hd dump end (%u sprites)", g_hd_seq); g_hd_dump = 0; }
    g_hd_cur ^= 1; g_hd_n[g_hd_cur] = 0; g_hd_seq = 0; g_hd_frames++; g_hd_pool_n = 0;
    if (g_hd_dump == 1) g_hd_dump = 2;
    if (GetFileAttributesA("GORender_hd.req") != INVALID_FILE_ATTRIBUTES) { DeleteFileA("GORender_hd.req"); g_hd_dump = 1; logf_("hd dump next frame"); }
    if (g_hd_dbg && g_hd_n[last]) {
        DWORD now = GetTickCount();
        if (now - g_hd_tlog >= 2000) {
            g_hd_tlog = now;
            int snaps = 0; for (int i = 0; i < g_hd_n[last]; i++) snaps += g_hd[last][i].bw > 0;
            logf_("hd frame %u: %d HD sprites, %d with occlusion snapshots", g_hd_frames, g_hd_n[last], snaps);
            for (int i = 0; i < g_hd_n[last] && i < 8; i++) {
                const HdRec *r = &g_hd[last][i];
                logf_("  #%u %-14s %-6s at %d,%d dir %d frame %d box %dx%d", r->seq, r->name, HD_SITE[r->site % 7],
                      r->fx, r->fy, r->dir, r->frame, r->bw, r->bh);
            }
        }
    }
}

/* sgd3d9.c draws them at present time (end of the same frame, game thread): the list being filled is complete */
int sgr_hd_list(const SGHdRec **recs) { if (g_hd_on <= 0) return 0; *recs = g_hd[g_hd_cur]; return g_hd_n[g_hd_cur]; }
const unsigned short *sgr_hd_pool(void) { return g_hd_pool; }
int sgr_hd_debug(void) { return g_hd_dbg; }
void sgr_hd_gpu(void) { g_hd_gpu_frame = g_hd_frames; }
