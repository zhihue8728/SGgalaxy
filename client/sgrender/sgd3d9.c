/* sgd3d9.c - the D3D9 presenter of SGRender's own DirectDraw.
 * d3d9.dll is loaded at run time (no import: a PC without it falls back to GDI).  The device is a windowed D3D9
 * device on the game window (borderless full screen is just a window covering the monitor: no display mode change,
 * Alt+Tab is instant), back buffer = client size, no vsync wait (the game's lock-step loop must never block in
 * Present).  The frame (RGB565) goes into a dynamic texture (R5G6B5, or X8R8G8B8 converted on the CPU when the card
 * lacks R5G6B5) and is drawn as one quad at the aspect-kept destination, LINEAR (smooth) or POINT (sharp) filter.
 * Phase 3 adds a second, native-resolution RGBA texture (the new HUD) blended on top. */
#define COBJMACROS
#include <windows.h>
#include <d3d9.h>
#include <stdlib.h>
#include <string.h>
#include "sgrender.h"

typedef IDirect3D9 *(WINAPI *create9_fn)(UINT);
static HMODULE g_d3d9_dll;
static IDirect3D9 *g_d3d;
static IDirect3DDevice9 *g_dev;
static IDirect3DTexture9 *g_tex, *g_ovt, *g_hdm;   /* g_hdm: HD unit masks (below) */
static int g_ovt_w, g_ovt_h, g_ovt_ver = -1;
static int g_tex_w, g_tex_h, g_tex_565;
static int g_bb_w, g_bb_h, g_need_reset, g_failed;
static HWND g_dev_hwnd;

typedef struct { float x, y, z, rhw, u, v; } VTX;
#define VTX_FVF (D3DFVF_XYZRHW | D3DFVF_TEX1)

void sgr_d3d9_reset(void) { g_need_reset = 1; }

static void release_tex(void)
{
    if (g_tex) { IDirect3DTexture9_Release(g_tex); g_tex = NULL; }
    if (g_ovt) { IDirect3DTexture9_Release(g_ovt); g_ovt = NULL; g_ovt_ver = -1; }
    if (g_hdm) { IDirect3DTexture9_Release(g_hdm); g_hdm = NULL; }   /* D3DPOOL_DEFAULT: gone with a Reset */
}

/* the native-resolution overlay (premultiplied BGRA) -> a texture of the client size */
static int upload_overlay(const SGOverlay *ov)
{
    if (g_ovt && (g_ovt_w != ov->w || g_ovt_h != ov->h)) { IDirect3DTexture9_Release(g_ovt); g_ovt = NULL; g_ovt_ver = -1; }
    if (!g_ovt) {
        if (FAILED(IDirect3DDevice9_CreateTexture(g_dev, ov->w, ov->h, 1, D3DUSAGE_DYNAMIC, D3DFMT_A8R8G8B8, D3DPOOL_DEFAULT, &g_ovt, NULL))) {
            g_ovt = NULL; return 0;
        }
        g_ovt_w = ov->w; g_ovt_h = ov->h; g_ovt_ver = -1;
    }
    if (g_ovt_ver == ov->version) return 1;
    D3DLOCKED_RECT lr;
    /* (11-01) only what this version changed, when the texture holds the version before it; else all of it */
    int part = g_ovt_ver == ov->version - 1 && ov->dx0 >= 0 && ov->dy0 >= 0 && ov->dx1 <= ov->w && ov->dy1 <= ov->h;
    if (part && (ov->dx1 <= ov->dx0 || ov->dy1 <= ov->dy0)) { g_ovt_ver = ov->version; return 1; }   /* nothing changed */
    if (part && !(ov->dx0 == 0 && ov->dy0 == 0 && ov->dx1 == ov->w && ov->dy1 == ov->h)) {
        RECT r = { ov->dx0, ov->dy0, ov->dx1, ov->dy1 };
        if (FAILED(IDirect3DTexture9_LockRect(g_ovt, 0, &lr, &r, 0))) return 0;
        for (int y = r.top; y < r.bottom; y++)
            memcpy((unsigned char *)lr.pBits + (size_t)(y - r.top) * lr.Pitch, ov->bits + (size_t)y * ov->w + r.left, (size_t)(r.right - r.left) * 4);
    } else {
        if (FAILED(IDirect3DTexture9_LockRect(g_ovt, 0, &lr, NULL, D3DLOCK_DISCARD))) return 0;
        for (int y = 0; y < ov->h; y++) memcpy((unsigned char *)lr.pBits + (size_t)y * lr.Pitch, ov->bits + (size_t)y * ov->w, (size_t)ov->w * 4);
    }
    IDirect3DTexture9_UnlockRect(g_ovt, 0);
    g_ovt_ver = ov->version;
    return 1;
}

