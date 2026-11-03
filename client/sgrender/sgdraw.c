/* sgdraw.c - SGRender's own DirectDraw (phase 2 of the drawing-layer plan, 2026-10-28; replaces cnc-ddraw).
 *
 * SG.exe uses a very small part of DirectDraw (inventory from the disassembly, CGraph 004c0bd0 / 004c00b0 / 004c01f0 /
 * 004bad80 / 004bd0f0 / 005490c0): DirectDrawCreate; IDirectDraw::SetCooperativeLevel, SetDisplayMode(w, h, 16),
 * GetDisplayMode, CreateSurface (the primary, caps 0x200; a W x 600 system-memory back surface, caps 0x840),
 * Release; IDirectDrawSurface::Lock / Unlock, BltFast / Blt (back -> primary, once a frame), GetDC / ReleaseDC
 * (GDI text, 004bd0f0), GetPixelFormat, Restore, Flip.  Bink (intro films) is decoded by the game itself
 * (BinkCopyToBuffer) into locked surfaces.  Every other method is answered "unsupported" and LOGGED once, so a path
 * that needs more shows up in SGRender.log.
 *
 * Surfaces are DIB sections, 16-bit RGB565, top-down: Lock hands out the DIB bits, GetDC a memory DC with the DIB.
 * The game believes it has an exclusive full-screen W x 600 x 16 mode; nothing changes the real display mode.
 * Whenever the primary surface changes (BltFast / Blt into it, Unlock / ReleaseDC / Flip of it) the frame is
 * presented to the game window, scaled with the aspect kept (black bars), by the presenter (sgr_present: D3D9 when
 * available, else GDI StretchDIBits).  Window: borderless full screen on its monitor (default) or a normal window
 * (SGRender.ini [display] mode=windowed); Alt+Enter switches.  Mouse: client coordinates are mapped back to game
 * coordinates in the game's window procedure (subclassed), ClipCursor / SetCursorPos (exe imports, IAT) map the
 * other way.
 */
#include <windows.h>
#include <ddraw.h>
#include <stdio.h>
#include <string.h>
#include "sgrender.h"

#define SGD_UNSUP DDERR_UNSUPPORTED
static const GUID SG_IID_DD = { 0x6C14DB80, 0xA733, 0x11CE, { 0xA5, 0x21, 0x00, 0x20, 0xAF, 0x0B, 0xE5, 0x60 } };
static const GUID SG_IID_DDS = { 0x6C14DB81, 0xA733, 0x11CE, { 0xA5, 0x21, 0x00, 0x20, 0xAF, 0x0B, 0xE5, 0x60 } };

/* ---------------------------------------------------------------------------------------------------------------- */
typedef struct SGSurf {
    void **vt;
    LONG ref;
    int w, h, pitch;            /* pitch in bytes */
    unsigned char *bits;
    HBITMAP dib, old;
    HDC dc;
    int primary;
    DWORD caps;
    DDCOLORKEY ck; int has_ck;
} SGSurf;

typedef struct SGDD {
    void **vt;
    LONG ref;
} SGDD;

SGDisplay g_disp;                       /* shared with the presenter */
static SGDD g_dd_obj;
static int g_dd_made;

static void unsup(const char *what)
{
    static char seen[64][40]; static int n;
    for (int i = 0; i < n; i++) if (!strcmp(seen[i], what)) return;
    if (n < 64) lstrcpynA(seen[n++], what, 40);
    sgr_log("DDRAW unsupported call: %s", what);
}

static void fill_pf(DDPIXELFORMAT *pf)
{
    memset(pf, 0, sizeof *pf);
    pf->dwSize = sizeof *pf;
    pf->dwFlags = DDPF_RGB;
    pf->dwRGBBitCount = 16;
    pf->dwRBitMask = 0xf800; pf->dwGBitMask = 0x07e0; pf->dwBBitMask = 0x001f;
}

/* ---------------------------------------------------------------------------------------------------------------- */
/* surfaces */
static void **g_surf_vt;

