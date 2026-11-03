/* sgnames.h - included by ddraw_proxy.c (2026-11-02, user 16:53 "SG 改成 GO" for the files too).  The game folder's
 * files are now GO.exe, GO_debug.exe, GOLauncher.exe, GORelay.exe, GORender.dll (+ .ini / .log), GOHud.pak.
 *  - render_dll(): GORender.dll, else an old SGRender.dll (a folder the launcher has not updated yet)
 *  - SG.exe's own F48 loader asks for "SGRender.dll" (a string in .dbgmov, inside the code checksum - not changed):
 *    its LoadLibraryA import is hooked and given the DLL found by render_dll()
 *  - names_migrate(): SGRender.ini (the player's display / HUD settings) -> GORender.ini once */
static const char *render_dll(void)
{
    return GetFileAttributesA("GORender.dll") != INVALID_FILE_ATTRIBUTES ? "GORender.dll" : "SGRender.dll";
}

typedef HMODULE (WINAPI *LoadLibraryA_t)(LPCSTR);
static LoadLibraryA_t o_LoadLibraryA;
static HMODULE WINAPI h_LoadLibraryA(LPCSTR n)
{
    if (n && !lstrcmpiA(n, "SGRender.dll")) n = render_dll();
    return o_LoadLibraryA(n);
}

static void names_install(void)
{
    if (GetFileAttributesA("GORender.ini") == INVALID_FILE_ATTRIBUTES && GetFileAttributesA("SGRender.ini") != INVALID_FILE_ATTRIBUTES)
        CopyFileA("SGRender.ini", "GORender.ini", TRUE);
    o_LoadLibraryA = (LoadLibraryA_t)iat_hook(GetModuleHandleA(NULL), "KERNEL32.dll", "LoadLibraryA", (void *)h_LoadLibraryA);
    if (!o_LoadLibraryA) o_LoadLibraryA = LoadLibraryA;
}
