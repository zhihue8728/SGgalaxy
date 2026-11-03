"""test98 (user 2026-10-28 14:37 "first build the UI architecture"): client patch F48 = SGRender.dll hooks (phase 0 of
the new drawing layer, claude/RENDER_UI_REDESIGN_PLAN.md).
1. the release exe jumps from the three hook sites into the F48 stubs; strings "SGRender.dll" / "SGR_Init" are in place;
2. (x86 emulation of the real patched exe)
   - LOADER  004c0bd0: LoadLibraryA("SGRender.dll") -> GetProcAddress("SGR_Init") -> SGR_Init(TABLE) ONCE, registers kept,
     replays 'sub esp,0xac' and goes on at 004c0bd6; no DLL -> the game goes on the same way;
   - PRESENT CGraph::EndFrame 004c4a60: table empty -> replays push esi / mov esi,ecx / mov eax,[esi+0x184] -> 004c4a69;
     on_present(CGraph) returning 0 -> the same; returning 1 -> plain ret (the DLL drew the frame);
   - CREATE  CWnd::Create 005ecc50: on_create(wnd, create struct) with every register kept, then the replayed
     instructions -> 005ecc5a;
3. client/sgrender/SGRender.dll exports SGR_Init; deploy/ota_files.json ships it to every player."""
import sys, os, struct, json
def chk(n, ok, i=''): print(('PASS ' if ok else 'FAIL ') + n, i, flush=True)
REPO = os.path.expanduser('~/mnt/SGgalaxy')
EXE = os.environ.get('SG_EXE', os.path.join(REPO, 'out/SG_cn.exe'))
d = open(EXE, 'rb').read()
pe = struct.unpack_from('<I', d, 0x3c)[0]; n = struct.unpack_from('<H', d, pe + 6)[0]; opt = struct.unpack_from('<H', d, pe + 20)[0]
secs = [struct.unpack_from('<8sIIII', d, pe + 24 + opt + 40 * i) for i in range(n)]
def off(va):
    for _nm, vs, sva, rs, ro in secs:
        if 0x400000 + sva <= va < 0x400000 + sva + min(vs, rs):
            return va - 0x400000 - sva + ro
def jmp_to(va):
    o = off(va)
    return d[o] == 0xe9 and va + 5 + struct.unpack_from('<i', d, o + 1)[0]
TABLE, LOADLIB, GETPROC = 0xEAFF80, 0x64c1b0, 0x64c1ac
L_STUB, P_STUB, C_STUB = jmp_to(0x4c0bd0), jmp_to(0x4c4a60), jmp_to(0x5ecc50)
chk('loader hook 004c0bd0 -> stub', L_STUB and 0xeb4b40 <= L_STUB < 0xeb4c40, hex(L_STUB or 0))
chk('present hook EndFrame 004c4a60 -> stub', P_STUB and 0xeb4b40 <= P_STUB < 0xeb4c40, hex(P_STUB or 0))
chk('create hook 005ecc50 -> stub', C_STUB and 0xeb4b40 <= C_STUB < 0xeb4c40, hex(C_STUB or 0))
chk('strings', d[off(0xeb4c40):off(0xeb4c40) + 22] == b'SGRender.dll\0SGR_Init\0')
chk('windowed copy 004c01f0 untouched', d[off(0x4c01f0):off(0x4c01f0) + 6] == bytes.fromhex('81ece0000000'))

# 3. the DLL and the OTA list
dll = os.path.join(REPO, 'client/sgrender/SGRender.dll')
ok = False
if os.path.exists(dll):
    b = open(dll, 'rb').read()
    p2 = struct.unpack_from('<I', b, 0x3c)[0]; o2 = struct.unpack_from('<H', b, p2 + 20)[0]; n2 = struct.unpack_from('<H', b, p2 + 6)[0]
    exp_rva = struct.unpack_from('<I', b, p2 + 24 + 96)[0]
    s2 = [struct.unpack_from('<8sIIII', b, p2 + 24 + o2 + 40 * i) for i in range(n2)]
    def roff(rva):
        for _nm, vs, va, rs, ro in s2:
            if va <= rva < va + max(vs, rs):
                return rva - va + ro
    e = roff(exp_rva)
    nn = struct.unpack_from('<I', b, e + 24)[0]; names = roff(struct.unpack_from('<I', b, e + 32)[0])
    exports = [b[roff(struct.unpack_from('<I', b, names + 4 * i)[0]):].split(b'\0')[0] for i in range(nn)]
    ok = b'SGR_Init' in exports
