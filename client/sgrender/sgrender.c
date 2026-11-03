/* SGRender.dll - the new drawing layer of Galactic Overlord (银河霸主, formerly Shattered Galaxy) (plan: Claude Docs "SGalaxy 绘图层与界面重设计规划",
 * project doc claude/RENDER_UI_REDESIGN_PLAN.md).
 *
 * PHASE 0 (2026-10-28): the skeleton.
 *   - SG.exe (client patch F48) loads this DLL once at start (CGraph init 004c0bd0) and calls SGR_Init(table).
 *   - The DLL fills the call-out TABLE (exe .data page tail 0xEAFF80) that F48's stubs call:
 *       table[1] on_present(CGraph*) at CGraph::EndFrame 004c4a60 -> nonzero = "I drew the frame myself, skip unlock+present"
 *       table[2] on_create(CWnd*, create struct*)        (CWnd::Create 005ecc50, every window)
 *     The exe code is NOT changed at run time (the anti-cheat hash covers it): every hook is a static F48 stub that
 *     calls through this table; without the DLL the table stays 0 and the stubs do nothing.
 *   - Phase 0 only OBSERVES: a log of every window (RTTI class, name, rect, parent) = the runtime window inventory,
 *     frame statistics, and F12 = a screenshot of the 800x600 canvas (BMP) to prove the canvas is captured
 *     pixel-exact (phase 0 gate).  It returns 0 from on_present, so the original present still draws.
 * PHASE 1 (2026-10-28): widescreen - see "PHASE 1: WIDESCREEN (F49)" below.  SGRender.dbg also enables F11 /
 * SGRender_tree.req (the live window tree into the log).
 * Build: i686-w64-mingw32-gcc -O2 -shared -static-libgcc -o SGRender.dll sgrender.c -Wl,--kill-at
 */
#include <windows.h>
#include <stdio.h>
#include <string.h>
#include "sgrender.h"

#define SGR_VERSION 2
#define TBL_VERSION 0
#define TBL_PRESENT 1
#define TBL_CREATE  2
#define TBL_FRAME   3          /* F49: frame begin (back surface locked, before the window tree) */
#define TBL_WIDTH   4          /* F49: the frame width W the exe uses (0 = 800) */
#define TBL_WUSED   5          /* F49: written by the exe = the W really in use */
#define TBL_WIDE_MAIN  9       /* F49: the main window "TC Main" (spans the frame) */
#define TBL_WIDE_FIELD 10      /* F49: the field window "Field" (spans the frame) */
#define TBL_FOG_DRAW   11      /* F49: the field map's fog of war draw 00499d90 (MapWnd) -> fog_draw */
#define TBL_FOG_VIS    12      /* F49: fog visibility test 004b6120 (fog, x, y) -> fog_vis */
#define TBL_MAPH       13      /* F51: the field map's height MH (462..600; 0 = 462) */
#define TBL_QMSLIDE    14      /* F52: the quick menu's slide 004a4a50 (CFieldWnd) -> qm_slide */
#define TBL_PATH       15      /* F55: the path builder 00413c60 (A*) -> path_build: straight paths (sgpath.h) */
static volatile DWORD *g_table;
#include "sgpath.h"

static FILE *g_log;
static unsigned g_frames, g_frames_win, g_t_win, g_shots;
static int g_f12_was;

static int g_dbg;   /* SGRender.dbg next to SG.exe -> window inventory + FPS lines (players' logs stay small) */

static void open_log(void)
{
    if (g_log) return;
    if (GetFileAttributesA("GORender.ini") == INVALID_FILE_ATTRIBUTES)   /* (11-02 GO names) the old settings, once */
        CopyFileA("SGRender.ini", "GORender.ini", TRUE);
    g_dbg = GetFileAttributesA("GORender.dbg") != INVALID_FILE_ATTRIBUTES;
    g_log = fopen("GORender.log", g_dbg ? "a" : "w");
}

static void logf_(const char *fmt, ...)
{
    open_log();
    if (!g_log) return;
    SYSTEMTIME st; GetLocalTime(&st);
    fprintf(g_log, "%02d:%02d:%02d.%03d ", st.wHour, st.wMinute, st.wSecond, st.wMilliseconds);
    va_list ap; va_start(ap, fmt); vfprintf(g_log, fmt, ap); va_end(ap);
    fputc('\n', g_log); fflush(g_log);
}

static int in_image(const void *p) { DWORD a = (DWORD)p; return a >= 0x401000 && a < 0xEB5000; }

void sgr_log(const char *fmt, ...)
{
    open_log();
    if (!g_log) return;
    char buf[1024];
    va_list ap; va_start(ap, fmt); _vsnprintf(buf, sizeof buf - 1, fmt, ap); va_end(ap);
    buf[sizeof buf - 1] = 0;
    logf_("%s", buf);
}

/* MSVC RTTI: vtable[-1] = Complete Object Locator; COL+12 = TypeDescriptor; TD+8 = ".?AVName@@" */
static const char *rtti_name_to(void *obj, char *buf, int cap)
{
    if (!obj || IsBadReadPtr(obj, 4)) return "?";
    void **vt = *(void ***)obj;
    if (!vt || IsBadReadPtr(vt - 1, 4)) return "?";      /* the HUD hooks some instances with vtable copies (outside the image) */
    void *col = vt[-1];
    if (!in_image(col)) return "?";
    void *td = *(void **)((char *)col + 12);
    if (!in_image(td)) return "?";
    const char *n = (const char *)td + 8;
    if (strncmp(n, ".?AV", 4) != 0) return "?";
    n += 4;
    int i = 0;
    while (n[i] && !(n[i] == '@' && n[i + 1] == '@') && i < cap - 1) { buf[i] = n[i]; i++; }
    buf[i] = 0;
    return buf;
}

