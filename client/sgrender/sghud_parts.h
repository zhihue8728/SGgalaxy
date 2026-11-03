/* sghud_parts.h - part of sghud.c (included in this order; not a header on its own): the parts of the game screen: cards, banner, radar, band, the re-skinned windows and controls */
/* ---- the parts ----------------------------------------------------------------------------------------------- */
static void paint_cards(void)
{
    HudState *s = &g_ps;
    if (!s->ncard) return;
    /* up to 6: one column; more: two columns of compact cards (user 10-28 19:50: 11 cards were too long) */
    int cols = s->ncard > 6 ? 2 : 1, rows = (s->ncard + cols - 1) / cols;
    /* (user 10-29 22:30 "units cover the replay buttons"): a recording's controls (drawn by the game, frame y 8..76
       at the top left) stay free - the cards start below them */
    float x0 = 24, y0 = s->replay ? fy_ref(84) : 24, w = cols == 1 ? 250 : 196, gapx = 8, avail = fy_ref(462) - y0 - 16;
    float h = cols == 1 ? 60 : 52, gap = 6;
    if (rows * (h + gap) > avail) { h = avail / rows - gap; if (h < 34) { h = 34; gap = 4; } }
    if (occluded(x0, y0, cols * w + (cols - 1) * gapx, rows * (h + gap))) return;
    float r = h * 0.36f;
    for (int i = 0; i < s->ncard; i++) {
        HudUnit *u = &s->card[i];
        float x = x0 + (i / rows) * (w + gapx), y = y0 + (i % rows) * (h + gap);
        int hov = hovered(H_CARD, (int)u->id);
        ARGB edge = u->sel ? C_BRASS : hov ? 0xA0C9A45Cu : 0x48C9A45Cu;
        float op = u->dead ? 0.55f : 1.0f;
        fill_rect(x, y, w, h, alpha(C_INK, 0.82f * op));
        stroke_rect(x + 0.5f, y + 0.5f, w - 1, h - 1, edge, u->sel ? 1.6f : 1.0f);
        if (u->sel) diamond(x + w, y + h / 2, 4.5f, C_BRASS);
        WCHAR key[4]; swprintf(key, 4, L"%d", i + 1);
        text(key, x + 3, y, 24, h, h * 0.24f, 1, 1, C_MUTED, GP_ALIGN_CENTER, GP_ALIGN_CENTER);
        float cx = x + 28 + r + 2, cy = y + h / 2;
        float frac = u->hpmax > 0 ? (float)u->hp / u->hpmax : 0;
        ARGB hpc = u->dead ? 0xFF5B5F62u : frac < 0.35f ? C_EMBER : C_HP;
        fill_circle(cx, cy, r, 0xFF121A20u);
        stroke_circle(cx, cy, r, 0x1FFFFFFFu, 3);
        if (!u->dead) arc(cx, cy, r, -90, 360 * frac, hpc, 3);
        icon(unit_icon(u), cx, cy, r * 1.05f, unit_color(u), 1.6f);
        float tx = cx + r + 8, tw = x + w - 10 - tx;
        text(u->name, tx, y + h * 0.08f, tw * 0.62f, h * 0.38f, h * 0.25f, 1, 1, u->dead ? C_MUTED : C_TEXT, GP_ALIGN_NEAR, GP_ALIGN_CENTER);
        text(unit_class(u), tx + tw * 0.5f, y + h * 0.08f, tw * 0.5f, h * 0.38f, h * 0.2f, 0, 1, u->dead ? C_MUTED : unit_color(u), GP_ALIGN_FAR, GP_ALIGN_CENTER);
        bar(tx, y + h * 0.56f, tw, h * 0.08f, frac, hpc);
        bar(tx, y + h * 0.70f, tw, h * 0.05f, u->enmax > 0 ? (float)u->en / u->enmax : 0, C_ENERGY);
        hit_add(x, y, w, h, 0, H_CARD, (int)u->id);
    }
}

static void paint_banner(void)
{
    HudState *s = &g_ps;
    if (!s->battle) return;
    float w = 200 + s->npoc * 64 + 190, h = 76, x = (C.RW - w) / 2, y = 14;
    if (occluded(x, y, w, h)) return;
    fill_rect(x, y, w, h, 0xD80A1016u);
    stroke_rect(x + 0.5f, y + 0.5f, w - 1, h - 1, 0xB0C9A45Cu, 1.2f);
    stroke_rect(x + 4, y + 4, w - 8, h - 8, 0x30C9A45Cu, 1.0f);
    diamond(x + w / 2, y + h, 5, C_BRASS);
    /* timer dial */
    float cx = x + 44, cy = y + h / 2, r = 27;
    fill_circle(cx, cy, r, 0xFF121A20u);
    stroke_circle(cx, cy, r, 0x30FFFFFFu, 3);
    float frac = s->total > 0 ? (float)s->left / s->total : 0;
    arc(cx, cy, r, -90, 360 * frac, s->left < 180 ? C_EMBER : C_BRASS, 3);
    WCHAR t[16]; swprintf(t, 16, L"%02d:%02d", s->left / 60, s->left % 60);
    text(t, x + 78, y, 110, h, 30, 1, 1, s->left < 180 ? 0xFFF2A06Au : C_BRASS_HI, GP_ALIGN_NEAR, GP_ALIGN_CENTER);
    /* POCs */
    float px = x + 200;
    for (int i = 0; i < s->npoc; i++, px += 64) {
        HudPoc *p = &s->poc[i];
        float pcx = px + 26, pcy = cy - 6;
        ARGB c = rel_color(p->rel);
        GpPointF d[4] = { { X(pcx), Y(pcy - 22) }, { X(pcx + 22), Y(pcy) }, { X(pcx), Y(pcy + 22) }, { X(pcx - 22), Y(pcy) } };
        pGdipFillPolygon(C.g, brush(alpha(c, 0.22f)), d, 4, GP_FILL_ALT);
        pGdipDrawPolygon(C.g, pen(c, S(1.6f)), d, 4);
        float fr = p->max > 0 ? (float)p->str / p->max : 0;
        arc(pcx, pcy, 26, -90, 360 * fr, alpha(c, 0.9f), 2);
        WCHAR l[2] = { (WCHAR)(L'A' + i), 0 };
        text(l, pcx - 20, pcy - 20, 40, 40, 18, 1, 1, C_BRASS_HI, GP_ALIGN_CENTER, GP_ALIGN_CENTER);
        WCHAR pc[8]; swprintf(pc, 8, L"%d%%", (int)(fr * 100 + 0.5f));
        text(pc, pcx - 30, pcy + 22, 60, 16, 11, 1, 0, C_MUTED, GP_ALIGN_CENTER, GP_ALIGN_CENTER);
    }
    /* unit counts */
    float rx = x + 200 + s->npoc * 64 + 18;
    line(rx - 10, y + 14, rx - 10, y + h - 14, 0x50C9A45Cu, 1);
    WCHAR a[40], e[40];
    swprintf(a, 40, L"%ls  %d", T3("Allies", "我方", "我方"), s->n_mine);
    swprintf(e, 40, L"%ls  %d", T3("Enemy", "敌方", "敵方"), s->n_enemy);
    fill_circle(rx + 8, y + 26, 5, C_MINE);
    text(a, rx + 20, y + 12, 180, 28, 16, 0, 1, C_TEXT, GP_ALIGN_NEAR, GP_ALIGN_CENTER);
    fill_circle(rx + 8, y + 52, 5, C_ENEMY);
    text(e, rx + 20, y + 38, 180, 28, 16, 0, 1, C_TEXT, GP_ALIGN_NEAR, GP_ALIGN_CENTER);
    hit_add(x, y, w, h, 0, H_SWALLOW, 0);
}

