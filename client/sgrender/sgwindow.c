/* sgwindow.c - the game window and the presenter of SGRender's own DirectDraw (sgdraw.c).
 *
 * Window: borderless full screen on its monitor (default) or a normal resizable window ([display] mode=windowed in
 * SGRender.ini); Alt+Enter switches.  The frame (the primary surface, W x 600 RGB565) is scaled into the client area
 * with its aspect ratio kept (black bars): presenter D3D9 (sgd3d9.c) when it starts, else GDI StretchDIBits
 * ([display] filter=smooth -> HALFTONE, sharp -> nearest).  The process is made DPI aware so the picture is scaled
 * once, by us, at the screen's real resolution.
 * Mouse: the game expects the coordinates of its W x 600 mode; client coordinates are mapped back in the window
 * procedure (subclassed); the exe's ClipCursor / SetCursorPos imports (IAT, outside the code checksum) map game
 * coordinates to the screen.  In a window or while inactive the cursor is never clipped.
 */
#include <windows.h>
#include <stdio.h>
#include <stdlib.h>
#include <math.h>
#include "sgrender.h"
#include "sghud_cursor.h"

static WNDPROC g_orig_proc;
static RECT g_game_clip; static int g_game_clip_set;
static BOOL (WINAPI *real_ClipCursor)(const RECT *);
static BOOL (WINAPI *real_SetCursorPos)(int, int);
static int (WINAPI *real_ShowCursor)(BOOL);
static int g_game_cur = 0, g_real_cur_adj, g_over_hud;   /* the game's ShowCursor count; our extra shows */

/* the game's own arrow as the Windows cursor over the HUD (user 10-28 20:11: not the Windows arrow), scaled like
 * the frame, smooth, with a thin dark outline */
static HCURSOR g_hud_cur; static int g_hud_cur_px;
static HCURSOR hud_cursor(void)
{
    int dw = g_disp.dest.right - g_disp.dest.left, gw = g_disp.gw ? g_disp.gw : 800;
    float k = dw > 0 ? (float)dw / gw : 1;
    if (k < 1) k = 1;
    int W = (int)(CUR_W * k + 0.5f) + 2, H = (int)(CUR_H * k + 0.5f) + 2;
    if (g_hud_cur && g_hud_cur_px == W) return g_hud_cur;
    BITMAPV5HEADER bi; memset(&bi, 0, sizeof bi);
    bi.bV5Size = sizeof bi; bi.bV5Width = W; bi.bV5Height = -H; bi.bV5Planes = 1; bi.bV5BitCount = 32;
    bi.bV5Compression = BI_BITFIELDS; bi.bV5RedMask = 0x00FF0000; bi.bV5GreenMask = 0x0000FF00; bi.bV5BlueMask = 0x000000FF;
    bi.bV5AlphaMask = 0xFF000000;
    unsigned int *px = NULL;
    HDC dc = GetDC(NULL);
    HBITMAP col = CreateDIBSection(dc, (BITMAPINFO *)&bi, DIB_RGB_COLORS, (void **)&px, NULL, 0);
    ReleaseDC(NULL, dc);
    if (!col) return LoadCursor(NULL, IDC_ARROW);
    for (int y = 0; y < H; y++)                         /* bilinear sample of the sprite (premultiplied) */
        for (int x = 0; x < W; x++) {
            float sx = (x - 1 + 0.5f) / k - 0.5f, sy = (y - 1 + 0.5f) / k - 0.5f;
            int x0 = (int)floorf(sx), y0 = (int)floorf(sy); float fx = sx - x0, fy = sy - y0;
            float acc[4] = {0, 0, 0, 0};
            for (int j = 0; j < 2; j++) for (int i = 0; i < 2; i++) {
                int xx = x0 + i, yy = y0 + j;
                unsigned v = (xx >= 0 && yy >= 0 && xx < CUR_W && yy < CUR_H) ? CUR_PIX[yy * CUR_W + xx] : 0;
                float wgt = (i ? fx : 1 - fx) * (j ? fy : 1 - fy), a = (v >> 24) / 255.0f;
                acc[0] += wgt * a; acc[1] += wgt * a * ((v >> 16) & 255); acc[2] += wgt * a * ((v >> 8) & 255); acc[3] += wgt * a * (v & 255);
            }
            px[y * W + x] = ((unsigned)(acc[0] * 255 + 0.5f) << 24) | ((unsigned)(acc[1] + 0.5f) << 16) |
                            ((unsigned)(acc[2] + 0.5f) << 8) | (unsigned)(acc[3] + 0.5f);
        }
    unsigned *tmp = (unsigned *)malloc((size_t)W * H * 4);   /* outline: dark where a neighbour is drawn */
    if (tmp) {
        memcpy(tmp, px, (size_t)W * H * 4);
        for (int y = 0; y < H; y++) for (int x = 0; x < W; x++) {
            if ((tmp[y * W + x] >> 24) > 40) continue;
            int nb = 0;
            for (int dy = -1; dy <= 1 && !nb; dy++) for (int dx = -1; dx <= 1; dx++) {
                int xx = x + dx, yy = y + dy;
                if (xx >= 0 && yy >= 0 && xx < W && yy < H && (tmp[yy * W + xx] >> 24) > 120) { nb = 1; break; }
            }
            if (nb) px[y * W + x] = 0xC0000000u;
        }
        free(tmp);
    }
    void *mz = calloc((size_t)((W + 15) / 16) * 2 * H, 1);   /* AND mask all 0: the alpha channel decides */
    HBITMAP mask = CreateBitmap(W, H, 1, 1, mz);
    free(mz);
    ICONINFO ii = { FALSE, (DWORD)(CUR_HX * k + 1), (DWORD)(CUR_HY * k + 1), mask, col };
    HCURSOR c = (HCURSOR)CreateIconIndirect(&ii);
    DeleteObject(mask); DeleteObject(col);
    if (!c) return LoadCursor(NULL, IDC_ARROW);
    if (g_hud_cur) DestroyCursor(g_hud_cur);
    g_hud_cur = c; g_hud_cur_px = W;
    sgr_log("HUD cursor: the game arrow at %dx%d (scale %.2f)", W, H, k);
    return c;
}