static void fill_pp(D3DPRESENT_PARAMETERS *pp, HWND h, int w, int hh)
{
    ZeroMemory(pp, sizeof *pp);
    pp->Windowed = TRUE;
    pp->SwapEffect = D3DSWAPEFFECT_DISCARD;
    pp->hDeviceWindow = h;
    pp->BackBufferWidth = w; pp->BackBufferHeight = hh;
    pp->BackBufferFormat = D3DFMT_UNKNOWN;
    pp->PresentationInterval = D3DPRESENT_INTERVAL_IMMEDIATE;
}

static int create_device(HWND h, int w, int hh)
{
    if (!g_d3d) {
        if (!g_d3d9_dll) g_d3d9_dll = LoadLibraryA("d3d9.dll");
        create9_fn c = g_d3d9_dll ? (create9_fn)GetProcAddress(g_d3d9_dll, "Direct3DCreate9") : NULL;
        g_d3d = c ? c(D3D_SDK_VERSION) : NULL;
        if (!g_d3d) { sgr_log("d3d9: Direct3DCreate9 failed"); return 0; }
    }
    D3DPRESENT_PARAMETERS pp; fill_pp(&pp, h, w, hh);
    HRESULT hr = IDirect3D9_CreateDevice(g_d3d, D3DADAPTER_DEFAULT, D3DDEVTYPE_HAL, h,
                                         D3DCREATE_SOFTWARE_VERTEXPROCESSING | D3DCREATE_FPU_PRESERVE | D3DCREATE_MULTITHREADED, &pp, &g_dev);
    if (FAILED(hr)) { sgr_log("d3d9: CreateDevice failed %08lx", hr); g_dev = NULL; return 0; }
    g_tex_565 = SUCCEEDED(IDirect3D9_CheckDeviceFormat(g_d3d, D3DADAPTER_DEFAULT, D3DDEVTYPE_HAL, D3DFMT_X8R8G8B8, D3DUSAGE_DYNAMIC, D3DRTYPE_TEXTURE, D3DFMT_R5G6B5));
    g_bb_w = w; g_bb_h = hh; g_dev_hwnd = h; g_need_reset = 0;
    D3DADAPTER_IDENTIFIER9 id;
    if (SUCCEEDED(IDirect3D9_GetAdapterIdentifier(g_d3d, D3DADAPTER_DEFAULT, 0, &id)))
        sgr_log("d3d9: device on \"%s\", back buffer %dx%d, frame texture %s", id.Description, w, hh, g_tex_565 ? "R5G6B5" : "X8R8G8B8");
    return 1;
}

static int reset_device(HWND h, int w, int hh)
{
    release_tex();
    D3DPRESENT_PARAMETERS pp; fill_pp(&pp, h, w, hh);
    HRESULT hr = IDirect3DDevice9_Reset(g_dev, &pp);
    if (FAILED(hr)) return 0;
    g_bb_w = w; g_bb_h = hh; g_need_reset = 0;
    return 1;
}

/* (user 10-31 18:56 "smooth the whole picture") filter=hq: the frame is doubled on the CPU with EPX (Scale2x) using a
   colour tolerance instead of exact equality (the game's art is pre-rendered, not flat pixel art), so diagonal and
   curved edges become smooth steps; the GPU then scales the double frame LINEAR to the screen.  ~3-6 ms a frame. */