/* ---- PHASE 1: WIDESCREEN (F49) ----------------------------------------------------------------------------
 * The exe draws a W x 600 frame (cnc-ddraw scales it to the screen).  The game keeps its 800 x 600 world: F49 moves
 * every viewport DX = (W-800)/2 to the right and the mouse back, so every screen / dialog is centred by itself.
 * The DLL only (a) chooses W, (b) widens the field's map view (MapWnd: x = -DX, width W), (c) puts the field's
 * right-edge pieces at the frame's right edge (+DX), (d) tells the exe which windows span the frame (TC Main, Field:
 * child clipping and mouse hit tests use -DX .. 800+DX for them), (e) clears the back surface every frame.
 * W: SGRender.ini [render] width=N (800 = the old picture; 0 / missing = from the monitor: 600 * cx / cy). */
static int g_W = 800, g_DX = 0;
static int g_MH = 462;           /* F51: the field map's height (600 with the HUD: its panels float over the map) */
int sgr_map_h(void) { return g_MH; }

static int choose_width(void)
{
    int w = GetPrivateProfileIntA("render", "width", 0, ".\\GORender.ini");
    if (w <= 0) {
        int cx = GetSystemMetrics(SM_CXSCREEN), cy = GetSystemMetrics(SM_CYSCREEN);
        w = (cx > 0 && cy > 0) ? 600 * cx / cy : 800;
    }
    w -= w % 10;                     /* the windowed 32-bit present copies 5 px per step; DX must be whole */
    if (w < 800) w = 800;
    if (w > 1440) w = 1440;          /* 21:9 and wider: 1440 x 600 is 2.4:1 */
    return w;
}

int sgr_debug(void) { return g_dbg; }
const char *sgr_class(void *obj) { static char b[96]; return rtti_name_to(obj, b, sizeof b); }

/* two calls in one printf need two buffers */
static const char *rtti_name(void *obj) { static char b[96]; return rtti_name_to(obj, b, sizeof b); }
static const char *rtti_name2(void *obj) { static char b[96]; return rtti_name_to(obj, b, sizeof b); }

/* CWnd::Create(create struct): struct = name[0x104] then x, y, w, h (+0x104..+0x110), parent (+0x114), +0x118 */
static void __cdecl on_create(void *wnd, void *cs)
{
    if ((g_DX || g_MH != 462) && cs && !IsBadWritePtr(cs, 0x118)) {
        int *r = (int *)((char *)cs + 0x104);          /* x, y, w, h (relative to the parent) */
        char *parent = *(char **)((char *)cs + 0x114);
        const char *name = (const char *)cs;
        if (!parent && !strcmp(name, "TC Main"))
            g_table[TBL_WIDE_MAIN] = (DWORD)wnd;
        else if (parent && !IsBadReadPtr(parent, 0x11c)) {
            const char *pname = parent + 4;            /* CWnd +4 = its name (CWnd::Create strcpy) */
            if (!strcmp(name, "Field"))
                g_table[TBL_WIDE_FIELD] = (DWORD)wnd;
            else if (!strcmp(pname, "Field")) {
                if (!strcmp(name, "MapWnd") && r[2] == 800) {
                    r[0] = -g_DX; r[2] = g_W;          /* the field map over the whole frame */
                    if (r[3] == 462) r[3] = g_MH;      /* F51: and the whole height */
                } else if (r[1] < 400 && (r[0] >= 800 || (r[0] >= 400 && r[0] + r[2] >= 795 && r[2] <= 320)
                                          || !strncmp(name, "@ fw-rt-", 8)))   /* (10-28 23:41) the retreat / reinforce
                                                          buttons sit left of the frame edge but belong to its frame */
                    r[0] += g_DX;                      /* right-edge pieces (quick menu, top-right buttons, the
                                                          right status cards at x 800): at the frame's right edge */
            }
        }
    }
    if (!g_dbg) return;
    if (!cs || IsBadReadPtr(cs, 0x11c)) { logf_("WND %p %s (no create struct)", wnd, rtti_name(wnd)); return; }
    const int *r = (const int *)((char *)cs + 0x104);
    void *parent = *(void **)((char *)cs + 0x114);
    char name[64]; lstrcpynA(name, (const char *)cs, sizeof name);
    logf_("WND %p %-28s name=\"%s\" rect=%d,%d %dx%d parent=%p %s flags=%d",
          wnd, rtti_name(wnd), name, r[0], r[1], r[2], r[3], parent, parent ? rtti_name2(parent) : "-", r[5]);
}

/* the canvas pixel format, read once from the back surface (IDirectDrawSurface::GetPixelFormat, vtable +0x54) */
static DWORD g_rm = 0xf800, g_gm = 0x07e0, g_bm = 0x001f;   /* defaults RGB565; 004c01f0's 32-bit path assumes 555 */
static int g_fmt_known;

static int shift_of(DWORD m) { int s = 0; if (!m) return 0; while (!(m & 1)) { m >>= 1; s++; } return s; }
static int bits_of(DWORD m) { int b = 0; m >>= shift_of(m); while (m & 1) { m >>= 1; b++; } return b; }
static unsigned char chan(unsigned v, DWORD m)
{
    int b = bits_of(m); unsigned c = (v & m) >> shift_of(m);
    return b >= 8 ? (unsigned char)(c >> (b - 8)) : (unsigned char)((c << (8 - b)) | (c >> (2 * b - 8 > 0 ? 2 * b - 8 : 0)));
}

static void read_format(void *cg)
{
    g_fmt_known = 1;
    void **surf = *(void ***)((char *)cg + 0x19c);
    if (!surf || IsBadReadPtr(surf, 4) || IsBadReadPtr(*surf, 0x58)) return;
    typedef HRESULT (WINAPI *GPF)(void *, DWORD *);
    DWORD pf[8] = {32};
    HRESULT hr = ((GPF)(*(void ***)surf)[0x54 / 4])(surf, pf);
    logf_("FORMAT hr=%08lx flags=%08lx bits=%lu R=%08lx G=%08lx B=%08lx", hr, pf[1], pf[3], pf[4], pf[5], pf[6]);
    if (hr == 0 && pf[3] == 16 && pf[4] && pf[5] && pf[6]) { g_rm = pf[4]; g_gm = pf[5]; g_bm = pf[6]; }
}

