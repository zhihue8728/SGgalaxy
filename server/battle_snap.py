"""Battle world snapshot (2026-10-23, claude/NPC_BATTLE_AI_ARCH.md P1): the server cannot see the battle - every client
simulates it (lock-step) - so the NPC / alien AI worked on ESTIMATED positions.  The 1.8.5 client can dump its whole
world on request:

  server class-A 0x0E [06][u32 T]  (client 00547540 case 5) -> FUN_004a9890 builds the dump; T = 0 leaves the client's
                                    clock alone (T != 0 would reset its clock base).
  client 0x1d [u16 zlen][zlib( u32 T, u16 n, n x UNIT, u8 nObj x {u32 id, u16, u32, u8}, ... )]
  UNIT (0x38 + 4 m bytes, 004a9890):
      u32 uid, u16 x, u16 y, u8 command,
      u16 hp (ring +0xa464, the value 004cb3d0 subtracts damage from), u16 energy?, u16 ?,
      u8 flags x4, u32, u32, u16 dest_x?, u16 dest_y?, 6 x u32, u8 m, m x u32

parse() is defensive: a layout mismatch returns None (the caller then keeps its estimates)."""
import struct, zlib

REC_FIXED = 0x38


def parse(body):
    """body = the whole client packet (starting with 0x1d).  -> {"T": int, "units": {uid: {...}}} or None."""
    try:
        if len(body) < 4 or body[0] != 0x1D:
            return None
        zlen = struct.unpack_from(">H", body, 1)[0]
        raw = body[3:3 + zlen]
        try:
            d = zlib.decompress(raw)
        except zlib.error:
            d = zlib.decompress(raw, -15)
        T, n = struct.unpack_from(">IH", d, 0)
        o = 6
        units = {}
        for _ in range(n):
            if o + REC_FIXED > len(d):
                return None
            uid, x, y, cmd, hp, en, f3 = struct.unpack_from(">IHHBHHH", d, o)
            fl = d[o + 15:o + 19]
            a, b, dx, dy = struct.unpack_from(">IIHH", d, o + 19)
            m = d[o + 0x37]
            if o + REC_FIXED + 4 * m > len(d):
                return None
            units[uid] = {"x": x, "y": y, "cmd": cmd, "hp": hp, "en": en, "f3": f3, "flags": bytes(fl),
                          "a": a, "b": b, "dest": (dx, dy)}
            o += REC_FIXED + 4 * m
        return {"T": T, "units": units, "rest": len(d) - o}
    except Exception:
        return None