static int near565(unsigned a, unsigned b)
{
    int dr = (int)((a >> 11) & 31) - (int)((b >> 11) & 31), dg = (int)((a >> 5) & 63) - (int)((b >> 5) & 63), db = (int)(a & 31) - (int)(b & 31);
    if (dr < 0) dr = -dr; if (dg < 0) dg = -dg; if (db < 0) db = -db;
    return dr * 2 + dg + db * 2 < 14;
}
static void epx2(const unsigned char *bits, int pitch, int w, int h, unsigned char *out, int opitch)
{
    for (int y = 0; y < h; y++) {
        const unsigned short *r0 = (const unsigned short *)(bits + (size_t)(y ? y - 1 : 0) * pitch);
        const unsigned short *r1 = (const unsigned short *)(bits + (size_t)y * pitch);
        const unsigned short *r2 = (const unsigned short *)(bits + (size_t)(y < h - 1 ? y + 1 : y) * pitch);
        unsigned short *o0 = (unsigned short *)(out + (size_t)(2 * y) * opitch), *o1 = (unsigned short *)(out + (size_t)(2 * y + 1) * opitch);
        for (int x = 0; x < w; x++) {
            unsigned P = r1[x], A = r0[x], D = r2[x], C = r1[x ? x - 1 : 0], B = r1[x < w - 1 ? x + 1 : x];
            unsigned e1 = P, e2 = P, e3 = P, e4 = P;
            if (!(near565(A, D) && near565(C, B)) && !near565(P, A) + !near565(P, B) + !near565(P, C) + !near565(P, D) >= 2) {
                int ca = near565(C, A), ab = near565(A, B), dc = near565(D, C), bd = near565(B, D);
                if (ca && !dc && !ab) e1 = A;
                if (ab && !ca && !bd) e2 = B;
                if (dc && !bd && !ca) e3 = C;
                if (bd && !ab && !dc) e4 = D;
            }
            o0[2 * x] = (unsigned short)e1; o0[2 * x + 1] = (unsigned short)e2; o1[2 * x] = (unsigned short)e3; o1[2 * x + 1] = (unsigned short)e4;
        }
    }
}
static unsigned char *g_hq_buf; static int g_hq_cap;
static int upload(void)
{
    unsigned char *bits; int pitch, w, h;
    if (!sgr_primary_info(&bits, &pitch, &w, &h)) return 0;
    if (g_disp.smooth == 2) {                              /* hq: the doubled frame becomes the source */
        int need = w * 2 * 2 * h * 2;
        if (need > g_hq_cap) { free(g_hq_buf); g_hq_buf = (unsigned char *)malloc(need); g_hq_cap = g_hq_buf ? need : 0; }
        if (g_hq_buf) {
            static DWORD tsum, n; DWORD t0 = GetTickCount();
            epx2(bits, pitch, w, h, g_hq_buf, w * 4);
            tsum += GetTickCount() - t0;
            if (++n == 600) { sgr_log("d3d9: hq frame %dx%d -> %dx%d, %lu ms avg", w, h, w * 2, h * 2, tsum / 600); tsum = 0; n = 0; }
            bits = g_hq_buf; pitch = w * 4; w *= 2; h *= 2;
        }
    }
    if (g_tex && (g_tex_w != w || g_tex_h != h)) release_tex();
    if (!g_tex) {
        HRESULT hr = IDirect3DDevice9_CreateTexture(g_dev, w, h, 1, D3DUSAGE_DYNAMIC, g_tex_565 ? D3DFMT_R5G6B5 : D3DFMT_X8R8G8B8,
                                                    D3DPOOL_DEFAULT, &g_tex, NULL);
        if (FAILED(hr)) { sgr_log("d3d9: CreateTexture %dx%d failed %08lx", w, h, hr); g_tex = NULL; return 0; }
        g_tex_w = w; g_tex_h = h;
    }
    D3DLOCKED_RECT lr;
    if (FAILED(IDirect3DTexture9_LockRect(g_tex, 0, &lr, NULL, D3DLOCK_DISCARD))) return 0;
    for (int y = 0; y < h; y++) {
        const unsigned short *s = (const unsigned short *)(bits + (size_t)y * pitch);
        if (g_tex_565) memcpy((unsigned char *)lr.pBits + (size_t)y * lr.Pitch, s, (size_t)w * 2);
        else {
            DWORD *d = (DWORD *)((unsigned char *)lr.pBits + (size_t)y * lr.Pitch);
            for (int x = 0; x < w; x++) {
                unsigned v = s[x], r = (v >> 11) & 31, g = (v >> 5) & 63, b = v & 31;
                d[x] = 0xff000000u | ((r << 3 | r >> 2) << 16) | ((g << 2 | g >> 4) << 8) | (b << 3 | b >> 2);
            }
        }
    }
    IDirect3DTexture9_UnlockRect(g_tex, 0);
    return 1;
}


