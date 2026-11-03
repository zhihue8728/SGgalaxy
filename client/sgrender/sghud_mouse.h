/* sghud_mouse.h - part of sghud.c (included in this order; not a header on its own): the mouse (window procedure, client pixels) and the exported entry points */
/* ---- mouse (window procedure, client pixels) ------------------------------------------------------------------- */
static Hit g_hit_found;
static const Hit *hit_at(int x, int y)
{
    if (!g_thr) return NULL;
    const Hit *res = NULL;
    g_hole_hit = 0;
    EnterCriticalSection(&g_lock);
    for (int i = g_nhit - 1; i >= 0; i--) {   /* last drawn = on top */
        const Hit *h = &g_hits[i];
        if (x < h->r.left || x >= h->r.right || y < h->r.top || y >= h->r.bottom) continue;
        if (h->circle) {
            float cx = (h->r.left + h->r.right) / 2.0f, cy = (h->r.top + h->r.bottom) / 2.0f, r = (h->r.right - h->r.left) / 2.0f;
            if ((x - cx) * (x - cx) + (y - cy) * (y - cy) > r * r) continue;
        }
        if (h->kind != H_HOLE) { g_hit_found = *h; res = &g_hit_found; }
        else g_hole_hit = h->arg;
        break;
    }
    LeaveCriticalSection(&g_lock);
    return res;
}

int sghud_over(int x, int y) { return g_on > 0 && (g_st.lg || (g_st.active && hit_at(x, y) != NULL)); }   /* login: the whole screen */   /* covered: hits = skins only */

/* radar point -> the old minimap's own coordinates (relative to the hidden panel) */
static int radar_to_panel(int x, int y, int *px, int *py)
{
    EnterCriticalSection(&g_lock);
    Ctx c = g_pubC; float rcx = g_rad_cx, rcy = g_rad_cy, rr = g_rad_r; int mw = g_pub_mapw, mh = g_pub_maph;
    LeaveCriticalSection(&g_lock);
    if (!rr || !rd(g_panel, 0xa100) || mw <= 0 || mh <= 0) return 0;
    float rx = (x - c.ox) / c.s, ry = (y - c.oy) / c.s;
    float side = rr * 1.414f, k = side / (float)(mw > mh ? mw : mh);
    float ox = rcx - side / 2 + (side - mw * k) / 2, oy = rcy - side / 2 + (side - mh * k) / 2;
    float u = (rx - ox) / (mw * k), v = (ry - oy) / (mh * k);
    if (u < 0) u = 0; if (u > 0.999f) u = 0.999f; if (v < 0) v = 0; if (v > 0.999f) v = 0.999f;
    const int *mm = (const int *)(g_panel + 0xa0cc);   /* the old minimap's rect in the panel: left, top, right, bottom */
    *px = mm[0] + (int)(u * (mm[2] - mm[0]));
    *py = mm[1] + (int)(v * (mm[3] - mm[1]));
    return 1;
}

static int g_cap_kind, g_cap_arg;
/* keys (game thread): Enter opens a folded chat (the game's input is in it) and starts / ends typing */
void sghud_key(UINT m, WPARAM w)
{
    if (g_on <= 0) return;
    if (m == WM_KEYDOWN && w == VK_RETURN) {
        g_chat_typing = !g_chat_typing;
        if (!g_chat_open) { g_chat_open = 1; g_dirty = 1; if (g_chat_hid && rd(g_chat, 0x160)) { g_chat[0x155] = 1; g_chat_hid = 0; } }
    } else if (m == WM_KEYDOWN && w == VK_ESCAPE) g_chat_typing = 0;
    if (g_chat_typing || (m == WM_KEYDOWN && w == VK_RETURN)) g_chat_touch = GetTickCount();
}

