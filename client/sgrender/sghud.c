/* sghud.c - the new battlefield HUD (phase 3, design canvas "SGalaxy 战场 HUD 设计").
 *
 * Drawn with GDI+ (anti-aliased shapes, TrueType text) into the native-resolution overlay of SGDraw (sgwindow.c),
 * over the scaled game frame.  The game itself is not changed: the HUD READS the game's state every frame and
 * FORWARDS clicks to the game's own windows (their event handler, vtable +0x14), so every action takes the
 * original code path and sends the original packets.
 *
 * Layout (reference 1080 px high, anchored to the edges of the frame):
 *   left        squad cards (the 12 status cards CUnitWnd, which are hidden)
 *   top centre  battle banner: time left, the POCs (owner colour + capture ring), unit counts
 *   top right   compass radar (replaces the minimap; enemies only where the fog of war is clear)
 *   bottom band (frame rows 462..600, where the old panel CStatusLowerWnd was - hidden now):
 *               chat (the game's own chat, moved to the left; phase 4 replaces it), selected unit with its
 *               commands, and the command wheel (strategic map, quick menu, who list, mail, board, options, exit)
 * Windows that pop up over the field (dialogs, the sliding quick menu / strategic map) hide the HUD parts they cover.
 *
 * Game structures used (SG.exe 1.8.5, reverse engineered 2026-10-28; see claude/BATTLE_HUD.md):
 *   CMainSystem *0x6ba7c8: +0x25a0 clock (1/100 s)
 *   CFieldWnd   *0x6ba7cc: +0x29bdc in battle, +0x29be8 / +0x29bec battle start / end (clock), +0x8564 map window,
 *                          +0x29b34 the 12 status cards (0x174 each), +0x29b3c selection (CUnitArray: units at +4,
 *                          count +0x8c)
 *   CUnitMan    *0x6ba7d4: +0x50 count, +0x58 units sorted by id (unit +4)
 *   unit: +0x78 name, +0x108 energy max, +0x110 HP max, +0x354 nation, +0x944c x / y (map pixels),
 *         timed values (ring of pointers, value at +4): HP 0xa464/0xa866, energy 0x9454/0x9856, state 0xa868/0xac6a
 *         (0x3d = destroyed)
 *   status card CUnitWnd: +0x15c selected, +0x160 slot, +0x164 unit id (+0x168 / +0x16c alternative); click 0x201
 *   map window: +0x534 / +0x538 scroll (32 px tiles) + 0x53c / 0x540 pixels, +0x1025f6 / f8 map size (8 px cells),
 *               objects +0x10255c..+0x102560 (0xc74 each): [0] type (0 = POC), [2] / [3] tile, [0xe] max strength,
 *               strength 0x44/0x446, owner 0x448/0x84a
 *   command buttons (CCommandButtonWnd = old panel +0x15c): +0x21c[8] command ids (-1 = none), press = 0x428a70(slot)
 *   old panel CStatusLowerWnd: minimap rect +0xa0cc; its event handler moves the camera / gives the order
 *   nation: user object *0x6ba7d8 (bits 0x3dc..0x3f8), alliance groups *0x6ba80c +0x18 (count +0x1c)
 */
#include <windows.h>
#include <stdio.h>
#include <string.h>
#include <math.h>
#include <wchar.h>
#include <stddef.h>
#include <stdlib.h>
#include "sgrender.h"
#include "sghud_gdip.h"
#include "sghud_rec.h"
#include "sghud_units.h"

/* ---- game interface ------------------------------------------------------------------------------------------ */
#define G_MAIN    (*(char **)0x6ba7c8)
#define G_FIELD   (*(char **)0x6ba7cc)
#define G_UNITMAN (*(char **)0x6ba7d4)
#define G_USER    (*(char **)0x6ba7d8)
#define G_NATION  (*(char **)0x6ba80c)
#define CARD_SIZE 0x174
#define ST_DEAD   0x3d

