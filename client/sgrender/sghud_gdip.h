/* sghud_gdip.h - the GDI+ flat API, loaded at run time from gdiplus.dll (no import: without GDI+ the HUD is off).
 * Only what the HUD uses.  Signatures: Windows SDK gdiplusflat.h. */
#ifndef SGHUD_GDIP_H
#define SGHUD_GDIP_H
#include <windows.h>

typedef int GpStatus;
typedef float REAL;
typedef DWORD ARGB;
typedef void GpGraphics, GpImage, GpBitmap, GpBrush, GpSolidFill, GpPen, GpPath, GpFont, GpFontFamily,
             GpFontCollection, GpStringFormat, GpMatrix, GpLineGradient;
typedef struct { REAL X, Y; } GpPointF;
typedef struct { REAL X, Y, Width, Height; } GpRectF;
typedef struct { UINT32 GdiplusVersion; void *DebugEventCallback; BOOL SuppressBackgroundThread; BOOL SuppressExternalCodecs; } GdipStartupInput;

#define GP_PARGB          0x000E200B   /* PixelFormat32bppPARGB */
#define GP_UNIT_PIXEL     2
#define GP_SMOOTH_AA      4
#define GP_TEXT_AA        4            /* TextRenderingHintAntiAlias */
#define GP_PIXOFF_HALF    4
#define GP_FONT_BOLD      1
#define GP_ALIGN_NEAR     0
#define GP_ALIGN_CENTER   1
#define GP_ALIGN_FAR      2
#define GP_SF_NOWRAP      0x1000
#define GP_SF_NOCLIP      0x4000
#define GP_TRIM_ELLIPSIS  3
#define GP_CAP_ROUND      2
#define GP_JOIN_ROUND     2
#define GP_FILL_ALT       0
#define GP_COMBINE_REPLACE 0
#define GP_DASH_DASH      1