/* the game hides the Windows cursor (ShowCursor(FALSE)) and draws its own into the frame - which lies under the HUD.
 * Over a HUD part the Windows arrow is shown; elsewhere the count the game asked for is restored. */
static void cursor_apply(int over)
{
    if (!real_ShowCursor) return;
    int want = over && g_game_cur < 0 ? -g_game_cur : 0;   /* extra ShowCursor(TRUE) calls needed to reach 0 */
    while (g_real_cur_adj < want) { real_ShowCursor(TRUE); g_real_cur_adj++; }
    while (g_real_cur_adj > want) { real_ShowCursor(FALSE); g_real_cur_adj--; }
    g_over_hud = over;
}
static int WINAPI hook_ShowCursor(BOOL show)
{
    g_game_cur += show ? 1 : -1;
    int r = real_ShowCursor ? real_ShowCursor(show) : g_game_cur;
    cursor_apply(g_over_hud);
    return r - g_real_cur_adj;
}
static int g_d3d_ok = -1;                 /* -1 not tried, 0 failed, 1 running */
static char g_backend[16] = "auto";

int sgr_d3d9_present(HWND hwnd, const RECT *client, const RECT *dest);   /* sgd3d9.c; 0 = not available */
void sgr_d3d9_reset(void);

const char *sgr_presenter_name(void) { return g_d3d_ok == 1 ? "d3d9" : (g_d3d_ok == 0 ? "gdi" : (strcmp(g_backend, "gdi") ? "d3d9/gdi" : "gdi")); }

void sgr_display_init(void)
{
    char v[32];
    GetPrivateProfileStringA("display", "mode", "fullscreen", v, sizeof v, ".\\GORender.ini");
    g_disp.windowed = !_stricmp(v, "windowed") || !_stricmp(v, "window");
    GetPrivateProfileStringA("display", "filter", "smooth", v, sizeof v, ".\\GORender.ini");
    g_disp.smooth = !_stricmp(v, "sharp") ? 0 : !_stricmp(v, "hq") ? 2 : 1;   /* (10-31 18:56) hq = edge-smoothing x2 first */
    GetPrivateProfileStringA("display", "backend", "auto", g_backend, sizeof g_backend, ".\\GORender.ini");
    if (!_stricmp(g_backend, "gdi")) g_d3d_ok = 0;
    HMODULE u = GetModuleHandleA("user32.dll");
    BOOL (WINAPI *aware)(void) = u ? (BOOL (WINAPI *)(void))GetProcAddress(u, "SetProcessDPIAware") : NULL;
    if (aware) aware();
    sgr_log("display: %s, filter %s, backend %s", g_disp.windowed ? "windowed" : "full screen", g_disp.smooth == 2 ? "hq" : g_disp.smooth ? "smooth" : "sharp", g_backend);
}

