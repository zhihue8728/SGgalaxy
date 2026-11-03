"""GAME NAME IN THE TEXT FILES (2026-11-02; user 16:15 "Shattered Galaxy改成Galactic Overlord", 16:50 check Nexon /
TacticalCommanders / Shattered Galaxy / SG, 16:53 credits "不保留"; Chinese name 银河霸主).  Idempotent:
  1. ntt.dat (UI / tutorial texts): "Shattered Galaxy", "Nexon", "SG" in the texts (not the keys)
       "SG" -> "GO" (user: "如果SG改成GO"); cn / tw: 银河霸主 / 銀河霸主, "Nexon" -> 官方, "\\Nexon\\" (a reserved-name example) -> \\GM\\
       en:      Galactic Overlord, "Nexon will" -> "Galactic Overlord staff will", "by Nexon" -> "by the Galactic
                Overlord team", "Notices from Nexon" -> "Official notices"
     - tools/i18n_ui.json (so build_i18n_dat.py keeps it), out/ntt_cn.dat, out/ntt_tw.dat (in place)
     - out/ntt_en.dat from the English ntt.dat (out/orig_dat/en/ntt.dat: rebuilt from unpacked/ntt, the original texts)
  2. out/dns_zh.dat (shared by every channel): the tutorial scripts tutscr*.txt ("Shattered Galaxy", beta@sgalaxy.com)
     and CREDITS.TXT (the old Nexon credits -> the Galactic Overlord credits below; Bink / Miles stay credited), and
     WEBINFO.TXT (the old secure.nexon.net pages, not used -> our server)
usage: python tools/rename_go_texts.py"""
import json, os, re, struct, sys

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.normpath(os.path.join(HERE, ".."))
sys.path.insert(0, HERE)
import sgdat

OLD = "Shattered Galaxy"
ZH = {"cn": ("银河霸主", "gbk"), "tw": ("銀河霸主", "cp950")}
CJK = r"[　-鿿＀-￯]"
IDEO = "[" + chr(0x4e00) + "-" + chr(0x9fff) + "]"     # ideographs only: a space after 。，！ (put there for the word wrap) stays
EN_RULES = [("\\Nexon\\", "\\GM\\"), ("Notices from Nexon.", "Official notices."),
            ("reimbursed by Nexon", "reimbursed by the Galactic Overlord team"),
            ("Nexon will", "Galactic Overlord staff will"), ("Nexon", "Galactic Overlord"),
(OLD + ": Massive Online Warfare", "Galactic Overlord"),
            (OLD, "Galactic Overlord")]
WEB = "http://%s/web/" % json.load(open(os.path.join(HERE, "board_url.json"), encoding="utf-8"))["host"]
CREDITS = """<C=0,YELLOW>CREDITS

<C=0,RED>GALACTIC OVERLORD

<L=0,RED>DEVELOPMENT & OPERATION
<L=1,GREEN>Galactic Overlord Team<R=0,YELLOW>Server, Client, Art

<L=0,RED>THIRD-PARTY SOFTWARE
<L=1,GREEN>Bink by RAD Game Tools<R=0,YELLOW>Video Playback Code
<L=1,GREEN>Miles Sound System<R=0,YELLOW>Audio

<C=0,YELLOW>Thank you for playing!
""".replace("\n", "\r\n")


def zh_name(text, name):
    """in Chinese text a name needs no spaces around it ("来到 X 的世界" -> "来到银河霸主的世界")"""
    t = text.replace("\\Nexon\\", "\\GM\\")
    t = re.sub(r"(?<![A-Za-z0-9_\\])SG(?![A-Za-z0-9_\\])", "GO", t)     # (user: SG -> GO; spaces stay)
    for old, new in ((OLD, name), ("Nexon", "官方")):
        pat = re.escape(old)
        t = re.sub(r"(?<=" + IDEO + r") ?" + pat + r" ?(?=" + CJK + r")", new, t)
        t = re.sub(r"(?<=" + IDEO + r") ?" + pat, new, t)
        t = re.sub(pat + r" ?(?=" + CJK + r")", new, t)
        t = re.sub(pat, new, t)
    return t


