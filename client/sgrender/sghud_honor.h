/* sghud_honor.h - part of sghud.c (included in this order; not a header on its own): unit honor page and medals (drawing, tips) */
/* ---- UNIT HONOR PAGE (user 2026-10-31 14:10) ---------------------------------------------------------------------------
   "a page that keeps the highest-star units and the lifetime kills; past a number a special mark and honor".  The data is
   the server's /b/<c|t|e>/honor/list.txt (server/sgs/board_mail.py honor_page), fetched from the board base URL the exe
   carries (0x64eae0, patched by tools/build_i18n_exe.py) in a worker thread; lines: I me honor / M my unit / T top. */
#include <wininet.h>
static void acc_query(char *q, int n)                 /* "?acc=<url-encoded login account>" or "" */
{
    char a[40]; lstrcpynA(a, g_acc, sizeof a);
    int k = 0; q[0] = 0;
    if (!a[0] || n < 8) return;
    k = _snprintf(q, n, "?acc=");
    for (const unsigned char *c = (const unsigned char *)a; *c && k < n - 4; c++) {
        if ((*c >= '0' && *c <= '9') || (*c >= 'A' && *c <= 'Z') || (*c >= 'a' && *c <= 'z') || *c == '-' || *c == '_' || *c == '.') q[k++] = (char)*c;
        else k += _snprintf(q + k, n - k, "%%%02X", *c);
    }
    q[k] = 0;
}
static DWORD WINAPI hon_fetch(LPVOID p)
{
    (void)p;
    char base[128], url[256], buf[sizeof g_hon_buf];
    int n = 0, ok = 0;
    lstrcpynA(base, (char *)0x64eae0, sizeof base);
    if (!strncmp(base, "http://", 7) && !strstr(base, "sgalaxy.com")) {
        char q[96]; acc_query(q, sizeof q);
        _snprintf(url, sizeof url, "%shonor/list.txt%s", base, q);
        HINTERNET in = InternetOpenA("SGRender", INTERNET_OPEN_TYPE_PRECONFIG, NULL, NULL, 0);
        HINTERNET h = in ? InternetOpenUrlA(in, url, NULL, 0, INTERNET_FLAG_RELOAD | INTERNET_FLAG_NO_CACHE_WRITE | INTERNET_FLAG_NO_UI, 0) : NULL;
        if (h) {
            DWORD got;
            while (n < (int)sizeof buf - 1 && InternetReadFile(h, buf + n, sizeof buf - 1 - n, &got) && got) n += got;
            ok = 1;
            InternetCloseHandle(h);
        }
        if (in) InternetCloseHandle(in);
    }
    buf[n] = 0;
    EnterCriticalSection(&g_hon_cs);
    if (ok) memcpy(g_hon_buf, buf, n + 1);
    LeaveCriticalSection(&g_hon_cs);
    g_hon_state = ok ? 2 : 3;
    g_hon_t = GetTickCount();
    g_dirty = 1;
    InterlockedExchange(&g_hon_busy, 0);
    return 0;
}
static DWORD WINAPI rep_fetch(LPVOID p)
{
    (void)p;
    char base[128], url[256], buf[sizeof g_rep_buf];
    int n = 0, ok = 0;
    lstrcpynA(base, (char *)0x64eae0, sizeof base);
    if (!strncmp(base, "http://", 7) && !strstr(base, "sgalaxy.com")) {
        char q[96]; acc_query(q, sizeof q);
        _snprintf(url, sizeof url, "%shonor/report.txt%s", base, q);
        HINTERNET in = InternetOpenA("SGRender", INTERNET_OPEN_TYPE_PRECONFIG, NULL, NULL, 0);
        HINTERNET h = in ? InternetOpenUrlA(in, url, NULL, 0, INTERNET_FLAG_RELOAD | INTERNET_FLAG_NO_CACHE_WRITE | INTERNET_FLAG_NO_UI, 0) : NULL;
        if (h) {
            DWORD got;
            while (n < (int)sizeof buf - 1 && InternetReadFile(h, buf + n, sizeof buf - 1 - n, &got) && got) n += got;
            ok = 1;
            InternetCloseHandle(h);
        }
        if (in) InternetCloseHandle(in);
    }
    buf[n] = 0;
    EnterCriticalSection(&g_hon_cs);
    if (ok) memcpy(g_rep_buf, buf, n + 1);
    LeaveCriticalSection(&g_hon_cs);
    g_rep_state = ok ? 2 : 3;
    g_rep_t = GetTickCount();
    g_dirty = 1;
    InterlockedExchange(&g_rep_busy, 0);
    return 0;
}
static DWORD WINAPI cmd_fetch(LPVOID p)
{
    (void)p;
    char base[128], url[256], buf[sizeof g_cmd_buf];
    int n = 0, ok = 0;
    lstrcpynA(base, (char *)0x64eae0, sizeof base);
    if (!strncmp(base, "http://", 7) && !strstr(base, "sgalaxy.com")) {
        char q[96]; acc_query(q, sizeof q);
        _snprintf(url, sizeof url, "%shonor/cmd.txt%s", base, q);
        HINTERNET in = InternetOpenA("SGRender", INTERNET_OPEN_TYPE_PRECONFIG, NULL, NULL, 0);
        HINTERNET h = in ? InternetOpenUrlA(in, url, NULL, 0, INTERNET_FLAG_RELOAD | INTERNET_FLAG_NO_CACHE_WRITE | INTERNET_FLAG_NO_UI, 0) : NULL;
        if (h) {
            DWORD got;
            while (n < (int)sizeof buf - 1 && InternetReadFile(h, buf + n, sizeof buf - 1 - n, &got) && got) n += got;
            ok = 1;
            InternetCloseHandle(h);
        }
        if (in) InternetCloseHandle(in);
    }
    buf[n] = 0;
    EnterCriticalSection(&g_hon_cs);
    /* (11-01) a bad answer (error page, cut short) never replaces a good page already here */
    int good = ok && buf[0] == 'I' && buf[1] == '\t', had = g_cmd_buf[0] == 'I' && g_cmd_buf[1] == '\t';
    if (good || (ok && !had)) memcpy(g_cmd_buf, buf, n + 1);
    LeaveCriticalSection(&g_hon_cs);
    g_cmd_state = (ok || had) ? 2 : 3;
    g_cmd_t = GetTickCount();
    g_dirty = 1;
    InterlockedExchange(&g_cmd_busy, 0);
    return 0;
}
static DWORD WINAPI oth_fetch(LPVOID p)
{
    (void)p;
    char base[128], url[320], buf[sizeof g_oth_buf], want[64];
    int n = 0, ok = 0;
    lstrcpynA(want, g_oth_req, sizeof want);
    lstrcpynA(base, (char *)0x64eae0, sizeof base);
    if (!strncmp(base, "http://", 7) && !strstr(base, "sgalaxy.com") && want[0]) {
        int k = _snprintf(url, sizeof url, "%shonor/user.txt?name=", base);
        for (const unsigned char *c = (const unsigned char *)want; *c && k < (int)sizeof url - 4; c++) {
            if ((*c >= '0' && *c <= '9') || (*c >= 'A' && *c <= 'Z') || (*c >= 'a' && *c <= 'z')) url[k++] = (char)*c;
            else k += _snprintf(url + k, sizeof url - k, "%%%02X", *c);
        }
        url[k] = 0;
        HINTERNET in = InternetOpenA("SGRender", INTERNET_OPEN_TYPE_PRECONFIG, NULL, NULL, 0);
        HINTERNET h = in ? InternetOpenUrlA(in, url, NULL, 0, INTERNET_FLAG_RELOAD | INTERNET_FLAG_NO_CACHE_WRITE | INTERNET_FLAG_NO_UI, 0) : NULL;
        if (h) {
            DWORD got;
            while (n < (int)sizeof buf - 1 && InternetReadFile(h, buf + n, sizeof buf - 1 - n, &got) && got) n += got;
            ok = 1;
            InternetCloseHandle(h);
        }
        if (in) InternetCloseHandle(in);
    }
    buf[n] = 0;
    EnterCriticalSection(&g_hon_cs);
    if (ok && buf[0] == 'I' && buf[1] == '\t') { memcpy(g_oth_buf, buf, n + 1); lstrcpynA(g_oth_got, want, sizeof g_oth_got); }
    LeaveCriticalSection(&g_hon_cs);
    g_oth_state = ok ? 2 : 3;
    g_oth_t = GetTickCount();
    g_dirty = 1;
    InterlockedExchange(&g_oth_busy, 0);
    return 0;
}
static void oth_fetch_start(void)
{
    if (!g_hon_csok) { InitializeCriticalSection(&g_hon_cs); g_hon_csok = 1; }
    if (InterlockedExchange(&g_oth_busy, 1)) return;
    lstrcpynA(g_oth_req, g_oth_name, sizeof g_oth_req);
    g_oth_state = 1;
    HANDLE t = CreateThread(NULL, 0, oth_fetch, NULL, 0, NULL);
    if (t) CloseHandle(t); else InterlockedExchange(&g_oth_busy, 0);
}
static void cmd_fetch_start(void)
{
    if (!g_hon_csok) { InitializeCriticalSection(&g_hon_cs); g_hon_csok = 1; }
    if (InterlockedExchange(&g_cmd_busy, 1)) return;
    if (g_cmd_state != 2) g_cmd_state = 1;
    HANDLE t = CreateThread(NULL, 0, cmd_fetch, NULL, 0, NULL);
    if (t) CloseHandle(t); else InterlockedExchange(&g_cmd_busy, 0);
}
static void rep_fetch_start(void)
{
    if (!g_hon_csok) { InitializeCriticalSection(&g_hon_cs); g_hon_csok = 1; }
    if (InterlockedExchange(&g_rep_busy, 1)) return;
    g_rep_tries++;
    HANDLE t = CreateThread(NULL, 0, rep_fetch, NULL, 0, NULL);
    if (t) CloseHandle(t); else InterlockedExchange(&g_rep_busy, 0);
}
static void hon_fetch_start(void)
{
    if (!g_hon_csok) { InitializeCriticalSection(&g_hon_cs); g_hon_csok = 1; }
    if (InterlockedExchange(&g_hon_busy, 1)) return;
    if (g_hon_state != 2) g_hon_state = 1;
    HANDLE t = CreateThread(NULL, 0, hon_fetch, NULL, 0, NULL);
    if (t) CloseHandle(t); else InterlockedExchange(&g_hon_busy, 0);
}
static int hon_split(char *line, char **f, int max)
{
    int n = 0;
    while (n < max) { f[n++] = line; char *t = strchr(line, '\t'); if (!t) break; *t = 0; line = t + 1; }
    return n;
}
/* ---- MEDALS (user 10-31 14:36 "commemorative medal designs"): a ribbon of the medal's colours above a metal body whose
   shape and emblem tell the deed - crossed swords for the kill records, a lightning bolt for one-against-a-thousand, a
   laurel for the veterans, a flame for the phoenix, a flag for the conqueror, a shield for the guardian, stars for stars */