static SGSurf *surf_new(int w, int h, DWORD caps, int primary)
{
    SGSurf *s = (SGSurf *)calloc(1, sizeof *s);
    if (!s) return NULL;
    s->vt = g_surf_vt; s->ref = 1; s->w = w; s->h = h; s->caps = caps; s->primary = primary;
    struct { BITMAPINFOHEADER h; DWORD m[3]; } bi;
    memset(&bi, 0, sizeof bi);
    bi.h.biSize = sizeof bi.h; bi.h.biWidth = w; bi.h.biHeight = -h; bi.h.biPlanes = 1; bi.h.biBitCount = 16;
    bi.h.biCompression = BI_BITFIELDS; bi.m[0] = 0xf800; bi.m[1] = 0x07e0; bi.m[2] = 0x001f;
    void *bits = NULL;
    s->dib = CreateDIBSection(NULL, (BITMAPINFO *)&bi, DIB_RGB_COLORS, &bits, NULL, 0);
    if (!s->dib || !bits) { free(s); return NULL; }
    s->bits = (unsigned char *)bits;
    s->pitch = ((w * 2) + 3) & ~3;
    memset(s->bits, 0, (size_t)s->pitch * h);
    return s;
}

static void primary_changed(SGSurf *s) { if (s->primary) sgr_present(); }

static HRESULT WINAPI S_QueryInterface(SGSurf *s, REFIID r, void **o)
{
    if (IsEqualGUID(r, &IID_IUnknown) || IsEqualGUID(r, &SG_IID_DDS)) { s->ref++; *o = s; return S_OK; }
    unsup("Surface::QueryInterface (other interface)");
    *o = NULL; return E_NOINTERFACE;
}
static ULONG WINAPI S_AddRef(SGSurf *s) { return ++s->ref; }
static ULONG WINAPI S_Release(SGSurf *s)
{
    LONG r = --s->ref;
    if (r <= 0) {
        if (s->primary && g_disp.primary == (void *)s) g_disp.primary = NULL;
        if (s->dc) { SelectObject(s->dc, s->old); DeleteDC(s->dc); }
        if (s->dib) DeleteObject(s->dib);
        free(s);
        return 0;
    }
    return r;
}
static HRESULT WINAPI S_AddAttachedSurface(SGSurf *s, void *a) { (void)s; (void)a; unsup("Surface::AddAttachedSurface"); return SGD_UNSUP; }
static HRESULT WINAPI S_AddOverlayDirtyRect(SGSurf *s, RECT *r) { (void)s; (void)r; unsup("Surface::AddOverlayDirtyRect"); return SGD_UNSUP; }

static int clip_copy(SGSurf *d, int dx, int dy, SGSurf *src, RECT *sr, int keyed)
{
    RECT r = { 0, 0, src->w, src->h };
    if (sr) r = *sr;
    if (r.left < 0) { dx -= r.left; r.left = 0; }
    if (r.top < 0) { dy -= r.top; r.top = 0; }
    if (r.right > src->w) r.right = src->w;
    if (r.bottom > src->h) r.bottom = src->h;
    if (dx < 0) { r.left -= dx; dx = 0; }
    if (dy < 0) { r.top -= dy; dy = 0; }
    int w = r.right - r.left, h = r.bottom - r.top;
    if (dx + w > d->w) w = d->w - dx;
    if (dy + h > d->h) h = d->h - dy;
    if (w <= 0 || h <= 0) return 0;
    unsigned short key = (unsigned short)src->ck.dwColorSpaceLowValue;
    for (int y = 0; y < h; y++) {
        unsigned short *dp = (unsigned short *)(d->bits + (size_t)(dy + y) * d->pitch) + dx;
        const unsigned short *sp = (const unsigned short *)(src->bits + (size_t)(r.top + y) * src->pitch) + r.left;
        if (!keyed) memmove(dp, sp, (size_t)w * 2);
        else for (int x = 0; x < w; x++) if (sp[x] != key) dp[x] = sp[x];
    }
    return 1;
}

