/* sghud_state.h - part of sghud.c (included in this order; not a header on its own): state read every frame + the re-skinned game windows (hooks, art windows, F4 / result data fetch) */
/* ---- state read every frame ---------------------------------------------------------------------------------- */
typedef struct { unsigned id; int slot, branch, hp, hpmax, en, enmax, sel, dead, hero; WCHAR name[28]; } HudUnit;
typedef struct { int owner, rel, str, max, tx, ty; } HudPoc;
typedef struct { short x, y; unsigned char rel; } HudDot;
typedef struct { short tx, ty, tw, th; unsigned char rel, type; } HudBox;   /* map tiles */
/* a re-skinned game window and its controls (frame pixels): the game keeps the window and its behaviour (clicks go
   to it), its art is not drawn (instance vtables: draw = glass / nothing) and the HUD draws the new look on top */
enum { SK_BUTTON, SK_TEXT, SK_TAB, SK_TAB_ON, SK_CLOSE, SK_RADIO, SK_HIDE, SK_HEAD, SK_KEEP };
typedef struct { short x0, y0, x1, y1; WCHAR title[24]; unsigned char def, page; char *wp; } HudSkinWnd;   /* wp: the game window */
typedef struct { short x0, y0, x1, y1; unsigned char kind, accent; unsigned short color; WCHAR label[36]; } HudSkin;
typedef struct {
    int active, covered, battle, W, DX, mine;
    int replay;                              /* a recording plays (CRecorder *0x6ba818 +0x50) */
    /* the login screen (user 10-29 21:10 "方案A"): lg 0 none, 1 main menu, 2 the CONTINUE dialog (ID / password);
       frame pixels of the game's controls the new look sends the mouse to */
    int lg, lg_focus, lg_caret, lg_blink, lg_nf, lg_nb;
    short lg_btn[6][4], lg_ed[4][4], lg_bt[3][4];   /* main menu buttons, a form's edits / buttons (frame px) */
    unsigned char lg_mask[4], lg_len[4]; char lg_txt[4][40];
    int lg_cnt, lg_first, lg_sel, lg_nrow;          /* briefing room: records, first row shown, chosen record */
    short lg_row[4], lg_scr[4];                     /* row x, y, width, height; the scroll bar */
    char lg_rec[10][80];
    /* select commander: the hero (1..9), points left, the 4 stats; portrait buttons, spinners (dec, inc), SELECT,
       the panel's PREVIOUS / NEXT; a checksum of the pictures copied out of the frame */
    int lg_hero, lg_pts, lg_stat[4]; unsigned lg_imgsum;
    short lg_hbtn[9][4], lg_spin[4][2][4], lg_hsel[4], lg_nav[2][4], lg_hview[4];
    /* select nation: the tab (0 planet, 1 faction, 2 friend), the live viewer (shown through the overlay), the tab
       buttons, SELECT, the friend ID box (edit, OK, CANCEL) */
    int lg_tab, lg_fr, lg_qon;                     /* lg_qon: the advisor's OK (CPannelQuestionDlg) is up */
    short lg_q[4];
    short lg_view[4], lg_ntab[3][4], lg_nsel[4], lg_fred[4], lg_frbt[2][4];
    WCHAR lg_msg[160];
    /* (user 11-01 08:31) the OPTIONS page (CNewOptionWnd > CInsideOptionWnd): its controls (frame px) by id (OPT_*),
       its values (+0x2f0 .. +0x307), the two volume tracks */
    short lg_ot[40][4]; unsigned char lg_oon[40];
    short lg_osl[2][4];
    int lg_otab, lg_ovol[2], lg_oscroll, lg_o3d; unsigned char lg_of[12];
    int lg_game; short lg_odead[2];                 /* (11-01 13:02) the options opened in the game (not the login screen);
                                                       a spot of its window on nothing (the mouse elsewhere goes there) */
    int lg_osub; short lg_ohole[4];                 /* its dialogs: 1 colour picker (the game's picture in a hole), 2 macros */
    char lg_omac[10][40]; int lg_ofoc, lg_ocaret;  /* the 10 macro texts (code page), the focused one (1..10) */
    int binfo;                               /* unread battle reports (Field+0x388: +8 queue count, 00402eb0 adds) */
    int ui_d[4], ui_ok; int ui_merc; int my_look;   /* my_look: commander [0x450] = portrait Hero-NN (18:26) */      /* (17:31) F4 window: live attribute texts, mercenary on/off */
    int chat_open, chat_pin, chat_mode, chat_dlg;   /* (17:11) chat_mode 0 all / 1 private / 2 allies; chat_dlg: a dialog covers it */                 /* user 10-28 21:15: the chat folds to the left or stays pinned */
    int nskw; HudSkinWnd skw[8];             /* game windows re-skinned by the HUD (user 10-28 21:36) */
    int nhold; char *hold[8];                /* (11-01 14:40) skinned windows the game must not draw yet (opening, data) */
    int nfh; short fh[4][4];                 /* (14:40) a game window the HUD does not skin, ABOVE a skinned one (an alert
                                                over the permission box): its frame rect is left open in the HUD */
    int nsk; HudSkin sk[160]; char *skp[160]; int nhid; char *hid[64];   /* skp: the game control of each item (hidden this frame) */
    int left, total;                         /* seconds */
    int ncard; HudUnit card[12];
    int npoc; HudPoc poc[8];
    int ngate; HudBox gate[16];          /* star gates (area list type 1, to the neighbour province) */
    int nbld; HudBox bld[32];            /* buildings (capital areas 2..14, map objects other than POCs) */
    int n_mine, n_enemy;
    int nsel; HudUnit sel; int cmd[8], cmd_on; signed char cmd_tg[8];
    int nocc; RECT occ[24];                  /* windows over the field, frame pixels */
    int mapw, maph, camx, camy, camw, camh;  /* radar (excluded from the main hash) */
    int ndot; HudDot dot[512];
} HudState;
static HudState g_st;          /* game thread: read every frame */
static HudState g_ps;          /* painter thread: the snapshot it paints */
static char g_acc[40];         /* the login account (16:10: ?acc= on the honor / report pages) */
#define MAIN_HASH_BYTES ((int)offsetof(HudState, mapw))

static int g_on = -1;                        /* [hud] enable=1 (default) */
static char *g_field, *g_map, *g_panel, *g_chat, *g_cbw;
static int g_chat_moved;
/* the chat (user 10-28 21:15 "grey background, no frame, folds to the left or pinned"): pinned = always open; not
   pinned = folds 8 s after the mouse left it (not while typing: Enter opens the input, Enter / Esc ends it) */
static int g_chat_pin = -1, g_chat_open = 1, g_chat_hid, g_chat_typing;
/* unit honor page (user 10-31 14:10): open, tab (0 mine, 1 server top), page; the text fetched from the server */
static int g_hon_open, g_hon_tab, g_hon_page, g_hon_sel = -1;
static volatile LONG g_hon_busy; static volatile int g_hon_state; static DWORD g_hon_t;   /* 0 -, 1 loading, 2 ok, 3 failed */
static char g_hon_buf[32768]; static CRITICAL_SECTION g_hon_cs; static int g_hon_csok;
/* battle report (user 10-31 15:01): fetched when the result window shows; 0 -, 1 loading, 2 ok, 3 failed */
static volatile LONG g_rep_busy; static volatile int g_rep_state; static DWORD g_rep_t, g_rep_seen, g_rep_first; static int g_rep_tries;
static volatile DWORD g_rep_open;   /* game thread: last tick a result window was seen opening */
static char g_cmd_buf[8192]; static volatile LONG g_cmd_busy; static volatile int g_cmd_state; static volatile DWORD g_cmd_t, g_cmd_seen;
static void cmd_fetch_start(void);
static int cmd_ready(void) { return g_cmd_state == 2 && g_cmd_buf[0] == 'I' && g_cmd_buf[1] == '\t'; }   /* (11-01) data page here */
/* (user 11-01 14:17) another commander's info (CUserInfoWnd "@ f4-bk-nm", 0x27 sub 1) in the same look: its public page
   honor/user.txt?name=<the shown name, window +0x80d> (I, B x4, N, M lines) */
static char g_oth_buf[4096]; static volatile LONG g_oth_busy; static volatile int g_oth_state; static volatile DWORD g_oth_t;
static char g_oth_name[64], g_oth_got[64], g_oth_req[64];
static void oth_fetch_start(void);
static int oth_ready(void) { return g_oth_state == 2 && g_oth_buf[0] == 'I' && g_oth_buf[1] == '\t' && !strcmp(g_oth_got, g_oth_name); }
static void rep_fetch_start(void);
static char g_rep_buf[8192];
static DWORD g_chat_touch;
static volatile int g_hole_hit;
/* the command wheel: commands of the old panel (CStatusLowerWnd OnCommand 005b7010 ids; the ids of its buttons and
 * of its slide-out sub menus) */
#define WHEEL_N 10
/* [9] (user 10-28 23:41 "the deploy button is missing"): deploy units 0x1b (out of battle) / reinforcement 0x18 in
   battle (005b4cb0: packet 0x19 = F7) - the old panel had them in its slide-out menus */
static const int WHEEL_ID[WHEEL_N] = { 20, 28, 19, 21, 23, 22, 29, 16, 35, 0x1b };
static const int WHEEL_ICON[WHEEL_N] = { IC_MAP, IC_QUICK, IC_WHO, IC_MAIL, IC_BOARD, IC_INFO, IC_KEY, IC_GEAR, IC_EXIT, IC_INF };
#define WHEEL_LEAVE 8
static int g_hover_kind, g_hover_arg;          /* game thread (mouse) */
static int g_dirty = 1;                        /* repaint wanted (hover, wheel, size) */
static volatile int g_frame_live;              /* (17:47) a tier-4 rank frame is shown: keep repainting (its running light) */
static int g_ps_hover_kind, g_ps_hover_arg;   /* their copies in the snapshot */
static DWORD g_last_paint;
static unsigned g_hash_main, g_hash_dots;

static unsigned fnv(const void *p, int n, unsigned h)
{
    const unsigned char *b = (const unsigned char *)p;
    while (n--) { h ^= *b++; h *= 16777619u; }
    return h;
}

