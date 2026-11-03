/* sglaunch_guard.h - included by ddraw_proxy.c (2026-11-02, user 16:11 "SGLauncher.exe是否能直接取代SG.exe" -> "加上").
 * The game started WITHOUT the launcher (a double click on SG.exe / SG_debug.exe in the folder) starts SGLauncher.exe
 * instead and ends at once: the launcher updates the files, starts the UDP relay, sets the server address, then starts
 * the game itself.  Runs in ddraw.dll's DllMain, before any game code.
 * The game is let through when: its parent process is SGLauncher*.exe; the parent is gone already (the launcher closes
 * right after starting the game) or cannot be read; there is no SGLauncher.exe in the folder; the folder has a file
 * nolauncher.txt, or the environment has SG_DIRECT=1 (tests, debugging). */
#include <tlhelp32.h>

static int lg_parent_is_launcher(int *known)
{
    *known = 0;
    DWORD me = GetCurrentProcessId(), parent = 0;
    HANDLE sn = CreateToolhelp32Snapshot(TH32CS_SNAPPROCESS, 0);
    if (sn == INVALID_HANDLE_VALUE) return 0;
    PROCESSENTRY32W pe; pe.dwSize = sizeof pe;
    for (BOOL ok = Process32FirstW(sn, &pe); ok; ok = Process32NextW(sn, &pe))
        if (pe.th32ProcessID == me) { parent = pe.th32ParentProcessID; break; }
    int is = 0;
    if (parent) {
        pe.dwSize = sizeof pe;
        for (BOOL ok = Process32FirstW(sn, &pe); ok; ok = Process32NextW(sn, &pe))
            if (pe.th32ProcessID == parent) {
                *known = 1;
                WCHAR n[11]; lstrcpynW(n, pe.szExeFile, 11);
                is = !lstrcmpiW(n, L"GOLauncher") || !lstrcmpiW(n, L"SGLauncher");   /* (11-02) GO names; SG = older */
                break;
            }
    }
    CloseHandle(sn);
    return is;
}

static void launch_guard(void)
{
    WCHAR exe[MAX_PATH], dir[MAX_PATH], la[MAX_PATH + 2], *base;
    char env[8];
    if (GetEnvironmentVariableA("SG_DIRECT", env, sizeof env) && env[0] == '1') return;
    if (!GetModuleFileNameW(NULL, exe, MAX_PATH)) return;
    base = exe; for (WCHAR *p = exe; *p; p++) if (*p == L'\\' || *p == L'/') base = p + 1;
    if (lstrcmpiW(base, L"GO.exe") && lstrcmpiW(base, L"GO_debug.exe") &&
        lstrcmpiW(base, L"SG.exe") && lstrcmpiW(base, L"SG_debug.exe")) return;   /* only the game itself */
    lstrcpynW(dir, exe, (int)(base - exe) + 1);                                  /* the folder, with its '\' */
    lstrcpyW(la, dir); lstrcatW(la, L"nolauncher.txt");
    if (GetFileAttributesW(la) != INVALID_FILE_ATTRIBUTES) return;
    lstrcpyW(la, dir); lstrcatW(la, L"GOLauncher.exe");
    if (GetFileAttributesW(la) == INVALID_FILE_ATTRIBUTES) { lstrcpyW(la, dir); lstrcatW(la, L"SGLauncher.exe"); }
    if (GetFileAttributesW(la) == INVALID_FILE_ATTRIBUTES) return;
    int known, isl = lg_parent_is_launcher(&known);
    if (isl || !known) return;
    WCHAR cmd[MAX_PATH + 4]; lstrcpyW(cmd, L"\""); lstrcatW(cmd, la); lstrcatW(cmd, L"\"");
    STARTUPINFOW si; PROCESS_INFORMATION pi;
    memset(&si, 0, sizeof si); si.cb = sizeof si;
    if (!CreateProcessW(la, cmd, NULL, NULL, FALSE, 0, NULL, dir, &si, &pi)) return;   /* cannot: play on */
    CloseHandle(pi.hThread); CloseHandle(pi.hProcess);
    TerminateProcess(GetCurrentProcess(), 0);
}