#define GDIP_FUNCS(X) \
    X(GpStatus, GdiplusStartup, (ULONG_PTR *, const GdipStartupInput *, void *)) \
    X(GpStatus, GdipCreateBitmapFromScan0, (INT, INT, INT, INT, BYTE *, GpBitmap **)) \
    X(GpStatus, GdipGetImageGraphicsContext, (GpImage *, GpGraphics **)) \
    X(GpStatus, GdipDeleteGraphics, (GpGraphics *)) \
    X(GpStatus, GdipDisposeImage, (GpImage *)) \
    X(GpStatus, GdipSetSmoothingMode, (GpGraphics *, INT)) \
    X(GpStatus, GdipSetTextRenderingHint, (GpGraphics *, INT)) \
    X(GpStatus, GdipSetPixelOffsetMode, (GpGraphics *, INT)) \
    X(GpStatus, GdipCreateSolidFill, (ARGB, GpSolidFill **)) \
    X(GpStatus, GdipSetSolidFillColor, (GpSolidFill *, ARGB)) \
    X(GpStatus, GdipDeleteBrush, (GpBrush *)) \
    X(GpStatus, GdipCreateLineBrush, (const GpPointF *, const GpPointF *, ARGB, ARGB, INT, GpLineGradient **)) \
    X(GpStatus, GdipCreatePen1, (ARGB, REAL, INT, GpPen **)) \
    X(GpStatus, GdipDeletePen, (GpPen *)) \
    X(GpStatus, GdipSetPenLineCap197819, (GpPen *, INT, INT, INT)) \
    X(GpStatus, GdipSetPenLineJoin, (GpPen *, INT)) \
    X(GpStatus, GdipSetPenDashStyle, (GpPen *, INT)) \
    X(GpStatus, GdipFillRectangle, (GpGraphics *, GpBrush *, REAL, REAL, REAL, REAL)) \
    X(GpStatus, GdipDrawRectangle, (GpGraphics *, GpPen *, REAL, REAL, REAL, REAL)) \
    X(GpStatus, GdipFillEllipse, (GpGraphics *, GpBrush *, REAL, REAL, REAL, REAL)) \
    X(GpStatus, GdipDrawEllipse, (GpGraphics *, GpPen *, REAL, REAL, REAL, REAL)) \
    X(GpStatus, GdipDrawArc, (GpGraphics *, GpPen *, REAL, REAL, REAL, REAL, REAL, REAL)) \
    X(GpStatus, GdipDrawLine, (GpGraphics *, GpPen *, REAL, REAL, REAL, REAL)) \
    X(GpStatus, GdipFillPolygon, (GpGraphics *, GpBrush *, const GpPointF *, INT, INT)) \
    X(GpStatus, GdipDrawPolygon, (GpGraphics *, GpPen *, const GpPointF *, INT)) \
    X(GpStatus, GdipCreatePath, (INT, GpPath **)) \
    X(GpStatus, GdipDeletePath, (GpPath *)) \
    X(GpStatus, GdipStartPathFigure, (GpPath *)) \
    X(GpStatus, GdipClosePathFigure, (GpPath *)) \
    X(GpStatus, GdipAddPathLine, (GpPath *, REAL, REAL, REAL, REAL)) \
    X(GpStatus, GdipAddPathBezier, (GpPath *, REAL, REAL, REAL, REAL, REAL, REAL, REAL, REAL)) \
    X(GpStatus, GdipAddPathEllipse, (GpPath *, REAL, REAL, REAL, REAL)) \
    X(GpStatus, GdipAddPathRectangle, (GpPath *, REAL, REAL, REAL, REAL)) \
    X(GpStatus, GdipDrawPath, (GpGraphics *, GpPen *, GpPath *)) \
    X(GpStatus, GdipFillPath, (GpGraphics *, GpBrush *, GpPath *)) \
    X(GpStatus, GdipSetClipPath, (GpGraphics *, GpPath *, INT)) \
    X(GpStatus, GdipSetClipRect, (GpGraphics *, REAL, REAL, REAL, REAL, INT)) \
    X(GpStatus, GdipResetClip, (GpGraphics *)) \
    X(GpStatus, GdipCreateFontFamilyFromName, (const WCHAR *, GpFontCollection *, GpFontFamily **)) \
    X(GpStatus, GdipDeleteFontFamily, (GpFontFamily *)) \
    X(GpStatus, GdipCreateFont, (const GpFontFamily *, REAL, INT, INT, GpFont **)) \
    X(GpStatus, GdipDeleteFont, (GpFont *)) \
    X(GpStatus, GdipNewPrivateFontCollection, (GpFontCollection **)) \
    X(GpStatus, GdipPrivateAddFontFile, (GpFontCollection *, const WCHAR *)) \
    X(GpStatus, GdipGetFontCollectionFamilyList, (GpFontCollection *, INT, GpFontFamily **, INT *)) \
    X(GpStatus, GdipCreateStringFormat, (INT, LANGID, GpStringFormat **)) \
    X(GpStatus, GdipDeleteStringFormat, (GpStringFormat *)) \
    X(GpStatus, GdipSetStringFormatAlign, (GpStringFormat *, INT)) \
    X(GpStatus, GdipSetStringFormatLineAlign, (GpStringFormat *, INT)) \
    X(GpStatus, GdipSetStringFormatFlags, (GpStringFormat *, INT)) \
    X(GpStatus, GdipSetStringFormatTrimming, (GpStringFormat *, INT)) \
    X(GpStatus, GdipDrawString, (GpGraphics *, const WCHAR *, INT, const GpFont *, const GpRectF *, const GpStringFormat *, const GpBrush *)) \
    X(GpStatus, GdipLoadImageFromFile, (const WCHAR *, GpImage **)) \
    X(GpStatus, GdipLoadImageFromStream, (void *, GpImage **)) \
    X(GpStatus, GdipPrivateAddMemoryFont, (GpFontCollection *, const void *, INT)) \
    X(GpStatus, GdipGetImageWidth, (GpImage *, UINT *)) \
    X(GpStatus, GdipGetImageHeight, (GpImage *, UINT *)) \
    X(GpStatus, GdipSetInterpolationMode, (GpGraphics *, INT)) \
    X(GpStatus, GdipTranslateWorldTransform, (GpGraphics *, REAL, REAL, INT)) \
    X(GpStatus, GdipDrawImageRectRect, (GpGraphics *, GpImage *, REAL, REAL, REAL, REAL, REAL, REAL, REAL, REAL, INT, const void *, void *, void *)) \
    X(GpStatus, GdipMeasureString, (GpGraphics *, const WCHAR *, INT, const GpFont *, const GpRectF *, const GpStringFormat *, GpRectF *, INT *, INT *))

#define GDIP_DECL(ret, name, args) static ret (WINAPI *p##name) args;
GDIP_FUNCS(GDIP_DECL)

static int gdip_load(void)
{
    static int state;                                  /* 0 not tried, 1 ok, -1 failed */
    if (state) return state > 0;
    state = -1;
    HMODULE m = LoadLibraryA("gdiplus.dll");
    if (!m) return 0;
#define GDIP_GET(ret, name, args) if (!(p##name = (ret (WINAPI *) args)GetProcAddress(m, #name))) return 0;
    GDIP_FUNCS(GDIP_GET)
    GdipStartupInput in = { 1, NULL, FALSE, FALSE };
    ULONG_PTR tok;
    if (pGdiplusStartup(&tok, &in, NULL) != 0) return 0;
    state = 1;
    return 1;
}
#endif