/* ---- coordinates ------------------------------------------------------------------------------------------------ */
static void calc_dest(void)
{
    RECT c; GetClientRect(g_disp.hwnd, &c);
    int cw = c.right, ch = c.bottom, gw = g_disp.gw ? g_disp.gw : 800, gh = g_disp.gh ? g_disp.gh : 600;
    if (cw <= 0 || ch <= 0) { SetRect(&g_disp.dest, 0, 0, gw, gh); return; }
    int dw = cw, dh = (int)((long long)cw * gh / gw);
    if (dh > ch) { dh = ch; dw = (int)((long long)ch * gw / gh); }
    int dx = (cw - dw) / 2, dy = (ch - dh) / 2;
    SetRect(&g_disp.dest, dx, dy, dx + dw, dy + dh);
}

static void client_to_game(int cx, int cy, int *gx, int *gy)
{
    RECT *d = &g_disp.dest;
    int dw = d->right - d->left, dh = d->bottom - d->top;
    if (dw <= 0 || dh <= 0) { *gx = cx; *gy = cy; return; }
    int x = (int)((long long)(cx - d->left) * g_disp.gw / dw), y = (int)((long long)(cy - d->top) * g_disp.gh / dh);
    if (x < 0) x = 0; if (x >= g_disp.gw) x = g_disp.gw - 1;
    if (y < 0) y = 0; if (y >= g_disp.gh) y = g_disp.gh - 1;
    *gx = x; *gy = y;
}

static POINT game_to_screen(int gx, int gy)
{
    RECT *d = &g_disp.dest;
    POINT p = { d->left + (int)((long long)gx * (d->right - d->left) / (g_disp.gw ? g_disp.gw : 800)),
                d->top + (int)((long long)gy * (d->bottom - d->top) / (g_disp.gh ? g_disp.gh : 600)) };
    ClientToScreen(g_disp.hwnd, &p);
    return p;
}

static void apply_clip(void)
{
    if (!real_ClipCursor) return;
    if (g_disp.windowed || !g_disp.active || !g_game_clip_set || !g_disp.hwnd) { real_ClipCursor(NULL); return; }
    POINT a = game_to_screen(g_game_clip.left, g_game_clip.top), b = game_to_screen(g_game_clip.right, g_game_clip.bottom);
    RECT r = { a.x, a.y, b.x, b.y };
    real_ClipCursor(&r);
}

static BOOL WINAPI hook_ClipCursor(const RECT *r)
{
    if (r) { g_game_clip = *r; g_game_clip_set = 1; } else g_game_clip_set = 0;
    apply_clip();
    return TRUE;
}

static BOOL WINAPI hook_SetCursorPos(int x, int y)
{
    if (!g_disp.hwnd || !real_SetCursorPos) return real_SetCursorPos ? real_SetCursorPos(x, y) : FALSE;
    POINT p = game_to_screen(x, y);
    return real_SetCursorPos(p.x, p.y);
}