static void shot(const unsigned short *px, int pitch)
{
    char fn[64]; sprintf(fn, "GORender_shot%03u.bmp", ++g_shots);
    FILE *f = fopen(fn, "wb");
    if (!f) return;
    const int W = g_W, H = 600, row = W * 3;
    BITMAPFILEHEADER bf = {0}; BITMAPINFOHEADER bi = {0};
    bf.bfType = 0x4D42; bf.bfOffBits = sizeof bf + sizeof bi; bf.bfSize = bf.bfOffBits + row * H;
    bi.biSize = sizeof bi; bi.biWidth = W; bi.biHeight = H; bi.biPlanes = 1; bi.biBitCount = 24;
    fwrite(&bf, sizeof bf, 1, f); fwrite(&bi, sizeof bi, 1, f);
    static unsigned char line[1440 * 3];
    for (int y = H - 1; y >= 0; y--) {
        const unsigned short *s = px + y * pitch;
        for (int x = 0; x < W; x++) {
            unsigned v = s[x];
            line[x * 3 + 0] = chan(v, g_bm);
            line[x * 3 + 1] = chan(v, g_gm);
            line[x * 3 + 2] = chan(v, g_rm);
        }
        fwrite(line, row, 1, f);
    }
    fclose(f);
    logf_("SHOT %s (canvas %p, pitch %d px)", fn, px, pitch);
}

/* the frame: CGraph::EndFrame 004c4a60 (thiscall, CGraph in ecx), called once per frame by the main loop 005490c0
 * while the back surface [cg+0x19c] is still LOCKED (it unlocks it, then BltFast's it to the primary in 004c00b0;
 * windowed mode [cg+0x31] first converts the canvas in 004c01f0).
 * canvas = [cg+0x34] (u16 pixels, locked back surface), pitch [cg+0x60] in pixels; [cg+0x5c] = viewport origin.  A nonzero return skips unlock + present. */
static int __cdecl on_present(void *cg)
{
    g_frames++; g_frames_win++;
    DWORD now = GetTickCount();
    if (!cg || IsBadReadPtr(cg, 0x1a0)) return 0;
    if (!g_fmt_known && g_dbg) {
        const char *c = (const char *)cg;
        logf_("FRAME1 cg=%p canvas=%p pitch=%d +64=%d +68=%d windowed=%d +32=%d mode=%d back=%p primary=%p",
              cg, *(void **)(c + 0x5c), *(int *)(c + 0x60), *(int *)(c + 0x64), *(int *)(c + 0x68),
              c[0x31], c[0x32], *(int *)(c + 0x184), *(void **)(c + 0x19c), *(void **)(c + 0x194));
        read_format(cg);
    }
    if (!g_t_win) g_t_win = now;
    if (g_dbg && now - g_t_win >= 10000) {
        logf_("FPS %.1f (%u frames total)", g_frames_win * 1000.0 / (now - g_t_win), g_frames);
        g_frames_win = 0; g_t_win = now;
    }
    int f12 = (GetAsyncKeyState(VK_F12) & 0x8000) != 0;
    int req = GetFileAttributesA("GORender_shot.req") != INVALID_FILE_ATTRIBUTES;   /* test harness trigger */
    if ((f12 && !g_f12_was) || req) {
        if (req) DeleteFileA("GORender_shot.req");
        if (!g_fmt_known) read_format(cg);
        /* +0x34 = locked back surface base (+0x5c is only the CURRENT VIEWPORT origin, see SetViewport 00438100) */
        const unsigned short *px = *(const unsigned short **)((char *)cg + 0x34);
        int pitch = *(int *)((char *)cg + 0x60);
        if (px && pitch >= g_W && pitch < 4096 && !IsBadReadPtr(px, pitch * 2 * 600)) shot(px, pitch);
        else logf_("SHOT skipped: canvas %p pitch %d", px, pitch);
    }
    g_f12_was = f12;
    return 0;                               /* phase 0: the original unlock + present still run */
}

/* debug: F11 / SGRender_tree.req = the live window tree (abs / rel rects) into the log */
static void dump_tree(char *w, int depth)
{
    if (!w || depth > 12 || IsBadReadPtr(w, 0x158)) return;
    const int *a = (const int *)(w + 0x118), *r = (const int *)(w + 0x128);
    logf_("TREE %*s%s \"%.40s\" abs=%d,%d-%d,%d rel=%d,%d %dx%d vis=%d", depth * 2, "", rtti_name(w), w + 4,
          a[0], a[1], a[2], a[3], r[0], r[1], r[2], r[3], w[0x155]);
    int n = *(int *)(w + 0x148);
    char **kids = *(char ***)(w + 0x150);
    if (n > 0 && n < 500 && kids && !IsBadReadPtr(kids, n * 4))
        for (int i = 0; i < n; i++) dump_tree(kids[i], depth + 1);
}

static char *find_wnd(char *w, const char *want, int depth)
{
    if (!w || depth > 12 || IsBadReadPtr(w, 0x158)) return NULL;
    if (strstr(w + 4, want)) return w;
    int n = *(int *)(w + 0x148); char **kids = *(char ***)(w + 0x150);
    for (int i = 0; n > 0 && n < 500 && kids && i < n; i++) { char *r = find_wnd(kids[i], want, depth + 1); if (r) return r; }
    return NULL;
}

/* debug: SGRender_units.req = the unit manager (DAT_006ba7d4: +0x50 count, +0x58 array sorted by id at unit+4)
 * and the side status cards (CUnitWnd: +0x160 slot, +0x164 unit id) into the log; raw dump of the first unit. */
