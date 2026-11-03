/* sghud_pages.h - part of sghud.c (included in this order; not a header on its own): battle report, unit growth, commander info (F4), rank frames, login painting entry */
/* ---- BATTLE REPORT on the result window (user 10-31 15:01 "units should not only show XP"): over the window's right box
   (437,30)-(725,372) - result, MVP, each unit (alive / destroyed, stars, kills, level, XP, medals of this battle), the
   bonuses.  Data: <board base>/honor/report.txt (board_mail.report_page); while it is missing the game's list shows. */
/* (user 10-31 15:27 "redesign the left half: the resources need not be so big - the point is raising the units"): over the
   window's left box (80,30)-(415,372): commander + honor gained (one line), the four branches (level, XP bar), every unit's
   growth (stars, level bar 1..60 with this battle's climb, how far to the next star), the resources in one line. */
/* (15:45 user "keep the portrait", "not only text - the branch pictures and the Rank") the panel leaves holes where the game
   paints the commander portrait and the four branch pictures (+ INF/MOB/AVI/ORG), and lays its rows out beside them. */
#define GR_PX0 91.0f
#define GR_PY0 73.0f
#define GR_PX1 170.0f
#define GR_PY1 130.0f
#define GR_BX0 88.0f
#define GR_BX1 124.5f
static float gr_btop(int i) { return 162.7f + 48.85f * i; }   /* window y of branch picture i (its label ends 43 lower) */
/* fill (x0,y0)-(x1,y1) except the holes h[i] = {x0,y0,x1,y1}: one polygon, alternate fill, zero-width bridges to the holes */
static void fill_holed(float x0, float y0, float x1, float y1, const float (*h)[4], int n, ARGB c)
{
    GpPointF p[4 + 7 * 8]; int k = 0;
#define GP_(a, b) (p[k].X = X(a), p[k].Y = Y(b), k++)
    GP_(x0, y0); GP_(x1, y0); GP_(x1, y1); GP_(x0, y1);
    for (int i = 0; i < n && i < 8; i++) {
        GP_(x0, h[i][1]); GP_(h[i][0], h[i][1]); GP_(h[i][0], h[i][3]); GP_(h[i][2], h[i][3]); GP_(h[i][2], h[i][1]); GP_(h[i][0], h[i][1]);
        GP_(x0, h[i][1]);
    }
#undef GP_
    pGdipFillPolygon(C.g, brush(c), p, k, GP_FILL_ALT);
}
static void paint_growth(float bx, float by, char **Cm, char *Br[][9], int nb, char *U[][17], int nu)
{
    float x0 = fx_ref(bx + 82), y0 = fy_ref(by + 32), x1 = fx_ref(bx + 413), y1 = fy_ref(by + 370), w = x1 - x0;
    WCHAR v[160];
    /* the holes (ref coords) - portrait, then the four branch pictures (top to bottom: the polygon walks down x0) */
    float H[5][4];
    H[0][0] = fx_ref(bx + GR_PX0); H[0][1] = fy_ref(by + GR_PY0); H[0][2] = fx_ref(bx + GR_PX1); H[0][3] = fy_ref(by + GR_PY1);
    for (int i = 0; i < 4; i++) {
        H[1 + i][0] = fx_ref(bx + GR_BX0); H[1 + i][1] = fy_ref(by + gr_btop(i)); H[1 + i][2] = fx_ref(bx + GR_BX1); H[1 + i][3] = fy_ref(by + gr_btop(i) + 44.5f);
    }
    fill_holed(x0, y0, x1, y1, (const float (*)[4])H, 5, 0xFA0A1016u);
    hd_portrait(g_ps.my_look, H[0][0], H[0][1], H[0][2], H[0][3]);   /* (18:26) the HD portrait over the game's */
    for (int i = 0; i < 5; i++) stroke_rect(H[i][0] - 1, H[i][1] - 1, H[i][2] - H[i][0] + 2, H[i][3] - H[i][1] + 2, i ? 0x90C9A45Cu : 0xE0C9A45Cu, i ? 1.2f : 1.6f);
    float hy0 = H[0][1], pa = g_rep_anim;
    /* (16:51 user) no title over the portrait; (17:44) over it: planet · nation · regiment */
    {   WCHAR pl[32], na[32], rg[40];
        MultiByteToWideChar(CP_ACP, 0, Cm[5], -1, pl, 32); MultiByteToWideChar(CP_ACP, 0, Cm[6], -1, na, 32); MultiByteToWideChar(CP_ACP, 0, Cm[7], -1, rg, 40);
        float ty = y0 + 12, th = hy0 - ty - 6, tx = H[0][0];
        if (pl[0] || na[0]) {
            fill_circle(tx + 7, ty + th / 2, 6, 0xFF2E6DA4u);           /* a little planet with its ring */
            arc(tx + 7, ty + th / 2, 9, 200, 140, 0xFFC9A45Cu, 1.2f);
            fill_circle(tx + 5, ty + th / 2 - 2, 2, 0x70FFFFFFu);
            WCHAR hd[128];
            if (rg[0]) swprintf(hd, 128, L"%ls  \x00b7  %ls  \x00b7  %ls", pl, na, rg); else swprintf(hd, 128, L"%ls  \x00b7  %ls", pl, na);
            text(hd, tx + 20, ty, x1 - tx - 30, th, 14, 0, 1, C_BRASS_HI, GP_ALIGN_NEAR, GP_ALIGN_CENTER);
            line(tx, hy0 - 4, x1 - 12, hy0 - 4, 0x50C9A45Cu, 1);
        }
    }
    /* beside the portrait: name, honor (+ this battle), resources */
    float cx = H[0][2] + 10, cw = x1 - 10 - cx, ch = H[0][3] - H[0][1];
    WCHAR nm[48]; MultiByteToWideChar(CP_ACP, 0, Cm[1], -1, nm, 48);
    text(nm, cx, hy0, cw, ch * 0.34f, 16, 0, 1, C_TEXT, GP_ALIGN_NEAR, GP_ALIGN_CENTER);
    long h0 = atol(Cm[2]), h1 = atol(Cm[3]), dh = (long)((h1 - h0) * pa);
    swprintf(v, 160, L"%ls %ld.%02ld", T3("Honor", "声望", "聲望"), h1 / 100, (h1 < 0 ? -h1 : h1) % 100);
    text(v, cx, hy0 + ch * 0.34f, cw * 0.55f, ch * 0.3f, 12, 0, 0, C_BRASS_HI, GP_ALIGN_NEAR, GP_ALIGN_CENTER);
    if (dh) {
        swprintf(v, 160, L"%ls%ld.%02ld", dh > 0 ? L"+" : L"-", (dh < 0 ? -dh : dh) / 100, (dh < 0 ? -dh : dh) % 100);
        text(v, cx + cw * 0.55f, hy0 + ch * 0.34f, cw * 0.45f, ch * 0.3f, 12, 1, 1, dh > 0 ? 0xFF8BE28Bu : 0xFFE57373u, GP_ALIGN_FAR, GP_ALIGN_CENTER);
    }
    line(cx, hy0 + ch * 0.66f, x1 - 10, hy0 + ch * 0.66f, 0x40C9A45Cu, 1);
    static const WCHAR *RN[3][5] = { { L"$", L"Ore", L"Si", L"U", L"S" }, { L"金", L"矿", L"硅", L"铀", L"硫" }, { L"金", L"礦", L"矽", L"鈾", L"硫" } };
    static const ARGB RC[5] = { 0xFF9FE8E8u, 0xFFB8C4E0u, 0xFFFF8A65u, 0xFF9FD8F0u, 0xFFFFE066u };
    char rr[80]; lstrcpynA(rr, Cm[4], sizeof rr);
    int ri = 0; float rw = cw / 5;
    for (char *tk = strtok(rr, ","); tk && ri < 5; tk = strtok(NULL, ","), ri++) {
        float rx = cx + ri * rw, ry = hy0 + ch * 0.68f, rh2 = ch * 0.32f;
        fill_circle(rx + 4, ry + rh2 / 2, 3, atoi(tk) ? RC[ri] : 0x50FFFFFFu);
        swprintf(v, 160, L"%ls%d", RN[g_lang][ri], atoi(tk));
        text(v, rx + 9, ry, rw - 9, rh2, 10, 0, 0, atoi(tk) ? C_TEXT : C_MUTED, GP_ALIGN_NEAR, GP_ALIGN_CENTER);
    }
    /* the two columns: branches beside the game's pictures, units on the right */
    float sy = H[0][3] + (H[1][1] - H[0][3]) * 0.5f, sx = x0 + w * 0.36f;
    line(x0 + 8, H[0][3] + 6, x1 - 8, H[0][3] + 6, 0x60C9A45Cu, 1);
    text(T3("Branch", "兵科", "兵科"), x0 + 8, H[0][3] + 7, sx - x0 - 8, H[1][1] - H[0][3] - 8, 11, 0, 1, C_BRASS, GP_ALIGN_NEAR, GP_ALIGN_CENTER);
    (void)sy;
    float bxr = H[1][2] + 6, bw = sx - 6 - bxr;
    for (int i = 0; i < nb && i < 4; i++) {
        int b = !strcmp(Br[i][1], "inf") ? 0 : !strcmp(Br[i][1], "mob") ? 1 : !strcmp(Br[i][1], "avi") ? 2 : 3;
        float ty = H[1 + b][1], th = H[1 + b][3] - ty;
        int l0 = atoi(Br[i][2]), l1 = atoi(Br[i][3]), xp = atoi(Br[i][4]), nd = atoi(Br[i][5]), upb = l1 > l0;
        WCHAR rk[32], rk0[32]; MultiByteToWideChar(CP_ACP, 0, Br[i][7], -1, rk, 32); MultiByteToWideChar(CP_ACP, 0, Br[i][6], -1, rk0, 32);
        /* (11-01) the game's insignia (ui-insg) right, the rank's name left of it */
        float iw2 = 0;
        if (Br[i][8][0] && insg_img(b, atoi(Br[i][8]), sx - 4 - 74, ty - th * 0.04f, 74, th * 0.44f, 1)) iw2 = 76;
        else if (Br[i][8][0]) { insignia(sx - 16, ty + th * 0.18f, 22, atoi(Br[i][8])); iw2 = 28; }
        if (upb && wcscmp(rk, rk0)) {                    /* promoted this battle */
            swprintf(v, 160, L"%ls\x2192%ls", rk0, rk);
            text(v, bxr, ty, bw - iw2, th * 0.36f, 12, 0, 1, 0xFFFFE066u, GP_ALIGN_NEAR, GP_ALIGN_CENTER);
        } else text(rk[0] ? rk : branch_name(b), bxr, ty, bw - iw2, th * 0.36f, 13, 0, 1, C_BRASS_HI, GP_ALIGN_NEAR, GP_ALIGN_CENTER);
        if (upb) swprintf(v, 160, L"Lv %d\x2192%d", l0, l1); else swprintf(v, 160, L"Lv %d", l1);
        text(v, bxr, ty + th * 0.36f, bw * 0.62f, th * 0.3f, 11, 1, upb, upb ? 0xFF8BE28Bu : C_TEXT, GP_ALIGN_NEAR, GP_ALIGN_CENTER);
        swprintf(v, 160, L"%d%%", nd > 0 ? xp * 100 / nd : 100);
        text(v, bxr + bw * 0.6f, ty + th * 0.36f, bw * 0.4f, th * 0.3f, 10, 1, 0, C_MUTED, GP_ALIGN_FAR, GP_ALIGN_CENTER);
        bar(bxr, ty + th * 0.74f, bw, th * 0.12f, (nd > 0 ? (float)xp / nd : 1) * pa, upb ? 0xFF8BE28Bu : C_BRASS);   /* (17:44) fills up */
    }
    line(sx, H[0][3] + 12, sx, y1 - 8, 0x40C9A45Cu, 1);
    /* units: stars, name, the level track 1..60 (this battle's climb in green), how far to the next star */
    float ux = sx + 8, uw = x1 - 8 - ux, yy = H[0][3] + 7;
    text(T3("Units", "单位成长", "單位成長"), ux, yy, uw * 0.5f, H[1][1] - H[0][3] - 8, 11, 0, 1, C_BRASS, GP_ALIGN_NEAR, GP_ALIGN_CENTER);
    text(T3("Lv 60 \x2192 \x2605", "60 级升星", "60 級升星"), ux + uw * 0.5f, yy, uw * 0.5f, H[1][1] - H[0][3] - 8, 9, 0, 0, C_MUTED, GP_ALIGN_FAR, GP_ALIGN_CENTER);
    yy = H[1][1];
    float rh = (y1 - 6 - yy) / (nu > 0 ? nu : 1);
    if (rh > 54) rh = 54;
    int two = rh >= 25;                                  /* two lines a unit when they fit */
    float big = rh >= 44 ? 1.25f : rh >= 34 ? 1.12f : 1.0f;
    for (int i = 0; i < nu && yy + rh <= y1 - 4; i++, yy += rh) {
        char **f = U[i];
        int st = atoi(f[4]), st0 = atoi(f[5]), lv0 = atoi(f[8]), lv = atoi(f[9]), uxp = atoi(f[13]), nd = atoi(f[14]), al = f[7][0] == '1';
        int up = st > st0;
        if (i & 1) fill_rect(ux - 4, yy, uw + 8, rh, 0x12FFFFFFu);
        MultiByteToWideChar(CP_ACP, 0, f[2], -1, nm, 48);
        WCHAR sv[8]; for (int q = 0; q < 5; q++) sv[q] = q < st ? 0x2605 : 0x2606; sv[5] = 0;
        float l1h = two ? rh * 0.5f : rh, fs = (two ? 11 : 10) * big, sw = fs * 4.6f;
        if (up) swprintf(v, 160, L"\x2605%d %ls", st, T3("star up!", "升星！", "升星！"));
        else if (lv > lv0) swprintf(v, 160, L"Lv %d\x2192%d", lv0, lv);
        else swprintf(v, 160, L"Lv %d", lv);
        ARGB lc = up ? 0xFFFFE066u : lv > lv0 ? 0xFF8BE28Bu : C_TEXT;
        if (two) {
            text(sv, ux, yy + 1, sw, l1h, fs * 0.85f, 0, 0, st ? 0xFFFFE066u : 0x50FFFFFFu, GP_ALIGN_NEAR, GP_ALIGN_CENTER);
            text(nm, ux + sw + 2, yy + 1, uw - sw - 2 - uw * 0.36f, l1h, fs, 0, 1, al ? C_TEXT : C_MUTED, GP_ALIGN_NEAR, GP_ALIGN_CENTER);
            text(v, ux + uw * 0.62f, yy + 1, uw * 0.38f, l1h, fs, 1, up || lv > lv0, lc, GP_ALIGN_FAR, GP_ALIGN_CENTER);
        } else {
            swprintf(sv, 8, st ? L"\x2605%d" : L"", st);
            text(sv, ux, yy, fs * 2.2f, rh, fs, 1, 1, 0xFFFFE066u, GP_ALIGN_NEAR, GP_ALIGN_CENTER);
            text(nm, ux + fs * 2.2f, yy, uw * 0.42f - fs * 2.2f, rh, fs, 0, 1, al ? C_TEXT : C_MUTED, GP_ALIGN_NEAR, GP_ALIGN_CENTER);
            text(v, ux + uw * 0.74f, yy, uw * 0.26f, rh, fs, 1, up || lv > lv0, lc, GP_ALIGN_FAR, GP_ALIGN_CENTER);
        }
        float tx = two ? ux : ux + uw * 0.42f, tw = two ? uw * 0.62f : uw * 0.31f, th = two ? 5 : 4;
        float ty = two ? yy + l1h + (rh - l1h) / 2 - th / 2 - 1 : yy + rh / 2 - th / 2;
        fill_rect(tx, ty, tw, th, 0x24FFFFFFu);
        if (up) fill_rect(tx, ty, tw * pa, th, 0xFFFFE066u);
        else {
            float a0 = tw * (lv0 - 1) / 59.0f, a1 = tw * ((lv - 1) + (nd > 0 ? (float)uxp / nd : 0)) / 59.0f;
            if (a1 > tw) a1 = tw;
            fill_rect(tx, ty, a0, th, C_BRASS);
            a1 = a0 + (a1 - a0) * pa;                    /* (17:44) this battle's climb grows */
            if (a1 > a0) fill_rect(tx + a0, ty, a1 - a0, th, 0xFF8BE28Bu);
        }
        for (int q = 1; q < 6; q++) line(tx + tw * q / 6, ty, tx + tw * q / 6, ty + th, 0x40000000u, 1);
        if (two) {
            if (st >= 5 && lv >= 60) swprintf(v, 160, L"%ls", T3("max", "满星", "滿星"));
            else swprintf(v, 160, g_lang == 1 ? L"\x2605%d 差 %d 级" : g_lang == 2 ? L"\x2605%d 差 %d 級" : L"%d lv to \x2605%d",
                          g_lang ? st + 1 : 60 - lv, g_lang ? 60 - lv : st + 1);
            text(v, ux + uw * 0.64f, yy + l1h - 1, uw * 0.36f, rh - l1h, 9, 0, 0, C_MUTED, GP_ALIGN_FAR, GP_ALIGN_CENTER);
        }
    }
    /* (17:44) stripes along the bottom */
    {   float sy = y1 - 12, sh = 8;
        GpPointF clip[4] = { { 0, 0 } }; (void)clip;
        for (float sx = x0 + 6; sx < x1 - 14; sx += 14) {
            GpPointF st[4] = { { X(sx), Y(sy + sh) }, { X(sx + 7), Y(sy + sh) }, { X(sx + 13), Y(sy) }, { X(sx + 6), Y(sy) } };
            pGdipFillPolygon(C.g, brush(0x70C9A45Cu), st, 4, GP_FILL_ALT);
        }
        line(x0 + 6, sy - 2, x1 - 6, sy - 2, 0x60C9A45Cu, 1);
    }
    rank_frame(x0, y0, x1, y1, g_rep_tier, g_rep_reinc);   /* (17:47) the frame by rank */
}
/* (15:45 user "the result needs a picture: victory or defeat") the emblem in the report's banner: a gold laurel wreath
   around a star (victory), a broken red shield (defeat), a grey flag with back-chevrons (retreat). */
