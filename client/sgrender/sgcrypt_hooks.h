/* sgcrypt_hooks.h - included by ddraw_proxy.c (the game folder's ddraw.dll, loaded with SG.exe at start-up, before the
 * game opens a file or a connection).  2026-11-02, user 13:56 "1/2/3都要加密".
 *
 * 1. ENCRYPTED GAME FILES: a file ending in the "SGCRYPT2" trailer (format: sgcrypt.h) is AES-128-CTR encrypted chunk by
 *    chunk with SGFILE_KEY (tools/sgcrypt_files.py makes them at publish).  Hooks in the import tables of SG.exe,
 *    binkw32.dll and mss32.dll: CreateFileA / OpenFile (a read-only open of such a file is remembered), ReadFile (decrypts
 *    what was read, at the file position), CreateFileMappingA + MapViewOfFile (a view of such a file = a private copy,
 *    read and decrypted; UnmapViewOfFile frees it), CloseHandle.  Files without the trailer are untouched.
 * 2. ENCRYPTED CONNECTION (tools/sgnet.py has the protocol): SG.exe's connect / send / recv / closesocket.  Right after a
 *    connect the hook sends HELLO = "SGX1" + a fresh X25519 public key; both directions are then AES-128-CTR. */
#include <winsock.h>
#include <stdarg.h>
#include <string.h>
#include "sgcrypt.h"
#include "sgfile_key.h"
#ifdef SGNET_TEST_PUB_H
#include SGNET_TEST_PUB_H                  /* local tests: a test key, never the real one */
#else
#include "sgnet_pub.h"
#endif

static CRITICAL_SECTION g_cs;
static SgcAes g_fkey;
static void sgclog(const char *fmt, ...)
{
    char b[512]; va_list a; va_start(a, fmt); int n = wvsprintfA(b, fmt, a); va_end(a);
    HANDLE f = CreateFileA("GOCrypt.log", FILE_APPEND_DATA, FILE_SHARE_READ | FILE_SHARE_WRITE, NULL, OPEN_ALWAYS, 0, NULL);
    if (f != INVALID_HANDLE_VALUE) { DWORD w; WriteFile(f, b, n, &w, NULL); WriteFile(f, "\r\n", 2, &w, NULL); CloseHandle(f); }
}

/* ---- import-table hooks -------------------------------------------------------------------------------------------- */
/* by name, or by ordinal (ord != 0): SG.exe imports WSOCK32 by ordinal (connect 4, send 19, recv 16, closesocket 3) */
static void *iat_hook_o(HMODULE m, const char *dll, const char *fn, WORD ord, void *nf)
{
    if (!m) return NULL;
    IMAGE_NT_HEADERS *nt = (IMAGE_NT_HEADERS *)((char *)m + ((IMAGE_DOS_HEADER *)m)->e_lfanew);
    IMAGE_DATA_DIRECTORY dd = nt->OptionalHeader.DataDirectory[IMAGE_DIRECTORY_ENTRY_IMPORT];
    if (!dd.VirtualAddress) return NULL;
    void *old = NULL;
    for (IMAGE_IMPORT_DESCRIPTOR *id = (IMAGE_IMPORT_DESCRIPTOR *)((char *)m + dd.VirtualAddress); id->Name; id++) {
        if (lstrcmpiA((char *)m + id->Name, dll)) continue;
        IMAGE_THUNK_DATA *ot = (IMAGE_THUNK_DATA *)((char *)m + (id->OriginalFirstThunk ? id->OriginalFirstThunk : id->FirstThunk));
        IMAGE_THUNK_DATA *ft = (IMAGE_THUNK_DATA *)((char *)m + id->FirstThunk);
        for (; ot->u1.AddressOfData; ot++, ft++) {
            if (IMAGE_SNAP_BY_ORDINAL(ot->u1.Ordinal)) {
                if (!ord || IMAGE_ORDINAL(ot->u1.Ordinal) != ord) continue;
            } else {
                IMAGE_IMPORT_BY_NAME *ibn = (IMAGE_IMPORT_BY_NAME *)((char *)m + ot->u1.AddressOfData);
                if (strcmp((char *)ibn->Name, fn)) continue;
            }
            DWORD pr;
            if (!VirtualProtect(&ft->u1.Function, sizeof ft->u1.Function, PAGE_READWRITE, &pr)) continue;
            old = (void *)ft->u1.Function;
            ft->u1.Function = (DWORD_PTR)nf;
            VirtualProtect(&ft->u1.Function, sizeof ft->u1.Function, pr, &pr);
        }
    }
    return old;
}
static void *iat_hook(HMODULE m, const char *dll, const char *fn, void *nf) { return iat_hook_o(m, dll, fn, 0, nf); }