static char *g_app;
static int tv(char *u, int base, int idx) { char *p = *(char **)(u + base + 4 * *(unsigned short *)(u + idx)); return p && !IsBadReadPtr(p, 8) ? *(int *)(p + 4) : -1; }
static void dump_units(void)
{
    char *mgr = *(char **)0x6ba7d4;
    if (!mgr || IsBadReadPtr(mgr, 0x60)) { logf_("UNITS no manager"); return; }
    int n = *(int *)(mgr + 0x50);
    char **arr = *(char ***)(mgr + 0x58);
    logf_("UNITS mgr %p n=%d", mgr, n);
    if (n <= 0 || n > 2000 || IsBadReadPtr(arr, n * 4)) return;
    for (int i = 0; i < n; i++) {
        char *u = arr[i];
        if (!u || IsBadReadPtr(u, 0xf200)) continue;
        logf_("U %p %s id=%u name=\"%.20s\" 108=%d/%d 110=%d/%d 370=%d/%d 158=%x 15c=%x",
              u, rtti_name(u), *(unsigned *)(u + 4), u + 0x78,
              tv(u, 0x9454, 0x9856), *(int *)(u + 0x108), tv(u, 0xa464, 0xa866), *(int *)(u + 0x110),
              tv(u, 0x1f94, 0x2396), *(int *)(u + 0x370), *(unsigned *)(u + 0x158), *(unsigned *)(u + 0x15c));
    }
    static int raw;
    char fn[64]; sprintf(fn, "GORender_unit%d.bin", raw++);
    FILE *f = fopen(fn, "wb");
    if (f) { for (int i = 0; i < n && i < 8; i++) if (arr[i] && !IsBadReadPtr(arr[i], 0xf200)) fwrite(arr[i], 0xf200, 1, f); fclose(f); }
    char *app = g_app;   /* the app object (on_frame): dump it too (selection lists live somewhere) */
    sprintf(fn, "GORender_app%d.bin", raw - 1);
    if (app && !IsBadReadPtr(app, 0x8000) && (f = fopen(fn, "wb"))) { fwrite(app, 0x8000, 1, f); fclose(f); }
    logf_("UNITS app %p", app);
    if (app) {   /* buttons of the old bottom panel and the quick menu: name, command id */
        char *slw = find_wnd((char *)app + 0x28, "StatusLowerWnd", 0), *qm = find_wnd((char *)app + 0x28, "QuickMenuWnd", 0);
        char *roots[2] = { slw, qm };
        for (int r = 0; r < 2; r++) {
            char *w = roots[r]; if (!w) continue;
            int n = *(int *)(w + 0x148); char **kids = *(char ***)(w + 0x150);
            for (int i = 0; i < n && i < 100; i++)
                if (!strcmp(rtti_name(kids[i]), "CCtrlButton"))
                    logf_("BTN %s \"%.30s\" id=%d vis=%d", r ? "qm" : "panel", kids[i] + 4, *(int *)(kids[i] + 0x2c0), kids[i][0x155]);
        }
    }
    if (app) {
        char *field = NULL, *tc = app + 0x28;
        int nk = *(int *)(tc + 0x148); char **kids = *(char ***)(tc + 0x150);
        for (int i = 0; i < nk && i < 64; i++) if (!strcmp(kids[i] + 4, "Field")) field = kids[i];
        if (field) {
            int nf = *(int *)(field + 0x148); char **fk = *(char ***)(field + 0x150);
            for (int i = 0; i < nf && i < 300; i++) {
                char *w = fk[i];
                if (strcmp(rtti_name(w), "CUnitWnd")) continue;
                logf_("CARD %p slot=%d id=%u sel=%d alt=%u/%d vis=%d x=%d target=%d", w, *(int *)(w + 0x160), *(unsigned *)(w + 0x164),
                      w[0x15c], *(unsigned *)(w + 0x168), w[0x16c], w[0x155], *(int *)(w + 0x118), *(int *)(w + 0x170));
            }
        }
    }
    for (DWORD g = 0x6ba7c0; g <= 0x6ba810; g += 4) {
        void *o = *(void **)g;
        logf_("G %06lx = %p %s", g, o, o && !IsBadReadPtr(o, 4) ? rtti_name(o) : "-");
    }
    char *uo = *(char **)0x6ba7d8;
    if (uo && !IsBadReadPtr(uo, 0x400)) {
        unsigned nat = (*(unsigned *)(uo + 0x3f8) & 0xf000) | (*(unsigned *)(uo + 0x3ec) & 0xf00) | (*(unsigned *)(uo + 0x3dc) & 0xf0) |
                       (*(unsigned *)(uo + 0x3f0) & 3) | (*(unsigned *)(uo + 0x3e0) & 0xc);
        char *ni = *(char **)0x6ba80c; int *grp = ni ? *(int **)(ni + 0x18) : 0; int ng = ni ? *(int *)(ni + 0x1c) : 0;
        char g[200]; int k = 0; for (int i = 0; i <= ng && i < 30 && grp; i++) k += sprintf(g + k, " %d", grp[i]);
        logf_("NATION mine=%u groups(n=%d):%s mode1c58=%d 2570=%d 25b0=%d", nat, ng, g,
              *(int *)(*(char **)0x6ba7c8 + 0x1c58), *(int *)(*(char **)0x6ba7c8 + 0x2570), *(*(char **)0x6ba7c8 + 0x25b0));
    }
    if (n > 0 && arr) {
        typedef int *(__attribute__((thiscall)) *posfn)(void *);
        for (int i = 0; i < n && i < 40; i++) {
            int *p = ((posfn)(*(void ***)arr[i])[5])(arr[i]);
            logf_("POS id=%u owner=%d x=%d y=%d mine69=%d slot6b=%d state=%d", *(unsigned *)(arr[i] + 4), *(int *)(arr[i] + 0x354),
                  p ? p[0] : -1, p ? p[1] : -1, arr[i][0x69], ((unsigned char *)arr[i])[0x6b], tv(arr[i], 0xa868, 0xac6a));
        }
    }
    char *bt = *(char **)0x6ba7cc, *ck = *(char **)0x6ba7c8;
    if (bt && !IsBadReadPtr(bt, 0x29c40)) {
        int sn = *(int *)(bt + 0x29b3c + 0x8c);
        logf_("SEL n=%d first=%u", sn, sn > 0 ? *(unsigned *)(*(char **)(bt + 0x29b40) + 4) : 0);
        char *map = *(char **)(bt + 0x8564);
        if (map) logf_("MAPVIEW 534=%d 538=%d 53c=%d 540=%d size=%d,%d", *(int *)(map + 0x534), *(int *)(map + 0x538),
                       *(int *)(map + 0x53c), *(int *)(map + 0x540), *(unsigned short *)(map + 0x1025f6), *(unsigned short *)(map + 0x1025f8));
    }
    if (bt && ck && !IsBadReadPtr(bt, 0x29c40)) {
        logf_("BATTLE in=%d start=%u end=%u now=%u 29bd4=%x 29c2f=%d", bt[0x29bdc], *(unsigned *)(bt + 0x29be8),
              *(unsigned *)(bt + 0x29bec), *(unsigned *)(ck + 0x25a0), *(unsigned *)(bt + 0x29bd4), bt[0x29c2f]);
        char *map = *(char **)(bt + 0x8564);
        if (map && !IsBadReadPtr(map, 0x102600)) {
            char *b = *(char **)(map + 0x10255c), *e = *(char **)(map + 0x102560);
            logf_("MAP %p %s objs %p..%p 1025e0=%d e4=%d e8=%d", map, rtti_name(map), b, e,
                  *(int *)(map + 0x1025e0), *(int *)(map + 0x1025e4), *(int *)(map + 0x1025e8));
            for (char *r = b; b && r + 0xc74 <= e && r < b + 0xc74 * 16; r += 0xc74) {
                int *q = (int *)r; char h[200]; int k = 0;
                for (int j = 0; j < 16; j++) k += sprintf(h + k, " %d", q[j]);
                logf_("OBJ type=%d str=%d/%d owner=%d flag=%d |%s", q[0], tv(r, 0x44, 0x446), q[0xe], tv(r, 0x448, 0x84a),
                      (*(unsigned char **)(r + 0x84c + 4 * *(unsigned short *)(r + 0xc4e)))[4], h);
            }
        }
    }
}