static void result_emblem(int res, float cx, float cy, float r)
{
    if (res == 1) {
        GpPointF p[20]; int n = medal_shape(MS_STAR5, cx, cy - r * 0.04f, r * 0.62f, p);
        fill_grad(p, n, 0xFFFFF3B0u, 0xFFC08A10u, cy - r * 0.66f, cy + r * 0.6f, 0, 0, 0, 0, 0);
        pGdipDrawPolygon(C.g, pen(0xFF7A5200u, S(1.3f)), p, n);
        for (int sd = -1; sd <= 1; sd += 2) {            /* the wreath: two branches of leaves */
            float R = r * 0.86f;                         /* the stem, then leaf pairs along it (tips toward the top) */
            for (int i = 0; i < 6; i++) {
                float ang = 3.0f - i * 0.29f, s1 = sinf(ang), c1 = cosf(ang);
                float px2 = cx + sd * R * s1, py2 = cy - R * c1, tx = -sd * c1, ty = -s1;   /* toward smaller angle = up */
                float rx = sd * s1, ry = -c1, L = r * (0.24f - i * 0.012f), W = r * 0.075f;
                for (int s = -1; s <= 1; s += 2) {
                    float dx = tx * 0.8f + rx * 0.6f * s, dy = ty * 0.8f + ry * 0.6f * s, nx = -dy, ny = dx;
                    float mx = px2 + dx * L, my = py2 + dy * L;
                    GpPointF lf[4] = { { X(px2), Y(py2) }, { X(mx + nx * W), Y(my + ny * W) },
                                       { X(px2 + dx * L * 2), Y(py2 + dy * L * 2) }, { X(mx - nx * W), Y(my - ny * W) } };
                    pGdipFillPolygon(C.g, brush(s > 0 ? 0xFFFFD54Fu : 0xFFD9A520u), lf, 4, GP_FILL_ALT);
                }
            }
            arc(cx, cy, R, sd > 0 ? -2.0f : 99.0f, 83, 0xFFB8860Bu, 1.4f);
        }
        line(cx - r * 0.3f, cy + r * 0.95f, cx + r * 0.3f, cy + r * 0.95f, 0xFFD9A520u, 2);
    } else if (res == 0) {
        GpPointF p[20]; int n = medal_shape(MS_SHIELD, cx, cy, r * 0.95f, p);   /* a shield, split by a crack */
        fill_grad(p, n, 0xFFE57373u, 0xFF6F1515u, cy - r, cy + r, 0, 0, 0, 0, 0);
        pGdipDrawPolygon(C.g, pen(0xFF3A0A0Au, S(1.4f)), p, n);
        stroke_circle(cx, cy - r * 0.1f, r * 0.42f, 0x70FFFFFFu, 1.4f);
        float ck[5][2] = { { 0.08f, -1.02f }, { -0.16f, -0.38f }, { 0.14f, 0.05f }, { -0.1f, 0.5f }, { 0.04f, 1.02f } };
        for (int i = 0; i < 4; i++) {
            line(cx + ck[i][0] * r, cy + ck[i][1] * r, cx + ck[i + 1][0] * r, cy + ck[i + 1][1] * r, 0xFF0A1016u, 3.2f);
            line(cx + ck[i][0] * r + 1.2f, cy + ck[i][1] * r, cx + ck[i + 1][0] * r + 1.2f, cy + ck[i + 1][1] * r, 0x50FFB0B0u, 0.8f);
        }
    } else {
        line(cx - r * 0.45f, cy + r, cx - r * 0.45f, cy - r, 0xFFB0BEC5u, 2.2f);
        GpPointF fl[4] = { { X(cx - r * 0.4f), Y(cy - r) }, { X(cx + r * 0.8f), Y(cy - r * 0.6f) }, { X(cx - r * 0.4f), Y(cy - r * 0.1f) }, { X(cx - r * 0.4f), Y(cy - r) } };
        pGdipFillPolygon(C.g, brush(0xFFECEFF1u), fl, 4, GP_FILL_ALT);
        for (int k = 0; k < 2; k++) {
            float ax = cx + r * (0.2f + 0.4f * k), ay = cy + r * 0.45f;
            line(ax + r * 0.25f, ay - r * 0.3f, ax, ay, 0xFF90A4AEu, 2); line(ax, ay, ax + r * 0.25f, ay + r * 0.3f, 0xFF90A4AEu, 2);
        }
    }
}
/* ---- COMMANDER INFO (user 10-31 17:14 "optimise the commander info HUD - plan what else it can show", plan confirmed
   17:31): over the game's F4 window CUserInfoWnd (584 x 411): the four branches side by side (rank, level, XP, how far
   to the next rank), the commander (the game's portrait shows through, name, title, nation, regiment, superior,
   reincarnation, honor, prestige, record), attributes with what they do (the game's spin buttons stay: the arrows here
   pass the click), resources in one column, the army (deploy limit / roster, best unit, lifetime kills, battles), the
   nation (allies, provinces, office), the last battle, the commander medals (hover = text), mercenary + close.
   Data: <board base>/honor/cmd.txt (board_mail.cmd_page); live attribute values from the window's own statics. */
/* ---- RANK FRAMES (user 10-31 17:47 "the frame of the commander info and the battle result by rank - the higher the
   rank, the more splendid"): five tiers by the commander's top rank (21 ranks, commander_deploy.RANK_TITLES):
     0 soldiers  (recruit .. PFC)        a thin brass line
     1 NCOs      (corporal .. staff sgt) a double line, corner brackets
     2 officers  (warrant .. sr captain) a bronze band, studded corners, a chevron crest
     3 field     (major .. brigadier)    a gold band, filigree corners, rivets, a laurel crest with a star
     4 generals  (maj. general ..)       a heavy gold band with a light running round it, star corners, a winged crest
   a reincarnated commander gets a faint violet glow around the frame.  [hud] frame_tier=N forces a tier (tests). */
