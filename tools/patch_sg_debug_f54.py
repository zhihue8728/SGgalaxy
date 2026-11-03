"""F54 GAME NAME (2026-11-02, user 16:15 "Shattered Galaxy改成Galactic Overlord" / "SG改成GO", 16:18 + 16:32 + 16:40 the
registry keys, 16:50 "check Nexon, TacticalCommanders, Shattered Galaxy, SG").
Strings of the exe rewritten IN PLACE (same address; the new text must fit in the string's slot = up to the next
non-zero byte), so no code changes and the F16 code checksum (.text + .dbgmov) stays the same:
  .rdata
    0x64e40c "SOFTWARE\\KRU\\Shattered Galaxy"        -> "SOFTWARE\\Galactic Overlord"  HKCU value "Version" (0042d7e0:
             only when HKLM NXsgckfr exists - old Nexon anti-cheat - so normally never used)
    0x64e440 "SOFTWARE\\Nexon\\TacticalCommanders"    -> "SOFTWARE\\Galactic Overlord"  the settings (REG_NAME, REG_SG_IP ..);
             ddraw.dll copies the old key's values once (client/sgrender/sgreg.h)
    0x65a5a0 "SOFTWARE\\Nexon\\" (HKLM, TC_QSN)       -> "SOFTWARE\\GO\\" (16-byte slot); ddraw.dll opens it as
             SOFTWARE\\Galactic Overlord
    0x64e588 "SG.EXE", 0x64e590 "NEXON"              -> "GO.EXE", "|GO|": 0042df40 counts running processes whose path has
             both (never true before - no NEXON folder - and never after: '|' cannot be in a path)
    0x64ead4 "sg0.kru.com" (default server name)      -> "127.0.0.1" (REG_SG_IP is always set)
    0x658598 the DirectDraw failure message, 0x658618 window class / title / message caption "Shattered Galaxy"
             -> "Galactic Overlord"; 0x658630 "Patcher file not found ... www.sgalaxy.com" -> "... reinstall Galactic
             Overlord." (ddraw.dll answers the patcher.exe check anyway)
    0x657ef0 the abnormal-DirectX message: "SG" -> "GO"; the BBS / mail level-15 notes (en): support.kru.com -> a GM
    window classes "SG RadioConsole" / "SG SolarSystemView" / "SG ScrollPlanets" -> "GO ..." (registered and created
             through the same string)
  .data
    0x6b4330 "NexonInc." (an unused copy of the old packet key; the cipher uses 0x6b6908, F53) -> "GOverlord"
Not changed (internal names): registry value names SG_TYPE / REG_SG_IP / SG_QNO, the resource names nexonci1.bik /
Nexon800.jpg / sGalaxy.xpf (inside the .dat archives).  Idempotent.
usage: python patch_sg_debug_f54.py SG.exe [more exes]"""
import sys, shutil

RDATA = (0x24c000, 0x24c000 + 0x4f000)          # file range of .rdata (same as build_i18n_exe.py)
DATA = (0x29b000, 0x29b000 + 0x20000)           # the start of .data (initialised part)
OLD, NEW = b"Shattered Galaxy", b"Galactic Overlord"
EXACT = {                                       # whole strings (old -> new); a list: any of the old ones
    b"SOFTWARE\\KRU\\Shattered Galaxy": b"SOFTWARE\\Galactic Overlord",
    b"SOFTWARE\\KRU\\Galactic Overlord": b"SOFTWARE\\Galactic Overlord",
    b"SOFTWARE\\Nexon\\TacticalCommanders": b"SOFTWARE\\Galactic Overlord",
    b"SOFTWARE\\Nexon\\": b"SOFTWARE\\GO\\",
    b"SG.EXE": b"GO.EXE",
    b"NEXON": b"|GO|",
    b"sg0.kru.com": b"127.0.0.1",
    b"Patcher file not found. Please download new patch file from SG web site www.sgalaxy.com":
        b"Patcher file not found. Please reinstall Galactic Overlord.",
    b"SG RadioConsole": b"GO RadioConsole",
    b"SG SolarSystemView": b"GO SolarSystemView",
    b"SG ScrollPlanets": b"GO ScrollPlanets",
}
SUB = [(b" SG has detected", b" GO has detected"), (b"terminate SG and", b"terminate GO and"),
       (b"please contact us at https://support.kru.com.", b"please tell a GM in the game.")]   # (en: BBS / mail level-15 notes)
DATA_EXACT = {b"NexonInc.": b"GOverlord"}


def strings(d, rng):
    """(start, end, slot end) of every NUL-terminated string in the range"""
    i = rng[0]
    while i < rng[1]:
        if d[i] == 0:
            i += 1; continue
        e = d.index(b"\0", i)
        n = e
        while n < rng[1] and d[n] == 0:
            n += 1
        yield i, e, n
        i = e


def apply(fn):
    d = bytearray(open(fn, "rb").read())
    hits = []
    for rng, exact in ((RDATA, EXACT), (DATA, DATA_EXACT)):
        for s, e, n in strings(d, rng):
            cur = bytes(d[s:e]); new = cur
            if cur in exact:
                new = exact[cur]
            elif rng is RDATA:
                new = cur.replace(OLD, NEW)
                for a, b in SUB:
                    new = new.replace(a, b)
            if new != cur:
                assert len(new) < n - s, f"{fn}: {cur!r} does not fit ({len(new)} >= {n - s})"
                hits.append((s, n, new, cur))
    if not hits:
        print(f"{fn}: F54 already applied"); return
    shutil.copy(fn, fn + ".before_f54")
    for s, n, new, cur in hits:
        d[s:n] = new + b"\0" * (n - s - len(new))
    open(fn, "wb").write(d)
    print(f"{fn}: F54 applied, {len(hits)} string(s): " + ", ".join(repr(c[:24]) for _, _, _, c in hits))


if __name__ == "__main__":
    for fn in sys.argv[1:]:
        apply(fn)