/* patch one import of a module (IAT entries live in .rdata - not part of the code checksum F16 / F34) */
static void *iat_hook(HMODULE mod, const char *dll, const char *fn, void *repl)
{
    unsigned char *base = (unsigned char *)mod;
    IMAGE_NT_HEADERS *nt = (IMAGE_NT_HEADERS *)(base + ((IMAGE_DOS_HEADER *)base)->e_lfanew);
    IMAGE_DATA_DIRECTORY dir = nt->OptionalHeader.DataDirectory[IMAGE_DIRECTORY_ENTRY_IMPORT];
    if (!dir.VirtualAddress) { sgr_log("iat: no import directory"); return NULL; }
    for (IMAGE_IMPORT_DESCRIPTOR *d = (IMAGE_IMPORT_DESCRIPTOR *)(base + dir.VirtualAddress); d->Name; d++) {
        if (_stricmp((char *)(base + d->Name), dll)) continue;
        IMAGE_THUNK_DATA *names = (IMAGE_THUNK_DATA *)(base + (d->OriginalFirstThunk ? d->OriginalFirstThunk : d->FirstThunk));
        IMAGE_THUNK_DATA *iat = (IMAGE_THUNK_DATA *)(base + d->FirstThunk);
        void *want = (void *)GetProcAddress(GetModuleHandleA(dll), fn);
        for (; iat->u1.Function; names++, iat++) {
            int hit = want && (void *)iat->u1.Function == want;        /* resolved address (works without names) */
            if (!hit && d->OriginalFirstThunk && names->u1.AddressOfData && !IMAGE_SNAP_BY_ORDINAL(names->u1.Ordinal)) {
                IMAGE_IMPORT_BY_NAME *ibn = (IMAGE_IMPORT_BY_NAME *)(base + names->u1.AddressOfData);
                hit = !strcmp((char *)ibn->Name, fn);
            }
            if (!hit) continue;
            DWORD old;
            void *prev = (void *)iat->u1.Function;
            if (VirtualProtect(&iat->u1.Function, sizeof(void *), PAGE_READWRITE, &old)) {
                iat->u1.Function = (DWORD_PTR)repl;
                VirtualProtect(&iat->u1.Function, sizeof(void *), old, &old);
                return prev;
            }
            return NULL;
        }
    }
    return NULL;
}

/* ---- window ----------------------------------------------------------------------------------------------------- */
void sgr_window_apply(void)
{
    HWND h = g_disp.hwnd;
    if (!h) return;
    HMONITOR mon = MonitorFromWindow(h, MONITOR_DEFAULTTOPRIMARY);
    MONITORINFO mi; mi.cbSize = sizeof mi; GetMonitorInfoA(mon, &mi);
    if (!g_disp.windowed) {
        SetWindowLongA(h, GWL_STYLE, WS_POPUP | WS_VISIBLE);
        SetWindowLongA(h, GWL_EXSTYLE, GetWindowLongA(h, GWL_EXSTYLE) & ~(WS_EX_CLIENTEDGE | WS_EX_WINDOWEDGE | WS_EX_DLGMODALFRAME));
        RECT m = mi.rcMonitor;
        SetWindowPos(h, HWND_TOP, m.left, m.top, m.right - m.left, m.bottom - m.top, SWP_FRAMECHANGED | SWP_SHOWWINDOW);
    } else {
        RECT wa = mi.rcWork;
        int aw = (wa.right - wa.left) * 9 / 10, ah = (wa.bottom - wa.top) * 9 / 10, gw = g_disp.gw, gh = g_disp.gh;
        int cw = aw, ch = (int)((long long)aw * gh / gw);
        if (ch > ah) { ch = ah; cw = (int)((long long)ah * gw / gh); }
        DWORD st = WS_OVERLAPPEDWINDOW | WS_VISIBLE;
        RECT r = { 0, 0, cw, ch };
        AdjustWindowRect(&r, st, FALSE);
        int ww = r.right - r.left, wh = r.bottom - r.top;
        SetWindowLongA(h, GWL_STYLE, st);
        SetWindowPos(h, HWND_NOTOPMOST, wa.left + ((wa.right - wa.left) - ww) / 2, wa.top + ((wa.bottom - wa.top) - wh) / 2,
                     ww, wh, SWP_FRAMECHANGED | SWP_SHOWWINDOW);
    }
    calc_dest();
    sgr_d3d9_reset();
    InvalidateRect(h, NULL, TRUE);
    apply_clip();
    sgr_log("window: %s, client -> frame %ldx%ld at %ld,%ld", g_disp.windowed ? "windowed" : "full screen",
            g_disp.dest.right - g_disp.dest.left, g_disp.dest.bottom - g_disp.dest.top, g_disp.dest.left, g_disp.dest.top);
}

