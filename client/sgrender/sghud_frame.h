/* sghud_frame.h - part of sghud.c (included in this order; not a header on its own): actions queued by the mouse; the per-frame entry sghud_frame() (game thread) */
/* ---- actions (queued by the mouse, run at the next frame start) ------------------------------------------------ */
enum { H_NONE, H_SWALLOW, H_CARD, H_CMD, H_WHEEL, H_RADAR, H_HOLE, H_CHAT, H_CHATBG, H_PASS, H_LDEAD, H_LMENU, H_LFIELD, H_LBTN, H_LROW, H_LSCR, H_LHERO, H_LSTAT, H_LPASS, H_LTAB, H_LFR, H_LQ, H_HONOR, H_HONCL, H_HONTAB, H_HONPG, H_HONROW, H_HONBACK, H_MEDAL, H_UITIP, H_LOPT, H_LOSL };
typedef struct { int kind, arg, msg, x, y, flags; } HudAct;
static HudAct g_q[16]; static int g_nq;
static int g_cmd_flash_slot = -1; static DWORD g_cmd_flash_t;
static void queue(int kind, int arg, int msg, int x, int y, int flags)
{
    if (g_nq < 16) { HudAct a = { kind, arg, msg, x, y, flags }; g_q[g_nq++] = a; }
}

static void run_actions(void)
{
    for (int i = 0; i < g_nq; i++) {
        HudAct *a = &g_q[i];
        char *f = G_FIELD;
        if (sgr_debug()) sgr_log("HUD act kind %d arg %d msg %x %d,%d", a->kind, a->arg, a->msg, a->x, a->y);
        if (!rd(f, 0x29c40)) break;
        g_stage_game = a->kind == H_CARD ? "act card" : a->kind == H_CMD ? "act command" : a->kind == H_WHEEL ? "act wheel" : "act radar";
        if (a->kind == H_CARD) {
            /* select the card's unit the way a click on the unit does (map click 0049a570 -> 004b2820); the old card
               handler (005db230) goes through the roster slot table, which does not match the cards on this server */
            char *u = unit_by_id((unsigned)a->arg);
            if (u && u[0x69]) {
                if (a->flags & MK_SHIFT) {
                    if (unit_selected(u)) { ((sel1_fn)0x5c4ff0)(f + 0x29b3c, u); ((noarg_fn)0x4b1fd0)(f); }
                    else ((sel4_fn)0x4b2820)(f, u, 1, 0, 0);
                } else ((sel4_fn)0x4b2820)(f, u, 0, 0, 0);
                char *help = *(char **)0x6ba804;
                if (rd(help, 4)) ((slot_fn)0x51d1f0)(help, 0x1a);       /* the selection sound */
            }
        } else if (a->kind == H_CMD) {
            if (rd(g_cbw, 0x260) && a->arg >= 0 && a->arg < 8 && *(int *)(g_cbw + 0x21c + 4 * a->arg) != -1)
                ((slot_fn)0x428a70)(g_cbw, a->arg);
        } else if (a->kind == H_WHEEL) {
            if (a->arg >= 0 && a->arg < WHEEL_N && rd(g_panel, 0x160))
            {
                char *qm = a->arg == 9 && !f[0x29bdc] ? find_child(f + 4, "CQuickMenuWnd", NULL) : NULL;
                char *db = qm ? find_child(qm, NULL, "@ qm-bts1.xpf 6") : NULL;
                /* (user 10-28 23:53 "the deploy window is wrong": 0x1b opened the quick menu) out of battle: the command
                   of the quick menu's own DEPLOY units button (its id +0x2c0) sent to the quick menu's OnCommand */
                if (db && rd(db, 0x2c4) && rd(*(void ***)qm, 16 * 4))
                    ((cmd_fn)(*(void ***)qm)[15])(qm, 2, 0, *(int *)(db + 0x2c0));
                else
                    ((cmd_fn)(*(void ***)g_panel)[15])(g_panel, 2, 0, a->arg == 9 && f[0x29bdc] ? 0x18 : WHEEL_ID[a->arg]);
            }
        } else if (a->kind == H_RADAR) {
            if (rd(g_panel, 0xa100)) ((ev_fn)(*(void ***)g_panel)[5])(g_panel, a->msg, a->x, a->y, a->flags);
        } else if (a->kind == H_CHAT) {                  /* CCtrlChatting 0043aef0(mode, focus): 0 all, 1 whisper, 2 allies */
            if (rd(g_chat, 0xec70) && a->arg >= 0 && a->arg <= 2)
                ((void (__attribute__((thiscall)) *)(char *, int, int))0x43aef0)(g_chat, a->arg, a->arg == 1);
            g_dirty = 1;
        }
    }
    g_nq = 0;
}

