"""test106 (user 2026-10-29 21:10 "方案A"): the login screen's new look (SGRender.dll HUD, design A: side menu + login
card + advisor bar).  Source / package checks:
A. the setup screen is read (CNewSetupWnd: 6 main menu CBinkButtons, CNewContinueWnd edits / START / CHANGE PASSWORD /
   CANCEL, edit text +4, caret +0x300, focus app +0xc10, the advisor message CCtrlMessageWnd +0x334);
B. any other setup page (new commander, options, credits ...) keeps the game's own screen;
C. the mouse goes to the game's control under the new look's item (return 3 + sghud_mapped), nowhere elsewhere;
   a field / CHANGE PASSWORD clicked on the main menu opens CONTINUE and the click is repeated;
D. the art ships through OTA (SGHud-login.jpg, SGHud-advisor.jpg are JPEGs).
(user 10-29 21:34 "新指挥官的介面，简报室，去掉 nexon 跟动画直接进入主画面")
E. intro: BinkOpen (import) returns NULL for the 3 calls of 0053cd10 (return 0041d239, caller 0053cdc9/dd/f1), the logo
   (CLogoWnd +0x3f8) and the server select's fly-in (CNewSeverSelectWnd +0x4710) put where Esc puts them;
F. CREATE ID / CHANGE PASSWORD forms, the briefing room (records: vector +0x5280, count +0x5278, first +0x526c,
   chosen +0x5270, rows +0x34ec/+0x34f0/+0x34f8), select commander (hero setup +0x60b38, stats CCtrlPoint +0x6510,
   points +0x6560, pictures copied out of the frame), select nation (tab +0x26bec, the live viewer shown through the
   overlay, friend ID box), the advisor's OK (CPannelQuestionDlg).
(user 10-29 22:30, watching a recording)
G. the cards start below the recording's controls; the map draw's debug lines off (the recorder's playing flag 0 for
   the map draw only); no battle news (the message box cancelled, polls / alerts hidden, no battle-info badge); a new
   recording is named <planet>_<province>_SS<yyyymmdd><NN>.rcd (CreateFileA import) and listed by planet."""
import os, re, json
def chk(n, ok, i=''): print(('PASS ' if ok else 'FAIL ') + n, i, flush=True)
REPO = os.path.expanduser('~/mnt/SGgalaxy')
SRC = os.environ.get('SG_SRC', os.path.join(REPO, 'client/sgrender'))
h = open(os.path.join(SRC, 'sghud.c'), encoding='utf-8', errors='replace').read()
w = open(os.path.join(SRC, 'sgwindow.c'), encoding='utf-8', errors='replace').read()
chk('A. setup screen read', all(k in h for k in ('"CNewSetupWnd"', '"CNewContinueWnd"', '"@ ChPsBtn.xpf 0"', '"@ CanclBtn.xpf 0"',
    '*(int *)(f + 0x300)', '*(char **)(app + 0xc10)', '*(char **)(mw + 0x334)')))
chk('A. login read before the field HUD', 'if (app && read_login(s, app, DX)) return;' in h)
chk('B. another visible page: the game screen', '/* another page (commander, nation, options ...): the game' in h)
chk('C. mouse mapped (return 3), dead point outside the 800 screen', 'return 3;' in h and 'g_mgx = 2; g_mgy = 2;' in h
    and 'if (hr == 3) { sghud_mapped(&gx, &gy);' in w)
chk('C. pending click after CONTINUE opens', 'login_pending();' in h and 'PostMessageA(g_disp.hwnd, WM_LBUTTONDOWN' in h)
chk('C. login: system cursor over the whole screen', 'g_st.lg || (g_st.active && hit_at(x, y) != NULL)' in h)
ota = json.load(open(os.path.join(REPO, 'deploy/ota_files.json'), encoding='utf-8'))['common']
ok = True
for k in ('SGHud-login.jpg', 'SGHud-advisor.jpg'):
    p = os.path.join(REPO, ota.get(k, 'missing'))
    ok &= os.path.isfile(p) and open(p, 'rb').read(3) == b'\xff\xd8\xff'
chk('D. art in OTA, JPEG', ok)
w2 = w
chk('E. intro movies not opened (BinkOpen hook, caller check)', '"_BinkOpen@8"' in w2 and 'sp[0] == 0x41d239' in w2
    and all(a in w2 for a in ('0x53cdc9', '0x53cddd', '0x53cdf1')))
chk('E. logo / server select fly-in skipped, [hud] skip_intro', '*(int *)(w + 0x3f8) = 5' in h and '*(int *)(w + 0x4710) = 1' in h
    and '"skip_intro"' in h and '"skip_intro"' in w2)
chk('F. create ID / change password forms', '"CNewSelectIdWnd"' in h and '"CNewChangePasswordWnd"' in h and '"@ OkBtn.xpf 0"' in h)
chk('F. briefing room records', all(k in h for k in ('(bf + 0x5278)', '(bf + 0x526c)', '(bf + 0x5270)', '(bf + 0x5284)', '(bf + 0x34f8)')))
chk('F. select commander', all(k in h for k in ('(su + 0x60b38)', '(w + 0x6510 + 4 * j)', '(w + 0x6560)', '0x00021006', 'HV_S 224')))
chk('F. select nation: live viewer through the overlay', '(fw + 0x26bec)' in h and 'g_lg_hole' in h and 'return 0;                                   /* the live viewer' in h)
chk('F. the advisor OK', '"CPannelQuestionDlg"' in h and 'H_LQ' in h)
chk('G. replay: cards below the controls, debug lines off', 'y0 = s->replay ? fy_ref(84) : 24' in h and 'rc[0x50] = 0' in h and '"replay_debug"' in h)
chk('G. replay: no battle news', '((cmd_fn)(*(void ***)modal)[15])(modal, 2, 0, 2)' in h and '"CPollWnd", "CAlertWnd"' in h and 's->replay) s->binfo = 0' in h)
chk('G. recording named after the planet', 'str_at(pm + 0x78)' in h and 'str_at(pv + 0xc)' in h and '"CreateFileA", (void *)hook_CreateFileA' in w2
    and 'sghud_rec_prefix(pre, sizeof pre)' in w2)
chk('H. after a recording the field windows are looked up again', "the field's windows changed - looked up again" in h)
