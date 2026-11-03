/* sghud_rec.h - the HUD's draw-call recorder (user 2026-11-01 "HUD architecture, steps 1-3").
 *
 * The HUD is drawn in parts (band, cards, radar, every re-skinned window, the controls, the tips).  Each frame every
 * part is first run in RECORD mode: its GDI+ draw calls on the record graphics are not executed, they are hashed
 * (64-bit FNV of the call, its arguments and the content of the brushes / pens / paths / fonts / formats / strings /
 * points they use) and their bounds are collected.  Only a part whose hash or bounds changed is drawn for real (into
 * its own layer), and only the changed rectangles are composed, copied to the overlay and uploaded.
 *
 * The real GDI+ entry points stay in r_*; pGdip* point at the wrappers once rec_install() ran.  Object calls
 * (create / set colour / path figures / string format) always run for real and keep a content hash per object, so a
 * draw call hashes WHAT it draws, not the address of a brush that is reused with another colour. */
#ifndef SGHUD_REC_H
#define SGHUD_REC_H
#include <stdint.h>

static int g_rec;                    /* 1: draw calls on g_recg are recorded, not drawn */
static GpGraphics *g_recg;           /* the record graphics (a 1 x 1 bitmap: measuring works, nothing is drawn) */
static uint64_t g_rh;                /* the running hash of the part being recorded */
static float g_rbx0, g_rby0, g_rbx1, g_rby1; static int g_rbany, g_rball;   /* its bounds (client pixels) */
static unsigned g_rcalls;            /* draw calls recorded (perf) */
static uint64_t g_ch;                /* the hash of the draw call being recorded */
static float g_cx0, g_cy0, g_cx1, g_cy1; static int g_call_all;            /* its bounds */
/* (step 4, 11-01) tiles: every draw call's hash also goes into the 64 x 64 screen tiles its bounds touch, so a part
   that changed is drawn again only in the tiles that changed (clipped), not in all of its layer */
#define TILE 64
static uint64_t *g_rtile; static int g_rtw, g_rth;   /* the tiles of the part being recorded (screen grid) */
/* the graphics state that changes what later draw calls give (clip, modes) */
static struct { int smooth, text, pix, interp; uint64_t clip; } g_gst;

static inline void rh_bytes(const void *p, size_t n)
{
    const unsigned char *b = (const unsigned char *)p;
    uint64_t h = g_ch;
    for (size_t i = 0; i < n; i++) { h ^= b[i]; h *= 1099511628211ULL; }
    g_ch = h;
}
static inline void rh_u(uint64_t v) { rh_bytes(&v, sizeof v); }
static inline void rh_f(float v) { rh_bytes(&v, sizeof v); }
static inline uint64_t hmix(uint64_t a, const void *p, size_t n)
{
    const unsigned char *b = (const unsigned char *)p;
    for (size_t i = 0; i < n; i++) { a ^= b[i]; a *= 1099511628211ULL; }
    return a;
}

/* object content hashes (+ a pen's width, a path's bounds) */
typedef struct { const void *p; uint64_t h; float w; float x0, y0, x1, y1; int has; int st[4]; } RecObj;   /* st: settable state */
static RecObj g_obj[1024];
static DWORD g_rec_tid;              /* the painter thread: the object table is only kept there (the cursor and the
                                        image loads draw with GDI+ on other threads) */
