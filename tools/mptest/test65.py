"""test65 (user 2026-10-25 20:35): F34 code challenge.  The server asks 0xF7 [nonce][start][count]; the PATCHED CLIENT
CODE (the real exe, run in an x86 emulator when 'unicorn' is installed) answers 0xF8; right answer passes, a replayed /
wrong one or none disconnects.  Needs the patched exe: SG_EXE (default /mnt/user-data/uploads/SGgalaxy/out/SG_cn.exe)."""
import sys, os, time, struct, asyncio, random
os.chdir('/tmp/mp'); sys.path.insert(0, '/tmp/mp')
import sgserver as S
S.LOG = open('/tmp/mp/server65.log', 'w', encoding='utf-8')
def chk(n, ok, i=''): print(('PASS ' if ok else 'FAIL ') + n, i, flush=True)
EXE = os.environ.get('SG_EXE', '/mnt/user-data/uploads/SGgalaxy/out/SG_cn.exe')
S.CLIENT_EXE_FILES = [EXE]; S._ALLOWED_HASHES['t'] = 0
S.CHALLENGE_FIRST, S.CHALLENGE_EVERY, S.CHALLENGE_TIMEOUT = (0.1, 0.2), (0.1, 0.2), 1.0
H = S.client_code_hash(EXE)
chk('patched exe carries the F34 marker', S._exe_image(EXE)[3])
emu = None
try:
    from unicorn import Uc, UC_ARCH_X86, UC_MODE_32, UC_HOOK_CODE
    from unicorn.x86_const import UC_X86_REG_ESP, UC_X86_REG_EIP
    d = open(EXE, 'rb').read()
    pe = struct.unpack_from('<I', d, 0x3c)[0]; n = struct.unpack_from('<H', d, pe + 6)[0]; opt = struct.unpack_from('<H', d, pe + 20)[0]
    mu = Uc(UC_ARCH_X86, UC_MODE_32)
    for i in range(n):
        nm, vs, va, rs, ro = struct.unpack_from('<8sIIII', d, pe + 24 + opt + 40 * i)
        size = (max(vs, rs) + 0xfff) & ~0xfff
        mu.mem_map(0x400000 + va, size); mu.mem_write(0x400000 + va, d[ro:ro + min(rs, size)])
    mu.mem_map(0x100000, 0x10000); mu.mem_map(0x200000, 0x1000); mu.mem_map(0xdead0000, 0x1000)
    CALLS = {0x5a8ee0: 0, 0x5a8f80: 1, 0x5a9070: 1, 0x5aa1e0: 0, 0x5a8f50: 0}
    def emu(pkt):
        got = []
        mu.mem_write(0x200000, pkt)
        mu.mem_write(0x108000, struct.pack('<III', 0xdead0000, 0x200000, len(pkt)))
        mu.reg_write(UC_X86_REG_ESP, 0x108000)
        def hook(uc, a, sz, ud):
            if a in CALLS:
                sp = uc.reg_read(UC_X86_REG_ESP); ret = struct.unpack('<I', uc.mem_read(sp, 4))[0]
                k = CALLS[a]
                got.append((a, struct.unpack('<%dI' % k, uc.mem_read(sp + 4, 4 * k)) if k else ()))
                uc.reg_write(UC_X86_REG_ESP, sp + 4 + 4 * k); uc.reg_write(UC_X86_REG_EIP, ret)
            elif a == 0xdead0000:
                uc.emu_stop()
        h = mu.hook_add(UC_HOOK_CODE, hook)
        mu.emu_start(0x54a1d0, 0xdead0000, count=30000000)
        mu.hook_del(h)
        typ = [g[1][0] for g in got if g[0] == 0x5a8f80]
        vals = [g[1][0] for g in got if g[0] == 0x5a9070]
        return bytes(typ[:1]) + struct.pack('>II', *vals) if typ == [0xF8] and len(vals) == 2 else None
except ImportError:
    pass
class W:
    closed = False
    def is_closing(self): return self.closed
    def close(self): self.closed = True
class P:
    def __init__(s):
        s.acc, s.w, s.peer, s.logged_in, s.sent, s.lang, s.enc = 'jjjjjjjj', W(), ('1.2.3.4', 1), True, [], 'en', 'latin-1'
    def send(s, d, quiet=False): s.sent.append(d)
async def run(answer):
    p = P()
    S.client_hash_report(p, H, 0x19)
    for _ in range(60):
        await asyncio.sleep(0.05)
        q = [d for d in p.sent if d[:1] == bytes([0xF7])]
        if q and getattr(p, 'chal', None) and p.chal.get('exp') is not None:
            break
    q = [d for d in p.sent if d[:1] == bytes([0xF7])]
    if not q:
        return p, None
    pkt = q[-1]
    rep = answer(pkt)
    if rep is not None:
        S._pkt_f8(p, rep, 0xF8)
    await asyncio.sleep(S.CHALLENGE_TIMEOUT + 1.6)
    return p, pkt
async def main():
    if emu is not None:
        p, pkt = await run(lambda pk: emu(pk))
        chk('the real client code (emulated) answers right -> passes', pkt is not None and getattr(p, 'chal_ok', 0) >= 1 and not p.w.closed,
            (pkt and pkt.hex(), getattr(p, 'chal_ok', 0)))
    else:
        print('SKIP emulator (pip install unicorn)')
    p, pkt = await run(lambda pk: bytes([0xF8]) + pk[1:5] + struct.pack('>I', S.challenge_answer(EXE, *struct.unpack('>III', pk[1:13]))))
    chk('server formula answer passes', getattr(p, 'chal_ok', 0) >= 1 and not p.w.closed)
    p, pkt = await run(lambda pk: bytes([0xF8]) + pk[1:5] + struct.pack('>I', H))      # replay the static checksum
    chk('replayed static checksum -> disconnected', p.w.closed)
    p, pkt = await run(lambda pk: None)                                                  # never answers
    chk('no answer -> disconnected', p.w.closed)
asyncio.run(main())
