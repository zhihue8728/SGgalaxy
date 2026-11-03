/* shared between sgrender.c (game hooks, HUD), sgdraw.c (own DirectDraw) and sgwindow.c (window, presenter) */
#ifndef SGRENDER_H
#define SGRENDER_H
#include <windows.h>

typedef struct SGDisplay {
    int gw, gh;                 /* the game's mode (W x 600) */
    void *primary;              /* SGSurf of the primary surface: 16-bit 565 DIB, top-down */
    HWND hwnd;
    int windowed;               /* 0 = borderless full screen, 1 = window */
    int smooth;                 /* scaling filter: 1 = smooth, 0 = sharp (nearest) */
    RECT dest;                  /* where the frame lands in the client area */
    int active;
} SGDisplay;
extern SGDisplay g_disp;

void sgr_log(const char *fmt, ...);
void sgr_present(void);                    /* show the primary surface */
const char *sgr_presenter_name(void);
void sgr_window_attach(HWND hwnd);         /* SetCooperativeLevel: subclass the game window */
void sgr_window_apply(void);               /* SetDisplayMode / Alt+Enter: place the window */
void sgr_display_init(void);               /* SGR_Init: settings, DPI awareness */
int sgr_primary_info(unsigned char **bits, int *pitch, int *w, int *h);

/* native-resolution overlay (the new HUD, phase 3): a 32-bit premultiplied BGRA DIB the size of the client area,
 * drawn over the scaled frame by either presenter.  The HUD draws into it from sgr_overlay_paint (called by the
 * presenter when sgr_overlay_invalidate() was called or the window size changed). */
typedef struct SGOverlay { HDC dc; unsigned int *bits; int w, h, version; int dx0, dy0, dx1, dy1; } SGOverlay;   /* dx..: what this version changed (11-01) */
void sgr_overlay_invalidate(void);
const SGOverlay *sgr_overlay(void);           /* NULL when no overlay is shown */
int sgr_overlay_paint(SGOverlay *ov);         /* sgrender.c: draw the HUD; 0 = nothing to show */

/* sgrender.c helpers for the HUD */
const char *sgr_class(void *obj);
int sgr_debug(void);                              /* SGRender.dbg present: detailed log */                 /* RTTI class name ("CUnitWnd") or "?" */
int sgr_fog_ok(char *map);                        /* the map's fog buffer readable (check once per frame) */
int sgr_fog_visible(char *map, int px, int py);   /* map pixel clear of the fog of war */
extern volatile const char *g_stage_game, *g_stage_paint;   /* what the HUD is doing (crash report) */
/* sghud.c - the battlefield HUD */
void sghud_frame(char *app, int W, int DX);       /* every frame start (game thread): read state, run queued clicks */
int sghud_paint(SGOverlay *ov);                   /* paint into the overlay; 0 = nothing to show */
void sghud_overlay_lost(void);                     /* the overlay bits were drawn over by someone else */
void sghud_debug_spr(void);
int sgr_map_h(void);                       /* F51: the field map's height in frame rows */
void sghud_key(UINT msg, WPARAM w);           /* WM_KEYDOWN: Enter opens a folded chat */
int sghud_mouse(UINT msg, int x, int y, WPARAM w);/* client pixels; 1 = the HUD took it */
void sghud_mapped(int *gx, int *gy);              /* sghud_mouse returned 3: the game sees the mouse here (frame px) */
int sghud_over(int x, int y);                     /* client pixels over a HUD part (system cursor there) */
/* sghd.h (HD field units): the sprites of the HD art codes the game drew in this frame, in draw order (frame px) */
typedef struct SGHdRec {
    unsigned char site;          /* F58 site 0..6 */
    char name[15];               /* sprite file, lower case ("g039mo.xpf") */
    void *cxpf;
    int fx, fy;                  /* frame position of the sprite's pivot */
    int dir, frame, a5, a6;
    unsigned seq;                /* draw order in the frame (all sprites) */
} SGHdRec;
int sgr_hd_list(const SGHdRec **recs);        /* -> count; valid until the next frame begins */
int sgr_hd_debug(void);
#endif