enum { MS_ROUND, MS_STAR5, MS_STAR8, MS_HEX, MS_SHIELD, MS_DIAMOND, MS_PENT };
enum { ME_TEXT, ME_SWORDS, ME_BOLT, ME_LAUREL, ME_FLAME, ME_FLAG, ME_CROSS };
typedef struct {
    const char *code; const WCHAR *cn, *tw, *en, *ccn, *ctw, *cen;
    ARGB rib[3], hi, lo; int shape, emblem; const WCHAR *mark;
} Medal;
static const Medal MEDALS[] = {     /* milestones (once), then the battle medals (every settlement, counted) */
    { "bronze", L"铜质战功", L"銅質戰功", L"Bronze record", L"历史击杀 100", L"歷史擊殺 100", L"100 kills",
      { 0xFF8E2A1Eu, 0xFFD9B38Cu, 0xFF8E2A1Eu }, 0xFFF0B07Au, 0xFF6E3A16u, MS_ROUND, ME_SWORDS, NULL },
    { "silver", L"银质战功", L"銀質戰功", L"Silver record", L"历史击杀 500", L"歷史擊殺 500", L"500 kills",
      { 0xFF1F3F7Au, 0xFFEDEFF2u, 0xFF1F3F7Au }, 0xFFFAFBFCu, 0xFF7B838Bu, MS_ROUND, ME_SWORDS, NULL },
    { "gold", L"金质战功", L"金質戰功", L"Gold record", L"历史击杀 1000", L"歷史擊殺 1000", L"1000 kills",
      { 0xFFB71C1Cu, 0xFFFFD54Fu, 0xFFB71C1Cu }, 0xFFFFF0A8u, 0xFFA87406u, MS_ROUND, ME_SWORDS, NULL },
    { "legend", L"传奇战功", L"傳奇戰功", L"Legendary record", L"历史击杀 3000", L"歷史擊殺 3000", L"3000 kills",
      { 0xFF141414u, 0xFFFFC107u, 0xFF141414u }, 0xFFFFE08Au, 0xFFA3300Eu, MS_STAR8, ME_SWORDS, NULL },
    { "vet30", L"沙场老兵", L"沙場老兵", L"Veteran", L"参战 30 场", L"參戰 30 場", L"30 battles",
      { 0xFF556B2Fu, 0xFFC8B98Au, 0xFF556B2Fu }, 0xFFD5DCE2u, 0xFF56606Au, MS_ROUND, ME_LAUREL, L"30" },
    { "vet100", L"百战之魂", L"百戰之魂", L"Hundred battles", L"参战 100 场", L"參戰 100 場", L"100 battles",
      { 0xFF7F0000u, 0xFFE0B040u, 0xFF7F0000u }, 0xFFFFEAA0u, 0xFF9C6A05u, MS_ROUND, ME_LAUREL, L"100" },
    { "star3", L"三星精锐", L"三星精銳", L"Three-star elite", L"升到 3 星", L"升到 3 星", L"Reach 3 stars",
      { 0xFF283593u, 0xFFCFD8DCu, 0xFF283593u }, 0xFFF4F6F8u, 0xFF7A848Eu, MS_STAR5, ME_TEXT, L"3" },
    { "fivestar", L"五星传奇", L"五星傳奇", L"Five-star legend", L"升到 5 星", L"升到 5 星", L"Reach 5 stars",
      { 0xFFC62828u, 0xFFFFD54Fu, 0xFFC62828u }, 0xFFFFF3B0u, 0xFFB07800u, MS_STAR5, ME_TEXT, L"5" },
    { "ace", L"一骑当千", L"一騎當千", L"One vs a thousand", L"单场 15 杀", L"單場 15 殺", L"15 kills in a battle",
      { 0xFFE65100u, 0xFF1A1A1Au, 0xFFE65100u }, 0xFFFFE07Au, 0xFF9A6A08u, MS_DIAMOND, ME_BOLT, NULL },
    { "mvp", L"本场最佳", L"本場最佳", L"Best of the battle", L"本场击杀最多", L"本場擊殺最多", L"Most kills of his units",
      { 0xFF00695Cu, 0xFFFFD54Fu, 0xFF00695Cu }, 0xFFFFE9A0u, 0xFF8F6A06u, MS_STAR8, ME_TEXT, L"MVP" },
    { "survivor", L"不死鸟", L"不死鳥", L"Phoenix", L"半数阵亡仍生还", L"半數陣亡仍生還", L"Alive though half fell",
      { 0xFFD84315u, 0xFFFFCC80u, 0xFFD84315u }, 0xFFFFC27Au, 0xFFA8320Eu, MS_HEX, ME_FLAME, NULL },
    { "conqueror", L"开疆拓土", L"開疆拓土", L"Conqueror", L"参与占领省份", L"參與佔領省份", L"Took a province",
      { 0xFF4A148Cu, 0xFFE1C16Eu, 0xFF4A148Cu }, 0xFFF3D27Au, 0xFF8A5A10u, MS_PENT, ME_FLAG, NULL },
    { "guardian", L"守护之盾", L"守護之盾", L"Shield of the realm", L"守土胜利", L"守土勝利", L"Won a defence",
      { 0xFF0D47A1u, 0xFFE3F2FDu, 0xFF0D47A1u }, 0xFFCFE3F7u, 0xFF2E5A8Au, MS_SHIELD, ME_CROSS, NULL } };