static int g_frame_tier_ini = -2;
static int rank_tier(int rank)
{
    if (g_frame_tier_ini == -2) g_frame_tier_ini = GetPrivateProfileIntA("hud", "frame_tier", -1, ".\\GORender.ini");
    if (g_frame_tier_ini >= 0 && g_frame_tier_ini <= 4) return g_frame_tier_ini;
    return rank <= 2 ? 0 : rank <= 5 ? 1 : rank <= 10 ? 2 : rank <= 16 ? 3 : 4;
}
static void band_grad(float x, float y, float w, float h, ARGB c1, ARGB c2, int vert)
{
    GpPointF g0 = { vert ? X(x) : 0, vert ? 0 : Y(y) }, g1 = { vert ? X(x + w) : 0, vert ? 0 : Y(y + h) };
    GpLineGradient *lg = NULL;
    pGdipCreateLineBrush(&g0, &g1, c1, c2, 3, &lg);
    pGdipFillRectangle(C.g, lg ? (GpBrush *)lg : brush(c1), X(x), Y(y), S(w), S(h));
    if (lg) pGdipDeleteBrush((GpBrush *)lg);
}
static void star5(float cx, float cy, float r, ARGB c)
{
    GpPointF p[10];
    for (int i = 0; i < 10; i++) { float a = -1.5708f + i * 0.62832f, rr = (i & 1) ? r * 0.45f : r; p[i].X = X(cx + rr * cosf(a)); p[i].Y = Y(cy + rr * sinf(a)); }
    pGdipFillPolygon(C.g, brush(c), p, 10, GP_FILL_ALT);
}
/* tier 4: a light running round the frame band (4 s a round) */
typedef struct { float x0, y0, x1, y1, bw; } GlowReq;
static GlowReq g_glow[4]; static int g_nglow, g_glow_defer;
static void glow_light(float x0, float y0, float x1, float y1, float bw)
{
    float w = x1 - x0, h = y1 - y0;
    float per = 2 * (w + h), pos = (float)(GetTickCount() % 4000) / 4000.0f * per;
    for (int k = 0; k < 2; k++) {
        float q = fmodf(pos + k * per / 2, per), lx, ly, len = 70;
        ARGB gl = 0xB0FFFFFFu;
        if (q < w) { lx = x0 + q; band_grad(lx - len / 2, y0, len, bw, 0x00FFFFFFu, gl, 1); }
        else if (q < w + h) { ly = y0 + q - w; band_grad(x1 - bw, ly - len / 2, bw, len, 0x00FFFFFFu, gl, 0); }
        else if (q < 2 * w + h) { lx = x1 - (q - w - h); band_grad(lx - len / 2, y1 - bw, len, bw, gl, 0x00FFFFFFu, 1); }
        else { ly = y1 - (q - 2 * w - h); band_grad(x0, ly - len / 2, bw, len, gl, 0x00FFFFFFu, 0); }
    }
}
static void paint_glow(void)
{
    for (int i = 0; i < g_nglow; i++) {
        const GlowReq *q = &g_glow[i];
        /* the layer keeps the frame's bounds (not the lights'): its place stays put and only the tiles the lights
           pass through are drawn again */
        if (g_rec) { rb_add(X(q->x0 - 40), Y(q->y0 - 40), X(q->x1 + 40), Y(q->y1 + 40), 2); g_cany = 0; }   /* + half a light */
        glow_light(q->x0, q->y0, q->x1, q->y1, q->bw);
    }
}
static void rank_frame(float x0, float y0, float x1, float y1, int tier, int reinc)
{
    float w = x1 - x0, h = y1 - y0;
    if (reinc > 0)
        for (int k = 3; k >= 1; k--) stroke_rect(x0 - k * 2.0f, y0 - k * 2.0f, w + k * 4.0f, h + k * 4.0f, (ARGB)((0x18 * (4 - k)) << 24) | 0x00B070E0u, 2.0f);
    if (tier <= 0) {
        stroke_rect(x0 + 0.5f, y0 + 0.5f, w - 1, h - 1, 0xC0C9A45Cu, 1.3f);
        diamond((x0 + x1) / 2, y0 + 1, 5, C_BRASS);
        return;
    }
    if (tier == 1) {
        stroke_rect(x0 + 0.5f, y0 + 0.5f, w - 1, h - 1, 0xE0C9A45Cu, 1.5f);
        stroke_rect(x0 + 4.5f, y0 + 4.5f, w - 9, h - 9, 0x70C9A45Cu, 1.0f);
        float L = 16;
        float cx[4] = { x0 + 2, x1 - 2, x0 + 2, x1 - 2 }, cy[4] = { y0 + 2, y0 + 2, y1 - 2, y1 - 2 };
        for (int i = 0; i < 4; i++) {
            float sx = i & 1 ? -1.0f : 1.0f, sy = i & 2 ? -1.0f : 1.0f;
            line(cx[i], cy[i], cx[i] + sx * L, cy[i], C_BRASS_HI, 2.4f); line(cx[i], cy[i], cx[i], cy[i] + sy * L, C_BRASS_HI, 2.4f);
        }
        diamond((x0 + x1) / 2, y0 + 1, 6, C_BRASS_HI);
        return;
    }
    /* tiers 2..4: a metal band between two lines */
    float bw = tier == 2 ? 5 : tier == 3 ? 7 : 9;
    ARGB m1 = tier == 2 ? 0xFF8A5A2Bu : 0xFFFFE08Au, m2 = tier == 2 ? 0xFF5A3816u : tier == 3 ? 0xFFB07A10u : 0xFFC08A10u;
    ARGB edge = tier == 2 ? 0xFFC9A45Cu : 0xFFFFF0B0u;
    band_grad(x0, y0, w, bw, m1, m2, 0); band_grad(x0, y1 - bw, w, bw, m2, m1, 0);
    band_grad(x0, y0 + bw, bw, h - 2 * bw, m1, m2, 1); band_grad(x1 - bw, y0 + bw, bw, h - 2 * bw, m2, m1, 1);
    stroke_rect(x0 + 0.5f, y0 + 0.5f, w - 1, h - 1, edge, 1.0f);
    stroke_rect(x0 + bw + 0.5f, y0 + bw + 0.5f, w - 2 * bw - 1, h - 2 * bw - 1, 0xA0000000u, 1.2f);
    stroke_rect(x0 + bw + 2.5f, y0 + bw + 2.5f, w - 2 * bw - 5, h - 2 * bw - 5, (edge & 0x00FFFFFFu) | 0x50000000u, 1.0f);
    if (tier >= 3) {                                   /* rivets along the band */
        for (float x = x0 + 60; x < x1 - 50; x += 60) { fill_circle(x, y0 + bw / 2, bw * 0.28f, 0xFFFFF6D0u); fill_circle(x, y1 - bw / 2, bw * 0.28f, 0xFFFFF6D0u); }
        for (float y = y0 + 60; y < y1 - 50; y += 60) { fill_circle(x0 + bw / 2, y, bw * 0.28f, 0xFFFFF6D0u); fill_circle(x1 - bw / 2, y, bw * 0.28f, 0xFFFFF6D0u); }
    }
    if (tier == 4 && g_glow_defer) {                   /* (11-01 layers) the running light: its own part (P_GLOW), so
                                                          the page itself does not change every frame */
        if (!g_hit_off && g_nglow < 4) { GlowReq *q = &g_glow[g_nglow++]; q->x0 = x0; q->y0 = y0; q->x1 = x1; q->y1 = y1; q->bw = bw; }
    } else if (tier == 4) glow_light(x0, y0, x1, y1, bw);
    if (tier == 4) {
        for (int k = 1; k <= 3; k++) stroke_rect(x0 - k * 1.5f, y0 - k * 1.5f, w + k * 3.0f, h + k * 3.0f, (ARGB)((0x22 * (4 - k)) << 24) | 0x00FFD54Fu, 1.5f);
    }
    /* corners */
    float cs = tier == 2 ? 9 : tier == 3 ? 13 : 16;
    float cxs[4] = { x0, x1, x0, x1 }, cys[4] = { y0, y0, y1, y1 };
    for (int i = 0; i < 4; i++) {
        float cx = cxs[i] + (i & 1 ? -bw / 2 : bw / 2), cy = cys[i] + (i & 2 ? -bw / 2 : bw / 2);
        if (tier == 2) { fill_rect(cx - cs / 2, cy - cs / 2, cs, cs, 0xFF6E4520u); stroke_rect(cx - cs / 2, cy - cs / 2, cs, cs, edge, 1.2f); diamond(cx, cy, cs * 0.35f, 0xFFFFE08Au); }
        else if (tier == 3) {
            fill_circle(cx, cy, cs * 0.75f, 0xFF7A5200u); stroke_circle(cx, cy, cs * 0.75f, 0xFFFFE08Au, 1.4f);
            float sx = i & 1 ? -1.0f : 1.0f, sy = i & 2 ? -1.0f : 1.0f;
            arc(cx + sx * cs * 1.2f, cy + sy * cs * 0.2f, cs * 0.6f, 0, 360, 0x90FFE08Au, 1.2f);
            arc(cx + sx * cs * 0.2f, cy + sy * cs * 1.2f, cs * 0.6f, 0, 360, 0x90FFE08Au, 1.2f);
            diamond(cx, cy, cs * 0.4f, 0xFFFFF6D0u);
        } else {
            fill_circle(cx, cy, cs * 0.85f, 0xFF5A3A00u); stroke_circle(cx, cy, cs * 0.85f, 0xFFFFF0B0u, 1.6f);
            star5(cx, cy, cs * 0.7f, 0xFFFFE066u);
        }
    }
    /* crest, top centre */
    float mx = (x0 + x1) / 2, my = y0 + bw / 2;
    if (y0 < 24) my = y0 + bw + 14;                    /* a window at the very top (F4): the crest hangs inside */
    if (tier == 2) {
        line(mx - 14, my - 4, mx, my + 8, 0xFFFFE08Au, 3.2f); line(mx, my + 8, mx + 14, my - 4, 0xFFFFE08Au, 3.2f);
        diamond(mx, my - 6, 5, 0xFFFFE08Au);
    } else if (tier == 3) {
        for (int sd = -1; sd <= 1; sd += 2)
            for (int i = 0; i < 5; i++) {
                float a = 0.35f + i * 0.33f, px = mx + sd * (14 + i * 7), py = my + 6 - sinf(a) * 9;
                GpPointF lf[4] = { { X(px - sd * 5), Y(py + 2) }, { X(px), Y(py - 3) }, { X(px + sd * 5), Y(py - 2) }, { X(px), Y(py + 3) } };
                pGdipFillPolygon(C.g, brush(i & 1 ? 0xFFD9A520u : 0xFFFFD54Fu), lf, 4, GP_FILL_ALT);
            }
        fill_circle(mx, my, 11, 0xFF5A3A00u); stroke_circle(mx, my, 11, 0xFFFFF0B0u, 1.4f);
        star5(mx, my, 8, 0xFFFFE066u);
    } else {
        for (int sd = -1; sd <= 1; sd += 2)            /* wings */
            for (int i = 0; i < 4; i++) {
                float px = mx + sd * (16 + i * 9), py = my - 2 + i * 1.5f, L = 26 - i * 4.0f;
                GpPointF wg[4] = { { X(px), Y(py - 4) }, { X(px + sd * L), Y(py - 9 + i * 2.5f) }, { X(px + sd * (L - 4)), Y(py + 1) }, { X(px), Y(py + 5) } };
                pGdipFillPolygon(C.g, brush(i & 1 ? 0xFFE0B040u : 0xFFFFE08Au), wg, 4, GP_FILL_ALT);
                pGdipDrawPolygon(C.g, pen(0xFF7A5200u, S(0.8f)), wg, 4);
            }
        fill_circle(mx, my, 14, 0xFF4A2E00u); stroke_circle(mx, my, 14, 0xFFFFF0B0u, 1.8f);
        stroke_circle(mx, my, 11, 0x90FFE066u, 1.0f);
        star5(mx, my, 10, 0xFFFFE066u);
        for (int k = -1; k <= 1; k += 2) star5(mx + k * 22, my + 14, 4, 0xFFFFE066u);
        star5(mx, my + 18, 4, 0xFFFFE066u);
    }
}
/* (18:04 "pictures, not only text") a rank insignia drawn for the 21 ranks: chevrons for the soldiers / NCOs,
   bars for the officers, diamonds for the field officers, stars for the generals - in the tier's metal */
static void insignia(float cx, float cy, float s, int rank)
{
    ARGB c = rank <= 5 ? 0xFFC9A45Cu : rank <= 10 ? 0xFFD0D6DCu : 0xFFFFD54Fu, d = 0xFF1A1E22u;
    fill_circle(cx, cy, s * 0.62f, 0xC0101418u);
    stroke_circle(cx, cy, s * 0.62f, (c & 0x00FFFFFFu) | 0x90000000u, 1.2f);
    if (rank <= 5) {                                     /* 1..3 chevrons (+ a rocker for the staff ranks) */
        int n = rank <= 2 ? rank + 1 : rank - 2;
        for (int i = 0; i < n; i++) {
            float y = cy - s * 0.18f + i * s * 0.2f - (n - 1) * s * 0.1f;
            line(cx - s * 0.32f, y, cx, y - s * 0.16f, c, s * 0.09f); line(cx, y - s * 0.16f, cx + s * 0.32f, y, c, s * 0.09f);
        }
        if (rank >= 3) arc(cx, cy + s * 0.05f, s * 0.36f, 30, 120, c, s * 0.07f);
    } else if (rank <= 10) {                             /* 1..5 bars */
        int n = rank - 5;
        float bw = s * 0.12f, gap = s * 0.05f, tot = n * bw + (n - 1) * gap, x = cx - tot / 2;
        for (int i = 0; i < n; i++, x += bw + gap) { fill_rect(x, cy - s * 0.3f, bw, s * 0.6f, c); stroke_rect(x, cy - s * 0.3f, bw, s * 0.6f, d, 0.6f); }
    } else if (rank <= 16) {                             /* 1..6 diamonds */
        int n = rank - 10, rows = n > 3 ? 2 : 1, per = (n + rows - 1) / rows;
        for (int i = 0; i < n; i++) {
            int r = i / per, k = i % per, inrow = r == rows - 1 ? n - r * per : per;
            diamond(cx + (k - (inrow - 1) / 2.0f) * s * 0.24f, cy + (rows == 2 ? (r ? s * 0.13f : -s * 0.13f) : 0), s * 0.11f, c);
        }
    } else {                                             /* 1..4 stars */
        int n = rank - 16;
        for (int i = 0; i < n; i++) {
            float a = n == 1 ? 0 : -0.6f + i * 1.2f / (n - 1);
            star5(cx + sinf(a) * s * 0.28f * (n > 1), cy - cosf(a) * s * 0.06f * (n > 1), n == 1 ? s * 0.3f : s * 0.17f, c);
        }
    }
}
static void ui_box(float x, float y, float w, float h, const WCHAR *title)
{
    fill_rect(x, y, w, h, 0x50000000u);
    stroke_rect(x + 0.5f, y + 0.5f, w - 1, h - 1, 0x80C9A45Cu, 1.1f);
    if (title) {
        fill_rect(x + 1, y + 1, w - 2, 20, 0x30C9A45Cu);
        text(title, x + 8, y + 1, w - 16, 20, 12, 0, 1, C_BRASS_HI, GP_ALIGN_NEAR, GP_ALIGN_CENTER);
    }
}
static void ui_kv(float x, float y, float w, float h, const WCHAR *k, const WCHAR *v, ARGB vc)
{
    text(k, x, y, w * 0.5f, h, 11, 0, 0, C_MUTED, GP_ALIGN_NEAR, GP_ALIGN_CENTER);
    text(v, x + w * 0.38f, y, w * 0.62f, h, 12, 1, 1, vc, GP_ALIGN_FAR, GP_ALIGN_CENTER);
}
/* other = 1 (11-01 14:17): another commander's window (CUserInfoWnd "@ f4-bk-nm", 404 x 410): its public page
   (user.txt: I, B, N, M) - branches left, the commander middle, nation and medals below, 效力 / 关闭 over the game's */