/* ---- 1. encrypted files (format 2: sgcrypt.h) ------------------------------------------------------------------- */
typedef struct { int ref; SgcIdx x; } CIdx;      /* shared by a file handle and the mapping made from it */
typedef struct { HANDLE h; HANDLE map; CIdx *ix; uint64_t plain, total; } CFile;
#define SGCF_MAX 64
static CFile g_cf[SGCF_MAX];
#define SGCV_MAX 64
static void *g_cv[SGCV_MAX];
static CFile *cf_find(HANDLE h)
{
    for (int i = 0; i < SGCF_MAX; i++) if (g_cf[i].h && g_cf[i].h == h) return &g_cf[i];
    return NULL;
}
static CFile *cf_find_map(HANDLE m)
{
    for (int i = 0; i < SGCF_MAX; i++) if (g_cf[i].map && g_cf[i].map == m) return &g_cf[i];
    return NULL;
}
static void cf_drop(CFile *e)                     /* (under g_cs) */
{
    if (e->ix && --e->ix->ref == 0) { sgc_idx_free(&e->ix->x); HeapFree(GetProcessHeap(), 0, e->ix); }
    memset(e, 0, sizeof *e);
}
static void cf_probe(HANDLE h)
{
    LARGE_INTEGER sz, z, cur, at;
    if (!GetFileSizeEx(h, &sz) || sz.QuadPart < SGC_TRAILER) return;
    z.QuadPart = 0;
    if (!SetFilePointerEx(h, z, &cur, FILE_CURRENT)) return;
    uint8_t t[SGC_TRAILER]; DWORD got = 0;
    uint64_t plain = 0; uint32_t n = 0;
    at.QuadPart = sz.QuadPart - SGC_TRAILER;
    int ok = SetFilePointerEx(h, at, NULL, FILE_BEGIN) && ReadFile(h, t, SGC_TRAILER, &got, NULL) && got == SGC_TRAILER
             && sgc_trailer(t, (uint64_t)sz.QuadPart, &plain, &n);
    CIdx *ix = NULL;
    if (ok) {
        uint8_t *raw = (uint8_t *)HeapAlloc(GetProcessHeap(), 0, 12 * (SIZE_T)n + 1);
        ix = (CIdx *)HeapAlloc(GetProcessHeap(), HEAP_ZERO_MEMORY, sizeof *ix);
        at.QuadPart = (LONGLONG)plain;
        ok = raw && ix && SetFilePointerEx(h, at, NULL, FILE_BEGIN)
             && ReadFile(h, raw, 12 * n, &got, NULL) && got == 12 * n && sgc_idx_load(&ix->x, raw, n, plain);
        if (raw) HeapFree(GetProcessHeap(), 0, raw);
        if (!ok) { sgclog("encrypted file with a bad index"); if (ix) HeapFree(GetProcessHeap(), 0, ix); ix = NULL; }
    }
    SetFilePointerEx(h, cur, NULL, FILE_BEGIN);
    if (!ok) return;
    ix->ref = 1;
    EnterCriticalSection(&g_cs);
    int put = 0;
    for (int i = 0; i < SGCF_MAX; i++)
        if (!g_cf[i].h) { g_cf[i].h = h; g_cf[i].map = NULL; g_cf[i].ix = ix; g_cf[i].plain = plain; g_cf[i].total = (uint64_t)sz.QuadPart; put = 1; break; }
    if (!put) { sgclog("too many open encrypted files"); sgc_idx_free(&ix->x); HeapFree(GetProcessHeap(), 0, ix); }
    LeaveCriticalSection(&g_cs);
}
static void cf_decrypt(const CFile *e, uint64_t pos, void *buf, uint64_t n)
{
    sgc_idx_xor(&g_fkey, &e->ix->x, pos, (uint8_t *)buf, (size_t)n);
}
typedef HANDLE (WINAPI *CreateFileA_t)(LPCSTR, DWORD, DWORD, LPSECURITY_ATTRIBUTES, DWORD, DWORD, HANDLE);
typedef HFILE (WINAPI *OpenFile_t)(LPCSTR, LPOFSTRUCT, UINT);
typedef BOOL (WINAPI *ReadFile_t)(HANDLE, LPVOID, DWORD, LPDWORD, LPOVERLAPPED);
typedef HANDLE (WINAPI *CreateFileMappingA_t)(HANDLE, LPSECURITY_ATTRIBUTES, DWORD, DWORD, DWORD, LPCSTR);
typedef LPVOID (WINAPI *MapViewOfFile_t)(HANDLE, DWORD, DWORD, DWORD, SIZE_T);
typedef BOOL (WINAPI *UnmapViewOfFile_t)(LPCVOID);
typedef BOOL (WINAPI *CloseHandle_t)(HANDLE);
/* (2026-11-02, user 16:13 "现在patch不需要Patcher.exe, 请打包安装文件时把这个也去掉"): SG.exe opens patcher.exe (fopen "rb",
   0x544c3d) at start-up only to see that it is there, else "Patcher file not found" and exit.  The launcher does the
   updates now: a missing patcher.exe opens the NUL device instead (the game closes it at once; the old auto-patch at
   0x544600 needs Patch\\Script + Patch\\Info, which are not there, so Patcher.exe is never started). */