/* ---- per frame (game thread, frame start) --------------------------------------------------------------------- */
static int painter_start(void);
static int request_paint(void);
static void login_pending(void);
static volatile LONG g_busy, g_ready;
/* user 10-28 21:34 "the chat is one dark see-through box, no hole": the chat window's draw before its children
   (vtable +0x2c, viewport = the chat window, called by the window tree 005487c0) darkens the map under the chat box
   in the frame itself (the HUD is drawn over the frame, so a box there would dim the text too); the text lines have
   their own fill switched off (CCtrlEditORG +0x316) */
static void *g_chat_vtb[65];
#define g_chat_vt (g_chat_vtb + 1)
static RECT g_glass = { 0, 453, 434, 600 };            /* frame pixels */
static void __fastcall chat_glass(char *wnd)
{
    (void)wnd;
    int act = g_st.active || (g_st.lg_game && !g_pub_lgv);   /* (14:40) the options card not shown yet: glass stays */
    if (g_on <= 0 || !act || cov_shown() || cdlg_shown() || !g_chat_open) return;
    char *cg = *(char **)0x6ba7d0;
    if (!rd(cg, 0x84)) return;
    unsigned short *org = *(unsigned short **)(cg + 0x5c);
    int pitch = *(int *)(cg + 0x60), vl = *(int *)(cg + 0x64), vt = *(int *)(cg + 0x68);
    int cx0 = *(int *)(cg + 0x74), cy0 = *(int *)(cg + 0x78), cx1 = *(int *)(cg + 0x7c), cy1 = *(int *)(cg + 0x80);
    int x0 = g_glass.left - vl, y0 = g_glass.top - vt, x1 = g_glass.right - vl, y1 = g_glass.bottom - vt;
    if (x0 < cx0) x0 = cx0; if (y0 < cy0) y0 = cy0; if (x1 > cx1) x1 = cx1; if (y1 > cy1) y1 = cy1;
    if (!org || x0 >= x1 || y0 >= y1) return;
    for (int y = y0; y < y1; y++) {
        unsigned short *p = org + (long)y * pitch + x0;
        for (int x = x0; x < x1; x++, p++) {           /* 38 % of the map + a cold dark tint */
            unsigned v = *p, r = v >> 11, g = (v >> 5) & 63, b = v & 31;
            r = r * 3 / 8 + 1; g = g * 3 / 8 + 3; b = b * 3 / 8 + 3;
            *p = (unsigned short)((r << 11) | (g << 5) | b);
        }
    }
}
static int g_last_cw, g_last_ch;
/* (user 10-29 21:34 "no NEXON logo and movies, straight to the main menu"): the intro movies are not opened at all
   (sgwindow.c hook_BinkOpen); the logo window (CLogoWnd) is put where its own Esc handler 0053c850 puts it (fade 0x15,
   state 0-2 -> 2, 3-5 -> 5); the server select's fly-in (CNewSeverSelectWnd +0x4710 = 0) where Esc puts it (1).
   [hud] skip_intro=0 keeps them. */