static void paint_userinfo(float bx, float by, int other)
{
    static char work[sizeof g_cmd_buf];
    work[0] = 0;
    if (other) { if (g_hon_csok) { EnterCriticalSection(&g_hon_cs); memcpy(work, g_oth_buf, sizeof g_oth_buf); LeaveCriticalSection(&g_hon_cs); } }
    else if (g_hon_csok && g_cmd_state == 2) { EnterCriticalSection(&g_hon_cs); memcpy(work, g_cmd_buf, sizeof work); LeaveCriticalSection(&g_hon_cs); }
    char *I[16] = { 0 }, *B[4][9], *A[6] = { 0 }, *R[6] = { 0 }, *U[9] = { 0 }, *N[3] = { 0 }, *Lr[5] = { 0 }, *M[40][3];
    int ni = 0, nb = 0, na = 0, nr = 0, nu = 0, nn = 0, nl = 0, nm = 0;
    for (char *l = work; *l; ) {
        char *e = strchr(l, '\n'); if (e) *e = 0;
        char *f[16]; int k = hon_split(l, f, 16);
        #define TAKE(arr, cnt, max) { for (int j = 0; j < max; j++) arr[j] = j < k ? f[j] : (char *)""; cnt = 1; }
        if (f[0][0] == 'I' && k >= 12) TAKE(I, ni, 16)
        else if (f[0][0] == 'B' && k >= 6 && nb < 4) { for (int j = 0; j < 9; j++) B[nb][j] = j < k ? f[j] : (char *)""; nb++; }
        else if (f[0][0] == 'A' && k >= 6) TAKE(A, na, 6)
        else if (f[0][0] == 'R' && k >= 6) TAKE(R, nr, 6)
        else if (f[0][0] == 'U' && k >= 8) TAKE(U, nu, 9)
        else if (f[0][0] == 'N' && k >= 2) TAKE(N, nn, 3)
        else if (f[0][0] == 'L' && k >= 4) TAKE(Lr, nl, 5)
        else if (f[0][0] == 'M' && k >= 3 && nm < 40) { for (int j = 0; j < 3; j++) M[nm][j] = f[j]; nm++; }
        #undef TAKE
        if (!e) break;
        l = e + 1;
    }
    #define WX(v) fx_ref(bx + (v))
    #define WY(v) fy_ref(by + (v))
    float x0 = WX(0), y0 = WY(0), x1 = WX(other ? 404 : 584), y1 = WY(other ? 410 : 411), w = x1 - x0;
    WCHAR v[160], ws[96];
    /* the panel (the portrait hole stays open) */
    {   float px0 = WX(201), py0 = WY(other ? 66 : 64), px1 = WX(other ? 268 : 279), py1 = WY(other ? 127 : 131);
        float H[1][4] = { { px0, py0, px1, py1 } };
        (void)H;   /* (11-01 F4 delay) four rectangles around the hole: the anti-aliased polygon cost ~5x more */
        pGdipSetSmoothingMode(C.g, 3);                       /* none: the edges are whole pixels anyway */
        fill_rect(x0, y0, x1 - x0, py0 - y0, 0xF60A1016u); fill_rect(x0, py1, x1 - x0, y1 - py1, 0xF60A1016u);
        fill_rect(x0, py0, px0 - x0, py1 - py0, 0xF60A1016u); fill_rect(px1, py0, x1 - px1, py1 - py0, 0xF60A1016u);
        pGdipSetSmoothingMode(C.g, GP_SMOOTH_AA);
        hd_portrait(ni ? atoi(I[11]) : g_ps.my_look, px0, py0, px1, py1);
        stroke_rect(px0 - 1, py0 - 1, px1 - px0 + 2, py1 - py0 + 2, 0xE0C9A45Cu, 1.6f); }
    {   int tr = ni && I[15] ? rank_tier(atoi(I[15])) : rank_tier(ni ? 0 : 0), rc = ni ? atoi(I[6]) : 0;
        rank_frame(x0, y0, x1, y1, tr, rc); if (tr == 4) g_frame_live = 1; }
    text(T3("COMMANDER", "指挥官信息", "指揮官資訊"), x0 + 14, y0 + 6, w * 0.5f, WY(36) - y0 - 6, 18, 0, 1, C_BRASS_HI, GP_ALIGN_NEAR, GP_ALIGN_CENTER);
    if (!ni) {
        text(T3("Loading...", "读取中…", "讀取中…"), x0, WY(180), w, 30, 14, 0, 0, C_MUTED, GP_ALIGN_CENTER, GP_ALIGN_CENTER);
        return;
    }
    if (atoi(I[12]) || atoi(I[13])) {
        const WCHAR *off = atoi(I[12]) ? T3("President", "总统", "總統") : T3("Council", "议员", "議員");
        text(off, x1 - 160, y0 + 6, 146, WY(36) - y0 - 6, 13, 0, 1, 0xFFFFE066u, GP_ALIGN_FAR, GP_ALIGN_CENTER);
    }
    /* ---- branches (left) */
    float lx = WX(10), lw = WX(192) - lx;
    ui_box(lx, WY(40), lw, WY(330) - WY(40), T3("Branches", "兵科", "兵科"));
    static const ARGB BC[4] = { 0xFFE9C46Au, 0xFF8BC4E2u, 0xFF9FD8F0u, 0xFF8BE28Bu };
    for (int i = 0; i < nb; i++) {
        int b = !strcmp(B[i][1], "inf") ? 0 : !strcmp(B[i][1], "mob") ? 1 : !strcmp(B[i][1], "avi") ? 2 : 3;
        float ry = WY(64 + b * 66), rh = WY(64 + b * 66 + 62) - ry;
        int lv = atoi(B[i][2]), xp = atoi(B[i][3]), nd = atoi(B[i][4]), nlv = atoi(B[i][6]);
        if (b & 1) fill_rect(lx + 2, ry, lw - 4, rh, 0x10FFFFFFu);
        /* (user 11-01 02:41) the game's branch picture (INF/MOB/AVI/ORG) left; beside it name + Lv, then the rank's name
           (moved left) with the game's insignia (ui-insg) right of it, then the bar */
        float px1 = lx + 6, ph = rh - 8, pw = ph * 34 / 42;
        if (branch_img(b, px1, ry + 4, pw, ph)) stroke_rect(px1 - 0.5f, ry + 3.5f, pw + 1, ph + 1, 0x90C9A45Cu, 1);
        else icon(IC_INF + b, px1 + pw / 2, ry + 14, 20, BC[b], 1.6f);
        float cx2 = px1 + pw + 6, cw2 = lx + lw - 6 - cx2;
        text(branch_name(b), cx2, ry + 1, cw2 * 0.6f, 18, 13, 0, 1, BC[b], GP_ALIGN_NEAR, GP_ALIGN_CENTER);
        swprintf(v, 160, L"Lv %d", lv);
        text(v, cx2 + cw2 * 0.5f, ry + 1, cw2 * 0.5f, 18, 12, 1, 1, C_TEXT, GP_ALIGN_FAR, GP_ALIGN_CENTER);
        float iw3 = 0;
        if (B[i][8][0] && insg_img(b, atoi(B[i][8]), cx2 + cw2 - 78, ry + 18, 78, 24, 1)) iw3 = 78;
        else if (B[i][8][0]) { insignia(cx2 + cw2 - 12, ry + 30, 22, atoi(B[i][8])); iw3 = 26; }
        MultiByteToWideChar(CP_ACP, 0, B[i][5], -1, ws, 96);
        text(ws, cx2, ry + 19, cw2 - iw3, 21, 12, 0, 1, C_TEXT, GP_ALIGN_NEAR, GP_ALIGN_CENTER);
        bar(cx2, ry + 42, cw2, 5, nd > 0 ? (float)xp / nd : 1, BC[b]);
        swprintf(v, 160, L"%d / %d", xp, nd);
        text(v, cx2 + cw2 * 0.45f, ry + 48, cw2 * 0.55f, 13, 9, 1, 0, C_MUTED, GP_ALIGN_FAR, GP_ALIGN_CENTER);
        if (nlv > lv) {
            WCHAR nr2[32]; MultiByteToWideChar(CP_ACP, 0, B[i][7], -1, nr2, 32);
            if (g_lang == 1) swprintf(v, 160, L"距「%ls」还差 %d 级", nr2, nlv - lv);
            else if (g_lang == 2) swprintf(v, 160, L"距「%ls」還差 %d 級", nr2, nlv - lv);
            else swprintf(v, 160, L"%d lv to %ls", nlv - lv, nr2);
            text(v, cx2, ry + 48, cw2 * 0.6f, 13, 9, 0, 0, C_MUTED, GP_ALIGN_NEAR, GP_ALIGN_CENTER);
        }
    }
    /* ---- commander (middle) */
    float mx = WX(198), mw = WX(394) - mx;
    ui_box(mx, WY(40), mw, WY(232) - WY(40), NULL);
    {   float tx = WX(286), tw = WX(392) - tx;
        MultiByteToWideChar(CP_ACP, 0, I[1], -1, ws, 96);
        text(ws, tx, WY(62), tw, 22, 15, 0, 1, C_TEXT, GP_ALIGN_NEAR, GP_ALIGN_CENTER);
        MultiByteToWideChar(CP_ACP, 0, I[2], -1, ws, 96);
        /* (user 11-01 02:38) under the name: the game's insignia (the branch that holds the top rank) with room, the
           rank's name larger and right-aligned */
        {   int tr = I[15] && I[15][0] ? atoi(I[15]) : -1, tb = 0, tl = -1;
            for (int i = 0; i < nb; i++) {
                int b = !strcmp(B[i][1], "inf") ? 0 : !strcmp(B[i][1], "mob") ? 1 : !strcmp(B[i][1], "avi") ? 2 : 3;
                if (B[i][8][0] && atoi(B[i][8]) == tr && atoi(B[i][2]) > tl) { tl = atoi(B[i][2]); tb = b; }
            }
            float ry2 = WY(80), rh2 = WY(108) - ry2, nw = 58, iw4 = tw - nw - 2;   /* the name keeps 58 for 3-4 characters */
            if (iw4 > rh2 * 140 / 44) iw4 = rh2 * 140 / 44;
            if (tr >= 0 && !insg_img(tb, tr, tx - 4, ry2, iw4, rh2, 0)) insignia(tx + 9, ry2 + rh2 / 2, 20, tr);
            text(ws, tx + tw - nw - 4, ry2, nw, rh2, 15, 0, 1, C_BRASS_HI, GP_ALIGN_FAR, GP_ALIGN_CENTER); }
        MultiByteToWideChar(CP_ACP, 0, I[3], -1, ws, 96);
        text(ws, tx, WY(109), tw, 17, 12, 0, 0, C_TEXT, GP_ALIGN_NEAR, GP_ALIGN_CENTER);
        int reinc = atoi(I[6]);
        if (reinc) { swprintf(v, 160, g_lang ? L"转生 %d" : L"Reborn %d", reinc); text(v, tx, WY(125), tw, 15, 11, 0, 1, 0xFFE8A0C8u, GP_ALIGN_NEAR, GP_ALIGN_CENTER); } }
    {   float ky = WY(140), kh = 17.5f * (WY(232) - WY(140)) / 92 * 0 + (WY(232) - WY(140) - 6) / 5, kx = mx + 10, kw = mw - 20;
        MultiByteToWideChar(CP_ACP, 0, I[4], -1, ws, 96);
        ui_kv(kx, ky, kw, kh, T3("Regiment", "军团", "軍團"), ws[0] ? ws : L"-", C_TEXT); ky += kh;
        MultiByteToWideChar(CP_ACP, 0, I[5], -1, ws, 96);
        ui_kv(kx, ky, kw, kh, T3("Superior", "上级", "上級"), ws[0] ? ws : L"-", C_TEXT); ky += kh;
        long hon = atol(I[7]);
        swprintf(v, 160, L"%ld.%02ld", hon / 100, (hon < 0 ? -hon : hon) % 100);
        ui_kv(kx, ky, kw, kh, T3("Honor", "荣誉", "榮譽"), v, C_BRASS_HI); ky += kh;
        swprintf(v, 160, L"%d", atoi(I[8]));
        ui_kv(kx, ky, kw, kh, T3("Prestige", "声望", "聲望"), v, C_TEXT); ky += kh;
        int wi = atoi(I[9]), lo = atoi(I[10]);
        swprintf(v, 160, L"%d / %d  (%d%%)", wi, lo, wi + lo ? wi * 100 / (wi + lo) : 0);
        ui_kv(kx, ky, kw, kh, T3("Won / lost", "战绩 胜/负", "戰績 勝/負"), v, C_TEXT); }
    /* ---- army (middle, lower); another commander: the nation */
    ui_box(mx, WY(238), mw, WY(330) - WY(238), other ? T3("Nation", "国家", "國家") : T3("Army", "部队", "部隊"));
    if (other && nn) {
        float ky = WY(238) + 22, kh = (WY(330) - WY(238) - 26) / 4, kx = mx + 10, kw = mw - 20;
        MultiByteToWideChar(CP_ACP, 0, I[3], -1, ws, 96);
        ui_kv(kx, ky, kw, kh, T3("Nation", "国家", "國家"), ws[0] ? ws : L"-", C_TEXT); ky += kh;
        if (I[14] && I[14][0]) { MultiByteToWideChar(CP_ACP, 0, I[14], -1, ws, 96); ui_kv(kx, ky, kw, kh, T3("Planet", "星球", "星球"), ws, C_TEXT); ky += kh; }
        swprintf(v, 160, L"%d", atoi(N[2]));
        ui_kv(kx, ky, kw, kh, T3("Provinces", "本国省份", "本國省份"), v, C_TEXT); ky += kh;
        MultiByteToWideChar(CP_ACP, 0, N[1], -1, ws, 96);
        for (WCHAR *c = ws; *c; c++) if (*c == L',') *c = 0x3001;
        ui_kv(kx, ky, kw, kh, T3("Allies", "同盟", "同盟"), ws[0] ? ws : L"-", ws[0] ? 0xFF8BE28Bu : C_MUTED);
    }
    if (!other && nu) {
        float ky = WY(238) + 22, kh = (WY(330) - WY(238) - 26) / 4, kx = mx + 10, kw = mw - 20;
        swprintf(v, 160, L"%d  \x00b7  %d / %d", atoi(U[1]), atoi(U[3]), atoi(U[2]));
        ui_kv(kx, ky, kw, kh, T3("Deploy \x00b7 units", "出战 \x00b7 单位", "出戰 \x00b7 單位"), v, C_TEXT); ky += kh;
        MultiByteToWideChar(CP_ACP, 0, U[5], -1, ws, 96);
        if (ws[0]) swprintf(v, 160, L"\x2605%d %ls", atoi(U[4]), ws); else lstrcpynW(v, L"-", 160);
        ui_kv(kx, ky, kw, kh, T3("Best unit", "最佳单位", "最佳單位"), v, 0xFFFFE066u); ky += kh;
        swprintf(v, 160, L"%d", atoi(U[6]));
        ui_kv(kx, ky, kw, kh, T3("Lifetime kills", "累计击杀", "累計擊殺"), v, C_TEXT); ky += kh;
        swprintf(v, 160, L"%d  (%ls %d)", atoi(U[7]), g_lang ? L"胜" : L"won", atoi(U[8]));
        ui_kv(kx, ky, kw, kh, T3("Unit battles", "单位参战", "單位參戰"), v, C_TEXT);
    }
    /* ---- attributes (right): rows on the game's spin buttons (window y 86 + 22 i, x 513) */
    float ax = WX(400), aw = WX(574) - ax;
    if (!other) {
    ui_box(ax, WY(40), aw, WY(180) - WY(40), T3("Attributes", "属性", "屬性"));
    {   int dsum = 0; for (int i = 0; i < 4; i++) dsum += g_ps.ui_d[i];
        int pts = (na ? atoi(A[5]) : 0) - dsum;
        swprintf(v, 160, g_lang ? L"可分配点数  %d" : L"Points  %d", pts);
        text(v, ax + 8, WY(64), aw - 16, WY(84) - WY(64), 12, 0, 1, pts > 0 ? 0xFF8BE28Bu : C_MUTED, GP_ALIGN_NEAR, GP_ALIGN_CENTER);
        static const WCHAR *AN[3][4] = { { L"Tactics", L"Clout", L"Education", L"Mech apt" }, { L"战术", L"影响力", L"教育", L"机械" },
                                         { L"戰術", L"影響力", L"教育", L"機械" } };
        static const WCHAR *AD[3][4] = {
            { L"Units per battle = tactics / 20 + 6", L"Unit quality and branch influence + clout / 2", L"Tech level of a unit + education / 2", L"Carry weight x (1 + mech / 120)" },
            { L"每场可出战单位 = 战术 / 20 + 6", L"单位品质与兵科影响力 + 影响力 / 2（工厂买更高级单位）", L"单位科技等级 + 教育 / 2（可装备更高级装备）", L"单位载重 x (1 + 机械 / 120)" },
            { L"每場可出戰單位 = 戰術 / 20 + 6", L"單位品質與兵科影響力 + 影響力 / 2（工廠買更高級單位）", L"單位科技等級 + 教育 / 2（可裝備更高級裝備）", L"單位載重 x (1 + 機械 / 120)" } };
        for (int i = 0; i < 4; i++) {
            float ry = WY(86 + 22 * i), rh = WY(108 + 22 * i) - ry;
            if (i & 1) fill_rect(ax + 2, ry, aw - 4, rh, 0x10FFFFFFu);
            text(AN[g_lang][i], ax + 10, ry, WX(470) - ax - 10, rh, 12, 0, 0, C_TEXT, GP_ALIGN_NEAR, GP_ALIGN_CENTER);
            swprintf(ws, 96, L"%d", (na ? atoi(A[1 + i]) : 0) + g_ps.ui_d[i]);
            text(ws, WX(470), ry, WX(509) - WX(470), rh, 13, 1, 1, g_ps.ui_d[i] ? 0xFF8BE28Bu : C_BRASS_HI, GP_ALIGN_FAR, GP_ALIGN_CENTER);
            text_hit(100 + i, ax + 4, ry, WX(509) - ax - 4, rh, AN[g_lang][i], AD[g_lang][i]);
            /* the game's spin (14 x 22) - drawn here, the click passes to it */
            float sx = WX(513), sw = WX(527) - sx, sh = rh / 2;
            for (int d = 0; d < 2; d++) {
                float sy = ry + d * sh, cx = sx + sw / 2, cy = sy + sh / 2;
                fill_rect(sx, sy + 0.5f, sw, sh - 1, pts > 0 && !d ? 0x5050C878u : 0x30FFFFFFu);
                ARGB c = pts > 0 && !d ? 0xFF8BE28Bu : C_MUTED;
                if (!d) { line(cx - 3, cy + 1.5f, cx, cy - 1.5f, c, 1.5f); line(cx, cy - 1.5f, cx + 3, cy + 1.5f, c, 1.5f); }
                else { line(cx - 3, cy - 1.5f, cx, cy + 1.5f, c, 1.5f); line(cx, cy + 1.5f, cx + 3, cy - 1.5f, c, 1.5f); }
                hit_add(sx, sy, sw, sh, 0, H_PASS, 0);
            }
        }
    }
    /* ---- resources (right, lower) */
    ui_box(ax, WY(186), aw, WY(286) - WY(186), T3("Resources", "资源", "資源"));
    if (nr) {
        static const WCHAR *RN[3][5] = { { L"Money", L"Ore", L"Silicon", L"Uranium", L"Sulfur" }, { L"金钱", L"矿", L"硅", L"铀", L"硫" }, { L"金錢", L"礦", L"矽", L"鈾", L"硫" } };
        static const ARGB RC[5] = { 0xFF9FE8E8u, 0xFFB8C4E0u, 0xFFFF8A65u, 0xFF9FD8F0u, 0xFFFFE066u };
        float ry = WY(186) + 22, rh = (WY(286) - WY(186) - 26) / 5;
        for (int i = 0; i < 5; i++, ry += rh) {
            fill_circle(ax + 14, ry + rh / 2, 4, RC[i]);
            swprintf(v, 160, L"%ld", atol(R[1 + i]));
            ui_kv(ax + 24, ry, aw - 32, rh, RN[g_lang][i], v, C_TEXT);
        }
    }
    /* ---- nation */
    ui_box(ax, WY(292), aw, WY(368) - WY(292), T3("Nation", "国家", "國家"));
    if (nn) {
        float ry = WY(292) + 22, rh = (WY(368) - WY(292) - 26) / 2;
        swprintf(v, 160, L"%d", atoi(N[2]));
        ui_kv(ax + 10, ry, aw - 20, rh, T3("Provinces", "本国省份", "本國省份"), v, C_TEXT); ry += rh;
        MultiByteToWideChar(CP_ACP, 0, N[1], -1, ws, 96);
        for (WCHAR *c = ws; *c; c++) if (*c == L',') *c = 0x3001;
        ui_kv(ax + 10, ry, aw - 20, rh, T3("Allies", "同盟", "同盟"), ws[0] ? ws : L"-", ws[0] ? 0xFF8BE28Bu : C_MUTED);
    }
    }   /* (!other) */
    if (other) {   /* ---- another commander: the medals across the lower box, 效力 / 关闭 over the game's buttons */
        float bx0 = lx, bw0 = WX(394) - lx, ry = WY(336), rh = WY(370) - ry;
        ui_box(bx0, ry, bw0, rh, NULL);
        text(T3("Medals", "勋章", "勳章"), bx0 + 8, ry, 40, rh, 11, 0, 1, C_BRASS, GP_ALIGN_NEAR, GP_ALIGN_CENTER);
        float m0 = bx0 + 50, mrw = 40, mrh = mrw * 16 / 44, mgap = 3;
        int per = (int)((bx0 + bw0 - 6 - m0) / (mrw + mgap)); if (per < 1) per = 1;
        int two = nm > per;
        for (int i = 0; i < nm && i < per * 2; i++) {
            unsigned id = (unsigned)atol(M[i][1]);
            float rx = m0 + (i % per) * (mrw + mgap), ryy = two ? ry + rh / 2 - mrh - 1 + (i / per) * (mrh + 2) : ry + (rh - mrh) / 2;
            if (!medal_img(id, rx, ryy, mrw, mrh)) { fill_rect(rx, ryy, mrw, mrh, 0xFF404040u); fill_rect(rx + mrw / 2 - 3, ryy, 6, mrh, 0xFFE9C46Au); }
            stroke_rect(rx - 0.5f, ryy - 0.5f, mrw + 1, mrh + 1, 0x80000000u, 1);
            MultiByteToWideChar(CP_ACP, 0, M[i][2], -1, ws, 96);
            const WCHAR *mt = T3("Commander medal", "指挥官勋章", "指揮官勳章"), *mb = ws;
            WCHAR mname[48]; WCHAR *sep = wcschr(ws, 0xFF1A); int sl = 1;
            if (!sep) { sep = wcsstr(ws, L": "); sl = 2; }
            if (sep && sep > ws && sep - ws < 47) { lstrcpynW(mname, ws, (int)(sep - ws) + 1); mt = mname; mb = sep + sl; }
            text_hit(200 + i, rx, ryy, mrw, mrh, mt, mb);
        }
        if (!nm) text(L"-", m0, ry, 30, rh, 11, 0, 0, C_MUTED, GP_ALIGN_NEAR, GP_ALIGN_CENTER);
        for (int k = 0; k < 2; k++) {                  /* the game's 效力 (208..284) and 关闭 (301..369), y 377..404 */
            float b0 = WX(k ? 301 : 208), b1 = WX(k ? 369 : 284), c0 = WY(377), c1 = WY(404);
            fill_rect(b0, c0, b1 - b0, c1 - c0, k ? 0xD0201A10u : 0x900A1016u);
            stroke_rect(b0 + 0.5f, c0 + 0.5f, b1 - b0 - 1, c1 - c0 - 1, k ? C_BRASS_HI : 0xB0C9A45Cu, k ? 1.3f : 1.1f);
            text(k ? T3("CLOSE", "关闭", "關閉") : T3("Serve", "效力", "效力"), b0, c0, b1 - b0, c1 - c0, 13, 0, 1, k ? C_BRASS_HI : C_TEXT, GP_ALIGN_CENTER, GP_ALIGN_CENTER);
        }
    }
    /* ---- last battle + commander medals (bottom left / middle) */
    if (!other) {
    {   float bx0 = lx, bw0 = WX(394) - lx, ry = WY(336);
        ui_box(bx0, ry, bw0, WY(368) - ry, NULL);
        if (nl) {
            int r = atoi(Lr[1]), dh = atoi(Lr[3]), age = atoi(Lr[4]);
            MultiByteToWideChar(CP_ACP, 0, Lr[2], -1, ws, 96);
            const WCHAR *rt = r == 1 ? T3("Victory", "胜利", "勝利") : r == 2 ? T3("Retreat", "撤退", "撤退") : T3("Defeat", "战败", "戰敗");
            WCHAR ago[32];
            if (age < 3600) swprintf(ago, 32, g_lang ? L"%d 分钟前" : L"%d min ago", age / 60);
            else if (age < 86400) swprintf(ago, 32, g_lang ? L"%d 小时前" : L"%d h ago", age / 3600);
            else swprintf(ago, 32, g_lang ? L"%d 天前" : L"%d d ago", age / 86400);
            swprintf(v, 160, L"%ls  %ls \x00b7 %ls \x00b7 %ls %ls%d.%02d", T3("Last battle", "最近战斗", "最近戰鬥"), rt, ws, T3("honor", "荣誉", "榮譽"),
                     dh >= 0 ? L"+" : L"-", (dh < 0 ? -dh : dh) / 100, (dh < 0 ? -dh : dh) % 100);
            text(v, bx0 + 8, ry, bw0 * 0.78f, WY(368) - ry, 11, 0, 0, r == 1 ? 0xFFFFE066u : r == 2 ? C_MUTED : 0xFFE57373u, GP_ALIGN_NEAR, GP_ALIGN_CENTER);
            text(ago, bx0 + bw0 * 0.78f, ry, bw0 * 0.22f - 8, WY(368) - ry, 10, 0, 0, C_MUTED, GP_ALIGN_FAR, GP_ALIGN_CENTER);
        } else text(T3("No battle yet", "还没有战斗记录", "還沒有戰鬥紀錄"), bx0 + 8, ry, bw0 - 16, WY(368) - ry, 11, 0, 0, C_MUTED, GP_ALIGN_NEAR, GP_ALIGN_CENTER);
    }
    /* ---- bottom bar: commander medals (ribbons, hover = text), mercenary, close */
    {   float ry = WY(374), rh = WY(406) - ry, mx0 = lx + 4;
        text(T3("Medals", "勋章", "勳章"), mx0, ry, 40, rh, 11, 0, 1, C_BRASS, GP_ALIGN_NEAR, GP_ALIGN_CENTER);
        mx0 += 42;
        /* (user 11-01 02:39) the game's ribbons (dcr-NNN.xpf, 44 x 16), two rows when they don't fit one */
        float m0 = mx0, mrw = 40, mrh = mrw * 16 / 44, mgap = 3;
        int per = (int)((WX(326) - m0) / (mrw + mgap)); if (per < 1) per = 1;
        int two = nm > per;
        for (int i = 0; i < nm && i < per * 2; i++) {
            unsigned id = (unsigned)atol(M[i][1]), hsh = id * 2654435761u;
            float rx = m0 + (i % per) * (mrw + mgap), rw2 = mrw, rh2 = mrh;
            float ryy = two ? ry + rh / 2 - mrh - 1 + (i / per) * (mrh + 2) : ry + (rh - mrh) / 2;
            if (!medal_img(id, rx, ryy, rw2, rh2)) {
                ARGB c1 = 0xFF000000u | ((hsh >> 8) & 0x7F7F7Fu) | 0x303030u, c2 = 0xFFE9C46Au;
                fill_rect(rx, ryy, rw2, rh2, c1);
                fill_rect(rx + rw2 / 2 - 3, ryy, 6, rh2, c2);
            }
            stroke_rect(rx - 0.5f, ryy - 0.5f, rw2 + 1, rh2 + 1, 0x80000000u, 1);
            MultiByteToWideChar(CP_ACP, 0, M[i][2], -1, ws, 96);
            /* (user 11-01 13:36) "name：condition" from the server: the medal's own name as the tip's title */
            const WCHAR *mt = T3("Commander medal", "指挥官勋章", "指揮官勳章"), *mb = ws;
            WCHAR mname[48];
            WCHAR *sep = wcschr(ws, 0xFF1A); int sl = 1;
            if (!sep) { sep = wcsstr(ws, L": "); sl = 2; }
            if (sep && sep > ws && sep - ws < 47) {          /* (text_hit copies both) */
                lstrcpynW(mname, ws, (int)(sep - ws) + 1); mt = mname; mb = sep + sl;
            }
            text_hit(200 + i, rx, ryy, rw2, rh2, mt, mb);
        }
        if (!nm) text(L"-", mx0, ry, 30, rh, 11, 0, 0, C_MUTED, GP_ALIGN_NEAR, GP_ALIGN_CENTER);
        /* mercenary 开 (389..423) / 关 (426..460) and close (482..550): the game's buttons under, clicks pass */
        text(T3("Mercenary", "佣兵", "傭兵"), WX(330), ry, WX(386) - WX(330), rh, 12, 0, 1, C_TEXT, GP_ALIGN_FAR, GP_ALIGN_CENTER);
        for (int k = 0; k < 2; k++) {
            float bx1 = WX(k ? 426 : 389), bw1 = WX(k ? 460 : 423) - bx1, by1 = WY(382), bh1 = WY(399) - by1;
            int on = g_ps.ui_merc == (k ? 0 : 1);
            fill_rect(bx1, by1, bw1, bh1, on ? 0x6050C878u : 0x30FFFFFFu);
            stroke_rect(bx1 + 0.5f, by1 + 0.5f, bw1 - 1, bh1 - 1, on ? 0xFF8BE28Bu : 0x80C9A45Cu, on ? 1.4f : 1);
            text(k ? T3("Off", "关", "關") : T3("On", "开", "開"), bx1, by1, bw1, bh1, 11, 0, on, on ? 0xFF8BE28Bu : C_MUTED, GP_ALIGN_CENTER, GP_ALIGN_CENTER);
        }
        float cx1 = WX(482), cw1 = WX(550) - cx1, cy1 = WY(377), ch1 = WY(404) - cy1;
        fill_rect(cx1, cy1, cw1, ch1, 0xD0201A10u);
        stroke_rect(cx1 + 0.5f, cy1 + 0.5f, cw1 - 1, ch1 - 1, C_BRASS_HI, 1.3f);
        text(T3("CLOSE", "关闭", "關閉"), cx1, cy1, cw1, ch1, 13, 0, 1, C_BRASS_HI, GP_ALIGN_CENTER, GP_ALIGN_CENTER);
    }
    }   /* (!other) */
    #undef WX
    #undef WY
}
static void paint_report(float bx, float by)
{
    DWORD now = GetTickCount();
    /* a new result window: seen opening on the game thread (16:51 - not "not painted for 3 s": the HUD paints only on
       change, so a long look at the result followed by a hover reset it, the report was then too old and the game's own
       panels came back) */
    if (!g_rep_first) g_rep_first = now;
    g_rep_seen = now;
    static char work[sizeof g_rep_buf];
    work[0] = 0;
    if (g_hon_csok && g_rep_state == 2) { EnterCriticalSection(&g_hon_cs); memcpy(work, g_rep_buf, sizeof work); LeaveCriticalSection(&g_hon_cs); }
    char *R[8] = { 0 }, *U[24][17], *Cm[11] = { 0 }, *Br[4][9]; int nu = 0, nr = 0, nc = 0, nb = 0;
    for (char *l = work; *l; ) {
        char *e = strchr(l, '\n'); if (e) *e = 0;
        char *f[17]; int k = hon_split(l, f, 17);
        if (f[0][0] == 'R' && k >= 5) { for (int j = 0; j < 8; j++) R[j] = j < k ? f[j] : (char *)""; nr = k; }
        else if (f[0][0] == 'U' && k >= 12 && nu < 24) { for (int j = 0; j < 17; j++) U[nu][j] = j < k ? f[j] : (char *)""; nu++; }
        else if (f[0][0] == 'C' && k >= 5) { for (int j = 0; j < 11; j++) Cm[j] = j < k ? f[j] : (char *)""; nc = 1; }
        else if (f[0][0] == 'B' && k >= 6 && nb < 4) { for (int j = 0; j < 9; j++) Br[nb][j] = j < k ? f[j] : (char *)""; nb++; }
        if (!e) break;
        l = e + 1;
    }
    int fresh = nr && atoi(R[2]) <= 40 + (int)((now - g_rep_first) / 1000);
    if (!fresh || !nu) {                                   /* not here yet: ask again (at most 8 times, 1.5 s apart) */
        if (!g_rep_busy && g_rep_tries < 8 && (g_rep_state == 0 || now - g_rep_t > 1500)) rep_fetch_start();
        return;                                            /* the game's own list stays */
    }
    float x0 = fx_ref(bx + 439), y0 = fy_ref(by + 32), x1 = fx_ref(bx + 723), y1 = fy_ref(by + 370), w = x1 - x0, h = y1 - y0;
    fill_rect(x0, y0, w, h, 0xFA0A1016u);
    {   static char last[24]; static DWORD t0;          /* (17:44) a new report: the growth animates for 1.8 s */
        if (strcmp(last, R[1])) { lstrcpynA(last, R[1], sizeof last); t0 = now; }
        float q = (now - t0) / 1800.0f; if (q > 1) q = 1;
        g_rep_anim = 1 - (1 - q) * (1 - q) * (1 - q);
        if (q < 1) g_frame_live = 1;
        g_rep_tier = rank_tier(nc ? atoi(Cm[8]) : 0); g_rep_reinc = nc ? atoi(Cm[9]) : 0; }
    int res = atoi(R[3]);
    const WCHAR *rt = res == 1 ? T3("VICTORY", "胜利", "勝利") : res == 2 ? T3("RETREAT", "撤退", "撤退") : T3("DEFEAT", "战败", "戰敗");
    ARGB rc = res == 1 ? 0xFFFFD54Fu : res == 2 ? 0xFFB0BEC5u : 0xFFE57373u;
    {                                                    /* the banner: a band in the result's colour + the emblem */
        GpPointF bp[4] = { { X(x0 + 2), Y(y0 + 2) }, { X(x1 - 2), Y(y0 + 2) }, { X(x1 - 2), Y(y0 + 52) }, { X(x0 + 2), Y(y0 + 52) } };
        fill_grad(bp, 4, (rc & 0x00FFFFFFu) | 0x50000000u, (rc & 0x00FFFFFFu) | 0x08000000u, y0 + 2, y0 + 52, 0, 0, 0, 0, 0);
        line(x0 + 8, y0 + 52, x1 - 8, y0 + 52, (rc & 0x00FFFFFFu) | 0x90000000u, 1.2f);
        result_emblem(res, x0 + 31, y0 + 27, 21);
    }
    text(rt, x0 + 58, y0 + 4, w * 0.4f, 46, 26, 0, 1, rc, GP_ALIGN_NEAR, GP_ALIGN_CENTER);
    WCHAR v[160], pv[64]; MultiByteToWideChar(CP_ACP, 0, nr > 5 ? R[5] : "", -1, pv, 64);
    text(pv, x0 + w * 0.45f, y0 + 4, w * 0.55f - 12, 46, 12, 0, 0, C_MUTED, GP_ALIGN_FAR, GP_ALIGN_CENTER);
    /* MVP */
    int mvp = -1, sum_k = 0, alive = 0;
    for (int i = 0; i < nu; i++) { sum_k += atoi(U[i][6]); alive += U[i][7][0] == '1'; if (U[i][11][0] == '1' && mvp < 0) mvp = i; }
    float yy = y0 + 56;
    if (mvp >= 0) {
        WCHAR mn[48]; MultiByteToWideChar(CP_ACP, 0, U[mvp][2], -1, mn, 48);
        const Medal *m = medal_of("mvp");
        if (m) { draw_medal(m, x0 + 22, yy + 13, 8, 1); medal_hit(m, x0 + 12, yy - 6, 20, 30, -1); }
        swprintf(v, 160, L"%ls  %ls \x00b7 %d %ls", T3("Best of the battle", "本场最佳", "本場最佳"), mn, atoi(U[mvp][6]), T3("kills", "杀", "殺"));
        text(v, x0 + 38, yy, w - 50, 24, 13, 0, 1, 0xFFFFE066u, GP_ALIGN_NEAR, GP_ALIGN_CENTER);
        yy += 26;
    }
    swprintf(v, 160, L"%ls %d   %ls %d / %d   %ls %d", T3("Units", "参战单位", "參戰單位"), nu, T3("Alive", "存活", "存活"), alive, nu,
             T3("Kills", "总击杀", "總擊殺"), sum_k);
    text(v, x0 + 12, yy, w - 24, 20, 11, 0, 0, C_TEXT, GP_ALIGN_NEAR, GP_ALIGN_CENTER);
    yy += 22;
    /* header */
    float cN = x0 + 10, cK = x0 + w * 0.48f, cL = x0 + w * 0.58f, cX = x0 + w * 0.58f, cM = x0 + w * 0.74f;   /* (15:27) levels: left half */
    fill_rect(x0 + 6, yy, w - 12, 18, 0x28C9A45Cu);
    if (nu > 10) swprintf(v, 160, L"%ls \x00b7 %ls", T3("Unit", "单位", "單位"), g_lang == 0 ? L"top 10" : L"前 10 名");
    else lstrcpynW(v, T3("Unit", "单位", "單位"), 160);
    text(v, cN, yy, cK - cN, 18, 11, 0, 1, C_BRASS_HI, GP_ALIGN_NEAR, GP_ALIGN_CENTER);
    text(T3("Kills", "击杀", "擊殺"), cK, yy, cX - cK, 18, 11, 0, 1, C_BRASS_HI, GP_ALIGN_CENTER, GP_ALIGN_CENTER);
    text(T3("XP", "经验", "經驗"), cX, yy, cM - cX, 18, 11, 0, 1, C_BRASS_HI, GP_ALIGN_CENTER, GP_ALIGN_CENTER);
    text(T3("Medals", "勋章", "勳章"), cM, yy, x1 - 6 - cM, 18, 11, 0, 1, C_BRASS_HI, GP_ALIGN_CENTER, GP_ALIGN_CENTER);
    yy += 20;
    /* (16:51 user "only the top 10, there are too many units"): by kills, then XP; the summary above counts all */
    int ord[24], nshow = nu < 10 ? nu : 10;
    for (int i = 0; i < nu; i++) ord[i] = i;
    for (int i = 1; i < nu; i++) {
        int k = ord[i], j = i;
        while (j > 0) {
            int p = ord[j - 1], kk = atoi(U[k][6]) - atoi(U[p][6]);
            if (kk < 0 || (kk == 0 && atoi(U[k][10]) <= atoi(U[p][10]))) break;
            ord[j] = p; j--;
        }
        ord[j] = k;
    }
    float foot = 44, rh = (y1 - foot - yy) / (nshow > 0 ? nshow : 1);
    if (rh > 44) rh = 44; if (rh < 15) rh = 15;
    float big = rh >= 34 ? 1.25f : rh >= 24 ? 1.1f : 1.0f;
    for (int i = 0; i < nshow && yy + rh <= y1 - foot + 1; i++, yy += rh) {
        char **f = U[ord[i]];
        int al = f[7][0] == '1', st = atoi(f[4]), st0 = atoi(f[5]), lv0 = atoi(f[8]), lv = atoi(f[9]);
        if (i & 1) fill_rect(x0 + 6, yy, w - 12, rh, 0x12FFFFFFu);
        if (f[11][0] == '1') fill_rect(x0 + 6, yy, 3, rh, 0xFFFFE066u);
        /* alive / destroyed */
        float cx = cN + 5, cy = yy + rh / 2;
        if (al) fill_circle(cx, cy, 3.5f, 0xFF66BB6Au);
        else { line(cx - 3.5f, cy - 3.5f, cx + 3.5f, cy + 3.5f, 0xFFE57373u, 1.8f); line(cx + 3.5f, cy - 3.5f, cx - 3.5f, cy + 3.5f, 0xFFE57373u, 1.8f); }
        WCHAR nm[48], ch[48]; MultiByteToWideChar(CP_ACP, 0, f[2], -1, nm, 48); MultiByteToWideChar(CP_ACP, 0, f[3], -1, ch, 48);
        if (st > 0) swprintf(v, 160, L"\x2605%d %ls", st, nm); else lstrcpynW(v, nm, 160);
        text(v, cN + 14, yy, cK - cN - 16, rh, 12 * big, 0, 1, al ? C_TEXT : C_MUTED, GP_ALIGN_NEAR, GP_ALIGN_CENTER);
        swprintf(v, 160, L"%d", atoi(f[6]));
        text(v, cK, yy, cX - cK, rh, 13 * big, 1, 1, atoi(f[6]) ? C_TEXT : C_MUTED, GP_ALIGN_CENTER, GP_ALIGN_CENTER);
        (void)st0; (void)lv0; (void)lv; (void)cL;
        swprintf(v, 160, L"+%d", atoi(f[10]));
        text(v, cX, yy, cM - cX, rh, 12 * big, 1, 0, C_TEXT, GP_ALIGN_CENTER, GP_ALIGN_CENTER);
        /* medals of this battle */
        char mk[160]; lstrcpynA(mk, f[12], sizeof mk);
        float mx = cM + 2, adv;
        for (char *t = strtok(mk, ","); t; t = strtok(NULL, ",")) {
            char *c = strchr(t, ':'); if (c) *c = 0;
            if (mx + 18 > x1 - 6) break;
            hon_mark(t, mx, yy + (rh - 20) / 2 + 2, &adv); mx += adv - 2;
        }
    }
    if (nc) paint_growth(bx, by, Cm, Br, nb, U, nu);
    /* bonuses */
    float fy = y1 - foot + 4;
    line(x0 + 8, fy, x1 - 8, fy, 0x60C9A45Cu, 1);
    static const WCHAR *BN[3][6] = {
        { L"Faction", L"Army", L"Participation", L"Mercenary", L"Commander", L"Controlled" },
        { L"阵营", L"兵力", L"参战", L"佣兵", L"指挥官", L"阵营控制" },
        { L"陣營", L"兵力", L"參戰", L"傭兵", L"指揮官", L"陣營控制" } };
    char bb[64]; lstrcpynA(bb, R[4], sizeof bb);
    int bi = 0; float bxp = x0 + 10, bw = (w - 20) / 3;
    for (char *t = strtok(bb, ","); t && bi < 6; t = strtok(NULL, ","), bi++) {
        int pc = atoi(t);                                  /* percent x 100 (the result packet's scale) */
        if (pc % 100) swprintf(v, 160, L"%ls %ls%d.%d%%", BN[g_lang][bi], pc > 0 ? L"+" : L"", pc / 100, (pc % 100) / 10);
        else swprintf(v, 160, L"%ls %ls%d%%", BN[g_lang][bi], pc > 0 ? L"+" : L"", pc / 100);
        text(v, bxp + (bi % 3) * bw, fy + 3 + (bi / 3) * 18, bw, 18, 11, 0, 0, pc > 0 ? 0xFF8BE28Bu : C_MUTED, GP_ALIGN_NEAR, GP_ALIGN_CENTER);
    }
    rank_frame(x0, y0, x1, y1, g_rep_tier, g_rep_reinc);   /* (17:47) */
}
/* (user 11-01 08:30 "the options page in the same style") the OPTIONS page: a card like the login's, the game's
   CInsideOptionWnd underneath gets the clicks (lg_ot) and the volume drags (lg_osl) */