static RecObj g_obj_dummy;
static RecObj *obj_slot(const void *p, int make)
{
    if (GetCurrentThreadId() != g_rec_tid) { memset(&g_obj_dummy, 0, sizeof g_obj_dummy); return make ? &g_obj_dummy : NULL; }
    unsigned i = (unsigned)(((uintptr_t)p >> 3) * 2654435761u) & 1023;
    for (int k = 0; k < 1024; k++, i = (i + 1) & 1023) {
        if (g_obj[i].p == p) return &g_obj[i];
        if (!g_obj[i].p) {
            if (!make) return NULL;
            memset(&g_obj[i], 0, sizeof g_obj[i]); g_obj[i].p = p; g_obj[i].h = 1469598103934665603ULL ^ (uintptr_t)p;
            return &g_obj[i];
        }
    }
    if (!make) return NULL;
    memset(g_obj, 0, sizeof g_obj);       /* full (should never happen): start over */
    return obj_slot(p, 1);
}
static uint64_t obj_h(const void *p) { RecObj *o = p ? obj_slot(p, 0) : NULL; return o ? hmix(o->h, o->st, sizeof o->st) : (uint64_t)(uintptr_t)p; }
static void obj_set(const void *p, uint64_t h) { RecObj *o = obj_slot(p, 1); o->h = h; memset(o->st, 0, sizeof o->st); }
static void obj_st(const void *p, int k, int v) { obj_slot(p, 1)->st[k] = v; }
static void obj_free(const void *p)
{   /* removing from open addressing: rehash the cluster after it */
    RecObj *o = p ? obj_slot(p, 0) : NULL;
    if (!o || o == &g_obj_dummy) return;
    unsigned i = (unsigned)(o - g_obj);
    o->p = NULL;
    for (unsigned j = (i + 1) & 1023; g_obj[j].p; j = (j + 1) & 1023) {
        RecObj t = g_obj[j]; g_obj[j].p = NULL;
        RecObj *n = obj_slot(t.p, 1); *n = t;
    }
}

static int g_cany;
static void rb_add(float x0, float y0, float x1, float y1, float pad)
{
    if (x1 < x0) { float t = x0; x0 = x1; x1 = t; }
    if (y1 < y0) { float t = y0; y0 = y1; y1 = t; }
    x0 -= pad; y0 -= pad; x1 += pad; y1 += pad;
    if (!g_cany) { g_cx0 = x0; g_cy0 = y0; g_cx1 = x1; g_cy1 = y1; g_cany = 1; }
    else { if (x0 < g_cx0) g_cx0 = x0; if (y0 < g_cy0) g_cy0 = y0; if (x1 > g_cx1) g_cx1 = x1; if (y1 > g_cy1) g_cy1 = y1; }
    if (!g_rbany) { g_rbx0 = x0; g_rby0 = y0; g_rbx1 = x1; g_rby1 = y1; g_rbany = 1; return; }
    if (x0 < g_rbx0) g_rbx0 = x0; if (y0 < g_rby0) g_rby0 = y0;
    if (x1 > g_rbx1) g_rbx1 = x1; if (y1 > g_rby1) g_rby1 = y1;
}
/* a draw call is complete: with the graphics state into the part's hash and into the tiles it touches */
static GpStatus rec_end(void)
{
    g_ch = hmix(g_ch, &g_gst, sizeof g_gst);
    { uint64_t c = g_ch; g_rh = hmix(g_rh, &c, sizeof c); }
    if (g_rtile) {
        int tx0, ty0, tx1, ty1;
        if (g_call_all || g_rball || !g_cany) { tx0 = 0; ty0 = 0; tx1 = g_rtw - 1; ty1 = g_rth - 1; }
        else {
            tx0 = (int)floorf(g_cx0) / TILE; ty0 = (int)floorf(g_cy0) / TILE; tx1 = (int)ceilf(g_cx1) / TILE; ty1 = (int)ceilf(g_cy1) / TILE;
            if (tx0 < 0) tx0 = 0; if (ty0 < 0) ty0 = 0; if (tx1 >= g_rtw) tx1 = g_rtw - 1; if (ty1 >= g_rth) ty1 = g_rth - 1;
        }
        for (int y = ty0; y <= ty1; y++) for (int x = tx0; x <= tx1; x++) g_rtile[y * g_rtw + x] = hmix(g_rtile[y * g_rtw + x], &g_ch, sizeof g_ch);
    }
    g_cany = 0; g_call_all = 0;
    return 0;
}
static void rb_pts(const GpPointF *p, int n, float pad) { for (int i = 0; i < n; i++) rb_add(p[i].X, p[i].Y, p[i].X, p[i].Y, pad); }
static float pen_pad(const void *pen) { RecObj *o = pen ? obj_slot(pen, 0) : NULL; return (o ? o->w : 4) / 2 + 2; }
#define REC_ON(g) (g_rec && (g) == g_recg)
#define REC_CALL(id) (g_rcalls++, g_ch = 14695981039346656037ULL, g_cany = 0, g_call_all = 0, rh_u((uint64_t)(id) * 0x9E3779B97F4A7C15ULL))

