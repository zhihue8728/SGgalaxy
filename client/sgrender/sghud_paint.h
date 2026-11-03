/* sghud_paint.h - part of sghud.c (included in this order; not a header on its own): the painter thread: layers, tiles, compose, the overlay hand-over */
/* ---- the painter thread -----------------------------------------------------------------------------------------
 * GDI+ needs several milliseconds for a full HUD (40 ms under wine), too long for the game loop (lock-step: a slow
 * frame is a late frame).  The game thread hands a snapshot to this thread; the finished picture is copied into the
 * overlay at the next present. */
static CRITICAL_SECTION g_lock; static HANDLE g_evt, g_thr;
static int g_ps_w, g_ps_h;                       /* client size of the snapshot */

/* ---- layers (user 11-01 06:14 "HUD architecture steps 1-3") --------------------------------------------------------
 * Each part of the HUD is recorded (sghud_rec.h: hash + bounds of its draw calls, nothing drawn), and drawn for real
 * into its own layer only when that hash or its bounds changed.  The changed rectangles (old and new bounds of every
 * changed part) are composed from the layers into the full picture g_fbuf and queued; the presenter copies only those
 * rectangles into the overlay and uploads only their union.  Before: every change drew the whole screen with GDI+
 * and copied it three times (memset, overlay, texture: 3 x 22 MB at 2880 x 1920). */
enum { P_BAND, P_CARDS, P_BANNER, P_RADAR, P_SKIN0, P_GLOW = P_SKIN0 + 8, P_SKINCTL, P_HONOR, P_TIP, NPART };   /* P_GLOW: tier-4 frame lights */
typedef struct { uint64_t h; int on, x0, y0, x1, y1; unsigned *buf; size_t cap; uint64_t *tiles; int tw, th; int def; } Layer;
/* (11-01 "keep going": F4 opens without waiting) a re-skinned window's page is kept when the window closes, by window
   kind (SKIN_WINS index), and F4's page is drawn ahead in the background once its data is here: opening finds its
   layer ready (same hash: nothing drawn) or nearly (only the changed tiles drawn) */
#define NPAGE 32
static Layer g_page[NPAGE];
static int g_f4_def = -1;
static Layer g_L[NPART];
static unsigned *g_fbuf; static int g_fw, g_fh, g_rhas;   /* the composed picture (lock) */
static RECT g_pend[32]; static int g_npend, g_pend_full;  /* rectangles the overlay has not taken yet (lock) */
static int g_full_next = 1;                               /* the next picture: everything is dirty */
static int g_ov_sync; static unsigned *g_ov_bits;         /* the overlay holds the picture up to g_pend */
static unsigned *g_wbuf; static int g_bw, g_bh;           /* the login screen's full picture */
static int g_layers_on = -1;                              /* [hud] layers=0: the old full repaint (compare / fall back) */
/* perf (step 1): what the painter and the presenter did, logged every 15 s */
static double pf_rec, pf_ras, pf_cmp; static long long pf_dirty, pf_copy; static int pf_n, pf_parts, pf_tiled; static DWORD pf_t0;
static uint64_t *g_nt; static size_t g_nt_cap;           /* the record pass's tile hashes, NPART grids */

/* what a part leaves behind for the parts after it (tips) or for the mouse (radar, band): saved after its record,
   put back while its layer is drawn again, and the record pass's state restored after */
typedef struct {
    const Medal *tip_m; float tip_x, tip_y; int tip_n;
    int ttip_on; WCHAR ttip1[48], ttip2[96]; float ttip_x, ttip_y;
    float wrad_cx, wrad_cy, wrad_r, band_y; int frame_live;
} SideFx;
static void fx_save(SideFx *f)
{
    f->tip_m = g_tip_m; f->tip_x = g_tip_x; f->tip_y = g_tip_y; f->tip_n = g_tip_n;
    f->ttip_on = g_ttip_on; memcpy(f->ttip1, g_ttip1, sizeof f->ttip1); memcpy(f->ttip2, g_ttip2, sizeof f->ttip2);
    f->ttip_x = g_ttip_x; f->ttip_y = g_ttip_y;
    f->wrad_cx = g_wrad_cx; f->wrad_cy = g_wrad_cy; f->wrad_r = g_wrad_r; f->band_y = g_band_y; f->frame_live = g_frame_live;
}
static void fx_load(const SideFx *f)
{
    g_tip_m = f->tip_m; g_tip_x = f->tip_x; g_tip_y = f->tip_y; g_tip_n = f->tip_n;
    g_ttip_on = f->ttip_on; memcpy(g_ttip1, f->ttip1, sizeof g_ttip1); memcpy(g_ttip2, f->ttip2, sizeof g_ttip2);
    g_ttip_x = f->ttip_x; g_ttip_y = f->ttip_y;
    g_wrad_cx = f->wrad_cx; g_wrad_cy = f->wrad_cy; g_wrad_r = f->wrad_r; g_band_y = f->band_y; g_frame_live = f->frame_live;
}

