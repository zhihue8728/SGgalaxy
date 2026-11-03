/* sghud_draw.h - part of sghud.c (included in this order; not a header on its own): painting primitives: colours, context, hits, brushes / pens, fonts, text, icons */
/* ---- painting ------------------------------------------------------------------------------------------------ */
#define C_BRASS    0xFFC9A45Cu
#define C_BRASS_HI 0xFFF4E2B4u
#define C_INK      0xFF0A1016u
#define C_TEXT     0xFFEDE3CCu
#define C_MUTED    0xFFC9BC9Cu
#define C_HP       0xFF8CC56Bu
#define C_EMBER    0xFFE07A3Au
#define C_ENERGY   0xFF5DA9E9u
#define C_MINE     0xFF6FD3C6u
#define C_ALLY     0xFF9FD8A6u
#define C_ENEMY    0xFFF07A5Eu
#define C_NEUTRAL  0xFF9AA0A6u
static const ARGB BRANCH_C[4] = { 0xFFD7C49Eu, 0xFFE8A85Cu, 0xFF8FC1E3u, 0xFF9CCB7Au };
static ARGB unit_color(const HudUnit *u) { return u->branch >= 0 ? BRANCH_C[u->branch] : u->hero ? C_BRASS_HI : C_MUTED; }
static ARGB rel_color(int r) { return r == REL_MINE ? C_MINE : r == REL_ALLY ? C_ALLY : r == REL_ENEMY ? C_ENEMY : C_NEUTRAL; }
static ARGB alpha(ARGB c, float a) { return ((DWORD)(a * 255.0f + 0.5f) << 24) | (c & 0xFFFFFF); }

typedef struct { GpGraphics *g; float s, ox, oy, RW, RH; float fx0, fy0, fsx, fsy; } Ctx;
static Ctx C;
#define X(v) (C.ox + (v) * C.s)
#define Y(v) (C.oy + (v) * C.s)
#define S(v) ((v) * C.s)

typedef struct { RECT r; int circle, kind, arg; } Hit;
static Hit g_whits[96]; static int g_wnhit;     /* painter */
static Hit g_hits[96]; static int g_nhit;       /* published (lock) - the mouse uses these */
static int g_hit_off;                            /* the layer raster pass: hits were taken in the record pass */
static void hit_add(float x, float y, float w, float h, int circle, int kind, int arg)
{
    if (g_hit_off || g_wnhit >= 96) return;
    Hit *t = &g_whits[g_wnhit++];
    SetRect(&t->r, (int)X(x), (int)Y(y), (int)(X(x + w) + 0.5f), (int)(Y(y + h) + 0.5f));
    t->circle = circle; t->kind = kind; t->arg = arg;
}
static int hovered(int kind, int arg) { return g_ps_hover_kind == kind && g_ps_hover_arg == arg; }

/* frame pixels <-> reference units */
static float fx_ref(float fx) { return (C.fx0 + fx * C.fsx - C.ox) / C.s; }
static float fy_ref(float fy) { return (C.fy0 + fy * C.fsy - C.oy) / C.s; }
static float fx_frame(float rx) { return (rx * C.s + C.ox - C.fx0) / C.fsx; }
static float fy_frame(float ry) { return (ry * C.s + C.oy - C.fy0) / C.fsy; }

static int occluded(float x, float y, float w, float h)
{
    for (int i = 0; i < g_ps.nocc; i++) {
        RECT *o = &g_ps.occ[i];
        float ox0 = fx_ref((float)o->left), oy0 = fy_ref((float)o->top), ox1 = fx_ref((float)o->right), oy1 = fy_ref((float)o->bottom);
        if (x < ox1 && x + w > ox0 && y < oy1 && y + h > oy0) return 1;
    }
    return 0;
}