/* the real entry points */
#define GDIP_REAL(ret, name, args) static ret (WINAPI *r_##name) args;
GDIP_FUNCS(GDIP_REAL)

/* ---- graphics state (always real; hashed when recording) */
/* the layer being drawn again in some tiles only: its graphics and the clip of those tiles (the part's own clip
   calls are kept inside it) */
static GpGraphics *g_rasg; static GpPath *g_rasclip;
#define RAS_CLIP(g) ((g) == g_rasg && g_rasclip)
static RECT g_rasr[48]; static int g_nrasr;           /* those tiles (screen = world coordinates) */
/* a draw call whose bounds miss every tile being drawn again is not given to GDI+ at all (clipping alone still
   costs its set-up and, for text, its layout) */
static int ras_skip(GpGraphics *g, float x0, float y0, float x1, float y1, float pad)
{
    if (!RAS_CLIP(g)) return 0;
    if (x1 < x0) { float t = x0; x0 = x1; x1 = t; }
    if (y1 < y0) { float t = y0; y0 = y1; y1 = t; }
    x0 -= pad; y0 -= pad; x1 += pad; y1 += pad;
    for (int i = 0; i < g_nrasr; i++)
        if (x1 > g_rasr[i].left && x0 < g_rasr[i].right && y1 > g_rasr[i].top && y0 < g_rasr[i].bottom) return 0;
    return 1;
}
static int ras_skip_pts(GpGraphics *g, const GpPointF *p, int n, float pad)
{
    if (!RAS_CLIP(g) || n <= 0) return 0;
    float x0 = p[0].X, y0 = p[0].Y, x1 = x0, y1 = y0;
    for (int i = 1; i < n; i++) { if (p[i].X < x0) x0 = p[i].X; if (p[i].X > x1) x1 = p[i].X; if (p[i].Y < y0) y0 = p[i].Y; if (p[i].Y > y1) y1 = p[i].Y; }
    return ras_skip(g, x0, y0, x1, y1, pad);
}
static GpStatus WINAPI w_SetSmoothingMode(GpGraphics *g, INT m) { if (REC_ON(g)) g_gst.smooth = m; return r_GdipSetSmoothingMode(g, m); }
static GpStatus WINAPI w_SetTextRenderingHint(GpGraphics *g, INT m) { if (REC_ON(g)) g_gst.text = m; return r_GdipSetTextRenderingHint(g, m); }
static GpStatus WINAPI w_SetPixelOffsetMode(GpGraphics *g, INT m) { if (REC_ON(g)) g_gst.pix = m; return r_GdipSetPixelOffsetMode(g, m); }
static GpStatus WINAPI w_SetInterpolationMode(GpGraphics *g, INT m) { if (REC_ON(g)) g_gst.interp = m; return r_GdipSetInterpolationMode(g, m); }
static GpStatus WINAPI w_SetClipPath(GpGraphics *g, GpPath *p, INT m)
{
    if (REC_ON(g)) { uint64_t h[3] = { m ? g_gst.clip : 0, obj_h(p), (uint64_t)m }; g_gst.clip = hmix(5, h, sizeof h); }
    if (RAS_CLIP(g) && m == GP_COMBINE_REPLACE) { r_GdipSetClipPath(g, g_rasclip, GP_COMBINE_REPLACE); return r_GdipSetClipPath(g, p, 1); }
    return r_GdipSetClipPath(g, p, m);
}
static GpStatus WINAPI w_SetClipRect(GpGraphics *g, REAL x, REAL y, REAL w, REAL h, INT m)
{
    if (REC_ON(g)) { float v[4] = { x, y, w, h }; uint64_t a = hmix(m ? g_gst.clip : 0, v, sizeof v); g_gst.clip = hmix(a ^ 6, &m, sizeof m); }
    if (RAS_CLIP(g) && m == GP_COMBINE_REPLACE) { r_GdipSetClipPath(g, g_rasclip, GP_COMBINE_REPLACE); return r_GdipSetClipRect(g, x, y, w, h, 1); }
    return r_GdipSetClipRect(g, x, y, w, h, m);
}
static GpStatus WINAPI w_ResetClip(GpGraphics *g)
{
    if (REC_ON(g)) g_gst.clip = 0;
    if (RAS_CLIP(g)) return r_GdipSetClipPath(g, g_rasclip, GP_COMBINE_REPLACE);
    return r_GdipResetClip(g);
}