static HRESULT WINAPI S_Blt(SGSurf *d, RECT *dr, SGSurf *src, RECT *sr, DWORD flags, DDBLTFX *fx)
{
    RECT D = { 0, 0, d->w, d->h };
    if (dr) D = *dr;
    if (flags & DDBLT_COLORFILL) {
        unsigned short c = fx ? (unsigned short)fx->dwFillColor : 0;
        if (D.left < 0) D.left = 0; if (D.top < 0) D.top = 0;
        if (D.right > d->w) D.right = d->w; if (D.bottom > d->h) D.bottom = d->h;
        for (int y = D.top; y < D.bottom; y++) {
            unsigned short *p = (unsigned short *)(d->bits + (size_t)y * d->pitch);
            for (int x = D.left; x < D.right; x++) p[x] = c;
        }
        primary_changed(d);
        return DD_OK;
    }
    if (!src) { unsup("Surface::Blt (no source, flags)"); return DDERR_INVALIDPARAMS; }
    RECT S = { 0, 0, src->w, src->h };
    if (sr) S = *sr;
    int keyed = (flags & DDBLT_KEYSRC) && src->has_ck;
    if (D.right - D.left == S.right - S.left && D.bottom - D.top == S.bottom - S.top)
        clip_copy(d, D.left, D.top, src, &S, keyed);
    else {                                                /* stretch, nearest */
        int dw = D.right - D.left, dh = D.bottom - D.top, sw = S.right - S.left, sh = S.bottom - S.top;
        if (dw > 0 && dh > 0 && sw > 0 && sh > 0)
            for (int y = 0; y < dh; y++) {
                int ty = D.top + y, sy = S.top + y * sh / dh;
                if (ty < 0 || ty >= d->h || sy < 0 || sy >= src->h) continue;
                unsigned short *dp = (unsigned short *)(d->bits + (size_t)ty * d->pitch);
                const unsigned short *sp = (const unsigned short *)(src->bits + (size_t)sy * src->pitch);
                for (int x = 0; x < dw; x++) {
                    int tx = D.left + x, sx = S.left + x * sw / dw;
                    if (tx < 0 || tx >= d->w || sx < 0 || sx >= src->w) continue;
                    if (keyed && sp[sx] == (unsigned short)src->ck.dwColorSpaceLowValue) continue;
                    dp[tx] = sp[sx];
                }
            }
    }
    primary_changed(d);
    return DD_OK;
}
static HRESULT WINAPI S_BltBatch(SGSurf *s, void *b, DWORD c, DWORD f) { (void)s; (void)b; (void)c; (void)f; unsup("Surface::BltBatch"); return SGD_UNSUP; }
static HRESULT WINAPI S_BltFast(SGSurf *d, DWORD x, DWORD y, SGSurf *src, RECT *sr, DWORD trans)
{
    if (!src) return DDERR_INVALIDPARAMS;
    clip_copy(d, (int)x, (int)y, src, sr, (trans & DDBLTFAST_SRCCOLORKEY) && src->has_ck);
    primary_changed(d);
    return DD_OK;
}
static HRESULT WINAPI S_DeleteAttachedSurface(SGSurf *s, DWORD f, void *a) { (void)s; (void)f; (void)a; unsup("Surface::DeleteAttachedSurface"); return SGD_UNSUP; }
static HRESULT WINAPI S_EnumAttachedSurfaces(SGSurf *s, void *c, void *cb) { (void)s; (void)c; (void)cb; return DD_OK; }
static HRESULT WINAPI S_EnumOverlayZOrders(SGSurf *s, DWORD f, void *c, void *cb) { (void)s; (void)f; (void)c; (void)cb; unsup("Surface::EnumOverlayZOrders"); return SGD_UNSUP; }
static HRESULT WINAPI S_Flip(SGSurf *s, void *t, DWORD f) { (void)t; (void)f; primary_changed(s); return DD_OK; }
static HRESULT WINAPI S_GetAttachedSurface(SGSurf *s, DDSCAPS *c, void **o) { (void)s; (void)c; unsup("Surface::GetAttachedSurface"); if (o) *o = NULL; return DDERR_NOTFOUND; }
static HRESULT WINAPI S_GetBltStatus(SGSurf *s, DWORD f) { (void)s; (void)f; return DD_OK; }
static HRESULT WINAPI S_GetCaps(SGSurf *s, DDSCAPS *c) { if (c) c->dwCaps = s->caps | (s->primary ? DDSCAPS_PRIMARYSURFACE | DDSCAPS_VISIBLE : 0); return DD_OK; }
static HRESULT WINAPI S_GetClipper(SGSurf *s, void **c) { (void)s; if (c) *c = NULL; return DDERR_NOCLIPPERATTACHED; }
static HRESULT WINAPI S_GetColorKey(SGSurf *s, DWORD f, DDCOLORKEY *k) { (void)f; if (!s->has_ck) return DDERR_NOCOLORKEY; if (k) *k = s->ck; return DD_OK; }
static HRESULT WINAPI S_GetDC(SGSurf *s, HDC *o)
{
    if (!s->dc) { s->dc = CreateCompatibleDC(NULL); s->old = (HBITMAP)SelectObject(s->dc, s->dib); }
    GdiFlush();
    *o = s->dc;
    return DD_OK;
}
static HRESULT WINAPI S_GetFlipStatus(SGSurf *s, DWORD f) { (void)s; (void)f; return DD_OK; }
static HRESULT WINAPI S_GetOverlayPosition(SGSurf *s, LONG *x, LONG *y) { (void)s; (void)x; (void)y; unsup("Surface::GetOverlayPosition"); return SGD_UNSUP; }
static HRESULT WINAPI S_GetPalette(SGSurf *s, void **p) { (void)s; if (p) *p = NULL; return DDERR_NOPALETTEATTACHED; }
static HRESULT WINAPI S_GetPixelFormat(SGSurf *s, DDPIXELFORMAT *pf) { (void)s; if (pf) fill_pf(pf); return DD_OK; }
static void fill_desc(SGSurf *s, DDSURFACEDESC *d, unsigned char *ptr)
{
    memset(d, 0, sizeof *d);
    d->dwSize = sizeof *d;
    d->dwFlags = DDSD_CAPS | DDSD_HEIGHT | DDSD_WIDTH | DDSD_PITCH | DDSD_PIXELFORMAT | (ptr ? DDSD_LPSURFACE : 0);
    d->dwWidth = s->w; d->dwHeight = s->h; d->lPitch = s->pitch; d->lpSurface = ptr;
    fill_pf(&d->ddpfPixelFormat);
    S_GetCaps(s, &d->ddsCaps);
}
static HRESULT WINAPI S_GetSurfaceDesc(SGSurf *s, DDSURFACEDESC *d) { if (!d) return DDERR_INVALIDPARAMS; fill_desc(s, d, NULL); return DD_OK; }
static HRESULT WINAPI S_Initialize(SGSurf *s, void *dd, DDSURFACEDESC *d) { (void)s; (void)dd; (void)d; return DDERR_ALREADYINITIALIZED; }
static HRESULT WINAPI S_IsLost(SGSurf *s) { (void)s; return DD_OK; }
static HRESULT WINAPI S_Lock(SGSurf *s, RECT *r, DDSURFACEDESC *d, DWORD f, HANDLE e)
{
    (void)f; (void)e;
    if (!d) return DDERR_INVALIDPARAMS;
    GdiFlush();
    unsigned char *p = s->bits;
    if (r) p += (size_t)r->top * s->pitch + (size_t)r->left * 2;
    fill_desc(s, d, p);
    return DD_OK;
}
static HRESULT WINAPI S_ReleaseDC(SGSurf *s, HDC dc) { (void)dc; GdiFlush(); primary_changed(s); return DD_OK; }
static HRESULT WINAPI S_Restore(SGSurf *s) { (void)s; return DD_OK; }
static HRESULT WINAPI S_SetClipper(SGSurf *s, void *c) { (void)s; (void)c; return DD_OK; }
static HRESULT WINAPI S_SetColorKey(SGSurf *s, DWORD f, DDCOLORKEY *k)
{
    (void)f;
    if (k) { s->ck = *k; s->has_ck = 1; } else s->has_ck = 0;
    return DD_OK;
}
static HRESULT WINAPI S_SetOverlayPosition(SGSurf *s, LONG x, LONG y) { (void)s; (void)x; (void)y; unsup("Surface::SetOverlayPosition"); return SGD_UNSUP; }
static HRESULT WINAPI S_SetPalette(SGSurf *s, void *p) { (void)s; (void)p; return DD_OK; }
static HRESULT WINAPI S_Unlock(SGSurf *s, void *p) { (void)p; primary_changed(s); return DD_OK; }
static HRESULT WINAPI S_UpdateOverlay(SGSurf *s, RECT *a, void *b, RECT *c, DWORD f, void *fx) { (void)s; (void)a; (void)b; (void)c; (void)f; (void)fx; unsup("Surface::UpdateOverlay"); return SGD_UNSUP; }
static HRESULT WINAPI S_UpdateOverlayDisplay(SGSurf *s, DWORD f) { (void)s; (void)f; unsup("Surface::UpdateOverlayDisplay"); return SGD_UNSUP; }
static HRESULT WINAPI S_UpdateOverlayZOrder(SGSurf *s, DWORD f, void *r) { (void)s; (void)f; (void)r; unsup("Surface::UpdateOverlayZOrder"); return SGD_UNSUP; }