static float g_wrad_cx, g_wrad_cy, g_wrad_r;   /* radar geometry (reference units), painter */
static float g_rad_cx, g_rad_cy, g_rad_r;      /* published for the mouse */
static Ctx g_pubC; static int g_pub_mapw, g_pub_maph;
static void paint_radar(void)
{
    HudState *s = &g_ps;
    /* a fixed place (user 10-28 21:15 "the minimap moves": it used to step below small game windows at the top
       right); hidden only while a game window covers its centre (the quick menu sliding in) */
    float r = 128, cx = C.RW - 24 - 34 - r, cy = 24 + 16 + r;
    g_wrad_r = 0;
    if (s->mapw <= 0 || s->maph <= 0) return;
    if (occluded(cx - 1, cy - 1, 2, 2)) return;
    g_wrad_cx = cx; g_wrad_cy = cy; g_wrad_r = r;
    fill_circle(cx, cy, r + 10, 0xE00A1016u);
    stroke_circle(cx, cy, r + 10, 0xC0C9A45Cu, 1.4f);
    stroke_circle(cx, cy, r, 0x60C9A45Cu, 1.0f);
    for (int i = 0; i < 72; i++) {                       /* compass ticks */
        float a = i * 5 * 3.14159265f / 180, l = (i % 18 == 0) ? 9 : (i % 2 == 0 ? 5 : 3);
        line(cx + (r + 10) * cosf(a), cy + (r + 10) * sinf(a), cx + (r + 10 - l) * cosf(a), cy + (r + 10 - l) * sinf(a),
             (i % 18 == 0) ? C_BRASS : 0x70C9A45Cu, 1);
    }
    const WCHAR *nesw[4] = { L"N", L"E", L"S", L"W" };
    for (int i = 0; i < 4; i++) {
        float a = (i * 90 - 90) * 3.14159265f / 180;
        float tx = cx + (r + 24) * cosf(a), ty = cy + (r + 24) * sinf(a);
        fill_circle(tx, ty, 9, 0xF00A1016u);
        text(nesw[i], tx - 10, ty - 10, 20, 20, 12, 1, 1, C_BRASS_HI, GP_ALIGN_CENTER, GP_ALIGN_CENTER);
    }
    /* the map square inscribed in the circle */
    float side = r * 1.414f, mx = cx - side / 2, my = cy - side / 2;
    float k = side / (float)(s->mapw > s->maph ? s->mapw : s->maph);
    float ox = mx + (side - s->mapw * k) / 2, oy = my + (side - s->maph * k) / 2;
    GpPath *clip; pGdipCreatePath(GP_FILL_ALT, &clip);
    pGdipAddPathEllipse(clip, X(cx - r), Y(cy - r), S(2 * r), S(2 * r));
    pGdipSetClipPath(C.g, clip, GP_COMBINE_REPLACE);
    fill_rect(ox, oy, s->mapw * k, s->maph * k, 0x40142018u);
    for (int i = 1; i < 5; i++) {                        /* grid A-E / 1-5 like the old minimap */
        line(ox + s->mapw * k * i / 5, oy, ox + s->mapw * k * i / 5, oy + s->maph * k, 0x22C9A45Cu, 1);
        line(ox, oy + s->maph * k * i / 5, ox + s->mapw * k, oy + s->maph * k * i / 5, 0x22C9A45Cu, 1);
    }
    stroke_rect(ox, oy, s->mapw * k, s->maph * k, 0x50C9A45Cu, 1);
    for (int i = 0; i < s->npoc; i++) {
        HudPoc *p = &s->poc[i];
        diamond(ox + (p->tx * 32 + 16) * k, oy + (p->ty * 32 + 16) * k, 6, rel_color(p->rel));
    }
    for (int i = 0; i < s->nbld; i++) {                  /* buildings: small brass blocks */
        HudBox *b = &s->bld[i];
        float bx = ox + b->tx * 32 * k, by = oy + b->ty * 32 * k, bw = b->tw * 32 * k, bh = b->th * 32 * k;
        if (bw < 7) { bx -= (7 - bw) / 2; bw = 7; }
        if (bh < 7) { by -= (7 - bh) / 2; bh = 7; }
        fill_rect(bx, by, bw, bh, 0xD0B08A48u);
        stroke_rect(bx, by, bw, bh, 0xFFF2D9A0u, 1);
    }
    for (int i = 0; i < s->ngate; i++) {                 /* star gates: a ring in the colour of the province beyond */
        HudBox *g = &s->gate[i];
        float gx = ox + (g->tx + g->tw / 2.0f) * 32 * k, gy = oy + (g->ty + g->th / 2.0f) * 32 * k;
        float gr = g->tw * 16 * k; if (gr < 5.5f) gr = 5.5f;
        ARGB c = g->rel == REL_NEUTRAL ? 0xFF8FD8FFu : rel_color(g->rel);
        fill_circle(gx, gy, gr + 1.5f, 0xC0000000u);
        stroke_circle(gx, gy, gr, c, 1.8f);
        fill_circle(gx, gy, gr * 0.45f, alpha(c, 0.75f));
    }
    for (int i = 0; i < s->ndot; i++) {
        HudDot *d = &s->dot[i];
        fill_circle(ox + d->x * k, oy + d->y * k, d->rel == REL_MINE ? 2.6f : 2.3f, rel_color(d->rel));
    }
    stroke_rect(ox + s->camx * k, oy + s->camy * k, s->camw * k, s->camh * k, C_BRASS_HI, 1.2f);
    pGdipResetClip(C.g);
    pGdipDeletePath(clip);
    hit_add(cx - r - 10, cy - r - 10, 2 * r + 20, 2 * r + 20, 1, H_RADAR, 0);
}