typedef int (__attribute__((thiscall)) *ev_fn)(void *, unsigned, int, int, int);
typedef void (__attribute__((thiscall)) *slot_fn)(void *, int);
typedef void (__attribute__((thiscall)) *move_fn)(void *, int, int, int, int);
typedef void (__attribute__((thiscall)) *sel4_fn)(void *, void *, int, int, int);
typedef int (__attribute__((thiscall)) *sel1_fn)(void *, void *);
typedef void (__attribute__((thiscall)) *noarg_fn)(void *);

static int rd(const void *p, int n) { return p && !IsBadReadPtr(p, n); }
static int tvi(char *o, int base, int idx)
{
    char *p = *(char **)(o + base + 4 * *(unsigned short *)(o + idx));
    return rd(p, 8) ? *(int *)(p + 4) : 0;
}
static int wvis(char *w) { return w && w[0x155]; }
static int wkids(char *w, char ***kids)
{
    int n = *(int *)(w + 0x148); *kids = *(char ***)(w + 0x150);
    return (n > 0 && n < 600 && rd(*kids, n * 4)) ? n : 0;
}
/* the old panel's buttons post (2, 0, id) to its OnCommand (vtable +0x3c) through the app queue (00545130 ->
 * 00548b20), which delivers only to visible windows - the HUD hides the panel and calls OnCommand itself */
typedef int (__attribute__((thiscall)) *cmd_fn)(void *, int, int, int);

static char *unit_by_id(unsigned id)
{
    char *m = G_UNITMAN;
    if (!id || !rd(m, 0x60)) return NULL;
    int lo = 0, hi = *(int *)(m + 0x50) - 1;
    char **a = *(char ***)(m + 0x58);
    if (hi < 0 || hi > 4000 || !rd(a, (hi + 1) * 4)) return NULL;
    while (lo <= hi) {
        int mid = (lo + hi) >> 1;
        unsigned v = *(unsigned *)(a[mid] + 4);
        if (v == id) return a[mid];
        if (id < v) hi = mid - 1; else lo = mid + 1;
    }
    return NULL;
}

static int unit_selected(char *u)
{
    char *f = G_FIELD;
    int n = *(int *)(f + 0x29bc8);
    char **a = (char **)(f + 0x29b40);
    for (int i = 0; i < n && i < 34; i++) if (a[i] == u) return 1;
    return 0;
}

static int my_nation(void)
{
    char *u = G_USER;
    if (!rd(u, 0x400)) return -1;
    return (*(unsigned *)(u + 0x3f8) & 0xf000) | (*(unsigned *)(u + 0x3ec) & 0xf00) | (*(unsigned *)(u + 0x3dc) & 0xf0) |
           (*(unsigned *)(u + 0x3f0) & 3) | (*(unsigned *)(u + 0x3e0) & 0xc);
}

enum { REL_NEUTRAL, REL_MINE, REL_ALLY, REL_ENEMY };
static int relation(int nat, int mine)
{
    if (nat == mine) return REL_MINE;
    char *ni = G_NATION;
    if (nat <= 0 || !rd(ni, 0x20)) return REL_NEUTRAL;
    int n = *(int *)(ni + 0x1c); int *g = *(int **)(ni + 0x18);
    if (nat > n || mine < 0 || mine > n || !rd(g, (n + 1) * 4)) return REL_ENEMY;
    return g[nat] == g[mine] ? REL_ALLY : REL_ENEMY;
}

/* ---- language ----------------------------------------------------------------------------------------------- */
static int g_lang;                 /* 0 English, 1 zh-CN, 2 zh-TW (the client's code page) */
#define T3(en, cn, tw) (g_lang == 1 ? L##cn : g_lang == 2 ? L##tw : L##en)

static const WCHAR *branch_name(int b)
{
    switch (b) {
    case 0: return T3("Infantry", "步兵", "步兵");
    case 1: return T3("Mobile", "机动", "機動");
    case 2: return T3("Aviation", "航空", "航空");
    case 3: return T3("Organic", "生物", "生物");
    }
    return L"";
}