static LRESULT CALLBACK sg_wndproc(HWND h, UINT m, WPARAM w, LPARAM l)
{
    switch (m) {
    case WM_MOUSEMOVE: case WM_LBUTTONDOWN: case WM_LBUTTONUP: case WM_LBUTTONDBLCLK:
    case WM_RBUTTONDOWN: case WM_RBUTTONUP: case WM_RBUTTONDBLCLK:
    case WM_MBUTTONDOWN: case WM_MBUTTONUP: case WM_MBUTTONDBLCLK: {
        int gx, gy;
        if (m == WM_MOUSEMOVE) {              /* WM_SETCURSOR does not come while the game holds the mouse capture */
            int over = sghud_over((short)LOWORD(l), (short)HIWORD(l));
            if (over != g_over_hud) { cursor_apply(over); SetCursor(over ? hud_cursor() : NULL); }
        }
        int hr = sghud_mouse(m, (short)LOWORD(l), (short)HIWORD(l), w);
        if (hr == 1) return 0;
        if (hr == 3) { sghud_mapped(&gx, &gy); l = MAKELPARAM(gx, gy); break; }   /* the login screen's new look */
        client_to_game((short)LOWORD(l), (short)HIWORD(l), &gx, &gy);
        if (hr == 2) {                        /* over the HUD: the game sees the move, kept off the edges (no scroll) */
            int gw = g_disp.gw ? g_disp.gw : 800, gh = g_disp.gh ? g_disp.gh : 600;
            if (gx < 16) gx = 16; if (gx > gw - 17) gx = gw - 17;
            if (gy < 16) gy = 16; if (gy > gh - 17) gy = gh - 17;
        }
        l = MAKELPARAM(gx, gy);
        break;
    }
    case WM_KEYDOWN:
        if (w == VK_F11 && (GetKeyState(VK_CONTROL) & 0x8000)) {   /* (18:56) Ctrl+F11: sharp -> smooth -> hq */
            static const char *FN[3] = { "sharp", "smooth", "hq" };
            g_disp.smooth = (g_disp.smooth + 1) % 3;
            WritePrivateProfileStringA("display", "filter", FN[g_disp.smooth], ".\\GORender.ini");
            sgr_log("display: filter %s (Ctrl+F11)", FN[g_disp.smooth]);
            InvalidateRect(h, NULL, FALSE);
            return 0;
        }
        sghud_key(m, w);
        break;
    case WM_SYSKEYDOWN:
        if (w == VK_RETURN && (l & (1 << 29))) { g_disp.windowed = !g_disp.windowed; sgr_window_apply(); return 0; }
        break;
    case WM_SYSCHAR:
        if (w == VK_RETURN) return 0;
        break;
    case WM_SIZE:
        calc_dest(); sgr_d3d9_reset(); InvalidateRect(h, NULL, TRUE);
        break;
    case WM_ERASEBKGND:
        return 1;
    case WM_PAINT: {
        PAINTSTRUCT ps; BeginPaint(h, &ps); EndPaint(h, &ps);
        sgr_present();
        return 0;
    }
    case WM_SETCURSOR:
        if (LOWORD(l) == HTCLIENT) {          /* the game draws its own cursor; over the HUD (drawn above it) Windows' */
            POINT p; GetCursorPos(&p); ScreenToClient(h, &p);
            int over = sghud_over(p.x, p.y);
            cursor_apply(over);
            SetCursor(over ? hud_cursor() : NULL);
            return TRUE;
        }
        break;
    case WM_ACTIVATEAPP:
        g_disp.active = (w != 0);
        apply_clip();
        break;
    }
    return CallWindowProcA(g_orig_proc, h, m, w, l);
}

/* (user 10-29 21:34 "no NEXON logo and movies"): the intro movies (nexonci1 / intro / intro2.bik) play inside the logo
 * window's constructor (0053cd10 -> 0041d1b0, its own message loop, before any frame).  BinkOpen (import, .rdata) returns
 * NULL for exactly those three calls: 0041d1b0 then returns at once.  Caller check: our return address is 0041d239,
 * 0041d1b0's own one (at entry esp + 0x34) is one of the three calls in 0053cd10.  [hud] skip_intro=0 keeps them. */
static void *(WINAPI *real_BinkOpen)(void *, unsigned);
static void *WINAPI hook_BinkOpen(void *name, unsigned flags)
{
    static int skip = -1;
    if (skip < 0) skip = GetPrivateProfileIntA("hud", "skip_intro", 1, ".\\GORender.ini") != 0;
    volatile DWORD *sp = (volatile DWORD *)((UINT_PTR)&name - 4);    /* entry esp: our return address */
    if (skip && sp[0] == 0x41d239) {
        DWORD cr = sp[13];
        if (cr == 0x53cdc9 || cr == 0x53cddd || cr == 0x53cdf1) { sgr_log("intro movie skipped (%x)", (unsigned)cr); return NULL; }
    }
    return real_BinkOpen(name, flags);
}

