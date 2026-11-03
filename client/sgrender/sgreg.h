/* sgreg.h - included by ddraw_proxy.c (2026-11-02, user 16:40 "游戏设定 Software\Nexon\TacticalCommanders, 名称也改成
 * Galactic Overlord, 去掉 Nexon\TacticalCommanders").  F54 renamed the game's registry keys in SG.exe:
 *   HKCU / HKLM  SOFTWARE\Nexon\TacticalCommanders  ->  SOFTWARE\Galactic Overlord   (the settings: REG_NAME, REG_SG_IP ...)
 *   HKLM         SOFTWARE\Nexon\ (value TC_QSN)       ->  "SOFTWARE\GO\" in the exe (16-byte slot), opened here as
 *                                                        SOFTWARE\Galactic Overlord (RegCreateKeyExA hook)
 * reg_migrate(): at the first start of the renamed game, the old key's values and sub-keys are copied to the new key
 * (values the new key has already - REG_SG_IP written by the launcher - are kept; once: value "MigratedFromNexon"),
 * so the saved ID, quick-menu states and options stay. */
#define REG_NEW "SOFTWARE\\Galactic Overlord"
#define REG_OLD "SOFTWARE\\Nexon\\TacticalCommanders"

static void reg_copy(HKEY src, HKEY dst, int depth)
{
    char name[256]; BYTE data[4096]; DWORD i, nl, dl, type;
    for (i = 0;; i++) {
        nl = sizeof name; dl = sizeof data;
        LONG r = RegEnumValueA(src, i, name, &nl, NULL, &type, data, &dl);
        if (r == ERROR_NO_MORE_ITEMS) break;
        DWORD t2, l2 = 0;                        /* a value already in the new key (REG_SG_IP the launcher wrote) wins */
        if (r == ERROR_SUCCESS && RegQueryValueExA(dst, name, NULL, &t2, NULL, &l2) != ERROR_SUCCESS)
            RegSetValueExA(dst, name, 0, type, data, dl);
    }
    if (depth > 4) return;
    for (i = 0;; i++) {
        nl = sizeof name;
        LONG r = RegEnumKeyExA(src, i, name, &nl, NULL, NULL, NULL, NULL);
        if (r == ERROR_NO_MORE_ITEMS) break;
        if (r != ERROR_SUCCESS) continue;
        HKEY s2, d2;
        if (RegOpenKeyExA(src, name, 0, KEY_READ, &s2) != ERROR_SUCCESS) continue;
        if (RegCreateKeyExA(dst, name, 0, NULL, 0, KEY_ALL_ACCESS, NULL, &d2, NULL) == ERROR_SUCCESS) {
            reg_copy(s2, d2, depth + 1); RegCloseKey(d2);
        }
        RegCloseKey(s2);
    }
}

static void reg_migrate(void)
{
    HKEY roots[2] = { HKEY_CURRENT_USER, HKEY_LOCAL_MACHINE };
    for (int i = 0; i < 2; i++) {
        HKEY n, o; DWORD disp = 0;
        if (RegOpenKeyExA(roots[i], REG_OLD, 0, KEY_READ, &o) != ERROR_SUCCESS) continue;
        if (RegCreateKeyExA(roots[i], REG_NEW, 0, NULL, 0, KEY_ALL_ACCESS, NULL, &n, &disp) == ERROR_SUCCESS) {
            DWORD t2, l2 = 0, one = 1;
            if (RegQueryValueExA(n, "MigratedFromNexon", NULL, &t2, NULL, &l2) != ERROR_SUCCESS) {
                reg_copy(o, n, 0);
                RegSetValueExA(n, "MigratedFromNexon", 0, REG_DWORD, (const BYTE *)&one, 4);
            }
            RegCloseKey(n);
        }
        RegCloseKey(o);
    }
    {   /* HKLM SOFTWARE\Nexon value TC_QSN */
        HKEY o, n; BYTE data[64]; DWORD dl = sizeof data, type;
        if (RegOpenKeyExA(HKEY_LOCAL_MACHINE, "SOFTWARE\\Nexon", 0, KEY_READ, &o) == ERROR_SUCCESS) {
            if (RegQueryValueExA(o, "TC_QSN", NULL, &type, data, &dl) == ERROR_SUCCESS &&
                RegCreateKeyExA(HKEY_LOCAL_MACHINE, REG_NEW, 0, NULL, 0, KEY_ALL_ACCESS, NULL, &n, NULL) == ERROR_SUCCESS) {
                DWORD t2, l2 = 0;
                if (RegQueryValueExA(n, "TC_QSN", NULL, &t2, NULL, &l2) != ERROR_SUCCESS) RegSetValueExA(n, "TC_QSN", 0, type, data, dl);
                RegCloseKey(n);
            }
            RegCloseKey(o);
        }
    }
}

typedef LONG (WINAPI *RegCreateKeyExA_t)(HKEY, LPCSTR, DWORD, LPSTR, DWORD, REGSAM, const LPSECURITY_ATTRIBUTES, PHKEY, LPDWORD);
static RegCreateKeyExA_t o_RegCreateKeyExA;
static LONG WINAPI h_RegCreateKeyExA(HKEY k, LPCSTR sub, DWORD r, LPSTR cls, DWORD opt, REGSAM sam, const LPSECURITY_ATTRIBUTES sa, PHKEY out, LPDWORD disp)
{
    if (sub && !lstrcmpiA(sub, "SOFTWARE\\GO\\")) sub = REG_NEW;
    return o_RegCreateKeyExA(k, sub, r, cls, opt, sam, sa, out, disp);
}

static void sgreg_install(void)
{
    reg_migrate();
    o_RegCreateKeyExA = (RegCreateKeyExA_t)iat_hook(GetModuleHandleA(NULL), "ADVAPI32.dll", "RegCreateKeyExA", (void *)h_RegCreateKeyExA);
    if (!o_RegCreateKeyExA) o_RegCreateKeyExA = RegCreateKeyExA;
}