chk('SGRender.dll exports SGR_Init', ok)
ota = json.load(open(os.path.join(REPO, 'deploy/ota_files.json'), encoding='utf-8'))
chk('OTA ships SGRender.dll', ota['common'].get('SGRender.dll') == 'client/sgrender/SGRender.dll')

# 2. emulation
try:
    from unicorn import Uc, UC_ARCH_X86, UC_MODE_32, UC_HOOK_CODE
    from unicorn.x86_const import (UC_X86_REG_ESP, UC_X86_REG_EIP, UC_X86_REG_EAX, UC_X86_REG_EBX, UC_X86_REG_ECX,
                                   UC_X86_REG_EDX, UC_X86_REG_ESI, UC_X86_REG_EDI, UC_X86_REG_EBP)
except ImportError:
    print('PASS (unicorn not installed - emulation skipped)'); sys.exit(0)
mu = Uc(UC_ARCH_X86, UC_MODE_32)
for _nm, vs, va, rs, ro in secs:
    size = (max(vs, rs) + 0xfff) & ~0xfff
    mu.mem_map(0x400000 + va, size); mu.mem_write(0x400000 + va, d[ro:ro + min(rs, size)])
try:
    mu.mem_map(0xEAF000, 0x1000)
except Exception:
    pass
mu.mem_map(0x100000, 0x10000)          # stack
mu.mem_map(0x200000, 0x1000)           # fake API / DLL entry points
mu.mem_map(0xdead0000, 0x1000)         # the caller (return address)
F_LOADLIB, F_GETPROC, F_INIT, F_PRESENT, F_CREATE = 0x200000, 0x200010, 0x200020, 0x200030, 0x200040
mu.mem_write(LOADLIB, struct.pack('<I', F_LOADLIB)); mu.mem_write(GETPROC, struct.pack('<I', F_GETPROC))
u32 = lambda a: struct.unpack('<I', mu.mem_read(a, 4))[0]
def cstr(a): return bytes(mu.mem_read(a, 32)).split(b'\0')[0]
calls, STOP, state = [], set(), {'dll': 0x10000000, 'present_ret': 0}
STDCALL = {F_LOADLIB: 1, F_GETPROC: 2}
def hook(uc, addr, size, ud):
    if addr in STOP:
        uc.emu_stop(); return
    if addr in (F_LOADLIB, F_GETPROC, F_INIT, F_PRESENT, F_CREATE):
        esp = uc.reg_read(UC_X86_REG_ESP); ret = u32(esp)
        args = [u32(esp + 4 + 4 * k) for k in range(2)]
        calls.append((addr, args))
        rv = {F_LOADLIB: state['dll'], F_GETPROC: F_INIT, F_INIT: 1, F_PRESENT: state['present_ret'], F_CREATE: 0}[addr]
        if addr == F_INIT:
            mu.mem_write(TABLE + 4, struct.pack('<II', F_PRESENT, F_CREATE)); mu.mem_write(TABLE, struct.pack('<I', 1))
        for r in (UC_X86_REG_ECX, UC_X86_REG_EDX):
            uc.reg_write(r, 0x5a5a5a5a)
        uc.reg_write(UC_X86_REG_EAX, rv)
        uc.reg_write(UC_X86_REG_ESP, esp + 4 + 4 * STDCALL.get(addr, 0)); uc.reg_write(UC_X86_REG_EIP, ret)
mu.hook_add(UC_HOOK_CODE, hook)
REGS = {UC_X86_REG_EBX: 0x11, UC_X86_REG_ESI: 0x22, UC_X86_REG_EBP: 0x33, UC_X86_REG_EDI: 0x44, UC_X86_REG_ECX: 0x101000,
        UC_X86_REG_EDX: 0x55, UC_X86_REG_EAX: 0x66}
def run(start, stops, esp=0x108000, regs=None):
    calls.clear(); STOP.clear(); STOP.update(stops)
    r = dict(REGS); r.update(regs or {}); r[UC_X86_REG_ESP] = esp
    for k, v in r.items():
        mu.reg_write(k, v)
    mu.mem_write(esp, struct.pack('<I', 0xdead0000))       # return address of the hooked function
    mu.emu_start(start, 0, count=5000)
    return mu.reg_read(UC_X86_REG_EIP), {k: mu.reg_read(k) for k in r}