/* command ids: the exe's table at 0x69b8bc (0x48 per command: hotkey, ..., the name 0x3c bytes before) */
static const char *CMD_EN[74] = {
    "Move", "Stop", "Attack", "Attack ground", "Install", "Uninstall", "Bombard", "Stop bombard", "Identify", "Radar",
    "Load", "Unload", "Heal", "Repair", "Teleport", "Mine", "Jammer", "Mine detector", "Refuel", "Cloak",
    "EMP mine", "EMP attack", "Grenade", "Mind warp", "Evasion", "Neutron shield", "Afterburner", "EMP grenade",
    "Disguise", "Self-destruct", "Anti-grav", "Short circuit", "IRBM", "Camouflage", "Alt charge", "Flak",
    "Stop flak", "Booster", "Link gate", "Carpet bomb", "Defense field", "Flare", "Shield", "Drop shield",
    "Explosives", "Detonate", "Tachyon sweep", "Snipe", "Stop snipe", "Chemical mine", "Earthquake", "IRBM defense",
    "Stop IRBM def.", "Fusion storm", "Warp", "Unit mode", "Stop unit mode", "Energy mode", "Stop energy mode",
    "Rally point", "Heal mode", "Stop heal mode", "Bunker", "Dispose bunker", "My list", "Infantry list",
    "Mobile list", "Air list", "Aux list", "Virus attack", "Virus kill", "Ping map", "Overload", "Frenzy" };
static const WCHAR *CMD_CN[74] = {
    L"移动", L"停止", L"攻击", L"攻击地面", L"架设", L"解除架设", L"轰击", L"解除轰击", L"识别", L"雷达",
    L"装载", L"卸载", L"治疗", L"修理", L"传送", L"布雷", L"雷达干扰", L"探雷", L"补给", L"隐形",
    L"EMP地雷", L"EMP攻击", L"手雷", L"心灵扭曲", L"感应规避", L"中子护盾", L"后燃器", L"EMP手雷",
    L"伪装", L"自爆", L"反重力", L"短路", L"导弹", L"迷彩", L"高爆炸药", L"防空",
    L"解除防空", L"推进器", L"连接星门", L"地毯轰炸", L"防御力场", L"照明弹", L"护盾", L"解除护盾",
    L"安放炸药", L"引爆", L"超光速扫描", L"狙击", L"解除狙击", L"化学地雷", L"地震", L"导弹防御",
    L"解除导弹防御", L"聚变风暴", L"曲速", L"生产单位", L"停止生产单位", L"生产能量", L"停止生产能量",
    L"集结点", L"治疗模式", L"解除治疗模式", L"碉堡", L"拆除碉堡", L"我的列表", L"步兵列表",
    L"机动列表", L"航空列表", L"辅助列表", L"病毒攻击", L"病毒清除", L"标记地图", L"超载", L"狂暴" };
static const WCHAR *CMD_TW[74] = {
    L"移動", L"停止", L"攻擊", L"攻擊地面", L"架設", L"解除架設", L"轟擊", L"解除轟擊", L"識別", L"雷達",
    L"裝載", L"卸載", L"治療", L"修理", L"傳送", L"佈雷", L"雷達干擾", L"探雷", L"補給", L"隱形",
    L"EMP地雷", L"EMP攻擊", L"手雷", L"心靈扭曲", L"感應規避", L"中子護盾", L"後燃器", L"EMP手雷",
    L"偽裝", L"自爆", L"反重力", L"短路", L"導彈", L"迷彩", L"高爆炸藥", L"防空",
    L"解除防空", L"推進器", L"連接星門", L"地毯轟炸", L"防禦力場", L"照明彈", L"護盾", L"解除護盾",
    L"安放炸藥", L"引爆", L"超光速掃描", L"狙擊", L"解除狙擊", L"化學地雷", L"地震", L"導彈防禦",
    L"解除導彈防禦", L"聚變風暴", L"曲速", L"生產單位", L"停止生產單位", L"生產能量", L"停止生產能量",
    L"集結點", L"治療模式", L"解除治療模式", L"碉堡", L"拆除碉堡", L"我的列表", L"步兵列表",
    L"機動列表", L"航空列表", L"輔助列表", L"病毒攻擊", L"病毒清除", L"標記地圖", L"超載", L"狂暴" };