/* the login screen: every mouse message goes to the game, at the control under the new look's item (or nowhere) */
static int g_mgx, g_mgy;                         /* frame pixels for the game (return 3) */
static int g_lg_pend_kind, g_lg_pend_arg; static DWORD g_lg_pend_t;
void sghud_mapped(int *gx, int *gy) { *gx = g_mgx; *gy = g_mgy; }
static void lg_target(const short *r, int end) { g_mgx = end ? r[2] - 3 : (r[0] + r[2]) / 2; g_mgy = (r[1] + r[3]) / 2; }
static int g_osl_drag; static RECT g_osl_r;      /* a volume dragged (1 + track) and its hit rectangle */
static int login_mouse(UINT m, int x, int y)
{
    HudState *s = &g_st;
    const Hit *h = hit_at(x, y);
    int kind = h ? h->kind : H_NONE, arg = h ? h->arg : 0;
    if (s->lg == LG_OPTION && (g_osl_drag || (kind == H_LOSL && m == WM_LBUTTONDOWN))) {
        /* (11-01) the volume: the mouse's place along the new track = the same place along the game's, while held */
        if (!g_osl_drag) { g_osl_drag = 1 + arg; g_osl_r = h->r; }
        int j = g_osl_drag - 1;
        float pad = 10 * g_pubC.s, l = g_osl_r.left + pad, r = g_osl_r.right - pad;   /* the hit is the track + 10 each side */
        float u = r > l ? (x - l) / (r - l) : 0;
        if (u < 0) u = 0; if (u > 1) u = 1;
        g_mgx = s->lg_osl[j][0] + (int)(u * (s->lg_osl[j][2] - s->lg_osl[j][0]) + 0.5f); g_mgy = s->lg_osl[j][1];
        if (m == WM_LBUTTONUP) g_osl_drag = 0;
        if (m == WM_MOUSEMOVE && (kind != g_hover_kind || arg != g_hover_arg)) { g_hover_kind = kind; g_hover_arg = arg; g_dirty = 1; }
        g_dirty = 1;
        return 3;
    }
    if (m == WM_MOUSEMOVE && (kind != g_hover_kind || arg != g_hover_arg)) { g_hover_kind = kind; g_hover_arg = arg; g_dirty = 1; }
    g_mgx = 2; g_mgy = 2;                         /* outside the 800-wide setup screen: nothing there */
    if (s->lg_game) { g_mgx = s->lg_odead[0]; g_mgy = s->lg_odead[1]; }   /* (11-01) in the game: the options' own edge, not the map */
    int form = s->lg == LG_CONT || s->lg == LG_CREATE || s->lg == LG_CHPW;
    if (kind == H_LMENU && s->lg == LG_MAIN && arg >= 0 && arg < 6) lg_target(s->lg_btn[arg], 0);
    else if (kind == H_LFIELD && arg >= 0 && arg < 4 && s->lg != LG_OPTION) {
        if (form && arg < s->lg_nf) lg_target(s->lg_ed[arg], 1);   /* the edit's right end: the caret goes behind the text */
        else if (s->lg == LG_NATION && s->lg_fr && arg == 0) lg_target(s->lg_fred, 1);
        else if (s->lg == LG_MAIN) lg_target(s->lg_btn[1], 0);  /* main menu: CONTINUE opens the dialog first */
    } else if (kind == H_LBTN && arg >= 0 && arg < 3) {
        if (s->lg == LG_HERO) lg_target(arg ? s->lg_nav[arg - 1] : s->lg_hsel, 0);
        else if (s->lg == LG_NATION) lg_target(arg ? s->lg_nav[arg - 1] : s->lg_nsel, 0);
        else if ((form || s->lg == LG_BRIEF) && arg < s->lg_nb) lg_target(s->lg_bt[arg], 0);
        else if (s->lg == LG_MAIN && arg < 2) lg_target(s->lg_btn[1], 0);
    } else if (kind == H_LROW && s->lg == LG_BRIEF && arg >= 0 && arg < s->lg_nrow) {
        g_mgx = s->lg_row[0] + 40; g_mgy = s->lg_row[1] + s->lg_row[3] * arg + s->lg_row[3] / 2;
    } else if (kind == H_LQ && s->lg_qon) lg_target(s->lg_q, 0);
    else if (kind == H_LOPT && s->lg == LG_OPTION && arg >= 0 && arg < OPT_N && s->lg_ot[arg][2] > s->lg_ot[arg][0]) lg_target(s->lg_ot[arg], 0);
    else if (kind == H_LFIELD && s->lg == LG_OPTION && arg >= 0 && arg < 10) lg_target(g_mac_ed[arg], 1);
    else if (kind == H_LPASS && s->lg == LG_OPTION) return 0;   /* the colour picker: the game's own mouse */
    else if (kind == H_LPASS && s->lg == LG_NATION) {
        return 0;                                   /* the live viewer: the game's own mouse */
    } else if (kind == H_LTAB && s->lg == LG_NATION && arg >= 0 && arg < 3) lg_target(s->lg_ntab[arg], 0);
    else if (kind == H_LFR && s->lg == LG_NATION && arg >= 0 && arg < 2) lg_target(s->lg_frbt[arg], 0);
    else if (kind == H_LHERO && s->lg == LG_HERO && arg >= 0 && arg < 9) lg_target(s->lg_hbtn[arg], 0);
    else if (kind == H_LSTAT && s->lg == LG_HERO && arg >= 0 && arg < 8) lg_target(s->lg_spin[arg / 2][arg & 1], 0);
    else if (kind == H_LSCR && s->lg == LG_BRIEF && s->lg_scr[2] > s->lg_scr[0]) {
        g_mgx = (s->lg_scr[0] + s->lg_scr[2]) / 2; g_mgy = arg ? s->lg_scr[3] - 5 : s->lg_scr[1] + 5;
    }
    if (m != WM_MOUSEMOVE && sgr_debug()) sgr_log("LOGIN mouse %x hit %d/%d -> game %d,%d (lg %d)", m, kind, arg, g_mgx, g_mgy, s->lg);
    /* a field / CHANGE PASSWORD clicked on the main menu: the click is repeated once the dialog is up */
    if (m == WM_LBUTTONUP && s->lg == LG_MAIN && (kind == H_LFIELD || (kind == H_LBTN && arg == 1))) {
        g_lg_pend_kind = kind; g_lg_pend_arg = arg; g_lg_pend_t = GetTickCount();
    }
    return 3;
}
static void login_pending(void)                  /* game thread, frame start */
{
    if (!g_lg_pend_kind) return;
    if (GetTickCount() - g_lg_pend_t > 4000 || !g_st.lg) { g_lg_pend_kind = 0; return; }
    if (g_st.lg != LG_CONT || g_pub_lg != LG_CONT) return;
    int cx = -1, cy = -1;
    EnterCriticalSection(&g_lock);
    for (int i = 0; i < g_nhit; i++)
        if (g_hits[i].kind == g_lg_pend_kind && g_hits[i].arg == g_lg_pend_arg) {
            cx = (g_hits[i].r.left + g_hits[i].r.right) / 2; cy = (g_hits[i].r.top + g_hits[i].r.bottom) / 2;
        }
    LeaveCriticalSection(&g_lock);
    g_lg_pend_kind = 0;
    if (cx < 0) return;
    PostMessageA(g_disp.hwnd, WM_LBUTTONDOWN, MK_LBUTTON, MAKELPARAM(cx, cy));
    PostMessageA(g_disp.hwnd, WM_LBUTTONUP, 0, MAKELPARAM(cx, cy));
}