static GpSolidFill *g_brush; static GpPen *g_pen;
static GpBrush *brush(ARGB c) { pGdipSetSolidFillColor(g_brush, c); return g_brush; }
static GpPen *pen(ARGB c, float w)
{
    if (g_pen) pGdipDeletePen(g_pen);
    pGdipCreatePen1(c, w, GP_UNIT_PIXEL, &g_pen);
    pGdipSetPenLineCap197819(g_pen, GP_CAP_ROUND, GP_CAP_ROUND, GP_CAP_ROUND);
    pGdipSetPenLineJoin(g_pen, GP_JOIN_ROUND);
    return g_pen;
}
static void fill_rect(float x, float y, float w, float h, ARGB c) { pGdipFillRectangle(C.g, brush(c), X(x), Y(y), S(w), S(h)); }
static void stroke_rect(float x, float y, float w, float h, ARGB c, float lw) { pGdipDrawRectangle(C.g, pen(c, S(lw)), X(x), Y(y), S(w), S(h)); }
static void fill_circle(float cx, float cy, float r, ARGB c) { pGdipFillEllipse(C.g, brush(c), X(cx - r), Y(cy - r), S(2 * r), S(2 * r)); }
static void stroke_circle(float cx, float cy, float r, ARGB c, float lw) { pGdipDrawEllipse(C.g, pen(c, S(lw)), X(cx - r), Y(cy - r), S(2 * r), S(2 * r)); }
static void arc(float cx, float cy, float r, float a0, float sweep, ARGB c, float lw)
{
    if (sweep > 0.5f || sweep < -0.5f) pGdipDrawArc(C.g, pen(c, S(lw)), X(cx - r), Y(cy - r), S(2 * r), S(2 * r), a0, sweep);
}
static void line(float x0, float y0, float x1, float y1, ARGB c, float lw) { pGdipDrawLine(C.g, pen(c, S(lw)), X(x0), Y(y0), X(x1), Y(y1)); }
static void diamond(float cx, float cy, float r, ARGB c)
{
    GpPointF p[4] = { { X(cx), Y(cy - r) }, { X(cx + r), Y(cy) }, { X(cx), Y(cy + r) }, { X(cx - r), Y(cy) } };
    pGdipFillPolygon(C.g, brush(c), p, 4, GP_FILL_ALT);
}
static void bar(float x, float y, float w, float h, float frac, ARGB c)
{
    if (frac < 0) frac = 0; if (frac > 1) frac = 1;
    fill_rect(x, y, w, h, 0x1FFFFFFFu);
    if (frac > 0) fill_rect(x, y, w * frac, h, c);
}