static char cmd_hotkey(int id)
{
    if (id < 0 || id >= 74) return 0;
    unsigned k = *(unsigned *)(0x69b8bc + 0x48 * id);
    return (k > 32 && k < 127) ? (char)k : 0;
}

/* ---- icons (SVG path data, 24 x 24) ------------------------------------------------------------------------- */
enum { IC_INF, IC_MOB, IC_AVI, IC_ORG, IC_MOVE, IC_STOP, IC_ATTACK, IC_GROUND, IC_INSTALL, IC_BOMB, IC_EYE, IC_RADAR,
       IC_LOAD, IC_UNLOAD, IC_HEAL, IC_REPAIR, IC_TELEPORT, IC_MINE, IC_SHIELD, IC_CLOAK, IC_DASH, IC_DOT,
       IC_MAP, IC_QUICK, IC_WHO, IC_MAIL, IC_BOARD, IC_GEAR, IC_EXIT, IC_HUB, IC_INFO, IC_KEY, IC_TROPHY, IC_COUNT };
static const char *ICONS[IC_COUNT] = {
    "M7 9a5 5 0 0 1 10 0zM5.5 9h13M9 9v1.5a3 3 0 0 0 6 0V9M5 21c0-4 3-6.5 7-6.5s7 2.5 7 6.5",
    "M3 14h18v3a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2zM6 14v-3h9l2 3M13 11V8h8",
    "M12 2l1.6 7 8.4 4v2l-8.4-2-.8 5 3 2v1.5l-3.8-1-3.8 1V20l3-2-.8-5L2 15v-2l8.4-4z",
    "M3 12c2-5 5-7 9-7s7 2 9 7c-2 5-5 7-9 7s-7-2-9-7zM12 8.5c-1 2-1 5 0 7c1-2 1-5 0-7z",
    "M4 12h13M13 7l5 5-5 5",
    "M7 7h10v10H7z",
    "M12 2v5M12 17v5M2 12h5M17 12h5M12 9a3 3 0 1 0 0 6 3 3 0 0 0 0-6z",
    "M12 4v5M12 15v4M5 12h4M15 12h4M3 21h18",
    "M12 3v12M6 21l6-6 6 6M8 8h8",
    "M12 2l2 6 6-2-4 5 5 4-6 1 1 6-4-4-4 4 1-6-6-1 5-4-4-5 6 2z",
    "M2 12c3-5 6-7 10-7s7 2 10 7c-3 5-6 7-10 7s-7-2-10-7zM12 9a3 3 0 1 0 0 6 3 3 0 0 0 0-6z",
    "M12 12l6-6M12 3a9 9 0 1 0 9 9M12 7a5 5 0 1 0 5 5",
    "M3 12h10M9 8l4 4-4 4M15 4h6v16h-6",
    "M21 12H11M15 8l-4 4 4 4M9 4H3v16h6",
    "M9 3h6v6h6v6h-6v6H9v-6H3V9h6z",
    "M14 6a4 4 0 0 0-5 5l-6 6 3 3 6-6a4 4 0 0 0 5-5l-3 3-3-3z",
    "M12 3a9 9 0 1 1-9 9M12 7a5 5 0 1 1-5 5M12 11v2",
    "M12 7a5 5 0 1 0 0 10 5 5 0 0 0 0-10zM12 2v3M12 19v3M2 12h3M19 12h3",
    "M12 3l8 3v6c0 5-4 8-8 9-4-1-8-4-8-9V6z",
    "M3 12c3-5 15-5 18 0M6 15l-2 3M18 15l2 3M12 16v3",
    "M4 12h10M10 6l6 6-6 6M18 6v12",
    "M12 8a4 4 0 1 0 0 8 4 4 0 0 0 0-8z",
    "M3 6l6-2 6 2 6-2v14l-6 2-6-2-6 2zM9 4v14M15 6v14",
    "M13 2L5 14h6l-1 8 8-12h-6z",
    "M9 7a3 3 0 1 0 0 6 3 3 0 0 0 0-6zM3 20c0-3 3-5 6-5s6 2 6 5M16 8a2.5 2.5 0 1 0 0 5M17 15c2.5 0 4 2 4 4",
    "M3 6h18v12H3zM3 6l9 7 9-7",
    "M6 3h12v18H6zM9 7h6M9 11h6M9 15h4",
    "M12 8a4 4 0 1 0 0 8 4 4 0 0 0 0-8zM12 2v3M12 19v3M2 12h3M19 12h3M5 5l2 2M17 17l2 2M5 19l2-2M17 7l2-2",
    "M14 4H5v16h9M10 12h11M17 8l4 4-4 4",
    "M12 4a8 8 0 1 0 0 16 8 8 0 0 0 0-16zM12 2v4M12 18v4M2 12h4M18 12h4M12 8l2 4-2 4-2-4z",
    "M12 3a9 9 0 1 0 0 18 9 9 0 0 0 0-18zM12 7.5v1M10.5 11H12v6M10.5 17h3",
    "M8 15a4 4 0 1 1 3.5-6H21v3h-2v3h-3v-3h-4.5A4 4 0 0 1 8 15z",
    "M7 3h10v6a5 5 0 0 1-10 0zM7 5H3c0 3 2 5 4.5 5M17 5h4c0 3-2 5-4.5 5M12 14v4M8 21h8M9.5 18h5" };