static void skip_intro(char *app)
{
    static int inited;
    if (!inited) { inited = 1; g_skip_intro = GetPrivateProfileIntA("hud", "skip_intro", 1, ".\\GORender.ini") != 0; }
    if (!g_skip_intro || g_seen_setup) return;
    char **k; int n = rd(app + 0x28, 0x160) ? wkids(app + 0x28, &k) : 0;
    for (int i = 0; i < n; i++) {
        char *w = k[i];
        if (!rd(w, 0x404) || !wvis(w) || strcmp(sgr_class(w), "CLogoWnd")) continue;
        char *ml = find_child(w, "CMultiLoginSelectWnd", NULL);
        if (ml && wvis(ml)) return;                /* a choice for the player */
        int st = *(int *)(w + 0x3f8);
        if (st >= 0 && st <= 1) { *(int *)(w + 0x3f4) = 0x15; *(int *)(w + 0x3f8) = 2; }
        else if (st >= 3 && st <= 4) { *(int *)(w + 0x3f4) = 0x15; *(int *)(w + 0x3f8) = 5; }
    }
}
/* (user 10-29 22:30 "no battle messages while watching a recording"): the recorded battle's message box (CScrMsgDlg /
   CNoticeDlg: modal, 00478ec0 keeps playing the recording; its OnCommand (2, 0, 2) = CANCEL ends it, +0x164) is
   cancelled, polls and alerts are hidden */
static void replay_quiet(char *app, char *fw)
{
    char *modal = *(char **)(app + 0xc18);
    if (rd(modal, 0x170) && *(int *)(modal + 0x164) == 0) {
        const char *c = sgr_class(modal);
        if ((!strcmp(c, "CScrMsgDlg") || !strcmp(c, "CNoticeDlg")) && rd(*(void ***)modal, 16 * 4)) {
            ((cmd_fn)(*(void ***)modal)[15])(modal, 2, 0, 2);
            if (sgr_debug()) sgr_log("replay: %s cancelled", c);
        }
    }
    static const char *QUIET[] = { "CPollWnd", "CAlertWnd", "CPannelQuestionDlg", "CScrMsgDlg", "CNoticeDlg", "CJoinBattleWaitDlg" };
    char *tops[2] = { fw, app + 0x28 };
    for (int t = 0; t < 2; t++) {
        char **k; int n = rd(tops[t], 0x160) ? wkids(tops[t], &k) : 0;
        for (int i = 0; i < n; i++) {
            if (!rd(k[i], 0x160) || !k[i][0x155]) continue;
            const char *c = sgr_class(k[i]);
            for (unsigned j = 0; j < sizeof QUIET / sizeof *QUIET; j++)
                if (!strcmp(c, QUIET[j])) { k[i][0x155] = 0; break; }
        }
    }
}
/* (user 10-29 22:30 "name a recording after the planet it was fought on"): the battle's planet + province, kept while
   a battle runs (not a recording); sgwindow.c's CreateFileA puts them in front of the file name the recorder makes */
static char g_rec_prefix[96];
int sghud_rec_prefix(char *buf, int n)
{
    if (!g_rec_prefix[0] || n < 2) return 0;
    lstrcpynA(buf, g_rec_prefix, n);
    return 1;
}
static void rec_track(HudState *s)
{
    static DWORD t; static int last;
    if (!s->active || !s->battle || s->replay || !rd(g_map, 0x400)) return;
    int mapid = *(int *)(g_map + 0x3f4);
    if (mapid == last && GetTickCount() - t < 5000) return;
    last = mapid; t = GetTickCount();
    char *pm = *(char **)0xc30bc4, nm[96] = { 0 };
    if (!rd(pm, 0xa0)) return;
    lstrcpynA(nm, str_at(pm + 0x78), 40);                        /* the planet (+0x74 its id) */
    char *pv = ((char *(__fastcall *)(char *, int, int))0x565ce0)(pm, 0, mapid);
    if (rd(pv, 0x30)) {                                           /* the province */
        int L = lstrlenA(nm);
        if (L) nm[L++] = '_';
        lstrcpynA(nm + L, str_at(pv + 0xc), 40);
    }
    for (char *c = nm; *c; c++) {                                 /* no characters a file name cannot hold */
        unsigned char u = (unsigned char)*c;
        if (u < 0x20 || strchr("\\/:*?\"<>|", u)) *c = '-';
        if (u >= 0x81) { if (c[1]) c++; }                          /* a double-byte character: its second byte stays */
    }
    lstrcpynA(g_rec_prefix, nm, sizeof g_rec_prefix);
}
/* (11-01 13:37 diagnosis) the roster's equipped items (unit +0xe0 list: u16 ids, begin +0xe8 / end +0xec), logged
   when the totals change */
