/* ddraw.dll - the game folder's DirectDraw (2026-10-28, phase 2 of the drawing-layer plan).
 * SG.exe imports DirectDrawCreate from DDRAW.dll; this proxy sends it to SGRender.dll's own DirectDraw
 * (SGR_DirectDrawCreate, sgdraw.c).  Fallbacks, in order: cnc-ddraw (shipped as ddraw_cnc.dll, the presenter used
 * until 1.0.48), then the system's ddraw.dll.  SGRender.ini [display] backend=cnc picks cnc-ddraw directly.
 * Build: i686-w64-mingw32-gcc -O2 -shared -static-libgcc -o ddraw.dll ddraw_proxy.c ddraw_proxy.def */
#include <windows.h>
#include "sgcrypt_hooks.h"
#include "sglaunch_guard.h"
#include "sgreg.h"
#include "sgnames.h"
typedef HRESULT (WINAPI *create_fn)(GUID *, void **, IUnknown *);
static HMODULE g_sys;
static HMODULE sys_ddraw(void)
{
    if (!g_sys) {
        char p[MAX_PATH]; UINT n = GetSystemDirectoryA(p, MAX_PATH - 12);
        lstrcpyA(p + n, "\\ddraw.dll");
        g_sys = LoadLibraryA(p);
    }
    return g_sys;
}
HRESULT WINAPI DirectDrawCreate(GUID *g, void **o, IUnknown *u)
{
    static create_fn target;
    if (!target) {
        char v[16];
        GetPrivateProfileStringA("display", "backend", "auto", v, sizeof v, ".\\GORender.ini");
        if (lstrcmpiA(v, "cnc")) {
            HMODULE m = LoadLibraryA(render_dll());      /* (11-02) GORender.dll (sgnames.h) */
            if (m) target = (create_fn)GetProcAddress(m, "SGR_DirectDrawCreate");
        }
        if (!target) {
            HMODULE c = LoadLibraryA("ddraw_cnc.dll");
            if (c) target = (create_fn)GetProcAddress(c, "DirectDrawCreate");
        }
        if (!target && sys_ddraw()) target = (create_fn)GetProcAddress(sys_ddraw(), "DirectDrawCreate");
        if (!target) return E_FAIL;
    }
    return target(g, o, u);
}
#define FWD(name, args, call) \
    HRESULT WINAPI name args { FARPROC fp_ = sys_ddraw() ? GetProcAddress(sys_ddraw(), #name) : NULL; \
        return fp_ ? ((HRESULT (WINAPI *) args)fp_) call : E_FAIL; }
FWD(DirectDrawCreateEx, (GUID *g, void **o, REFIID r, IUnknown *u), (g, o, r, u))
FWD(DirectDrawCreateClipper, (DWORD f, void **c, IUnknown *u), (f, c, u))
FWD(DirectDrawEnumerateA, (void *cb, void *ctx), (cb, ctx))
FWD(DirectDrawEnumerateW, (void *cb, void *ctx), (cb, ctx))
FWD(DirectDrawEnumerateExA, (void *cb, void *ctx, DWORD f), (cb, ctx, f))
FWD(DirectDrawEnumerateExW, (void *cb, void *ctx, DWORD f), (cb, ctx, f))

/* (2026-11-02) the encrypted files and connection: hooks installed before the game's own code runs */
BOOL WINAPI DllMain(HINSTANCE h, DWORD why, LPVOID r)
{
    (void)r;
    if (why == DLL_PROCESS_ATTACH) { DisableThreadLibraryCalls(h); launch_guard(); sgcrypt_install(); sgreg_install(); names_install(); }
    return TRUE;
}