/* SVG path data -> GDI+ path (icon space 24 x 24 placed at cx, cy with size sz reference units) */
static const char *num(const char *p, float *v)
{
    while (*p == ' ' || *p == ',') p++;
    char *e; *v = strtof(p, &e);
    return e == p ? NULL : e;
}
static void icon(int id, float cx, float cy, float sz, ARGB col, float lw)
{
    if (id < 0 || id >= IC_COUNT) return;
    GpPath *path; pGdipCreatePath(GP_FILL_ALT, &path);
    float k = S(sz) / 24.0f, bx = X(cx) - S(sz) / 2, by = Y(cy) - S(sz) / 2;
#define PX(v) (bx + (v) * k)
#define PY(v) (by + (v) * k)
    float x = 0, y = 0, sx = 0, sy = 0, lcx = 0, lcy = 0; char cmd = 0, prev = 0;
    const char *p = ICONS[id];
    while (*p) {
        while (*p == ' ' || *p == ',') p++;
        if (!*p) break;
        if ((*p >= 'A' && *p <= 'Z') || (*p >= 'a' && *p <= 'z')) cmd = *p++;
        int rel = cmd >= 'a';
        char c = (char)(rel ? cmd - 32 : cmd);
        float a[7]; const char *q;
        if (c == 'Z') { pGdipClosePathFigure(path); x = sx; y = sy; prev = 'Z'; continue; }
        if (c == 'M' || c == 'L') {
            if (!(q = num(p, &a[0])) || !(q = num(q, &a[1]))) break; p = q;
            float nx = rel ? x + a[0] : a[0], ny = rel ? y + a[1] : a[1];
            if (c == 'M') { pGdipStartPathFigure(path); sx = nx; sy = ny; cmd = rel ? 'l' : 'L'; }
            else pGdipAddPathLine(path, PX(x), PY(y), PX(nx), PY(ny));
            x = nx; y = ny;
        } else if (c == 'H' || c == 'V') {
            if (!(q = num(p, &a[0]))) break; p = q;
            float nx = x, ny = y;
            if (c == 'H') nx = rel ? x + a[0] : a[0]; else ny = rel ? y + a[0] : a[0];
            pGdipAddPathLine(path, PX(x), PY(y), PX(nx), PY(ny)); x = nx; y = ny;
        } else if (c == 'C' || c == 'S') {
            int n = c == 'C' ? 6 : 4, bad = 0;
            q = p;
            for (int i = 0; i < n; i++) if (!(q = num(q, &a[i]))) { bad = 1; break; }
            if (bad) break; p = q;
            float x1, y1, x2, y2, ex, ey;
            if (c == 'C') { x1 = a[0]; y1 = a[1]; x2 = a[2]; y2 = a[3]; ex = a[4]; ey = a[5];
                if (rel) { x1 += x; y1 += y; x2 += x; y2 += y; ex += x; ey += y; } }
            else { x2 = a[0]; y2 = a[1]; ex = a[2]; ey = a[3]; if (rel) { x2 += x; y2 += y; ex += x; ey += y; }
                   int sm = prev == 'C' || prev == 'S'; x1 = sm ? 2 * x - lcx : x; y1 = sm ? 2 * y - lcy : y; }
            pGdipAddPathBezier(path, PX(x), PY(y), PX(x1), PY(y1), PX(x2), PY(y2), PX(ex), PY(ey));
            lcx = x2; lcy = y2; x = ex; y = ey;
        } else if (c == 'A') {
            int bad = 0; q = p;
            for (int i = 0; i < 7; i++) if (!(q = num(q, &a[i]))) { bad = 1; break; }
            if (bad) break; p = q;
            float ex = rel ? x + a[5] : a[5], ey = rel ? y + a[6] : a[6], rx = fabsf(a[0]), ry = fabsf(a[1]);
            int large = a[3] != 0, sweep = a[4] != 0;
            /* endpoint -> centre parameterisation (no rotation in our icons), then line segments */
            float dx = (x - ex) / 2, dy = (y - ey) / 2;
            if (rx < 1e-3f || ry < 1e-3f) { pGdipAddPathLine(path, PX(x), PY(y), PX(ex), PY(ey)); x = ex; y = ey; prev = c; continue; }
            float lam = (dx * dx) / (rx * rx) + (dy * dy) / (ry * ry);
            if (lam > 1) { float r = sqrtf(lam); rx *= r; ry *= r; }
            float num_ = rx * rx * ry * ry - rx * rx * dy * dy - ry * ry * dx * dx;
            float den = rx * rx * dy * dy + ry * ry * dx * dx;
            float co = den > 0 ? sqrtf(fmaxf(0, num_ / den)) : 0;
            if (large == sweep) co = -co;
            float cxp = co * rx * dy / ry, cyp = -co * ry * dx / rx;
            float ccx = cxp + (x + ex) / 2, ccy = cyp + (y + ey) / 2;
            float t0 = atan2f((dy - cyp) / ry, (dx - cxp) / rx), t1 = atan2f((-dy - cyp) / ry, (-dx - cxp) / rx);
            float dt = t1 - t0;
            if (sweep && dt < 0) dt += 6.2831853f;
            if (!sweep && dt > 0) dt -= 6.2831853f;
            int segs = 16; float px0 = x, py0 = y;
            for (int i = 1; i <= segs; i++) {
                float t = t0 + dt * i / segs, nx = ccx + rx * cosf(t), ny = ccy + ry * sinf(t);
                pGdipAddPathLine(path, PX(px0), PY(py0), PX(nx), PY(ny)); px0 = nx; py0 = ny;
            }
            x = ex; y = ey;
        } else break;
        prev = c;
    }
#undef PX
#undef PY
    pGdipDrawPath(C.g, pen(col, S(lw * sz / 24.0f)), path);
    pGdipDeletePath(path);
}

/* ---- the HUD's art pack SGHud.pak (tools/make_hud_pack.py) -------------------------------------------------------
   "SGHP", u32 version 1, u32 count, count x { char name[48]; u32 offset; u32 size; }, then the files as they are.
   The pack is read first; a loose file in the game folder is used only when the pack (or its entry) is missing, or
   with [hud] art_loose=1 (trying new art).  Loose files left from older releases then cannot hide newer pack art. */