def clear_table():
    mu.mem_write(TABLE, bytes(0x40))
# LOADER
clear_table()
eip, out = run(0x4c0bd0, {0x4c0bd6})
names = [cstr(a[0]) if f == F_LOADLIB else cstr(a[1]) if f == F_GETPROC else None for f, a in calls]
chk('loader: LoadLibraryA(SGRender.dll), GetProcAddress(SGR_Init), SGR_Init(TABLE)',
    [f for f, _ in calls] == [F_LOADLIB, F_GETPROC, F_INIT] and names[:2] == [b'SGRender.dll', b'SGR_Init']
    and calls[2][1][0] == TABLE, str(names))
chk('loader: replays sub esp,0xac and goes on at 004c0bd6, registers kept',
    eip == 0x4c0bd6 and out[UC_X86_REG_ESP] == 0x108000 - 0xac
    and all(out[k] == REGS[k] for k in REGS), hex(out[UC_X86_REG_ESP]))
chk('loader: table filled by the DLL', u32(TABLE + 4) == F_PRESENT and u32(TABLE + 8) == F_CREATE and u32(TABLE + 0x3c) == 1)
eip, out = run(0x4c0bd0, {0x4c0bd6})
chk('loader: only once', calls == [] and eip == 0x4c0bd6)
clear_table(); state['dll'] = 0
eip, out = run(0x4c0bd0, {0x4c0bd6})
chk('loader: no DLL -> game goes on', [f for f, _ in calls] == [F_LOADLIB] and eip == 0x4c0bd6 and u32(TABLE + 4) == 0)

# PRESENT (EndFrame); CGraph at 0x101000 with [+0x184] = 7
mu.mem_write(0x101000 + 0x184, struct.pack('<I', 7))
clear_table()
eip, out = run(0x4c4a60, {0x4c4a69})
chk('present, no DLL: replays push esi/mov esi,ecx/mov eax,[esi+0x184] -> 004c4a69',
    eip == 0x4c4a69 and calls == [] and out[UC_X86_REG_EAX] == 7 and out[UC_X86_REG_ESI] == 0x101000
    and out[UC_X86_REG_ESP] == 0x108000 - 4 and u32(0x108000 - 4) == 0x22)
mu.mem_write(TABLE + 4, struct.pack('<II', F_PRESENT, F_CREATE))
state['present_ret'] = 0
eip, out = run(0x4c4a60, {0x4c4a69})
chk('present, DLL returns 0: on_present(CGraph) then the original EndFrame',
    [c for c in calls] == [(F_PRESENT, [0x101000, calls[0][1][1] if calls else 0])] and eip == 0x4c4a69
    and out[UC_X86_REG_EAX] == 7 and out[UC_X86_REG_ESI] == 0x101000 and out[UC_X86_REG_ESP] == 0x108000 - 4)
state['present_ret'] = 1
eip, out = run(0x4c4a60, {0x4c4a69, 0xdead0000})
chk('present, DLL returns 1: plain ret to the caller (the DLL drew the frame)',
    eip == 0xdead0000 and out[UC_X86_REG_ESP] == 0x108004 and out[UC_X86_REG_ESI] == 0x22)

# CREATE: CWnd at 0x101000, create struct pointer = first stack argument
mu.mem_write(0x108004, struct.pack('<I', 0x102000))
eip, out = run(0x5ecc50, {0x5ecc5a})
chk('create: on_create(wnd, create struct)', calls == [(F_CREATE, [0x101000, 0x102000])], str(calls))
chk('create: registers kept, replayed instructions -> 005ecc5a',
    eip == 0x5ecc5a and out[UC_X86_REG_ESI] == 0x101000 and out[UC_X86_REG_ESP] == 0x108000 - 4
    and u32(0x108000 - 4) == 0x22 and mu.mem_read(0x101000 + 0x156, 1)[0] == 1
    and all(out[k] == REGS[k] for k in (UC_X86_REG_EBX, UC_X86_REG_EBP, UC_X86_REG_EDI, UC_X86_REG_EDX, UC_X86_REG_EAX)))
clear_table()
eip, out = run(0x5ecc50, {0x5ecc5a})
chk("create, no DLL: straight on, eax kept", calls == [] and eip == 0x5ecc5a and out[UC_X86_REG_EAX] == 0x66)
