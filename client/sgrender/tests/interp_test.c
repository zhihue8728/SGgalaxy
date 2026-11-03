/* native test of sghud_interp.h (gcc -O2 -o t interp_test.c -lm && ./t): a unit stepping 2 px every 50 ms (sim), drawn every 16 ms; checks the shown point
   moves every frame, never jumps back, never runs ahead of the sim, the sim value is put back after the draw,
   teleports snap, and slow frames show the sim directly */
#include <stdio.h>
#include <string.h>
#include <math.h>
#include <stdlib.h>
#define IP_TEST
typedef struct { long long QuadPart; } LARGE_INTEGER;
static double g_clock;
static double ip_now(void) { return g_clock; }
static int GetPrivateProfileIntA(const char *a, const char *b, int d, const char *f) { return d; }
static int rd(const void *p, int n) { return p != 0; }
static char *g_um;
#define IP_UNITMAN g_um
#include "../sghud_interp.h"
static char unitbuf[2][0xf200];
int main(void)
{
    char um[0xb0] = {0}; char *arr[2] = { unitbuf[0], unitbuf[1] };
    g_um = um; *(int *)(um + 0xa0) = 2; *(char ***)(um + 0xa8) = arr;
    *(unsigned *)(unitbuf[0] + 4) = 11; *(unsigned *)(unitbuf[1] + 4) = 12;
    int x = 1000, y = 500, bad = 0, frames = 0, still = 0, last = -1;
    double nextstep = 50;
    for (g_clock = 0; g_clock < 3000; g_clock += 16.0) {
        while (g_clock >= nextstep) { x += 6; y += 3; nextstep += 50; if (fabs(nextstep - 1550) < 1) { x += 400; } }
        *(int *)(unitbuf[0] + 0x4bc4) = x; *(int *)(unitbuf[0] + 0x4bc8) = y;
        *(int *)(unitbuf[1] + 0x4bc4) = 7; *(int *)(unitbuf[1] + 0x4bc8) = 7;
        interp_begin();
        int sx = *(int *)(unitbuf[0] + 0x4bc4);
        if (sx > x) { bad++; printf("ahead %d > %d at %.0f\n", sx, x, g_clock); }
        if (last >= 0 && sx < last) { bad++; printf("back %d < %d at %.0f\n", sx, last, g_clock); }
        if (last >= 0 && sx == last && g_clock > 100) still++;
        if (g_clock > 1550 && g_clock < 1600 && sx < x - 50) { bad++; printf("no snap %d vs %d\n", sx, x); }
        last = sx; frames++;
        interp_end();
        if (*(int *)(unitbuf[0] + 0x4bc4) != x || *(int *)(unitbuf[1] + 0x4bc4) != 7) { bad++; printf("not restored\n"); }
    }
    printf("frames %d, frames without movement %d, errors %d\n", frames, still, bad);
    /* slow frames (120 ms > a step): shown = sim */
    int lag = 0;
    for (; g_clock < 6000; g_clock += 120.0) {
        while (g_clock >= nextstep) { x += 2; nextstep += 50; }
        *(int *)(unitbuf[0] + 0x4bc4) = x;
        interp_begin(); if (*(int *)(unitbuf[0] + 0x4bc4) != x) lag++; interp_end();
    }
    printf("slow frames shown behind the sim: %d\n", lag);
    return bad || lag > 1;
}