static int unit_branch(const WCHAR *name)
{
    WCHAR b[32]; lstrcpynW(b, name, 32);
    int n = (int)wcslen(b);
    for (int i = n - 1; i > 0; i--)            /* drop " MK3" / "-MK3" */
        if ((b[i] == L'K' || b[i] == L'k') && i > 1 && (b[i - 1] == L'M' || b[i - 1] == L'm') &&
            (b[i - 2] == L' ' || b[i - 2] == L'-')) { b[i - 2] = 0; break; }
    for (unsigned i = 0; i < sizeof HUD_UNITS / sizeof HUD_UNITS[0]; i++)
        if (!wcscmp(HUD_UNITS[i].name, b)) return HUD_UNITS[i].branch;
    return -1;
}

static void read_unit(char *u, HudUnit *o)
{
    memset(o, 0, sizeof *o);
    if (!rd(u, 0xf200)) return;
    o->id = *(unsigned *)(u + 4);
    o->slot = ((unsigned char *)u)[0x6b];
    o->hpmax = *(int *)(u + 0x110); o->hp = tvi(u, 0xa464, 0xa866);
    o->enmax = *(int *)(u + 0x108); o->en = tvi(u, 0x9454, 0x9856);
    o->dead = tvi(u, 0xa868, 0xac6a) == ST_DEAD || o->hp <= 0;
    char nm[32]; lstrcpynA(nm, u + 0x78, sizeof nm);
    /* (user 10-31 14:07) a starred unit's name comes as "*N name": the HUD shows it with a star */
    int star = nm[0] == '*' && nm[1] >= '1' && nm[1] <= '9' && nm[2] == ' ' ? nm[1] - '0' : 0;
    MultiByteToWideChar(CP_ACP, 0, star ? nm + 3 : nm, -1, o->name, 28);
    o->branch = unit_branch(o->name);
    if (star) { WCHAR t[28]; swprintf(t, 28, L"\x2605%d %ls", star, o->name); lstrcpynW(o->name, t, 28); }
    o->hero = o->branch < 0 && !strncmp(u + 0x78, u + 0xb9, 20);   /* the commander: unit name = player name */
}

static const WCHAR *unit_class(const HudUnit *u)
{
    if (u->dead) return T3("Destroyed", "已阵亡", "已陣亡");
    if (u->hero) return T3("Commander", "指挥官", "指揮官");
    return branch_name(u->branch);
}
static int unit_icon(const HudUnit *u) { return u->branch >= 0 ? IC_INF + u->branch : u->hero ? IC_HUB : IC_DOT; }
static ARGB unit_color(const HudUnit *u);

static char *find_child(char *w, const char *cls, const char *name)
{
    char **k; int n = wkids(w, &k);
    for (int i = 0; i < n; i++) {
        if (!rd(k[i], 0x160)) continue;
        if (cls && strcmp(sgr_class(k[i]), cls)) continue;
        if (name && strcmp(k[i] + 4, name)) continue;
        return k[i];
    }
    return NULL;
}

static char *g_occ_w[24];
static void add_occ(HudState *s, char *w)
{
    if (s->nocc >= 24 || !rd(w, 0x160) || !wvis(w)) return;
    const int *a = (const int *)(w + 0x118);
    if (a[2] - a[0] <= 4 || a[3] - a[1] <= 4) return;
    RECT r = { a[0] + s->DX, a[1], a[2] + s->DX, a[3] };
    g_occ_w[s->nocc] = w;
    s->occ[s->nocc++] = r;
}
static void log_occ(HudState *s)           /* which game windows cover parts of the HUD (log, when the set changes) */
{
    static unsigned last; static int lines;
    unsigned h = fnv(g_occ_w, s->nocc * (int)sizeof(char *), 2166136261u);   /* the set of windows (not their slide) */
    if (h == last || lines > 60) return;
    last = h;
    for (int i = 0; i < s->nocc && lines <= 60; i++, lines++)
        sgr_log("HUD window over the field: %s \"%.30s\" %ld,%ld-%ld,%ld", sgr_class(g_occ_w[i]), g_occ_w[i] + 4,
                s->occ[i].left, s->occ[i].top, s->occ[i].right, s->occ[i].bottom);
}

/* ---- re-skinned game windows (phase 4, user 10-28 21:36 "the quick menu and the other old windows too") ------
 * Instance vtables: the window's draw (+0x2c, before its children) darkens the map under it like the chat
 * (skin_glass), its buttons' draw does nothing; the HUD paints the window and the buttons over the frame.
 * Labels of sprite buttons ("@ file.xpf frame") from SKIN_LABELS (their art read with SGRender_spr.req);
 * text buttons ("CCF", list entries) use their own text (client code page) and colour (+0x2b8, RGB565). */
