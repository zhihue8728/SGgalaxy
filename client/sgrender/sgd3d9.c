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
static IDirect3DTexture9 *g_tex, *g_ovt;
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
   art codes (sghd.h / F58) are drawn again at screen resolution from hd\<code>\<file>.hds (tools/hd_pack.py) ---- */
typedef struct { unsigned short x, y, w, h; short px, py; } HdCell;
typedef struct {
    char name[16];               /* "a008mo" */
    int state;                   /* 1 loaded, -1 missing / bad */
    IDirect3DTexture9 *tex;
    int aw, ah, dirs, fpd, blend, scale;
    HdCell *cells;
} HdAsset;
#define HD_MAXASSETS 96
static HdAsset g_hda[HD_MAXASSETS]; static int g_hda_n;
static DWORD g_hd_ms, g_hd_frames, g_hd_quads;

static HdAsset *hd_asset(const char *xpf)
{
    char base[16]; int i = 0;
    for (; xpf[i] && xpf[i] != '.' && i < 15; i++) base[i] = xpf[i];
    base[i] = 0;
    for (int k = 0; k < g_hda_n; k++) if (!strcmp(g_hda[k].name, base)) return g_hda[k].state > 0 ? &g_hda[k] : NULL;
    if (g_hda_n >= HD_MAXASSETS) return NULL;
    HdAsset *a = &g_hda[g_hda_n++]; memset(a, 0, sizeof *a); strcpy(a->name, base); a->state = -1;
    char path[MAX_PATH]; char code[5]; memcpy(code, base, 4); code[4] = 0;
    wsprintfA(path, "hd\\%s\\%s.hds", code, base);
    HANDLE f = CreateFileA(path, GENERIC_READ, FILE_SHARE_READ, NULL, OPEN_EXISTING, 0, NULL);
    if (f == INVALID_HANDLE_VALUE) return NULL;
    DWORD sz = GetFileSize(f, NULL), got = 0;
    unsigned char *b = sz > 16 ? (unsigned char *)malloc(sz) : NULL;
    if (b) ReadFile(f, b, sz, &got, NULL);
    CloseHandle(f);
    if (!b || got != sz || memcmp(b, "HDS1", 4)) { free(b); sgr_log("hd: %s unreadable", path); return NULL; }
    const unsigned short *h = (const unsigned short *)(b + 4);
    a->aw = h[0]; a->ah = h[1]; a->dirs = h[2]; a->fpd = h[3]; a->blend = b[12]; a->scale = b[13] ? b[13] : 1;
    size_t nc = (size_t)a->dirs * a->fpd, off = 16 + nc * sizeof(HdCell);
    if (!a->dirs || !a->fpd || off + (size_t)a->aw * a->ah * 4 != sz) { free(b); sgr_log("hd: %s bad size", path); return NULL; }
    a->cells = (HdCell *)malloc(nc * sizeof(HdCell));
    memcpy(a->cells, b + 16, nc * sizeof(HdCell));
    if (FAILED(IDirect3DDevice9_CreateTexture(g_dev, a->aw, a->ah, 1, 0, D3DFMT_A8R8G8B8, D3DPOOL_MANAGED, &a->tex, NULL))) {
        free(b); sgr_log("hd: %s texture %dx%d failed", path, a->aw, a->ah); a->tex = NULL; return NULL;
    }
    D3DLOCKED_RECT lr;
    if (SUCCEEDED(IDirect3DTexture9_LockRect(a->tex, 0, &lr, NULL, 0))) {
        for (int y = 0; y < a->ah; y++) memcpy((unsigned char *)lr.pBits + (size_t)y * lr.Pitch, b + off + (size_t)y * a->aw * 4, (size_t)a->aw * 4);
        IDirect3DTexture9_UnlockRect(a->tex, 0);
    }
    free(b);
    a->state = 1;
    sgr_log("hd: %s loaded (%dx%d, %d dirs x %d frames, blend %d, x%d)", path, a->aw, a->ah, a->dirs, a->fpd, a->blend, a->scale);
    return a;
}