/* ---- objects (always real; their content hash follows them) */
static GpStatus WINAPI w_CreateSolidFill(ARGB c, GpSolidFill **b)
{ GpStatus s = r_GdipCreateSolidFill(c, b); if (!s && *b) obj_set(*b, hmix(11, &c, sizeof c)); return s; }
static GpStatus WINAPI w_SetSolidFillColor(GpSolidFill *b, ARGB c)
{ obj_set(b, hmix(11, &c, sizeof c)); return r_GdipSetSolidFillColor(b, c); }
static GpStatus WINAPI w_DeleteBrush(GpBrush *b) { obj_free(b); return r_GdipDeleteBrush(b); }
static GpStatus WINAPI w_CreateLineBrush(const GpPointF *a, const GpPointF *b, ARGB c1, ARGB c2, INT wrap, GpLineGradient **o)
{
    GpStatus s = r_GdipCreateLineBrush(a, b, c1, c2, wrap, o);
    if (!s && *o) { uint64_t h = hmix(12, a, sizeof *a); h = hmix(h, b, sizeof *b); h = hmix(h, &c1, 4); h = hmix(h, &c2, 4); h = hmix(h, &wrap, 4); obj_set(*o, h); }
    return s;
}
static GpStatus WINAPI w_CreatePen1(ARGB c, REAL w, INT u, GpPen **o)
{
    GpStatus s = r_GdipCreatePen1(c, w, u, o);
    if (!s && *o) { uint64_t h = hmix(13, &c, 4); h = hmix(h, &w, 4); h = hmix(h, &u, 4); obj_set(*o, h); obj_slot(*o, 1)->w = w; }
    return s;
}
static GpStatus WINAPI w_DeletePen(GpPen *p) { obj_free(p); return r_GdipDeletePen(p); }
static GpStatus WINAPI w_SetPenLineCap197819(GpPen *p, INT a, INT b, INT c)
{ obj_st(p, 0, a | b << 8 | c << 16); return r_GdipSetPenLineCap197819(p, a, b, c); }
static GpStatus WINAPI w_SetPenLineJoin(GpPen *p, INT a) { obj_st(p, 1, a); return r_GdipSetPenLineJoin(p, a); }
static GpStatus WINAPI w_SetPenDashStyle(GpPen *p, INT a) { obj_st(p, 2, a); return r_GdipSetPenDashStyle(p, a); }
static GpStatus WINAPI w_CreatePath(INT f, GpPath **o)
{ GpStatus s = r_GdipCreatePath(f, o); if (!s && *o) { RecObj *r = obj_slot(*o, 1); r->h = hmix(17, &f, 4); r->has = 0; } return s; }
static GpStatus WINAPI w_DeletePath(GpPath *p) { obj_free(p); return r_GdipDeletePath(p); }
static void path_pt(RecObj *o, float x, float y)
{
    if (!o->has) { o->x0 = o->x1 = x; o->y0 = o->y1 = y; o->has = 1; return; }
    if (x < o->x0) o->x0 = x; if (x > o->x1) o->x1 = x; if (y < o->y0) o->y0 = y; if (y > o->y1) o->y1 = y;
}
static GpStatus WINAPI w_StartPathFigure(GpPath *p) { RecObj *o = obj_slot(p, 1); o->h = hmix(o->h, "S", 1); return r_GdipStartPathFigure(p); }
static GpStatus WINAPI w_ClosePathFigure(GpPath *p) { RecObj *o = obj_slot(p, 1); o->h = hmix(o->h, "C", 1); return r_GdipClosePathFigure(p); }
static GpStatus WINAPI w_AddPathLine(GpPath *p, REAL a, REAL b, REAL c, REAL d)
{ RecObj *o = obj_slot(p, 1); float v[4] = { a, b, c, d }; o->h = hmix(o->h ^ 18, v, sizeof v); path_pt(o, a, b); path_pt(o, c, d); return r_GdipAddPathLine(p, a, b, c, d); }
static GpStatus WINAPI w_AddPathBezier(GpPath *p, REAL a, REAL b, REAL c, REAL d, REAL e, REAL f, REAL g, REAL h)
{
    RecObj *o = obj_slot(p, 1); float v[8] = { a, b, c, d, e, f, g, h }; o->h = hmix(o->h ^ 19, v, sizeof v);
    for (int i = 0; i < 8; i += 2) path_pt(o, v[i], v[i + 1]);
    return r_GdipAddPathBezier(p, a, b, c, d, e, f, g, h);
}
static GpStatus WINAPI w_AddPathEllipse(GpPath *p, REAL x, REAL y, REAL w, REAL h)
{ RecObj *o = obj_slot(p, 1); float v[4] = { x, y, w, h }; o->h = hmix(o->h ^ 20, v, sizeof v); path_pt(o, x, y); path_pt(o, x + w, y + h); return r_GdipAddPathEllipse(p, x, y, w, h); }
static GpStatus WINAPI w_CreateFont(const GpFontFamily *fam, REAL sz, INT st, INT u, GpFont **o)
{
    GpStatus s = r_GdipCreateFont(fam, sz, st, u, o);
    if (!s && *o) { uint64_t h = hmix(21, &fam, sizeof fam); h = hmix(h, &sz, 4); h = hmix(h, &st, 4); h = hmix(h, &u, 4); obj_set(*o, h); }
    return s;
}
static GpStatus WINAPI w_DeleteFont(GpFont *f) { obj_free(f); return r_GdipDeleteFont(f); }
static GpStatus WINAPI w_CreateStringFormat(INT fl, LANGID l, GpStringFormat **o)
{ GpStatus s = r_GdipCreateStringFormat(fl, l, o); if (!s && *o) { int v[2] = { fl, l }; obj_set(*o, hmix(22, v, sizeof v)); } return s; }
static GpStatus WINAPI w_DeleteStringFormat(GpStringFormat *f) { obj_free(f); return r_GdipDeleteStringFormat(f); }
static GpStatus WINAPI w_SetStringFormatAlign(GpStringFormat *f, INT a) { obj_st(f, 0, a); return r_GdipSetStringFormatAlign(f, a); }
static GpStatus WINAPI w_SetStringFormatLineAlign(GpStringFormat *f, INT a) { obj_st(f, 1, a); return r_GdipSetStringFormatLineAlign(f, a); }
static GpStatus WINAPI w_SetStringFormatFlags(GpStringFormat *f, INT a) { obj_st(f, 2, a); return r_GdipSetStringFormatFlags(f, a); }
static GpStatus WINAPI w_SetStringFormatTrimming(GpStringFormat *f, INT a) { obj_st(f, 3, a); return r_GdipSetStringFormatTrimming(f, a); }
/* setters keep the LAST value of each property (st[]): an object set to the same state hashes the same however often
   it was set; path figures accumulate (a path is built once, then drawn) */

