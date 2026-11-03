"""test100 (user 2026-10-28 16:32 "按建议顺序": phase 2 first - our own display layer instead of cnc-ddraw).
Static checks of what ships (the runtime behaviour was tested with the real client in wine, see
claude/RENDER_UI_REDESIGN_PLAN.md):
1. client/sgrender/ddraw.dll exports DirectDrawCreate (+ the other ddraw entry points) and imports no ddraw itself;
2. SGRender.dll exports SGR_Init and SGR_DirectDrawCreate and does NOT import DDRAW.dll / d3d9.dll (d3d9 is loaded
   at run time, so a PC without it falls back to GDI);
3. the proxy's fallback order is SGRender -> ddraw_cnc.dll -> the system ddraw (strings in the binary);
4. deploy/ota_files.json ships ddraw.dll = the proxy, ddraw_cnc.dll = cnc-ddraw, SGRender.dll, ddraw.ini."""
import os, struct, json
def chk(n, ok, i=''): print(('PASS ' if ok else 'FAIL ') + n, i, flush=True)
REPO = os.path.expanduser('~/mnt/SGgalaxy')
def pe_info(path):
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
D = os.path.join(REPO, 'client/sgrender')
b, ex, im = pe_info(os.path.join(D, 'ddraw.dll'))
chk('proxy exports DirectDrawCreate', 'DirectDrawCreate' in ex, str(ex))
chk('proxy exports the other ddraw entry points', all(x in ex for x in ('DirectDrawCreateEx', 'DirectDrawEnumerateA')))
chk('proxy imports no ddraw', 'ddraw.dll' not in im, str(im))
chk('proxy fallback order SGRender -> ddraw_cnc -> system', all(s in b for s in (b'SGRender.dll', b'SGR_DirectDrawCreate', b'ddraw_cnc.dll', b'\\ddraw.dll')))
b, ex, im = pe_info(os.path.join(D, 'SGRender.dll'))
chk('SGRender exports SGR_Init and SGR_DirectDrawCreate', 'SGR_Init' in ex and 'SGR_DirectDrawCreate' in ex, str(ex))
chk('SGRender imports neither ddraw nor d3d9', 'ddraw.dll' not in im and 'd3d9.dll' not in im, str(im))
chk('SGRender loads d3d9 at run time', b'd3d9.dll' in b and b'Direct3DCreate9' in b)
ota = json.load(open(os.path.join(REPO, 'deploy/ota_files.json'), encoding='utf-8'))['common']
chk('OTA: ddraw.dll = the proxy', ota.get('ddraw.dll') == 'client/sgrender/ddraw.dll', str(ota.get('ddraw.dll')))
chk('OTA: ddraw_cnc.dll = cnc-ddraw (fallback)', 'cnc-ddraw' in str(ota.get('ddraw_cnc.dll')))
chk('OTA: SGRender.dll and ddraw.ini', ota.get('SGRender.dll') == 'client/sgrender/SGRender.dll' and 'ddraw.ini' in ota)