typedef struct { const char *file; int frame; const WCHAR *en, *cn, *tw; int kind; } SkinLabel;
static const SkinLabel SKIN_LABELS[] = {
    { "qm-bts0.xpf", 0, L"CLOSE", L"关闭", L"關閉", SK_CLOSE },
    { "altw-bts.xpf", 0, L"OK", L"确定", L"確定", SK_BUTTON },        /* (11-01 14:40) the alert (battle news, attacks) */
    { "altw-bts.xpf", 3, L"CANCEL", L"取消", L"取消", SK_BUTTON },
    { "qm-bts0.xpf", 3, L"Assign XP", L"分配经验", L"分配經驗", SK_BUTTON },
    { "qm-bts0.xpf", 6, L"Whisper to Subordinates", L"密语部下", L"密語部下", SK_BUTTON },
    { "qm-bts0.xpf", 9, L"Whisper to Teacher", L"密语导师", L"密語導師", SK_BUTTON },
    { "qm-bts0.xpf", 12, L"Send E-Mail", L"发送邮件", L"發送郵件", SK_BUTTON },
    { "qm-bts1.xpf", 0, L"Initiate an ATTACK", L"发起进攻", L"發起進攻", SK_BUTTON },
    { "qm-bts1.xpf", 3, L"Go to my CAPITAL", L"回到首都", L"回到首都", SK_BUTTON },
    { "qm-bts1.xpf", 6, L"DEPLOY units", L"部署部队", L"部署部隊", SK_BUTTON },
    { "qm-bts1.xpf", 9, L"Go to UPGRADE", L"前往升级", L"前往升級", SK_BUTTON },
    { "qm-bts1.xpf", 12, L"Go to the ...", L"前往……", L"前往……", SK_BUTTON },
    { "qm-bts1.xpf", 15, L"Go to BATTLE", L"前往战场", L"前往戰場", SK_BUTTON },
    { "qm-bts1.xpf", 18, L"Go to REPAIR", L"前往修理", L"前往修理", SK_BUTTON },
    { "qm-bts2.xpf", 0, L"CLOSE", L"关闭", L"關閉", SK_CLOSE },
    { "qm-bts2.xpf", 3, L"F1 HELP", L"F1 说明", L"F1 說明", SK_BUTTON },
    { "qm-bts2.xpf", 6, L"VIEW SELF", L"查看自己", L"查看自己", SK_BUTTON },
    { "qm-bts2.xpf", 9, L"CENTER ON SELF", L"镜头回到自己", L"鏡頭回到自己", SK_BUTTON },
    { "uew-but2.xpf", 0, L"NAME", L"名称", L"名稱", SK_HEAD },          /* (11-01 16:50) Assign XP: list columns */
    { "uew-but2.xpf", 3, L"LV", L"等级", L"等級", SK_HEAD },
    { "uew-but2.xpf", 6, L"DIRECT", L"直接经验", L"直接經驗", SK_HEAD },
    { "uew-but2.xpf", 9, L"INDIRECT", L"间接经验", L"間接經驗", SK_HEAD },
    { "uew-but1.xpf", 0, L"LEVEL", L"等级", L"等級", SK_RADIO },          /* sort / branch filter */
    { "uew-but1.xpf", 3, L"INFANTRY", L"步兵", L"步兵", SK_RADIO },
    { "uew-but1.xpf", 6, L"MOBILE", L"机动", L"機動", SK_RADIO },
    { "uew-but1.xpf", 9, L"AVIATION", L"航空", L"航空", SK_RADIO },
    { "uew-but1.xpf", 12, L"ORGANIC", L"有机", L"有機", SK_RADIO },
    { "uew-but0.xpf", 0, L"AUTO ASSIGN", L"自动分配", L"自動分配", SK_BUTTON },
    { "uew-but0.xpf", 3, L"UNDO", L"复原", L"復原", SK_BUTTON },
    { "uew-but0.xpf", 6, L"CLEAR", L"清除", L"清除", SK_BUTTON },
    { "uew-but0.xpf", 9, L"OK", L"确定", L"確定", SK_BUTTON },
    { "uew-but0.xpf", 12, L"CANCEL", L"取消", L"取消", SK_BUTTON },
    { "qm-ttbt.xpf", 0, L"Q.R.F", L"Q.R.F", L"Q.R.F", SK_TAB },
    { "qm-ttbt.xpf", 3, L"QUICK MENU", L"快速选单", L"快速選單", SK_TAB },
    { "pmw-bk.xpf", 0, NULL, NULL, NULL, SK_HIDE },
    { "pmw-buts.xpf", 0, L"AUTO PERMISSION", L"自动许可", L"自動許可", SK_RADIO },
    { "pmw-buts.xpf", 3, L"AUTO REJECT", L"自动拒绝", L"自動拒絕", SK_RADIO },
    { "pmw-buts.xpf", 6, L"MANUAL SELECT", L"手动选择", L"手動選擇", SK_RADIO },
    { "pmw-buts.xpf", 9, L"OK", L"确定", L"確定", SK_BUTTON },
    { "mld-mbt.xpf", 6, L"CLOSE", L"关闭", L"關閉", SK_CLOSE },
    { "mld-mbt.xpf", 0, NULL, NULL, NULL, SK_HIDE },      /* (11-01 12:56) the READ / WRITE SGMAIL tab art: the HUD's tabs */
    { "mld-mbt.xpf", 3, NULL, NULL, NULL, SK_HIDE },
    { "mld-sbt.xpf", 15, L"SEND", L"寄出", L"寄出", SK_BUTTON },
    { "mld-sbt.xpf", 18, L"RESET", L"清除", L"清除", SK_BUTTON },
    { "bbs-fd.xpf", 0, NULL, NULL, NULL, SK_HIDE },
    { "bbs-b-tt.xpf", 0, L"OFFICIAL", L"官方公告", L"官方公告", SK_TAB },   /* (11-02 16:32 "不要有KRU") */
    { "bbs-b-tt.xpf", 3, L"SUGGESTION", L"建议", L"建議", SK_TAB },
    { "bbs-b-tt.xpf", 6, L"FREE", L"自由讨论", L"自由討論", SK_TAB },
    { "bbs-b-tt.xpf", 9, L"BUGS", L"错误回报", L"錯誤回報", SK_TAB },
    { "bbs-b-tt.xpf", 12, L"FACTION", L"阵营", L"陣營", SK_TAB },
    { "bbs-b-ok.xpf", 0, L"CLOSE", L"关闭", L"關閉", SK_CLOSE },
    { "bbs0-bts.xpf", 0, L"SEARCH", L"搜索", L"搜尋", SK_BUTTON },
    { "bbs0-bts.xpf", 3, L"POST", L"发文", L"發文", SK_BUTTON },
    /* (user 11-02 17:44 "the board is not aligned"): the READ page (bbs1-*) and the WRITE page (bbs2-bts) buttons */
    { "bbs1-bts.xpf", 0, L"LIST", L"列表", L"列表", SK_BUTTON },
    { "bbs1-bts.xpf", 3, L"DELETE", L"删除", L"刪除", SK_BUTTON },
    { "bbs1-bts.xpf", 6, L"MODIFY", L"修改", L"修改", SK_BUTTON },
    { "bbs1-pn.xpf", 0, L"PREVIOUS", L"上一篇", L"上一篇", SK_BUTTON },
    { "bbs1-pn.xpf", 3, L"NEXT", L"下一篇", L"下一篇", SK_BUTTON },
    { "bbs2-bts.xpf", 6, L"OK", L"确定", L"確定", SK_BUTTON },
    { "bbs2-bts.xpf", 3, L"CANCEL", L"取消", L"取消", SK_BUTTON },
    { "bbs2-bts.xpf", 0, L"LIST", L"列表", L"列表", SK_BUTTON },
    { "ss-cb-ar.xpf", 0, L"\x25BE", L"\x25BE", L"\x25BE", SK_BUTTON },
    /* (user 10-31 12:49 "the 3 map buttons in Chinese, 2 pages do nothing"): the strategic map's page tabs are the
       buttons "# bdw-fdbt.xpf 0 0/3/6" (the page shown = the hidden one); the strip behind them (bdw-fdtt, its frame =
       the page) is art.  The ASSEMBLE page (row 3) and AVOID page (row 4) buttons were unknown art and got lost under
       the re-skinned board - now drawn by the HUD (xpf index = frame x 8 + row) */
    { "bdw-fdbt.xpf", 0, L"SHOW", L"显示", L"顯示", SK_TAB },
    { "bdw-fdbt.xpf", 3, L"ASSEMBLE", L"集结", L"集結", SK_TAB },
    { "bdw-fdbt.xpf", 6, L"AVOID", L"回避", L"迴避", SK_TAB },
    { "bdw-fdbt.xpf", 300, L"ALL", L"全部", L"全部", SK_RADIO },
    { "bdw-fdbt.xpf", 303, L"ANTI-GROUND", L"反地面", L"反地面", SK_RADIO },
    { "bdw-fdbt.xpf", 306, L"ANTI-AIR", L"反空", L"反空", SK_RADIO },
    { "bdw-fdbt.xpf", 309, L"SPECIALITY", L"特殊", L"特殊", SK_RADIO },
    { "bdw-fdbt.xpf", 400, L"ALL", L"全部", L"全部", SK_RADIO },
    { "bdw-fdbt.xpf", 403, L"GROUND", L"地面", L"地面", SK_RADIO },
    { "bdw-fdbt.xpf", 406, L"AIR", L"空中", L"空中", SK_RADIO },
    { "bdw-fdbt.xpf", 109, L"SURFACE", L"地表", L"地表", SK_RADIO },
    { "bdw-fdbt.xpf", 100, L"CAVE 1", L"洞穴 1", L"洞穴 1", SK_RADIO },
    { "bdw-fdbt.xpf", 103, L"CAVE 2", L"洞穴 2", L"洞穴 2", SK_RADIO },
    { "bdw-fdbt.xpf", 106, L"CAVE 3", L"洞穴 3", L"洞穴 3", SK_RADIO },
    { "bdw-fdbt.xpf", 200, L"OVERLORD MARKER", L"统帅标记", L"統帥標記", SK_RADIO },
    { "bdw-fdbt.xpf", 206, L"COMMANDER MARKER", L"指挥官标记", L"指揮官標記", SK_RADIO },
    { "bdw-fdbt.xpf", 203, L"REGIMENTS", L"军团", L"軍團", SK_RADIO },
    { "bdw-fdbt.xpf", 209, L"HOLDINGS", L"领地", L"領地", SK_RADIO },
    { "bdw-rbt3.xpf", 0, L"WAR", L"战况", L"戰況", SK_TAB },
    { "bdw-rbt3.xpf", 3, L"BATTLE", L"战斗", L"戰鬥", SK_TAB },
    { "bdw-rbt3.xpf", 6, L"USERS", L"人员", L"人員", SK_TAB },
    { "smc-sbut.xpf", 15, L"LEGEND", L"图例", L"圖例", SK_TAB },
    { "smc-sbut.xpf", 3, L"RESOURCE", L"资源", L"資源", SK_TAB },
    { "smc-buts.xpf", 12, L"REFRESH", L"刷新", L"刷新", SK_BUTTON },
    { "smc-buts.xpf", 3, L"EXIT", L"退出", L"退出", SK_CLOSE },
    { "smc-buts.xpf", 9, L"FIND PATH", L"寻路", L"尋路", SK_BUTTON },
    { "smc-buts.xpf", 0, L"FORCE OPEN", L"强制开启", L"強制開啟", SK_BUTTON },
    { "smc-buts.xpf", 6, L"FORCE OPEN", L"强制开启", L"強制開啟", SK_BUTTON },
    { "bdw-uibt.xpf", 6, L"NAME", L"名称", L"名稱", SK_HEAD },
    { "bdw-uibt.xpf", 0, L"FACTION", L"阵营", L"陣營", SK_HEAD },
    { "bdw-uibt.xpf", 3, L"LEV.", L"等级", L"等級", SK_HEAD },
    { "bdw-rfd3.xpf", 0, NULL, NULL, NULL, SK_HIDE },
    { "bdw-rfrm.xpf", 1, NULL, NULL, NULL, SK_HIDE },
    { "bdw-fdbk.xpf", 0, NULL, NULL, NULL, SK_HIDE },
    { "smc-fdtt.xpf", 1, NULL, NULL, NULL, SK_HIDE },
    { "smc-fdbk.xpf", 2, NULL, NULL, NULL, SK_KEEP },
    { "smc-fdbk.xpf", 0, NULL, NULL, NULL, SK_KEEP },
    { "smc-fdbk.xpf", 1, NULL, NULL, NULL, SK_KEEP },
    { "bdw-fdtt.xpf", 3, NULL, NULL, NULL, SK_HIDE },     /* the tab strip art (any frame): the HUD draws the tabs */
    { "brw-clos.xpf", 0, L"CLOSE", L"关闭", L"關閉", SK_CLOSE },
    { "poll-bts.xpf", 6, L"OK", L"确定", L"確定", SK_BUTTON },
    { "poll-bts.xpf", 0, L"CANCEL", L"取消", L"取消", SK_CLOSE },
    { "HF-bts.xpf", 0, L"WHO-LIST", L"在线名单", L"線上名單", SK_TAB },
    { "HF-bts.xpf", 3, L"REGIMENT", L"军团", L"軍團", SK_TAB },
    { "HF-bts.xpf", 6, L"HALL OF FAME", L"名人堂", L"名人堂", SK_TAB },
    { "HF-bts.xpf", 9, L"CLOSE", L"关闭", L"關閉", SK_CLOSE },
    { "HF-ul-bt.xpf", 15, L"NAME", L"名称", L"名稱", SK_HEAD },
    { "HF-ul-bt.xpf", 0, L"FACTION", L"阵营", L"陣營", SK_HEAD },
    { "HF-ul-bt.xpf", 12, L"REGIMENT", L"军团", L"軍團", SK_HEAD },
    { "HF-ul-bt.xpf", 6, L"LEVEL", L"等级", L"等級", SK_HEAD },
    { "HF-ul-bt.xpf", 9, L"PRE.", L"声望", L"聲望", SK_HEAD },
    { "HF-ul-bt.xpf", 3, L"PR", L"战力", L"戰力", SK_HEAD },
    { "HF-ul-bt.xpf", 18, L"RECORD", L"战绩", L"戰績", SK_HEAD },
};
#define VT_SLOTS 64     /* copied slots: more than any class has (CMailDlg calls slot 20 - 10-29 00:02 crash with 19) */
/* instance vtable hooks: one copy per (original vtable, mode); the copy keeps slot -1 (the RTTI locator, so
   sgr_class / find_child still work on hooked windows) and replaces slot 11 (+0x2c, the draw before the children) */
enum { HK_NONE = 1, HK_GLASS = 2, HK_MAP = 3, HK_ART = 4, HK_KEEP = 5 };
typedef struct { void **orig; int mode; void *copy[VT_SLOTS + 1]; } VtHook;
static VtHook g_vth[64]; static int g_nvth;
static VtHook *vth_find(void **vt)
{
    for (int i = 0; i < g_nvth; i++) if (g_vth[i].copy + 1 == vt) return &g_vth[i];
    return NULL;
}
static int skin_live(void) { return g_on > 0 && (g_st.active || g_st.lg_game); }   /* (14:40) the options in the game too */
static void call_orig(char *w)
{
    VtHook *h = vth_find(*(void ***)w);
    if (h) ((void (__fastcall *)(char *))h->orig[11])(w);
}
static int art_moving(char *w);
static int art_is_empty(char *w);
static int win_held(char *w);
static void __fastcall skin_draw_none(char *w)
{
    char *par = rd(w, 0x13c) ? *(char **)(w + 0x138) : NULL;
    int listed = 0;                                       /* (10-28 23:53 buttons vanished on the strategic map: a */
    for (int i = 0; i < g_st.nsk && !listed; i++) listed = g_st.skp[i] == w;   /* hook stays, the list was full) */
    for (int i = 0; i < g_st.nhid && !listed; i++) listed = g_st.hid[i] == w;
    if (skin_live() && par && art_moving(par)) return;   /* (16:51) the result sliding in / out: not drawn at all */
    if (skin_live() && par && win_held(par)) return;      /* (11-01 14:40) its window is held */
    if (!skin_live() || !listed || (par && (art_moving(par) || art_is_empty(par)))) call_orig(w);
}
/* (11-01 14:40) a hidden control's draw AFTER its children (slot 12, +0x30): CInsideOptionWnd 00561370 draws the
   options' volume bars there - for a hidden (listed) control it is not drawn either */