int sghud_mouse(UINT m, int x, int y, WPARAM w)
{
    if (g_on > 0 && g_st.lg) { g_cap_kind = 0; return login_mouse(m, x, y); }
    if (g_on <= 0 || !g_st.active) { g_cap_kind = 0; return 0; }
    const Hit *h = hit_at(x, y);
    if (m != WM_MOUSEMOVE && sgr_debug()) sgr_log("HUD mouse %x at %d,%d -> %d/%d (hits %d)", m, x, y, h ? h->kind : 0, h ? h->arg : 0, g_nhit);
    int kind = h ? h->kind : H_NONE, arg = h ? h->arg : 0;
    if (m == WM_MOUSEMOVE && (kind != g_hover_kind || arg != g_hover_arg)) { g_hover_kind = kind; g_hover_arg = arg; g_dirty = 1; }
    if (kind == H_PASS && !g_cap_kind) return 0;        /* a re-skinned game window: the game handles the mouse */
    if (m == WM_MOUSEMOVE) {
        if (kind == H_CHATBG || kind == H_CHAT || g_hole_hit == 1) g_chat_touch = GetTickCount();
        if (kind == H_CHAT && arg == 2 && !g_chat_pin && !g_chat_open) { g_chat_open = 1; g_dirty = 1; }   /* hover opens */
        if (g_cap_kind == H_RADAR && (w & MK_LBUTTON)) {
            int px, py; if (radar_to_panel(x, y, &px, &py)) queue(H_RADAR, 0, 0x200, px, py, 1);
            return 1;
        }
        /* over the HUD the game still gets the move (its cursor follows instead of freezing at the HUD's edge -
           user 10-28 21:15 "the mouse sticks over the HUD"), kept off the frame edges so the map does not scroll */
        return g_cap_kind != 0 ? 1 : h != NULL ? 2 : 0;
    }
    int down = m == WM_LBUTTONDOWN || m == WM_RBUTTONDOWN || m == WM_LBUTTONDBLCLK || m == WM_RBUTTONDBLCLK ||
               m == WM_MBUTTONDOWN || m == WM_MBUTTONDBLCLK;
    int up = m == WM_LBUTTONUP || m == WM_RBUTTONUP || m == WM_MBUTTONUP;
    if (down) {
        if (!h) return 0;
        g_cap_kind = kind; g_cap_arg = arg;
        if (kind == H_RADAR) {
            int px, py;
            if (radar_to_panel(x, y, &px, &py)) {
                if (m == WM_RBUTTONDOWN || m == WM_RBUTTONDBLCLK) queue(H_RADAR, 0, 0x204, px, py, 0);
                else if (m == WM_LBUTTONDOWN || m == WM_LBUTTONDBLCLK) queue(H_RADAR, 0, 0x201, px, py, 1);
            }
        }
        return 1;
    }
    if (up) {
        if (!g_cap_kind) return 0;
        int ck = g_cap_kind, ca = g_cap_arg;
        g_cap_kind = 0;
        if (ck == H_RADAR) {
            int px, py; if (m == WM_LBUTTONUP && radar_to_panel(x, y, &px, &py)) queue(H_RADAR, 0, 0x202, px, py, 0);
        } else if (m == WM_LBUTTONUP && kind == ck && arg == ca && ck == H_CHAT) {
            if (ca >= 10 && ca <= 12) queue(H_CHAT, ca - 10, 0, 0, 0, 0);   /* send mode, on the game thread */
            else if (ca == 0) g_chat_open = 0;
            else if (ca == 1) {
                g_chat_pin = !g_chat_pin; g_chat_open = 1;
                WritePrivateProfileStringA("hud", "chat_pin", g_chat_pin ? "1" : "0", ".\\GORender.ini");
            } else g_chat_open = 1;
            g_chat_touch = GetTickCount(); g_dirty = 1;
        } else if (m == WM_LBUTTONUP && kind == ck && arg == ca && (ck == H_HONOR || ck == H_HONCL || ck == H_HONTAB || ck == H_HONPG || ck == H_HONROW || ck == H_HONBACK)) {
            if (ck == H_HONOR) { g_hon_open = !g_hon_open; g_hon_sel = -1; if (g_hon_open) { g_hon_page = 0; hon_fetch_start(); } }
            else if (ck == H_HONCL) { g_hon_open = 0; g_hon_sel = -1; }
            else if (ck == H_HONTAB) { g_hon_tab = ca; g_hon_page = 0; g_hon_sel = -1; }
            else if (ck == H_HONROW) g_hon_sel = ca;
            else if (ck == H_HONBACK) g_hon_sel = -1;
            else g_hon_page += ca ? 1 : -1;
            if (g_hon_page < 0) g_hon_page = 0;
            g_dirty = 1;
        } else if (m == WM_LBUTTONUP && kind == ck && arg == ca && (ck == H_CARD || ck == H_CMD || ck == H_WHEEL))
        {
            queue(ck, ca, 0, 0, 0, (int)(w & MK_SHIFT));
            if (ck == H_CMD) { g_cmd_flash_slot = ca; g_cmd_flash_t = GetTickCount(); g_dirty = 1; }
        }
        return 1;
    }
    return 0;
}