static void items_watch(void)
{
    static DWORD t; static int last_u = -1, last_i = -1;
    DWORD now = GetTickCount(); if (now - t < 1000) return; t = now;
    char *cmd = *(char **)0x6ba7d8;
    if (!rd(cmd, 0x6d8)) return;
    int nu = 0, ni = 0;
    for (int k = 0; k < 140; k++) {
        char *u = *(char **)(cmd + (k < 12 ? 0x4a8 + 4 * k : 0x4d8 + 4 * (k - 12)));
        if (!u || !rd(u, 0xf0)) continue;
        char *b = *(char **)(u + 0xe8), *e = *(char **)(u + 0xec);
        nu++;
        if (b && e >= b && e - b < 200) ni += (int)(e - b) / 2;
    }
    if (nu != last_u || ni != last_i) { sgr_log("ITEMS roster %d unit(s), %d equipped item(s)", nu, ni); last_u = nu; last_i = ni; }
}
void sghud_frame(char *app, int W, int DX)
{
    items_watch();
    g_app_last = app;
    if (g_on < 0) {
        g_on = GetPrivateProfileIntA("hud", "enable", 1, ".\\GORender.ini");
        UINT cp = GetACP();
        g_lang = cp == 936 ? 1 : cp == 950 ? 2 : 0;
        if (g_on && (!gdip_load() || (rec_install(), !painter_start()))) { g_on = 0; sgr_log("HUD off: no GDI+ / thread"); }
        else sgr_log("HUD %s (language %d)", g_on ? "on" : "off", g_lang);
    }
    if (!g_on || !g_disp.hwnd) return;
    int was = g_st.active;
    g_stage_game = "actions";
    if (app) skip_intro(app);
    run_actions();
    g_stage_game = "read";
    read_state(app, W, DX);
    g_stage_game = "hide";
    HudState *s = &g_st;
    {   /* test harness: SGRender_rec.req = the "record battles" option (app +0x25bc) kept on */
        static int force; if (app && GetFileAttributesA("GORender_rec.req") != INVALID_FILE_ATTRIBUTES) { DeleteFileA("GORender_rec.req"); force = 1; }
        if (force && app) app[0x25bc] = 1;
    }
    if (s->active && s->replay && app) replay_quiet(app, G_FIELD + 4);
    rec_track(s);
    {   static int last_lg; if (s->lg != last_lg) { if (sgr_debug()) sgr_log("LOGIN lg %d -> %d", last_lg, s->lg); last_lg = s->lg; g_hover_kind = 0; g_dirty = 1; } }
    login_pending();
    if (s->lg == LG_BOOT || s->lg == LG_LOAD || s->lg_qon) { static DWORD bt; if (GetTickCount() - bt >= 60) { bt = GetTickCount(); g_dirty = 1; } }
    if (s->active && g_acc[0]) {   /* (user 11-01 03:18 "F4 opens with a delay") the commander page is fetched ahead
                                      (in game, then every 90 s) so F4 opens on data already here; it refreshes while open */
        static DWORD pre_t;
        if (g_cmd_state != 1 && (g_cmd_state == 0 || GetTickCount() - g_cmd_t > 90000) && GetTickCount() - pre_t > 5000) {
            pre_t = GetTickCount(); cmd_fetch_start();
        }
    }
    if (s->active) {
        char *cards = *(char **)(G_FIELD + 0x29b34);   /* the old pieces the HUD replaces */
        if (rd(cards, CARD_SIZE * 12)) for (int i = 0; i < 12; i++) cards[i * CARD_SIZE + 0x155] = 0;
        g_panel[0x155] = 0;
        char **ck; int nck = wkids(g_chat, &ck);       /* the chat's controls on the old panel's right part (town user
                                                           list and its toggles): no room for them in the band */
        for (int i = 0; i < nck; i++)
            if (rd(ck[i], 0x160) && (*(int *)(ck[i] + 0x128) >= 600 || !strcmp(sgr_class(ck[i]), "CCtrlRadioButton")
                                     || !strncmp(ck[i] + 4, "@ ctp-chat.xpf", 14))) ck[i][0x155] = 0;   /* (17:11) the 3 mode icons: HUD tabs */
        int want = 12 - DX - 160;                       /* chat text column at frame x 12 */
        int *rel = (int *)(g_chat + 0x128);
        if (rel[0] != want || !g_chat_moved) {
            *(int *)(g_chat + 0x108) = -4000; *(int *)(g_chat + 0x110) = 4000;   /* Move clamps to these limits */
            ((move_fn)0x5ed3c0)(g_chat, want, rel[1], rel[2], rel[3]);
            g_chat_moved = 1;
        }
        if (g_chat_pin < 0) {
            g_chat_pin = GetPrivateProfileIntA("hud", "chat_pin", 1, ".\\GORender.ini") != 0;
            g_chat_open = 1; g_chat_touch = GetTickCount();
        }
        if (!g_chat_pin && g_chat_open && !g_chat_typing && GetTickCount() - g_chat_touch > 8000) { g_chat_open = 0; g_dirty = 1; }
        if ((!g_chat_open && !cov_shown()) || cdlg_shown()) { if (g_chat[0x155]) { g_chat[0x155] = 0; g_chat_hid = 1; } }
        else if (g_chat_hid) { g_chat[0x155] = 1; g_chat_hid = 0; }
        for (int i = 0; i < nck; i++) {                 /* the message lines and the input: no own background, */
            char *k = ck[i];                            /* the text stands on the dark glass (chat_glass) */
            if (!rd(k, 0x318) || *(int *)(k + 0x130) < 300 || strcmp(sgr_class(k), "CCtrlEditORG")) continue;
            k[0x316] = 0;
        }
        if (rd(*(void ***)g_chat - 1, 65 * 4) && *(void **)g_chat != (void *)g_chat_vt) {   /* hook its pre-children draw */
            memcpy(g_chat_vtb, *(void ***)g_chat - 1, sizeof g_chat_vtb);
            g_chat_vt[11] = (void *)chat_glass;
            *(void ***)g_chat = g_chat_vt;
        }
    } else if (g_chat_hid && rd(g_chat, 0x160)) { g_chat[0x155] = 1; g_chat_hid = 0; }
    {   /* over the HUD the game's own cursor (drawn into the frame under the HUD, CMainSystem +0xbf8 = drawn) is off,
           the HUD shows the game's arrow as the Windows cursor (one cursor, never under a panel) */
        static int cleared;
        POINT p; GetCursorPos(&p); ScreenToClient(g_disp.hwnd, &p);
        int over = (s->active || s->lg) && sghud_over(p.x, p.y);
        if (over && app && app[0xbf8]) { app[0xbf8] = 0; cleared = 1; }
        else if (!over && cleared) { if (app) app[0xbf8] = 1; cleared = 0; }
    }
    if (g_frame_live) {                                  /* (17:47) the running light of a general's frame */
        static DWORD t; if (GetTickCount() - t >= 60) { t = GetTickCount(); g_dirty = 1; }
    }
    if (s->binfo > 0) {                                  /* the flowing light on the battle info button: ~25 fps */
        static DWORD t; if (GetTickCount() - t >= 40) { t = GetTickCount(); g_dirty = 1; }
    }
    {   static int was_flash;                           /* a clicked command's solid look ends: repaint */
        int fl = g_cmd_flash_slot >= 0 && GetTickCount() - g_cmd_flash_t < 600;
        if (was_flash && !fl) g_dirty = 1;
        was_flash = fl;
    }
    g_stage_game = "request";
    if (g_ready) { g_ready = 0; sgr_overlay_invalidate(); }   /* a finished picture: show it */
    unsigned hm = fnv(s, MAIN_HASH_BYTES, 2166136261u);
    unsigned hd = fnv(&s->mapw, (int)(sizeof *s - MAIN_HASH_BYTES), 2166136261u);
    DWORD now = GetTickCount();
    RECT c; GetClientRect(g_disp.hwnd, &c);
    if (c.right != g_last_cw || c.bottom != g_last_ch) { g_last_cw = c.right; g_last_ch = c.bottom; g_dirty = 1; }
    if (g_dirty || s->active != was || (hm != g_hash_main && now - g_last_paint >= 33) ||
        (hd != g_hash_dots && now - g_last_paint >= 150)) {
        if (request_paint()) { g_dirty = 0; g_hash_main = hm; g_hash_dots = hd; g_last_paint = now; }
    }
    g_stage_game = "-";
}