/* ---- draw calls: recorded (hash + bounds) on the record graphics, drawn anywhere else */
static GpStatus WINAPI w_FillRectangle(GpGraphics *g, GpBrush *b, REAL x, REAL y, REAL w, REAL h)
{ if (!REC_ON(g)) return ras_skip(g, x, y, x + w, y + h, 2) ? 0 : r_GdipFillRectangle(g, b, x, y, w, h); REC_CALL(40); rh_u(obj_h(b)); rh_f(x); rh_f(y); rh_f(w); rh_f(h); rb_add(x, y, x + w, y + h, 2); return rec_end(); }
static GpStatus WINAPI w_DrawRectangle(GpGraphics *g, GpPen *p, REAL x, REAL y, REAL w, REAL h)
{ if (!REC_ON(g)) return ras_skip(g, x, y, x + w, y + h, pen_pad(p)) ? 0 : r_GdipDrawRectangle(g, p, x, y, w, h); REC_CALL(41); rh_u(obj_h(p)); rh_f(x); rh_f(y); rh_f(w); rh_f(h); rb_add(x, y, x + w, y + h, pen_pad(p)); return rec_end(); }
static GpStatus WINAPI w_FillEllipse(GpGraphics *g, GpBrush *b, REAL x, REAL y, REAL w, REAL h)
{ if (!REC_ON(g)) return ras_skip(g, x, y, x + w, y + h, 2) ? 0 : r_GdipFillEllipse(g, b, x, y, w, h); REC_CALL(42); rh_u(obj_h(b)); rh_f(x); rh_f(y); rh_f(w); rh_f(h); rb_add(x, y, x + w, y + h, 2); return rec_end(); }
static GpStatus WINAPI w_DrawEllipse(GpGraphics *g, GpPen *p, REAL x, REAL y, REAL w, REAL h)
{ if (!REC_ON(g)) return ras_skip(g, x, y, x + w, y + h, pen_pad(p)) ? 0 : r_GdipDrawEllipse(g, p, x, y, w, h); REC_CALL(43); rh_u(obj_h(p)); rh_f(x); rh_f(y); rh_f(w); rh_f(h); rb_add(x, y, x + w, y + h, pen_pad(p)); return rec_end(); }
static GpStatus WINAPI w_DrawArc(GpGraphics *g, GpPen *p, REAL x, REAL y, REAL w, REAL h, REAL a, REAL s)
{ if (!REC_ON(g)) return ras_skip(g, x, y, x + w, y + h, pen_pad(p)) ? 0 : r_GdipDrawArc(g, p, x, y, w, h, a, s); REC_CALL(44); rh_u(obj_h(p)); rh_f(x); rh_f(y); rh_f(w); rh_f(h); rh_f(a); rh_f(s); rb_add(x, y, x + w, y + h, pen_pad(p)); return rec_end(); }
static GpStatus WINAPI w_DrawLine(GpGraphics *g, GpPen *p, REAL a, REAL b, REAL c, REAL d)
{ if (!REC_ON(g)) return ras_skip(g, a, b, c, d, pen_pad(p)) ? 0 : r_GdipDrawLine(g, p, a, b, c, d); REC_CALL(45); rh_u(obj_h(p)); rh_f(a); rh_f(b); rh_f(c); rh_f(d); rb_add(a, b, c, d, pen_pad(p)); return rec_end(); }
static GpStatus WINAPI w_FillPolygon(GpGraphics *g, GpBrush *b, const GpPointF *p, INT n, INT m)
{ if (!REC_ON(g)) return ras_skip_pts(g, p, n, 2) ? 0 : r_GdipFillPolygon(g, b, p, n, m); REC_CALL(46); rh_u(obj_h(b)); rh_u(n); rh_u(m); if (n > 0) rh_bytes(p, sizeof *p * n); rb_pts(p, n, 2); return rec_end(); }
static GpStatus WINAPI w_DrawPolygon(GpGraphics *g, GpPen *pen, const GpPointF *p, INT n)
{ if (!REC_ON(g)) return ras_skip_pts(g, p, n, pen_pad(pen)) ? 0 : r_GdipDrawPolygon(g, pen, p, n); REC_CALL(47); rh_u(obj_h(pen)); rh_u(n); if (n > 0) rh_bytes(p, sizeof *p * n); rb_pts(p, n, pen_pad(pen)); return rec_end(); }
static void path_bounds(GpPath *p, float pad)
{ RecObj *o = p ? obj_slot(p, 0) : NULL; if (o && o->has) rb_add(o->x0, o->y0, o->x1, o->y1, pad); else { g_rball = 1; g_call_all = 1; } }
static GpStatus WINAPI w_DrawPath(GpGraphics *g, GpPen *pen, GpPath *p)
{ if (!REC_ON(g)) return r_GdipDrawPath(g, pen, p); REC_CALL(48); rh_u(obj_h(pen)); rh_u(obj_h(p)); path_bounds(p, pen_pad(pen)); return rec_end(); }
static GpStatus WINAPI w_FillPath(GpGraphics *g, GpBrush *b, GpPath *p)
{ if (!REC_ON(g)) return r_GdipFillPath(g, b, p); REC_CALL(49); rh_u(obj_h(b)); rh_u(obj_h(p)); path_bounds(p, 2); return rec_end(); }
static GpStatus WINAPI w_DrawString(GpGraphics *g, const WCHAR *s, INT n, const GpFont *f, const GpRectF *r, const GpStringFormat *fm, const GpBrush *b)
{
    if (!REC_ON(g)) return r->Width > 0 && r->Height > 0 && ras_skip(g, r->X, r->Y, r->X + r->Width, r->Y + r->Height, 6) ? 0 : r_GdipDrawString(g, s, n, f, r, fm, b);
    REC_CALL(50);
    int len = n < 0 ? (int)wcslen(s) : n;
    rh_u(len); if (len > 0) rh_bytes(s, sizeof *s * len);
    rh_u(obj_h(f)); rh_u(obj_h(fm)); rh_u(obj_h(b)); rh_bytes(r, sizeof *r);
    if (r->Width <= 0 || r->Height <= 0) { g_rball = 1; g_call_all = 1; } else rb_add(r->X, r->Y, r->X + r->Width, r->Y + r->Height, 6);
    return rec_end();
}
static GpStatus WINAPI w_DrawImageRectRect(GpGraphics *g, GpImage *im, REAL x, REAL y, REAL w, REAL h, REAL sx, REAL sy, REAL sw, REAL sh,
                                           INT u, const void *ia, void *cb, void *cd)
{
    if (!REC_ON(g)) return ras_skip(g, x, y, x + w, y + h, 2) ? 0 : r_GdipDrawImageRectRect(g, im, x, y, w, h, sx, sy, sw, sh, u, ia, cb, cd);
    REC_CALL(51);
    rh_u((uintptr_t)im); rh_u((uintptr_t)ia);
    float v[8] = { x, y, w, h, sx, sy, sw, sh }; rh_bytes(v, sizeof v); rh_u(u);
    rb_add(x, y, x + w, y + h, 2);
    return rec_end();
}