static void part_run(int p)
{
    g_skin_sel = -1;
    switch (p) {
    case P_BAND:   g_stage_paint = "paint_band"; paint_band(); break;
    case P_CARDS:  g_stage_paint = "paint_cards"; paint_cards(); break;
    case P_BANNER: g_stage_paint = "paint_banner"; paint_banner(); break;
    case P_RADAR:  g_stage_paint = "paint_radar"; paint_radar(); break;
    case P_HONOR:  g_stage_paint = "paint_honor"; paint_honor(); break;
    case P_TIP:    g_stage_paint = "paint_tip"; paint_tip(); break;
    case P_GLOW:   g_stage_paint = "paint_glow"; paint_glow(); break;
    default:       g_stage_paint = "paint_skin"; g_skin_sel = p == P_SKINCTL ? 100 : p - P_SKIN0; paint_skin(); g_skin_sel = -1; break;
    }
}
static int part_wanted(int p)
{
    if (!g_ps.active || (g_ps.covered && !g_ps.nskw)) return 0;
    if (p <= P_RADAR) return !g_ps.covered;
    if (p == P_GLOW) return g_nglow > 0;
    if (p >= P_SKIN0 && p < P_GLOW) return p - P_SKIN0 < g_ps.nskw;
    if (p == P_SKINCTL) return g_ps.nsk > 0;
    if (p == P_HONOR) return g_hon_open;
    return 1;
}

static void layer_reset_all(void)
{
    for (int p = 0; p < NPART; p++) { g_L[p].h = 0; g_L[p].on = 0; }
    g_full_next = 1;
}
static void blend_rect(unsigned *dst, int dw, const Layer *L, int x0, int y0, int x1, int y1)
{   /* premultiplied "over": dst = src + dst * (1 - src.alpha) */
    int lw = L->x1 - L->x0;
    if (x0 < L->x0) x0 = L->x0; if (y0 < L->y0) y0 = L->y0;
    if (x1 > L->x1) x1 = L->x1; if (y1 > L->y1) y1 = L->y1;
    for (int y = y0; y < y1; y++) {
        unsigned *d = dst + (size_t)y * dw + x0;
        const unsigned *s = L->buf + (size_t)(y - L->y0) * lw + (x0 - L->x0);
        for (int x = x0; x < x1; x++, d++, s++) {
            unsigned sv = *s, sa = sv >> 24;
            if (!sa) continue;
            if (sa == 255) { *d = sv; continue; }
            unsigned dv = *d, ia = 255 - sa;
            unsigned rb = ((dv & 0x00FF00FFu) * ia + 0x00800080u), ag = (((dv >> 8) & 0x00FF00FFu) * ia + 0x00800080u);
            rb = ((rb + ((rb >> 8) & 0x00FF00FFu)) >> 8) & 0x00FF00FFu;
            ag = ((ag + ((ag >> 8) & 0x00FF00FFu)) & 0xFF00FF00u);
            *d = sv + (rb | ag);
        }
    }
}
static RECT g_fhole[4]; static int g_nfhole;     /* (14:40) open rectangles (client px): a game window above the HUD */
static void compose_rect(const RECT *r)          /* lock held */
{
    for (int y = r->top; y < r->bottom; y++) memset(g_fbuf + (size_t)y * g_fw + r->left, 0, (size_t)(r->right - r->left) * 4);
    for (int p = 0; p < NPART; p++) {
        const Layer *L = &g_L[p];
        if (!L->on || L->x1 <= r->left || L->x0 >= r->right || L->y1 <= r->top || L->y0 >= r->bottom) continue;
        blend_rect(g_fbuf, g_fw, L, r->left, r->top, r->right, r->bottom);
    }
    for (int h = 0; h < g_nfhole; h++) {
        RECT q; if (!IntersectRect(&q, r, &g_fhole[h])) continue;
        for (int y = q.top; y < q.bottom; y++) memset(g_fbuf + (size_t)y * g_fw + q.left, 0, (size_t)(q.right - q.left) * 4);
    }
}
static void pend_add(const RECT *r)              /* lock held */
{
    if (g_pend_full) return;
    for (int i = 0; i < g_npend; i++) {          /* inside one already queued: nothing to add */
        const RECT *q = &g_pend[i];
        if (r->left >= q->left && r->top >= q->top && r->right <= q->right && r->bottom <= q->bottom) return;
    }
    if (g_npend == 32) { g_pend_full = 1; g_npend = 0; return; }
    g_pend[g_npend++] = *r;
}

