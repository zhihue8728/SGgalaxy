#!/usr/bin/env python3
"""Phase 2 of the Chinese client (2026-10-22): translated ntt.dat (UI texts) and hlp.dat (unit / item help).
Translations: tools/i18n_ui.json {"ntt": {english: [traditional, simplified]}, "hlp": {...}} (machine-translated
draft, to be proofread).  Writes out/ntt_tw.dat, out/ntt_cn.dat (cp950 / gbk) from the game's ntt.dat and
out/hlp_tw.dat, out/hlp_cn.dat from out/hlp_fixed.dat (build_hlp.py output; InfoTbl.txt names stay English, the
client matches items by them).  equip.txt / index.bkm stay unchanged.
Rules applied here: leading / trailing whitespace of the English text is kept; "[能力：" -> "[技能："; a space is
put after Chinese full stops / commas so the client's word wrap (breaks at spaces) can break long lines.
usage: build_i18n_dat.py GAMEDIR"""
import sys, os, json, re
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import sgdat
HERE = os.path.dirname(os.path.abspath(__file__))
T = json.load(open(os.path.join(HERE, "i18n_ui.json"), encoding="utf-8"))
sys.path.insert(0, os.path.join(HERE, "..", "server"))
import unitnames
UNITZH = {"tw": unitnames.TW, "cn": unitnames.CN}
ITEMZH = json.load(open(os.path.join(HERE, "..", "server", "item_names_zh.json"), encoding="utf-8"))
PUNCT = re.compile(r"([，。；！？：、])(?=[^\s\\\]）」』,.;:!?]|$)")

def fix(en, zh):
    zh = zh.replace("[能力：", "[技能：").replace("[能力:", "[技能：")
    zh = PUNCT.sub(r"\1 ", zh).rstrip(" ")
    lead = en[:len(en) - len(en.lstrip())]
    trail = en[len(en.rstrip()):]
    return lead + zh.strip() + trail

def tr(kind, en, k):
    v = T[kind].get(en)
    return fix(en, v[k]) if v else en

# (2026-10-27 "still English in the game") hlp texts whose numbers change with the item stats (ability lines, hide
# tiers) cannot be matched exactly: fallbacks below.  Anything still English is listed by the build (hlp_missing).
SKILL_ZH = {"Repair": ("修理", "修理"), "Heal": ("治療", "治疗"), "?": ("主動技能", "主动技能")}
ABILITY = re.compile(r"^(.*?)\s*\[Ability: (.+?) - (\d+) kJ per use(?:, power (\d+))?\]\s*$", re.S)
HIDE = re.compile(r"^The creature's natural hide \(tier (\d+)\)\.$")

def tr_hlp(en, k):
    """hlp text -> Chinese, or None when there is no translation."""
    if en in T["hlp"]:
        return tr("hlp", en, k)
    m = HIDE.match(en.strip())
    if m:
        return ("生物的天然外皮（等級 %s）。" if k == 0 else "生物的天然外皮（等级 %s）。") % m.group(1)
    m = ABILITY.match(en)
    if m:
        base, sk, kj, pw = m.groups()
        if base.strip() and base.strip() not in T["hlp"]:
            return None
        b = tr("hlp", base.strip(), k) if base.strip() else ""
        skn = SKILL_ZH.get(sk, (sk, sk))[k]
        line = f"[技能：{skn} - 每次 {kj} kJ" + ((f"，威力 {pw}" if k else f"，威力 {pw}") if pw else "") + "]"
        return fix(en, b + line) if b else line
    return None

def write_dat(entries, out):
    import struct
    off = 4 + 17 * len(entries); idx = b""; body = b""
    for n, data in entries:
        idx += struct.pack("<I", off + len(body)) + n.encode("latin-1").ljust(13, b"\0"); body += data
    open(out, "wb").write(struct.pack("<I", len(entries)) + idx + body)

def main():
    gd = sys.argv[1]
    src = os.path.join(gd, "ntt.dat.orig") if os.path.exists(os.path.join(gd, "ntt.dat.orig")) else os.path.join(gd, "ntt.dat")
    d = open(src, "rb").read()
    ntt = [(n, d[o:o + s]) for n, o, s in sgdat.read_index(d)]
    h = open(os.path.join(HERE, "..", "out", "hlp_fixed.dat"), "rb").read()
    hlp = [(n, h[o:o + s]) for n, o, s in sgdat.read_index(h)]
    for k, tag, enc in ((0, "tw", "cp950"), (1, "cn", "gbk")):
        miss = 0
        out = []
        for n, b in ntt:
            if n in ("equip.txt", "index.bkm", ""):
                out.append((n, b)); continue
            lines = []
            for ln in b.decode("latin-1").split("\n"):
                cr = ln.endswith("\r"); core = ln[:-1] if cr else ln
                if "\t" in core and not core.startswith(";"):
                    key, _, rest = core.partition("\t")
                    tabs = rest[:len(rest) - len(rest.lstrip("\t"))]; val = rest[len(tabs):]
                    if val.strip():
                        if val not in T["ntt"]:
                            miss += 1
                        core = key + "\t" + tabs + tr("ntt", val, k)
                lines.append(core + ("\r" if cr else ""))
            out.append((n, "\n".join(lines).encode(enc, "replace")))
        write_dat(out, os.path.join(HERE, "..", "out", f"ntt_{tag}.dat"))
        outh, hmiss = [], []
        for n, b in hlp:
            if n.lower() == "infotbl.txt":
                # item names (category 1) in Chinese, the same as the server's item database (item_names_zh.json)
                lines = []
                for ln in b.decode("latin-1").split("\n"):
                    cr = ln.endswith("\r"); core = ln[:-1] if cr else ln
                    f = core.split("\t")
                    if len(f) >= 3 and f[0] == "1" and f[1] in ITEMZH[tag]:
                        f[1] = ITEMZH[tag][f[1]]
                    elif len(f) >= 3 and f[0] != "1" and f[1] in UNITZH[tag]:
                        f[1] = UNITZH[tag][f[1]]          # chassis names, same as server/unitnames.py
                    lines.append("\t".join(f) + ("\r" if cr else ""))
                outh.append((n, "\n".join(lines).encode(enc, "replace"))); continue
            if not n:
                outh.append((n, b)); continue
            en = b.decode("latin-1")
            zh = tr_hlp(en, k)
            if zh is None and re.search(r"[A-Za-z]{3,}.*[A-Za-z]{3,}.*[A-Za-z]{3,}", en):
                hmiss.append((n, en))
            outh.append((n, zh.encode(enc, "replace") if zh is not None else b))
        write_dat(outh, os.path.join(HERE, "..", "out", f"hlp_{tag}.dat"))
        print(tag, "ntt untranslated lines", miss, "/ hlp untranslated texts", len(hmiss))
        for n, en in hmiss[:20]:
            print("   hlp_missing", n, en[:100])
main()