static void __fastcall skin_draw_none12(char *w)
{
    int listed = 0;
    for (int i = 0; i < g_st.nsk && !listed; i++) listed = g_st.skp[i] == w;
    for (int i = 0; i < g_st.nhid && !listed; i++) listed = g_st.hid[i] == w;
    if (skin_live() && listed) return;
    VtHook *h = vth_find(*(void ***)w);
    if (h) ((void (__fastcall *)(char *))h->orig[12])(w);
}
static void glass_rect(int fx0, int fy0, int fx1, int fy1)   /* darken frame pixels (viewport-relative clip) */
{
    char *cg = *(char **)0x6ba7d0;
    if (!rd(cg, 0x84)) return;
    unsigned short *org = *(unsigned short **)(cg + 0x5c);
    int pitch = *(int *)(cg + 0x60), vl = *(int *)(cg + 0x64), vt = *(int *)(cg + 0x68);
    int x0 = fx0 - vl, y0 = fy0 - vt, x1 = fx1 - vl, y1 = fy1 - vt;
    if (x0 < *(int *)(cg + 0x74)) x0 = *(int *)(cg + 0x74);
    if (y0 < *(int *)(cg + 0x78)) y0 = *(int *)(cg + 0x78);
    if (x1 > *(int *)(cg + 0x7c)) x1 = *(int *)(cg + 0x7c);
    if (y1 > *(int *)(cg + 0x80)) y1 = *(int *)(cg + 0x80);
    if (!org || x0 >= x1 || y0 >= y1) return;
    for (int y = y0; y < y1; y++) {
        unsigned short *p = org + (long)y * pitch + x0;
        for (int x = x0; x < x1; x++, p++) {
            unsigned v = *p, r = v >> 11, g = (v >> 5) & 63, b = v & 31;
            *p = (unsigned short)(((r * 3 / 8 + 1) << 11) | ((g * 3 / 8 + 3) << 5) | (b * 3 / 8 + 3));
        }
    }
}
/* ---- (user 11-01 14:40 "no old look first when a HUD window opens or closes") ---------------------------------------
   1. a commander info window (own F4 / another's) is HELD - the game draws neither it nor its children - while it slides
      (+0x2d0 < 16, off its rest y 0, closing +0x2d4 >= 0) and until its data page is here (3 s at most: an old server
      without the page shows the game's own window then); a held window does not cover the HUD either;
   2. any skinned window is drawn by the game only once the HUD has published a picture that has its page (700 ms at
      most): until then the old HUD stays and the window is not drawn, then both appear in the same frame. */
static char *g_pub_wins[8]; static int g_pub_nw;            /* the windows in the last published picture (g_lock) */
static CRITICAL_SECTION g_lock; static HANDLE g_thr;           /* (defined with the painter, sghud_paint.h) */
static volatile int g_pub_cov, g_pub_cdlg, g_pub_lgv;          /* covered / chat under a dialog / login page in the shown picture */
static int cov_shown(void) { return g_thr ? g_pub_cov : g_st.covered; }
static int cdlg_shown(void) { return g_thr ? (g_pub_cdlg && g_st.chat_dlg) : g_st.chat_dlg; }
static char *g_seen_w[8]; static DWORD g_seen_t[8];
static int ui_kind(char *w)                                 /* 1 own F4, 2 another commander's, 0 not one */
{
    if (!rd(w, 0x2e0) || strcmp(sgr_class(w), "CUserInfoWnd")) return 0;
    return strncmp(w + 4, "@ f4-bk-mi", 10) ? 2 : 1;
}
static int ui_hold_now(char *w)                             /* rule 1 */
{
    int k = ui_kind(w);
    if (!k || !wvis(w)) return 0;
    if (*(int *)(w + 0x2d0) < 16 || *(int *)(w + 0x11c) != 0 || *(int *)(w + 0x2d4) >= 0) return 1;
    if (k == 1 ? cmd_ready() : oth_ready()) return 0;
    static char *ww; static DWORD t0;                      /* the data: 3 s at most for this window */
    if (ww != w) { ww = w; t0 = GetTickCount(); }
    return GetTickCount() - t0 < 3000;
}
static int win_held(char *w)
{
    for (int i = 0; i < g_st.nhold; i++) if (g_st.hold[i] == w) return 1;
    int mine = 0;
    for (int i = 0; i < g_st.nskw; i++) if (g_st.skw[i].wp == w) mine = 1;
    if (!mine || !g_thr) return 0;
    int pub = 0;
    EnterCriticalSection(&g_lock);
    for (int i = 0; i < g_pub_nw; i++) if (g_pub_wins[i] == w) pub = 1;
    LeaveCriticalSection(&g_lock);
    if (pub) return 0;
    DWORD now = GetTickCount(); int slot = -1;
    for (int i = 0; i < 8; i++) if (g_seen_w[i] == w && now - g_seen_t[i] < 5000) slot = i;
    if (slot < 0) {                                        /* first frame of this window: from now */
        for (int i = 0; i < 8 && slot < 0; i++) if (!g_seen_w[i] || now - g_seen_t[i] >= 5000) slot = i;
        if (slot < 0) slot = 0;
        g_seen_w[slot] = w; g_seen_t[slot] = now;
    }
    return now - g_seen_t[slot] < 700;
}
static void __fastcall skin_draw_glass(char *w)
{
    if (!skin_live()) { call_orig(w); return; }
    if (win_held(w)) return;
    int dx = g_st.DX;
    glass_rect(*(int *)(w + 0x118) + dx, *(int *)(w + 0x11c), *(int *)(w + 0x120) + dx, *(int *)(w + 0x124));
}
/* the map under a slid-in quick menu (user 10-28 22:05 "the black below it"): without F52 the game narrows MapWnd
   while the quick menu is out, so the frame under the menu stayed black.  MapWnd's draw (0049ba40) runs here with
   the window's rect widened to the frame's right edge for that one call and put back afterwards */
typedef void (__attribute__((thiscall)) *setvp_fn)(void *cg, int *rect, int *clip);
/* (user 10-29 22:30 "the picture is a mess" while a recording plays): the map draw 0049ba40 prints its debug lines
   (FPS, FindCount, GT, WinPortalCount ...) when map +0x969 or the recorder's playing flag (*0x6ba818 +0x50) is set -
   for the map draw only the flag reads 0 (it is read nowhere else in it).  [hud] replay_debug=1 keeps the lines. */
static void replay_draw(void (__fastcall *orig)(char *), char *w)
{
    static int keep = -1;
    if (keep < 0) keep = GetPrivateProfileIntA("hud", "replay_debug", 0, ".\\GORender.ini") != 0;
    char *rc = *(char **)0x6ba818;
    char was = rd(rc, 0x60) ? rc[0x50] : 0;
    if (was && !keep && !w[0x969]) rc[0x50] = 0;
    interp_begin();                                     /* (11-02) units between their steps (sghud_interp.h) */
    orig(w);
    interp_end();
    if (was) rc[0x50] = was;
}
static void __fastcall map_draw_full(char *w)
{
    VtHook *h = vth_find(*(void ***)w);
    if (!h) return;
    void (__fastcall *orig_)(char *) = (void (__fastcall *)(char *))h->orig[11];
#define orig(w) replay_draw(orig_, w)
    int *abs = (int *)(w + 0x118), *rel = (int *)(w + 0x128), dx = g_st.DX, fr = 800 + dx;
    if (!skin_live() || g_st.covered || abs[0] != -dx || abs[2] >= fr || abs[2] < 400) { orig(w); return; }
    int sa[4], sr[4]; memcpy(sa, abs, 16); memcpy(sr, rel, 16);
    abs[2] = fr; rel[2] = fr - abs[0];
    char *cg = *(char **)0x6ba7d0;
    int clip[4] = { -dx, 0, fr, 600 };
    ((setvp_fn)0x438100)(cg, abs, clip);
    orig(w);
    memcpy(abs, sa, 16); memcpy(rel, sr, 16);
    ((setvp_fn)0x438100)(cg, abs, clip);
#undef orig
}
static void __fastcall skin_draw_art(char *w);
static void __fastcall skin_draw_keep(char *w);
static void skin_hook(char *w, int mode)
{
    void **cur = *(void ***)w;
    if (vth_find(cur) || !rd(cur - 1, (VT_SLOTS + 1) * 4)) return;      /* hooked already / unreadable */
    VtHook *h = NULL;
    for (int i = 0; i < g_nvth; i++) if (g_vth[i].orig == cur && g_vth[i].mode == mode) { h = &g_vth[i]; break; }
    if (!h) {
        if (g_nvth >= 64) return;
        h = &g_vth[g_nvth++];
        h->orig = cur; h->mode = mode;
        memcpy(h->copy, cur - 1, sizeof h->copy);
        h->copy[1 + 11] = mode == HK_GLASS ? (void *)skin_draw_glass : mode == HK_MAP ? (void *)map_draw_full :
                          mode == HK_ART ? (void *)skin_draw_art : mode == HK_KEEP ? (void *)skin_draw_keep : (void *)skin_draw_none;
        if (mode == HK_NONE && cur[12] == (void *)0x561370) h->copy[1 + 12] = (void *)skin_draw_none12;   /* (14:40) CInsideOptionWnd only */
    }
    *(void ***)w = h->copy + 1;
}