/* F4's page drawn ahead (painter thread, an idle picture): the window at rest is at frame (108, 0) - (692, 411)
   (005e182e centres it in 800, it ends at y 0); a fake skin entry for it, recorded and drawn like an open one, the
   result kept in g_page.  Done once (and again after the window size / scale changed); later opens only draw the
   tiles whose data changed since. */
static int g_pre_w, g_pre_h;
static void predraw_f4(int w, int h, int tw, int th)
{
    if (g_f4_def < 0) for (unsigned j = 0; j < sizeof SKIN_WINS / sizeof *SKIN_WINS; j++) if (!strcmp(SKIN_WINS[j].cls, "CUserInfoWnd")) g_f4_def = (int)j;
    if (g_f4_def < 0 || g_f4_def >= NPAGE || !cmd_ready() || !g_recg) return;
    if (g_page[g_f4_def].on && g_pre_w == w && g_pre_h == h) return;
    for (int i = 0; i < g_ps.nskw; i++) if (g_ps.skw[i].def == g_f4_def) return;   /* it is open */
    for (int p = P_SKIN0; p < P_GLOW; p++) if (g_L[p].on && g_L[p].def == g_f4_def) return;
    size_t tn = (size_t)tw * th;
    uint64_t *tiles = (uint64_t *)calloc(tn, sizeof *tiles);
    if (!tiles) return;
    HudState keep_skw; memcpy(&keep_skw, &g_ps, sizeof g_ps);
    SideFx fx0; fx_save(&fx0);
    int keep_nglow = g_nglow, keep_nhit = g_wnhit;
    HudSkinWnd *e = &g_ps.skw[0];
    memset(e, 0, sizeof *e);
    e->x0 = (short)(108 + g_ps.DX); e->y0 = 0; e->x1 = (short)(692 + g_ps.DX); e->y1 = 411; e->def = (unsigned char)g_f4_def;
    g_ps.nskw = 1;
    /* record */
    C.g = g_recg; memset(&g_gst, 0, sizeof g_gst);
    pGdipSetSmoothingMode(C.g, GP_SMOOTH_AA); pGdipSetTextRenderingHint(C.g, GP_TEXT_AA); pGdipSetPixelOffsetMode(C.g, GP_PIXOFF_HALF);
    pGdipResetClip(C.g);
    g_rtile = tiles; g_rtw = tw; g_rth = th;
    g_rh = 14695981039346656037ULL ^ (uint64_t)(1000 + g_f4_def); g_rbany = 0; g_rball = 0; g_rec = 1; g_hit_off = 1;
    g_skin_sel = 0; paint_skin(); g_skin_sel = -1;
    g_rec = 0; C.g = NULL; g_rtile = NULL;
    int x0 = g_rball ? 0 : (int)floorf(g_rbx0), y0 = g_rball ? 0 : (int)floorf(g_rby0);
    int x1 = g_rball ? w : (int)ceilf(g_rbx1), y1 = g_rball ? h : (int)ceilf(g_rby1);
    if (x0 < 0) x0 = 0; if (y0 < 0) y0 = 0; if (x1 > w) x1 = w; if (y1 > h) y1 = h;
    Layer *L = &g_page[g_f4_def];
    if (g_rbany && x1 > x0 && y1 > y0) {
        int lw = x1 - x0, lh = y1 - y0; size_t need = (size_t)lw * lh;
        if (need > L->cap) { free(L->buf); L->buf = (unsigned *)malloc(need * 4); L->cap = L->buf ? need : 0; }
        GpBitmap *bmp = NULL; GpGraphics *g = NULL;
        if (L->buf && pGdipCreateBitmapFromScan0(lw, lh, lw * 4, GP_PARGB, (BYTE *)L->buf, &bmp) == 0) {
            memset(L->buf, 0, need * 4);
            if (pGdipGetImageGraphicsContext(bmp, &g) == 0) {
                pGdipSetSmoothingMode(g, GP_SMOOTH_AA); pGdipSetTextRenderingHint(g, GP_TEXT_AA); pGdipSetPixelOffsetMode(g, GP_PIXOFF_HALF);
                pGdipTranslateWorldTransform(g, (REAL)-x0, (REAL)-y0, 0);
                fx_load(&fx0); C.g = g;
                g_skin_sel = 0; paint_skin(); g_skin_sel = -1;
                C.g = NULL;
                pGdipDeleteGraphics(g);
                L->h = g_rh; L->x0 = x0; L->y0 = y0; L->x1 = x1; L->y1 = y1; L->on = 1; L->def = g_f4_def;
                free(L->tiles); L->tiles = tiles; tiles = NULL; L->tw = tw; L->th = th;
                g_pre_w = w; g_pre_h = h;
                sgr_log("HUD F4 page drawn ahead (%dx%d)", lw, lh);
            }
            pGdipDisposeImage(bmp);
        }
    }
    free(tiles);
    g_hit_off = 0;
    memcpy(&g_ps, &keep_skw, sizeof g_ps);
    fx_load(&fx0); g_nglow = keep_nglow; g_wnhit = keep_nhit;
}

