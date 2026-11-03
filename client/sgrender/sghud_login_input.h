/* sghud_login_input.h - part of sghud.c (included in this order; not a header on its own): the login screen: reading its controls and sending the mouse to them */
/* ---- the login screen (user 10-29 21:10: design A, "side menu + login card") ----------------------------------
 * CNewSetupWnd (800 x 600, Bink videos) keeps working underneath; the HUD covers it with the new look and sends the
 * mouse to the game's own controls (main menu CBinkButtons, the CONTINUE dialog's edits and buttons).  Any other page
 * (new commander, options, credits, change password ...) shows the game's own screen.
 * CCtrlEditORG: text = the window name (+4), caret +0x300; the focused control = app +0xc10. */
static void lg_rect(char *w, int DX, short *r)
{
    r[0] = (short)(*(int *)(w + 0x118) + DX); r[1] = (short)*(int *)(w + 0x11c);
    r[2] = (short)(*(int *)(w + 0x120) + DX); r[3] = (short)*(int *)(w + 0x124);
}
enum { LG_MAIN = 1, LG_CONT, LG_CREATE, LG_CHPW, LG_BRIEF, LG_BOOT, LG_HERO, LG_NATION, LG_OPTION, LG_LOAD };
/* the OPTIONS page (CInsideOptionWnd, probed 11-01 in wine):
   +0x2f0 u16 sound volume, +0x2f2 u16 music volume (0..100; the track: x 75..215 of the window, the sound row's centre
   y 120, the music row's y 194); +0x2f4 bytes footprints, unit speech, sound, music; +0x2f8 record battles, tutorial,
   curse filter, help messages; +0x2fc news messages, units targetable by allies, 3D sound; +0x300 scroll rate 0..4;
   +0x304 3D sound mode (headphones / 2 speakers / surround).  The tab shown: its own tab button is hidden. */
enum { OPT_TAB0, OPT_TAB1, OPT_OK, OPT_CANCEL,
       OPT_T0 = 4,          /* tab 0 rows 0..4 (y 37 + 37 r): ON +0 / OFF +1 */
       OPT_3D = 14,         /* 3 modes */
       OPT_CHG = 17,        /* text colour, macro */
       OPT_T1 = 19,         /* tab 1 rows 0..5 (y 72 + 36 r): ON / OFF */
       OPT_SCR = 31,        /* scroll rate 0..4 */
       OPT_DOK = 36, OPT_DCANCEL, OPT_DDEFAULT,   /* a dialog's OK / CANCEL / DEFAULT */
       OPT_N = 39 };
