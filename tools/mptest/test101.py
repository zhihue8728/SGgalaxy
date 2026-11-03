"""test101 (user 2026-10-28 17:02 "下一步": phase 3 - the new battlefield HUD from the design canvas, drawn by SGRender.dll
over the game at screen resolution; see claude/BATTLE_HUD.md).  Static checks of what ships (the HUD itself was
tested with the real client in wine: cards, banner, radar, band, wheel, unit panel, clicks forwarded, zh-CN text):
1. the HUD sources are in client/sgrender and build.sh compiles sghud.c;
2. sghud_units.h (unit name -> branch) is up to date with server/units_manual.json + unitnames.py;
3. SGRender.dll exports SGR_Init / SGR_DirectDrawCreate, does not import gdiplus.dll (loaded at run time: no GDI+ ->
   no HUD, old panel) and contains the HUD (font file name, ini switch);
4. the Cinzel font + its OFL licence ship: deploy/ota_files.json common SGHud-Cinzel.ttf;
5. fairness: the radar and the enemy count only use enemies the fog of war shows (sgr_fog_visible before counting);
6. the HUD only hides the old panel / status cards while it is active (ini [hud] enable=0 = old interface)."""
import os, re, subprocess, sys, json, struct
def pe_info(path):     # (same as test100) bytes, exported names, imported dll names
    b = open(path, 'rb').read()
    pe = struct.unpack_from('<I', b, 0x3c)[0]; n = struct.unpack_from('<H', b, pe + 6)[0]; o = struct.unpack_from('<H', b, pe + 20)[0]
    secs = [struct.unpack_from('<8sIIII', b, pe + 24 + o + 40 * i) for i in range(n)]
    def roff(rva):
        for _nm, vs, va, rs, ro in secs:
            if va <= rva < va + max(vs, rs):
                return rva - va + ro
    exp_rva, imp_rva = struct.unpack_from('<I', b, pe + 24 + 96)[0], struct.unpack_from('<I', b, pe + 24 + 104)[0]
    exports = []
    if exp_rva:
        e = roff(exp_rva); nn = struct.unpack_from('<I', b, e + 24)[0]; names = roff(struct.unpack_from('<I', b, e + 32)[0])
        exports = [b[roff(struct.unpack_from('<I', b, names + 4 * i)[0]):].split(b'\0')[0].decode() for i in range(nn)]
    imports = []
    if imp_rva:
        d = roff(imp_rva)
        while True:
            name = struct.unpack_from('<I', b, d + 12)[0]
            if not name: break
            imports.append(b[roff(name):].split(b'\0')[0].decode().lower()); d += 20
    return b, exports, imports
def chk(n, ok, i=''): print(('PASS ' if ok else 'FAIL ') + n, i, flush=True)
REPO = os.path.expanduser('~/mnt/SGgalaxy')
D = os.path.join(REPO, 'client/sgrender')
src = open(os.path.join(D, 'sghud.c'), encoding='utf-8').read()
chk('HUD sources present', all(os.path.exists(os.path.join(D, f)) for f in ('sghud.c', 'sghud_gdip.h', 'sghud_units.h')))
chk('build.sh compiles sghud.c', 'sghud.c' in open(os.path.join(D, 'build.sh')).read())
r = subprocess.run([sys.executable, os.path.join(REPO, 'tools/gen_sghud_units.py'), '--check'], capture_output=True, text=True)
chk('sghud_units.h up to date', r.returncode == 0, r.stdout.strip() + r.stderr.strip()[-200:])
units = open(os.path.join(D, 'sghud_units.h'), encoding='utf-8').read()
chk('branch table has the four branches incl. CN/TW names',
    all(s in units for s in ('{L"Imp", 0', '{L"Manticore", 1', '{L"Hawk", 2', '{L"Oizys", 3', '{L"蝎狮", 1', '{L"蠍獅", 1')))
b, ex, im = pe_info(os.path.join(D, 'SGRender.dll'))
chk('SGRender exports SGR_Init and SGR_DirectDrawCreate', 'SGR_Init' in ex and 'SGR_DirectDrawCreate' in ex, str(ex))
chk('SGRender does not import gdiplus (loaded at run time)', 'gdiplus.dll' not in im, str(im))
chk('SGRender contains the HUD', b'gdiplus.dll' in b and 'SGHud-Cinzel.ttf'.encode('utf-16-le') in b and b'HUD paint' in b)
F = os.path.join(D, 'fonts')
chk('Cinzel font + OFL licence', os.path.getsize(os.path.join(F, 'SGHud-Cinzel.ttf')) > 20000 and
    'Open Font License' in open(os.path.join(F, 'OFL-Cinzel.txt'), encoding='utf-8').read())
ota = json.load(open(os.path.join(REPO, 'deploy/ota_files.json'), encoding='utf-8'))['common']
chk('OTA ships SGHud-Cinzel.ttf', ota.get('SGHud-Cinzel.ttf') == 'client/sgrender/fonts/SGHud-Cinzel.ttf', str(ota.get('SGHud-Cinzel.ttf')))
body = src[src.index('static void read_state'):src.index('/* ---- actions')]
m = re.search(r'else if \(!fog \|\| !sgr_fog_visible\(g_map, x, y\)\) continue;[^\n]*\n\s*else s->n_enemy\+\+;', body)
chk('fairness: enemies counted / shown only where the fog is clear', m is not None)
fr = src[src.index('void sghud_frame'):src.index('/* ---- painting')]
chk('old panel hidden only while the HUD is active', 'if (s->active) {' in fr and fr.index('if (s->active) {') < fr.index("g_panel[0x155] = 0"))
chk('ini switch [hud] enable', 'GetPrivateProfileIntA("hud", "enable", 1' in src)
chk('painting off the game thread', 'CreateThread' in src and 'static DWORD WINAPI painter' in src)