/* one picture of the game screen in layers; returns 1 when anything is shown */
static int paint_layers(int w, int h)
{
    LARGE_INTEGER f, t0, t1, t2, t3; QueryPerformanceFrequency(&f); QueryPerformanceCounter(&t0);
    g_wnhit = 0; g_wrad_r = 0; g_frame_live = 0; g_nglow = 0; g_glow_defer = 1;
    int ok = ctx_setup();
    if (!g_recg) {                               /* the record graphics: 1 x 1, measuring works, nothing drawn */
        static unsigned px; GpBitmap *b = NULL;
        if (pGdipCreateBitmapFromScan0(1, 1, 4, GP_PARGB, (BYTE *)&px, &b) == 0) pGdipGetImageGraphicsContext(b, &g_recg);
    }
    uint64_t nh[NPART]; int nb[NPART][4], non[NPART]; SideFx fx[NPART], after;
    int tw = (w + TILE - 1) / TILE, th = (h + TILE - 1) / TILE; size_t tn = (size_t)tw * th;
    if (NPART * tn > g_nt_cap) { free(g_nt); g_nt = (uint64_t *)malloc(NPART * tn * sizeof *g_nt); g_nt_cap = g_nt ? NPART * tn : 0; }
    for (int p = 0; p < NPART; p++) {
        non[p] = 0;
        if (!ok || !g_recg || !part_wanted(p)) continue;
        fx_save(&fx[p]);                             /* the state before this part (its raster starts from it) */
        C.g = g_recg;
        memset(&g_gst, 0, sizeof g_gst);
        pGdipSetSmoothingMode(C.g, GP_SMOOTH_AA); pGdipSetTextRenderingHint(C.g, GP_TEXT_AA); pGdipSetPixelOffsetMode(C.g, GP_PIXOFF_HALF);
        pGdipResetClip(C.g);
        g_rtile = g_nt ? g_nt + p * tn : NULL; g_rtw = tw; g_rth = th;
        if (g_rtile) memset(g_rtile, 0, tn * sizeof *g_rtile);
        g_rh = 14695981039346656037ULL ^ (uint64_t)(p >= P_SKIN0 && p < P_GLOW ? 1000 + g_ps.skw[p - P_SKIN0].def : p);
        g_rbany = 0; g_rball = 0; g_rec = 1;
        part_run(p);
        g_rec = 0; C.g = NULL; g_rtile = NULL;
        if (!g_rbany && !g_rball) continue;
        int x0 = g_rball ? 0 : (int)floorf(g_rbx0), y0 = g_rball ? 0 : (int)floorf(g_rby0);
        int x1 = g_rball ? w : (int)ceilf(g_rbx1), y1 = g_rball ? h : (int)ceilf(g_rby1);
        if (x0 < 0) x0 = 0; if (y0 < 0) y0 = 0; if (x1 > w) x1 = w; if (y1 > h) y1 = h;
        if (x1 <= x0 || y1 <= y0) continue;
        non[p] = 1; nh[p] = g_rh; nb[p][0] = x0; nb[p][1] = y0; nb[p][2] = x1; nb[p][3] = y1;
    }
    fx_save(&after);
    QueryPerformanceCounter(&t1);
    /* draw the changed parts into their layers: in the tiles that changed (step 4), or all of it when its place / size
       changed, it is new, or most of it changed */
    RECT dirty[NPART * 2 + 64]; int nd = 0, nras = 0;
    for (int p = 0; p < NPART; p++) {
        Layer *L = &g_L[p];
        int fresh = 0;                              /* a kept page brought back: all of it is new on screen */
        if (p >= P_SKIN0 && p < P_GLOW) {
            int d = non[p] ? g_ps.skw[p - P_SKIN0].def : -1;
            if (L->on && L->def != d && L->def >= 0 && L->def < NPAGE) {   /* its window closed: keep the page */
                SetRect(&dirty[nd++], L->x0, L->y0, L->x1, L->y1);
                Layer t = g_page[L->def]; g_page[L->def] = *L; *L = t; L->on = 0;
            }
            if (!L->on && d >= 0 && d < NPAGE && g_page[d].on) {   /* opened again: its kept page */
                Layer t = *L; *L = g_page[d]; g_page[d] = t; g_page[d].on = 0; fresh = 1;
            }
        }
        int samebox = non[p] && L->on && nb[p][0] == L->x0 && nb[p][1] == L->y0 && nb[p][2] == L->x1 && nb[p][3] == L->y1;
        if (non[p] == L->on && (!non[p] || (samebox && nh[p] == L->h))) {   /* unchanged */
            if (fresh) SetRect(&dirty[nd++], L->x0, L->y0, L->x1, L->y1);
            continue;
        }
        if (!non[p]) { SetRect(&dirty[nd++], L->x0, L->y0, L->x1, L->y1); L->on = 0; continue; }   /* gone */
        uint64_t *nt = g_nt ? g_nt + p * tn : NULL;
        /* the changed tiles, as rectangles (runs in a row, grown down while the next row has the same run) */
        RECT tr[48]; int ntr = 0, part = samebox && nt && L->tiles && L->tw == tw && L->th == th;
        long long area = 0, larea = (long long)(nb[p][2] - nb[p][0]) * (nb[p][3] - nb[p][1]);
        if (part) {
            int tx0 = nb[p][0] / TILE, ty0 = nb[p][1] / TILE, tx1 = (nb[p][2] - 1) / TILE, ty1 = (nb[p][3] - 1) / TILE;
            for (int y = ty0; y <= ty1 && part; y++) {
                for (int x = tx0; x <= tx1 && part; x++) {
                    if (nt[y * tw + x] == L->tiles[y * tw + x]) continue;
                    int xe = x; while (xe + 1 <= tx1 && nt[y * tw + xe + 1] != L->tiles[y * tw + xe + 1]) xe++;
                    RECT r; SetRect(&r, x * TILE, y * TILE, (xe + 1) * TILE, (y + 1) * TILE);
                    if (r.left < nb[p][0]) r.left = nb[p][0]; if (r.top < nb[p][1]) r.top = nb[p][1];
                    if (r.right > nb[p][2]) r.right = nb[p][2]; if (r.bottom > nb[p][3]) r.bottom = nb[p][3];
                    int k; for (k = 0; k < ntr; k++)       /* the same run in the row above: grow it */
                        if (tr[k].left == r.left && tr[k].right == r.right && tr[k].bottom == r.top) { tr[k].bottom = r.bottom; break; }
                    if (k == ntr) { if (ntr == 48) part = 0; else tr[ntr++] = r; }
                    area += (long long)(r.right - r.left) * (r.bottom - r.top);
                    x = xe;
                }
            }
            if (part && (ntr == 0 || area * 10 > larea * 6)) part = ntr == 0 ? 2 : 0;   /* nothing / most of it: see below */
        }
        if (part == 2) { L->h = nh[p]; if (fresh) SetRect(&dirty[nd++], L->x0, L->y0, L->x1, L->y1); continue; }   /* hash moved, no tile did */
        int lw = nb[p][2] - nb[p][0], lh = nb[p][3] - nb[p][1];
        if (!part) {
            if (L->on) SetRect(&dirty[nd++], L->x0, L->y0, L->x1, L->y1);
            L->on = 0;
            size_t need = (size_t)lw * lh;
            if (need > L->cap) { free(L->buf); L->buf = (unsigned *)malloc(need * 4); L->cap = L->buf ? need : 0; }
            if (!L->buf) continue;
            memset(L->buf, 0, need * 4);
        } else {
            for (int k = 0; k < ntr; k++)           /* only those rectangles are drawn again */
                for (int y = tr[k].top; y < tr[k].bottom; y++)
                    memset(L->buf + (size_t)(y - nb[p][1]) * lw + (tr[k].left - nb[p][0]), 0, (size_t)(tr[k].right - tr[k].left) * 4);
        }
        GpBitmap *bmp = NULL; GpGraphics *g = NULL; GpPath *clip = NULL;
        if (pGdipCreateBitmapFromScan0(lw, lh, lw * 4, GP_PARGB, (BYTE *)L->buf, &bmp) != 0) continue;
        if (pGdipGetImageGraphicsContext(bmp, &g) != 0) { pGdipDisposeImage(bmp); continue; }
        pGdipSetSmoothingMode(g, GP_SMOOTH_AA); pGdipSetTextRenderingHint(g, GP_TEXT_AA); pGdipSetPixelOffsetMode(g, GP_PIXOFF_HALF);
        pGdipTranslateWorldTransform(g, (REAL)-nb[p][0], (REAL)-nb[p][1], 0);
        if (part && pGdipCreatePath(GP_FILL_ALT, &clip) == 0) {
            for (int k = 0; k < ntr; k++)
                pGdipAddPathRectangle(clip, (REAL)tr[k].left, (REAL)tr[k].top, (REAL)(tr[k].right - tr[k].left), (REAL)(tr[k].bottom - tr[k].top));
            r_GdipSetClipPath(g, clip, GP_COMBINE_REPLACE);
            g_rasg = g; g_rasclip = clip;
            g_nrasr = ntr; memcpy(g_rasr, tr, sizeof(RECT) * ntr);
        }
        fx_load(&fx[p]); g_hit_off = 1; C.g = g;
        part_run(p);
        C.g = NULL; g_hit_off = 0; g_rasg = NULL; g_rasclip = NULL;
        if (clip) pGdipDeletePath(clip);
        pGdipDeleteGraphics(g); pGdipDisposeImage(bmp);
        L->h = nh[p]; L->x0 = nb[p][0]; L->y0 = nb[p][1]; L->x1 = nb[p][2]; L->y1 = nb[p][3]; L->on = 1;
        L->def = p >= P_SKIN0 && p < P_GLOW ? g_ps.skw[p - P_SKIN0].def : -1;
        if (fresh) { SetRect(&dirty[nd++], L->x0, L->y0, L->x1, L->y1); pf_tiled += part ? 1 : 0; }
        else if (part) { for (int k = 0; k < ntr && nd < (int)(sizeof dirty / sizeof *dirty); k++) dirty[nd++] = tr[k]; pf_tiled++;
}
        else SetRect(&dirty[nd++], L->x0, L->y0, L->x1, L->y1);
        if (nt) {                                   /* keep this picture's tiles */
            if (!L->tiles || L->tw != tw || L->th != th) { free(L->tiles); L->tiles = (uint64_t *)malloc(tn * sizeof *L->tiles); L->tw = L->tiles ? tw : 0; L->th = L->tiles ? th : 0; }
            if (L->tiles) memcpy(L->tiles, nt, tn * sizeof *nt);
        }
        nras++;
    }
    fx_load(&after);
    if (!nras && ok && !g_ps.covered) { g_stage_paint = "predraw_f4"; predraw_f4(w, h, tw, th); }
    g_glow_defer = 0;
    g_stage_paint = "done";
    QueryPerformanceCounter(&t2);
    int has = 0;
    for (int p = 0; p < NPART; p++) has |= g_L[p].on;
    /* compose + queue (lock: the presenter reads g_fbuf) */
    long long dpx = 0;
    EnterCriticalSection(&g_lock);
    if (g_fw != w || g_fh != h || !g_fbuf) {
        free(g_fbuf); g_fbuf = (unsigned *)calloc((size_t)w * h, 4); g_fw = g_fbuf ? w : 0; g_fh = g_fbuf ? h : 0;
        g_full_next = 1;
    }
    {   /* (14:40) the open rectangles of this picture; a change recomposes the whole picture */
        RECT nh[4]; int nn = 0;
        for (int i = 0; i < g_ps.nfh && i < 4; i++)
            SetRect(&nh[nn++], (int)X(fx_ref(g_ps.fh[i][0])), (int)Y(fy_ref(g_ps.fh[i][1])), (int)(X(fx_ref(g_ps.fh[i][2])) + 0.999f), (int)(Y(fy_ref(g_ps.fh[i][3])) + 0.999f));
        if (nn != g_nfhole || memcmp(nh, g_fhole, sizeof(RECT) * nn)) { memcpy(g_fhole, nh, sizeof(RECT) * nn); g_nfhole = nn; g_full_next = 1; }
    }
    if (g_fbuf) {
        if (g_full_next) { nd = 1; SetRect(&dirty[0], 0, 0, w, h); g_full_next = 0; }
        for (int i = 0; i < nd; i++) {
            RECT r = dirty[i];
            if (r.left < 0) r.left = 0; if (r.top < 0) r.top = 0; if (r.right > w) r.right = w; if (r.bottom > h) r.bottom = h;
            if (r.right <= r.left || r.bottom <= r.top) continue;
            compose_rect(&r); pend_add(&r);
            dpx += (long long)(r.right - r.left) * (r.bottom - r.top);
        }
    }
    g_rhas = has && g_fbuf;
    LeaveCriticalSection(&g_lock);
    QueryPerformanceCounter(&t3);
    double fq = (double)f.QuadPart / 1000.0;
    pf_rec += (t1.QuadPart - t0.QuadPart) / fq; pf_ras += (t2.QuadPart - t1.QuadPart) / fq; pf_cmp += (t3.QuadPart - t2.QuadPart) / fq;
    pf_dirty += dpx; pf_parts += nras; pf_n++;
    return has;
}