static char *g_opt_cdlg, *g_opt_mdlg;     /* the colour picker (CColorSelectDlg) / macro (CMacroDlg) dialogs, when up */
static short g_mac_ed[10][4];             /* the macro edits (frame px) */
static void read_option(HudState *s, char *ow, int DX)
{
    char *iw = find_child(ow, "CInsideOptionWnd", NULL);
    if (!iw || !rd(iw, 0x308)) return;
    s->lg = LG_OPTION;
    memset(s->lg_ot, 0, sizeof s->lg_ot); memset(s->lg_oon, 0, sizeof s->lg_oon);
    int ix = *(int *)(iw + 0x118), iy = *(int *)(iw + 0x11c);
    char **k; int n = wkids(iw, &k);
    for (int i = 0; i < n; i++) {
        char *w = k[i];
        if (!rd(w, 0x160)) continue;
        const char *nm = w + 4;
        int y = *(int *)(w + 0x11c) - iy, id = -1;
        if (!strcmp(nm, "@ opw-fd.xpf 0")) id = OPT_TAB0;
        else if (!strcmp(nm, "@ opw-fd.xpf 3")) id = OPT_TAB1;
        else if (!strcmp(nm, "@ opw-ok.xpf 0")) id = OPT_OK;
        else if (!strcmp(nm, "@ opw-ok.xpf 3")) id = OPT_CANCEL;
        else if (!strcmp(nm, "# opw-bts.xpf 0 0") || !strcmp(nm, "# opw-bts.xpf 0 3")) {
            int off = nm[16] == '3';
            if (y >= 37 && y <= 185 && (y - 37) % 37 == 0) id = OPT_T0 + (y - 37) / 37 * 2 + off;
            else if (y >= 72 && y <= 252 && (y - 72) % 36 == 0) id = OPT_T1 + (y - 72) / 36 * 2 + off;
        }
        else if (!strcmp(nm, "# opw-bts.xpf 0 6")) id = y < 240 ? OPT_CHG : OPT_CHG + 1;
        else if (!strncmp(nm, "# opw-bts.xpf 2 ", 16)) id = OPT_3D + atoi(nm + 16) / 3;
        else if (!strncmp(nm, "# opw-bts.xpf 1 ", 16)) id = OPT_SCR + atoi(nm + 16) / 3;
        if (id >= 0 && id < OPT_N) { lg_rect(w, DX, s->lg_ot[id]); s->lg_oon[id] = (unsigned char)w[0x155]; }
    }
    char *t0 = find_child(iw, NULL, "@ opw-fd.xpf 0");
    s->lg_otab = t0 && !t0[0x155] ? 0 : 1;
    s->lg_ovol[0] = *(unsigned short *)(iw + 0x2f0); s->lg_ovol[1] = *(unsigned short *)(iw + 0x2f2);
    for (int j = 0; j < 12; j++) s->lg_of[j] = (unsigned char)iw[0x2f4 + j];
    s->lg_oscroll = *(int *)(iw + 0x300); s->lg_o3d = *(int *)(iw + 0x304);
    for (int j = 0; j < 2; j++) {
        s->lg_osl[j][0] = (short)(ix + 75 + DX); s->lg_osl[j][2] = (short)(ix + 215 + DX);
        s->lg_osl[j][1] = s->lg_osl[j][3] = (short)(iy + (j ? 194 : 120));
    }
    /* (11-01) its dialogs, over the same place: the colour picker (its square + brightness bar + sample: rel 2,16 -
       282,291 - shown through a hole), the macros (10 edits, DEFAULT / OK / CANCEL - drawn anew) */
    s->lg_osub = 0;
    char *d = g_opt_cdlg ? g_opt_cdlg : g_opt_mdlg;
    if (!d || !rd(d, 0x160)) return;
    s->lg_osub = g_opt_cdlg ? 1 : 2;
    int dx = *(int *)(d + 0x118), dy = *(int *)(d + 0x11c);
    s->lg_ohole[0] = (short)(dx + 2 + DX); s->lg_ohole[1] = (short)(dy + 16); s->lg_ohole[2] = (short)(dx + 282 + DX); s->lg_ohole[3] = (short)(dy + 291);
    char **dk; int dn = wkids(d, &dk), ne = 0;
    s->lg_ofoc = 0;
    char *f = *(char **)(g_app_last + 0xc10);
    for (int i = 0; i < dn; i++) {
        char *w = dk[i];
        if (!rd(w, 0x320)) continue;
        const char *nm = w + 4, *c = sgr_class(w);
        if (!strcmp(c, "CCtrlEditORG") && ne < 10) {
            lg_rect(w, DX, g_mac_ed[ne]);
            /* the text without the edit's control characters (an empty macro holds one), the caret counted the same */
            int L = 0, o = 0, cr = rd(w, 0x304) ? *(int *)(w + 0x300) : -1, ca = -1;
            for (; L < 39 && rd(w + 4 + L, 1) && w[4 + L]; L++) {
                if (L == cr) ca = o;
                unsigned char ch = (unsigned char)w[4 + L];
                if (ch >= 0x20 && ch != 0x7f) s->lg_omac[ne][o++] = (char)ch;
            }
            if (cr >= L || ca < 0) ca = o;
            s->lg_omac[ne][o] = 0;
            if (f == w) { s->lg_ofoc = ne + 1; s->lg_ocaret = ca; }
            ne++;
        }
        else if (!strcmp(nm, "@ opw-ok.xpf 0") || !strcmp(nm, "@ opw-ok.xpf 6")) lg_rect(w, DX, s->lg_ot[OPT_DOK]);
        else if (!strcmp(nm, "@ opw-ok.xpf 3") || !strcmp(nm, "@ opw-ok.xpf 12")) lg_rect(w, DX, s->lg_ot[OPT_DCANCEL]);
        else if (!strcmp(nm, "@ opw-ok.xpf 9")) lg_rect(w, DX, s->lg_ot[OPT_DDEFAULT]);
    }
    s->lg_blink = (int)(GetTickCount() / 530) & 1;
}
static int g_seen_setup;
static int g_skip_intro;
static void lg_msg_of(HudState *s, char *panel)    /* the advisor's message (wrong password, connecting ...) */
{
    char *mw = panel ? find_child(panel, "CCtrlMessageWnd", NULL) : NULL, *m = mw && rd(mw, 0x338) ? *(char **)(mw + 0x334) : NULL;
    if (!rd(m, 4) || !m[0]) return;
    char b[160]; int j = 0;
    for (; j < 159 && rd(m + j, 1) && m[j]; j++) b[j] = (char)(m[j] == '\n' || m[j] == '\r' ? ' ' : m[j]);
    b[j] = 0;
    MultiByteToWideChar(CP_ACP, 0, b, -1, s->lg_msg, 160);
}
static const char *str_at(char *it)                /* MSVC std::string (0x1c): text +4 inline below 16, else a pointer */
{
    if (!rd(it, 0x1c)) return "";
    char *t = *(unsigned *)(it + 0x18) < 16 ? it + 4 : *(char **)(it + 4);
    return rd(t, 1) ? t : "";
}
/* a form dialog (CONTINUE / CREATE ID / CHANGE PASSWORD): its edits in order, its buttons, the focus */
static void lg_form(HudState *s, char *app, char *fw, int DX, const unsigned char *mask)
{
    char **ck; int nc = wkids(fw, &ck), ne = 0; char *ed[4] = { 0 };
    s->lg_nb = 0;
    for (int i = 0; i < nc; i++) {
        char *w = ck[i];
        if (!rd(w, 0x320)) continue;
        const char *c = sgr_class(w);
        if (!strcmp(c, "CCtrlEditORG")) { if (ne < 4) { ed[ne] = w; lg_rect(w, DX, s->lg_ed[ne]); ne++; } }
        else if (!strcmp(c, "CBinkButton")) lg_rect(w, DX, s->lg_bt[0]);                       /* START */
        else if (!strcmp(w + 4, "@ OkBtn.xpf 0")) lg_rect(w, DX, s->lg_bt[0]);
        else if (!strcmp(w + 4, "@ ChPsBtn.xpf 0")) lg_rect(w, DX, s->lg_bt[1]);
        else if (!strcmp(w + 4, "@ CanclBtn.xpf 0")) lg_rect(w, DX, s->lg_bt[s->lg == LG_CONT ? 2 : 1]);
    }
    s->lg_nb = s->lg == LG_CONT || s->lg == LG_MAIN ? 3 : 2;
    s->lg_nf = ne;
    for (int i = 0; i < ne; i++) {
        s->lg_mask[i] = mask[i];
        int L = 0; while (L < 39 && rd(ed[i] + 4 + L, 1) && ed[i][4 + L]) L++;
        s->lg_len[i] = (unsigned char)L;
        if (!mask[i]) memcpy(s->lg_txt[i], ed[i] + 4, L);
    }
    if (s->lg == LG_CONT && ne >= 1 && !mask[0] && s->lg_len[0]) {   /* the account typed at login: the honor / report pages ask
                                                                     for it (several accounts online from one IP) */
        memcpy(g_acc, s->lg_txt[0], s->lg_len[0]); g_acc[s->lg_len[0]] = 0;
    }
    char *f = *(char **)(app + 0xc10);
    for (int i = 0; i < ne; i++) if (f == ed[i] && s->lg != LG_MAIN) s->lg_focus = i + 1;
    if (s->lg_focus) {
        s->lg_caret = *(int *)(f + 0x300);
        if (s->lg_caret < 0 || s->lg_caret > 39) s->lg_caret = 39;
        s->lg_blink = (int)(GetTickCount() / 530) & 1;
    }
}
/* pictures the game draws on the select commander page, copied out of the frame (RGB565): the 9 portrait buttons
   (146 x 36) and the big preview (223 x 142); the painter draws them in the new look */