/* debug: the old panel's sprites + the map objects (SGRender_spr.req) */
static void dump_spr_f(const char *tag, char *sp, int fi);
static void dump_spr(const char *tag, char *sp) { dump_spr_f(tag, sp, 0); }
static void dump_spr_f(const char *tag, char *sp, int fi)
{
    if (!rd(sp, 0x50)) return;
    unsigned char *b = (unsigned char *)sp; char hx[0x50 * 3 + 1];
    for (int i = 0; i < 0x50; i++) sprintf(hx + i * 3, "%02x ", b[i]);
    sgr_log("SPR %s %p: %s", tag, sp, hx);
    int w = *(unsigned short *)(sp + 6), h = *(unsigned short *)(sp + 8);
    char *ft = *(char **)(sp + 0x44) + fi * 0x28;
    if (!rd(ft, 0x28) || w <= 0 || h <= 0 || w > 2048 || h > 2048) return;
    unsigned short *px = *(unsigned short **)ft;
    sgr_log("SPR %s w %d h %d flags %02x frame0 px %p valid %d", tag, w, h, b[4], px, ft[0x26]);
    unsigned short *img = (unsigned short *)calloc(w * h, 2); if (!img) return;
    if (!(b[4] & 1)) { if (rd(px, w * h * 2)) memcpy(img, px, w * h * 2); }
    else if (rd(px, 2)) {                                   /* RLE: top, bottom; rows of (skip, n, n pixels) */
        unsigned char *q = (unsigned char *)px; int top = q[0], bot = q[1]; q += 2;
        for (int y = top; y < h - bot; y++) {
            int x = 0;
            while (x < w) {
                if (!rd(q, 2)) goto done;
                x += *q++; if (x >= w) break;
                int n = *q++; if (!rd(q, n * 2)) goto done;
                for (int i = 0; i < n && x + i < w; i++) img[y * w + x + i] = ((unsigned short *)q)[i];
                q += n * 2; x += n;
            }
        }
    }
done:;
    char fn[64]; sprintf(fn, "GORender_spr_%s.ppm", tag);
    FILE *o = fopen(fn, "wb"); if (o) {
        fprintf(o, "P6 %d %d 255\n", w, h);
        for (int i = 0; i < w * h; i++) { unsigned v = img[i]; unsigned char c[3] = { (v >> 11) << 3, ((v >> 5) & 63) << 2, (v & 31) << 3 }; fwrite(c, 1, 3, o); }
        fclose(o);
    }
    free(img);
}
void sghud_debug_spr(void)
{
    if (g_chat) {                                       /* the chat's sprites (vtable 0x64f628) */
        int sz = 0x4000; while (sz > 0x200 && !rd(g_chat, sz)) sz /= 2;
        sgr_log("SPR chat %p readable %x rel %d %d %d %d", g_chat, sz, ((int *)(g_chat + 0x128))[0], ((int *)(g_chat + 0x128))[1],
                ((int *)(g_chat + 0x128))[2], ((int *)(g_chat + 0x128))[3]);
        char **ck; int nck = wkids(g_chat, &ck);
        for (int i = 0; i < nck; i++) if (rd(ck[i], 0x160)) {
            int *rr = (int *)(ck[i] + 0x128);
            sgr_log("SPR chat kid %p %s '%s' rel %d %d %d %d vis %d", ck[i], sgr_class(ck[i]), ck[i] + 4, rr[0], rr[1], rr[2], rr[3], ck[i][0x155]);
            char **k2; int n2 = wkids(ck[i], &k2);
            for (int j = 0; j < n2; j++) if (rd(k2[j], 0x160)) { int *r2 = (int *)(k2[j] + 0x128);
                sgr_log("SPR   kid %p %s '%s' rel %d %d %d %d vis %d", k2[j], sgr_class(k2[j]), k2[j] + 4, r2[0], r2[1], r2[2], r2[3], k2[j][0x155]); }
        }
        for (int o = 0; o + 0x50 <= sz; o += 4)
            if (*(unsigned *)(g_chat + o) == 0x64f628u) { char t[16]; sprintf(t, "chat%x", o); dump_spr(t, g_chat + o); }
    }
    {   /* every visible sprite button under TC Main: its frame as SGRender_spr_<file>_<frame>.ppm (labels for skins) */
        char *stack[64]; int sp = 0;
        char *fw = G_FIELD ? G_FIELD + 4 : NULL;
        char *root = fw ? *(char **)(fw + 0x138) : NULL;   /* TC Main */
        if (rd(root, 0x160)) stack[sp++] = root;
        while (sp) {
            char *w = stack[--sp];
            char **k; int n = wkids(w, &k);
            for (int i = 0; i < n; i++) {
                char *b = k[i]; if (!rd(b, 0x400) || !b[0x155]) continue;
                if (sp < 64) stack[sp++] = b;
                char nm[64]; lstrcpynA(nm, b + 4, sizeof nm);
                int fi = 0; char file[32] = "";
                if (nm[0] == '@' && sscanf(nm, "@ %31s %d", file, &fi) == 2) {
                    char t[64]; sprintf(t, "%s_%d", file, fi);
                    char fb[96]; sprintf(fb, "GORender_btn_%s.bin", t);
                    FILE *bo = fopen(fb, "wb"); if (bo) { fwrite(b, 1, 0x400, bo); fclose(bo); }
                    char fn[96]; sprintf(fn, "GORender_spr_%s.ppm", t);
                    if (GetFileAttributesA(fn) != INVALID_FILE_ATTRIBUTES) continue;
                    for (int o = 0x160; o + 0x50 <= 0x400; o += 4)
                        if (*(unsigned *)(b + o) == 0x64f628u) { dump_spr_f(t, b + o, fi); break; }
                }
            }
        }
    }
    if (g_panel) {
        sgr_log("SPR panel %p minimap rect %d %d %d %d", g_panel, ((int *)(g_panel + 0xa0cc))[0], ((int *)(g_panel + 0xa0cc))[1],
                ((int *)(g_panel + 0xa0cc))[2], ((int *)(g_panel + 0xa0cc))[3]);
        dump_spr("9ce8", g_panel + 0x9ce8);
        dump_spr("9e34", g_panel + 0x9e34);
    }
    if (g_map) {
        char *L = *(char **)0xc34618;
        if (rd(L, 0x50)) {
            int *b0 = *(int **)(L + 0x48), *e0 = *(int **)(L + 0x4c);
            sgr_log("AREA list %p..%p map id %d", b0, e0, *(int *)(g_map + 0x3f4));
            for (int *r = b0; b0 && r + 11 <= e0 && rd(r, 0x2c); r += 11)
                sgr_log("AREA %d %d | %d %d %d %d | %d %d %d %d %d", r[0], r[1], r[2], r[3], r[4], r[5], r[6], r[7], r[8], r[9], r[10]);
        }
        sgr_log("SPR map scale %u off %d", *(unsigned *)(g_map + 0x1025fc), *(int *)(g_map + 0x102604));
        char *ob = *(char **)(g_map + 0x10255c), *oe = *(char **)(g_map + 0x102560);
        for (char *r = ob; ob && r + 0xc74 <= oe && rd(r, 0xc74); r += 0xc74) {
            int *q = (int *)r;
            sgr_log("OBJ type %d [1]%d tile %d,%d [4..13] %d %d %d %d %d %d %d %d %d %d max %d c50 %d", q[0], q[1], q[2], q[3],
                    q[4], q[5], q[6], q[7], q[8], q[9], q[10], q[11], q[12], q[13], q[0xe], r[0xc50]);
        }
    }
}
