/* sghud_login_paint.h - part of sghud.c (included in this order; not a header on its own): the login screen: painting */
/* ---- the login screen ---------------------------------------------------------------------------------------- */
static RECT g_ps_dest;
#define L3(en, cn, tw) (g_lang == 1 ? cn : g_lang == 2 ? tw : en)
static GpImage *g_img_bg, *g_img_adv;
static unsigned *g_lbg; static int g_lbg_w, g_lbg_h; static RECT g_lbg_d;   /* the static layer, client pixels */
static int g_pub_lg;                                                         /* the login state of the published hits */
static GpImage *load_img(const WCHAR *nm)
{
    WCHAR path[MAX_PATH]; GpImage *im = NULL; const char *from = "pack";
    int loose = loose_exists(nm, path);
    if (!(loose && g_art_loose)) im = pack_image(nm);
    if (!im && loose) { from = "file"; if (pGdipLoadImageFromFile(path, &im) != 0) im = NULL; }
    sgr_log("HUD art: %ls %s", nm, im ? from : "MISSING");
    return im;
}
static void draw_img_at(GpImage *im, float x, float y, float w, float h, int cover, float ay)   /* ay: vertical anchor 0..1 */
{
    UINT iw = 0, ih = 0;
    if (!im || pGdipGetImageWidth(im, &iw) || pGdipGetImageHeight(im, &ih) || !iw || !ih) { fill_rect(x, y, w, h, C_INK); return; }
    float sx = 0, sy = 0, sw = (float)iw, sh = (float)ih;
    if (cover) {
        if (sw / sh > w / h) { float nw = sh * w / h; sx = (sw - nw) / 2; sw = nw; }
        else { float nh = sw * h / w; sy = (sh - nh) * ay; sh = nh; }
    }
    pGdipDrawImageRectRect(C.g, im, X(x), Y(y), S(w), S(h), sx, sy, sw, sh, GP_UNIT_PIXEL, NULL, NULL, NULL);
}
static void draw_img(GpImage *im, float x, float y, float w, float h, int cover) { draw_img_at(im, x, y, w, h, cover, 0.5f); }
/* (user 10-31 18:26 Real-ESRGAN, stage 1) the commander portraits Hero-01..11 upscaled x4 (RealESRGAN_x4plus, offline):
   SGHud-hero-NN.png in the game folder (OTA common).  The HUD pages draw them over the game's 80 x 67 portrait. */
static GpImage *g_hero_img[12]; static char g_hero_tried[12];
static GpImage *hero_img(int look)
{
    if (look < 1 || look > 11) return NULL;
    if (!g_hero_tried[look]) {
        WCHAR nm[40]; swprintf(nm, 40, L"SGHud-hero-%02d.png", look);
        g_hero_tried[look] = 1; g_hero_img[look] = load_img(nm);
    }
    return g_hero_img[look];
}
static int hd_portrait(int look, float x0, float y0, float x1, float y1)
{
    GpImage *im = hero_img(look);
    if (!im) return 0;
    fill_rect(x0, y0, x1 - x0, y1 - y0, 0xFF000000u);
    draw_img(im, x0, y0, x1 - x0, y1 - y0, 1);
    return 1;
}
/* (user 11-01 02:38-02:41 "use the original pictures") atlases cut from the game's own art (tools/make_hud_atlases.py):
   SGHud-insg.png  rank insignia, ui-insg.xpf: 4 cols (branch inf/mob/avi/org) x 22 rows (rank index), cells 140 x 44
   SGHud-dcr.png   commander medal ribbons, dcr-NNN.xpf: 32 cols (id % 1000) x 30 rows (id / 1000), cells 44 x 16
   SGHud-brn.png   the four branch pictures + INF/MOB/AVI/ORG label (brw-frm.xpf), 4 cells 34 x 42 */