static void opt_seg(float x, float y, float w, float h, const WCHAR *t, int on, int dim, int id)
{
    int hov = hovered(H_LOPT, id);
    if (on) fill_rect(x, y, w, h, hov ? C_BRASS_HI : C_BRASS);
    else if (hov) fill_rect(x, y, w, h, 0x24C9A45Cu);
    stroke_rect(x + 0.5f, y + 0.5f, w - 1, h - 1, on ? C_BRASS_HI : hov ? C_BRASS_HI : 0x8CC9A45Cu, hov ? 1.5f : 1.1f);
    ARGB c = on ? 0xFF141008u : dim ? 0x66C9BC9Cu : hov ? C_BRASS_HI : C_TEXT;
    text(t, x, y, w, h, w < 64 ? 13 : 14, 0, on, c, GP_ALIGN_CENTER, GP_ALIGN_CENTER);
    hit_add(x, y, w, h, 0, H_LOPT, id);
}
static void opt_toggle(float xr, float y, float h, int on, int id)   /* ON / OFF at the right end xr */
{
    opt_seg(xr - 152, y, 74, h, T3("On", "开", "開"), on, 0, id);
    opt_seg(xr - 74, y, 74, h, T3("Off", "关", "關"), !on, 0, id + 1);
}
static void lg_paint_option_dlg(void)
{
    HudState *s = &g_ps;
    if (s->lg_osub == 1) {                           /* the colour picker: the game's square and bar in a framed hole */
        float hx0 = fx_ref(s->lg_ohole[0]), hy0 = fy_ref(s->lg_ohole[1]), hx1 = fx_ref(s->lg_ohole[2]), hy1 = fy_ref(s->lg_ohole[3]);
        float cx = hx0 - 36, cw = hx1 - hx0 + 72, cy = hy0 - 110, ch = hy1 - hy0 + 110 + 100;
        if (cy < 8) { cy = 8; }
        fill_rect(cx, cy, cw, ch, 0xDB0A1016u);
        stroke_rect(cx + 0.5f, cy + 0.5f, cw - 1, ch - 1, C_BRASS, 1.2f);
        diamond(cx + cw / 2, cy + 0.5f, 6, C_BRASS);
        if (g_lang) text(L"TEXT COLOUR", cx + 36, cy + 24, cw - 72, 20, 13, 1, 0, C_BRASS, GP_ALIGN_NEAR, GP_ALIGN_CENTER);
        text(T3("Text colour", "文字颜色", "文字顏色"), cx + 36, cy + 44, cw - 72, 40, 26, 0, 1, C_BRASS_HI, GP_ALIGN_NEAR, GP_ALIGN_CENTER);
        stroke_rect(hx0 - 2.5f, hy0 - 2.5f, hx1 - hx0 + 5, hy1 - hy0 + 5, C_BRASS, 1.4f);
        SetRect(&g_lg_hole, (int)(X(hx0) + 0.5f), (int)(Y(hy0) + 0.5f), (int)X(hx1), (int)Y(hy1));
        hit_add(hx0, hy0, hx1 - hx0, hy1 - hy0, 0, H_LPASS, 0);
        float by = hy1 + 24, hw = (cw - 72 - 12) / 2;
        lg_button(cx + 36, by, hw, 50, T3("OK", "确定", "確定"), 0, H_LOPT, OPT_DOK);
        lg_button(cx + 36 + hw + 12, by, hw, 50, T3("Cancel", "取消", "取消"), 2, H_LOPT, OPT_DCANCEL);
        return;
    }
    /* the macros: 10 lines (Ctrl + Shift + 1 .. 0), typed into the game's edits */
    float cw = 660, ch = 668, cx, cy; opt_card_pos(cw, ch, &cx, &cy);
    lg_card(cx, cy, cw, ch, L"MACROS", T3("Macros", "巨集", "巨集"));
    float px = cx + 44, pw = cw - 88, ry = cy + 104, rh = 42;
    for (int i = 0; i < 10; i++, ry += rh) {
        WCHAR num[4]; swprintf(num, 4, L"%d", (i + 1) % 10);
        text(num, px, ry, 30, rh, 18, 1, 1, C_BRASS, GP_ALIGN_NEAR, GP_ALIGN_CENTER);
        float ex = px + 36, ew = pw - 36, ey = ry + 4, eh = rh - 8;
        int foc = s->lg_ofoc == i + 1, hov = hovered(H_LFIELD, i);
        fill_rect(ex, ey, ew, eh, 0x73000000u);
        stroke_rect(ex + 0.5f, ey + 0.5f, ew - 1, eh - 1, foc ? C_BRASS_HI : hov ? C_BRASS : 0x8CC9A45Cu, foc ? 1.6f : 1.1f);
        WCHAR t[48] = { 0 }; int len = MultiByteToWideChar(CP_ACP, 0, s->lg_omac[i], -1, t, 48) - 1;
        if (len < 0) len = 0;
        text(t, ex + 12, ey, ew - 24, eh, 15, 0, 0, 0xFFF4E2B4u, GP_ALIGN_NEAR, GP_ALIGN_CENTER);
        if (foc && !s->lg_blink) {                   /* the caret: after the text up to it (bytes -> characters) */
            char a[40] = { 0 }; int cb = s->lg_ocaret; if (cb > 39) cb = 39; memcpy(a, s->lg_omac[i], cb);
            WCHAR u[48] = { 0 }; int cl = MultiByteToWideChar(CP_ACP, 0, a, -1, u, 48) - 1; if (cl < 0) cl = 0;
            float cxp = ex + 12 + text_w(u, cl, 15);
            line(cxp + 1, ey + 8, cxp + 1, ey + eh - 8, C_BRASS_HI, 1.4f);
        }
        hit_add(ex, ey, ew, eh, 0, H_LFIELD, i);
    }
    text(T3("Use: Ctrl + Shift + number", "使用：Ctrl + Shift + 数字", "使用：Ctrl + Shift + 數字"), px, ry, pw, 30, 13, 0, 0, C_MUTED, GP_ALIGN_NEAR, GP_ALIGN_CENTER);
    float by = cy + ch - 26 - 50, bw = (pw - 24) / 3;
    lg_button(px, by, bw, 50, T3("Default", "预设", "預設"), 1, H_LOPT, OPT_DDEFAULT);
    lg_button(px + bw + 12, by, bw, 50, T3("OK", "确定", "確定"), 0, H_LOPT, OPT_DOK);
    lg_button(px + 2 * (bw + 12), by, bw, 50, T3("Cancel", "取消", "取消"), 2, H_LOPT, OPT_DCANCEL);
}
static void lg_paint_option(void)
{
    HudState *s = &g_ps;
    if (s->lg_osub) { lg_paint_option_dlg(); return; }
    float cw = 660, ch = 668, cx, cy; opt_card_pos(cw, ch, &cx, &cy);
    lg_card(cx, cy, cw, ch, L"OPTIONS", T3("Options", "选项", "選項"));
    float px = cx + 44, pw = cw - 88, xr = px + pw;
    /* tabs */
    const WCHAR *tabs[2] = { T3("Sound & Graphics", "声音与画面", "聲音與畫面"), T3("Miscellaneous", "其他", "其他") };
    for (int i = 0; i < 2; i++) {
        float tx = px + i * (pw / 2), tw = pw / 2 - (i ? 0 : 8);
        int on = s->lg_otab == i, hov = hovered(H_LOPT, OPT_TAB0 + i);
        fill_rect(tx, cy + 104, tw, 44, on ? 0xE0201A10u : hov ? 0xD0161410u : 0xA00A1016u);
        stroke_rect(tx + 0.5f, cy + 104.5f, tw - 1, 43, on ? C_BRASS_HI : hov ? C_BRASS : 0x80C9A45Cu, on ? 1.6f : 1.0f);
        if (on) line(tx + 10, cy + 145, tx + tw - 10, cy + 145, C_BRASS, 2);
        text(tabs[i], tx, cy + 104, tw, 44, 16, 0, on, on || hov ? C_BRASS_HI : C_MUTED, GP_ALIGN_CENTER, GP_ALIGN_CENTER);
        if (!on) hit_add(tx, cy + 104, tw, 44, 0, H_LOPT, OPT_TAB0 + i);
    }
    float ry = cy + 164, rh = 58, bh = 36;
    #define ROW_LABEL(t) { text(t, px, ry, 200, rh, 16, 0, 0, C_TEXT, GP_ALIGN_NEAR, GP_ALIGN_CENTER); line(px, ry + rh - 0.5f, xr, ry + rh - 0.5f, 0x33C9A45Cu, 1); }
    float by = 0;
    if (s->lg_otab == 0) {
        const WCHAR *lab[5] = { T3("Footprints", "足迹", "足跡"), T3("Unit speech", "单位语音", "單位語音"), T3("Sound", "音效", "音效"),
                                T3("3D sound", "3D 音效", "3D 音效"), T3("Music", "音乐", "音樂") };
        int on[5] = { s->lg_of[0], s->lg_of[1], s->lg_of[2], s->lg_of[10], s->lg_of[3] };
        for (int r = 0; r < 5; r++, ry += rh) {
            ROW_LABEL(lab[r]);
            float yb = ry + (rh - bh) / 2;
            opt_toggle(xr, yb, bh, on[r], OPT_T0 + r * 2);
            if (r == 2 || r == 4) {                      /* volume: a track, its fill, a knob; dragged = the game's */
                int j = r == 4, v = s->lg_ovol[j]; if (v < 0) v = 0; if (v > 100) v = 100;
                float sx0 = px + 150, sx1 = xr - 152 - 22, sy = ry + rh / 2, f = v / 100.0f;
                fill_rect(sx0, sy - 3, sx1 - sx0, 6, 0x40C9A45Cu);
                fill_rect(sx0, sy - 3, (sx1 - sx0) * f, 6, on[r] ? C_BRASS : 0x80C9A45Cu);
                int hov = hovered(H_LOSL, j);
                fill_circle(sx0 + (sx1 - sx0) * f, sy, hov ? 10 : 8, hov ? C_BRASS_HI : C_BRASS);
                stroke_circle(sx0 + (sx1 - sx0) * f, sy, hov ? 10 : 8, 0xFF141008u, 1.2f);
                WCHAR pv[16]; swprintf(pv, 16, L"%d", v);
                text(pv, sx1 - 40, ry, 40, 14, 10, 1, 0, C_MUTED, GP_ALIGN_FAR, GP_ALIGN_NEAR);
                hit_add(sx0 - 10, ry + 6, sx1 - sx0 + 20, rh - 12, 0, H_LOSL, j);
            }
            if (r == 3) {                                /* 3D: headphones / two speakers / surround (off: dimmed) */
                const WCHAR *m3[3] = { T3("Headphones", "耳机", "耳機"), T3("2 speakers", "双喇叭", "雙喇叭"), T3("Surround", "环绕", "環繞") };
                float mw = 86, mx = xr - 152 - 18 - 3 * (mw + 6);
                for (int k = 0; k < 3; k++) opt_seg(mx + k * (mw + 6), yb, mw, bh, m3[k], on[3] && s->lg_o3d == k, !on[3], OPT_3D + k);
            }
        }
        const WCHAR *lc[2] = { T3("Text colour", "文字颜色", "文字顏色"), T3("Macros", "巨集", "巨集") };
        for (int r = 0; r < 2; r++, ry += rh) {
            ROW_LABEL(lc[r]);
            lg_button(xr - 152, ry + (rh - bh) / 2, 152, bh, T3("Change", "更改", "更改"), 1, H_LOPT, OPT_CHG + r);
        }
    } else {
        ROW_LABEL(T3("Scroll rate", "卷动速度", "捲動速度"));
        const WCHAR *sr[5] = { T3("V. low", "很慢", "很慢"), T3("Low", "慢", "慢"), T3("Med.", "中", "中"), T3("High", "快", "快"), T3("V. high", "很快", "很快") };
        float sw = 66, sx = xr - 5 * sw - 4 * 4;
        for (int k = 0; k < 5; k++) opt_seg(sx + k * (sw + 4), ry + (rh - bh) / 2, sw, bh, sr[k], s->lg_oscroll == k, 0, OPT_SCR + k);
        ry += rh;
        const WCHAR *lab[6] = { T3("Units targetable by allies", "盟友可选我方单位为目标", "盟友可選我方單位為目標"), T3("Record battles", "录制战斗", "錄製戰鬥"),
                                T3("Tutorial", "新手教学", "新手教學"), T3("Curse filter", "脏话过滤", "髒話過濾"),
                                T3("Help messages", "说明讯息", "說明訊息"), T3("News messages", "新闻讯息", "新聞訊息") };
        int on[6] = { s->lg_of[9], s->lg_of[4], s->lg_of[5], s->lg_of[6], s->lg_of[7], s->lg_of[8] };
        for (int r = 0; r < 6; r++, ry += rh) {
            text(lab[r], px, ry, pw - 170, rh, 16, 0, 0, C_TEXT, GP_ALIGN_NEAR, GP_ALIGN_CENTER);
            line(px, ry + rh - 0.5f, xr, ry + rh - 0.5f, 0x33C9A45Cu, 1);
            opt_toggle(xr, ry + (rh - bh) / 2, bh, on[r], OPT_T1 + r * 2);
        }
    }
    #undef ROW_LABEL
    by = cy + ch - 26 - 50;
    float hw = (pw - 12) / 2;
    lg_button(px, by, hw, 50, T3("OK", "确定", "確定"), 0, H_LOPT, OPT_OK);
    lg_button(px + hw + 12, by, hw, 50, T3("Cancel", "取消", "取消"), 2, H_LOPT, OPT_CANCEL);
}
static void paint_login(void)
{
    HudState *s = &g_ps;
    hit_add(0, 0, C.RW, C.RH, 0, H_LDEAD, 0);    /* everything else: the game sees the mouse nowhere */
    g_lg_game = s->lg_game;
    if (s->lg_game) {                            /* (11-01) the options over the game: the game dimmed, the card */
        fill_rect(0, 0, C.RW, C.RH, 0x8C000000u);
        if (s->lg_osub != 1) {                   /* the game's own window under the card: hidden */
            float cx, cy; opt_card_pos(660, 668, &cx, &cy);
            fill_rect(cx, cy, 660, 668, 0xFF0A1016u);
        }
        lg_paint_option();
        return;
    }
    int wide = s->lg == LG_NATION || (s->lg == LG_OPTION && s->lg_osub == 1);   /* pages that need the width */
    if (!wide) {                                 /* the side panel (the nation page needs the width) */
        fill_rect(0, 0, LG_SIDE, C.RH - LG_BAR, 0xB8060A10u);
        line(LG_SIDE, 0, LG_SIDE, C.RH - LG_BAR, 0x73C9A45Cu, 1);
    }
    /* title + server */
    /* (2026-11-02, user 16:15 "Shattered Galaxy改成Galactic Overlord"; Chinese name 银河霸主) */
    text(L"GALACTIC", 64, 48, 400, 44, 34, 1, 1, C_BRASS_HI, GP_ALIGN_NEAR, GP_ALIGN_CENTER);
    text(L"OVERLORD", 64 + 56, 92, 400, 44, 34, 1, 1, C_BRASS_HI, GP_ALIGN_NEAR, GP_ALIGN_CENTER);   /* (16:33) staggered, not aligned */
    {
        static WCHAR srv[40]; static int got;
        if (!got) {
            char a[64] = { 0 }; got = 1;
            GetPrivateProfileStringA("hud", "server_name", "", a, sizeof a, ".\\GORender.ini");
            if (a[0]) MultiByteToWideChar(CP_ACP, 0, a, -1, srv, 40);
            else lstrcpynW(srv, L3(L"Solar System", L"太阳系", L"太陽系"), 40);
        }
        WCHAR t[64]; wsprintfW(t, L"%s \x00b7 %s", L3(L"SERVER", L"服务器", L"伺服器"), srv);
        diamond(68, 160, 5, C_BRASS);
        text(t, 82, 148, 380, 24, 15, 0, 0, C_MUTED, GP_ALIGN_NEAR, GP_ALIGN_CENTER);
    }
    /* the side menu (the new commander's steps on its pages) */
    if (s->lg == LG_HERO) lg_paint_steps(1, 0);
    else if (s->lg == LG_NATION) { }              /* (its steps: right of the viewer, lg_paint_nation) */
    else if (wide) { }                            /* (the colour picker sits where the menu is) */
    else {
    static const WCHAR *MEN[6] = { L"NEW COMMANDER", L"CONTINUE", L"OPTIONS", L"BRIEFING ROOM", L"CREDITS", L"EXIT" };
    static const WCHAR *MCN[6] = { L"新指挥官", L"继续", L"选项", L"简报室", L"制作人员", L"退出游戏" };
    static const WCHAR *MTW[6] = { L"新指揮官", L"繼續", L"選項", L"簡報室", L"製作人員", L"退出遊戲" };
    int cur = s->lg == LG_CONT || s->lg == LG_CHPW ? 1 : s->lg == LG_CREATE ? 0 : s->lg == LG_BRIEF ? 3 : s->lg == LG_OPTION ? 2 : -1;
    float my = 236;
    for (int i = 0; i < 6; i++) {
        if (i == 4) continue;                    /* (user 11-01 08:31) no CREDITS */
        if (i == 5) { line(82, my + 8, 422, my + 8, 0x4DC9A45Cu, 1); my += 20; }
        float x = 64, w = 376, h = 56;
        int sel = i == cur, live = s->lg == LG_MAIN, hov = live && hovered(H_LMENU, i), ex = i == 5;
        if (sel || hov) {
            fill_rect(x, my, w, h, sel ? 0x24C9A45Cu : 0x18C9A45Cu);
            stroke_rect(x + 0.5f, my + 0.5f, w - 1, h - 1, sel ? C_BRASS : 0xB3C9A45Cu, 1.2f);
            diamond(x + 22, my + h / 2, 4.5f, sel ? C_BRASS_HI : C_BRASS);
        }
        float tx = x + ((sel || hov) ? 40 : 20);
        ARGB c1 = ex ? 0xFFF2A06Au : (sel || hov) ? C_BRASS_HI : C_MUTED, c2 = ex ? 0xFFC9875Au : (sel || hov) ? C_BRASS : 0xFF8E8470u;
        if (!live && !sel) { c1 = (c1 & 0xFFFFFF) | 0x73000000u; c2 = (c2 & 0xFFFFFF) | 0x59000000u; }
        if (g_lang) {
            const WCHAR *t = g_lang == 1 ? MCN[i] : MTW[i];
            text(t, tx, my, 200, h, 20, 0, sel || hov, c1, GP_ALIGN_NEAR, GP_ALIGN_CENTER);
            float tw = text_w(t, lstrlenW(t), 20);
            text(MEN[i], tx + tw + 14, my + 2, 260, h, 13, 1, 0, c2, GP_ALIGN_NEAR, GP_ALIGN_CENTER);
        } else text(MEN[i], tx, my, 330, h, 19, 1, 1, c1, GP_ALIGN_NEAR, GP_ALIGN_CENTER);
        if (live) hit_add(x, my, w, h, 0, H_LMENU, i);
        my += h + 4;
    }
    }
    /* the page */
    float cx = lg_cx();
    if (s->lg == LG_MAIN || s->lg == LG_CONT) {
        const WCHAR *lab[2] = { L3(L"ID", L"账号", L"帳號"), L3(L"Password", L"密码", L"密碼") };
        const WCHAR *btn[3] = { L3(L"START", L"开始", L"開始"), L3(L"Change password", L"修改密码", L"修改密碼"), L3(L"Cancel", L"取消", L"取消") };
        static const int st[3] = { 0, 1, 2 };
        lg_paint_form(cx, lg_cy(), L"COMMANDER LOGIN", L3(L"Commander Login", L"指挥官登录", L"指揮官登入"), lab, btn, st);
    } else if (s->lg == LG_CREATE) {
        const WCHAR *lab[4] = { L3(L"ID", L"账号", L"帳號"), L3(L"Password", L"密码", L"密碼"),
                                L3(L"Confirm password", L"确认密码", L"確認密碼"), L3(L"E-mail", L"电子邮件", L"電子郵件") };
        const WCHAR *btn[2] = { L3(L"OK", L"建立账号", L"建立帳號"), L3(L"Cancel", L"取消", L"取消") };
        static const int st[2] = { 0, 2 };
        lg_paint_form(cx, 40, L"CREATE ID", L3(L"Create ID", L"建立新账号", L"建立新帳號"), lab, btn, st);
    } else if (s->lg == LG_CHPW) {
        const WCHAR *lab[4] = { L3(L"ID", L"账号", L"帳號"), L3(L"Old password", L"旧密码", L"舊密碼"),
                                L3(L"New password", L"新密码", L"新密碼"), L3(L"Confirm new password", L"确认新密码", L"確認新密碼") };
        const WCHAR *btn[2] = { L3(L"OK", L"确定", L"確定"), L3(L"Cancel", L"取消", L"取消") };
        static const int st[2] = { 0, 2 };
        lg_paint_form(cx, 40, L"CHANGE PASSWORD", L3(L"Change Password", L"修改密码", L"修改密碼"), lab, btn, st);
    } else if (s->lg == LG_BRIEF) {
        lg_paint_brief(cx, 0);
    } else if (s->lg == LG_HERO) {
        lg_paint_hero();
    } else if (s->lg == LG_NATION) {
        lg_paint_nation();
    } else if (s->lg == LG_OPTION) {
        lg_paint_option();
    } else if (s->lg == LG_BOOT || s->lg == LG_LOAD) {
        float cy = lg_cy() + 150;
        text(s->lg == LG_LOAD ? L3(L"Loading ...", L"正在载入……", L"正在載入……") : L3(L"Starting ...", L"正在启动……", L"正在啟動……"), cx, cy, LG_CW, 60, 22, 0, 0, C_BRASS_HI, GP_ALIGN_CENTER, GP_ALIGN_CENTER);
        float t = (float)(GetTickCount() % 1600) / 1600.0f;
        fill_rect(cx + 80, cy + 70, LG_CW - 160, 3, 0x33C9A45Cu);
        fill_rect(cx + 80 + (LG_CW - 160 - 90) * t, cy + 70, 90, 3, C_BRASS);
    }
    /* the advisor bar */
    float ay = C.RH - LG_BAR;
    text(L3(L"TACTICAL ADVISOR", L"战术顾问", L"戰術顧問"), 194, ay + 14, 600, 22, 13, !g_lang, 0, C_BRASS, GP_ALIGN_NEAR, GP_ALIGN_CENTER);
    const WCHAR *tip = s->lg_msg[0] ? s->lg_msg
        : s->lg == LG_CONT ? L3(L"Enter your ID and password, then press START.", L"输入账号与密码，按「开始」进入银河。", L"輸入帳號與密碼，按「開始」進入銀河。")
        : s->lg == LG_CREATE ? L3(L"Choose an ID and a password for your new commander.", L"为新指挥官设定账号与密码。", L"為新指揮官設定帳號與密碼。")
        : s->lg == LG_CHPW ? L3(L"Enter your ID, the old password and the new one twice.", L"输入账号、旧密码，并输入两次新密码。", L"輸入帳號、舊密碼，並輸入兩次新密碼。")
        : s->lg == LG_BRIEF ? L3(L"Pick a recording and press PLAY to watch the battle again.", L"选择一条录像，按「播放」重温战斗。", L"選擇一筆錄影，按「播放」重溫戰鬥。")
        : s->lg == LG_NATION ? L3(L"Pick the planet and the nation you will fight for.", L"选择你要效力的星球与国家。", L"選擇你要效力的星球與國家。")
        : s->lg == LG_HERO ? L3(L"Pick your commander and share out the points.", L"选择你的指挥官并分配加成点数。", L"選擇你的指揮官並分配加成點數。")
        : s->lg == LG_BOOT ? L3(L"Connecting to the galaxy ...", L"正在连接银河……", L"正在連接銀河……")
        : s->lg == LG_LOAD ? L3(L"Loading the map, Commander ...", L"正在载入地图，请稍候……", L"正在載入地圖，請稍候……")
        : s->lg == LG_OPTION ? L3(L"Set sound, scrolling and messages, then press OK.", L"调整声音、卷动速度与讯息设定，按「确定」保存。", L"調整聲音、捲動速度與訊息設定，按「確定」儲存。")
        : L3(L"Welcome back, Commander. Choose CONTINUE to log in.", L"欢迎回来，指挥官。选择「继续」登录，或建立新指挥官。", L"歡迎回來，指揮官。選擇「繼續」登入，或建立新指揮官。");
    float tipw = C.RW - 220;
    if (s->lg_qon) {                                /* the advisor's OK */
        tipw -= 190;
        float qx = C.RW - 200, qy = ay + 26;
        float t = (float)(GetTickCount() % 1400) / 1400.0f, a = 0.5f + 0.5f * sinf(t * 6.2831853f);
        stroke_rect(qx - 4.5f, qy - 4.5f, 179, 61, alpha(C_BRASS_HI, 0.25f + 0.5f * a), 1.4f);
        lg_button(qx, qy, 170, 52, L3(L"OK", L"确定", L"確定"), 0, H_LQ, 0);
    }
    {   /* up to two lines (the game's advisor texts are long) */
        static GpStringFormat *wf;
        if (!wf) { pGdipCreateStringFormat(0, 0, &wf); pGdipSetStringFormatTrimming(wf, GP_TRIM_ELLIPSIS); }
        GpFont *f = font(16, 0, 0);
        GpRectF r = { X(194), Y(ay + 38), S(tipw), S(56) };
        if (f && wf) {
            pGdipSetStringFormatAlign(wf, GP_ALIGN_NEAR); pGdipSetStringFormatLineAlign(wf, GP_ALIGN_CENTER);
            pGdipDrawString(C.g, tip, -1, f, &r, wf, brush(s->lg_msg[0] ? C_BRASS_HI : C_TEXT));
        }
    }
}