def en_name(text):
    for a, b in EN_RULES:
        text = text.replace(a, b)
    return re.sub(r"(?<![A-Za-z0-9_\\])SG(?![A-Za-z0-9_\\])", "GO", text)


def values_only(fn):
    """apply fn to the text after the key of every 'key<TAB>...text' line (keys stay as they are)"""
    def f(t):
        out = []
        for ln in t.split("\n"):
            if "\t" in ln and not ln.startswith(";"):
                k, _, v = ln.partition("\t")
                ln = k + "\t" + fn(v)
            out.append(ln)
        return "\n".join(out)
    return f


def write_dat(entries, out):                       # = build_i18n_dat.write_dat
    off = 4 + 17 * len(entries); idx = b""; body = b""
    for n, data in entries:
        idx += struct.pack("<I", off + len(body)) + n.encode("latin-1").ljust(13, b"\0"); body += data
    open(out, "wb").write(struct.pack("<I", len(entries)) + idx + body)


def redo_dat(src, dst, fn, enc, names=None):
    d = open(src, "rb").read()
    out, n_hit = [], 0
    for n, o, s in sgdat.read_index(d):
        b = d[o:o + s]
        if n and n not in ("equip.txt", "index.bkm") and (names is None or n.lower() in names):
            t = b.decode(enc)
            t2 = fn(n, t)
            if t2 != t:
                n_hit += 1; b = t2.encode(enc)
        out.append((n, b))
    write_dat(out, dst)
    return n_hit


def main():
    p = os.path.join(HERE, "i18n_ui.json")
    T = json.load(open(p, encoding="utf-8"))
    n = 0
    for kind in T:
        for en, v in T[kind].items():
            if isinstance(v, list) and re.search(r"Shattered Galaxy|Nexon|(?<![A-Za-z0-9_\\])SG(?![A-Za-z0-9_\\])", en):
                nv = [zh_name(v[0], ZH["tw"][0]), zh_name(v[1], ZH["cn"][0])] + v[2:]
                if nv != v:
                    T[kind][en] = nv; n += 1
    if n:
        json.dump(T, open(p, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    print("i18n_ui.json:", n, "translation(s) changed")
    for tag, (name, enc) in ZH.items():
        f = os.path.join(REPO, "out", f"ntt_{tag}.dat")
        print(f, redo_dat(f, f, lambda _n, t, name=name: values_only(lambda v: zh_name(v, name))(t), enc), "file(s) changed")
    src, dst = os.path.join(REPO, "out", "orig_dat", "en", "ntt.dat"), os.path.join(REPO, "out", "ntt_en.dat")
    print(dst, redo_dat(src, dst, lambda _n, t: values_only(en_name)(t), "latin-1"), "file(s) changed")
    dns = os.path.join(REPO, "out", "dns_zh.dat")

    def dns_fix(nm, t):
        if nm.lower() == "credits.txt":
            return CREDITS
        if nm.lower() == "webinfo.txt":           # (web pages of the old Nexon site, not used: our server instead)
            return t.replace("https://secure.nexon.net/newsg/", WEB).replace("http://sgpage.html", WEB + "page.html")
        t = t.replace("Please send any questions or comments to beta@sgalaxy.com.",
                      "Please send any questions or comments through the in-game board.")
        return t.replace(OLD + ": Massive Online Warfare", "Galactic Overlord").replace(OLD, "Galactic Overlord")
    print(dns, redo_dat(dns, dns, dns_fix, "latin-1", {"credits.txt", "tutscr.txt", "tutscrj.txt", "tutscrk.txt", "webinfo.txt"}), "file(s) changed")


if __name__ == "__main__":
    main()
