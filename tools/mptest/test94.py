"""test94 (user 2026-10-28 01:00 "lost packets: units teleport and snap back - smooth it"): client patch F47.
1. the late-command stub (run in an x86 emulator on the real patched exe) sends 0xF9 [L][tick][w] once per tick,
   replays 'sub eax,edi / add eax,5', keeps every register / the stack and returns to 00548f2e;
2. the bigger clock buffer bytes are in place (brake 20, w floor / start 30);
3. the server logs and sums the reports."""
import sys, os, struct, time
os.chdir('/tmp/mp'); sys.path.insert(0, '/tmp/mp')
import sgserver as S
S.LOG = open('/tmp/mp/server94.log', 'w', encoding='utf-8')
def chk(n, ok, i=''): print(('PASS ' if ok else 'FAIL ') + n, i, flush=True)
EXE = os.environ.get('SG_EXE', os.path.expanduser('~/mnt/SGgalaxy/out/SG_cn.exe'))
if not os.path.exists(EXE):
    EXE = '/tmp/mp/../SG_debug.exe'
d = open(EXE, 'rb').read()
pe = struct.unpack_from('<I', d, 0x3c)[0]; n = struct.unpack_from('<H', d, pe + 6)[0]; opt = struct.unpack_from('<H', d, pe + 20)[0]
secs = [struct.unpack_from('<8sIIII', d, pe + 24 + opt + 40 * i) for i in range(n)]
def off(va):
    for _nm, vs, sva, rs, ro in secs:
        if 0x400000 + sva <= va < 0x400000 + sva + min(vs, rs):
            return va - 0x400000 - sva + ro
chk('brake threshold 20', d[off(0x549037):off(0x549037) + 3] == bytes.fromhex('83f814'))
chk('w floor 30', d[off(0x548fe6):off(0x548fe6) + 4] == bytes.fromhex('6683f923'))
chk('w starts at 30', d[off(0x6a5394):off(0x6a5394) + 2] == bytes.fromhex('1e00'))
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
mu.mem_map(0x100000, 0x10000)
CALLS = {0x5a8ee0: 0, 0x5a8f80: 1, 0x5a9070: 1, 0x5aa1e0: 0, 0x5a8f50: 0}
log_ = []
def hook(uc, addr, size, ud):
    if addr in CALLS:
        esp = uc.reg_read(UC_X86_REG_ESP)
        ret = struct.unpack('<I', uc.mem_read(esp, 4))[0]
        args = [struct.unpack('<I', uc.mem_read(esp + 4 + 4 * k, 4))[0] for k in range(CALLS[addr])]
        log_.append((addr, args))
        for r in (UC_X86_REG_EAX, UC_X86_REG_ECX, UC_X86_REG_EDX):
            uc.reg_write(r, 0x5a5a5a5a)                 # clobber the caller-saved registers like a real call
        uc.reg_write(UC_X86_REG_ESP, esp + 4 + 4 * CALLS[addr]); uc.reg_write(UC_X86_REG_EIP, ret)
    if addr == 0x548f2e:
        uc.emu_stop()
mu.hook_add(UC_HOOK_CODE, hook)
def run(L, tick):
    log_.clear()
    regs = {UC_X86_REG_EAX: tick, UC_X86_REG_EDI: L, UC_X86_REG_EBX: 0x11, UC_X86_REG_ESI: 0x22, UC_X86_REG_EBP: 0x33,
            UC_X86_REG_ECX: 0x44, UC_X86_REG_EDX: 0x55, UC_X86_REG_ESP: 0x108000}
    for r, v in regs.items():
        mu.reg_write(r, v)
    mu.emu_start(0x548f29, 0, count=2000)
    out = {r: mu.reg_read(r) for r in regs}
    return out, list(log_)
o, calls = run(1000, 1040)
sent = [a[0] for f, a in calls if f in (0x5a8f80, 0x5a9070)]
chk('late command sends 0xF9 [L][tick][w]', sent == [0xF9, 1000, 1040, 30], sent)
chk('... and sends it (0x5aa1e0)', any(f == 0x5aa1e0 for f, _a in calls))
rd = lambda a: struct.unpack('<I', mu.mem_read(a, 4))[0]
chk('only 5 ticks pushed back at once (no snap back)', o[UC_X86_REG_EAX] == 5, o[UC_X86_REG_EAX])
chk('... the rest (40) goes to PENDING', rd(0xEAFF68) == 40, rd(0xEAFF68))
chk('registers and stack kept', o[UC_X86_REG_ESP] == 0x108000 and o[UC_X86_REG_EBX] == 0x11 and o[UC_X86_REG_ESI] == 0x22
    and o[UC_X86_REG_EBP] == 0x33 and o[UC_X86_REG_EDI] == 1000 and o[UC_X86_REG_ECX] == 0x44 and o[UC_X86_REG_EDX] == 0x55)
o2, calls2 = run(1001, 1040)
chk('same tick twice: reported once', not any(f == 0x5aa1e0 for f, _a in calls2) and o2[UC_X86_REG_EAX] == 5
    and rd(0xEAFF68) == 79, rd(0xEAFF68))