static int is_patcher(LPCSTR n)
{
    if (!n) return 0;
    const char *b = n;
    for (const char *p = n; *p; p++) if (*p == '\\' || *p == '/') b = p + 1;
    return !lstrcmpiA(b, "patcher.exe");
}
static HANDLE WINAPI h_CreateFileA(LPCSTR n, DWORD acc, DWORD sh, LPSECURITY_ATTRIBUTES sa, DWORD disp, DWORD fl, HANDLE t)
{
    HANDLE h = CreateFileA(n, acc, sh, sa, disp, fl, t);
    if (h == INVALID_HANDLE_VALUE && disp == OPEN_EXISTING && is_patcher(n) && !(acc & GENERIC_WRITE)
        && GetLastError() == ERROR_FILE_NOT_FOUND)
        return CreateFileA("NUL", GENERIC_READ, FILE_SHARE_READ | FILE_SHARE_WRITE, NULL, OPEN_EXISTING, 0, NULL);
    if (h != INVALID_HANDLE_VALUE && disp == OPEN_EXISTING && !(acc & (GENERIC_WRITE | FILE_WRITE_DATA | FILE_APPEND_DATA)))
        cf_probe(h);
    return h;
}
static HFILE WINAPI h_OpenFile(LPCSTR n, LPOFSTRUCT of, UINT st)
{
    HFILE f = OpenFile(n, of, st);
    if (f != HFILE_ERROR && !(st & (OF_EXIST | OF_PARSE | OF_DELETE | OF_CREATE | OF_WRITE | OF_READWRITE)))
        cf_probe((HANDLE)(INT_PTR)f);
    return f;
}
static BOOL WINAPI h_ReadFile(HANDLE h, LPVOID buf, DWORD n, LPDWORD rd, LPOVERLAPPED ov)
{
    CFile *e = cf_find(h);
    if (!e) return ReadFile(h, buf, n, rd, ov);
    uint64_t pos;
    if (ov) pos = ov->Offset | (uint64_t)ov->OffsetHigh << 32;
    else { LARGE_INTEGER z, cur; z.QuadPart = 0; SetFilePointerEx(h, z, &cur, FILE_CURRENT); pos = (uint64_t)cur.QuadPart; }
    if (pos >= e->plain) n = 0;                   /* the trailer is not part of the file: end of file there */
    else if (n > e->plain - pos) n = (DWORD)(e->plain - pos);
    DWORD got = 0;
    BOOL ok = ReadFile(h, buf, n, &got, ov);
    if (rd) *rd = got;
    if (ok && got) cf_decrypt(e, pos, buf, got);
    else if (!ok && GetLastError() == ERROR_IO_PENDING) sgclog("overlapped read of an encrypted file (not decrypted)");
    return ok;
}
typedef DWORD (WINAPI *SetFilePointer_t)(HANDLE, LONG, PLONG, DWORD);
static DWORD WINAPI h_SetFilePointer(HANDLE h, LONG lo, PLONG hi, DWORD how)
{
    CFile *e = how == FILE_END ? cf_find(h) : NULL;
    if (!e) return SetFilePointer(h, lo, hi, how);
    int64_t d = hi ? ((int64_t)*hi << 32) | (uint32_t)lo : (int64_t)lo;   /* from the end of the PLAIN data */
    int64_t at = (int64_t)e->plain + d;
    LONG h2 = (LONG)(at >> 32);
    DWORD r = SetFilePointer(h, (LONG)(uint32_t)at, &h2, FILE_BEGIN);
    if (hi) *hi = h2;
    return r;
}
static HANDLE WINAPI h_CreateFileMappingA(HANDLE f, LPSECURITY_ATTRIBUTES sa, DWORD pr, DWORD hi, DWORD lo, LPCSTR nm)
{
    HANDLE m = CreateFileMappingA(f, sa, pr, hi, lo, nm);
    if (m) {
        EnterCriticalSection(&g_cs);
        CFile *e = cf_find(f);
        if (e) {
            HANDLE dup = NULL;           /* our own handle: the game may close its file handle while views remain */
            DuplicateHandle(GetCurrentProcess(), f, GetCurrentProcess(), &dup, 0, FALSE, DUPLICATE_SAME_ACCESS);
            for (int i = 0; i < SGCF_MAX; i++)
                if (!g_cf[i].h) { g_cf[i] = *e; g_cf[i].h = dup; g_cf[i].map = m; e->ix->ref++; break; }
        }
        LeaveCriticalSection(&g_cs);
    }
    return m;
}
static LPVOID WINAPI h_MapViewOfFile(HANDLE m, DWORD acc, DWORD hi, DWORD lo, SIZE_T sz)
{
    CFile *e = cf_find_map(m);
    if (!e) return MapViewOfFile(m, acc, hi, lo, sz);
    uint64_t off = (uint64_t)hi << 32 | lo;
    if (off > e->total) { SetLastError(ERROR_INVALID_PARAMETER); return NULL; }
    uint64_t n = sz ? sz : e->total - off;
    void *p = VirtualAlloc(NULL, (SIZE_T)n, MEM_COMMIT | MEM_RESERVE, PAGE_READWRITE);
    if (!p) { sgclog("MapViewOfFile: no memory for %u bytes", (unsigned)n); return NULL; }
    EnterCriticalSection(&g_cs);
    LARGE_INTEGER at, cur, z; z.QuadPart = 0; at.QuadPart = (LONGLONG)off;
    SetFilePointerEx(e->h, z, &cur, FILE_CURRENT);
    SetFilePointerEx(e->h, at, NULL, FILE_BEGIN);
    uint64_t done = 0;
    while (done < n) {
        DWORD want = (DWORD)(n - done > (1u << 24) ? (1u << 24) : n - done), got = 0;
        if (!ReadFile(e->h, (char *)p + done, want, &got, NULL) || !got) break;
        done += got;
    }
    SetFilePointerEx(e->h, cur, NULL, FILE_BEGIN);
    LeaveCriticalSection(&g_cs);
    if (done != n) { sgclog("MapViewOfFile: read %u of %u bytes", (unsigned)done, (unsigned)n); VirtualFree(p, 0, MEM_RELEASE); return NULL; }
    cf_decrypt(e, off, p, n);
    EnterCriticalSection(&g_cs);
    for (int i = 0; i < SGCV_MAX; i++) if (!g_cv[i]) { g_cv[i] = p; break; }
    LeaveCriticalSection(&g_cs);
    return p;
}
static BOOL WINAPI h_UnmapViewOfFile(LPCVOID p)
{
    EnterCriticalSection(&g_cs);
    for (int i = 0; i < SGCV_MAX; i++)
        if (g_cv[i] == p) { g_cv[i] = NULL; LeaveCriticalSection(&g_cs); return VirtualFree((LPVOID)p, 0, MEM_RELEASE); }
    LeaveCriticalSection(&g_cs);
    return UnmapViewOfFile(p);
}