#define HP_W 146
#define HP_H 36
#define HV_W 223
#define HV_H 142
#define HV_S 224                       /* row stride of the copy: GDI+ wants rows of 4-byte multiples */
static unsigned short g_himg[9][HP_W * HP_H], g_hview[HV_S * HV_H];
static void grab565(const short *r, unsigned short *dst, int w, int h, int stride)
{
    unsigned char *bits; int pitch, fw, fh;
    if (!sgr_primary_info(&bits, &pitch, &fw, &fh) || !bits) return;
    for (int y = 0; y < h; y++) {
        int sy = r[1] + y;
        if (sy < 0 || sy >= fh) continue;
        const unsigned short *sp = (const unsigned short *)(bits + (size_t)sy * pitch);
        for (int x = 0; x < w; x++) { int sx = r[0] + x; dst[y * stride + x] = sx >= 0 && sx < fw ? sp[sx] : 0; }
    }
}
static void read_hero(HudState *s, char *su, char *hw, char *panel, int DX)
{
    s->lg = LG_HERO;
    s->lg_hero = rd(su, 0x60b40) ? *(int *)(su + 0x60b38) : 0;
    char **k; int n = wkids(hw, &k);
    for (int i = 0; i < n; i++) {
        char *w = k[i];
        if (!rd(w, 0x160)) continue;
        if (!strncmp(w + 4, "@ CmdBtn.xpf ", 13)) {
            int f = atoi(w + 17) / 3;
            if (f >= 0 && f < 9) { lg_rect(w, DX, s->lg_hbtn[f]); grab565(s->lg_hbtn[f], g_himg[f], HP_W, HP_H, HP_W); }
        } else if (!strcmp(sgr_class(w), "CCtrlPortrait")) {
            char **pk; int pn = wkids(w, &pk); char *pv = NULL;   /* the portrait picture (223 x 142; named once loaded) */
            for (int j = 0; j < pn && !pv; j++)
                if (rd(pk[j], 0x160) && *(int *)(pk[j] + 0x130) == HV_W && *(int *)(pk[j] + 0x134) == HV_H) pv = pk[j];
            if (pv) { lg_rect(pv, DX, s->lg_hview); grab565(s->lg_hview, g_hview, HV_W, HV_H, HV_S); }
            static int logged; if (!logged++ && sgr_debug()) sgr_log("HERO preview %p rect %d,%d-%d,%d", pv, s->lg_hview[0], s->lg_hview[1], s->lg_hview[2], s->lg_hview[3]);
        } else if (!strcmp(sgr_class(w), "CCtrlPoint") && rd(w, 0x6570)) {
            for (int j = 0; j < 4; j++) s->lg_stat[j] = *(int *)(w + 0x6510 + 4 * j);
            s->lg_pts = *(int *)(w + 0x6560);
            char **pk; int pn = wkids(w, &pk), ns = 0;
            for (int j = 0; j < pn; j++) {
                char *c = pk[j];
                if (!rd(c, 0x160)) continue;
                const char *cl = sgr_class(c);
                if (!strcmp(cl, "CBinkButton")) lg_rect(c, DX, s->lg_hsel);
                else if (!strcmp(cl, "CCtrlSpin") && ns < 4) {
                    char *dn = find_child(c, NULL, "@ nsp-spi3.xpf 0"), *up = find_child(c, NULL, "@ nsp-spi3.xpf 3");
                    if (dn) lg_rect(dn, DX, s->lg_spin[ns][0]);
                    if (up) lg_rect(up, DX, s->lg_spin[ns][1]);
                    ns++;
                }
            }
        }
    }
    char *pb = panel ? find_child(panel, NULL, "@ PrevBtn.xpf 0") : NULL, *nb = panel ? find_child(panel, NULL, "@ NextBtn.xpf 0") : NULL;
    if (pb) lg_rect(pb, DX, s->lg_nav[0]);
    if (nb) lg_rect(nb, DX, s->lg_nav[1]);
    static DWORD t; static unsigned sum;               /* the pictures changed: repaint (at most 4 / s) */
    if (GetTickCount() - t > 250) { t = GetTickCount(); sum = fnv(g_himg, sizeof g_himg, fnv(g_hview, sizeof g_hview, 2166136261u)); }
    s->lg_imgsum = sum;
}
static void read_nation(HudState *s, char *app, char *fw, char *panel, int DX)
{
    s->lg = LG_NATION;
    s->lg_tab = rd(fw, 0x26bf0) ? *(int *)(fw + 0x26bec) : 0;
    char **k; int n = wkids(fw, &k);
    for (int i = 0; i < n; i++) {
        char *w = k[i];
        if (!rd(w, 0x160)) continue;
        const char *c = sgr_class(w);
        if (!strcmp(c, "CCtrlSolarSystemView")) {
            lg_rect(w, DX, s->lg_view);
            if (s->lg_view[3] > 372) s->lg_view[3] = 372;      /* the tab row and SELECT are the new look's */
        } else if (!strcmp(w + 4, "@ sGalaxy.xpf 0")) lg_rect(w, DX, s->lg_ntab[0]);
        else if (!strcmp(w + 4, "@ sPlanet.xpf 0")) lg_rect(w, DX, s->lg_ntab[1]);
        else if (!strcmp(w + 4, "@ sFriend.xpf 0")) lg_rect(w, DX, s->lg_ntab[2]);
        else if (!strcmp(c, "CBinkButton")) lg_rect(w, DX, s->lg_nsel);
        else if (!strcmp(c, "CNewSelectFriendNationWnd") && wvis(w)) {
            s->lg_fr = 1;
            char **fk; int fn = wkids(w, &fk);
            for (int j = 0; j < fn; j++) {
                char *e = fk[j];
                if (!rd(e, 0x320)) continue;
                if (!strcmp(sgr_class(e), "CCtrlEditORG")) {
                    lg_rect(e, DX, s->lg_fred);
                    int L = 0; while (L < 39 && e[4 + L]) L++;
                    memcpy(s->lg_txt[0], e + 4, L); s->lg_len[0] = (unsigned char)L;
                    if (*(char **)(app + 0xc10) == e) {
                        s->lg_focus = 1; s->lg_caret = *(int *)(e + 0x300);
                        if (s->lg_caret < 0 || s->lg_caret > 39) s->lg_caret = 39;
                        s->lg_blink = (int)(GetTickCount() / 530) & 1;
                    }
                } else if (!strcmp(e + 4, "@ FrDlgOk.xpf 0")) lg_rect(e, DX, s->lg_frbt[0]);
                else if (!strcmp(e + 4, "@ FrDlgCnl.xpf 0")) lg_rect(e, DX, s->lg_frbt[1]);
            }
        }
    }
    char *pb = panel ? find_child(panel, NULL, "@ PrevBtn.xpf 0") : NULL, *nb = panel ? find_child(panel, NULL, "@ NextBtn.xpf 0") : NULL;
    if (pb) lg_rect(pb, DX, s->lg_nav[0]);
    if (nb) lg_rect(nb, DX, s->lg_nav[1]);
}
static int read_login(HudState *s, char *app, int DX)
{
    char *tc = app + 0x28;
    if (!rd(tc, 0x160) || !wvis(tc)) return 0;
    char **tk; int tn = wkids(tc, &tk), other = 0;
    char *su = NULL, *bf = NULL;
    g_opt_cdlg = g_opt_mdlg = NULL;
    for (int i = 0; i < tn; i++) {
        char *w = tk[i];
        if (!rd(w, 0x160) || !wvis(w)) continue;
        const char *c = sgr_class(w);
        if (!strcmp(c, "CNewSetupWnd")) su = w;
        else if (!strcmp(c, "CBriefingWnd")) bf = w;
        else if (!strcmp(c, "CPannelQuestionDlg")) {   /* the advisor asks to click OK (bottom right of its panel) */
            char *qb = find_child(w, "CBinkButton", NULL);
            if (qb) { lg_rect(qb, DX, s->lg_q); s->lg_qon = 1; }
        }
        else if (!strcmp(c, "CLogoWnd")) { char *ml = find_child(w, "CMultiLoginSelectWnd", NULL); if (ml && wvis(ml)) other = 1; }
        else if (!strcmp(c, "CColorSelectDlg")) g_opt_cdlg = w;   /* (11-01) the options' dialogs */
        else if (!strcmp(c, "CMacroDlg")) g_opt_mdlg = w;
        else if (strcmp(c, "CBinkFullScreenWnd")) other = 1;
    }
    if (bf && rd(bf, 0x5290)) {                    /* the briefing room: the war record list */
        s->lg = LG_BRIEF;
        lg_msg_of(s, find_child(bf, "CNewPannelWnd", NULL));
        int n = *(int *)(bf + 0x5278), first = *(int *)(bf + 0x526c);
        char *vb = *(char **)(bf + 0x5284), *ve = *(char **)(bf + 0x5288);
        int nv = vb && ve > vb ? (int)((ve - vb) / 0x1c) : 0;
        if (n < 0 || n > nv) n = nv;
        if (first < 0 || first > n) first = 0;
        s->lg_cnt = n; s->lg_first = first; s->lg_sel = *(int *)(bf + 0x5270);
        for (int i = 0; i < 10 && first + i < n; i++) { lstrcpynA(s->lg_rec[i], str_at(vb + (first + i) * 0x1c), 80); s->lg_nrow = i + 1; }
        s->lg_row[0] = (short)(*(int *)(bf + 0x34ec) + DX); s->lg_row[1] = (short)*(int *)(bf + 0x34f0);
        s->lg_row[2] = 230; s->lg_row[3] = (short)*(int *)(bf + 0x34f8);
        char *sc = find_child(bf, "CCtrlScroll2", NULL);
        if (sc) lg_rect(sc, DX, s->lg_scr);
        char *pb = find_child(bf, NULL, "@ bfw-bts.xpf 0"), *cb = find_child(bf, NULL, "@ bfw-bts.xpf 3");
        if (pb) lg_rect(pb, DX, s->lg_bt[0]);
        if (cb) lg_rect(cb, DX, s->lg_bt[1]);
        s->lg_nb = 2;
        return 1;
    }
    if (!su) {                                     /* start-up (black, logo, intro): the new look's background */
        if (!g_seen_setup && !other) { s->lg = LG_BOOT; return 1; }
        return 0;
    }
    g_seen_setup = 1;
    char **k; int n = wkids(su, &k), nb = 0;
    char *cw = NULL, *iw = NULL, *pw = NULL, *bt[6], *panel = NULL, *hw = NULL, *nw = NULL;
    for (int i = 0; i < n; i++) {
        char *w = k[i];
        if (!rd(w, 0x160)) continue;
        const char *c = sgr_class(w);
        if (!strcmp(c, "CBinkButton")) { if (nb < 6) bt[nb++] = w; continue; }
        if (!strcmp(c, "CNewPannelWnd")) { lg_msg_of(s, w); panel = w; continue; }
        if (!strcmp(c, "CNewSelectHeroWnd")) { if (wvis(w)) hw = w; continue; }
        if (!strcmp(c, "CNewSelectFactionWnd")) { if (wvis(w)) nw = w; continue; }
        if (!strcmp(c, "CCtrlBink") || !strcmp(c, "CCtrlStatic")) continue;
        if (!strcmp(c, "CNewContinueWnd")) { cw = w; continue; }
        if (!strcmp(c, "CNewSelectIdWnd")) { iw = w; continue; }
        if (!strcmp(c, "CNewChangePasswordWnd")) { pw = w; continue; }
        if (!strcmp(c, "CNewSeverSelectWnd") && wvis(w) && rd(w, 0x5110)) {
            /* the server select: its fly-in skipped (Esc state), a single server is picked by the game itself
               (+0x4714 = 1) - meanwhile the new look's start screen; more servers: the game's page to choose */
            static DWORD t0; if (!t0) t0 = GetTickCount();
            if (*(int *)(w + 0x4710) == 0 && g_skip_intro > 0) *(int *)(w + 0x4710) = 1;
            if (*(int *)(w + 0x4714) == 1 || *(int *)(w + 0x4710) != 1 || GetTickCount() - t0 < 3000) { s->lg = LG_BOOT; return 1; }
            return 0;                              /* (the server list is in, the player picks) */
        }
        if (!strcmp(c, "CNewOptionWnd") && wvis(w)) {   /* (11-01) the options: the new look, unless a dialog of it is up */
            char *modal = *(char **)(app + 0xc18);
            if (rd(modal, 0x160) && modal[0x155] && modal != g_opt_cdlg && modal != g_opt_mdlg) return 0;
            read_option(s, w, DX);
            if (s->lg == LG_OPTION) { lg_msg_of(s, panel); return 1; }
            return 0;
        }
        if (wvis(w)) {                             /* another page (commander, nation, options ...): the game's screen */
            static char *lastw; if (w != lastw && sgr_debug()) sgr_log("LOGIN other page %s", c); lastw = w;
            return 0;
        }
    }
    if (nw) { read_nation(s, app, nw, panel, DX); return 1; }
    if (hw) { read_hero(s, su, hw, panel, DX); return 1; }
    if (nb != 6 || !cw) return 0;
    for (int i = 1; i < 6; i++)                    /* top to bottom: NEW COMMANDER .. EXIT */
        for (int j = i; j > 0 && *(int *)(bt[j] + 0x11c) < *(int *)(bt[j - 1] + 0x11c); j--) { char *t = bt[j]; bt[j] = bt[j - 1]; bt[j - 1] = t; }
    for (int i = 0; i < 6; i++) lg_rect(bt[i], DX, s->lg_btn[i]);
    static const unsigned char M_CONT[4] = { 0, 1 }, M_CREATE[4] = { 0, 1, 1, 0 }, M_CHPW[4] = { 0, 1, 1, 1 };
    if (iw && wvis(iw)) { s->lg = LG_CREATE; lg_form(s, app, iw, DX, M_CREATE); }
    else if (pw && wvis(pw)) { s->lg = LG_CHPW; lg_form(s, app, pw, DX, M_CHPW); }
    else { s->lg = wvis(cw) ? LG_CONT : LG_MAIN; lg_form(s, app, cw, DX, M_CONT); }
    if (s->lg_nf < 2) return 0;
    return 1;
}