static GpImage *g_at_img[3]; static char g_at_tried[3];
static GpImage *atlas(int k)
{
    static const WCHAR *nm[3] = { L"SGHud-insg.png", L"SGHud-dcr.png", L"SGHud-brn.png" };
    if (!g_at_tried[k]) { g_at_tried[k] = 1; g_at_img[k] = load_img(nm[k]); }
    return g_at_img[k];
}
/* cell (col,row) of atlas k (cw x ch) fitted into the box, aspect kept; ax: 0 left, 0.5 centre, 1 right */
static int atlas_cell(int k, int col, int row, float cw, float ch, float x, float y, float w, float h, float ax)
{
    GpImage *im = atlas(k); UINT iw = 0, ih = 0;
    if (!im || pGdipGetImageWidth(im, &iw) || pGdipGetImageHeight(im, &ih)) return 0;
    if (col < 0 || row < 0 || (col + 1) * cw > iw || (row + 1) * ch > ih) return 0;
    float s = w / cw < h / ch ? w / cw : h / ch, dw = cw * s, dh = ch * s;
    float dx = x + (w - dw) * ax, dy = y + (h - dh) / 2;
    pGdipDrawImageRectRect(C.g, im, X(dx), Y(dy), S(dw), S(dh), col * cw, row * ch, cw, ch, GP_UNIT_PIXEL, NULL, NULL, NULL);
    return 1;
}
static int insg_img(int branch, int rank, float x, float y, float w, float h, float ax)
{ return rank >= 0 && rank < 22 && atlas_cell(0, branch & 3, rank, 140, 44, x, y, w, h, ax); }
static int medal_img(unsigned id, float x, float y, float w, float h)
{ unsigned f = id % 1000, r = id / 1000; return f && f < 32 && r < 30 && atlas_cell(1, (int)f, (int)r, 44, 16, x, y, w, h, 0.5f); }
static int branch_img(int b, float x, float y, float w, float h) { return atlas_cell(2, b & 3, 0, 34, 42, x, y, w, h, 0.5f); }
/* layout (reference units: the frame is 810 high) */
#define LG_SIDE 470.0f
#define LG_BAR  104.0f
#define LG_CW   460.0f
#define LG_CH   430.0f
static float lg_cx(void) { float x = LG_SIDE + (C.RW - LG_SIDE - LG_CW) / 2; return x < LG_SIDE + 16 ? LG_SIDE + 16 : x; }
static float lg_cy(void) { return (C.RH - LG_BAR - LG_CH) / 2; }
static int g_lg_game;                            /* (11-01) painting the options over the game: no side panel / bar */
static void opt_card_pos(float cw, float ch, float *cx, float *cy)
{
    if (g_lg_game) { *cx = (C.RW - cw) / 2; *cy = (C.RH - ch) / 2; }
    else { *cx = LG_SIDE + (C.RW - LG_SIDE - cw) / 2; *cy = (C.RH - LG_BAR - ch) / 2; }
    if (*cy < 8) *cy = 8;
}
static void login_static(void)                   /* background, side panel, bottom bar, portrait */
{
    if (!g_img_bg && !g_img_adv) { g_img_bg = load_img(L"SGHud-login.jpg"); g_img_adv = load_img(L"SGHud-advisor.jpg"); }
    pGdipSetInterpolationMode(C.g, 7);           /* high quality bicubic */
    draw_img(g_img_bg, 0, 0, C.RW, C.RH, 1);
    float by = C.RH - LG_BAR;
    fill_rect(0, by, C.RW, LG_BAR, 0xE6060A10u);
    draw_img(g_img_adv, 0, by, 170, LG_BAR, 1);
    line(0, by, C.RW, by, 0x99C9A45Cu, 1.2f);
    line(170, by, 170, C.RH, 0x80C9A45Cu, 1);
}
static void login_layer(int w, int h)            /* build the static layer once per size */
{
    if (g_lbg && g_lbg_w == w && g_lbg_h == h && EqualRect(&g_lbg_d, &g_ps_dest)) return;
    free(g_lbg); g_lbg = (unsigned *)calloc((size_t)w * h, 4); g_lbg_w = g_lbg ? w : 0; g_lbg_h = g_lbg ? h : 0; g_lbg_d = g_ps_dest;
    if (!g_lbg) return;
    GpBitmap *bmp = NULL; GpGraphics *keep = C.g;
    if (pGdipCreateBitmapFromScan0(w, h, w * 4, GP_PARGB, (BYTE *)g_lbg, &bmp) != 0) return;
    if (pGdipGetImageGraphicsContext(bmp, &C.g) == 0) {
        pGdipSetSmoothingMode(C.g, GP_SMOOTH_AA); pGdipSetPixelOffsetMode(C.g, GP_PIXOFF_HALF);
        login_static();
        pGdipDeleteGraphics(C.g);
    }
    C.g = keep;
    pGdipDisposeImage(bmp);
}
static float text_w(const WCHAR *t, int len, float size)
{
    GpFont *f = font(size, 0, 0);
    if (!f || len <= 0) return 0;
    GpRectF lay = { 0, 0, 4000, 200 }, box = { 0, 0, 0, 0 };
    pGdipSetStringFormatAlign(g_fmt, GP_ALIGN_NEAR);
    pGdipMeasureString(C.g, t, len, f, &lay, g_fmt, &box, NULL, NULL);
    return box.Width / C.s;
}
static void lg_button(float x, float y, float w, float h, const WCHAR *t, int style, int kind, int arg)
{
    int hov = hovered(kind, arg);
    if (style == 0) {                             /* primary */
        fill_rect(x, y, w, h, hov ? C_BRASS_HI : C_BRASS);
        text(t, x, y, w, h, 20, 0, 1, 0xFF141008u, GP_ALIGN_CENTER, GP_ALIGN_CENTER);
    } else {
        ARGB c = style == 2 ? 0xFFF2A06Au : C_TEXT, b = style == 2 ? (hov ? 0xFFF2A06Au : 0xBFE07A3Au) : (hov ? C_BRASS_HI : 0x99C9A45Cu);
        if (hov) fill_rect(x, y, w, h, 0x24C9A45Cu);
        stroke_rect(x + 0.5f, y + 0.5f, w - 1, h - 1, b, hov ? 1.6f : 1.1f);
        text(t, x, y, w, h, 15, 0, 0, hov && style != 2 ? C_BRASS_HI : c, GP_ALIGN_CENTER, GP_ALIGN_CENTER);
    }
    hit_add(x, y, w, h, 0, kind, arg);
}
static void lg_card(float cx, float cy, float cw, float ch, const WCHAR *latin, const WCHAR *title)
{
    fill_rect(cx, cy, cw, ch, 0xDB0A1016u);
    stroke_rect(cx + 0.5f, cy + 0.5f, cw - 1, ch - 1, C_BRASS, 1.2f);
    diamond(cx + cw / 2, cy + 0.5f, 6, C_BRASS);
    float px = cx + 44, pw = cw - 88;
    if (g_lang) text(latin, px, cy + 30, pw, 20, 13, 1, 0, C_BRASS, GP_ALIGN_NEAR, GP_ALIGN_CENTER);
    text(title, px, cy + 50, pw, 40, 30, 0, 1, C_BRASS_HI, GP_ALIGN_NEAR, GP_ALIGN_CENTER);
}
/* a form: its fields (labels), its buttons (the first one primary, the others in one row) */
static void lg_paint_form(float cx, float cy, const WCHAR *latin, const WCHAR *title, const WCHAR **lab, const WCHAR **btn, const int *bstyle)
{
    HudState *s = &g_ps;
    int nf = s->lg_nf, nb = s->lg_nb, live = s->lg != LG_MAIN;
    if (s->lg == LG_MAIN) nb = 2;                    /* the menu: START + CHANGE PASSWORD (both open CONTINUE first) */
    float step = nf > 2 ? 80 : 90, ih = nf > 2 ? 42 : 46;
    float ch = 108 + nf * step + 8 + 56 + (nb > 1 ? 64 : 0) + 30;
    lg_card(cx, cy, LG_CW, ch, latin, title);
    float px = cx + 44, pw = LG_CW - 88, fy = cy + 108;
    for (int i = 0; i < nf; i++) {
        text(lab[i], px, fy, pw, 20, 14, 0, 0, C_MUTED, GP_ALIGN_NEAR, GP_ALIGN_CENTER);
        float iy = fy + 24;
        int foc = s->lg_focus == i + 1, hov = hovered(H_LFIELD, i);
        fill_rect(px, iy, pw, ih, 0x73000000u);
        stroke_rect(px + 0.5f, iy + 0.5f, pw - 1, ih - 1, foc ? C_BRASS_HI : hov ? C_BRASS : 0x8CC9A45Cu, foc ? 1.6f : 1.1f);
        WCHAR t[48] = { 0 }; int len = 0;
        if (s->lg_mask[i]) { for (len = 0; len < s->lg_len[i] && len < 40; len++) t[len] = 0x25CF; t[len] = 0; }
        else { char a[41] = { 0 }; memcpy(a, s->lg_txt[i], 39); len = MultiByteToWideChar(CP_ACP, 0, a, -1, t, 48) - 1; }
        if (len < 0) len = 0;
        float fs = s->lg_mask[i] ? 14.0f : 18.0f;
        text(t, px + 16, iy, pw - 32, ih, fs, 0, 0, 0xFFF4E2B4u, GP_ALIGN_NEAR, GP_ALIGN_CENTER);
        if (foc && live && !s->lg_blink) {
            int c = s->lg_caret < len ? s->lg_caret : len;
            float x = px + 16 + text_w(t, c, fs) - (c ? 3 : 0);
            line(x + 1, iy + 11, x + 1, iy + ih - 11, C_BRASS_HI, 1.4f);
        }
        hit_add(px, iy, pw, ih, 0, H_LFIELD, i);
        fy += step;
    }
    float by = fy + 8;
    lg_button(px, by, pw, 56, btn[0], bstyle[0], H_LBTN, 0);
    if (nb > 1) {
        float hw = (pw - 12 * (nb - 2)) / (nb - 1);
        for (int i = 1; i < nb; i++) lg_button(px + (i - 1) * (hw + 12), by + 76, hw, 44, btn[i], bstyle[i], H_LBTN, i);
    }
}
static void lg_tri(float cx, float cy, float r, int up, ARGB c)
{
    GpPointF p[3] = { { X(cx - r), Y(cy + (up ? r * 0.5f : -r * 0.5f)) }, { X(cx + r), Y(cy + (up ? r * 0.5f : -r * 0.5f)) },
                      { X(cx), Y(cy + (up ? -r * 0.6f : r * 0.6f)) } };
    pGdipFillPolygon(C.g, brush(c), p, 3, GP_FILL_ALT);
}
static void lg_paint_brief(float cx, float cy)
{
    HudState *s = &g_ps;
    float cw = LG_CW + 80, ch = 586;
    cx -= 40; if (cx < LG_SIDE + 16) cx = LG_SIDE + 16;
    cy = (C.RH - LG_BAR - ch) / 2;
    lg_card(cx, cy, cw, ch, L"WAR RECORD", L3(L"War Record", L"战斗记录", L"戰鬥記錄"));
    float px = cx + 44, pw = cw - 88 - 34, ly = cy + 108, rh = 36;
    fill_rect(px, ly, pw + 34, rh * 10, 0x59000000u);
    stroke_rect(px + 0.5f, ly + 0.5f, pw + 33, rh * 10 - 1, 0x8CC9A45Cu, 1.0f);
    if (!s->lg_cnt)
        text(L3(L"No battle recordings yet.", L"暂无战斗录像。", L"暫無戰鬥錄影。"), px, ly, pw, rh * 10, 16, 0, 0, C_MUTED, GP_ALIGN_CENTER, GP_ALIGN_CENTER);
    for (int i = 0; i < s->lg_nrow; i++) {
        float y = ly + i * rh;
        int sel = s->lg_first + i == s->lg_sel, hov = hovered(H_LROW, i);
        if (sel || hov) fill_rect(px + 1, y + 1, pw - 2, rh - 2, sel ? 0x40C9A45Cu : 0x20C9A45Cu);
        if (sel) { fill_rect(px + 1, y + 1, 3, rh - 2, C_BRASS_HI); }
        if (i) line(px + 8, y, px + pw - 8, y, 0x26C9A45Cu, 1);
        /* the file name: [<planet>_<province>_]SS<yyyymmdd><NN>[_k].rcd (NN: the day's battle number) */
        char nm[80]; lstrcpynA(nm, s->lg_rec[i], 80);
        int L = lstrlenA(nm); if (L > 4 && !lstrcmpiA(nm + L - 4, ".rcd")) nm[L - 4] = 0;
        char *ss = NULL;
        for (char *c = nm; *c; c++) {
            int ok = c[0] == 'S' && c[1] == 'S' && (c == nm || c[-1] == '_');
            for (int j = 2; j < 12 && ok; j++) ok = c[j] >= '0' && c[j] <= '9';
            if (ok) { ss = c; break; }
        }
        WCHAR t[64] = { 0 }, dt[32] = { 0 };
        if (ss) {
            wsprintfW(dt, L"%c%c%c%c-%c%c-%c%c  #%c%c", ss[2], ss[3], ss[4], ss[5], ss[6], ss[7], ss[8], ss[9], ss[10], ss[11]);
            if (ss > nm) {                               /* planet_province: "planet · province" */
                ss[-1] = 0;
                char *u = strchr(nm, '_'); if (u) { *u = 0; }
                WCHAR a[32] = { 0 }, b[32] = { 0 };
                MultiByteToWideChar(CP_ACP, 0, nm, -1, a, 32);
                if (u) MultiByteToWideChar(CP_ACP, 0, u + 1, -1, b, 32);
                if (b[0]) wsprintfW(t, L"%s  \x00b7  %s", a, b); else lstrcpynW(t, a, 64);
            } else lstrcpynW(t, L3(L"Battle recording", L"战斗录像", L"戰鬥錄影"), 64);   /* (an old name: no planet) */
        } else MultiByteToWideChar(CP_ACP, 0, nm, -1, t, 64);
        text(t, px + 16, y, pw - 190, rh, 15, 0, sel, sel ? C_BRASS_HI : C_TEXT, GP_ALIGN_NEAR, GP_ALIGN_CENTER);
        if (dt[0]) text(dt, px + pw - 176, y, 164, rh, 13, 1, 0, sel ? C_BRASS : 0xFF8E8470u, GP_ALIGN_FAR, GP_ALIGN_CENTER);
        hit_add(px, y, pw, rh, 0, H_LROW, i);
    }
    /* the scroll arrows */
    float sx = px + pw, sw = 34;
    line(sx, ly, sx, ly + rh * 10, 0x59C9A45Cu, 1);
    for (int d = 0; d < 2; d++) {
        float y = d ? ly + rh * 10 - 40 : ly, hov = hovered(H_LSCR, d);
        if (hov) fill_rect(sx + 1, y + 1, sw - 2, 38, 0x30C9A45Cu);
        lg_tri(sx + sw / 2, y + 20, 7, !d, hov ? C_BRASS_HI : C_BRASS);
        hit_add(sx, y, sw, 40, 0, H_LSCR, d);
    }
    if (s->lg_cnt > 10) {                            /* the thumb */
        float tr = rh * 10 - 88, th = tr * 10 / s->lg_cnt, ty = ly + 44 + (tr - th) * s->lg_first / (s->lg_cnt - 10);
        if (th < 16) th = 16;
        fill_rect(sx + 13, ty, 8, th, 0x99C9A45Cu);
    }
    WCHAR cnt[48]; wsprintfW(cnt, L3(L"%d recordings", L"共 %d 条录像", L"共 %d 筆錄影"), s->lg_cnt);
    text(cnt, px, ly + rh * 10 + 6, pw, 22, 13, 0, 0, C_MUTED, GP_ALIGN_FAR, GP_ALIGN_CENTER);
    float by = ly + rh * 10 + 36, hw = (pw + 34 - 12) / 2;
    lg_button(px, by, hw, 52, L3(L"PLAY", L"播放", L"播放"), 0, H_LBTN, 0);
    lg_button(px + hw + 12, by, hw, 52, L3(L"Close", L"关闭", L"關閉"), 2, H_LBTN, 1);
}
static void draw565(const unsigned short *buf, int bw, int bh, int stride, float sx, float sy, float sw, float sh, float x, float y, float w, float h)
{
    GpBitmap *b = NULL;
    if (pGdipCreateBitmapFromScan0(bw, bh, stride * 2, 0x00021006, (BYTE *)buf, &b) != 0 || !b) return;   /* 16bpp RGB565 */
    pGdipSetInterpolationMode(C.g, 7);
    pGdipDrawImageRectRect(C.g, b, X(x), Y(y), S(w), S(h), sx, sy, sw, sh, GP_UNIT_PIXEL, NULL, NULL, NULL);
    pGdipDisposeImage(b);
}
/* the new commander's steps (instead of the menu): 1 ID, 2 commander, 3 nation */
static void lg_paint_steps(int cur, float ox)
{
    float fs = ox > 0 ? 15.0f : 19.0f;   /* the narrow column right of the nation viewer */
    text(L3(L"NEW COMMANDER", L"新指挥官", L"新指揮官"), ox + 64, 236, 380, 40, ox > 0 ? 17.0f : 22.0f, !g_lang, 1, C_BRASS_HI, GP_ALIGN_NEAR, GP_ALIGN_CENTER);
    if (g_lang) text(L"NEW COMMANDER", ox + 64, 270, 380, 20, 13, 1, 0, C_BRASS, GP_ALIGN_NEAR, GP_ALIGN_CENTER);
    static const WCHAR *SE[3] = { L"Create ID", L"Select commander", L"Select nation" };
    static const WCHAR *SC[3] = { L"建立账号", L"选择指挥官", L"选择国家" };
    static const WCHAR *ST[3] = { L"建立帳號", L"選擇指揮官", L"選擇國家" };
    for (int i = 0; i < 3; i++) {
        float y = 318 + i * 70;
        int done = i < cur, on = i == cur;
        if (i < 2) line(ox + 87, y + 46, ox + 87, y + 70, done ? C_BRASS : 0x4DC9A45Cu, 1.4f);
        fill_circle(ox + 87, y + 23, 18, on ? C_BRASS : done ? 0x40C9A45Cu : 0x400A1016u);
        stroke_circle(ox + 87, y + 23, 18, on || done ? C_BRASS : 0x66C9A45Cu, 1.2f);
        WCHAR n[4]; wsprintfW(n, L"%d", i + 1);
        if (done) { line(ox + 80, y + 23, ox + 85, y + 29, C_BRASS_HI, 2.2f); line(ox + 85, y + 29, ox + 95, y + 16, C_BRASS_HI, 2.2f); }
        else text(n, ox + 69, y + 5, 36, 36, 16, 1, 1, on ? 0xFF141008u : C_MUTED, GP_ALIGN_CENTER, GP_ALIGN_CENTER);
        text(g_lang == 1 ? SC[i] : g_lang == 2 ? ST[i] : SE[i], ox + 122, y + 5, 320, 36, fs, 0, on, on ? C_BRASS_HI : done ? C_TEXT : C_MUTED,
             GP_ALIGN_NEAR, GP_ALIGN_CENTER);
    }
}
static void lg_paint_hero(void)
{
    HudState *s = &g_ps;
    float cx = LG_SIDE + 24, cw = C.RW - cx - 24, cy = 30, ch = C.RH - LG_BAR - 60;
    lg_card(cx, cy, cw, ch, L"SELECT COMMANDER", L3(L"Select Commander", L"选择指挥官", L"選擇指揮官"));
    /* the 9 portraits */
    float lx = cx + 44, ly = cy + 104, tw = 200, th = 50, fw = th * 78 / 28;   /* face: x 6..84, y 4..32 of the strip */
    for (int i = 0; i < 9; i++) {
        float y = ly + i * (th + 6);
        int sel = s->lg_hero == i + 1, hov = hovered(H_LHERO, i);
        fill_rect(lx, y, tw, th, sel ? 0x40C9A45Cu : hov ? 0x26C9A45Cu : 0x590A1016u);
        if (hero_img(i + 1)) draw_img_at(hero_img(i + 1), lx, y, fw, th, 1, 0.3f);     /* (18:55) the new portraits */
        else if (s->lg_hbtn[i][2] > s->lg_hbtn[i][0]) draw565(g_himg[i], HP_W, HP_H, HP_W, 6, 4, 78, 28, lx, y, fw, th);
        if (!sel && !hov) fill_rect(lx, y, fw, th, 0x40000000u);
        WCHAR n[8]; wsprintfW(n, L"%02d", i + 1);
        text(n, lx + fw, y, tw - fw, th, 18, 1, 1, sel ? C_BRASS_HI : hov ? C_TEXT : C_MUTED, GP_ALIGN_CENTER, GP_ALIGN_CENTER);
        stroke_rect(lx + 0.5f, y + 0.5f, tw - 1, th - 1, sel ? C_BRASS_HI : hov ? C_BRASS : 0x59C9A45Cu, sel ? 1.8f : 1.0f);
        if (sel) diamond(lx - 10, y + th / 2, 5, C_BRASS_HI);
        hit_add(lx, y, tw, th, 0, H_LHERO, i);
    }
    /* the preview */
    float rx = lx + tw + 30, rw = cx + cw - 44 - rx, pvh = rw * HV_H / HV_W;
    if (pvh > 186) { pvh = 186; }
    float pvw = pvh * HV_W / HV_H, pvx = rx + (rw - pvw) / 2, pvy = ly;
    fill_rect(pvx, pvy, pvw, pvh, 0x73000000u);
    {   static GpImage *card[10]; static char tried[10]; int h = s->lg_hero;   /* (18:55) the new commander cards */
        if (h >= 1 && h <= 9 && !tried[h]) { WCHAR nm[40]; swprintf(nm, 40, L"SGHud-heroport-%02d.png", h); tried[h] = 1; card[h] = load_img(nm); }
        if (h >= 1 && h <= 9 && card[h]) draw_img(card[h], pvx, pvy, pvw, pvh, 1);
        else if (s->lg_hview[2] > s->lg_hview[0]) draw565(g_hview, HV_W, HV_H, HV_S, 0, 0, HV_W, HV_H, pvx, pvy, pvw, pvh); }
    stroke_rect(pvx + 0.5f, pvy + 0.5f, pvw - 1, pvh - 1, C_BRASS, 1.2f);
    /* the points */
    float py = pvy + pvh + 18;
    text(L3(L"Points left", L"可分配点数", L"可分配點數"), rx, py, rw - 80, 32, 16, 0, 0, C_MUTED, GP_ALIGN_NEAR, GP_ALIGN_CENTER);
    WCHAR v[16]; wsprintfW(v, L"%d", s->lg_pts);
    text(v, rx + rw - 80, py - 4, 80, 40, 28, 1, 1, s->lg_pts ? C_BRASS_HI : C_MUTED, GP_ALIGN_FAR, GP_ALIGN_CENTER);
    static const WCHAR *NE[4] = { L"TACTICS", L"CLOUT", L"EDUCATION", L"MECH APT" };
    static const WCHAR *NC[4] = { L"战术", L"影响力", L"教育", L"机械能力" };
    static const WCHAR *NT[4] = { L"戰術", L"影響力", L"教育", L"機械能力" };
    py += 40;
    for (int j = 0; j < 4; j++) {
        float y = py + j * 40;
        text(g_lang == 1 ? NC[j] : g_lang == 2 ? NT[j] : NE[j], rx, y, 110, 36, 15, !g_lang, 0, C_TEXT, GP_ALIGN_NEAR, GP_ALIGN_CENTER);
        wsprintfW(v, L"%d", s->lg_stat[j]);
        text(v, rx + 110, y, 34, 36, 17, 1, 1, C_BRASS_HI, GP_ALIGN_FAR, GP_ALIGN_CENTER);
        float bx = rx + 156, bw = rw - 156 - 84;
        bar(bx, y + 15, bw, 6, (s->lg_stat[j] - 5) / 20.0f, C_BRASS);
        for (int d = 0; d < 2; d++) {
            float x = rx + rw - 76 + d * 40;
            int hov = hovered(H_LSTAT, j * 2 + d);
            fill_rect(x, y + 3, 34, 30, hov ? 0x40C9A45Cu : 0x590A1016u);
            stroke_rect(x + 0.5f, y + 3.5f, 33, 29, hov ? C_BRASS_HI : 0x99C9A45Cu, 1.1f);
            line(x + 11, y + 18, x + 23, y + 18, hov ? C_BRASS_HI : C_BRASS, 1.8f);
            if (d) line(x + 17, y + 12, x + 17, y + 24, hov ? C_BRASS_HI : C_BRASS, 1.8f);
            hit_add(x, y + 3, 34, 30, 0, H_LSTAT, j * 2 + d);
        }
    }
    float by = py + 4 * 40 + 10;
    lg_button(rx, by, rw, 48, L3(L"SELECT", L"确定指挥官", L"確定指揮官"), 0, H_LBTN, 0);
    float hw2 = (rw - 12) / 2;
    lg_button(rx, by + 58, hw2, 40, L3(L"Previous", L"上一步", L"上一步"), 1, H_LBTN, 1);
    lg_button(rx + hw2 + 12, by + 58, hw2, 40, L3(L"Next", L"下一步", L"下一步"), 1, H_LBTN, 2);
}
static RECT g_lg_hole;                            /* client pixels left transparent: the game's live viewer */
static void lg_paint_nation(void)
{
    HudState *s = &g_ps;
    float hx0 = fx_ref(s->lg_view[0]), hy0 = fy_ref(s->lg_view[1]), hx1 = fx_ref(s->lg_view[2]), hy1 = fy_ref(s->lg_view[3]);
    float cx = hx0 - 24, cy = hy0 - 84, cw = hx1 - hx0 + 48, ch = hy1 - cy + 16 + 52 + (s->lg_fr ? 62 : 0) + 18;
    fill_rect(cx, cy, cw, ch, 0xDB0A1016u);
    stroke_rect(cx + 0.5f, cy + 0.5f, cw - 1, ch - 1, C_BRASS, 1.2f);
    diamond(cx + cw / 2, cy + 0.5f, 6, C_BRASS);
    if (g_lang) text(L"SELECT NATION", cx + 24, cy + 14, cw - 48, 20, 13, 1, 0, C_BRASS, GP_ALIGN_NEAR, GP_ALIGN_CENTER);
    text(L3(L"Select Nation", L"选择国家", L"選擇國家"), cx + 24, cy + 32, cw - 48, 40, 28, 0, 1, C_BRASS_HI, GP_ALIGN_NEAR, GP_ALIGN_CENTER);
    stroke_rect(hx0 - 1.5f, hy0 - 1.5f, hx1 - hx0 + 3, hy1 - hy0 + 3, C_BRASS, 1.2f);
    SetRect(&g_lg_hole, (int)(X(hx0) + 0.5f), (int)(Y(hy0) + 0.5f), (int)X(hx1), (int)Y(hy1));
    hit_add(hx0, hy0, hx1 - hx0, hy1 - hy0, 0, H_LPASS, 0);
    /* tabs + SELECT */
    static const WCHAR *TE[3] = { L"PLANET", L"FACTION", L"FRIEND" };
    static const WCHAR *TC[3] = { L"星球", L"阵营", L"盟友" };
    static const WCHAR *TT[3] = { L"星球", L"陣營", L"盟友" };
    float ry = hy1 + 16, tw = 110;
    for (int i = 0; i < 3; i++) {
        float x = hx0 + i * (tw + 8);
        int on = s->lg_tab == i, hov = hovered(H_LTAB, i);
        fill_rect(x, ry, tw, 44, on ? 0xE0201A10u : hov ? 0xD0161410u : 0xA00A1016u);
        stroke_rect(x + 0.5f, ry + 0.5f, tw - 1, 43, on ? C_BRASS_HI : hov ? C_BRASS : 0x80C9A45Cu, on ? 1.6f : 1.0f);
        if (on) line(x + 10, ry + 40, x + tw - 10, ry + 40, C_BRASS, 1.6f);
        text(g_lang == 1 ? TC[i] : g_lang == 2 ? TT[i] : TE[i], x, ry, tw, 44, 15, !g_lang, 1, on || hov ? C_BRASS_HI : C_MUTED,
             GP_ALIGN_CENTER, GP_ALIGN_CENTER);
        hit_add(x, ry, tw, 44, 0, H_LTAB, i);
    }
    float sw = hx1 - (hx0 + 3 * (tw + 8)) - 4;
    if (sw > 200) sw = 200;
    lg_button(hx1 - sw, ry, sw, 44, L3(L"SELECT", L"选择", L"選擇"), 0, H_LBTN, 0);
    if (s->lg_fr) {                                 /* the friend ID box */
        float fy = ry + 60;
        text(L3(L"Friend ID", L"盟友账号", L"盟友帳號"), hx0, fy, 110, 44, 15, 0, 0, C_MUTED, GP_ALIGN_NEAR, GP_ALIGN_CENTER);
        float ex = hx0 + 112, ew = hx1 - ex - 2 * 104 - 16;
        int foc = s->lg_focus == 1, hov = hovered(H_LFIELD, 0);
        fill_rect(ex, fy, ew, 44, 0x73000000u);
        stroke_rect(ex + 0.5f, fy + 0.5f, ew - 1, 43, foc ? C_BRASS_HI : hov ? C_BRASS : 0x8CC9A45Cu, foc ? 1.6f : 1.1f);
        WCHAR t[48] = { 0 }; char a[41] = { 0 }; memcpy(a, s->lg_txt[0], 39);
        int len = MultiByteToWideChar(CP_ACP, 0, a, -1, t, 48) - 1; if (len < 0) len = 0;
        text(t, ex + 14, fy, ew - 28, 44, 17, 0, 0, 0xFFF4E2B4u, GP_ALIGN_NEAR, GP_ALIGN_CENTER);
        if (foc && !s->lg_blink) { float x = ex + 14 + text_w(t, s->lg_caret < len ? s->lg_caret : len, 17) - (len ? 3 : 0); line(x + 1, fy + 11, x + 1, fy + 33, C_BRASS_HI, 1.4f); }
        hit_add(ex, fy, ew, 44, 0, H_LFIELD, 0);
        lg_button(ex + ew + 8, fy, 104, 44, L3(L"OK", L"确定", L"確定"), 1, H_LFR, 0);
        lg_button(ex + ew + 120, fy, 104, 44, L3(L"Cancel", L"取消", L"取消"), 2, H_LFR, 1);
    }
    /* the steps + PREVIOUS / NEXT right of the card */
    float ox = cx + cw + 8 - 40;
    lg_paint_steps(2, ox);
    float bx = ox + 64, bw = C.RW - bx - 24;
    if (bw > 60) {
        lg_button(bx, 560, bw, 44, L3(L"Previous", L"上一步", L"上一步"), 1, H_LBTN, 1);
        lg_button(bx, 614, bw, 44, L3(L"Next", L"下一步", L"下一步"), 1, H_LBTN, 2);
    }
}