/* ---- F49: the field map's fog of war over the wide frame ---------------------------------------------------
 * The exe keeps the fog of war of the whole map in 8x8-pixel cells (fog object = MapWnd+0x998: +0x18 = 1024x1024
 * bytes, row 0x400; +0x10 / +0x14 = window origin in cells) and copies an 800-pixel window (0x68 x 0x40 cells, row
 * 0x6a, +0x100018) that it softens (004b6210: two passes, every cell lifts its neighbours to value-1).  The fog draw
 * (00499d90) and the visibility test (004b6120) read that window, so beyond x 832 the map had no fog.  For a wide
 * frame the DLL builds the same window W+32 pixels wide with the same softening, draws it with the exe's own
 * DarkenStrip (004bf320, one call per run of equal cells, like the original) and answers the visibility test from it.
 * Cell values: 0 = black ... >= 24 = clear; a unit is visible when > 8. */
#define FOG_MAXR 0x58
#define FOG_ROWS g_fog_rows
static int g_fog_rows = 0x40;  /* F51: (MH + 32) / 8 + 3, at least the exe's 0x40 */
#define FOG_MAXC 200
static unsigned char g_fog[FOG_MAXR + 1][FOG_MAXC + 2];
static char *g_fog_obj;
static int g_fog_x0 = -1, g_fog_y0, g_fog_cols;
typedef void (__attribute__((thiscall)) *darken_fn)(void *cg, int x, int y, int level, int count);

static void fog_build(char *map)
{
    char *fog = map + 0x998;
    const unsigned char *full = (const unsigned char *)fog + 0x18;
    int cols = (g_W + 32) / 8 + 1;      /* one more: the row starts up to 31 px left of the frame (user 10-28 23:31: a
                                            strip at the right edge without fog) */
    if (cols > FOG_MAXC) cols = FOG_MAXC;
    int x0 = *(int *)(map + 0x534) * 4, y0 = *(int *)(map + 0x538) * 4;
    int mw = *(unsigned short *)(map + 0x1025f6), mh = *(unsigned short *)(map + 0x1025f8);
    int xe = x0 + cols, ye = y0 + FOG_ROWS;               /* inclusive ends, as 004b6210 */
    if (xe > mw - 1) xe = mw - 1;
    if (ye > mh - 1) ye = mh - 1;
    if (xe > 1023) xe = 1023;
    if (ye > 1023) ye = 1023;
    memset(g_fog, 0, sizeof g_fog);
    int nr = ye - y0, nc = xe - x0;
    if (x0 < 0 || y0 < 0 || nr < 0 || nc < 0) { g_fog_x0 = -1; return; }
    for (int r = 0; r <= nr; r++) memcpy(g_fog[r], full + (y0 + r) * 0x400 + x0, nc + 1);
    for (int r = 0; r < nr; r++)                          /* pass 1: right and down */
        for (int c = 0; c < nc; c++) {
            int b = g_fog[r][c];
            if (b > 1) {
                if (g_fog[r + 1][c] < b - 1) g_fog[r + 1][c] = b - 1;
                if (g_fog[r][c + 1] < b - 1) g_fog[r][c + 1] = b - 1;
            }
        }
    for (int r = nr; r > 0; r--)                          /* pass 2: left and up */
        for (int c = nc; c > 0; c--) {
            int b = g_fog[r][c];
            if (b > 1) {
                if (g_fog[r - 1][c] < b - 1) g_fog[r - 1][c] = b - 1;
                if (g_fog[r][c - 1] < b - 1) g_fog[r][c - 1] = b - 1;
            }
        }
    g_fog_obj = fog; g_fog_x0 = x0; g_fog_y0 = y0; g_fog_cols = cols;
}