static int cmd_icon(int id)
{
    static const signed char m[74] = {
        IC_MOVE, IC_STOP, IC_ATTACK, IC_GROUND, IC_INSTALL, IC_INSTALL, IC_BOMB, IC_BOMB, IC_EYE, IC_RADAR,
        IC_LOAD, IC_UNLOAD, IC_HEAL, IC_REPAIR, IC_TELEPORT, IC_MINE, IC_RADAR, IC_RADAR, IC_REPAIR, IC_CLOAK,
        IC_MINE, IC_ATTACK, IC_BOMB, IC_DOT, IC_CLOAK, IC_SHIELD, IC_DASH, IC_BOMB, IC_CLOAK, IC_BOMB,
        IC_DASH, IC_DOT, IC_BOMB, IC_CLOAK, IC_MINE, IC_ATTACK, IC_ATTACK, IC_DASH, IC_TELEPORT, IC_BOMB,
        IC_SHIELD, IC_DOT, IC_SHIELD, IC_SHIELD, IC_MINE, IC_BOMB, IC_RADAR, IC_ATTACK, IC_ATTACK, IC_MINE,
        IC_BOMB, IC_SHIELD, IC_SHIELD, IC_BOMB, IC_TELEPORT, IC_DOT, IC_DOT, IC_DOT, IC_DOT, IC_MOVE,
        IC_HEAL, IC_HEAL, IC_INSTALL, IC_INSTALL, IC_DOT, IC_DOT, IC_DOT, IC_DOT, IC_DOT, IC_ATTACK,
        IC_ATTACK, IC_RADAR, IC_DASH, IC_DASH };
    return (id >= 0 && id < 74) ? m[id] : IC_DOT;
}

#include "sghud_interp.h"
#include "sghud_state.h"
#include "sghud_login_input.h"
#include "sghud_frame.h"
#include "sghud_draw.h"
#include "sghud_parts.h"
#include "sghud_login_paint.h"
#include "sghud_honor.h"
#include "sghud_pages.h"
#include "sghud_paint.h"
#include "sghud_mouse.h"