/* ---- HD field units (11-03, plan claude/HD_UNIT_OVERLAY_PLAN.md): the sprites the game drew this frame for the HD
   art codes (sghd.h / F58) are drawn again at screen resolution from their .hds atlases, each multiplied by its own
   mask (step 3): the final frame compared with the reference pixels sghd.h kept for that sprite.  1 = still showing
   (the HD picture shows), k < 1 = the same colour darker (fog: the HD picture darkened by k), 0 = something else drawn
   over it (cut out). ---- */
typedef struct { float x, y, z, rhw, u, v, u2, v2; } VTX2;
#define VTX2_FVF (D3DFVF_XYZRHW | D3DFVF_TEX2)
#define HDM_W 2048
#define HDM_H 2048
static unsigned short *g_hdm_buf;                    /* CPU copy (A8L8) */
static int g_hdm_ok = -1;
static DWORD g_hd_us, g_hd_mask_us, g_hd_frames, g_hd_quads, g_hd_masked;
typedef struct { int u, v, w, h; } HdMaskCell;
static HdMaskCell g_hdmc[2048];

static int hd_tex(SGHdAsset *a)
{
    if (a->tex) return 1;
    if (a->state != 1) return 0;
    unsigned char *px = sgr_hd_pixels(a);
    IDirect3DTexture9 *t = NULL;
    if (!px || FAILED(IDirect3DDevice9_CreateTexture(g_dev, a->aw, a->ah, 1, 0, D3DFMT_A8R8G8B8, D3DPOOL_MANAGED, &t, NULL))) {
        free(px); a->state = -1; sgr_log("hd: %s texture %dx%d failed", a->path, a->aw, a->ah); return 0;
    }
    D3DLOCKED_RECT lr;
    if (SUCCEEDED(IDirect3DTexture9_LockRect(t, 0, &lr, NULL, 0))) {
        for (int y = 0; y < a->ah; y++) memcpy((unsigned char *)lr.pBits + (size_t)y * lr.Pitch, px + (size_t)y * a->aw * 4, (size_t)a->aw * 4);
        IDirect3DTexture9_UnlockRect(t, 0);
    }
    free(px);
    a->tex = t;
    sgr_log("hd: %s loaded (%dx%d, %d dirs x %d frames, blend %d, x%d)", a->path, a->aw, a->ah, a->dirs, a->fpd, a->blend, a->scale);
    return 1;
}

static void hd_release(void)
{
    SGHdAsset *a; int n = sgr_hd_assets(&a);
    for (int k = 0; k < n; k++) if (a[k].tex) { IDirect3DTexture9_Release((IDirect3DTexture9 *)a[k].tex); a[k].tex = NULL; }
    if (g_hdm) { IDirect3DTexture9_Release(g_hdm); g_hdm = NULL; }
    g_hdm_ok = -1;
}

/* k (0..255) for one pixel: final F against reference R, both RGB565 */
static int hd_k(unsigned short R, unsigned short F)
{
    if (R == F) return 255;
    int r[3] = { (R >> 11) << 3, ((R >> 5) & 63) << 2, (R & 31) << 3 };
    int f[3] = { (F >> 11) << 3, ((F >> 5) & 63) << 2, (F & 31) << 3 };
    int num = 0, den = 0;
    for (int c = 0; c < 3; c++) { num += f[c] * r[c]; den += r[c] * r[c]; }
    if (den < 3 * 24 * 24) return (f[0] + f[1] + f[2] < 3 * 40) ? -1 : 0;     /* dark reference: decided below */
    int k = num * 255 / den;                          /* least squares F = k R */
    if (k > 255) k = 255;
    for (int c = 0; c < 3; c++) { int e = f[c] - k * r[c] / 255; if (e > 24 || e < -24) return 0; }
    return k;
}