/* the bottom panels, floating over the map (F51: the map is the whole frame high now - user 10-28 20:41 "the battle
   view should be taller"): chat (left, a hole where the game's own chat shows through), the buttons of the old panel
   (bottom right, 3 x 3) and in battle the selected unit (left of the buttons, or above them when the frame is
   narrow).  Between them the map shows and takes the mouse. */
static void panel_bg(float x, float y, float w, float h)
{
    GpPointF g0 = { 0, Y(y) }, g1 = { 0, Y(y + h) };
    GpLineGradient *lg = NULL;
    pGdipCreateLineBrush(&g0, &g1, 0xEE121A20u, 0xF505080Bu, 0, &lg);
    pGdipFillRectangle(C.g, lg ? (GpBrush *)lg : brush(0xF00A1016u), X(x), Y(y), S(w), S(h));
    if (lg) pGdipDeleteBrush(lg);
    line(x, y + 0.5f, x + w, y + 0.5f, 0xC0C9A45Cu, 1.4f);
    line(x, y + 4.5f, x + w, y + 4.5f, 0x30C9A45Cu, 1);
    if (x > 0.5f) line(x + 0.5f, y, x + 0.5f, y + h, 0x80C9A45Cu, 1.2f);
    if (x + w < C.RW - 0.5f) line(x + w - 0.5f, y, x + w - 0.5f, y + h, 0x80C9A45Cu, 1.2f);
    diamond(x + w / 2, y + 1, 5, C_BRASS);
    hit_add(x, y, w, h, 0, H_SWALLOW, 0);
}
static float g_band_y;
static void paint_band(void)
{
    HudState *s = &g_ps;
    float hole_x0 = fx_ref(4), hole_x1 = fx_ref(12 + 410 + 6), hole_y0 = fy_ref(470), hole_y1 = fy_ref(598);
    float yb = hole_y0 - 30, cw0;
    g_band_y = yb;
    if (s->chat_open) {                                /* chat: grey, no frame; pin + fold buttons in its title row */
        cw0 = hole_x1 + 10;
        /* the box itself is darkened in the frame (chat_glass): here only its title row */
        g_glass.left = 0; g_glass.top = (LONG)fy_frame(yb); g_glass.right = (LONG)(fx_frame(cw0) + 0.5f); g_glass.bottom = 600;
        text(T3("CHAT", "聊天", "聊天"), hole_x0 + 6, yb + 2, 200, hole_y0 - yb - 4, 14, 0, 1, C_TEXT, GP_ALIGN_NEAR, GP_ALIGN_CENTER);
        hit_add(0, yb, cw0, C.RH - yb, 0, H_CHATBG, 0);
        {   /* (user 10-31 17:11 "all / allies / private"): the chat's three send modes (the game's ctp-chat buttons, hidden)
               as tabs - the one in use lit in its colour; 私人 shows the game's "whisper to" field in the input row */
            static const int ORD[3] = { 0, 2, 1 };
            static const ARGB MC[3] = { 0xFFF2E6C8u, 0xFFE8A0C8u, 0xFF8BE28Bu };
            float tx = hole_x0 + 62, tw2 = 62, th2 = hole_y0 - yb - 8;
            for (int q = 0; q < 3; q++) {
                int md = ORD[q], on = s->chat_mode == md, hov = hovered(H_CHAT, 10 + md);
                float bx = tx + q * (tw2 + 6), by = yb + 4;
                fill_rect(bx, by, tw2, th2, on ? (MC[md] & 0x00FFFFFFu) | 0x38000000u : hov ? 0x30FFFFFFu : 0x18FFFFFFu);
                stroke_rect(bx + 0.5f, by + 0.5f, tw2 - 1, th2 - 1, on ? MC[md] : 0x60C9A45Cu, on ? 1.4f : 1.0f);
                const WCHAR *lb = md == 0 ? T3("All", "全体", "全體") : md == 2 ? T3("Allies", "同盟", "同盟") : T3("Private", "私人", "私人");
                text(lb, bx, by, tw2, th2, 12, 0, on, on ? MC[md] : hov ? C_TEXT : C_MUTED, GP_ALIGN_CENTER, GP_ALIGN_CENTER);
                hit_add(bx, by, tw2, th2, 0, H_CHAT, 10 + md);
            }
        }
        hit_add(hole_x0, hole_y0, hole_x1 - hole_x0, hole_y1 - hole_y0, 0, H_HOLE, 1);   /* the game's chat: its clicks pass */
        float by = yb + 3, bs = 22;
        for (int k = 0; k < 2; k++) {                  /* k 0: fold (rightmost), 1: pin */
            float bx = cw0 - 8 - bs - k * (bs + 6);
            int hov = hovered(H_CHAT, k), on = k == 1 && s->chat_pin;
            if (hov || on) fill_rect(bx, by, bs, bs, on ? 0x80C9A45Cu : 0x40FFFFFFu);
            ARGB c = hov ? C_BRASS_HI : on ? 0xFF1A1E22u : C_MUTED;
            float cx = bx + bs / 2, cy = by + bs / 2;
            if (k == 0) {                              /* fold: a chevron to the left */
                line(cx + 3, cy - 6, cx - 3, cy, c, 2); line(cx - 3, cy, cx + 3, cy + 6, c, 2);
            } else {                                   /* pin: head, body, needle */
                fill_circle(cx, cy - 4, 4, c);
                line(cx - 5, cy + 1, cx + 5, cy + 1, c, 2);
                line(cx, cy + 1, cx, cy + 8, c, 1.6f);
            }
            hit_add(bx, by, bs, bs, 0, H_CHAT, k);
        }
    } else {                                           /* folded: a tab at the bottom left */
        float tw = 88, th = 34, ty = C.RH - th;
        int hov = hovered(H_CHAT, 2);
        fill_rect(0, ty, tw, th, hov ? 0xC0101418u : 0x9A0A0D10u);
        text(T3("CHAT", "聊天", "聊天"), 10, ty, 50, th, 14, 0, 1, hov ? C_BRASS_HI : C_TEXT, GP_ALIGN_NEAR, GP_ALIGN_CENTER);
        float cx = tw - 18, cy = ty + th / 2;
        ARGB c = hov ? C_BRASS_HI : C_MUTED;
        line(cx - 3, cy - 6, cx + 3, cy, c, 2); line(cx + 3, cy, cx - 3, cy + 6, c, 2);
        hit_add(0, ty, tw, th, 0, H_CHAT, 2);
        cw0 = tw;
    }

    const WCHAR *names[WHEEL_N] = { T3("Strategic map", "战略地图", "戰略地圖"), T3("Quick menu", "快速选单", "快速選單"),
                                    T3("Who list", "在线名单", "線上名單"), T3("Mail", "邮件", "郵件"), T3("Board", "公告板", "公告板"),
                                    T3("Battle info", "战况说明", "戰況說明"), T3("Permission", "加入许可", "加入許可"),
                                    T3("Options", "选项", "選項"), T3("Leave", "离开战场", "離開戰場"),
                                    s->battle ? T3("Reinforce", "请求增援", "請求增援") : T3("Deploy units", "部署单位", "部署單位") };
    /* user 10-28 21:03 "the menu takes too much view": four labelled buttons (strategic map, battle info,
       permission, quick menu) under a row of icon buttons (options, mail, board, who list, leave; name on hover) */
    static const int TXT[5] = { 0, 5, 6, 1, 9 }, ICO[6] = { 7, 3, 4, 2, -1, 8 };   /* -1: the unit honor page (10-31) */
    const float gap = 6, bw = 124, bh = 36, ib = 37, ih = 34;
    float pw = 2 * bw + gap + 24, ph = 14 + ih + gap + 3 * bh + 2 * gap + 12;      /* 272 x 190 */
    float px = C.RW - pw, py = C.RH - ph;
    /* in battle: the selected unit left of the buttons (500..600 wide) or above them */
    float uph = 162, uw = px - 8 - (cw0 + 8), ux0 = 0, uy0 = 0;
    int unit = s->battle && s->nsel;                  /* nothing selected: no unit panel, more map */
    if (unit) {
        if (uw >= 500) { if (uw > 600) uw = 600; ux0 = px - uw - 8; uy0 = C.RH - uph; }
        else { uw = 420; uph = 210; ux0 = C.RW - uw; uy0 = py - uph - 8; if (uy0 < fy_ref(300)) unit = 0; }
    }
    panel_bg(px, py, pw, ph);
    float ibx = px + 12 + ((pw - 24) - (6 * ib + 5 * gap)) / 2, iby = py + 14;
    for (int k = 0; k < 6; k++) {
        int i = ICO[k];
        float x = ibx + k * (ib + gap), y = iby;
        if (occluded(x, y, ib, ih)) continue;
        if (i < 0) {                                       /* (10-31) the unit honor page */
            int hov = hovered(H_HONOR, 0) || g_hon_open;
            fill_rect(x, y, ib, ih, hov ? 0xF0201A10u : 0xE80A1016u);
            stroke_rect(x + 0.5f, y + 0.5f, ib - 1, ih - 1, hov ? C_BRASS_HI : 0x90C9A45Cu, hov ? 1.8f : 1.2f);
            icon(IC_TROPHY, x + ib / 2, y + ih / 2, 18, hov ? C_BRASS_HI : 0xFFE3C88Au, 1.5f);
            if (hovered(H_HONOR, 0)) {
                float tw = 110, tx = x + ib / 2 - tw / 2;
                fill_rect(tx, y - 30, tw, 24, 0xF00A1016u);
                stroke_rect(tx + 0.5f, y - 29.5f, tw - 1, 23, 0x90C9A45Cu, 1);
                text(T3("Unit honors", "单位荣誉", "單位榮譽"), tx, y - 30, tw, 24, 12, 0, 1, C_BRASS_HI, GP_ALIGN_CENTER, GP_ALIGN_CENTER);
            }
            if (s->replay) fill_rect(x, y, ib, ih, 0xA00A1016u); else hit_add(x, y, ib, ih, 0, H_HONOR, 0);
            continue;
        }
        int hov = hovered(H_WHEEL, i), last = i == WHEEL_LEAVE;
        ARGB edge = last ? (hov ? 0xFFF2A06Au : 0xC0E07A3Au) : (hov ? C_BRASS_HI : 0x90C9A45Cu);
        fill_rect(x, y, ib, ih, hov ? 0xF0201A10u : 0xE80A1016u);
        stroke_rect(x + 0.5f, y + 0.5f, ib - 1, ih - 1, edge, hov ? 1.8f : 1.2f);
        icon(WHEEL_ICON[i], x + ib / 2, y + ih / 2, 18, last ? 0xFFF2A06Au : hov ? C_BRASS_HI : 0xFFE3C88Au, 1.5f);
        if (hov) {                                         /* its name above it */
            float tw = 110, tx = x + ib / 2 - tw / 2;
            if (tx + tw > C.RW - 4) tx = C.RW - 4 - tw;
            fill_rect(tx, y - 30, tw, 24, 0xF00A1016u);
            stroke_rect(tx + 0.5f, y - 29.5f, tw - 1, 23, 0x90C9A45Cu, 1);
            text(names[i], tx, y - 30, tw, 24, 12, 0, 1, last ? 0xFFF2A06Au : C_BRASS_HI, GP_ALIGN_CENTER, GP_ALIGN_CENTER);
        }
        if (s->replay) fill_rect(x, y, ib, ih, 0xA00A1016u); else hit_add(x, y, ib, ih, 0, H_WHEEL, i);   /* (17:20) a recording: no buttons */
    }
    for (int k = 0; k < 5; k++) {
        int i = TXT[k];
        float x = px + 12 + (k % 2) * (bw + gap), y = iby + ih + gap + (k / 2) * (bh + gap);
        float bw = k == 4 ? 2 * 124 + gap : 124;         /* the deploy / reinforce button: the whole width */
        if (occluded(x, y, bw, bh)) continue;
        int hov = hovered(H_WHEEL, i);
        fill_rect(x, y, bw, bh, hov ? 0xF0201A10u : 0xE80A1016u);
        stroke_rect(x + 0.5f, y + 0.5f, bw - 1, bh - 1, hov ? C_BRASS_HI : 0x90C9A45Cu, hov ? 1.8f : 1.2f);
        icon(WHEEL_ICON[i], x + 10 + 8, y + bh / 2, 16, hov ? C_BRASS_HI : 0xFFE3C88Au, 1.5f);
        text(names[i], x + 30, y, bw - 32, bh, 13, 0, 1, hov ? C_BRASS_HI : C_TEXT, GP_ALIGN_NEAR, GP_ALIGN_CENTER);
        if (i == 5 && s->binfo > 0) {                    /* (user 10-29 20:47) unread battle reports: light flowing */
            float per = 2 * (bw + bh), ph = (float)(GetTickCount() % 1600) / 1600.0f * per;   /* around the border */
            float pulse = 0.5f + 0.5f * sinf((float)(GetTickCount() % 1200) / 1200.0f * 6.2832f);
            stroke_rect(x + 0.5f, y + 0.5f, bw - 1, bh - 1, alpha(0xFFFFD98Au, 0.35f + 0.45f * pulse), 1.6f);
            for (int k2 = 0; k2 < 2; k2++) {             /* two runs, opposite sides */
                float st = ph + k2 * per / 2;
                for (int q = 0; q < 22; q++) {
                    float d = fmodf(st - q * 2.5f + 2 * per, per), px0, py0;
                    if (d < bw) { px0 = x + d; py0 = y; }
                    else if (d < bw + bh) { px0 = x + bw; py0 = y + d - bw; }
                    else if (d < 2 * bw + bh) { px0 = x + bw - (d - bw - bh); py0 = y + bh; }
                    else { px0 = x; py0 = y + bh - (d - 2 * bw - bh); }
                    fill_circle(px0, py0, 2.8f - q * 0.1f, (ARGB)((unsigned)(240 - q * 10) << 24) | 0x00FFE7A8u);
                }
            }
            WCHAR nb[8]; swprintf(nb, 8, L"%d", s->binfo > 99 ? 99 : s->binfo);
            fill_circle(x + bw - 4, y + 2, 9, 0xFFE07A3Au);
            text(nb, x + bw - 13, y - 7, 18, 18, 11, 1, 1, 0xFFFFFFFFu, GP_ALIGN_CENTER, GP_ALIGN_CENTER);
        }
        if (s->replay) fill_rect(x, y, bw, bh, 0xA00A1016u); else hit_add(x, y, bw, bh, 0, H_WHEEL, i);
    }
    if (!unit) return;

    /* selected unit */
    float uh = uph, uy = uy0, ux1 = ux0 + uw;
    if (occluded(ux0, uy, uw, uh)) return;
    panel_bg(ux0, uy, uw, uh);
    ux0 += 4; ux1 -= 4; uy += 6; uh -= 10;
    if (!s->nsel) {
        text(T3("No unit selected - click a unit or a squad card", "未选中单位 · 点击地图上的单位或左侧分队卡",
                "未選中單位 · 點擊地圖上的單位或左側分隊卡"), ux0, uy, ux1 - ux0, uh, 15, 0, 0, C_MUTED, GP_ALIGN_CENTER, GP_ALIGN_CENTER);
        return;
    }
    HudUnit *u = &s->sel;
    float pr = uh > 180 ? 40 : uh * 0.30f, pcx = ux0 + 18 + pr, pcy = uh > 180 ? uy + 70 : uy + uh / 2;
    fill_circle(pcx, pcy, pr, 0xFF121A20u);
    stroke_circle(pcx, pcy, pr, 0x99C9A45Cu, 1.6f);
    stroke_circle(pcx, pcy, pr - 6, 0x40C9A45Cu, 1);
    icon(unit_icon(u), pcx, pcy, pr * 1.0f, unit_color(u), 1.4f);
    float ix = pcx + pr + 14, iw = uh > 180 ? 1000 : 160;
    if (ix + iw > ux1 - 8) iw = ux1 - 8 - ix;
    text(u->name, ix, uy + 10, iw, 30, 22, 1, 1, C_BRASS_HI, GP_ALIGN_NEAR, GP_ALIGN_CENTER);
    WCHAR sub[64];
    if (s->nsel > 1) swprintf(sub, 64, L"%ls  ·  %ls %d", unit_class(u), T3("selected", "已选", "已選"), s->nsel);
    else swprintf(sub, 64, L"%ls", unit_class(u));
    text(sub, ix, uy + 40, iw, 20, 13, 0, 1, unit_color(u), GP_ALIGN_NEAR, GP_ALIGN_CENTER);
    float frac = u->hpmax > 0 ? (float)u->hp / u->hpmax : 0;
    WCHAR v[32];
    text(T3("HP", "生命", "生命"), ix, uy + 66, 40, 16, 12, 0, 0, C_MUTED, GP_ALIGN_NEAR, GP_ALIGN_CENTER);
    bar(ix + 40, uy + 70, iw - 40, 8, frac, frac < 0.35f ? C_EMBER : C_HP);
    swprintf(v, 32, L"%d / %d", u->hp, u->hpmax);
    text(v, ix + 40, uy + 80, iw - 40, 16, 12, 1, 0, C_TEXT, GP_ALIGN_FAR, GP_ALIGN_CENTER);
    text(T3("EN", "能量", "能量"), ix, uy + 100, 40, 16, 12, 0, 0, C_MUTED, GP_ALIGN_NEAR, GP_ALIGN_CENTER);
    bar(ix + 40, uy + 104, iw - 40, 8, u->enmax > 0 ? (float)u->en / u->enmax : 0, C_ENERGY);
    swprintf(v, 32, L"%d / %d", u->en, u->enmax);
    text(v, ix + 40, uy + 114, iw - 40, 16, 12, 1, 0, C_TEXT, GP_ALIGN_FAR, GP_ALIGN_CENTER);
    /* commands: up to 8 round buttons with their hotkey - right of the unit's bars, or under them when narrow */
    float cx0 = ix + iw + 22, cw = ux1 - 12 - cx0, top = uy, area_h = uh;
    int nc = 0; for (int i = 0; i < 8; i++) if (s->cmd[i] != -1) nc++;
    if (!nc) return;
    int below = uh > 180 && cw < 200;
    if (below) { cx0 = ix - 8; cw = ux1 - 12 - cx0; top = uy + 128; area_h = uh - 128; }
    else line(cx0 - 12, uy + 14, cx0 - 12, uy + uh - 14, 0x50C9A45Cu, 1);
    int cols = (below || nc <= 4) ? nc : (nc + 1) / 2, rows = (below || nc <= 4) ? 1 : 2;
    float cell = cw / cols; if (cell > 86) cell = 86;
    float rr = cell * 0.30f; if (rr > 23) rr = 23;
    if (rows == 2 && rr > (area_h / 2 - 22) / 2) rr = (area_h / 2 - 22) / 2;
    if (below && rr > (area_h - 22) / 2) rr = (area_h - 22) / 2;
    if (rr < 8) return;
    float rowh = area_h / rows;
    uy = top; uh = area_h;
    int k = 0;
    for (int i = 0; i < 8; i++) {
        int id = s->cmd[i];
        if (id == -1) continue;
        int col = k % cols, row = k / cols; k++;
        float bx = cx0 + cell * col + cell / 2, by = uy + rowh * row + rowh / 2 - 8;
        /* user 10-28 23:41 "a pressed skill must turn solid": solid = waiting for its target, an active toggle (the
           button already shows its stop / undo command), or just clicked (0.6 s) */
        int act = id == 5 || id == 7 || id == 36 || id == 43 || id == 48 || id == 52 || id == 56 || id == 58 || id == 61 || id == 63;
        int flash = g_cmd_flash_slot == i && GetTickCount() - g_cmd_flash_t < 600;
        int tg = s->cmd_tg[i];                               /* a toggle skill: 2 on, 1 some units on */
        if (tg == 2) act = 1;
        int hov = hovered(H_CMD, i), on = s->cmd_on == i || act || flash;
        fill_circle(bx, by, rr, on ? C_BRASS_HI : 0xFF121A20u);
        if (on) stroke_circle(bx, by, rr + 4, 0xC0F4E2B4u, 1.6f);
        else if (tg == 1) stroke_circle(bx, by, rr + 4, 0xA0F4E2B4u, 1.2f);   /* part of the selection: a ring only */
        /* (user 11-02 13:32 "no 开 tag - the button's look changing is enough") an active toggle is shown only by the
           solid button (filled brass, dark icon, outer ring), like a pressed skill */
        stroke_circle(bx, by, rr, hov || on ? C_BRASS_HI : C_BRASS, hov || on ? 2.2f : 1.6f);
        icon(cmd_icon(id), bx, by, rr * 1.15f, on ? 0xFF1A1408u : hov ? C_BRASS_HI : 0xFFE3C88Au, on ? 2.0f : 1.6f);
        char hk = cmd_hotkey(id);
        if (hk) {
            WCHAR h2[2] = { (WCHAR)hk, 0 };
            float kx = bx + rr * 0.72f, ky = by + rr * 0.72f;
            fill_circle(kx, ky, 9, 0xFF0B1014u);
            stroke_circle(kx, ky, 9, C_BRASS, 1);
            text(h2, kx - 9, ky - 9, 18, 18, 10, 1, 1, C_BRASS_HI, GP_ALIGN_CENTER, GP_ALIGN_CENTER);
        }
        WCHAR lab[24];
        if (id >= 0 && id < 74) lstrcpynW(lab, g_lang == 1 ? CMD_CN[id] : g_lang == 2 ? CMD_TW[id] : L"", 24);
        else lab[0] = 0;
        if (!lab[0] && id >= 0 && id < 74) MultiByteToWideChar(CP_ACP, 0, CMD_EN[id], -1, lab, 24);
        text(lab, bx - cell / 2, by + rr + 2, cell, 16, 11, 0, 0, hov ? C_BRASS_HI : C_MUTED, GP_ALIGN_CENTER, GP_ALIGN_NEAR);
        if (s->replay) fill_circle(bx, by, rr, 0xA00A1016u); else hit_add(bx - rr, by - rr, 2 * rr, 2 * rr, 1, H_CMD, i);
    }
}