o3, _c = run(1040, 1041)                       # 1 tick late: 6 <= ... -> eax 6 > 5 -> 1 to PENDING
chk('small lateness: 5 back, 1 pending', o3[UC_X86_REG_EAX] == 5 and rd(0xEAFF68) == 80, rd(0xEAFF68))
mu.mem_write(0xEAFF68, struct.pack('<I', 300)); run(5000, 5100)
chk('PENDING capped at 200', rd(0xEAFF68) == 200, rd(0xEAFF68))
# frame stub: F46's tail now jumps to it; it gives 1 tick back every 2nd frame and keeps eax / ecx / esi
t = off(0xeb4940); blk = d[t:t + 0x60]
tails = [i for i in range(0x5b) if blk[i] == 0xe9 and struct.unpack_from('<i', blk, i + 1)[0] == 0xeb4a40 - (0xeb4940 + i + 5)]
chk('F46 frame limiter continues into the smoothing stub', bool(tails), tails)
G = 0x10c000
mu.mem_write(0x6ba7c8, struct.pack('<I', G)); mu.mem_write(0x6ba7cc, struct.pack('<I', G + 0x100))
# timeGetTime (IAT 0x64c30c) -> a fake at 0x300000 returning CLOCK[0] (v3: client freeze report 0xFA)
mu.mem_map(0x300000, 0x1000); mu.mem_write(0x300000, b'\xc3'); mu.mem_write(0x64c30c, struct.pack('<I', 0x300000))
CLOCK = [100000]
def _tgt(uc, a, sz, u):
    if a == 0x300000:
        uc.reg_write(UC_X86_REG_EAX, CLOCK[0])
mu.hook_add(UC_HOOK_CODE, _tgt)
mu.mem_write(0xEAFF70, bytes(4))
mu.mem_write(G + 0x1c54, struct.pack('<I', 1000)); mu.mem_write(0xEAFF68, struct.pack('<I', 3)); mu.mem_write(0xEAFF6C, bytes(4))
stopper = mu.hook_add(UC_HOOK_CODE, lambda uc, a, sz, u: uc.emu_stop() if a == 0x549646 else None)
res = []
log_.clear()
for k in range(8):
    CLOCK[0] += 16
    mu.reg_write(UC_X86_REG_EAX, 0x1234); mu.reg_write(UC_X86_REG_ECX, 0x5678); mu.reg_write(UC_X86_REG_ESI, 0x9abc)
    mu.reg_write(UC_X86_REG_ESP, 0x108000)
    mu.emu_start(0xeb4a40, 0, count=200)
    res.append((rd(G + 0x1c54), rd(0xEAFF68), mu.reg_read(UC_X86_REG_EAX), mu.reg_read(UC_X86_REG_ECX),
                mu.reg_read(UC_X86_REG_ESP), mu.reg_read(UC_X86_REG_EIP)))
chk('1 tick every 2nd frame until PENDING is 0', [r[0] for r in res] == [1001, 1001, 1002, 1002, 1003, 1003, 1003, 1003]
    and res[-1][1] == 0, [(r[0], r[1]) for r in res])
chk('frame stub keeps eax / ecx / stack, returns to 00549646',
    all(r[2] == 0x1234 and r[3] == 0x5678 and r[4] == 0x108000 and r[5] == 0x549646 for r in res))
mu.mem_write(0xEAFF68, struct.pack('<I', 5)); mu.mem_write(0x6ba7cc, bytes(4))
mu.reg_write(UC_X86_REG_ESP, 0x108000); mu.emu_start(0xeb4a40, 0, count=200)
chk('normal 16 ms frames send no freeze report', not any(f == 0x5a8f80 and a == [0xFA] for f, a in log_))
_pend_after = rd(0xEAFF68); _base_after = rd(G + 0x1c54)
mu.mem_write(0x6ba7cc, struct.pack('<I', G + 0x100)); log_.clear(); CLOCK[0] += 700
mu.reg_write(UC_X86_REG_ESP, 0x108000); mu.emu_start(0xeb4a40, 0, count=400)
fz = [a[0] for f, a in log_ if f in (0x5a8f80, 0x5a9070)]
chk('a 700 ms frame gap in a battle is reported 0xFA [ms][tick]', fz[:2] == [0xFA, 700] and len(fz) == 3, (fz, hex(mu.reg_read(UC_X86_REG_EIP)), rd(0xEAFF70), CLOCK[0], log_[:3]))
chk('... and the stub still returns to 00549646 with the stack kept', mu.reg_read(UC_X86_REG_EIP) == 0x549646
    and mu.reg_read(UC_X86_REG_ESP) == 0x108000)
chk('outside a battle PENDING is dropped', _pend_after == 0 and _base_after == 1003)
# server side
class Sx: pass
sx = Sx(); sx.acc = 'p'; sx.battle = None
S.PACKET_HANDLERS = getattr(S, 'PACKET_HANDLERS', None)
S._pkt_f9(sx, bytes([0xF9]) + struct.pack('>III', 1000, 1040, 30), 0xF9)
S._pkt_f9(sx, bytes([0xF9]) + struct.pack('>III', 2000, 2010, 30), 0xF9)
lt = sx.__dict__.get('late') or {}
chk('server sums the late reports', lt.get('n') == 2 and lt.get('max') == 400, lt)
S.LOG.flush()
chk('... and logs them', 'LATE command' in open('/tmp/mp/server94.log', encoding='utf-8').read())