static void rec_install(void)
{
    static int done; if (done) return; done = 1;
#define GDIP_SAVE(ret, name, args) r_##name = p##name;
    GDIP_FUNCS(GDIP_SAVE)
#define W(n) pGdip##n = w_##n;
    W(SetSmoothingMode) W(SetTextRenderingHint) W(SetPixelOffsetMode) W(SetInterpolationMode) W(SetClipPath) W(SetClipRect) W(ResetClip)
    W(CreateSolidFill) W(SetSolidFillColor) W(DeleteBrush) W(CreateLineBrush) W(CreatePen1) W(DeletePen) W(SetPenLineCap197819)
    W(SetPenLineJoin) W(SetPenDashStyle) W(CreatePath) W(DeletePath) W(StartPathFigure) W(ClosePathFigure) W(AddPathLine)
    W(AddPathBezier) W(AddPathEllipse) W(CreateFont) W(DeleteFont) W(CreateStringFormat) W(DeleteStringFormat)
    W(SetStringFormatAlign) W(SetStringFormatLineAlign) W(SetStringFormatFlags) W(SetStringFormatTrimming)
    W(FillRectangle) W(DrawRectangle) W(FillEllipse) W(DrawEllipse) W(DrawArc) W(DrawLine) W(FillPolygon) W(DrawPolygon)
    W(DrawPath) W(FillPath) W(DrawString) W(DrawImageRectRect)
#undef W
}
#endif