/* (user 11-01 13:02 "the options in the game are still the old look"): the same CNewOptionWnd, opened from the
   field (child of TC Main or of the field window) - the login page's options card over the dimmed game */
static int read_game_option(HudState *s, char *app, int DX)
{
    char *tc = app + 0x28, *ow = NULL;
    if (!rd(tc, 0x160) || !wvis(tc)) return 0;
    char **tk; int tn = wkids(tc, &tk);
    g_opt_cdlg = g_opt_mdlg = NULL;
    for (int i = 0; i < tn; i++) {
        char *w = tk[i];
        if (!rd(w, 0x160) || !wvis(w)) continue;
        const char *c = sgr_class(w);
        if (!strcmp(c, "CNewOptionWnd")) ow = w;
        else if (!strcmp(c, "CColorSelectDlg")) g_opt_cdlg = w;
        else if (!strcmp(c, "CMacroDlg")) g_opt_mdlg = w;
    }
    char *f = G_FIELD;
    if (!ow && rd(f, 0x29c40)) {
        char *o = find_child(f + 4, "CNewOptionWnd", NULL);
        if (o && wvis(o)) ow = o;
    }
    if (!ow) return 0;
    char *modal = *(char **)(app + 0xc18);
    if (rd(modal, 0x160) && modal[0x155] && modal != ow && modal != g_opt_cdlg && modal != g_opt_mdlg) return 0;
    read_option(s, ow, DX);
    if (s->lg != LG_OPTION) { s->lg = 0; return 0; }
    s->lg_game = 1;
    {   /* (14:40) the game's own options window is never drawn in the game (the card is the HUD's): it, its inside
           window and their controls - no old window for the frames before the card is painted */
        char *lv[48]; int nl = 0; lv[nl++] = ow;
        for (int i = 0; i < nl && nl < 48; i++) { char **k; int n = wkids(lv[i], &k); for (int j = 0; j < n && nl < 48; j++) if (rd(k[j], 0x160)) lv[nl++] = k[j]; }
        for (int i = 0; i < nl; i++) { skin_hook(lv[i], HK_NONE); if (s->nhid < 64) s->hid[s->nhid++] = lv[i]; }
    }
    if (rd(f, 0x29c40)) {                       /* the field gets no mouse while the options are up: a scroll flag set
                                                   by the last move before (MapWnd +0x96a..+0x96d) would scroll on */
        char *map = *(char **)(f + 0x8564);
        if (rd(map, 0x970)) memset(map + 0x96a, 0, 4);
    }
    s->lg_odead[0] = (short)(*(int *)(ow + 0x118) + 6 + DX);       /* its left border, half way down */
    s->lg_odead[1] = (short)((*(int *)(ow + 0x11c) + *(int *)(ow + 0x124)) / 2);
    return 1;
}