static void hd_release(void)
{
    for (int k = 0; k < g_hda_n; k++) { if (g_hda[k].tex) IDirect3DTexture9_Release(g_hda[k].tex); free(g_hda[k].cells); }
    g_hda_n = 0;
}

/* frame pixel (fx, fy) -> client: dest is where the W x 600 frame lands */
static void hd_draw(const RECT *dest)
{
    const SGHdRec *r; int n = sgr_hd_list(&r);
    if (n <= 0 || g_disp.gw <= 0) return;
    LARGE_INTEGER q0, q1, qf; QueryPerformanceCounter(&q0);
    float s = (float)(dest->right - dest->left) / (float)g_disp.gw;
    int blend = -1, quads = 0;
    IDirect3DDevice9_SetSamplerState(g_dev, 0, D3DSAMP_MINFILTER, D3DTEXF_LINEAR);
    IDirect3DDevice9_SetSamplerState(g_dev, 0, D3DSAMP_MAGFILTER, D3DTEXF_LINEAR);
    IDirect3DDevice9_SetRenderState(g_dev, D3DRS_ALPHABLENDENABLE, TRUE);
    IDirect3DDevice9_SetTextureStageState(g_dev, 0, D3DTSS_ALPHAOP, D3DTOP_SELECTARG1);
    IDirect3DDevice9_SetTextureStageState(g_dev, 0, D3DTSS_ALPHAARG1, D3DTA_TEXTURE);
    for (int i = 0; i < n; i++) {
        HdAsset *a = hd_asset(r[i].name);
        if (!a) continue;
        int d = r[i].dir, f = r[i].frame;
        if (d < 0 || d >= a->dirs || f < 0) continue;
        const HdCell *c = &a->cells[(f % a->fpd) * a->dirs + d];
        if (!c->w) continue;
        if (a->blend != blend) {
            blend = a->blend;
            IDirect3DDevice9_SetRenderState(g_dev, D3DRS_SRCBLEND, D3DBLEND_ONE);
            IDirect3DDevice9_SetRenderState(g_dev, D3DRS_DESTBLEND, blend == 1 ? D3DBLEND_ONE : D3DBLEND_INVSRCALPHA);
        }
        float k = s / (float)a->scale;
        float x0 = dest->left + r[i].fx * s - c->px * k - 0.5f, y0 = dest->top + r[i].fy * s - c->py * k - 0.5f;
        float x1 = x0 + c->w * k, y1 = y0 + c->h * k;
        float u0 = (float)c->x / a->aw, v0 = (float)c->y / a->ah, u1 = (float)(c->x + c->w) / a->aw, v1 = (float)(c->y + c->h) / a->ah;
        VTX v[4] = { { x0, y0, 0, 1, u0, v0 }, { x1, y0, 0, 1, u1, v0 }, { x0, y1, 0, 1, u0, v1 }, { x1, y1, 0, 1, u1, v1 } };
        IDirect3DDevice9_SetTexture(g_dev, 0, (IDirect3DBaseTexture9 *)a->tex);
        IDirect3DDevice9_DrawPrimitiveUP(g_dev, D3DPT_TRIANGLESTRIP, 2, v, sizeof(VTX));
        quads++;
    }
    QueryPerformanceCounter(&q1); QueryPerformanceFrequency(&qf);
    g_hd_ms += (DWORD)((q1.QuadPart - q0.QuadPart) * 1000000 / qf.QuadPart); g_hd_quads += quads;
    if (++g_hd_frames == 600) {
        if (sgr_hd_debug()) sgr_log("hd: %lu quads/frame, %lu us/frame (CPU side)", g_hd_quads / 600, g_hd_ms / 600);
        g_hd_frames = 0; g_hd_ms = 0; g_hd_quads = 0;
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