#define N_ONCE 8
#define N_MEDALS (int)(sizeof MEDALS / sizeof *MEDALS)
static const Medal *medal_of(const char *code)
{
    for (int i = 0; i < N_MEDALS; i++) if (!strcmp(code, MEDALS[i].code)) return &MEDALS[i];
    return NULL;
}
static ARGB grey_of(ARGB c, float a)
{
    unsigned r = (c >> 16) & 255, g = (c >> 8) & 255, b = c & 255, y = (r * 3 + g * 6 + b) / 10;
    y = y / 2 + 30;
    return ((unsigned)(a * 255) << 24) | (y << 16) | (y << 8) | y;
}
static void fill_grad(const GpPointF *p, int n, ARGB c1, ARGB c2, float y0, float y1, int ellipse, float ex, float ey, float ew, float eh)
{
    GpPointF g0 = { 0, Y(y0) }, g1 = { 0, Y(y1) };
    GpLineGradient *lg = NULL;
    pGdipCreateLineBrush(&g0, &g1, c1, c2, 3, &lg);          /* 3 = TileFlipXY: no jump at the edges */
    GpBrush *br = lg ? (GpBrush *)lg : brush(c1);
    if (ellipse) pGdipFillEllipse(C.g, br, X(ex), Y(ey), S(ew), S(eh));
    else pGdipFillPolygon(C.g, br, p, n, GP_FILL_ALT);
    if (lg) pGdipDeleteBrush((GpBrush *)lg);
}
static int medal_shape(int shape, float cx, float cy, float r, GpPointF *p)
{
    int n = 0;
    if (shape == MS_STAR5 || shape == MS_STAR8) {
        int k = shape == MS_STAR5 ? 5 : 8; float ri = shape == MS_STAR5 ? 0.48f : 0.62f;
        for (int i = 0; i < 2 * k; i++) {
            float a = -1.5708f + i * 3.14159f / k, rr = (i & 1) ? r * ri : r;
            p[n].X = X(cx + rr * cosf(a)); p[n].Y = Y(cy + rr * sinf(a)); n++;
        }
    } else if (shape == MS_HEX || shape == MS_PENT) {
        int k = shape == MS_HEX ? 6 : 5;
        for (int i = 0; i < k; i++) {
            float a = -1.5708f + i * 6.28318f / k;
            p[n].X = X(cx + r * cosf(a)); p[n].Y = Y(cy + r * sinf(a)); n++;
        }
    } else if (shape == MS_DIAMOND) {
        float q[4][2] = { { 0, -1.1f }, { 0.85f, 0 }, { 0, 1.1f }, { -0.85f, 0 } };
        for (int i = 0; i < 4; i++) { p[n].X = X(cx + q[i][0] * r); p[n].Y = Y(cy + q[i][1] * r); n++; }
    } else if (shape == MS_SHIELD) {
        float q[7][2] = { { -0.85f, -0.9f }, { 0, -1.05f }, { 0.85f, -0.9f }, { 0.85f, 0.1f }, { 0.45f, 0.75f }, { 0, 1.05f }, { -0.45f, 0.75f } };
        for (int i = 0; i < 7; i++) { p[n].X = X(cx + q[i][0] * r); p[n].Y = Y(cy + q[i][1] * r); n++; }
        p[n].X = X(cx - 0.85f * r); p[n].Y = Y(cy + 0.1f * r); n++;
    }
    return n;
}
static void draw_medal(const Medal *m, float cx, float cy, float r, int earned)
{
    float a = earned ? 1.0f : 0.38f;
    ARGB hi = earned ? m->hi : grey_of(m->hi, a), lo = earned ? m->lo : grey_of(m->lo, a);
    ARGB ink = earned ? (((m->lo >> 1) & 0x007F7F7Fu) | 0xFF000000u) : grey_of(0xFF202020u, a);
    ARGB shine = earned ? 0x90FFFFFFu : 0x30FFFFFFu;
    /* ribbon: three stripes, a V cut at the bottom where the ring holds the medal */
    float rw = r * 0.95f, rt = cy - r * 2.15f, rb = cy - r * 0.75f;
    for (int k = 0; k < 3; k++) {
        float x0 = cx - rw + k * (2 * rw / 3), x1 = x0 + 2 * rw / 3;
        float b0 = rb - (x0 < cx ? (cx - x0) : (x0 - cx)) * 0.25f, b1 = rb - (x1 < cx ? (cx - x1) : (x1 - cx)) * 0.25f;
        GpPointF q[4] = { { X(x0), Y(rt) }, { X(x1), Y(rt) }, { X(x1), Y(b1) }, { X(x0), Y(b0) } };
        ARGB c = earned ? m->rib[k] : grey_of(m->rib[k], a);
        pGdipFillPolygon(C.g, brush(c), q, 4, GP_FILL_ALT);
    }
    line(cx - rw, rt, cx + rw, rt, earned ? 0xC0000000u : 0x40000000u, 1.2f);
    stroke_circle(cx, cy - r * 0.92f, r * 0.13f, hi, 2);               /* the ring */
    /* body */
    GpPointF p[20]; int n = medal_shape(m->shape, cx, cy, r, p);
    if (m->shape == MS_ROUND) {
        fill_grad(NULL, 0, hi, lo, cy - r, cy + r, 1, cx - r, cy - r, 2 * r, 2 * r);
        stroke_circle(cx, cy, r, lo, 1.6f);
        stroke_circle(cx, cy, r * 0.8f, shine, 1.2f);
    } else {
        fill_grad(p, n, hi, lo, cy - r, cy + r, 0, 0, 0, 0, 0);
        pGdipDrawPolygon(C.g, pen(lo, S(1.6f)), p, n);
        if (m->shape == MS_STAR8 || m->shape == MS_STAR5) fill_circle(cx, cy, r * 0.42f, (hi & 0x00FFFFFFu) | ((unsigned)(a * 200) << 24));
    }
    if (earned) { GpPointF g[3] = { { X(cx - r * 0.55f), Y(cy - r * 0.55f) }, { X(cx - r * 0.1f), Y(cy - r * 0.75f) }, { X(cx - r * 0.7f), Y(cy - r * 0.1f) } };
                  pGdipFillPolygon(C.g, brush(0x40FFFFFFu), g, 3, GP_FILL_ALT); }   /* a glint */
    /* emblem */
    float e = r * 0.5f;
    switch (m->emblem) {
    case ME_SWORDS:
        line(cx - e, cy + e, cx + e, cy - e, ink, 2.2f); line(cx + e, cy + e, cx - e, cy - e, ink, 2.2f);
        line(cx - e * 0.75f, cy + e * 0.35f, cx - e * 0.35f, cy + e * 0.75f, ink, 2); line(cx + e * 0.75f, cy + e * 0.35f, cx + e * 0.35f, cy + e * 0.75f, ink, 2);
        break;
    case ME_BOLT: {
        GpPointF b[6] = { { X(cx + e * 0.2f), Y(cy - e * 1.1f) }, { X(cx - e * 0.55f), Y(cy + e * 0.15f) }, { X(cx - e * 0.05f), Y(cy + e * 0.15f) },
                          { X(cx - e * 0.25f), Y(cy + e * 1.1f) }, { X(cx + e * 0.6f), Y(cy - e * 0.2f) }, { X(cx + e * 0.08f), Y(cy - e * 0.2f) } };
        pGdipFillPolygon(C.g, brush(ink), b, 6, GP_FILL_ALT);
        break; }
    case ME_LAUREL:
        for (int sd = -1; sd <= 1; sd += 2)
            for (int i = 0; i < 5; i++) {
                float t = 2.3f + i * 0.33f, lx = cx + sd * cosf(t) * r * 0.66f * -1, ly = cy + sinf(t) * r * 0.66f * -1 + r * 0.05f;
                (void)lx; (void)ly;
                float ang = 1.9f + i * 0.36f;
                float px2 = cx + sd * r * 0.64f * sinf(ang), py2 = cy - r * 0.64f * cosf(ang);
                pGdipFillEllipse(C.g, brush(ink), X(px2 - r * 0.09f), Y(py2 - r * 0.05f), S(r * 0.18f), S(r * 0.1f));
            }
        if (m->mark) text(m->mark, cx - r, cy - r * 0.45f, 2 * r, r * 0.9f, r * (wcslen(m->mark) > 2 ? 0.42f : 0.55f), 1, 1, ink, GP_ALIGN_CENTER, GP_ALIGN_CENTER);
        break;
    case ME_FLAME: {
        GpPointF f[7] = { { X(cx), Y(cy - e * 1.2f) }, { X(cx + e * 0.75f), Y(cy - e * 0.1f) }, { X(cx + e * 0.55f), Y(cy + e * 0.85f) },
                          { X(cx), Y(cy + e * 1.15f) }, { X(cx - e * 0.55f), Y(cy + e * 0.85f) }, { X(cx - e * 0.75f), Y(cy - e * 0.1f) }, { X(cx - e * 0.2f), Y(cy - e * 0.5f) } };
        pGdipFillPolygon(C.g, brush(ink), f, 7, GP_FILL_ALT);
        fill_circle(cx, cy + e * 0.45f, e * 0.33f, hi);
        break; }
    case ME_FLAG:
        line(cx - e * 0.55f, cy + e, cx - e * 0.55f, cy - e, ink, 2.2f);
        { GpPointF fl[4] = { { X(cx - e * 0.5f), Y(cy - e) }, { X(cx + e * 0.85f), Y(cy - e * 0.6f) }, { X(cx - e * 0.5f), Y(cy - e * 0.15f) }, { X(cx - e * 0.5f), Y(cy - e) } };
          pGdipFillPolygon(C.g, brush(ink), fl, 4, GP_FILL_ALT); }
        break;
    case ME_CROSS:
        fill_rect(cx - e * 0.18f, cy - e * 0.85f, e * 0.36f, e * 1.7f, ink);
        fill_rect(cx - e * 0.7f, cy - e * 0.3f, e * 1.4f, e * 0.36f, ink);
        break;
    default:
        if (m->mark) text(m->mark, cx - r, cy - r * 0.6f, 2 * r, r * 1.2f, r * (wcslen(m->mark) > 2 ? 0.4f : 0.75f), 1, 1, ink, GP_ALIGN_CENTER, GP_ALIGN_CENTER);
    }
    if (earned && !strcmp(m->code, "fivestar")) stroke_circle(cx, cy, r * 1.18f, 0x80FFE066u, 1.4f);
}
/* (user 10-31 17:12 "the mouse over a medal must explain it"): a medal under the mouse leaves a tip, drawn last */
static const Medal *g_tip_m; static float g_tip_x, g_tip_y; static int g_tip_n;
static void medal_hit(const Medal *m, float x, float y, float w, float h, int n)
{
    int i = (int)(m - MEDALS);
    hit_add(x, y, w, h, 0, H_MEDAL, i);
    if (hovered(H_MEDAL, i) && !g_tip_m) { g_tip_m = m; g_tip_x = x + w / 2; g_tip_y = y; g_tip_n = n; }
}
static WCHAR g_ttip1[48], g_ttip2[96]; static float g_ttip_x, g_ttip_y; static int g_ttip_on;
static void text_hit(int id, float x, float y, float w, float h, const WCHAR *t1, const WCHAR *t2)
{
    hit_add(x, y, w, h, 0, H_UITIP, id);
    if (hovered(H_UITIP, id) && !g_ttip_on) {
        g_ttip_on = 1; lstrcpynW(g_ttip1, t1, 48); lstrcpynW(g_ttip2, t2, 96); g_ttip_x = x + w / 2; g_ttip_y = y;
    }
}
static void paint_tip(void)
{
    if (g_ttip_on) {                                     /* a text tip (F4 attributes, commander medals) */
        g_ttip_on = 0;
        float w = 300, h = 66, x = g_ttip_x - w / 2, y = g_ttip_y - h - 6;
        if (x < 4) x = 4; if (x + w > C.RW - 4) x = C.RW - 4 - w;
        if (y < 4) y = g_ttip_y + 30;
        fill_rect(x, y, w, h, 0xF5101820u);
        stroke_rect(x + 0.5f, y + 0.5f, w - 1, h - 1, C_BRASS, 1.3f);
        text(g_ttip1, x + 12, y + 6, w - 24, 24, 14, 0, 1, C_BRASS_HI, GP_ALIGN_NEAR, GP_ALIGN_CENTER);
        text(g_ttip2, x + 12, y + 32, w - 24, 26, 11, 0, 0, C_TEXT, GP_ALIGN_NEAR, GP_ALIGN_CENTER);
    }
    const Medal *m = g_tip_m;
    g_tip_m = NULL;
    if (!m) return;
    int once = (int)(m - MEDALS) < N_ONCE;
    WCHAR l3[64];
    const WCHAR *l1 = g_lang == 1 ? m->cn : g_lang == 2 ? m->tw : m->en, *l2 = g_lang == 1 ? m->ccn : g_lang == 2 ? m->ctw : m->cen;
    const WCHAR *l4 = once ? T3("Milestone medal - earned once", "里程碑勋章：达成后永久获得一次", "里程碑勳章：達成後永久獲得一次")
                           : T3("Battle medal - every settlement can give it again", "战场勋章：每场结算都可再次获得", "戰場勳章：每場結算都可再次獲得");
    if (g_tip_n > 0) swprintf(l3, 64, once ? (g_lang ? L"已获得" : L"Earned") : (g_lang ? L"已获得 \x00d7%d" : L"Earned \x00d7%d"), g_tip_n);
    else lstrcpynW(l3, g_tip_n < 0 ? L"" : T3("Not earned yet", "尚未获得", "尚未獲得"), 64);
    if (g_lang == 2 && g_tip_n > 0) swprintf(l3, 64, once ? L"已獲得" : L"已獲得 \x00d7%d", g_tip_n);
    float w = 250, h = l3[0] ? 104 : 84, x = g_tip_x - w / 2, y = g_tip_y - h - 6;
    if (x < 4) x = 4; if (x + w > C.RW - 4) x = C.RW - 4 - w;
    if (y < 4) y = g_tip_y + 50;
    fill_rect(x, y, w, h, 0xF5101820u);
    stroke_rect(x + 0.5f, y + 0.5f, w - 1, h - 1, m->hi, 1.4f);
    for (int k = 0; k < 3; k++) fill_rect(x + 1 + k * (w - 2) / 3, y + 1, (w - 2) / 3, 4, m->rib[k]);
    draw_medal(m, x + 26, y + 40, 13, 1);
    text(l1, x + 50, y + 10, w - 58, 24, 15, 0, 1, m->hi, GP_ALIGN_NEAR, GP_ALIGN_CENTER);
    text(l2, x + 50, y + 34, w - 58, 20, 12, 0, 0, C_TEXT, GP_ALIGN_NEAR, GP_ALIGN_CENTER);
    text(l4, x + 10, y + 60, w - 20, 18, 10, 0, 0, C_MUTED, GP_ALIGN_NEAR, GP_ALIGN_CENTER);
    if (l3[0]) text(l3, x + 10, y + 80, w - 20, 18, 11, 0, 1, g_tip_n > 0 ? 0xFF8BE28Bu : C_MUTED, GP_ALIGN_NEAR, GP_ALIGN_CENTER);
}
static void hon_mark(const char *code, float x, float y, float *adv)
{
    const Medal *m = medal_of(code);
    *adv = 0;
    if (!m) return;
    draw_medal(m, x + 9, y + 10, 6.5f, 1);
    medal_hit(m, x, y - 4, 18, 26, -1);
    *adv = 20;
}
static void ymd(long t, int *y, int *mo, int *d)
{
    long z = t / 86400 + 719468, era = (z >= 0 ? z : z - 146096) / 146097;
    unsigned doe = (unsigned)(z - era * 146097), yoe = (doe - doe / 1460 + doe / 36524 - doe / 146096) / 365;
    unsigned doy = doe - (365 * yoe + yoe / 4 - yoe / 100), mp = (5 * doy + 2) / 153;
    *d = (int)(doy - (153 * mp + 2) / 5 + 1); *mo = (int)(mp < 10 ? mp + 3 : mp - 9); *y = (int)(yoe + era * 400 + (*mo <= 2));
}
static void paint_honor_detail(char **f, int nf, int mine, float x, float y, float w, float h)
{
    WCHAR v[128], nm[48], ch[48], own[48];
    MultiByteToWideChar(CP_ACP, 0, mine ? f[2] : f[4], -1, nm, 48);
    MultiByteToWideChar(CP_ACP, 0, mine ? f[3] : f[5], -1, ch, 48);
    MultiByteToWideChar(CP_ACP, 0, mine ? "" : f[2], -1, own, 48);
    int stars = atoi(mine ? f[4] : f[6]), kills = atoi(mine ? f[5] : f[7]);
    const char *marks = mine ? f[7] : f[8];
    int bt = nf > 9 ? atoi(f[9]) : 0, bw = nf > 10 ? atoi(f[10]) : 0, bk = nf > 11 ? atoi(f[11]) : 0, sv = nf > 12 ? atoi(f[12]) : 0;
    int cap = nf > 13 ? atoi(f[13]) : 0, dw = nf > 14 ? atoi(f[14]) : 0; long t0 = nf > 15 ? atol(f[15]) : 0;
    int gone = mine && f[8][0] == '0';
    /* back */
    int hb = hovered(H_HONBACK, 0);
    stroke_rect(x + 0.5f, y + 0.5f, 90, 28, hb ? C_BRASS_HI : 0x90C9A45Cu, 1.2f);
    line(x + 16, y + 14, x + 22, y + 8, hb ? C_BRASS_HI : C_TEXT, 2); line(x + 16, y + 14, x + 22, y + 20, hb ? C_BRASS_HI : C_TEXT, 2);
    text(T3("Back", "返回", "返回"), x + 28, y, 56, 28, 13, 0, 1, hb ? C_BRASS_HI : C_TEXT, GP_ALIGN_NEAR, GP_ALIGN_CENTER);
    hit_add(x, y, 90, 28, 0, H_HONBACK, 0);
    /* left: the unit */
    float lx = x, ly = y + 40, lw = w * 0.36f;
    fill_rect(lx, ly, lw, h - 40, 0x18FFFFFFu);
    stroke_rect(lx + 0.5f, ly + 0.5f, lw - 1, h - 41, 0x60C9A45Cu, 1);
    text(nm, lx + 16, ly + 12, lw - 32, 34, 22, 0, 1, gone ? C_MUTED : C_BRASS_HI, GP_ALIGN_NEAR, GP_ALIGN_CENTER);
    WCHAR st[8]; for (int q = 0; q < 5; q++) st[q] = q < stars ? 0x2605 : 0x2606; st[5] = 0;
    text(st, lx + 16, ly + 46, lw - 32, 30, 22, 0, 0, stars ? 0xFFFFE066u : 0x60FFFFFFu, GP_ALIGN_NEAR, GP_ALIGN_CENTER);
    swprintf(v, 128, L"%ls%ls%ls", ch, own[0] ? L"  \x00b7  " : L"", own);
    text(v, lx + 16, ly + 78, lw - 32, 22, 13, 0, 0, C_TEXT, GP_ALIGN_NEAR, GP_ALIGN_CENTER);
    text(gone ? T3("Retired", "已退役", "已退役") : T3("In service", "服役中", "服役中"), lx + 16, ly + 100, lw - 32, 20, 12, 0, 1,
         gone ? C_MUTED : 0xFF7FD17Fu, GP_ALIGN_NEAR, GP_ALIGN_CENTER);
    line(lx + 16, ly + 128, lx + lw - 16, ly + 128, 0x60C9A45Cu, 1);
    struct { const WCHAR *k; WCHAR v[32]; } S9[9];
    int ns = 0, yy, mo, dd;
    S9[ns].k = T3("Lifetime kills", "历史击杀", "歷史擊殺"); swprintf(S9[ns++].v, 32, L"%d", kills);
    S9[ns].k = T3("Battles", "参战场数", "參戰場數"); swprintf(S9[ns++].v, 32, L"%d", bt);
    S9[ns].k = T3("Wins", "胜场", "勝場"); swprintf(S9[ns++].v, 32, bt ? L"%d  (%d%%)" : L"%d", bw, bt ? bw * 100 / bt : 0);
    S9[ns].k = T3("Best battle", "单场最高击杀", "單場最高擊殺"); swprintf(S9[ns++].v, 32, L"%d", bk);
    S9[ns].k = T3("Longest survival", "最长连续存活", "最長連續存活"); swprintf(S9[ns++].v, 32, L"%d", sv);
    S9[ns].k = T3("Provinces taken", "参与占领", "參與佔領"); swprintf(S9[ns++].v, 32, L"%d", cap);
    S9[ns].k = T3("Defences won", "守土胜利", "守土勝利"); swprintf(S9[ns++].v, 32, L"%d", dw);
    if (mine) { S9[ns].k = T3("Peak level", "最高等级", "最高等級"); swprintf(S9[ns++].v, 32, L"%d", atoi(f[6])); }
    if (t0 > 0) { ymd(t0 + 8 * 3600, &yy, &mo, &dd); S9[ns].k = T3("On record since", "入册日期", "入冊日期"); swprintf(S9[ns++].v, 32, L"%d-%02d-%02d", yy, mo, dd); }
    for (int i = 0; i < ns; i++) {
        float ry = ly + 138 + i * 30;
        if (ry + 28 > ly + h - 40) break;
        text(S9[i].k, lx + 16, ry, lw * 0.55f, 28, 13, 0, 0, C_MUTED, GP_ALIGN_NEAR, GP_ALIGN_CENTER);
        text(S9[i].v, lx + lw * 0.55f, ry, lw * 0.45f - 16, 28, 14, 1, 1, C_TEXT, GP_ALIGN_FAR, GP_ALIGN_CENTER);
    }
    /* right: the medal wall */
    float rx = x + lw + 16, rw = w - lw - 16, ry = y + 40;
    int cnt[N_MEDALS], got = 0, total = 0, bat = 0;
    {   char mm[400]; lstrcpynA(mm, marks, sizeof mm);
        for (int i = 0; i < N_MEDALS; i++) cnt[i] = 0;
        for (char *t = strtok(mm, ","); t; t = strtok(NULL, ",")) {
            char *c = strchr(t, ':'); int n = c ? atoi(c + 1) : 1; if (c) *c = 0;
            for (int i = 0; i < N_MEDALS; i++) if (!strcmp(t, MEDALS[i].code)) { cnt[i] = n > 0 ? n : 1; got++; total += cnt[i]; if (i >= N_ONCE) bat += cnt[i]; }
        } }
    swprintf(v, 128, L"%ls  %d / %d", T3("Medals", "勋章墙", "勳章牆"), got, N_MEDALS);
    text(v, rx, ry, rw, 26, 15, 0, 1, C_BRASS_HI, GP_ALIGN_NEAR, GP_ALIGN_CENTER);
    text(T3("Row 2: battle medals - every settlement can give them again", "第二排为战场勋章：每场结算都可再次获得",
            "第二排為戰場勳章：每場結算都可再次獲得"), rx, ry, rw, 26, 11, 0, 0, C_MUTED, GP_ALIGN_FAR, GP_ALIGN_CENTER);
    int cols = N_ONCE; float cw = rw / cols, chh = 112, mr = cw * 0.2f > 19 ? 19 : cw * 0.2f;
    for (int i = 0; i < N_MEDALS; i++) {
        int on = cnt[i] > 0;
        int row = i < N_ONCE ? 0 : 1, col = i < N_ONCE ? i : i - N_ONCE;   /* milestones, then the battle medals */
        float cx = rx + (row ? col : col % cols) * cw + cw / 2 + (row ? 0 : 0), cy = ry + 30 + (row ? 1 : col / cols) * chh + 52;
        draw_medal(&MEDALS[i], cx, cy, mr, on);
        const Medal *m = &MEDALS[i];
        medal_hit(m, cx - cw / 2 + 4, cy - mr * 2.2f, cw - 8, mr * 2.2f + mr + 38, cnt[i]);
        text(g_lang == 1 ? m->cn : g_lang == 2 ? m->tw : m->en, cx - cw / 2, cy + mr + 4, cw, 18, 11, 0, 1, on ? C_TEXT : C_MUTED, GP_ALIGN_CENTER, GP_ALIGN_CENTER);
        text(g_lang == 1 ? m->ccn : g_lang == 2 ? m->ctw : m->cen, cx - cw / 2, cy + mr + 21, cw, 16, 9, 0, 0, on ? 0xFFB9B09Au : 0x80B9B09Au, GP_ALIGN_CENTER, GP_ALIGN_CENTER);
        if (i >= N_ONCE && on) {                                   /* a battle medal: how many times (14:44) */
            WCHAR xn[12]; swprintf(xn, 12, L"\x00d7%d", cnt[i]);
            float bx = cx + mr * 0.55f, by = cy - mr * 1.35f;
            fill_circle(bx + 9, by + 8, 10, 0xFFE07A3Au);
            text(xn, bx - 4, by, 26, 16, 10, 1, 1, 0xFFFFFFFFu, GP_ALIGN_CENTER, GP_ALIGN_CENTER);
        }
    }
    /* history */
    float hy = ry + 30 + 2 * chh + 8;
    line(rx, hy, rx + rw, hy, 0x60C9A45Cu, 1);
    text(T3("History", "历史纪录", "歷史紀錄"), rx, hy + 4, rw, 24, 14, 0, 1, C_BRASS_HI, GP_ALIGN_NEAR, GP_ALIGN_CENTER);
    swprintf(v, 128, g_lang == 1 ? L"累计获得勋章 %d 次（其中战场勋章 %d 次）" : g_lang == 2 ? L"累計獲得勳章 %d 次（其中戰場勳章 %d 次）"
                                 : L"%d medals earned in all (%d battle medals)", total, bat);
    text(v, rx + 110, hy + 4, rw - 110, 24, 12, 0, 1, C_TEXT, GP_ALIGN_FAR, GP_ALIGN_CENTER);
    char hist[600]; lstrcpynA(hist, nf > 16 ? f[16] : "", sizeof hist);
    char *ev[16]; int ne = 0;
    for (char *e = strtok(hist, ";"); e && ne < 16; e = strtok(NULL, ";")) ev[ne++] = e;
    int line_n = 0;
    for (int i = ne - 1; i >= 0; i--) {
        float ly2 = hy + 30 + line_n * 22;
        if (ly2 + 20 > y + h) break;
        char *c1 = strchr(ev[i], ':'); if (!c1) continue; *c1 = 0;
        char *c2 = strchr(c1 + 1, ':'); if (!c2) continue; *c2 = 0;
        long t = atol(ev[i]); ymd(t + 8 * 3600, &yy, &mo, &dd);
        WCHAR d[24]; swprintf(d, 24, L"%d-%02d-%02d", yy, mo, dd);
        if (!strcmp(c1 + 1, "star")) swprintf(v, 128, L"%ls \x2605%d", T3("Rose to", "升到", "升到"), atoi(c2 + 1));
        else { const Medal *m = medal_of(c2 + 1);
               swprintf(v, 128, L"%ls\x300c%ls\x300d", T3("Earned ", "获得", "獲得"), m ? (g_lang == 1 ? m->cn : g_lang == 2 ? m->tw : m->en) : L"?"); }
        text(d, rx + 4, ly2, 100, 20, 12, 1, 0, C_MUTED, GP_ALIGN_NEAR, GP_ALIGN_CENTER);
        text(v, rx + 110, ly2, rw - 110, 20, 13, 0, 0, C_TEXT, GP_ALIGN_NEAR, GP_ALIGN_CENTER);
        line_n++;
    }
    if (!line_n) text(T3("Nothing yet.", "尚无纪录。", "尚無紀錄。"), rx + 4, hy + 30, rw, 20, 12, 0, 0, C_MUTED, GP_ALIGN_NEAR, GP_ALIGN_CENTER);
}
static void paint_honor(void)
{
    if (g_hon_state != 1 && GetTickCount() - g_hon_t > 30000) hon_fetch_start();     /* fresh data every 30 s */
    float pw = C.RW - 60 > 880 ? 880 : C.RW - 60, ph = C.RH - 120 > 560 ? 560 : C.RH - 120;
    float px = (C.RW - pw) / 2, py = (C.RH - ph) / 2 - 20;
    hit_add(px, py, pw, ph, 0, H_SWALLOW, 0);
    fill_rect(px, py, pw, ph, 0xF20A1016u);
    stroke_rect(px + 0.5f, py + 0.5f, pw - 1, ph - 1, C_BRASS, 1.4f);
    diamond(px + pw / 2, py + 1, 6, C_BRASS);
    text(T3("UNIT HONORS", "单位荣誉", "單位榮譽"), px + 24, py + 12, 300, 30, 20, 0, 1, C_BRASS_HI, GP_ALIGN_NEAR, GP_ALIGN_CENTER);
    /* close */
    float cx = px + pw - 40, cy = py + 12;
    int hc = hovered(H_HONCL, 0);
    stroke_rect(cx + 0.5f, cy + 0.5f, 27, 27, hc ? 0xFFF2A06Au : 0xC0E07A3Au, 1.2f);
    line(cx + 8, cy + 8, cx + 20, cy + 20, hc ? 0xFFF2A06Au : 0xFFE07A3Au, 2); line(cx + 20, cy + 8, cx + 8, cy + 20, hc ? 0xFFF2A06Au : 0xFFE07A3Au, 2);
    hit_add(cx, cy, 28, 28, 0, H_HONCL, 0);
    /* data */
    static char work[sizeof g_hon_buf];
    if (g_hon_csok) { EnterCriticalSection(&g_hon_cs); memcpy(work, g_hon_buf, sizeof work); LeaveCriticalSection(&g_hon_cs); }
    else work[0] = 0;
    static char *rows[80][18]; int nf[80], nr = 0; long honor = -1;
    for (char *l = work; *l && nr < 80; ) {
        char *e = strchr(l, '\n'); if (e) *e = 0;
        char *f[18]; int k = hon_split(l, f, 18);
        if (k >= 3 && f[0][0] == 'I') honor = atol(f[2]);
        else if (k >= 8 && ((f[0][0] == 'M' && g_hon_tab == 0) || (f[0][0] == 'T' && g_hon_tab == 1))) {
            for (int j = 0; j < 18; j++) rows[nr][j] = j < k ? f[j] : (char *)"";
            nf[nr++] = k;
        }
        if (!e) break;
        l = e + 1;
    }
    WCHAR v[96];
    if (honor >= 0) {
        swprintf(v, 96, L"%ls %ld.%02ld", T3("Honor", "荣誉", "榮譽"), honor / 100, honor % 100);
        text(v, px + pw - 260, py + 12, 210, 30, 14, 0, 1, C_TEXT, GP_ALIGN_FAR, GP_ALIGN_CENTER);
    }
    /* tabs */
    for (int t = 0; t < 2; t++) {
        float tx = px + 24 + t * 150, ty = py + 52, tw = 140, th = 30;
        int on = g_hon_tab == t, hov = hovered(H_HONTAB, t);
        fill_rect(tx, ty, tw, th, on ? 0x40C9A45Cu : hov ? 0x20FFFFFFu : 0);
        stroke_rect(tx + 0.5f, ty + 0.5f, tw - 1, th - 1, on || hov ? C_BRASS_HI : 0x90C9A45Cu, on ? 1.8f : 1.2f);
        text(t ? T3("Server top", "全服排行", "全服排行") : T3("My units", "我的单位", "我的單位"), tx, ty, tw, th, 14, 0, 1,
             on ? C_BRASS_HI : C_TEXT, GP_ALIGN_CENTER, GP_ALIGN_CENTER);
        hit_add(tx, ty, tw, th, 0, H_HONTAB, t);
    }
    /* hint */
    text(T3("Click a unit to see its medals and record - every medal adds honor once",
            "点选单位查看它的勋章与战绩 · 每枚勋章一次性增加荣誉",
            "點選單位查看它的勳章與戰績 · 每枚勳章一次性增加榮譽"),
         px + 330, py + 52, pw - 354, 30, 11, 0, 0, C_MUTED, GP_ALIGN_FAR, GP_ALIGN_CENTER);
    if (g_hon_sel >= 0 && g_hon_sel < nr) { paint_honor_detail(rows[g_hon_sel], nf[g_hon_sel], g_hon_tab == 0, px + 24, py + 94, pw - 48, ph - 110); return; }
    if (g_hon_sel >= nr) g_hon_sel = -1;
    /* table */
    float tx0 = px + 24, ty0 = py + 94, tw0 = pw - 48, rh = 30;
    line(tx0, ty0 + 26, tx0 + tw0, ty0 + 26, 0x80C9A45Cu, 1);
    const float *cols; const WCHAR *hd[8];
    static const float CM[8] = { 0.00f, 0.05f, 0.19f, 0.45f, 0.57f, 0.67f, 0.77f, 1.0f };    /* # star name chassis kills peak marks */
    static const float CT[8] = { 0.00f, 0.06f, 0.22f, 0.42f, 0.56f, 0.70f, 0.79f, 1.0f };    /* # commander unit chassis star kills marks */
    if (g_hon_tab == 0) {
        cols = CM;
        hd[0] = L"#"; hd[1] = T3("Stars", "星级", "星級"); hd[2] = T3("Unit", "单位", "單位"); hd[3] = T3("Chassis", "兵种", "兵種");
        hd[4] = T3("Kills", "历史击杀", "歷史擊殺"); hd[5] = T3("Peak", "最高等级", "最高等級"); hd[6] = T3("Marks", "勋章", "勳章");
    } else {
        cols = CT;
        hd[0] = T3("Rank", "排名", "排名"); hd[1] = T3("Commander", "指挥官", "指揮官"); hd[2] = T3("Unit", "单位", "單位");
        hd[3] = T3("Chassis", "兵种", "兵種"); hd[4] = T3("Stars", "星级", "星級"); hd[5] = T3("Kills", "历史击杀", "歷史擊殺");
        hd[6] = T3("Marks", "勋章", "勳章");
    }
    for (int c = 0; c < 7; c++)
        text(hd[c], tx0 + cols[c] * tw0 + 4, ty0, (cols[c + 1] - cols[c]) * tw0 - 8, 24, 12, 0, 1, C_BRASS, GP_ALIGN_NEAR, GP_ALIGN_CENTER);
    int per = (int)((ph - 94 - 30 - 50) / rh); if (per < 1) per = 1;
    int pages = (nr + per - 1) / per; if (pages < 1) pages = 1;
    if (g_hon_page >= pages) g_hon_page = pages - 1;
    if (!nr) {
        const WCHAR *msg = g_hon_state == 1 ? T3("Loading...", "载入中…", "載入中…") :
                           g_hon_state == 3 ? T3("Cannot reach the server.", "无法连接服务器。", "無法連接伺服器。") :
                           g_hon_tab == 0 ? T3("No record yet: a unit is recorded with its first kill.", "还没有记录：单位第一次击杀后就会记在这里。", "還沒有紀錄：單位第一次擊殺後就會記在這裡。")
                                          : T3("No record yet.", "还没有记录。", "還沒有紀錄。");
        text(msg, tx0, ty0 + 60, tw0, 40, 14, 0, 0, C_MUTED, GP_ALIGN_CENTER, GP_ALIGN_CENTER);
    }
    for (int i = g_hon_page * per, k = 0; i < nr && k < per; i++, k++) {
        char **f = rows[i];
        float y = ty0 + 30 + k * rh;
        if (k & 1) fill_rect(tx0, y, tw0, rh, 0x14FFFFFFu);
        if (hovered(H_HONROW, i)) { fill_rect(tx0, y, tw0, rh, 0x30C9A45Cu); stroke_rect(tx0 + 0.5f, y + 0.5f, tw0 - 1, rh - 1, C_BRASS, 1); }
        hit_add(tx0, y, tw0, rh, 0, H_HONROW, i);
        int mine = g_hon_tab == 0;
        int stars = atoi(mine ? f[4] : f[6]);
        int gone = mine && nf[i] >= 9 && f[8][0] == '0';
        ARGB tc = gone ? C_MUTED : C_TEXT;
        WCHAR st[16] = L""; for (int q = 0; q < 5; q++) st[q] = q < stars ? 0x2605 : 0x2606; st[5] = 0;
        WCHAR w1[48], w2[48];
        if (mine) {
            swprintf(v, 96, L"%d", i + 1);
            text(v, tx0 + cols[0] * tw0 + 4, y, (cols[1] - cols[0]) * tw0 - 8, rh, 12, 1, 0, C_MUTED, GP_ALIGN_NEAR, GP_ALIGN_CENTER);
            text(st, tx0 + cols[1] * tw0 + 4, y, (cols[2] - cols[1]) * tw0 - 8, rh, 14, 0, 0, stars ? 0xFFFFE066u : 0x60FFFFFFu, GP_ALIGN_NEAR, GP_ALIGN_CENTER);
            MultiByteToWideChar(CP_ACP, 0, f[2], -1, w1, 48);
            if (gone) { WCHAR t[64]; swprintf(t, 64, L"%ls %ls", w1, T3("(retired)", "（已退役）", "（已退役）")); lstrcpynW(w1, t, 48); }
            text(w1, tx0 + cols[2] * tw0 + 4, y, (cols[3] - cols[2]) * tw0 - 8, rh, 13, 0, 1, tc, GP_ALIGN_NEAR, GP_ALIGN_CENTER);
            MultiByteToWideChar(CP_ACP, 0, f[3], -1, w2, 48);
            text(w2, tx0 + cols[3] * tw0 + 4, y, (cols[4] - cols[3]) * tw0 - 8, rh, 12, 0, 0, tc, GP_ALIGN_NEAR, GP_ALIGN_CENTER);
            MultiByteToWideChar(CP_ACP, 0, f[5], -1, w1, 48);
            text(w1, tx0 + cols[4] * tw0 + 4, y, (cols[5] - cols[4]) * tw0 - 8, rh, 13, 1, 1, tc, GP_ALIGN_NEAR, GP_ALIGN_CENTER);
            MultiByteToWideChar(CP_ACP, 0, f[6], -1, w1, 48);
            text(w1, tx0 + cols[5] * tw0 + 4, y, (cols[6] - cols[5]) * tw0 - 8, rh, 12, 1, 0, tc, GP_ALIGN_NEAR, GP_ALIGN_CENTER);
        } else {
            MultiByteToWideChar(CP_ACP, 0, f[1], -1, w1, 48);
            text(w1, tx0 + cols[0] * tw0 + 4, y, (cols[1] - cols[0]) * tw0 - 8, rh, 13, 1, 1, i < 3 ? 0xFFFFE066u : C_MUTED, GP_ALIGN_NEAR, GP_ALIGN_CENTER);
            MultiByteToWideChar(CP_ACP, 0, f[2], -1, w1, 48);
            text(w1, tx0 + cols[1] * tw0 + 4, y, (cols[2] - cols[1]) * tw0 - 8, rh, 12, 0, 0, C_TEXT, GP_ALIGN_NEAR, GP_ALIGN_CENTER);
            MultiByteToWideChar(CP_ACP, 0, f[4], -1, w1, 48);
            text(w1, tx0 + cols[2] * tw0 + 4, y, (cols[3] - cols[2]) * tw0 - 8, rh, 13, 0, 1, C_TEXT, GP_ALIGN_NEAR, GP_ALIGN_CENTER);
            MultiByteToWideChar(CP_ACP, 0, f[5], -1, w2, 48);
            text(w2, tx0 + cols[3] * tw0 + 4, y, (cols[4] - cols[3]) * tw0 - 8, rh, 12, 0, 0, C_TEXT, GP_ALIGN_NEAR, GP_ALIGN_CENTER);
            text(st, tx0 + cols[4] * tw0 + 4, y, (cols[5] - cols[4]) * tw0 - 8, rh, 14, 0, 0, stars ? 0xFFFFE066u : 0x60FFFFFFu, GP_ALIGN_NEAR, GP_ALIGN_CENTER);
            MultiByteToWideChar(CP_ACP, 0, f[7], -1, w1, 48);
            text(w1, tx0 + cols[5] * tw0 + 4, y, (cols[6] - cols[5]) * tw0 - 8, rh, 13, 1, 1, C_TEXT, GP_ALIGN_NEAR, GP_ALIGN_CENTER);
        }
        /* marks */
        char mk[64]; lstrcpynA(mk, mine ? f[7] : (nf[i] > 8 ? f[8] : ""), sizeof mk);
        float mx = tx0 + cols[6] * tw0 + 4, adv;
        for (char *m = strtok(mk, ","); m; m = strtok(NULL, ",")) {
            char *c = strchr(m, ':'); if (c) *c = 0;                 /* "code:times" (14:44) */
            if (mx + 20 > tx0 + tw0) break;
            hon_mark(m, mx, y + (rh - 16) / 2, &adv); mx += adv;
        }
    }
    /* pages */
    if (pages > 1) {
        float by = py + ph - 44;
        swprintf(v, 96, L"%d / %d", g_hon_page + 1, pages);
        text(v, px + pw / 2 - 40, by, 80, 30, 13, 1, 1, C_TEXT, GP_ALIGN_CENTER, GP_ALIGN_CENTER);
        for (int d = 0; d < 2; d++) {
            float bx = d ? px + pw / 2 + 50 : px + pw / 2 - 80;
            int hov = hovered(H_HONPG, d);
            stroke_rect(bx + 0.5f, by + 0.5f, 29, 29, hov ? C_BRASS_HI : 0x90C9A45Cu, 1.2f);
            float mx = bx + 15, my = by + 15; ARGB c = hov ? C_BRASS_HI : C_TEXT;
            if (d) { line(mx - 3, my - 6, mx + 3, my, c, 2); line(mx + 3, my, mx - 3, my + 6, c, 2); }
            else { line(mx + 3, my - 6, mx - 3, my, c, 2); line(mx - 3, my, mx + 3, my + 6, c, 2); }
            hit_add(bx, by, 30, 30, 0, H_HONPG, d);
        }
    }
}