/* ---- 2. encrypted connection ---------------------------------------------------------------------------------------- */
typedef struct { SOCKET s; int hello; SgcAes tx, rx; uint64_t txo, rxo; uint8_t hb[36]; } CConn;
#define CC_MAX 16
static CConn g_cc[CC_MAX];
typedef int (PASCAL *connect_t)(SOCKET, const struct sockaddr *, int);
typedef int (PASCAL *send_t)(SOCKET, const char *, int, int);
typedef int (PASCAL *recv_t)(SOCKET, char *, int, int);
typedef int (PASCAL *closesocket_t)(SOCKET);
static connect_t o_connect; static send_t o_send; static recv_t o_recv; static closesocket_t o_closesocket;
static CConn *cc_find(SOCKET s)
{
    for (int i = 0; i < CC_MAX; i++) if (g_cc[i].s == s && s) return &g_cc[i];
    return NULL;
}
static int rand_bytes(void *p, ULONG n)
{
    typedef BOOLEAN (WINAPI *gen_t)(PVOID, ULONG);
    static gen_t gen;
    if (!gen) { HMODULE a = LoadLibraryA("advapi32.dll"); if (a) gen = (gen_t)GetProcAddress(a, "SystemFunction036"); }
    return gen && gen(p, n);
}
static CConn *cc_new(SOCKET s)
{
    uint8_t sec[32], cpub[32], sh[32], k[32];
    if (!rand_bytes(sec, 32)) { sgclog("connect: no random bytes"); return NULL; }
    sgc_x25519_base(cpub, sec);
    sgc_x25519(sh, sec, SGNET_SERVER_PUB);
    SgcSha h; sgc_sha_init(&h);
    sgc_sha_add(&h, "SGX1", 4); sgc_sha_add(&h, sh, 32); sgc_sha_add(&h, cpub, 32); sgc_sha_add(&h, SGNET_SERVER_PUB, 32);
    sgc_sha_end(&h, k);
    SecureZeroMemory(sec, sizeof sec); SecureZeroMemory(sh, sizeof sh);
    CConn *c = NULL;
    EnterCriticalSection(&g_cs);
    for (int i = 0; i < CC_MAX; i++) if (!g_cc[i].s) { c = &g_cc[i]; break; }
    if (!c) { int i = 0; c = &g_cc[i]; }
    memset(c, 0, sizeof *c);
    c->s = s; c->hello = 1;
    sgc_aes_init(&c->tx, k); sgc_aes_init(&c->rx, k + 16);
    memcpy(c->hb, "SGX1", 4); memcpy(c->hb + 4, cpub, 32);
    LeaveCriticalSection(&g_cs);
    SecureZeroMemory(k, sizeof k);
    return c;
}
static int cc_send_hello(CConn *c)
{
    int done = 0;
    for (int tries = 0; done < 36 && tries < 3000; ) {
        int r = o_send(c->s, (const char *)c->hb + done, 36 - done, 0);
        if (r > 0) { done += r; continue; }
        if (r == SOCKET_ERROR && WSAGetLastError() == WSAEWOULDBLOCK) { Sleep(1); tries++; continue; }
        return 0;
    }
    if (done < 36) return 0;
    c->hello = 0;
    return 1;
}
static int PASCAL h_connect(SOCKET s, const struct sockaddr *a, int l)
{
    int r = o_connect(s, a, l);
    int blocked = r == SOCKET_ERROR && WSAGetLastError() == WSAEWOULDBLOCK;
    if (r == 0 || blocked) {
        CConn *c = cc_new(s);
        if (!c) { WSASetLastError(WSAECONNREFUSED); return SOCKET_ERROR; }
        if (r == 0 && !cc_send_hello(c)) { sgclog("connect: the hello could not be sent"); c->s = 0; WSASetLastError(WSAECONNRESET); return SOCKET_ERROR; }
        if (blocked) WSASetLastError(WSAEWOULDBLOCK);    /* (a non-blocking connect: the hello goes with the first send) */
    }
    return r;
}
static int PASCAL h_send(SOCKET s, const char *buf, int len, int fl)
{
    CConn *c = cc_find(s);
    if (!c || len <= 0) return o_send(s, buf, len, fl);
    if (c->hello && !cc_send_hello(c)) { WSASetLastError(WSAECONNRESET); return SOCKET_ERROR; }
    char stackb[4096];
    char *t = len <= (int)sizeof stackb ? stackb : (char *)HeapAlloc(GetProcessHeap(), 0, len);
    if (!t) { WSASetLastError(WSAENOBUFS); return SOCKET_ERROR; }
    memcpy(t, buf, len);
    sgc_ctr_xor(&c->tx, (const uint8_t *)"\0\0\0\0\0\0\0\0", c->txo, (uint8_t *)t, (size_t)len);
    int r = o_send(s, t, len, fl);
    if (r > 0) c->txo += (uint64_t)r;          /* the rest is sent again by the game later: encrypted from here */
    if (t != stackb) HeapFree(GetProcessHeap(), 0, t);
    return r;
}
static int PASCAL h_recv(SOCKET s, char *buf, int len, int fl)
{
    int r = o_recv(s, buf, len, fl);
    CConn *c = r > 0 ? cc_find(s) : NULL;
    if (c) {
        sgc_ctr_xor(&c->rx, (const uint8_t *)"\0\0\0\0\0\0\0\0", c->rxo, (uint8_t *)buf, (size_t)r);
        if (!(fl & MSG_PEEK)) c->rxo += (uint64_t)r;
    }
    return r;
}
static int PASCAL h_closesocket(SOCKET s)
{
    EnterCriticalSection(&g_cs);
    CConn *c = cc_find(s);
    if (c) SecureZeroMemory(c, sizeof *c);
    LeaveCriticalSection(&g_cs);
    return o_closesocket(s);
}
static BOOL WINAPI h_CloseHandle(HANDLE h)
{
    EnterCriticalSection(&g_cs);
    for (int i = 0; i < SGCF_MAX; i++) {
        if (g_cf[i].map && g_cf[i].map == h) { CloseHandle(g_cf[i].h); cf_drop(&g_cf[i]); }
        else if (!g_cf[i].map && g_cf[i].h == h) cf_drop(&g_cf[i]);
    }
    LeaveCriticalSection(&g_cs);
    return CloseHandle(h);
}

