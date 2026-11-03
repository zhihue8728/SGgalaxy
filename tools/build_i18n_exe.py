#!/usr/bin/env python3
"""Phase 3 of the Chinese client (2026-10-22): English strings hard-coded in the exe (.rdata) -> Chinese, written
IN PLACE (same address, zero padded), so no code reference changes and the anti-cheat code checksum (.text +
.dbgmov) stays the same.  A translation longer (in bytes) than the English is skipped and reported.
tools/i18n_exe.json = {english: traditional}; simplified via OpenCC tw2sp.
usage: build_i18n_exe.py IN.exe   -> out/SG_tw.exe (cp950), out/SG_cn.exe (gbk)"""
import sys, os, json
import opencc
HERE = os.path.dirname(os.path.abspath(__file__))
T = json.load(open(os.path.join(HERE, "i18n_exe.json"), encoding="utf-8"))
CC = opencc.OpenCC("tw2sp")
RDATA = (0x24c000, 0x24c000 + 0x4f000)          # file range of .rdata (strings live there)
BOARD_OLD = b"http://bbs.sgalaxy.com/tc_new/gamebbs/\0"      # .rdata 0x64eae0: base URL of the BOARD / SGMAIL web pages
def set_board_url(d, tag):
    """BOARD + SGMAIL load their pages from this URL; point it at our server (server/sgs/board_mail.py): /b/<c|t|e>/ = text code page"""
    host = json.load(open(os.path.join(HERE, "board_url.json"), encoding="utf-8"))["host"]
    url = ("http://%s/b/%s/" % (host, {"cn": "c", "tw": "t", "en": "e"}[tag])).encode()
    i = d.find(BOARD_OLD)
    assert i > 0 and d.find(BOARD_OLD, i + 1) < 0, "board URL string not found / not unique"
    assert len(url) < len(BOARD_OLD), "board URL too long: %d > %d" % (len(url), len(BOARD_OLD) - 1)
    d[i:i + len(BOARD_OLD)] = url + b"\0" * (len(BOARD_OLD) - len(url))
def build(src, out, conv, enc):
    d = bytearray(open(src, "rb").read())
    done, skip = 0, []
    for en, tw in T.items():
        zh = conv(tw).encode(enc, "replace")
        e = en.encode("latin-1") + b"\0"
        pos, hits = RDATA[0], 0
        while True:
            i = d.find(e, pos, RDATA[1])
            if i < 0: break
            pos = i + 1
            if d[i - 1] != 0 and i % 4:    # must be the START of a string (aligned strings may follow data)
                continue
            if len(zh) > len(en):
                skip.append(en); break
            d[i:i + len(e)] = zh + b"\0" * (len(e) - len(zh)); hits += 1
        done += hits > 0
    set_board_url(d, "cn" if enc == "gbk" else "tw")
    open(out, "wb").write(d)
    return done, skip
src = sys.argv[1]
o = os.path.join(HERE, "..", "out")
for tag, conv, enc in (("tw", lambda t: t, "cp950"), ("cn", CC.convert, "gbk")):
    n, skip = build(src, os.path.join(o, f"SG_{tag}.exe"), conv, enc)
    print(tag, "replaced", n, "/", len(T), "too long:", skip)
# English channel: the same exe, only the board URL changes (the code checksum does not cover .rdata)
d = bytearray(open(src, "rb").read()); set_board_url(d, "en"); open(os.path.join(o, "SG_en.exe"), "wb").write(d)
print("en board url set -> out/SG_en.exe")