/* build every snapshot's mask into the atlas (shelf packing); cell 0 = 4x4 white for sprites without a snapshot */
static int hd_masks(const SGHdRec *r, int n)
{
    unsigned char *bits; int pitch, w, h;
    if (!sgr_primary_info(&bits, &pitch, &w, &h)) return 0;
    const unsigned short *pool = sgr_hd_pool();
    if (!g_hdm_buf) g_hdm_buf = (unsigned short *)malloc((size_t)HDM_W * HDM_H * 2);
    if (!g_hdm_buf || !pool) return 0;
    for (int y = 0; y < 4; y++) for (int x = 0; x < 4; x++) g_hdm_buf[y * HDM_W + x] = 0xffff;
    int px = 6, py = 0, rowh = 4, used = 4;
    for (int i = 0; i < n && i < 2048; i++) {
        g_hdmc[i].w = 0;
        if (r[i].bw <= 0) continue;
        int bw = r[i].bw, bh = r[i].bh;
        if (px + bw + 2 > HDM_W) { px = 0; py += rowh + 2; rowh = 0; }
        if (py + bh + 2 > HDM_H) break;                   /* atlas full: the rest draw without a mask */
        const unsigned short *ref = pool + r[i].ref;
        long sum = 0; int cnt = 0;
        for (int y = 0; y < bh; y++) {
            const unsigned short *fr = (const unsigned short *)(bits + (size_t)(r[i].by + y) * pitch) + r[i].bx;
            unsigned short *m = g_hdm_buf + (size_t)(py + y) * HDM_W + px;
            for (int x = 0; x < bw; x++) {
                int k = hd_k(ref[y * bw + x], fr[x]);
                if (k > 0) { sum += k; cnt++; }
                m[x] = (unsigned short)(k < 0 ? 0xfffe : k * 0x0101);
            }
        }
        int avg = cnt ? (int)(sum / cnt) : 255;           /* dark pixels: the sprite's average darkening */
        for (int y = 0; y < bh; y++) {
            unsigned short *m = g_hdm_buf + (size_t)(py + y) * HDM_W + px;
            for (int x = 0; x < bw; x++) if (m[x] == 0xfffe) m[x] = (unsigned short)(avg * 0x0101);
        }
        g_hdmc[i].u = px; g_hdmc[i].v = py; g_hdmc[i].w = bw; g_hdmc[i].h = bh;
        px += bw + 2; if (bh > rowh) rowh = bh;
        if (py + rowh > used) used = py + rowh;
        g_hd_masked++;
    }
    if (!g_hdm) {
        if (FAILED(IDirect3DDevice9_CreateTexture(g_dev, HDM_W, HDM_H, 1, D3DUSAGE_DYNAMIC, D3DFMT_A8L8, D3DPOOL_DEFAULT, &g_hdm, NULL))) {
            g_hdm = NULL; if (g_hdm_ok) sgr_log("hd: A8L8 mask texture not supported: no occlusion"); g_hdm_ok = 0; return 0;
        }
        g_hdm_ok = 1;
    }
    D3DLOCKED_RECT lr; RECT rc = { 0, 0, HDM_W, used + 2 > HDM_H ? HDM_H : used + 2 };
    if (FAILED(IDirect3DTexture9_LockRect(g_hdm, 0, &lr, &rc, 0))) return 0;
    for (int y = 0; y < rc.bottom; y++) memcpy((unsigned char *)lr.pBits + (size_t)y * lr.Pitch, g_hdm_buf + (size_t)y * HDM_W, HDM_W * 2);
    IDirect3DTexture9_UnlockRect(g_hdm, 0);
    return 1;
}