static void *SURF_VT[36] = {
    S_QueryInterface, S_AddRef, S_Release, S_AddAttachedSurface, S_AddOverlayDirtyRect, S_Blt, S_BltBatch, S_BltFast,
    S_DeleteAttachedSurface, S_EnumAttachedSurfaces, S_EnumOverlayZOrders, S_Flip, S_GetAttachedSurface, S_GetBltStatus,
    S_GetCaps, S_GetClipper, S_GetColorKey, S_GetDC, S_GetFlipStatus, S_GetOverlayPosition, S_GetPalette,
    S_GetPixelFormat, S_GetSurfaceDesc, S_Initialize, S_IsLost, S_Lock, S_ReleaseDC, S_Restore, S_SetClipper,
    S_SetColorKey, S_SetOverlayPosition, S_SetPalette, S_Unlock, S_UpdateOverlay, S_UpdateOverlayDisplay,
    S_UpdateOverlayZOrder
};

/* ---------------------------------------------------------------------------------------------------------------- */
/* the DirectDraw object */
static HRESULT WINAPI D_QueryInterface(SGDD *d, REFIID r, void **o)
{
    if (IsEqualGUID(r, &IID_IUnknown) || IsEqualGUID(r, &SG_IID_DD)) { d->ref++; *o = d; return S_OK; }
    unsup("DirectDraw::QueryInterface (other interface)");
    *o = NULL; return E_NOINTERFACE;
}
static ULONG WINAPI D_AddRef(SGDD *d) { return ++d->ref; }
static ULONG WINAPI D_Release(SGDD *d) { LONG r = --d->ref; if (r <= 0) { d->ref = 0; sgr_log("DDRAW released"); } return r < 0 ? 0 : r; }
static HRESULT WINAPI D_Compact(SGDD *d) { (void)d; return DD_OK; }
static HRESULT WINAPI D_CreateClipper(SGDD *d, DWORD f, void **c, void *u) { (void)d; (void)f; (void)u; unsup("DirectDraw::CreateClipper"); if (c) *c = NULL; return SGD_UNSUP; }
static HRESULT WINAPI D_CreatePalette(SGDD *d, DWORD f, void *e, void **p, void *u) { (void)d; (void)f; (void)e; (void)u; unsup("DirectDraw::CreatePalette"); if (p) *p = NULL; return SGD_UNSUP; }
static HRESULT WINAPI D_CreateSurface(SGDD *d, DDSURFACEDESC *sd, SGSurf **o, void *u)
{
    (void)d; (void)u;
    if (!sd || !o) return DDERR_INVALIDPARAMS;
    DWORD caps = (sd->dwFlags & DDSD_CAPS) ? sd->ddsCaps.dwCaps : 0;
    int primary = (caps & DDSCAPS_PRIMARYSURFACE) != 0;
    int w = primary ? g_disp.gw : (int)sd->dwWidth, h = primary ? g_disp.gh : (int)sd->dwHeight;
    if (!primary && !((sd->dwFlags & DDSD_WIDTH) && (sd->dwFlags & DDSD_HEIGHT))) { unsup("DirectDraw::CreateSurface (no size)"); return DDERR_INVALIDPARAMS; }
    if (primary && (sd->dwFlags & DDSD_BACKBUFFERCOUNT) && sd->dwBackBufferCount) unsup("DirectDraw::CreateSurface (back buffers)");
    SGSurf *s = surf_new(w, h, caps, primary);
    if (!s) return DDERR_OUTOFMEMORY;
    if (primary) g_disp.primary = s;
    sgr_log("DDRAW CreateSurface %s %dx%d caps %08lx", primary ? "primary" : "offscreen", w, h, caps);
    *o = s;
    return DD_OK;
}
static HRESULT WINAPI D_DuplicateSurface(SGDD *d, void *a, void **b) { (void)d; (void)a; (void)b; unsup("DirectDraw::DuplicateSurface"); return SGD_UNSUP; }
static HRESULT WINAPI D_EnumDisplayModes(SGDD *d, DWORD f, DDSURFACEDESC *sd, void *ctx, LPDDENUMMODESCALLBACK cb)
{
    (void)d; (void)f; (void)sd;
    static const int modes[][2] = { { 640, 480 }, { 800, 600 }, { 1024, 768 } };
    for (unsigned i = 0; i < 3; i++) {
        DDSURFACEDESC m; memset(&m, 0, sizeof m);
        m.dwSize = sizeof m; m.dwFlags = DDSD_WIDTH | DDSD_HEIGHT | DDSD_PIXELFORMAT | DDSD_PITCH;
        m.dwWidth = modes[i][0]; m.dwHeight = modes[i][1]; m.lPitch = modes[i][0] * 2; fill_pf(&m.ddpfPixelFormat);
        if (cb && cb(&m, ctx) == DDENUMRET_CANCEL) break;
    }
    return DD_OK;
}
static HRESULT WINAPI D_EnumSurfaces(SGDD *d, DWORD f, void *sd, void *c, void *cb) { (void)d; (void)f; (void)sd; (void)c; (void)cb; unsup("DirectDraw::EnumSurfaces"); return SGD_UNSUP; }
static HRESULT WINAPI D_FlipToGDISurface(SGDD *d) { (void)d; return DD_OK; }
static HRESULT WINAPI D_GetCaps(SGDD *d, DDCAPS *a, DDCAPS *b)
{
    (void)d;
    if (a) { DWORD sz = a->dwSize ? a->dwSize : sizeof *a; memset(a, 0, sz); a->dwSize = sz; a->dwCaps = DDCAPS_BLT | DDCAPS_BLTSTRETCH | DDCAPS_COLORKEY; }
    if (b) { DWORD sz = b->dwSize ? b->dwSize : sizeof *b; memset(b, 0, sz); b->dwSize = sz; b->dwCaps = DDCAPS_BLT | DDCAPS_BLTSTRETCH | DDCAPS_COLORKEY; }
    return DD_OK;
}
static HRESULT WINAPI D_GetDisplayMode(SGDD *d, DDSURFACEDESC *sd)
{
    (void)d;
    if (!sd) return DDERR_INVALIDPARAMS;
    memset(sd, 0, sizeof *sd);
    sd->dwSize = sizeof *sd; sd->dwFlags = DDSD_WIDTH | DDSD_HEIGHT | DDSD_PITCH | DDSD_PIXELFORMAT | DDSD_REFRESHRATE;
    sd->dwWidth = g_disp.gw; sd->dwHeight = g_disp.gh; sd->lPitch = g_disp.gw * 2; sd->dwRefreshRate = 60;
    fill_pf(&sd->ddpfPixelFormat);
    return DD_OK;
}
static HRESULT WINAPI D_GetFourCCCodes(SGDD *d, DWORD *n, DWORD *c) { (void)d; (void)c; if (n) *n = 0; return DD_OK; }
static HRESULT WINAPI D_GetGDISurface(SGDD *d, void **o) { (void)d; if (o) *o = g_disp.primary; if (g_disp.primary) ((SGSurf *)g_disp.primary)->ref++; return g_disp.primary ? DD_OK : DDERR_NOTFOUND; }
static HRESULT WINAPI D_GetMonitorFrequency(SGDD *d, DWORD *f) { (void)d; if (f) *f = 60; return DD_OK; }
static HRESULT WINAPI D_GetScanLine(SGDD *d, DWORD *l) { (void)d; if (l) *l = 0; return DD_OK; }
static HRESULT WINAPI D_GetVerticalBlankStatus(SGDD *d, BOOL *b) { (void)d; if (b) *b = TRUE; return DD_OK; }
static HRESULT WINAPI D_Initialize(SGDD *d, GUID *g) { (void)d; (void)g; return DDERR_ALREADYINITIALIZED; }
static HRESULT WINAPI D_RestoreDisplayMode(SGDD *d) { (void)d; return DD_OK; }
static HRESULT WINAPI D_SetCooperativeLevel(SGDD *d, HWND hwnd, DWORD flags)
{
    (void)d;
    sgr_log("DDRAW SetCooperativeLevel hwnd %p flags %08lx", hwnd, flags);
    if (hwnd) sgr_window_attach(hwnd);
    return DD_OK;
}
static HRESULT WINAPI D_SetDisplayMode(SGDD *d, DWORD w, DWORD h, DWORD bpp)
{
    (void)d;
    sgr_log("DDRAW SetDisplayMode %lux%lux%lu", w, h, bpp);
    g_disp.gw = (int)w; g_disp.gh = (int)h;
    sgr_window_apply();
    return DD_OK;
}
static HRESULT WINAPI D_WaitForVerticalBlank(SGDD *d, DWORD f, HANDLE e) { (void)d; (void)f; (void)e; return DD_OK; }