static void __cdecl fog_draw(char *map)
{
    if (!map || IsBadReadPtr(map, 0x1025fa)) return;
    fog_build(map);
    if (g_fog_x0 < 0) return;
    void *cg = *(void **)0x6ba7d0;
    darken_fn darken = (darken_fn)0x4bf320;
    int ypix = -*(int *)(map + 0x540);
    for (int r = 0; r < FOG_ROWS; r++, ypix += 8) {
        int xpix = -*(int *)(map + 0x53c), run_x = xpix, run = 0, level = 0xff;
        for (int c = 0; c < g_fog_cols; c++, xpix += 8) {
            int v = g_fog[r][c];
            if (v == level) { run++; continue; }
            if (level != 0xff) darken(cg, run_x, ypix, level, run);
            level = v; run = 1; run_x = xpix;
        }
        darken(cg, run_x, ypix, level, run);            /* the original also ends every row with a call */
    }
}

static int __cdecl fog_vis(char *fog, int x, int y)
{
    if (x < 0 || y < 0 || x >= 0x400 || y >= 0x400) return 0;
    if (fog == g_fog_obj && g_fog_x0 >= 0 && x >= g_fog_x0 && x < g_fog_x0 + g_fog_cols &&
        y >= g_fog_y0 && y < g_fog_y0 + FOG_ROWS)
        return g_fog[y - g_fog_y0][x - g_fog_x0] > 8;
    int wx = *(int *)(fog + 0x10), wy = *(int *)(fog + 0x14);  /* the exe's own rule */
    if (x >= wx && x < wx + 0x68 && y >= wy && y < wy + 0x40)
        return ((unsigned char *)fog)[0x100018 + (y - wy) * 0x6a + (x - wx)] > 8;
    return ((unsigned char *)fog)[0x18 + y * 0x400 + x] > 8;
}

/* ---- F52: the quick menu slides over the map ---------------------------------------------------------------
 * The exe's slide (004a4a50) narrows the map to the menu's left edge (its slide state is the map's right edge), so
 * nothing was drawn under / below the open menu (user 10-28 21:58: a black block).  Here the menu slides by its own
 * x with the exe's steps (in 30 px, out 50 px; open at 587+DX, closed at 800+DX; hidden when closed) and the map
 * keeps its right edge at the frame's right edge. */
typedef void (__attribute__((thiscall)) *move4_fn)(void *, int, int, int, int);
typedef void (__attribute__((thiscall)) *show_fn)(void *, int);
static void __cdecl qm_slide(char *field)
{
    if (!field || IsBadReadPtr(field + 0x8554, 0x14)) return;
    char *qm = *(char **)(field + 0x855c), *map = *(char **)(field + 0x8564);
    if (!qm || !map || IsBadReadPtr(qm, 0x160) || IsBadReadPtr(map, 0x160)) return;
    move4_fn move = (move4_fn)0x5ed3c0; show_fn show = (show_fn)0x5ecf00;
    int R = 800 + g_DX, O = 587 + g_DX, x = *(int *)(qm + 0x128);
    if (*(int *)(map + 0x120) < R) {                     /* the map back to the right edge (camera unmoved) */
        int mx = *(int *)(map + 0x128);
        move(map, mx, 0, R - mx, g_MH);
        ((void (__attribute__((thiscall)) *)(void *))0x49ab30)(map);
    }
    if (*(char *)0xc34965) {                             /* open */
        if (!qm[0x155]) { show(qm, 1); x = R - 18; }
        else if (x > O) x = x - 30 < O ? O : x - 30;
        else return;
    } else {                                             /* closed */
        if (!qm[0x155]) { if (x != R) move(qm, R, 0, 0xd5, 0x1ce); return; }
        x += 50;
        if (x >= R - 18) { move(qm, R, 0, 0xd5, 0x1ce); show(qm, 0); return; }
    }
    move(qm, x, 0, 0xd5, 0x1ce);
}

/* ---- edge scroll (user 10-31 16:05 "the mouse is not at the edge yet and the map already scrolls right"): CFieldWnd's
 * mouse handler (vtable 0x652a24 slot 5 = 0049df60) sets the map's scroll flags (MapWnd +0x96a up / +0x96b down /
 * +0x96c left / +0x96d right) from the frame point in 800-space: x < 12 / x >= 788.  With the wide frame x runs
 * -DX .. 800+DX, so both sides scrolled DX+12 px before the edge (wine W 900: from 62 px).  Same rule, at the frame's
 * edges.  The slot lives in .rdata (the code checksum covers .text and .dbgmov only). */
static char __attribute__((thiscall)) field_mouse(char *self, int msg, int x, int y, int w)
{
    (void)w;
    if (msg != 0x200) return 0;
    char *m = *(char **)(self + 0x8560);
    if (!m || IsBadWritePtr(m + 0x96a, 4)) return 1;
    m[0x96a] = y < 12;
    m[0x96b] = y >= 0x24c;
    m[0x96c] = x < 12 - g_DX;
    m[0x96d] = x >= 788 + g_DX;
    return 1;
}
static void edge_scroll_hook(void)
{
    DWORD *slot = (DWORD *)0x652a38, old;
    if (IsBadReadPtr(slot, 4) || *slot != 0x49df60) { logf_("edge scroll: CFieldWnd slot 5 is %08lx, not hooked", IsBadReadPtr(slot, 4) ? 0 : *slot); return; }
    if (!VirtualProtect(slot, 4, PAGE_READWRITE, &old)) return;
    *slot = (DWORD)field_mouse;
    VirtualProtect(slot, 4, old, &old);
    logf_("edge scroll: at the frame edges (x < %d, x >= %d)", 12 - g_DX, 788 + g_DX);
}

/* map pixel visible through the fog of war? (the HUD radar shows enemies only there) */
int sgr_fog_ok(char *map) { return map && !IsBadReadPtr(map + 0x998, 0x100020); }
int sgr_fog_visible(char *map, int px, int py)   /* caller checked sgr_fog_ok(map) this frame */
{
    return fog_vis(map + 0x998, px >> 3, py >> 3);
}