/* the re-skinned windows: class -> title (its art title is gone with the background).
   art = 1: the window draws its art AND its content (lists, texts) in one draw function (CMailDlg 00540210 ...):
   skin_draw_art runs it, then turns everything outside the content holes into glass and, inside them, only the black
   art background (the texts / lines stay); decor = what the HUD draws instead of the art (window coordinates) */
enum { DC_FIELD = 100, DC_BOX = 0, DC_HEAD, DC_TAB, DC_LINE, DC_LABEL, DC_TITLE, DC_NOTE, DC_GLASS, DC_PASS, DC_SOLID };
typedef struct { unsigned char kind; short x0, y0, x1, y1; const WCHAR *en, *cn, *tw; } SkinDecor;
typedef struct { const char *cls; const WCHAR *en, *cn, *tw; int art; short holes[8][4]; int nholes; const SkinDecor *decor; int ndecor; } SkinWin;
static const SkinDecor DEC_MAIL[] = {
    { DC_BOX, 18, 30, 628, 368, 0, 0, 0 },
    { DC_TAB, 35, 2, 165, 26, L"READ SGMAIL", L"收件箱", L"收件匣" },
    { DC_TAB, 165, 2, 295, 26, L"WRITE SGMAIL", L"写邮件", L"寫郵件" },
    { DC_HEAD, 32, 42, 148, 62, L"FROM", L"寄件人", L"寄件人" },
    { DC_HEAD, 148, 42, 530, 62, L"SUBJECT", L"主题", L"主題" },
    { DC_HEAD, 530, 42, 612, 62, L"DATE", L"日期", L"日期" },
};
static const SkinDecor DEC_MAILW[] = {                /* (11-01 12:56) the WRITE page: to, subject, the letter */
    { DC_BOX, 18, 30, 628, 368, 0, 0, 0 },
    { DC_TAB, 35, 2, 165, 26, L"READ SGMAIL", L"收件箱", L"收件匣" },
    { DC_TAB, 165, 2, 295, 26, L"WRITE SGMAIL", L"写邮件", L"寫郵件" },
    { DC_HEAD, 32, 42, 148, 62, L"TO", L"收件人", L"收件人" },
    { DC_HEAD, 32, 64, 148, 83, L"SUBJECT", L"主题", L"主題" },
    { DC_FIELD, 150, 42, 612, 62, 0, 0, 0 },
    { DC_FIELD, 150, 64, 612, 83, 0, 0, 0 },
    { DC_FIELD, 32, 85, 597, 323, 0, 0, 0 },
};
static const SkinDecor DEC_BBS[] = {                  /* the LIST page (box down to the game's close button, 11-02 17:44) */
    { DC_BOX, 12, 28, 621, 398, 0, 0, 0 },
    { DC_HEAD, 32, 44, 93, 61, L"POST#", L"编号", L"編號" },
    { DC_HEAD, 93, 44, 160, 61, L"DATE", L"日期", L"日期" },
    { DC_HEAD, 160, 44, 241, 61, L"AUTHOR", L"作者", L"作者" },
    { DC_HEAD, 241, 44, 563, 61, L"SUBJECT", L"主题", L"主題" },
    { DC_HEAD, 563, 44, 609, 61, L"HIT#", L"点阅", L"點閱" },
    { DC_FIELD, 152, 324, 261, 342, 0, 0, 0 },
    { DC_FIELD, 264, 324, 452, 344, 0, 0, 0 },
};
static const SkinDecor DEC_BBSR[] = {                 /* (user 11-02 17:44) the READ page: its own POST# / AUTHOR row */
    { DC_BOX, 12, 28, 621, 398, 0, 0, 0 },
};
static const SkinDecor DEC_BBSW[] = {                 /* the WRITE page: subject, the text */
    { DC_BOX, 12, 28, 621, 398, 0, 0, 0 },
    { DC_HEAD, 32, 44, 142, 61, L"SUBJECT", L"主题", L"主題" },
    { DC_FIELD, 142, 44, 609, 61, 0, 0, 0 },
};
static const SkinDecor DEC_HOF[] = {
    { DC_BOX, 19, 28, 609, 363, 0, 0, 0 },
    { DC_LABEL, 305, 369, 428, 392, L"ACTIVE HEROES:", L"在线英雄：", L"線上英雄：" },
};
static const SkinDecor DEC_EXIT[] = {
    { DC_BOX, 9, 26, 518, 217, 0, 0, 0 },
    { DC_TITLE, 24, 2, 240, 24, L"LEAVE THE BATTLE", L"离开战场", L"離開戰場" },
    { DC_NOTE, 25, 185, 330, 212, L"Are you sure you wish to exit?", L"确定要离开吗？", L"確定要離開嗎？" },
};
static const SkinDecor DEC_RESULT[] = {
    { DC_BOX, 80, 30, 415, 372, 0, 0, 0 },
    { DC_BOX, 437, 30, 725, 372, 0, 0, 0 },
    { DC_TITLE, 90, 6, 300, 28, L"BATTLE RESULT", L"战斗结算", L"戰鬥結算" },
    { DC_HEAD, 87, 41, 250, 57, L"COMMANDER", L"指挥官", L"指揮官" },
    { DC_HEAD, 260, 41, 405, 57, L"FACTION", L"阵营信息", L"陣營資訊" },
    { DC_HEAD, 87, 145, 250, 161, L"TROOPS", L"部队信息", L"部隊資訊" },
    { DC_HEAD, 262, 145, 403, 161, L"RESOURCES", L"资源", L"資源" },
};
static const SkinDecor DEC_BOARD[] = {
    { DC_SOLID, -200, 0, 1100, 600, 0, 0, 0 },
    { DC_BOX, 8, 21, 539, 495, 0, 0, 0 },
    { DC_BOX, 562, 22, 790, 506, 0, 0, 0 },
    { DC_BOX, 12, 503, 220, 596, 0, 0, 0 },
    { DC_BOX, 222, 503, 532, 596, 0, 0, 0 },
    { DC_TITLE, 10, 0, 180, 13, L"STRATEGIC MAP", L"战略地图", L"戰略地圖" },
    { DC_HEAD, 704, 30, 776, 50, L"MAP INFO", L"地图信息", L"地圖資訊" },
};
static const SkinDecor DEC_USERINFO[] = {            /* (17:31) the commander info: the HUD draws it all (paint_userinfo) */
    { DC_PASS, 201, 64, 279, 131, 0, 0, 0 },           /* the game's portrait */
};
static const SkinDecor DEC_ALERT[] = {               /* (11-01 14:40) CAlertWnd 507 x 233: a message, OK / CANCEL */
    { DC_BOX, 30, 36, 487, 196, 0, 0, 0 },
    { DC_TITLE, 40, 4, 260, 30, L"MESSAGE", L"讯息", L"訊息" },
};
static const SkinDecor DEC_OTHERINFO[] = {           /* (11-01 14:17) another commander's info: the HUD draws it all */
    { DC_PASS, 201, 66, 268, 127, 0, 0, 0 },           /* the game's portrait */
};
static const SkinDecor DEC_USEEXP[] = {             /* (user 11-01 16:40) Assign XP (CUseExpWnd, quick menu 分配经验) */
    { DC_BOX, 18, 60, 318, 330, 0, 0, 0 },
    { DC_BOX, 328, 60, 780, 330, 0, 0, 0 },
    { DC_BOX, 18, 355, 778, 562, 0, 0, 0 },
    { DC_TITLE, 30, 4, 300, 28, L"ASSIGN XP", L"分配经验", L"分配經驗" },
    { DC_HEAD, 30, 40, 220, 58, L"SUBORDINATES", L"部下", L"部下" },
    { DC_HEAD, 340, 40, 560, 58, L"STATUS", L"状态", L"狀態" },
    { DC_HEAD, 30, 337, 260, 355, L"UNIT RESERVES", L"后备单位", L"後備單位" },
    { DC_LABEL, 690, 372, 752, 392, L"SORT BY", L"排序", L"排序" },
};
static const SkinDecor DEC_BOARDDETAIL[] = {
    { DC_SOLID, -200, 0, 1100, 600, 0, 0, 0 },
    { DC_PASS, 12, 25, 535, 491, 0, 0, 0 },
};
static const SkinWin SKIN_WINS[] = {
    { "CQuickMenuWnd", NULL, NULL, NULL, 0, {{0}}, 0, NULL, 0 },
    { "CCtrlPermissionWnd", L"BATTLE PERMISSION", L"加入许可", L"加入許可", 0, {{0}}, 0, NULL, 0 },
    { "CMailDlg", NULL, NULL, NULL, 1, {{ 32, 62, 612, 355 }}, 1, DEC_MAIL, sizeof DEC_MAIL / sizeof *DEC_MAIL },
    { "CBBSDlg", NULL, NULL, NULL, 1, {{ 32, 61, 609, 297 }, { 30, 298, 612, 318 }}, 2, DEC_BBS, sizeof DEC_BBS / sizeof *DEC_BBS },
    { "CPollWnd", NULL, NULL, NULL, 1, {{ 0, 0, 2000, 2000 }}, 1, NULL, 0 },
    { "CCtrlExitWnd", NULL, NULL, NULL, 1, {{ 21, 36, 504, 182 }}, 1, DEC_EXIT, sizeof DEC_EXIT / sizeof *DEC_EXIT },
    { "CBattleResultWnd", NULL, NULL, NULL, 1, {{ 87, 60, 250, 131 }, { 260, 57, 405, 134 }, { 87, 162, 250, 355 },
      { 262, 162, 403, 355 }, { 455, 67, 718, 355 }, { 530, 40, 645, 58 }}, 6, DEC_RESULT, sizeof DEC_RESULT / sizeof *DEC_RESULT },
    { "CBoardWnd", NULL, NULL, NULL, 1, {{ 236, 2, 352, 20 }}, 1, DEC_BOARD, sizeof DEC_BOARD / sizeof *DEC_BOARD },
    { "CCtrlBoardDetail", NULL, NULL, NULL, 1, {{ 565, 30, 697, 162 }, { 565, 200, 770, 500 },
      { 225, 529, 529, 593 }, { 15, 508, 217, 530 }}, 4,
      DEC_BOARDDETAIL, sizeof DEC_BOARDDETAIL / sizeof *DEC_BOARDDETAIL },
    { "CUserInfoWnd", NULL, NULL, NULL, 1, {{ 201, 64, 279, 131 }}, 1, DEC_USERINFO, sizeof DEC_USERINFO / sizeof *DEC_USERINFO },
    { "CHallOfFameDlg", NULL, NULL, NULL, 1, {{ 33, 66, 595, 352 }, { 430, 369, 480, 392 }, { 30, 368, 300, 398 }}, 3,
      DEC_HOF, sizeof DEC_HOF / sizeof *DEC_HOF },
    { "CAlertWnd", NULL, NULL, NULL, 1, {{ 40, 45, 477, 187 }}, 1, DEC_ALERT, sizeof DEC_ALERT / sizeof *DEC_ALERT },
    { "CUserInfoWnd#other", NULL, NULL, NULL, 1, {{ 201, 66, 268, 127 }}, 1, DEC_OTHERINFO, sizeof DEC_OTHERINFO / sizeof *DEC_OTHERINFO },
    { "CUseExpWnd", NULL, NULL, NULL, 1, {{ 22, 64, 314, 325 }, { 332, 65, 577, 324 }, { 582, 65, 775, 324 },
      { 22, 362, 681, 553 }}, 4, DEC_USEEXP, sizeof DEC_USEEXP / sizeof *DEC_USEEXP },
    { "CMailDlg#write", NULL, NULL, NULL, 1, {{ 150, 42, 612, 62 }, { 150, 64, 612, 83 }, { 32, 84, 597, 323 }}, 3,
      DEC_MAILW, sizeof DEC_MAILW / sizeof *DEC_MAILW },   /* (found by skin_def_of, not by class) */
    { "CBBSDlg#read", NULL, NULL, NULL, 1, {{ 32, 61, 609, 297 }, { 30, 298, 612, 318 }}, 2, DEC_BBSR, sizeof DEC_BBSR / sizeof *DEC_BBSR },
    { "CBBSDlg#write", NULL, NULL, NULL, 1, {{ 142, 42, 609, 62 }, { 32, 61, 609, 297 }, { 30, 298, 612, 318 }}, 3,
      DEC_BBSW, sizeof DEC_BBSW / sizeof *DEC_BBSW },
};
static int mail_write_page(char *w)              /* the READ tab shown as a button = the WRITE page */
{
    char **k; int n = wkids(w, &k);
    for (int i = 0; i < n; i++)
        if (rd(k[i], 0x160) && k[i][0x155] && !strncmp(k[i] + 4, "@ mld-mbt.xpf 0", 15) && !k[i][4 + 15]) return 1;
    return 0;
}
static int bbs_page(char *w)                    /* (11-02) 1 = READ (bbs1-bts shown), 2 = WRITE (bbs2-bts), 0 = the list */
{
    char **k; int n = wkids(w, &k);
    for (int i = 0; i < n; i++)
        if (rd(k[i], 0x160) && k[i][0x155]) {
            if (!strncmp(k[i] + 4, "@ bbs1-bts.xpf", 14)) return 1;
            if (!strncmp(k[i] + 4, "@ bbs2-bts.xpf", 14)) return 2;
        }
    return 0;
}
static const SkinWin *skin_def_of(char *w)
{
    const char *cls = sgr_class(w);
    if (!strcmp(cls, "CUserInfoWnd") && strncmp(w + 4, "@ f4-bk-mi", 10))   /* another commander's (0x27 sub 1) */
        for (unsigned j = 0; j < sizeof SKIN_WINS / sizeof *SKIN_WINS; j++) if (!strcmp(SKIN_WINS[j].cls, "CUserInfoWnd#other")) return &SKIN_WINS[j];
    if (!strcmp(cls, "CMailDlg") && mail_write_page(w))
        for (unsigned j = 0; j < sizeof SKIN_WINS / sizeof *SKIN_WINS; j++) if (!strcmp(SKIN_WINS[j].cls, "CMailDlg#write")) return &SKIN_WINS[j];
    if (!strcmp(cls, "CBBSDlg")) {
        int pg = bbs_page(w);
        if (pg) for (unsigned j = 0; j < sizeof SKIN_WINS / sizeof *SKIN_WINS; j++)
            if (!strcmp(SKIN_WINS[j].cls, pg == 1 ? "CBBSDlg#read" : "CBBSDlg#write")) return &SKIN_WINS[j];
    }
    for (unsigned j = 0; j < sizeof SKIN_WINS / sizeof *SKIN_WINS; j++) if (!strcmp(cls, SKIN_WINS[j].cls)) return &SKIN_WINS[j];
    return NULL;
}
static unsigned short g_art_save[1440 * 600];
/* (user 10-28 23:31 "after closing the battle result the HUD left ghosts"): a window that is still visible but whose
   draw paints nothing any more (the result window after its close) is not skinned: the frame is left as it was and
   its decor is not drawn (skin_window checks g_art_empty) */