#include "sgcrypt.h"
#include "sgfile_key.h"
static const unsigned char *g_pak; static DWORD g_pak_len; static int g_art_loose = -1;
static const void *hud_pack_get(const WCHAR *nm, DWORD *len)
{
    static int tried;
    if (g_art_loose < 0) g_art_loose = GetPrivateProfileIntA("hud", "art_loose", 0, ".\\GORender.ini") != 0;
    if (!tried) {
        tried = 1;
        WCHAR path[MAX_PATH]; GetFullPathNameW(L"GOHud.pak", MAX_PATH, path, NULL);      /* (11-02 GO names) */
        if (GetFileAttributesW(path) == INVALID_FILE_ATTRIBUTES) GetFullPathNameW(L"SGHud.pak", MAX_PATH, path, NULL);
        HANDLE f = CreateFileW(path, GENERIC_READ, FILE_SHARE_READ, NULL, OPEN_EXISTING, 0, NULL);
        if (f != INVALID_HANDLE_VALUE) {
            DWORD sz = GetFileSize(f, NULL);
            HANDLE m = sz != INVALID_FILE_SIZE && sz >= 12 ? CreateFileMappingW(f, NULL, PAGE_READONLY, 0, 0, NULL) : NULL;
            if (m) { g_pak = MapViewOfFile(m, FILE_MAP_READ, 0, 0, 0); CloseHandle(m); }
            CloseHandle(f);
            /* (2026-11-02, user "1/2/3都要加密") an encrypted pack (tools/sgcrypt_files.py, format 2 in sgcrypt.h):
               decrypted once into memory with the key built into the DLL */
            uint64_t plain = 0; uint32_t cn = 0;
            if (g_pak && sgc_trailer(g_pak + sz - (sz >= SGC_TRAILER ? SGC_TRAILER : 0), sz, &plain, &cn)) {
                unsigned char *d = VirtualAlloc(NULL, plain ? (SIZE_T)plain : 1, MEM_COMMIT | MEM_RESERVE, PAGE_READWRITE);
                SgcIdx x;
                if (d && sgc_idx_load(&x, g_pak + plain, cn, plain)) {
                    SgcAes k; sgc_aes_init(&k, SGFILE_KEY);
                    memcpy(d, g_pak, (size_t)plain);
                    sgc_idx_xor(&k, &x, 0, d, (size_t)plain);
                    SecureZeroMemory(&k, sizeof k);
                    sgc_idx_free(&x);
                } else if (d) { VirtualFree(d, 0, MEM_RELEASE); d = NULL; }
                UnmapViewOfFile(g_pak);
                g_pak = d; sz = (DWORD)plain;
                if (!d) sgr_log("HUD art pack: GOHud.pak encrypted, bad index / no memory");
            }
            if (g_pak) {
                DWORD n = *(const DWORD *)(g_pak + 8);
                if (memcmp(g_pak, "SGHP", 4) || *(const DWORD *)(g_pak + 4) != 1 || n > 4096 || 12 + n * 56 > sz) {
                    if (!VirtualFree((void *)g_pak, 0, MEM_RELEASE)) UnmapViewOfFile(g_pak);
                    g_pak = NULL;
                } else g_pak_len = sz;
            }
        }
        sgr_log("HUD art pack: %s%s", g_pak ? "GOHud.pak" : "none (loose files)", g_art_loose ? ", loose files first" : "");
    }
    if (!g_pak) return NULL;
    char a[48]; int i = 0;
    for (; nm[i] && i < 47; i++) a[i] = nm[i] < 128 ? (char)nm[i] : '?';
    a[i] = 0;
    DWORD n = *(const DWORD *)(g_pak + 8);
    for (DWORD k = 0; k < n; k++) {
        const unsigned char *e = g_pak + 12 + k * 56;
        if (_strnicmp((const char *)e, a, 48)) continue;
        DWORD off = *(const DWORD *)(e + 48), sz = *(const DWORD *)(e + 52);
        if (off > g_pak_len || sz > g_pak_len - off) return NULL;
        *len = sz; return g_pak + off;
    }
    return NULL;
}
static int loose_exists(const WCHAR *nm, WCHAR *path)
{
    if (g_art_loose < 0) g_art_loose = GetPrivateProfileIntA("hud", "art_loose", 0, ".\\GORender.ini") != 0;
    GetFullPathNameW(nm, MAX_PATH, path, NULL);
    return GetFileAttributesW(path) != INVALID_FILE_ATTRIBUTES;
}
/* an image from the pack (a memory stream; GDI+ keeps its own reference for the image's lifetime) */
static GpImage *pack_image(const WCHAR *nm)
{
    DWORD len = 0; const void *d = hud_pack_get(nm, &len);
    if (!d) return NULL;
    static HRESULT (WINAPI *mk)(HGLOBAL, BOOL, void **);
    if (!mk) { HMODULE o = LoadLibraryA("ole32.dll"); if (o) mk = (void *)GetProcAddress(o, "CreateStreamOnHGlobal"); }
    HGLOBAL h = mk ? GlobalAlloc(GMEM_MOVEABLE, len) : NULL;
    if (!h) return NULL;
    void *p = GlobalLock(h); memcpy(p, d, len); GlobalUnlock(h);
    void *st = NULL; GpImage *im = NULL;
    if (mk(h, TRUE, &st) != 0 || !st) { GlobalFree(h); return NULL; }
    if (pGdipLoadImageFromStream(st, &im) != 0) im = NULL;
    (*(ULONG (WINAPI ***)(void *))st)[2](st);                                   /* IUnknown::Release */
    return im;
}