static int ctx_setup(void)                      /* the scale of this snapshot (0: the window is too small) */
{
    fonts_init();
    RECT d = g_ps_dest;
    float dw = (float)(d.right - d.left), dh = (float)(d.bottom - d.top);
    if (dw < 200 || dh < 150) return 0;
    C.s = dh / 1080.0f;
    if (dw / C.s < 1500) C.s = dw / 1500.0f;
    C.ox = (float)d.left; C.oy = (float)d.top;
    C.RW = dw / C.s; C.RH = dh / C.s;
    C.fx0 = (float)d.left; C.fy0 = (float)d.top; C.fsx = dw / g_ps.W; C.fsy = dh / 600.0f;
    if (!g_brush) pGdipCreateSolidFill(0xFFFFFFFFu, &g_brush);
    if (!g_fmt) { pGdipCreateStringFormat(GP_SF_NOWRAP, 0, &g_fmt); pGdipSetStringFormatTrimming(g_fmt, GP_TRIM_ELLIPSIS); }
    return 1;
}
static int paint_inner(unsigned *bits, int w, int h)   /* the login screen: one full picture */
{
    g_wnhit = 0; g_wrad_r = 0;
    if (!g_ps.lg && (!g_ps.active || (g_ps.covered && !g_ps.nskw))) return 0;   /* a big window: only the re-skinned ones */
    if (!ctx_setup()) return 0;
    if (g_ps.lg) {                                    /* the login screen: its own scale (810 high), static layer */
        float dw = (float)(g_ps_dest.right - g_ps_dest.left), dh = (float)(g_ps_dest.bottom - g_ps_dest.top);
        C.s = dh / 810.0f; C.RW = dw / C.s; C.RH = 810;
        if (g_ps.lg_game) memset(bits, 0, (size_t)w * h * 4);   /* (11-01) the options over the game */
        else {
            login_layer(w, h);
            if (g_lbg) memcpy(bits, g_lbg, (size_t)w * h * 4);
        }
    }
    GpBitmap *bmp = NULL;
    if (pGdipCreateBitmapFromScan0(w, h, w * 4, GP_PARGB, (BYTE *)bits, &bmp) != 0) return 0;
    if (pGdipGetImageGraphicsContext(bmp, &C.g) != 0) { pGdipDisposeImage(bmp); return 0; }
    pGdipSetSmoothingMode(C.g, GP_SMOOTH_AA);
    pGdipSetTextRenderingHint(C.g, GP_TEXT_AA);
    pGdipSetPixelOffsetMode(C.g, GP_PIXOFF_HALF);
    if (!g_brush) pGdipCreateSolidFill(0xFFFFFFFFu, &g_brush);
    if (!g_fmt) { pGdipCreateStringFormat(GP_SF_NOWRAP, 0, &g_fmt); pGdipSetStringFormatTrimming(g_fmt, GP_TRIM_ELLIPSIS); }
    g_frame_live = 0;
    if (g_ps.lg) {
        SetRectEmpty(&g_lg_hole);
        g_stage_paint = "paint_login"; paint_login();
    } else if (!g_ps.covered) {
        g_stage_paint = "paint_band"; paint_band();
        g_stage_paint = "paint_cards"; paint_cards();
        g_stage_paint = "paint_banner"; paint_banner();
        g_stage_paint = "paint_radar"; paint_radar();
    }
    if (!g_ps.lg) { g_stage_paint = "paint_skin"; paint_skin(); }
    if (!g_ps.lg && g_hon_open) { g_stage_paint = "paint_honor"; paint_honor(); }
    if (!g_ps.lg) { g_stage_paint = "paint_tip"; paint_tip(); } else g_tip_m = NULL;
    g_stage_paint = "done";
    pGdipDeleteGraphics(C.g); C.g = NULL;
    pGdipDisposeImage(bmp);
    if (g_ps.lg && !IsRectEmpty(&g_lg_hole)) {      /* the game's live picture shows through */
        RECT r = g_lg_hole;
        if (r.left < 0) r.left = 0; if (r.top < 0) r.top = 0; if (r.right > w) r.right = w; if (r.bottom > h) r.bottom = h;
        for (int y = r.top; y < r.bottom; y++) memset(bits + (size_t)y * w + r.left, 0, (size_t)(r.right - r.left) * 4);
    }
    return 1;
}