/* ---- the native-resolution overlay: phase 3's HUD draws here.  Until then only a debug test card
 * (SGRender.dbg + a file SGRender_overlay.req) proves the path: crisp text and circles at screen resolution. */
static int g_ov_test;
int sgr_overlay_paint(SGOverlay *ov)
{
    if (!g_ov_test) return sghud_paint(ov);
    memset(ov->bits, 0, (size_t)ov->w * ov->h * 4); sghud_overlay_lost();
    ov->dx0 = ov->dy0 = 0; ov->dx1 = ov->w; ov->dy1 = ov->h;
    HDC dc = ov->dc;
    int s = ov->h / 600 > 0 ? ov->h * 100 / 600 : 100;          /* scale (percent) of a 600-high frame */
    HBRUSH br = CreateSolidBrush(RGB(16, 22, 10));
    HPEN pen = CreatePen(PS_SOLID, 3, RGB(201, 164, 92));        /* brass #C9A45C */
    HGDIOBJ ob = SelectObject(dc, br), op = SelectObject(dc, pen);
    int r = 60 * s / 100, cx = ov->w - r - 30, cy = r + 30;
    Ellipse(dc, cx - r, cy - r, cx + r, cy + r);
    HFONT f = CreateFontA(-28 * s / 100, 0, 0, 0, FW_BOLD, 0, 0, 0, DEFAULT_CHARSET, 0, 0, ANTIALIASED_QUALITY, 0, "Microsoft YaHei");
    HGDIOBJ of = SelectObject(dc, f);
    SetBkMode(dc, TRANSPARENT); SetTextColor(dc, RGB(244, 226, 180));
    char t[96]; sprintf(t, "SGRender overlay %dx%d", ov->w, ov->h);
    TextOutA(dc, 40, ov->h - 80 * s / 100, t, (int)strlen(t));
    SelectObject(dc, of); SelectObject(dc, ob); SelectObject(dc, op);
    DeleteObject(f); DeleteObject(br); DeleteObject(pen);
    GdiFlush();
    for (int i = 0; i < ov->w * ov->h; i++)                       /* GDI leaves alpha 0: drawn pixels become opaque */
        if (ov->bits[i] & 0xffffff) ov->bits[i] |= 0xff000000u;
    return 1;
}

/* F49 frame begin (back surface locked, nothing drawn yet): clear it.  The original never needed this - its windows
 * covered all 800 x 600 every frame; in a wide frame parts are covered by nothing (the bands beside a centred screen,
 * the space a sliding panel leaves) and would keep old pictures. */
static void __cdecl on_frame(void *cg, void *app)
{
    static int once;
    g_app = app;
    if (g_dbg && !once && app && !IsBadReadPtr(app, 0x150)) {
        const int *a = (const int *)app; once = 1;
        logf_("APP %p %s +0x140=%d,%d,%d,%d", app, rtti_name(app), a[0x50], a[0x51], a[0x52], a[0x53]);
    }
    if (g_dbg) {
        static int was;
        int k = (GetAsyncKeyState(VK_F11) & 0x8000) != 0;
        int req = GetFileAttributesA("GORender_tree.req") != INVALID_FILE_ATTRIBUTES;
        if ((k && !was) || req) { if (req) DeleteFileA("GORender_tree.req"); dump_tree((char *)app + 0x28, 0); }
        was = k;
        if (GetFileAttributesA("GORender_units.req") != INVALID_FILE_ATTRIBUTES) { DeleteFileA("GORender_units.req"); dump_units(); }
        if (GetFileAttributesA("GORender_spr.req") != INVALID_FILE_ATTRIBUTES) { DeleteFileA("GORender_spr.req"); sghud_debug_spr(); }
        if (GetFileAttributesA("GORender_crash.req") != INVALID_FILE_ATTRIBUTES) {   /* test the crash report */
            DeleteFileA("GORender_crash.req"); *(volatile int *)0 = 1;
        }
        FILE *oc = fopen("GORender_cmd.req", "r");
        if (oc) {   /* debug: "<window name> <id>" -> that window's OnCommand(2, 0, id) */
            char nm[64] = {0}; int id = 0; fscanf(oc, "%63s %d", nm, &id); fclose(oc); DeleteFileA("GORender_cmd.req");
            char *w = find_wnd((char *)app + 0x28, nm, 0);
            typedef int (__attribute__((thiscall)) *cmdf)(void *, int, int, int);
            if (w) ((cmdf)(*(void ***)w)[15])(w, 2, 0, id);
            logf_("CMD %s %d -> %p", nm, id, w);
        }
        FILE *cf = fopen("GORender_click.req", "r");
        if (cf) {   /* debug: forward a click to the window whose name contains the text (hidden windows too) */
            char want[96] = {0}; fgets(want, sizeof want, cf); fclose(cf); DeleteFileA("GORender_click.req");
            want[strcspn(want, "\r\n")] = 0;
            char *hit = find_wnd((char *)app + 0x28, want, 0);
            typedef int (__attribute__((thiscall)) *evfn)(void *, unsigned, int, int, int);
            if (hit) {
                int r1 = ((evfn)(*(void ***)hit)[5])(hit, 0x201, 1, 1, 0);
                int r2 = ((evfn)(*(void ***)hit)[5])(hit, 0x202, 1, 1, 0);
                logf_("CLICK \"%s\" -> %p %s id=%d vis=%d r=%d,%d", want, hit, rtti_name(hit), *(int *)(hit + 0x2c0), hit[0x155], r1, r2);
            } else logf_("CLICK \"%s\" not found", want);
        }
        int ovt = GetFileAttributesA("GORender_overlay.req") != INVALID_FILE_ATTRIBUTES;
        if (ovt != g_ov_test) { g_ov_test = ovt; sgr_overlay_invalidate(); }
    }
    if (g_disp.hwnd && cg && !IsBadWritePtr(cg, 0x40))
        ((char *)cg)[0x31] = 0;     /* SGDraw: the game's own windowed path (004c01f0) writes at screen positions */
    if (app && !IsBadReadPtr(app, 0xc20)) sghud_frame((char *)app, g_W, g_DX);
    if (!g_DX || !cg) return;
    unsigned short *px = *(unsigned short **)((char *)cg + 0x34);
    int pitch = *(int *)((char *)cg + 0x60);
    if (!px || pitch < g_W) return;
    if (pitch == g_W) memset(px, 0, (size_t)g_W * 600 * 2);
    else for (int y = 0; y < 600; y++) memset(px + y * pitch, 0, g_W * 2);
}