static void *DD_VT[23] = {
    D_QueryInterface, D_AddRef, D_Release, D_Compact, D_CreateClipper, D_CreatePalette, D_CreateSurface,
    D_DuplicateSurface, D_EnumDisplayModes, D_EnumSurfaces, D_FlipToGDISurface, D_GetCaps, D_GetDisplayMode,
    D_GetFourCCCodes, D_GetGDISurface, D_GetMonitorFrequency, D_GetScanLine, D_GetVerticalBlankStatus, D_Initialize,
    D_RestoreDisplayMode, D_SetCooperativeLevel, D_SetDisplayMode, D_WaitForVerticalBlank
};

/* the ddraw.dll proxy calls this instead of the system's / cnc-ddraw's DirectDrawCreate */
__declspec(dllexport) HRESULT WINAPI SGR_DirectDrawCreate(GUID *guid, void **out, IUnknown *outer)
{
    (void)guid; (void)outer;
    if (!out) return DDERR_INVALIDPARAMS;
    g_surf_vt = SURF_VT;
    if (!g_dd_made) {
        g_dd_obj.vt = DD_VT; g_dd_made = 1;
        if (!g_disp.gw) { g_disp.gw = 800; g_disp.gh = 600; }
        sgr_log("DDRAW SGDraw active (own DirectDraw, presenter %s)", sgr_presenter_name());
    }
    g_dd_obj.ref++;
    *out = &g_dd_obj;
    return DD_OK;
}

int sgr_primary_info(unsigned char **bits, int *pitch, int *w, int *h)
{
    SGSurf *s = (SGSurf *)g_disp.primary;
    if (!s) return 0;
    *bits = s->bits; *pitch = s->pitch; *w = s->w; *h = s->h;
    return 1;
}