static char *g_art_empty[8]; static DWORD g_art_empty_t[8];
/* the battle result slides its two panels in / out (0040d000: +0x394 < 16 opening, +0x398 != -1 closing): while it
   moves the game's own picture is shown (the skin's holes / decor are for the panels at rest) */
static int art_moving(char *w)
{
    if (!rd(w, 0x3a0) || strcmp(sgr_class(w), "CBattleResultWnd")) return 0;
    return *(int *)(w + 0x394) < 0x10 || *(int *)(w + 0x398) != -1;
}
static int art_is_empty(char *w)
{
    for (int i = 0; i < 8; i++) if (g_art_empty[i] == w && GetTickCount() - g_art_empty_t[i] < 500) return 1;
    return 0;
}
static void art_mark(char *w, int empty)
{
    int slot = -1;
    for (int i = 0; i < 8; i++) if (g_art_empty[i] == w) slot = i;
    if (!empty) { if (slot >= 0) g_art_empty[slot] = NULL; return; }
    if (slot < 0) for (int i = 0; i < 8; i++) if (!g_art_empty[i] || GetTickCount() - g_art_empty_t[i] >= 500) { slot = i; break; }
    if (slot < 0) slot = 0;
    g_art_empty[slot] = w; g_art_empty_t[slot] = GetTickCount();
}
static void skin_art_run(char *w, const SkinWin *def);
static void __fastcall skin_draw_keep(char *w)
{
    static const SkinWin keep = { "", NULL, NULL, NULL, 1, {{ -4000, -4000, 4000, 4000 }}, 1, NULL, 0 };
    skin_art_run(w, &keep);
}
static void __fastcall skin_draw_art(char *w) { skin_art_run(w, skin_def_of(w)); }
/* (11-01 user "does the mercenary work") a game dialog over a skinned window - the 开/关 "Are you certain ...?" confirm
   of F4 - must stay visible: while the app's modal window (+0xc18) is up and is not one the HUD skins itself, F4
   shows the game's own picture (the HUD page would cover the question and its YES / NO) */