/* frame pixel (fx, fy) -> client: dest is where the W x 600 frame lands */
static void hd_draw(const RECT *dest)
{
    const SGHdRec *r; int n = sgr_hd_list(&r);
    if (n <= 0 || g_disp.gw <= 0) return;
    sgr_hd_gpu();
    LARGE_INTEGER q0, q1, q2, qf; QueryPerformanceCounter(&q0);
    int masks = hd_masks(r, n);
    QueryPerformanceCounter(&q1);
    float s = (float)(dest->right - dest->left) / (float)g_disp.gw;
    int blend = -1, quads = 0;
    IDirect3DDevice9_SetFVF(g_dev, VTX2_FVF);
    for (int st = 0; st < 2; st++) {
        IDirect3DDevice9_SetSamplerState(g_dev, st, D3DSAMP_MINFILTER, D3DTEXF_LINEAR);
        IDirect3DDevice9_SetSamplerState(g_dev, st, D3DSAMP_MAGFILTER, D3DTEXF_LINEAR);
        IDirect3DDevice9_SetSamplerState(g_dev, st, D3DSAMP_ADDRESSU, D3DTADDRESS_CLAMP);
        IDirect3DDevice9_SetSamplerState(g_dev, st, D3DSAMP_ADDRESSV, D3DTADDRESS_CLAMP);
    }
    IDirect3DDevice9_SetRenderState(g_dev, D3DRS_ALPHABLENDENABLE, TRUE);
    IDirect3DDevice9_SetTextureStageState(g_dev, 0, D3DTSS_COLOROP, D3DTOP_SELECTARG1);
    IDirect3DDevice9_SetTextureStageState(g_dev, 0, D3DTSS_COLORARG1, D3DTA_TEXTURE);
    IDirect3DDevice9_SetTextureStageState(g_dev, 0, D3DTSS_ALPHAOP, D3DTOP_SELECTARG1);
    IDirect3DDevice9_SetTextureStageState(g_dev, 0, D3DTSS_ALPHAARG1, D3DTA_TEXTURE);
    IDirect3DDevice9_SetTextureStageState(g_dev, 0, D3DTSS_TEXCOORDINDEX, 0);
    if (masks) {                                          /* stage 1: x mask (premultiplied: colour and alpha) */
        IDirect3DDevice9_SetTexture(g_dev, 1, (IDirect3DBaseTexture9 *)g_hdm);
        IDirect3DDevice9_SetTextureStageState(g_dev, 1, D3DTSS_TEXCOORDINDEX, 1);
        IDirect3DDevice9_SetTextureStageState(g_dev, 1, D3DTSS_COLOROP, D3DTOP_MODULATE);
        IDirect3DDevice9_SetTextureStageState(g_dev, 1, D3DTSS_COLORARG1, D3DTA_TEXTURE);
        IDirect3DDevice9_SetTextureStageState(g_dev, 1, D3DTSS_COLORARG2, D3DTA_CURRENT);
        IDirect3DDevice9_SetTextureStageState(g_dev, 1, D3DTSS_ALPHAOP, D3DTOP_MODULATE);
        IDirect3DDevice9_SetTextureStageState(g_dev, 1, D3DTSS_ALPHAARG1, D3DTA_TEXTURE);
        IDirect3DDevice9_SetTextureStageState(g_dev, 1, D3DTSS_ALPHAARG2, D3DTA_CURRENT);
    } else IDirect3DDevice9_SetTextureStageState(g_dev, 1, D3DTSS_COLOROP, D3DTOP_DISABLE);
    for (int i = 0; i < n; i++) {
        SGHdAsset *a = r[i].asset;
        if (!a || r[i].cell < 0 || !hd_tex(a)) continue;
        const SGHdCell *c = &a->cells[r[i].cell];
        if (a->blend != blend) {
            blend = a->blend;
            IDirect3DDevice9_SetRenderState(g_dev, D3DRS_SRCBLEND, D3DBLEND_ONE);
            IDirect3DDevice9_SetRenderState(g_dev, D3DRS_DESTBLEND, blend == 1 ? D3DBLEND_ONE : D3DBLEND_INVSRCALPHA);
        }
        float k = s / (float)a->scale;
        float fx0 = r[i].fx - c->px / (float)a->scale, fy0 = r[i].fy - c->py / (float)a->scale;   /* frame coords */
        float fx1 = fx0 + c->w / (float)a->scale, fy1 = fy0 + c->h / (float)a->scale;
        float x0 = dest->left + fx0 * s - 0.5f, y0 = dest->top + fy0 * s - 0.5f;
        float x1 = x0 + c->w * k, y1 = y0 + c->h * k;
        float u0 = (float)c->x / a->aw, v0 = (float)c->y / a->ah, u1 = (float)(c->x + c->w) / a->aw, v1 = (float)(c->y + c->h) / a->ah;
        float m0 = 2.0f / HDM_W, n0 = 2.0f / HDM_H, m1 = m0, n1 = n0;            /* no snapshot: the white cell */
        if (masks && i < 2048 && g_hdmc[i].w) {                                   /* frame box -> its mask cell */
            const HdMaskCell *mc = &g_hdmc[i];
            m0 = (mc->u + fx0 - r[i].bx) / HDM_W; m1 = (mc->u + fx1 - r[i].bx) / HDM_W;
            n0 = (mc->v + fy0 - r[i].by) / HDM_H; n1 = (mc->v + fy1 - r[i].by) / HDM_H;
        }
        VTX2 v[4] = { { x0, y0, 0, 1, u0, v0, m0, n0 }, { x1, y0, 0, 1, u1, v0, m1, n0 },
                      { x0, y1, 0, 1, u0, v1, m0, n1 }, { x1, y1, 0, 1, u1, v1, m1, n1 } };
        IDirect3DDevice9_SetTexture(g_dev, 0, (IDirect3DBaseTexture9 *)a->tex);
        IDirect3DDevice9_DrawPrimitiveUP(g_dev, D3DPT_TRIANGLESTRIP, 2, v, sizeof(VTX2));
        quads++;
    }
    IDirect3DDevice9_SetTexture(g_dev, 1, NULL);
    IDirect3DDevice9_SetTextureStageState(g_dev, 1, D3DTSS_COLOROP, D3DTOP_DISABLE);
    IDirect3DDevice9_SetTextureStageState(g_dev, 1, D3DTSS_ALPHAOP, D3DTOP_DISABLE);
    IDirect3DDevice9_SetFVF(g_dev, VTX_FVF);
    QueryPerformanceCounter(&q2); QueryPerformanceFrequency(&qf);
    g_hd_mask_us += (DWORD)((q1.QuadPart - q0.QuadPart) * 1000000 / qf.QuadPart);
    g_hd_us += (DWORD)((q2.QuadPart - q0.QuadPart) * 1000000 / qf.QuadPart); g_hd_quads += quads;
    if (++g_hd_frames == 600) {
        if (sgr_hd_debug()) sgr_log("hd: %lu quads/frame (%lu masked), %lu us/frame CPU (masks %lu us)", g_hd_quads / 600,
                                    g_hd_masked / 600, g_hd_us / 600, g_hd_mask_us / 600);
        g_hd_frames = 0; g_hd_us = 0; g_hd_mask_us = 0; g_hd_quads = 0; g_hd_masked = 0;
    }
}