/* (user 10-29 22:30 "name a battle recording after the planet it was fought on"): the recorder (0057ade0) writes
 * .\Record\SS<yyyymmdd><NN>.rcd (fopen "wb" -> CreateFileA, CREATE_ALWAYS); the planet + province of the battle
 * (sghud_rec_prefix) go in front: .\Record\<planet>_<province>_SS<yyyymmdd><NN>.rcd (_2, _3 .. if it exists). The
 * briefing room lists every *.rcd and plays it by that name. */
int sghud_rec_prefix(char *buf, int n);
static HANDLE (WINAPI *real_CreateFileA)(LPCSTR, DWORD, DWORD, LPSECURITY_ATTRIBUTES, DWORD, DWORD, HANDLE);
static HANDLE WINAPI hook_CreateFileA(LPCSTR fn, DWORD acc, DWORD sh, LPSECURITY_ATTRIBUTES sa, DWORD disp, DWORD fl, HANDLE tpl)
{
    char pre[96], nm[MAX_PATH];
    if (fn && sgr_debug() && strstr(fn, "Record")) sgr_log("CreateFileA %s acc %lx disp %lu", fn, (unsigned long)acc, (unsigned long)disp);
    if (fn && (acc & GENERIC_WRITE) && disp == CREATE_ALWAYS && !_strnicmp(fn, ".\\Record\\SS", 11) && strlen(fn) < 64 &&
        sghud_rec_prefix(pre, sizeof pre)) {
        wsprintfA(nm, ".\\Record\\%s_%s", pre, fn + 9);
        for (int k = 2; k < 100 && GetFileAttributesA(nm) != INVALID_FILE_ATTRIBUTES; k++) {
            int L = lstrlenA(fn + 9) - 4;                       /* before ".rcd" */
            wsprintfA(nm, ".\\Record\\%s_%.*s_%d%s", pre, L, fn + 9, k, fn + 9 + L);
        }
        sgr_log("recording saved as %s", nm);
        return real_CreateFileA(nm, acc, sh, sa, disp, fl, tpl);
    }
    return real_CreateFileA(fn, acc, sh, sa, disp, fl, tpl);
}

void sgr_window_attach(HWND hwnd)
{
    if (g_disp.hwnd == hwnd) return;
    g_disp.hwnd = hwnd;
    g_disp.active = (GetForegroundWindow() == hwnd);
    g_orig_proc = (WNDPROC)SetWindowLongA(hwnd, GWL_WNDPROC, (LONG)sg_wndproc);
    HMODULE exe = GetModuleHandleA(NULL);
    int hooked = 0;
    if (!real_ClipCursor) { real_ClipCursor = (BOOL (WINAPI *)(const RECT *))iat_hook(exe, "USER32.dll", "ClipCursor", (void *)hook_ClipCursor); hooked += real_ClipCursor != NULL; }
    if (!real_SetCursorPos) { real_SetCursorPos = (BOOL (WINAPI *)(int, int))iat_hook(exe, "USER32.dll", "SetCursorPos", (void *)hook_SetCursorPos); hooked += real_SetCursorPos != NULL; }
    if (!real_ShowCursor) {
        real_ShowCursor = (int (WINAPI *)(BOOL))iat_hook(exe, "USER32.dll", "ShowCursor", (void *)hook_ShowCursor);
        hooked += real_ShowCursor != NULL;
        if (real_ShowCursor) { g_game_cur = real_ShowCursor(TRUE) - 1; real_ShowCursor(FALSE); }   /* count so far */
    }
    if (!real_BinkOpen && GetModuleHandleA("binkw32.dll"))
        real_BinkOpen = (void *(WINAPI *)(void *, unsigned))iat_hook(exe, "binkw32.dll", "_BinkOpen@8", (void *)hook_BinkOpen);
    static int cf_hooked;
    if (!real_CreateFileA) {
        real_CreateFileA = (HANDLE (WINAPI *)(LPCSTR, DWORD, DWORD, LPSECURITY_ATTRIBUTES, DWORD, DWORD, HANDLE))
            iat_hook(exe, "KERNEL32.dll", "CreateFileA", (void *)hook_CreateFileA);
        cf_hooked = real_CreateFileA != NULL;
    }
    if (!real_CreateFileA) real_CreateFileA = CreateFileA;
    if (!real_ClipCursor) real_ClipCursor = ClipCursor;
    if (!real_SetCursorPos) real_SetCursorPos = SetCursorPos;
    sgr_log("window %p attached (%d cursor import(s) hooked, BinkOpen %s, CreateFileA %s)", hwnd, hooked, real_BinkOpen ? "hooked" : "-",
            cf_hooked ? "hooked" : "-");
}