/* crash report: where it happened (module + offset), the registers, return addresses on the stack and what the
 * HUD was doing - written to SGRender.log, then the game's own handler runs (it reports to the server). */
volatile const char *g_stage_game = "-", *g_stage_paint = "-";
static LPTOP_LEVEL_EXCEPTION_FILTER g_prev_filter;
static const char *mod_of(DWORD a, DWORD *off)
{
    static char name[MAX_PATH]; HMODULE m = NULL;
    *off = a;
    if (!GetModuleHandleExA(GET_MODULE_HANDLE_EX_FLAG_FROM_ADDRESS | GET_MODULE_HANDLE_EX_FLAG_UNCHANGED_REFCOUNT, (LPCSTR)a, &m) || !m)
        return "?";
    GetModuleFileNameA(m, name, sizeof name);
    *off = a - (DWORD)m;
    const char *b = strrchr(name, '\\');
    return b ? b + 1 : name;
}
static LONG WINAPI crash_filter(EXCEPTION_POINTERS *e)
{
    static int once;
    if (!once++ && e && e->ExceptionRecord && e->ContextRecord) {
        EXCEPTION_RECORD *r = e->ExceptionRecord; CONTEXT *c = e->ContextRecord; DWORD off;
        const char *m = mod_of((DWORD)r->ExceptionAddress, &off);
        logf_("CRASH %08lx at %p = %s+%lx (thread %lu) access %lu %p; HUD game:%s paint:%s", r->ExceptionCode, r->ExceptionAddress, m, off,
              GetCurrentThreadId(), r->NumberParameters > 1 ? r->ExceptionInformation[0] : 0,
              r->NumberParameters > 1 ? (void *)r->ExceptionInformation[1] : NULL, g_stage_game, g_stage_paint);
        logf_("CRASH eax=%08lx ebx=%08lx ecx=%08lx edx=%08lx esi=%08lx edi=%08lx ebp=%08lx esp=%08lx", c->Eax, c->Ebx, c->Ecx, c->Edx, c->Esi, c->Edi, c->Ebp, c->Esp);
        DWORD *sp = (DWORD *)c->Esp;
        for (int i = 0, n = 0; i < 256 && n < 12; i++) {
            if (IsBadReadPtr(sp + i, 4)) break;
            DWORD v = sp[i];
            if (v < 0x401000) continue;
            const char *mm = mod_of(v, &off);
            if (strcmp(mm, "?") && !IsBadCodePtr((FARPROC)v)) { logf_("CRASH stack+%x %08lx = %s+%lx", i * 4, v, mm, off); n++; }
        }
    }
    return g_prev_filter ? g_prev_filter(e) : EXCEPTION_CONTINUE_SEARCH;
}

__declspec(dllexport) int __cdecl SGR_Init(volatile DWORD *table)
{
    open_log();
    g_prev_filter = SetUnhandledExceptionFilter(crash_filter);
    logf_("SGRender %d loaded, table %p%s", SGR_VERSION, (void *)table, g_dbg ? " (debug log on)" : "");
    if (!table || IsBadWritePtr((void *)table, 0x40)) return 0;
    g_table = table;
    sgr_display_init();
    g_W = choose_width();
    g_DX = (g_W - 800) / 2;
    logf_("frame %dx600 (screen %dx%d), UI centred at x %d", g_W, GetSystemMetrics(SM_CXSCREEN), GetSystemMetrics(SM_CYSCREEN), g_DX);
    table[TBL_WIDTH] = g_W;
    table[TBL_FRAME] = (DWORD)on_frame;
    {   /* F51: the map the whole frame high when the HUD floats its panels over it (not with backend=cnc / [hud]
           enable=0: the old lower panel covers 462..600 there); [render] maph=N overrides (462 = the old map) */
        char be[16] = "auto";
        GetPrivateProfileStringA("display", "backend", "auto", be, sizeof be, ".\\GORender.ini");
        int hud = GetPrivateProfileIntA("hud", "enable", 1, ".\\GORender.ini") && _stricmp(be, "cnc");
        int mh = GetPrivateProfileIntA("render", "maph", hud ? 600 : 462, ".\\GORender.ini");
        g_MH = mh < 462 ? 462 : mh > 600 ? 600 : mh;
        g_fog_rows = (g_MH + 32) / 8 + 3; if (g_fog_rows < 0x40) g_fog_rows = 0x40; if (g_fog_rows > FOG_MAXR) g_fog_rows = FOG_MAXR;
        table[TBL_MAPH] = g_MH;
        logf_("field map %dx%d (fog rows %d)", g_W, g_MH, g_fog_rows);
    }
    if (g_DX || g_MH != 462) { table[TBL_FOG_DRAW] = (DWORD)fog_draw; table[TBL_FOG_VIS] = (DWORD)fog_vis; }
    table[TBL_QMSLIDE] = (DWORD)qm_slide;
    table[TBL_PATH] = (DWORD)path_build;               /* (11-02) every client the same: lock-step (sgpath.h) */
    if (g_DX) edge_scroll_hook();
    table[TBL_PRESENT] = (DWORD)on_present;
    table[TBL_CREATE] = (DWORD)on_create;
    table[TBL_VERSION] = SGR_VERSION;
    return 1;
}

BOOL WINAPI DllMain(HINSTANCE h, DWORD why, LPVOID r) { (void)h; (void)r; if (why == DLL_PROCESS_DETACH && g_log) fclose(g_log); return TRUE; }