static DWORD WINAPI painter(LPVOID p)
{
    (void)p;
    g_rec_tid = GetCurrentThreadId();
    for (;;) {
        WaitForSingleObject(g_evt, INFINITE);
        int w = g_ps_w, h = g_ps_h, has = 0;
        if (g_layers_on < 0) g_layers_on = GetPrivateProfileIntA("hud", "layers", 1, ".\\GORender.ini") != 0;
        { static int pre; if (!pre) { pre = 1; for (int k = 0; k < 3; k++) atlas(k); } }   /* (11-01) F4's art loaded ahead */
        if (w > 0 && h > 0 && !g_ps.lg && g_layers_on) {
            has = paint_layers(w, h);
        } else if (w > 0 && h > 0) {             /* the login screen (or layers=0): one full picture as before */
            g_glow_defer = 0;
            if (w != g_bw || h != g_bh) { free(g_wbuf); g_wbuf = (unsigned *)malloc((size_t)w * h * 4); g_bw = g_wbuf ? w : 0; g_bh = g_wbuf ? h : 0; }
            if (g_wbuf) {
                memset(g_wbuf, 0, (size_t)w * h * 4);
                has = paint_inner(g_wbuf, w, h);
                EnterCriticalSection(&g_lock);
                if (g_fw != w || g_fh != h || !g_fbuf) { free(g_fbuf); g_fbuf = (unsigned *)malloc((size_t)w * h * 4); g_fw = g_fbuf ? w : 0; g_fh = g_fbuf ? h : 0; }
                if (g_fbuf) { memcpy(g_fbuf, g_wbuf, (size_t)w * h * 4); g_pend_full = 1; g_npend = 0; }
                g_rhas = has && g_fbuf;
                LeaveCriticalSection(&g_lock);
            }
            /* back in the game: every layer drawn anew, all composed - (11-01 14:40) after the options opened in the game
               the layers still hold the game's HUD (it did not change meanwhile): composed again only, so the HUD is
               back at once on OK / Cancel */
            if (g_ps.lg_game) g_full_next = 1; else layer_reset_all();
        }
        if (pf_n && GetTickCount() - pf_t0 >= 15000) {
            if (pf_t0) sgr_log("HUD perf: %d pictures - record %.1f ms, draw %.1f ms (%.1f parts), compose %.1f ms, dirty %.1f%% of %dx%d, "
                               "overlay copies %.1f%% (averages per picture); %d drawn in changed tiles only", pf_n, pf_rec / pf_n, pf_ras / pf_n, (double)pf_parts / pf_n,
                               pf_cmp / pf_n, 100.0 * pf_dirty / pf_n / ((double)w * h + 1), w, h, 100.0 * pf_copy / pf_n / ((double)w * h + 1), pf_tiled);
            pf_rec = pf_ras = pf_cmp = 0; pf_dirty = pf_copy = 0; pf_n = pf_parts = pf_tiled = 0; pf_t0 = GetTickCount();
        }
        EnterCriticalSection(&g_lock);
        memcpy(g_hits, g_whits, sizeof g_hits); g_nhit = g_wnhit;
        g_rad_cx = g_wrad_cx; g_rad_cy = g_wrad_cy; g_rad_r = g_wrad_r; g_pubC = C;
        g_pub_mapw = g_ps.mapw; g_pub_maph = g_ps.maph; g_pub_lg = has ? g_ps.lg : 0;
        g_pub_cov = g_ps.covered; g_pub_cdlg = g_ps.chat_dlg; g_pub_lgv = has ? g_ps.lg : 0;   /* (14:40) the game's chat follows the shown picture */
        g_pub_nw = 0;                                     /* (11-01 14:40) the windows whose page this picture has */
        for (int i = 0; i < g_ps.nskw && i < 8; i++) g_pub_wins[g_pub_nw++] = g_ps.skw[i].wp;
        LeaveCriticalSection(&g_lock);
        g_ready = 1;
        g_busy = 0;
    }
    return 0;
}