/* ---- the native-resolution overlay (phase 3 HUD) ------------------------------------------------------------- */
static SGOverlay g_ov;
static HBITMAP g_ov_bmp, g_ov_old;
static int g_ov_dirty = 1, g_ov_shown;
static HDC g_comp_dc; static HBITMAP g_comp_bmp, g_comp_old; static int g_comp_w, g_comp_h;

void sgr_overlay_invalidate(void) { g_ov_dirty = 1; }
const SGOverlay *sgr_overlay(void) { return g_ov_shown ? &g_ov : NULL; }

static HBITMAP dib32(HDC *dc, HBITMAP *old, int w, int h, unsigned int **bits)
{
    BITMAPINFO bi; memset(&bi, 0, sizeof bi);
    bi.bmiHeader.biSize = sizeof bi.bmiHeader; bi.bmiHeader.biWidth = w; bi.bmiHeader.biHeight = -h;
    bi.bmiHeader.biPlanes = 1; bi.bmiHeader.biBitCount = 32; bi.bmiHeader.biCompression = BI_RGB;
    void *p = NULL;
    HBITMAP b = CreateDIBSection(NULL, &bi, DIB_RGB_COLORS, &p, NULL, 0);
    if (!b) return NULL;
    if (!*dc) *dc = CreateCompatibleDC(NULL);
    HBITMAP o = (HBITMAP)SelectObject(*dc, b);
    if (!*old) *old = o;
    if (bits) *bits = (unsigned int *)p;
    return b;
}

static void overlay_update(int cw, int ch)
{
    if (g_ov.w != cw || g_ov.h != ch || !g_ov_bmp) {
        if (g_ov_bmp) { SelectObject(g_ov.dc, g_ov_old); DeleteObject(g_ov_bmp); g_ov_bmp = NULL; g_ov_old = NULL; }
        g_ov_bmp = dib32(&g_ov.dc, &g_ov_old, cw, ch, &g_ov.bits);
        if (!g_ov_bmp) { g_ov_shown = 0; return; }
        g_ov.w = cw; g_ov.h = ch; g_ov_dirty = 1;
    }
    if (!g_ov_dirty) return;
    g_ov_dirty = 0;
    /* (11-01) no full clear: the HUD keeps the overlay in step and copies only what changed (g_ov.dx0..dy1) */
    g_ov_shown = sgr_overlay_paint(&g_ov);
    GdiFlush();
    g_ov.version++;
}

/* ---- present ---------------------------------------------------------------------------------------------------- */
static LARGE_INTEGER g_qpf; static double g_pt_sum, g_pt_max; static int g_pt_n; static DWORD g_pt_t0;
static void present_inner(void);
void sgr_present(void)
{
    LARGE_INTEGER a, b;
    if (!g_qpf.QuadPart) QueryPerformanceFrequency(&g_qpf);
    QueryPerformanceCounter(&a);
    present_inner();
    QueryPerformanceCounter(&b);
    double ms = (double)(b.QuadPart - a.QuadPart) * 1000.0 / (double)g_qpf.QuadPart;
    g_pt_sum += ms; if (ms > g_pt_max) g_pt_max = ms; g_pt_n++;
    DWORD now = GetTickCount();
    if (!g_pt_t0) g_pt_t0 = now;
    if (now - g_pt_t0 >= 30000) {
        sgr_log("present: %d frames, %.2f ms average, %.1f ms max (%s)", g_pt_n, g_pt_sum / g_pt_n, g_pt_max, sgr_presenter_name());
        g_pt_sum = g_pt_max = 0; g_pt_n = 0; g_pt_t0 = now;
    }
}

/* (2026-11-02, user 15:25 "登入时旧的画面会跑出来, 请帮我删除但是保留音效"): at start-up the game draws its own logo and
   the galaxy title page for ~1.5 s before the HUD's first picture (the start screen of the new look) is ready - those
   frames are presented BLACK instead (only the picture: the game runs and sounds as before).  Ends for good with the
   first HUD picture, or after 20 s, or at once with [hud] enable=0 / skip_intro=0. */