extern int g_hide_game;          /* sgwindow.c boot_hide_update: the game's own start-up pictures are not shown */
int sgr_d3d9_present(HWND h, const RECT *client, const RECT *dest)
{
    if (g_failed) return 0;
    int w = client->right, hh = client->bottom;
    if (!g_dev || g_dev_hwnd != h) {
        if (g_dev) { release_tex(); hd_release(); IDirect3DDevice9_Release(g_dev); g_dev = NULL; }
        if (!create_device(h, w, hh)) { g_failed = 1; return 0; }
    }
    HRESULT co = IDirect3DDevice9_TestCooperativeLevel(g_dev);
    if (co == D3DERR_DEVICELOST) return 1;                        /* minimised / locked: skip this frame */
    if (co == D3DERR_DEVICENOTRESET || g_need_reset || w != g_bb_w || hh != g_bb_h) {
        if (!reset_device(h, w, hh)) return 1;                   /* try again next frame */
    }
    if (!upload()) { g_failed = 1; sgr_log("d3d9: frame upload failed, GDI from now on"); return 0; }
    IDirect3DDevice9_Clear(g_dev, 0, NULL, D3DCLEAR_TARGET, D3DCOLOR_XRGB(0, 0, 0), 1.0f, 0);
    if (SUCCEEDED(IDirect3DDevice9_BeginScene(g_dev))) {
        float l = (float)dest->left - 0.5f, t = (float)dest->top - 0.5f, r = (float)dest->right - 0.5f, b = (float)dest->bottom - 0.5f;
        VTX q[4] = { { l, t, 0, 1, 0, 0 }, { r, t, 0, 1, 1, 0 }, { l, b, 0, 1, 0, 1 }, { r, b, 0, 1, 1, 1 } };
        IDirect3DDevice9_SetFVF(g_dev, VTX_FVF);
        IDirect3DDevice9_SetTexture(g_dev, 0, (IDirect3DBaseTexture9 *)g_tex);
        DWORD f = g_disp.smooth ? D3DTEXF_LINEAR : D3DTEXF_POINT;
        IDirect3DDevice9_SetSamplerState(g_dev, 0, D3DSAMP_MINFILTER, f);
        IDirect3DDevice9_SetSamplerState(g_dev, 0, D3DSAMP_MAGFILTER, f);
        IDirect3DDevice9_SetSamplerState(g_dev, 0, D3DSAMP_ADDRESSU, D3DTADDRESS_CLAMP);
        IDirect3DDevice9_SetSamplerState(g_dev, 0, D3DSAMP_ADDRESSV, D3DTADDRESS_CLAMP);
        IDirect3DDevice9_SetRenderState(g_dev, D3DRS_LIGHTING, FALSE);
        IDirect3DDevice9_SetRenderState(g_dev, D3DRS_CULLMODE, D3DCULL_NONE);
        IDirect3DDevice9_SetRenderState(g_dev, D3DRS_ZENABLE, FALSE);
        IDirect3DDevice9_SetRenderState(g_dev, D3DRS_ALPHABLENDENABLE, FALSE);
        if (!g_hide_game) IDirect3DDevice9_DrawPrimitiveUP(g_dev, D3DPT_TRIANGLESTRIP, 2, q, sizeof(VTX));   /* (11-02) start-up: black */
        if (!g_hide_game) hd_draw(dest);                    /* (11-03) HD field units over the frame, under the HUD */
        const SGOverlay *ov = sgr_overlay();
        if (ov && upload_overlay(ov)) {                     /* the HUD, 1:1 pixels, premultiplied alpha */
            float R = (float)ov->w - 0.5f, B = (float)ov->h - 0.5f;
            VTX o[4] = { { -0.5f, -0.5f, 0, 1, 0, 0 }, { R, -0.5f, 0, 1, 1, 0 }, { -0.5f, B, 0, 1, 0, 1 }, { R, B, 0, 1, 1, 1 } };
            IDirect3DDevice9_SetTexture(g_dev, 0, (IDirect3DBaseTexture9 *)g_ovt);
            IDirect3DDevice9_SetSamplerState(g_dev, 0, D3DSAMP_MINFILTER, D3DTEXF_POINT);
            IDirect3DDevice9_SetSamplerState(g_dev, 0, D3DSAMP_MAGFILTER, D3DTEXF_POINT);
            IDirect3DDevice9_SetRenderState(g_dev, D3DRS_ALPHABLENDENABLE, TRUE);
            IDirect3DDevice9_SetRenderState(g_dev, D3DRS_SRCBLEND, D3DBLEND_ONE);
            IDirect3DDevice9_SetRenderState(g_dev, D3DRS_DESTBLEND, D3DBLEND_INVSRCALPHA);
            IDirect3DDevice9_SetTextureStageState(g_dev, 0, D3DTSS_ALPHAOP, D3DTOP_SELECTARG1);
            IDirect3DDevice9_SetTextureStageState(g_dev, 0, D3DTSS_ALPHAARG1, D3DTA_TEXTURE);
            IDirect3DDevice9_DrawPrimitiveUP(g_dev, D3DPT_TRIANGLESTRIP, 2, o, sizeof(VTX));
        }
        IDirect3DDevice9_EndScene(g_dev);
    }
    HRESULT pr = IDirect3DDevice9_Present(g_dev, NULL, NULL, NULL, NULL);
    if (pr == D3DERR_DEVICELOST) g_need_reset = 1;
    return 1;
}