static char *g_app_last;
static __attribute__((unused)) int foreign_modal(void)
{
    char *m = g_app_last ? *(char **)(g_app_last + 0xc18) : NULL;
    if (!rd(m, 0x160) || !m[0x155]) return 0;
    const char *cls = sgr_class(m);
    for (unsigned j = 0; j < sizeof SKIN_WINS / sizeof *SKIN_WINS; j++) if (!strcmp(cls, SKIN_WINS[j].cls)) return 0;
    { static const char *last; if (last != cls) { last = cls; sgr_log("HUD foreign modal: %s", cls); } }
    return 1;
}
static void skin_art_run(char *w, const SkinWin *def)
{
    char *cg = *(char **)0x6ba7d0;
    if (skin_live() && win_held(w)) return;              /* (11-01 14:40) held: not drawn yet */
    /* (14:40) a modal the HUD does not skin (the mercenary confirm) no longer turns F4 back to the game's own look: it is
       left open in the HUD (foreign_above) and seen on top of the HUD's page */
    if (def && def->cls && !strcmp(def->cls, "CUserInfoWnd") && !cmd_ready()) { call_orig(w); return; }   /* (11-01) */
    if (def && def->cls && !strcmp(def->cls, "CUserInfoWnd#other") && !oth_ready()) { call_orig(w); return; }
    if (skin_live() && art_moving(w)) return;            /* (16:51 user "after 关闭 the old look must not show"): the
                                                            result window sliding in / out is not drawn - it appears at
                                                            rest with the new look and is gone at once on 关闭 */
    if (!skin_live() || !def || !rd(cg, 0x84) || art_moving(w)) { call_orig(w); return; }
    unsigned short *org = *(unsigned short **)(cg + 0x5c);
    int pitch = *(int *)(cg + 0x60), vl = *(int *)(cg + 0x64), vt = *(int *)(cg + 0x68), dx = g_st.DX;
    int wx = *(int *)(w + 0x118) + dx, wy = *(int *)(w + 0x11c);       /* window, frame pixels */
    int x0 = wx - vl, y0 = wy - vt, x1 = *(int *)(w + 0x120) + dx - vl, y1 = *(int *)(w + 0x124) - vt;
    if (x0 < *(int *)(cg + 0x74)) x0 = *(int *)(cg + 0x74);
    if (y0 < *(int *)(cg + 0x78)) y0 = *(int *)(cg + 0x78);
    if (x1 > *(int *)(cg + 0x7c)) x1 = *(int *)(cg + 0x7c);
    if (y1 > *(int *)(cg + 0x80)) y1 = *(int *)(cg + 0x80);
    int ww = x1 - x0;
    if (!org || ww <= 0 || y1 <= y0 || ww > 1440 || y1 - y0 > 600) { call_orig(w); return; }
    for (int y = y0; y < y1; y++) memcpy(g_art_save + (y - y0) * ww, org + (long)y * pitch + x0, ww * 2);
    call_orig(w);
    if (def->ndecor && !strcmp(sgr_class(w), "CBattleResultWnd")) {   /* drew nothing (closed but still visible) */
        long changed = 0, area = (long)ww * (y1 - y0);
        for (int y = y0; y < y1 && changed * 50 < area; y++) {
            unsigned short *p = org + (long)y * pitch + x0, *q = g_art_save + (y - y0) * ww;
            for (int x = 0; x < ww; x++) if (p[x] != q[x]) changed++;
        }
        int empty = changed * 50 < area;                 /* under 2 % of its pixels */
        art_mark(w, empty);
        if (empty) return;
    }
    int ox = vl - wx, oy = vt - wy;                     /* viewport pixel -> window pixel */
    for (int y = y0; y < y1; y++) {
        unsigned short *p = org + (long)y * pitch + x0, *q = g_art_save + (y - y0) * ww;
        int ry = y + oy;
        for (int x = x0; x < x1; x++, p++, q++) {
            int rx = x + ox, hole = 0;
            for (int h = 0; h < def->nholes; h++)
                if (rx >= def->holes[h][0] && rx < def->holes[h][2] && ry >= def->holes[h][1] && ry < def->holes[h][3]) { hole = 1; break; }
            int pass = 0;
            for (int h = 0; h < def->ndecor && !pass; h++) {
                const SkinDecor *c = &def->decor[h];
                if (c->kind == DC_PASS && rx >= c->x0 && rx < c->x1 && ry >= c->y0 && ry < c->y1) pass = 1;
            }
            if (pass) continue;                          /* drawn by a child before (the map): as it is */
            int solid = 0;
            for (int h = 0; h < def->ndecor && !solid; h++) {
                const SkinDecor *c = &def->decor[h];
                if (c->kind == DC_SOLID && rx >= c->x0 && rx < c->x1 && ry >= c->y0 && ry < c->y1) solid = 1;
            }
            if (solid && !(hole && ((*p >> 11) > 11 || ((*p >> 5) & 63) > 23 || (*p & 31) > 11))) {
                *p = (unsigned short)((2 << 11) | (5 << 5) | 5);   /* a full-screen window: an even dark ground */
                continue;
            }
            if (hole && ((*p >> 11) > 11 || ((*p >> 5) & 63) > 23 || (*p & 31) > 11)) continue;   /* content: text, lines (dark art = background) */
            int glass = hole;
            for (int h = 0; h < def->ndecor && !glass; h++) {
                const SkinDecor *c = &def->decor[h];
                if ((c->kind == DC_BOX || c->kind == DC_TAB || c->kind == DC_GLASS) && rx >= c->x0 && rx < c->x1 && ry >= c->y0 && ry < c->y1) glass = 1;
            }
            if (!glass) { *p = *q; continue; }           /* outside the panel: the map as it was */
            unsigned v = *q, r = v >> 11, g = (v >> 5) & 63, b = v & 31;   /* a darker glass: text panels */
            *p = (unsigned short)(((r / 4 + 1) << 11) | ((g / 4 + 3) << 5) | (b / 4 + 3));
        }
    }
}
static const SkinLabel *skin_label(const char *nm)
{
    char file[32]; int fr, row;
    if (nm[0] == '#' && sscanf(nm, "# %31s %d %d", file, &row, &fr) == 3) fr += row * 100;   /* "# file row frame" */
    else if (nm[0] != '@' || sscanf(nm, "@ %31s %d", file, &fr) != 2) return NULL;
    for (unsigned j = 0; j < sizeof SKIN_LABELS / sizeof *SKIN_LABELS; j++)
        if (SKIN_LABELS[j].frame == fr && !strcmp(SKIN_LABELS[j].file, file)) return &SKIN_LABELS[j];
    for (unsigned j = 0; j < sizeof SKIN_LABELS / sizeof *SKIN_LABELS; j++)   /* background art: any of its frames */
        if (SKIN_LABELS[j].kind == SK_HIDE && !strcmp(SKIN_LABELS[j].file, file)) return &SKIN_LABELS[j];   /* (the board's
                                                         tab strip shows the page as its frame, user 10-29 00:13) */
    return NULL;
}
static void skin_rect(char *b, int DX, short *r)
{
    r[0] = (short)(*(int *)(b + 0x118) + DX); r[1] = (short)*(int *)(b + 0x11c);
    r[2] = (short)(*(int *)(b + 0x120) + DX); r[3] = (short)*(int *)(b + 0x124);
}
static void skin_children(HudState *s, char *w, int DX, int depth)
{
    char **k; int n = wkids(w, &k);
    for (int i = 0; i < n; i++) {
        char *b = k[i];
        if (!rd(b, 0x2c0) || *(int *)(b + 0x130) <= 0) continue;
        const char *cls = sgr_class(b);
        char nm[96]; lstrcpynA(nm, b + 4, sizeof nm);
        const SkinLabel *L = skin_label(nm);
        if (!b[0x155]) {                                /* a hidden tab button = the page shown (not the quick menu: */
            if (L && L->kind == SK_TAB && strncmp(nm, "@ qm-", 5) && s->nsk < 160) {   /* its tabs share a place) */
                HudSkin *e = &s->sk[s->nsk++];
                skin_rect(b, DX, &e->x0);
                e->kind = SK_TAB_ON; e->color = 0; e->accent = 1;
                lstrcpynW(e->label, g_lang == 1 ? L->cn : g_lang == 2 ? L->tw : L->en, 36);
            }
            continue;
        }
        if (L && L->kind == SK_HIDE) { skin_hook(b, HK_NONE); if (s->nhid < 64) s->hid[s->nhid++] = b; continue; }   /* art */
        if (L && L->kind == SK_KEEP) { skin_hook(b, HK_KEEP); continue; }     /* art with content: its dark part -> glass */
        if (!strcmp(cls, "CCtrlButton") || !strcmp(cls, "CCtrlButtonEx")) {
            if (s->nsk >= 160) continue;
            HudSkin *e = &s->sk[s->nsk];
            skin_rect(b, DX, &e->x0);
            e->color = *(unsigned short *)(b + 0x2b8); e->accent = 0;
            if (L) {
                lstrcpynW(e->label, g_lang == 1 ? L->cn : g_lang == 2 ? L->tw : L->en, 36);
                e->kind = (unsigned char)L->kind;
                if (L->kind == SK_RADIO) e->accent = (*(unsigned *)(b + 0x2e4) & 0x30) == 0x20;   /* the chosen one */
                /* (user 10-31 13:13 "an order cannot be cancelled, it comes back"): the ASSEMBLE / AVOID buttons are
                   on/off switches (+0x749, 0046e6f0): selecting a province switches on the ones it already has
                   (004660e0); clicking a lit one sends 0x101 = remove (00459120) - so it must look lit */
                if (L->frame >= 300 && !strcmp(L->file, "bdw-fdbt.xpf")) e->accent = b[0x749] != 0;
                if (L->kind == SK_TAB && strncmp(nm, "@ qm-", 5)) e->accent = 2;              /* a page tab strip */
            } else if (nm[0] != '@' && nm[0] != '#' && depth == 0 && (!strcmp(sgr_class(w), "CBBSDlg") || !strcmp(sgr_class(w), "CMailDlg"))) {
                /* (user 10-31 16:59 "the board shows the text twice"): a board / mail list row is a button named with
                   the row's text; the dialog draws the row itself, so the HUD only lights it (no label of its own) */
                e->label[0] = 0; e->kind = SK_TEXT;
            } else if (nm[0] && nm[0] != '@' && nm[0] != '#') {
                for (char *c = nm; *c; c++) if ((unsigned char)*c < 0x20) *c = ' ';   /* tabs between the columns */
                for (int q = (int)strlen(nm); q > 0 && nm[q - 1] == ' '; q--) nm[q - 1] = 0;
                MultiByteToWideChar(CP_ACP, 0, nm, -1, e->label, 36);
                e->kind = SK_TEXT;
            } else if (!nm[0] && depth == 0 && skin_def_of(w) && skin_def_of(w)->art) {
                /* (user 10-29 20:47 "the notice text overlaps"): a list row of an art dialog (board, mail) shows up
                   under the mouse and draws its text again in another font over the dialog's own row - hidden, the
                   HUD lights the row instead */
                e->label[0] = 0; e->kind = SK_TEXT;
            } else {                                    /* unknown art: the game's own button stays (logged once) */
                static unsigned seen[128]; static int nseen; unsigned hsh = 5381;
                for (const char *c = nm; *c; c++) hsh = hsh * 33 + (unsigned char)*c;
                hsh ^= (unsigned)(size_t)sgr_class(w)[1] << 24;
                int f = 0; for (int q = 0; q < nseen; q++) if (seen[q] == hsh) { f = 1; break; }
                if (!f && nseen < 128) { seen[nseen++] = hsh;
                    sgr_log("HUD skin: unknown art '%s' (%s) in %s at %d,%d %dx%d", nm, cls, sgr_class(w),
                            *(int *)(b + 0x118) - *(int *)(w + 0x118), *(int *)(b + 0x11c) - *(int *)(w + 0x11c),
                            *(int *)(b + 0x120) - *(int *)(b + 0x118), *(int *)(b + 0x124) - *(int *)(b + 0x11c)); }
                continue;
            }
            skin_hook(b, HK_NONE);
            s->skp[s->nsk] = b;
            s->nsk++;
        } else if (depth < 4 && (strncmp(cls, "CCtrl", 5) || !strcmp(cls, "CCtrlExitWnd") || !strcmp(cls, "CCtrlRadioButton")
                                 || !strcmp(cls, "CCtrlMarkerControlBox") || !strcmp(cls, "CCtrlBoardDetail")
                                 || !strcmp(cls, "CCtrlCombo"))) {
            const SkinWin *d = skin_def_of(b);
            if (d && d->art) skin_hook(b, HK_ART);       /* an inner art window (CPollWnd): glass + its texts */
            skin_children(s, b, DX, depth + 1);          /* an inner window: its buttons too */
        }
    }
}
static void skin_window(HudState *s, char *w, const SkinWin *def, int DX)
{
    if (s->nskw >= 8) return;
    if (!strcmp(def->cls, "CMailDlg") || !strcmp(def->cls, "CBBSDlg")) def = skin_def_of(w);   /* (11-01) its WRITE page has its own decor (board: READ / WRITE, 11-02) */
    /* (user 11-01 14:03 "another commander's info shows my own and cannot be closed"): the same class opens for
       another player (0x27 sub 1, art "@ f4-bk-nm.xpf", 404 wide, 效力 208..284 / 关闭 301..369 at y 377..404) - its
       own page (14:17 "keep it in the new HUD's look"): CUserInfoWnd#other with that commander's public data */
    if (!strcmp(def->cls, "CUserInfoWnd")) def = skin_def_of(w);
    if (!strncmp(def->cls, "CUserInfoWnd", 12)) {         /* (14:40) it and its children drawn only by the HUD's page */
        skin_hook(w, HK_ART);
        char **k; int n = wkids(w, &k);
        for (int i = 0; i < n; i++) if (rd(k[i], 0x160)) skin_hook(k[i], HK_NONE);
        if (ui_hold_now(w) && s->nhold < 8) s->hold[s->nhold++] = w;
    }
    if (!strcmp(def->cls, "CUserInfoWnd#other")) {
        if (*(int *)(w + 0x2d0) >= 0 && *(int *)(w + 0x2d0) < 15) *(int *)(w + 0x2d0) = 15;   /* the slides, as F4 */
        if (*(int *)(w + 0x2d4) >= 0 && *(int *)(w + 0x2d4) < 15) *(int *)(w + 0x2d4) = 15;
        char nm[64]; int k = 0;
        for (; k < 63 && rd(w + 0x80d + k, 1) && w[0x80d + k]; k++) nm[k] = w[0x80d + k];
        nm[k] = 0;
        if (strcmp(nm, g_oth_name)) { lstrcpynA(g_oth_name, nm, sizeof g_oth_name); g_dirty = 1; }
        if (nm[0] && (strcmp(g_oth_req, nm) || (g_oth_state != 1 && GetTickCount() - g_oth_t > 10000))) oth_fetch_start();
        if (*(int *)(w + 0x2d0) < 16 || *(int *)(w + 0x11c) != 0 || !oth_ready()) return;   /* the game's own until its page is here */
    }
    {   /* (11-01 F4 delay) a window that is a child of the frame AND the app's modal (F4) came here twice a frame and
           its page was painted twice: once is enough */
        HudSkinWnd tmp; skin_rect(w, DX, &tmp.x0);
        for (int i = 0; i < s->nskw; i++)
            if (s->skw[i].def == (unsigned char)(def - SKIN_WINS) && s->skw[i].x0 == tmp.x0 && s->skw[i].y0 == tmp.y0) return;
    }
    skin_hook(w, def->art ? HK_ART : HK_GLASS);
    if (def->art && rd(w, 0x3a0) && !strcmp(sgr_class(w), "CBattleResultWnd") && *(int *)(w + 0x394) < 0x10)
    {                                                    /* (16:51) a result window opening: its report is fetched anew,
                                                            already while it slides in (it is not drawn then) */
        DWORD now = GetTickCount();
        if (now - g_rep_open > 2000) { g_rep_first = now; g_rep_tries = 0; g_rep_state = 0; rep_fetch_start(); }
        g_rep_open = now;
    }
    if (def->art && !strcmp(def->cls, "CUserInfoWnd")) {   /* (17:31) commander info: its data page + the live values */
        /* (user 11-01 03:18 "F4 opens with a delay") the game slides the window down over 16 of its frames (005e1809:
           counter +0x2d0 0..15 = positions from -height, 16 = fill the controls, then 17+); jump to the last slide
           step: the window is at rest two frames after F4 */
        if (*(int *)(w + 0x2d0) >= 0 && *(int *)(w + 0x2d0) < 15) *(int *)(w + 0x2d0) = 15;
        /* closing slides it up over 15 frames (+0x2d4 2..16, +0x2d8 = 3): the same jump, it closes at once */
        if (*(int *)(w + 0x2d4) >= 0 && *(int *)(w + 0x2d4) < 15) *(int *)(w + 0x2d4) = 15;
        DWORD now = GetTickCount();
        if (now - g_cmd_seen > 1500 || (g_cmd_state != 1 && now - g_cmd_t > 4000)) cmd_fetch_start();
        g_cmd_seen = now;
        /* the points added in this window, not sent yet (0x25 on close, 005e0cf0: window +0xe64, 4 dwords) */
        s->ui_ok = rd(w, 0xe74);
        for (int j = 0; j < 4; j++) s->ui_d[j] = s->ui_ok ? *(int *)(w + 0xe64 + 4 * j) : 0;
        { static int prev[4]; if (memcmp(prev, s->ui_d, sizeof prev)) { memcpy(prev, s->ui_d, sizeof prev); g_dirty = 1; } }
        /* (11-01 user "does the mercenary work") the window's own state byte: +0xe78, set from the 0x27 page's last byte
           (004b537c -> 005e09f0) and flipped by the 开/关 confirm (005e0d80); the old guess from the button pictures
           never matched */
        {   int m = *(unsigned char *)(w + 0xe78) ? 1 : 0;
            if (m != s->ui_merc) { s->ui_merc = m; g_dirty = 1; } }
        /* (11-01 02:01 user: "after the update the other data cannot be read"): until the server's commander page
           (honor/cmd.txt) has really arrived - an old server without it, the network refused - the game's own F4 window
           stays as it was, never an empty "loading" page */
        if (!cmd_ready()) return;
        /* (11-01 pre-draw) at counter 15 the window is still at -height (it moves at 16): not skinned there, its page
           would be drawn once off screen for nothing */
        if (*(int *)(w + 0x2d0) < 16 || *(int *)(w + 0x11c) != 0) return;   /* (and not while it leaves: its kept page stays at rest) */
    }
    if (def->art && (art_is_empty(w) || art_moving(w))) return;   /* nothing / moving: no skin */
    HudSkinWnd *sw = &s->skw[s->nskw++];
    skin_rect(w, DX, &sw->x0);
    sw->wp = w;
    sw->title[0] = 0;
    sw->def = (unsigned char)(def - SKIN_WINS); sw->page = 0;
    if (def->en) lstrcpynW(sw->title, g_lang == 1 ? def->cn : g_lang == 2 ? def->tw : def->en, 24);
    skin_children(s, w, DX, 0);
    if (!strncmp(def->cls, "CMailDlg", 8) && mail_write_page(w)) sw->page = 1;   /* (11-01) the tab lit */
    if (!strcmp(def->cls, "CQuickMenuWnd")) {           /* the page title: the tab button that is hidden is the page */
        char **k; int n = wkids(w, &k);
        for (int i = 0; i < n; i++) {
            char *b = k[i]; char nm[64];
            if (!rd(b, 0x160) || b[0x155]) continue;
            lstrcpynA(nm, b + 4, sizeof nm);
            if (!strncmp(nm, "@ qm-ttbt.xpf", 13) && s->nsk < 160) {
                int fr = atoi(nm + 14);
                HudSkin *e = &s->sk[s->nsk++];
                e->x0 = (short)(sw->x0 + 26); e->y0 = (short)(sw->y0 + 14); e->x1 = (short)(sw->x0 + 118); e->y1 = (short)(sw->y0 + 33);
                e->kind = SK_TAB_ON; e->color = 0; e->accent = 0;
                lstrcpynW(e->label, fr == 3 ? T3("QUICK MENU", "快速选单", "快速選單") : L"Q.R.F", 36);
            }
        }
    }
}
/* (14:40) a visible game window the HUD does not skin, drawn after (above) skinned windows it overlaps: the HUD leaves
   its rectangle open, so the game's window is seen on top (the HUD's pages are one layer above the whole frame) */