static void sgcrypt_install(void)
{
    InitializeCriticalSection(&g_cs);
    sgc_aes_init(&g_fkey, SGFILE_KEY);
    const char *mods[] = { NULL, "binkw32.dll", "mss32.dll" };
    for (int i = 0; i < 3; i++) {
        HMODULE m = mods[i] ? GetModuleHandleA(mods[i]) : GetModuleHandleA(NULL);
        if (!m) continue;
        iat_hook(m, "KERNEL32.dll", "CreateFileA", (void *)h_CreateFileA);
        iat_hook(m, "KERNEL32.dll", "OpenFile", (void *)h_OpenFile);
        iat_hook(m, "KERNEL32.dll", "ReadFile", (void *)h_ReadFile);
        iat_hook(m, "KERNEL32.dll", "SetFilePointer", (void *)h_SetFilePointer);
        iat_hook(m, "KERNEL32.dll", "CreateFileMappingA", (void *)h_CreateFileMappingA);
        iat_hook(m, "KERNEL32.dll", "MapViewOfFile", (void *)h_MapViewOfFile);
        iat_hook(m, "KERNEL32.dll", "UnmapViewOfFile", (void *)h_UnmapViewOfFile);
        iat_hook(m, "KERNEL32.dll", "CloseHandle", (void *)h_CloseHandle);
    }
    HMODULE exe = GetModuleHandleA(NULL);
    o_connect = (connect_t)iat_hook_o(exe, "WSOCK32.dll", "connect", 4, (void *)h_connect);
    o_send = (send_t)iat_hook_o(exe, "WSOCK32.dll", "send", 19, (void *)h_send);
    o_recv = (recv_t)iat_hook_o(exe, "WSOCK32.dll", "recv", 16, (void *)h_recv);
    o_closesocket = (closesocket_t)iat_hook_o(exe, "WSOCK32.dll", "closesocket", 3, (void *)h_closesocket);
    if (!o_connect || !o_send || !o_recv || !o_closesocket) sgclog("network hooks missing (%d %d %d %d)", !!o_connect, !!o_send, !!o_recv, !!o_closesocket);
}