int g_hide_game;
static void boot_hide_update(void)
{
    static int done, cfg = -1; static DWORD t0;
    if (done) { g_hide_game = 0; return; }
    if (cfg < 0) cfg = GetPrivateProfileIntA("hud", "enable", 1, ".\\GORender.ini") && GetPrivateProfileIntA("hud", "skip_intro", 1, ".\\GORender.ini");
    if (!t0) t0 = GetTickCount();
    if (!cfg || g_ov_shown || GetTickCount() - t0 > 20000) {
        done = 1; g_hide_game = 0;
        sgr_log("start-up: game picture shown after %lu ms (%s)", GetTickCount() - t0, !cfg ? "off" : g_ov_shown ? "HUD picture ready" : "time-out");
        return;
    }
    g_hide_game = 1;
}

static void present_inner(void)
{
    HWND h = g_disp.hwnd;
    if (!h || !g_disp.primary || IsIconic(h)) return;
    RECT c; GetClientRect(h, &c);
    if (c.right <= 0 || c.bottom <= 0) return;
    if (g_disp.dest.right <= g_disp.dest.left) calc_dest();
    overlay_update(c.right, c.bottom);
    boot_hide_update();
    if (g_d3d_ok != 0) {
        int r = sgr_d3d9_present(h, &c, &g_disp.dest);
        if (r) { if (g_d3d_ok != 1) { g_d3d_ok = 1; sgr_log("presenter: d3d9"); } return; }
        g_d3d_ok = 0;
        sgr_log("presenter: gdi (d3d9 not available)");
    }
    unsigned char *bits; int pitch, w, hh;
    if (!sgr_primary_info(&bits, &pitch, &w, &hh)) return;
    struct { BITMAPINFOHEADER h; DWORD m[3]; } bi;
    memset(&bi, 0, sizeof bi);
    bi.h.biSize = sizeof bi.h; bi.h.biWidth = pitch / 2; bi.h.biHeight = -hh; bi.h.biPlanes = 1; bi.h.biBitCount = 16;
    bi.h.biCompression = BI_BITFIELDS; bi.m[0] = 0xf800; bi.m[1] = 0x07e0; bi.m[2] = 0x001f;
    HDC dc = GetDC(h);
    RECT *d = &g_disp.dest;
    HDC out = dc;
    if (g_ov_shown) {                                       /* compose off screen: frame, then the overlay */
        if (g_comp_w != c.right || g_comp_h != c.bottom || !g_comp_bmp) {
            if (g_comp_bmp) { SelectObject(g_comp_dc, g_comp_old); DeleteObject(g_comp_bmp); g_comp_bmp = NULL; g_comp_old = NULL; }
            g_comp_bmp = dib32(&g_comp_dc, &g_comp_old, c.right, c.bottom, NULL);
            g_comp_w = c.right; g_comp_h = c.bottom;
        }
        if (g_comp_bmp) out = g_comp_dc;
    }
    HBRUSH black = (HBRUSH)GetStockObject(BLACK_BRUSH);
    RECT bar;
    if (d->left > 0) { SetRect(&bar, 0, 0, d->left, c.bottom); FillRect(out, &bar, black); SetRect(&bar, d->right, 0, c.right, c.bottom); FillRect(out, &bar, black); }
    if (d->top > 0) { SetRect(&bar, 0, 0, c.right, d->top); FillRect(out, &bar, black); SetRect(&bar, 0, d->bottom, c.right, c.bottom); FillRect(out, &bar, black); }
    SetStretchBltMode(out, COLORONCOLOR);     /* HALFTONE costs 5x (measured: 12 vs 62 frames/s): smooth = D3D9 only */
    SetBrushOrgEx(out, 0, 0, NULL);
    if (g_hide_game) FillRect(out, d, black);
    else StretchDIBits(out, d->left, d->top, d->right - d->left, d->bottom - d->top, 0, 0, w, hh, bits, (BITMAPINFO *)&bi, DIB_RGB_COLORS, SRCCOPY);
    if (out != dc) {
        BLENDFUNCTION bf = { AC_SRC_OVER, 0, 255, AC_SRC_ALPHA };
        AlphaBlend(out, 0, 0, c.right, c.bottom, g_ov.dc, 0, 0, g_ov.w, g_ov.h, bf);
        BitBlt(dc, 0, 0, c.right, c.bottom, out, 0, 0, SRCCOPY);
    }
    ReleaseDC(h, dc);
}