/* fonts: Cinzel (shipped, SGHud-Cinzel.ttf) for numbers and Latin names, a CJK system font for the rest */
static GpFontCollection *g_coll; static GpFontFamily *g_fam_num, *g_fam_cjk;
static void fonts_init(void)
{
    static int done; if (done) return; done = 1;
    WCHAR path[MAX_PATH]; DWORD flen = 0;
    const void *fd = hud_pack_get(L"SGHud-Cinzel.ttf", &flen);
    int loose = loose_exists(L"SGHud-Cinzel.ttf", path) && (g_art_loose || !fd);
    if ((loose || fd) && pGdipNewPrivateFontCollection(&g_coll) == 0 &&
        (loose ? pGdipPrivateAddFontFile(g_coll, path) : pGdipPrivateAddMemoryFont(g_coll, fd, (INT)flen)) == 0) {
        int found = 0; pGdipGetFontCollectionFamilyList(g_coll, 1, &g_fam_num, &found);
        if (!found) g_fam_num = NULL;
    }
    static const WCHAR *cjk[] = { L"Microsoft YaHei UI", L"Microsoft YaHei", L"Microsoft JhengHei UI", L"Microsoft JhengHei",
                                  L"SimHei", L"PMingLiU", L"Noto Sans CJK SC", L"Noto Sans CJK TC", L"WenQuanYi Micro Hei",
                                  L"Arial Unicode MS", L"Tahoma", L"Arial", NULL };
    for (int i = 0; cjk[i] && !g_fam_cjk; i++)
        if (pGdipCreateFontFamilyFromName(cjk[i], NULL, &g_fam_cjk) != 0) g_fam_cjk = NULL;
    if (!g_fam_num) {
        static const WCHAR *ser[] = { L"Georgia", L"Times New Roman", NULL };
        for (int i = 0; ser[i] && !g_fam_num; i++)
            if (pGdipCreateFontFamilyFromName(ser[i], NULL, &g_fam_num) != 0) g_fam_num = NULL;
        if (!g_fam_num) g_fam_num = g_fam_cjk;
    }
    sgr_log("HUD fonts: numbers %s, text %s", g_coll && g_fam_num ? "Cinzel" : "fallback", g_fam_cjk ? "ok" : "MISSING");
}

typedef struct { GpFont *f; float px; int num, bold; } FontC;
static FontC g_fc[16]; static int g_nfc;
static GpFont *font(float size, int numeric, int bold)
{
    float px = S(size);
    for (int i = 0; i < g_nfc; i++)
        if (g_fc[i].num == numeric && g_fc[i].bold == bold && fabsf(g_fc[i].px - px) < 0.25f) return g_fc[i].f;
    GpFontFamily *fam = numeric ? g_fam_num : g_fam_cjk;
    if (!fam) return NULL;
    GpFont *f = NULL;
    if (pGdipCreateFont(fam, px, bold ? GP_FONT_BOLD : 0, GP_UNIT_PIXEL, &f) != 0 &&
        pGdipCreateFont(fam, px, 0, GP_UNIT_PIXEL, &f) != 0) return NULL;
    if (g_nfc == 16) { pGdipDeleteFont(g_fc[0].f); memmove(g_fc, g_fc + 1, sizeof(FontC) * 15); g_nfc = 15; }
    FontC fc = { f, px, numeric, bold }; g_fc[g_nfc++] = fc;
    return f;
}
static int is_latin(const WCHAR *t) { for (; *t; t++) if (*t > 0x2ff) return 0; return 1; }
static GpStringFormat *g_fmt;
static void text(const WCHAR *t, float x, float y, float w, float h, float size, int numeric, int bold, ARGB c, int align, int valign)
{
    if (!t || !*t) return;
    GpFont *f = font(size, numeric && is_latin(t), bold);
    if (!f) return;
    pGdipSetStringFormatAlign(g_fmt, align);
    pGdipSetStringFormatLineAlign(g_fmt, valign);
    GpRectF r = { X(x), Y(y), S(w), S(h) };
    pGdipDrawString(C.g, t, -1, f, &r, g_fmt, brush(c));
}