/* the re-skinned game windows: glass is in the frame already (skin_qm_draw); here the frame line, the buttons */
static ARGB rgb565(unsigned short v)
{
    unsigned r = v >> 11, g = (v >> 5) & 63, b = v & 31;
    return 0xFF000000u | ((r * 255 / 31) << 16) | ((g * 255 / 63) << 8) | (b * 255 / 31);
}
static void paint_report(float bx, float by);
static void rank_frame(float x0, float y0, float x1, float y1, int tier, int reinc); static int rank_tier(int rank); static void insignia(float cx, float cy, float s, int rank);
static float g_rep_anim = 1; static int g_rep_tier, g_rep_reinc;   /* (17:44 / 17:47) growth animation 0..1, frame tier */
static void paint_userinfo(float bx, float by, int other);
static int g_skin_sel = -1;                     /* layers: -1 everything, 0..7 that window only, 100 the controls only */
static void paint_skin(void)
{
    HudState *s = &g_ps;
    for (int i = 0; i < s->nskw; i++) {
        if (g_skin_sel == 100 || (g_skin_sel >= 0 && g_skin_sel != i)) continue;
        HudSkinWnd *w = &s->skw[i];
        float x0 = fx_ref(w->x0), y0 = fy_ref(w->y0), x1 = fx_ref(w->x1), y1 = fy_ref(w->y1);
        int art = w->def < sizeof SKIN_WINS / sizeof *SKIN_WINS && SKIN_WINS[w->def].art;
        if (!art) {
            stroke_rect(x0 + 0.5f, y0 + 0.5f, x1 - x0 - 1, y1 - y0 - 1, 0xA0C9A45Cu, 1.2f);
            line(x0 + 6, y0 + 4.5f, x1 - 6, y0 + 4.5f, 0x40C9A45Cu, 1);
            diamond((x0 + x1) / 2, y0 + 1, 5, C_BRASS);
        }
        if (w->def < sizeof SKIN_WINS / sizeof *SKIN_WINS && SKIN_WINS[w->def].art) {   /* art windows: their own decor */
            const SkinWin *d = &SKIN_WINS[w->def];
            float bx = (float)w->x0, by = (float)w->y0;
            /* the window frame itself is not drawn (the box decor is the visible panel) */
            for (int j = 0; j < d->ndecor; j++) {
                const SkinDecor *c = &d->decor[j];
                float a0 = fx_ref(bx + c->x0), b0 = fy_ref(by + c->y0), a1 = fx_ref(bx + c->x1), b1 = fy_ref(by + c->y1);
                const WCHAR *lab = c->en ? (g_lang == 1 ? c->cn : g_lang == 2 ? c->tw : c->en) : NULL;
                if (c->kind == DC_BOX) {
                    stroke_rect(a0 + 0.5f, b0 + 0.5f, a1 - a0 - 1, b1 - b0 - 1, 0xC0C9A45Cu, 1.3f);
                    line(a0 + 6, b0 + 4.5f, a1 - 6, b0 + 4.5f, 0x40C9A45Cu, 1);
                    diamond((a0 + a1) / 2, b0 + 1, 5, C_BRASS);
                } else if (c->kind == DC_HEAD) {
                    fill_rect(a0, b0, a1 - a0, b1 - b0, 0x28C9A45Cu);
                    line(a0, b1 - 0.5f, a1, b1 - 0.5f, 0x90C9A45Cu, 1);
                    if (lab) text(lab, a0 + 2, b0, a1 - a0 - 4, b1 - b0, 13, 0, 1, C_BRASS_HI, GP_ALIGN_CENTER, GP_ALIGN_CENTER);
                } else if (c->kind == DC_FIELD) {       /* an input field (its text is the game's control) */
                    stroke_rect(a0 + 0.5f, b0 + 0.5f, a1 - a0 - 1, b1 - b0 - 1, 0x90C9A45Cu, 1.0f);
                } else if (c->kind == DC_TITLE) {
                    if (lab) text(lab, a0, b0, a1 - a0, b1 - b0, 16, 0, 1, C_BRASS_HI, GP_ALIGN_NEAR, GP_ALIGN_CENTER);
                    line(a0, b1 - 1, a0 + 60, b1 - 1, C_BRASS, 1.6f);
                } else if (c->kind == DC_NOTE) {
                    if (lab) text(lab, a0, b0, a1 - a0, b1 - b0, 14, 0, 0, C_TEXT, GP_ALIGN_NEAR, GP_ALIGN_CENTER);
                } else if (c->kind == DC_LABEL) {
                    if (lab) text(lab, a0, b0, a1 - a0, b1 - b0, 13, 0, 1, C_BRASS_HI, GP_ALIGN_FAR, GP_ALIGN_CENTER);
                } else if (c->kind == DC_TAB) {
                    int on = (j == 1 && !w->page) || (j == 2 && w->page);
                    fill_rect(a0 + 2, b0, a1 - a0 - 4, b1 - b0, on ? 0xE0201A10u : 0xA00A1016u);
                    stroke_rect(a0 + 2.5f, b0 + 0.5f, a1 - a0 - 5, b1 - b0 - 1, on ? C_BRASS_HI : 0x80C9A45Cu, on ? 1.6f : 1.0f);
                    if (lab) text(lab, a0 + 2, b0, a1 - a0 - 4, b1 - b0, 13, 0, 1, on ? C_BRASS_HI : C_MUTED, GP_ALIGN_CENTER, GP_ALIGN_CENTER);
                    hit_add(a0 + 2, b0, a1 - a0 - 4, b1 - b0, 0, H_PASS, 1000 + j);
                }
            }
            hit_add(x0, y0, x1 - x0, y1 - y0, 0, H_PASS, -1);
            if (!strcmp(d->cls, "CBattleResultWnd")) paint_report(bx, by);   /* (17:12) after: its medals take the hover */
            if (!strcmp(d->cls, "CUserInfoWnd")) paint_userinfo(bx, by, 0);
            if (!strcmp(d->cls, "CUserInfoWnd#other")) paint_userinfo(bx, by, 1);   /* (11-01 14:17) another commander */
            continue;
        }
        if (w->title[0]) {
            text(w->title, x0 + 14, y0 + 8, x1 - x0 - 28, 30, 16, 0, 1, C_BRASS_HI, GP_ALIGN_NEAR, GP_ALIGN_CENTER);
            line(x0 + 14, y0 + 40, x0 + 74, y0 + 40, C_BRASS, 1.6f);
        }
        hit_add(x0, y0, x1 - x0, y1 - y0, 0, H_PASS, -1);
    }
    if (g_skin_sel >= 0 && g_skin_sel != 100) return;
    for (int i = 0; i < s->nsk; i++) {
        HudSkin *e = &s->sk[i];
        float x0 = fx_ref(e->x0), y0 = fy_ref(e->y0), x1 = fx_ref(e->x1), y1 = fy_ref(e->y1), w = x1 - x0, h = y1 - y0;
        int hov = hovered(H_PASS, i);
        if (e->kind == SK_TEXT) {                        /* list entry: its own colour */
            if (hov) fill_rect(x0, y0, w, h, 0x30F4E2B4u);
            text(e->label, x0 + 4, y0, w - 6, h, 13, 0, 0, rgb565(e->color), GP_ALIGN_NEAR, GP_ALIGN_CENTER);
        } else if ((e->kind == SK_TAB_ON && e->accent) || (e->kind == SK_TAB && e->accent == 2)) {   /* a strip of page tabs */
            int on = e->kind == SK_TAB_ON;
            fill_rect(x0 + 2, y0, w - 4, h, on ? 0xE0201A10u : hov ? 0xD0161410u : 0xA00A1016u);
            stroke_rect(x0 + 2.5f, y0 + 0.5f, w - 5, h - 1, on ? C_BRASS_HI : hov ? C_BRASS : 0x80C9A45Cu, on ? 1.6f : 1.0f);
            if (on) line(x0 + 8, y1 - 2, x1 - 8, y1 - 2, C_BRASS, 1.6f);
            text(e->label, x0 + 2, y0, w - 4, h, 13, 0, 1, on ? C_BRASS_HI : hov ? C_BRASS_HI : C_MUTED, GP_ALIGN_CENTER, GP_ALIGN_CENTER);
        } else if (e->kind == SK_TAB_ON) {
            text(e->label, x0, y0, w + 40, h, 15, 0, 1, C_BRASS_HI, GP_ALIGN_NEAR, GP_ALIGN_CENTER);
            line(x0, y1 - 1, x0 + 60, y1 - 1, C_BRASS, 1.6f);
        } else if (e->kind == SK_TAB) {
            text(e->label, x0, y0, w, h, 13, 0, 1, hov ? C_BRASS_HI : C_MUTED, GP_ALIGN_FAR, GP_ALIGN_CENTER);
        } else if (e->kind == SK_HEAD) {                 /* a column title (sorts the list when clicked) */
            fill_rect(x0, y0, w, h, hov ? 0x48C9A45Cu : 0x28C9A45Cu);
            line(x0, y1 - 0.5f, x1, y1 - 0.5f, 0x90C9A45Cu, 1);
            text(e->label, x0 + 2, y0, w - 4, h, 13, 0, 1, C_BRASS_HI, GP_ALIGN_CENTER, GP_ALIGN_CENTER);
        } else if (e->kind == SK_RADIO) {                /* one of a group: the chosen one lit */
            fill_rect(x0 + 1, y0 + 1, w - 2, h - 2, e->accent ? 0xF0263018u : hov ? 0xF0201A10u : 0xC00A1016u);
            stroke_rect(x0 + 1.5f, y0 + 1.5f, w - 3, h - 3, e->accent ? 0xFF9CCB7Au : hov ? C_BRASS_HI : 0x90C9A45Cu, e->accent ? 1.8f : 1.1f);
            if (e->accent) fill_circle(x0 + 12, (y0 + y1) / 2, 4, 0xFF9CCB7Au);
            text(e->label, x0 + 4, y0, w - 8, h, 13, 0, 1, e->accent ? 0xFFCDEBB0u : hov ? C_BRASS_HI : C_TEXT, GP_ALIGN_CENTER, GP_ALIGN_CENTER);
        } else {
            int cl = e->kind == SK_CLOSE;
            fill_rect(x0 + 1, y0 + 1, w - 2, h - 2, hov ? 0xF0201A10u : 0xC00A1016u);
            stroke_rect(x0 + 1.5f, y0 + 1.5f, w - 3, h - 3, cl ? (hov ? 0xFFF2A06Au : 0xC0E07A3Au) : (hov ? C_BRASS_HI : 0x90C9A45Cu), hov ? 1.6f : 1.1f);
            text(e->label, x0 + 4, y0, w - 8, h, 13, 0, 1, cl ? 0xFFF2A06Au : hov ? C_BRASS_HI : C_TEXT, GP_ALIGN_CENTER, GP_ALIGN_CENTER);
        }
        hit_add(x0, y0, w, h, 0, H_PASS, i);
    }
}