static int painter_start(void)
{
    if (g_thr) return 1;
    InitializeCriticalSection(&g_lock);
    g_evt = CreateEventA(NULL, FALSE, FALSE, NULL);
    g_thr = g_evt ? CreateThread(NULL, 0, painter, NULL, 0, NULL) : NULL;
    if (g_thr) SetThreadPriority(g_thr, THREAD_PRIORITY_BELOW_NORMAL);
    return g_thr != NULL;
}

/* game thread: start a repaint when the painter is free */
static int request_paint(void)
{
    if (g_busy) return 0;
    RECT c; GetClientRect(g_disp.hwnd, &c);
    g_ps = g_st;
    g_ps_hover_kind = g_hover_kind; g_ps_hover_arg = g_hover_arg;
    g_ps_dest = g_disp.dest; g_ps_w = c.right; g_ps_h = c.bottom;
    g_busy = 1;
    SetEvent(g_evt);
    return 1;
}

/* presenter (game thread): bring the overlay up to date - only the rectangles that changed since it last took them
   (step 3); ov->dx0..dy1 = their union for the texture upload */
void sghud_overlay_lost(void) { g_ov_sync = 0; }
int sghud_paint(SGOverlay *ov)
{
    int r = 0;
    ov->dx0 = ov->dy0 = ov->dx1 = ov->dy1 = 0;
    if (!g_thr) return 0;
    EnterCriticalSection(&g_lock);
    if (g_fbuf && g_rhas && g_fw == ov->w && g_fh == ov->h) {
        if (!g_ov_sync || g_ov_bits != ov->bits || g_pend_full) {
            memcpy(ov->bits, g_fbuf, (size_t)ov->w * ov->h * 4);
            ov->dx1 = ov->w; ov->dy1 = ov->h;
            pf_copy += (long long)ov->w * ov->h;
        } else if (g_npend) {
            RECT u = g_pend[0];
            for (int i = 0; i < g_npend; i++) {
                const RECT *q = &g_pend[i];
                for (int y = q->top; y < q->bottom; y++)
                    memcpy(ov->bits + (size_t)y * ov->w + q->left, g_fbuf + (size_t)y * g_fw + q->left, (size_t)(q->right - q->left) * 4);
                pf_copy += (long long)(q->right - q->left) * (q->bottom - q->top);
                UnionRect(&u, &u, q);
            }
            ov->dx0 = u.left; ov->dy0 = u.top; ov->dx1 = u.right; ov->dy1 = u.bottom;
        }
        g_npend = 0; g_pend_full = 0; g_ov_sync = 1; g_ov_bits = ov->bits;
        r = 1;
    } else g_ov_sync = 0;
    LeaveCriticalSection(&g_lock);
    return r;
}