static void foreign_above(HudState *s, char *w, int DX)
{
    if (!s->nskw || s->nfh >= 4 || !wvis(w) || w == g_map || w == g_panel || w == g_chat) return;
    const char *c = sgr_class(w);
    if (!strcmp(c, "CFieldMapWnd") || !strcmp(c, "CUnitWnd") || !strcmp(c, "CSmallUnitWnd") || !strncmp(c, "CCtrl", 5)) return;
    for (int i = 0; i < s->nhid; i++) if (s->hid[i] == w) return;
    short r[4]; skin_rect(w, DX, r);
    if (r[2] - r[0] < 40 || r[3] - r[1] < 30 || (r[2] - r[0] >= 780 && r[3] - r[1] >= 590)) return;   /* (a whole-frame one: a parent) */
    for (int i = 0; i < s->nskw; i++)                /* an ancestor of a skinned window is under it, not above */
        for (char *p = s->skw[i].wp; rd(p, 0x13c); p = *(char **)(p + 0x138)) if (p == w) return;
    for (int i = 0; i < s->nskw; i++) {
        HudSkinWnd *e = &s->skw[i];
        if (r[2] > e->x0 && r[0] < e->x1 && r[3] > e->y0 && r[1] < e->y1) {
            memcpy(s->fh[s->nfh++], r, sizeof r);
            static const char *lastc; if (lastc != c) { lastc = c; sgr_log("HUD: %s over a skinned window - left open", c); }
            return;
        }
    }
}
static void skin_windows(HudState *s, char *app, char *fw, int DX)
{
    if (g_map) skin_hook(g_map, HK_MAP);
    char *tops[3] = { fw, app ? app + 0x28 : NULL, NULL };
    char *modal = app ? *(char **)(app + 0xc18) : NULL;
    for (int t = 0; t < 2; t++) {
        char **k; int n = tops[t] ? wkids(tops[t], &k) : 0;
        int first = 0;                                  /* (10-28 23:53) a full-screen window (strategic map board) */
        for (int i = 0; i < n; i++)                     /* hides the ones drawn before it (the quick menu behind) */
            if (rd(k[i], 0x160) && k[i][0x155] && *(int *)(k[i] + 0x130) >= 800 && *(int *)(k[i] + 0x134) >= 600
                && strcmp(sgr_class(k[i]), "CFieldMapWnd")) first = i;
        for (int i = first; i < n; i++) {
            char *w = k[i];
            if (!rd(w, 0x160) || !w[0x155]) continue;
            const char *cls = sgr_class(w);
            int sk = 0;
            for (unsigned j = 0; j < sizeof SKIN_WINS / sizeof *SKIN_WINS; j++)
                if (!strcmp(cls, SKIN_WINS[j].cls)) { skin_window(s, w, &SKIN_WINS[j], DX); sk = 1; break; }
            if (!sk) foreign_above(s, w, DX);
        }
    }
    if (rd(modal, 0x160) && modal[0x155]) {
        const char *cls = sgr_class(modal);
        int sk = 0;
        for (unsigned j = 0; j < sizeof SKIN_WINS / sizeof *SKIN_WINS; j++)
            if (!strcmp(cls, SKIN_WINS[j].cls)) { skin_window(s, modal, &SKIN_WINS[j], DX); sk = 1; break; }
        if (!sk) foreign_above(s, modal, DX);
    }
}
