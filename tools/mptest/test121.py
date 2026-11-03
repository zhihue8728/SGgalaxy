"""test121 (user 11-03 HD field units, step 1): client patch F58 (tools/patch_sg_debug_f58.py), x86 emulation.
The seven sprite draws of 0x5f59d0 go through 12-byte entries + one common stub.  For every site:
A. TABLE slot 17 = 0 (no DLL): the original draw is reached with the caller's stack, ecx, esi and every other
   register exactly as the call left them;
B. slot 17 = a recorder returning 0: it is called once with (site, Cxpf = ecx, name = esi, args -> the draw's
   arguments) and may clobber eax / ecx / edx; then the original draw is reached exactly as in A;
C. (v2) the recorder returns 1: the original is NOT run; execution returns to the caller with the draw's own
   argument bytes popped (its "ret N"), ebx / esi / edi / ebp unchanged.
SG_EXE = a patched exe (default: a copy of SG_debug.exe patched here)."""
import sys, os, struct, shutil, tempfile
def chk(n, ok, i=''): print(('PASS ' if ok else 'FAIL ') + n, i, flush=True)
HERE = os.path.dirname(os.path.abspath(__file__)); REPO = os.path.abspath(os.path.join(HERE, '..', '..'))
sys.path.insert(0, os.path.join(REPO, 'tools'))
import patch_sg_debug_f58 as F58
EXE = os.environ.get('SG_EXE')
if not EXE:
    EXE = os.path.join(tempfile.mkdtemp(), 'SG_f58.exe'); shutil.copy(os.path.join(REPO, 'SG_debug.exe'), EXE)
    d = bytearray(open(EXE, 'rb').read())
    if not F58.applied(d): F58.apply(d); open(EXE, 'wb').write(d)
d = open(EXE, 'rb').read()
chk('F58 applied', F58.applied(bytearray(d)))
from unicorn import Uc, UC_ARCH_X86, UC_MODE_32, UC_HOOK_CODE
from unicorn.x86_const import *
from keystone import Ks, KS_ARCH_X86, KS_MODE_32
pe = struct.unpack_from('<I', d, 0x3c)[0]; n = struct.unpack_from('<H', d, pe + 6)[0]; opt = struct.unpack_from('<H', d, pe + 20)[0]
secs = [struct.unpack_from('<8sIIII', d, pe + 24 + opt + 40 * i) for i in range(n)]
STACK, HOOK, SAVE, RET, CXPF, NAME = 0x100000, 0x200000, 0x201000, 0x300000, 0x400100, 0x202000
ARGS = [0x11111111, 37, -5 & 0xffffffff, 6, 9, 0xabcd, 0x1234]
def hook_code_for(rv): return bytes(Ks(KS_ARCH_X86, KS_MODE_32).asm(f"""
    mov eax, [esp+4]; mov [{SAVE:#x}], eax
    mov eax, [esp+8]; mov [{SAVE + 4:#x}], eax
    mov eax, [esp+12]; mov [{SAVE + 8:#x}], eax
    mov eax, [esp+16]; mov [{SAVE + 12:#x}], eax
    add dword ptr [{SAVE + 16:#x}], 1
    mov ecx, 0xdead; mov edx, 0xdead; mov eax, {rv}
    ret""", HOOK)[0])

def run(k, slot, rv=0):
    site, orig = F58.SITES[k]
    mu = Uc(UC_ARCH_X86, UC_MODE_32)
    for _nm, vs, va, rs, ro in secs:
        size = (max(vs, rs) + 0xfff) & ~0xfff
        mu.mem_map(0x400000 + va, size); mu.mem_write(0x400000 + va, d[ro:ro + min(rs, size)])
    for base in (STACK, HOOK, SAVE, RET, NAME):
        try: mu.mem_map(base, 0x2000)
        except Exception: pass
    mu.mem_write(HOOK, hook_code_for(rv)); mu.mem_write(NAME, b'g039mo.xpf\0')
    mu.mem_write(0xEAFFC4, struct.pack('<I', HOOK if slot else 0))
    esp = STACK + 0x1000
    for a in reversed(ARGS): esp -= 4; mu.mem_write(esp, struct.pack('<I', a))
    esp -= 4; mu.mem_write(esp, struct.pack('<I', RET))          # what the patched call pushed
    regs = {UC_X86_REG_ECX: CXPF, UC_X86_REG_ESI: NAME, UC_X86_REG_EBX: 0xb0b0, UC_X86_REG_EDI: 0xd1d1,
            UC_X86_REG_EBP: 0xbebe, UC_X86_REG_EDX: 0x4242}
    for r, v in regs.items(): mu.reg_write(r, v)
    mu.reg_write(UC_X86_REG_ESP, esp)
    # the patched call site must target this site's entry
    o = site
    tgt = site + 5 + struct.unpack('<i', bytes(mu.mem_read(site + 1, 4)))[0]
    hit = {}
    def on_code(uc, addr, size, _):
        if addr in (orig, RET):
            hit['esp'] = uc.reg_read(UC_X86_REG_ESP)
            hit['regs'] = {r: uc.reg_read(r) for r in regs}; hit['at'] = addr
            uc.emu_stop()
    mu.hook_add(UC_HOOK_CODE, on_code)
    mu.emu_start(tgt, 0, count=200)
    return tgt, esp, hit, struct.unpack('<5I', bytes(mu.mem_read(SAVE, 20))), mu

for k, (site, orig) in enumerate(F58.SITES):
    for slot in (0, 1):
        tgt, esp, hit, saved, mu = run(k, slot)
        tag = f'site {k} {site:#x} -> {orig:#x} ({"recorder" if slot else "no DLL"})'
        ok = tgt == F58.CAVE_VA + k * F58.ENTRY and hit.get('at') == orig
        ok = ok and hit['esp'] == esp and struct.unpack('<I', bytes(mu.mem_read(esp, 4)))[0] == RET
        ok = ok and all(hit['regs'][r] == v for r, v in {UC_X86_REG_ECX: CXPF, UC_X86_REG_ESI: NAME, UC_X86_REG_EBX: 0xb0b0,
                                                         UC_X86_REG_EDI: 0xd1d1, UC_X86_REG_EBP: 0xbebe}.items())
        args_ok = list(struct.unpack('<7I', bytes(mu.mem_read(esp + 4, 28)))) == ARGS
        if slot:
            rec_ok = saved == (k, CXPF, NAME, esp + 4, 1)
            chk(tag + ': recorder called once with (site, cxpf, name, args), original reached unchanged',
                ok and args_ok and rec_ok, str(saved))
        else:
            chk(tag + ': original reached unchanged, recorder not called', ok and args_ok and saved[4] == 0)

for k, (site, orig) in enumerate(F58.SITES):
    tgt, esp, hit, saved, mu = run(k, 1, rv=1)
    ok = hit.get('at') == RET and hit['esp'] == esp + 4 + F58.ARGB[k] and saved[4] == 1
    ok = ok and all(hit['regs'][r] == v for r, v in {UC_X86_REG_ESI: NAME, UC_X86_REG_EBX: 0xb0b0, UC_X86_REG_EDI: 0xd1d1,
                                                     UC_X86_REG_EBP: 0xbebe}.items())
    chk(f'site {k} {site:#x}: recorder returns 1 -> original skipped, caller resumes with {F58.ARGB[k]:#x} bytes popped', ok)