static void read_state(char *app, int W, int DX)
{
    HudState *s = &g_st;
    memset(s, 0, sizeof *s);
    s->W = W; s->DX = DX;
    if (app && read_login(s, app, DX)) return;
    if (app && read_game_option(s, app, DX)) return;
    char *f = G_FIELD, *ms = G_MAIN;
    if (!app || !rd(f, 0x29c40) || !rd(ms, 0x2600)) return;
    char *tc = app + 0x28, *fw = f + 4;        /* *0x6ba7cc points 4 bytes before the window part (CWnd) */
    if (!wvis(tc) || !wvis(fw)) return;
    {   /* (2026-11-02, user 15:25 "登入时旧的画面会跑出来, 请帮我删除但是保留音效"): the game's loading screen (CLoadingWnd,
           the old city picture after login and before every map) - the new look's start screen instead; only the
           picture: the game loads and plays its sounds as before */
        char **lk; int ln = wkids(fw, &lk);
        for (int i = 0; i < ln; i++)
            if (rd(lk[i], 0x160) && wvis(lk[i]) && !strcmp(sgr_class(lk[i]), "CLoadingWnd")) { s->lg = LG_LOAD; return; }
    }
    if (f != g_field) { g_field = f; g_map = g_panel = g_chat = g_cbw = NULL; g_chat_hid = 0; }
    if (g_panel) {
        /* (user 10-29 23:13 "the old interface after logging in"): after a recording the field (same object) gets a new
           map / lower panel / chat - the ones remembered from the recording are gone: look them up again */
        char **pk; int pn = wkids(fw, &pk), have_p = 0, have_c = 0;
        for (int i = 0; i < pn; i++) { have_p |= pk[i] == g_panel; have_c |= pk[i] == g_chat; }
        if (!have_p || !have_c || *(char **)(f + 0x8564) != g_map) {
            sgr_log("HUD: the field's windows changed - looked up again");
            g_map = g_panel = g_chat = g_cbw = NULL; g_chat_hid = 0; g_chat_moved = 0;
        }
    }
    if (!g_panel) {
        g_map = *(char **)(f + 0x8564);
        g_panel = find_child(fw, "CStatusLowerWnd", NULL);
        g_chat = find_child(fw, "CCtrlChatting", NULL);
        g_cbw = g_panel ? *(char **)(g_panel + 0x15c) : NULL;
        if (g_cbw && strcmp(sgr_class(g_cbw), "CCommandButtonWnd")) g_cbw = NULL;
        static int logged; if (logged++ < 8) sgr_log("HUD: field %p map %p panel %p chat %p commands %p", f, g_map, g_panel, g_chat, g_cbw);
        if (g_panel && logged < 4) { const int *mm = (const int *)(g_panel + 0xa0cc); sgr_log("HUD: minimap rect %d,%d-%d,%d", mm[0], mm[1], mm[2], mm[3]); }
    }
    if (!rd(g_map, 0x102660) || !g_panel || !g_chat) return;
    /* loading screen: nothing */
    char **k; int n = wkids(tc, &k);
    for (int i = 0; i < n; i++)
        if (k[i] != fw) add_occ(s, k[i]);
    n = wkids(fw, &k);
    for (int i = 0; i < n; i++) {
        char *w = k[i];
        if (w == g_map || w == g_panel || w == g_chat || !rd(w, 0x160)) continue;
        const char *c = sgr_class(w);
        if (!strcmp(c, "CUnitWnd") || !strcmp(c, "CSmallUnitWnd")) continue;
        if (!strcmp(c, "CLoadingWnd") && wvis(w)) {
            /* (user 10-29 00:13 "HUD bits at the left of the loading screen"): the old status cards sit in the wide
               frame's side band (x < 0), outside the 800-wide loading picture - the HUD replaces them anyway */
            for (int j = 0; j < n; j++)
                if (rd(k[j], 0x160) && *(int *)(k[j] + 0x120) <= 0 &&
                    (!strcmp(sgr_class(k[j]), "CUnitWnd") || !strcmp(sgr_class(k[j]), "CSmallUnitWnd"))) k[j][0x155] = 0;
            return;
        }
        add_occ(s, w);
    }
    char *modal = *(char **)(app + 0xc18);
    if (modal) add_occ(s, modal);
    s->active = 1;
    log_occ(s);
    for (int i = 0; i < s->nocc; i++) {           /* a big window (strategic map board, who list ...): no HUD */
        RECT *o = &s->occ[i];
        if ((o->right - o->left) * (o->bottom - o->top) * 10 >= W * 600 * 4) s->covered = 1;
        const char *oc = sgr_class(g_occ_w[i]);          /* (user 17:11 "the chat must not show over the board") */
        if (!strcmp(oc, "CBBSDlg") || !strcmp(oc, "CMailDlg") || !strcmp(oc, "CHallOfFameDlg")) s->chat_dlg = 1;
    }
    {   char *rc = *(char **)0x6ba818;
        s->replay = rd(rc, 0x60) && rc[0x50];
    }
    s->mine = my_nation();
    s->chat_open = g_chat_open; s->chat_pin = g_chat_pin;
    {   char *cm = *(char **)0x6ba7d8; s->my_look = rd(cm, 0x454) ? (unsigned char)cm[0x450] : 0; }
    s->chat_mode = !rd(g_chat, 0x58c0 + 0x750) ? 0 : g_chat[0x5168 + 0x749] ? 1 : g_chat[0x58c0 + 0x749] ? 2 : 0;
    s->binfo = rd(f + 0x388, 0x10) ? *(int *)(f + 0x388 + 8) : 0;
    if (s->binfo < 0 || s->binfo > 999 || s->replay) s->binfo = 0;   /* a recording: no battle news */
    skin_windows(s, app, fw, DX);
    if (s->nfh) {                                    /* (14:40) controls under an open hole: not drawn by the HUD */
        int k = 0;
        for (int i = 0; i < s->nsk; i++) {
            HudSkin *e = &s->sk[i]; int under = 0;
            for (int h = 0; h < s->nfh; h++)
                if (e->x1 > s->fh[h][0] && e->x0 < s->fh[h][2] && e->y1 > s->fh[h][1] && e->y0 < s->fh[h][3]) under = 1;
            if (under) continue;
            if (k != i) { s->sk[k] = s->sk[i]; s->skp[k] = s->skp[i]; }
            k++;
        }
        s->nsk = k;
    }
    {   /* (11-01 14:40) what covers the HUD: the part of each window inside the frame; a held window (opening, its
           data not here) or a sliding result window does not cover it (the old HUD stays until the page is there) */
        s->covered = 0;
        for (int i = 0; i < s->nocc; i++) {
            char *ow = g_occ_w[i]; int held = 0;
            for (int j = 0; j < s->nhold; j++) if (s->hold[j] == ow) held = 1;
            if (held || art_moving(ow)) continue;
            RECT o = s->occ[i];
            if (o.left < 0) o.left = 0; if (o.top < 0) o.top = 0; if (o.right > W) o.right = W; if (o.bottom > 600) o.bottom = 600;
            if (o.right > o.left && o.bottom > o.top && (o.right - o.left) * (o.bottom - o.top) * 10 >= W * 600 * 4) s->covered = 1;
        }
    }
    {   /* (11-01 14:30) a commander info window (own F4 or another's, a modal) stands above the other skinned windows
           (the who list under it): it is painted last, and their controls under it are not painted (kept hidden) */
        int m = -1;
        for (int i = 0; i < s->nskw; i++)
            if (s->skw[i].def < sizeof SKIN_WINS / sizeof *SKIN_WINS && !strncmp(SKIN_WINS[s->skw[i].def].cls, "CUserInfoWnd", 12)) m = i;
        if (m >= 0 && s->nskw > 1) {
            HudSkinWnd top = s->skw[m];
            memmove(&s->skw[m], &s->skw[m + 1], (size_t)(s->nskw - 1 - m) * sizeof top);
            s->skw[s->nskw - 1] = top;
            int k = 0;
            for (int i = 0; i < s->nsk; i++) {
                HudSkin *e = &s->sk[i];
                if (e->x1 > top.x0 && e->x0 < top.x1 && e->y1 > top.y0 && e->y0 < top.y1) {   /* any part under it */
                    if (s->skp[i] && s->nhid < 64) s->hid[s->nhid++] = s->skp[i];
                    continue;
                }
                if (k != i) { s->sk[k] = s->sk[i]; s->skp[k] = s->skp[i]; }
                k++;
            }
            s->nsk = k;
        }
    }
    unsigned now = *(unsigned *)(ms + 0x25a0);
    s->battle = f[0x29bdc] != 0;
    if (s->battle) {
        unsigned st = *(unsigned *)(f + 0x29be8), en = *(unsigned *)(f + 0x29bec);
        s->left = (now && now < en) ? (int)((en - now) / 100) : 0;
        s->total = en > st ? (int)((en - st) / 100) : 0;
    }
    /* squad cards */
    char *cards = *(char **)(f + 0x29b34);
    if (rd(cards, CARD_SIZE * 12))
        for (int i = 0; i < 12; i++) {
            char *c = cards + i * CARD_SIZE;
            unsigned id = c[0x16c] ? *(unsigned *)(c + 0x168) : *(unsigned *)(c + 0x164);
            char *u = unit_by_id(id);
            if (!u) continue;
            HudUnit *h = &s->card[s->ncard++];
            read_unit(u, h);
            h->slot = i; h->sel = unit_selected(u);
        }
    /* selection + its commands */
    s->nsel = *(int *)(f + 0x29bc8);
    if (s->nsel > 0 && s->nsel <= 34) read_unit(*(char **)(f + 0x29b40), &s->sel);
    else s->nsel = 0;
    for (int i = 0; i < 8; i++) s->cmd[i] = (s->nsel && rd(g_cbw, 0x260)) ? *(int *)(g_cbw + 0x21c + 4 * i) : -1;
    s->cmd_on = rd(g_cbw, 0x260) ? *(int *)(g_cbw + 0x25c) : -1;   /* the command waiting for its target */
    /* (user 10-31 12:49 "a continuous skill must stay lit after it is pressed"): a toggle command (type 1 in the
       command table 0xc310f8 + id x 0x60, 00428a70) keeps its state per slot at +0x23c + 4 x slot: 2 on, 1 some of
       the selected units on (0x429474), 0 off - set from the units' state when the selection is rebuilt (00428db0) */
    for (int i = 0; i < 8; i++) {
        int id = s->cmd[i];
        s->cmd_tg[i] = -1;
        if (id >= 0 && id < 74 && rd((char *)(0xc310f8 + id * 0x60), 4) && *(int *)(0xc310f8 + id * 0x60) == 1)
            s->cmd_tg[i] = (signed char)*(int *)(g_cbw + 0x23c + 4 * i);
    }
    /* POCs */
    char *ob = *(char **)(g_map + 0x10255c), *oe = *(char **)(g_map + 0x102560);
    for (char *r = ob; ob && r + 0xc74 <= oe && s->npoc < 8 && rd(r, 0xc74); r += 0xc74) {
        int *q = (int *)r;
        if (q[0] != 0 || q[0xe] <= 0) continue;
        HudPoc *p = &s->poc[s->npoc++];
        p->owner = tvi(r, 0x448, 0x84a); p->rel = relation(p->owner, s->mine);
        p->str = tvi(r, 0x44, 0x446); p->max = q[0xe]; p->tx = q[2]; p->ty = q[3];
    }
    /* buildings: the other map objects (bases etc., 2 x 2 tiles; the old minimap blinked them) */
    s->nbld = 0;
    for (char *r = ob; ob && r + 0xc74 <= oe && s->nbld < 32 && rd(r, 0xc74); r += 0xc74) {
        int *q = (int *)r;
        if (q[0] == 0) continue;
        HudBox *b = &s->bld[s->nbld++];
        b->tx = (short)q[2]; b->ty = (short)q[3]; b->tw = (short)(q[4] > 0 ? q[4] : 2); b->th = (short)(q[5] > 0 ? q[5] : 2);
        b->type = (unsigned char)q[0]; b->rel = REL_NEUTRAL;
    }
    /* star gates: the area list *0xc34618 +0x48 (0x2c each): [0] type (1 = gate), [1] map id (= map +0x3f4), [2..5]
       tile x y w h, [7] the province it leads to; coloured by that province's owner (old minimap 005b6000) */
    s->ngate = 0;
    char *al = *(char **)0xc34618;
    if (rd(al, 0x50)) {
        int *b0 = *(int **)(al + 0x48), *e0 = *(int **)(al + 0x4c), mapid = *(int *)(g_map + 0x3f4);
        char *pm = *(char **)0xc30bc4;
        for (int *r = b0; b0 && r + 11 <= e0 && s->ngate < 16 && rd(r, 0x2c); r += 11) {
            if (r[1] != mapid) continue;
            if (r[0] != 1 && (r[7] == 0 || r[7] == mapid)) {   /* capital buildings (types 2..8, 12..14): no exit */
                if (s->nbld < 32) {
                    HudBox *b = &s->bld[s->nbld++];
                    b->tx = (short)r[2]; b->ty = (short)r[3]; b->tw = (short)r[4]; b->th = (short)r[5];
                    b->type = (unsigned char)r[0]; b->rel = REL_NEUTRAL;
                }
                continue;
            }
            HudBox *g = &s->gate[s->ngate++];
            g->tx = (short)r[2]; g->ty = (short)r[3]; g->tw = (short)r[4]; g->th = (short)r[5]; g->type = 1;
            g->rel = REL_NEUTRAL;
            if (rd(pm, 0x20)) {
                char *pv = ((char *(__fastcall *)(char *, int, int))0x565ce0)(pm, 0, r[7]);
                if (rd(pv, 0x34) && !pv[0x30]) g->rel = (unsigned char)relation(*(int *)(pv + 4), s->mine);
            }
        }
    }
    /* units: counts + radar dots (enemies only where the fog is clear) */
    s->mapw = *(unsigned short *)(g_map + 0x1025f6) * 8; s->maph = *(unsigned short *)(g_map + 0x1025f8) * 8;
    s->camx = *(int *)(g_map + 0x534) * 32 + *(int *)(g_map + 0x53c);
    s->camy = *(int *)(g_map + 0x538) * 32 + *(int *)(g_map + 0x540);
    s->camw = W; s->camh = sgr_map_h();
    char *um = G_UNITMAN;
    int fog = sgr_fog_ok(g_map);
    if (rd(um, 0x60)) {
        int nu = *(int *)(um + 0x50); char **a = *(char ***)(um + 0x58);
        if (nu > 0 && nu < 4000 && rd(a, nu * 4))
            for (int i = 0; i < nu; i++) {
                char *u = a[i];
                if (!rd(u, 0xf200)) continue;
                if (tvi(u, 0xa868, 0xac6a) == ST_DEAD || tvi(u, 0xa464, 0xa866) <= 0) continue;
                int rel = relation(*(int *)(u + 0x354), s->mine);
                int x = *(int *)(u + 0x944c), y = *(int *)(u + 0x9450);
                if (rel == REL_MINE || rel == REL_ALLY) s->n_mine++;
                else if (!fog || !sgr_fog_visible(g_map, x, y)) continue;      /* hidden by the fog: not counted, not shown */
                else s->n_enemy++;
                if (s->ndot < 512) { HudDot *d = &s->dot[s->ndot++]; d->x = (short)x; d->y = (short)y; d->rel = (unsigned char)rel; }
            }
    }
}
