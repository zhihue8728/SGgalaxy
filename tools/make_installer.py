"""FULL CLIENT INSTALLER (2026-11-02, user: "需要将客户端重新打包, 可以给我一个安装文件, 避免用户要从服务器上下载").
Builds out/GalacticOverlord_Setup_<version>.exe: the whole game for the cn channel exactly as the last published release (the
files deploy/ota_files.json names: encrypted .dat + SGHud.pak, SG.exe, DLLs, the stamped out/ota/GOLauncher.exe) plus
the original game's own files (out/orig_dat/base/: Mss32, binkw32, chigamec, thidchk, mssmp3.asi, msssoft.m3d).
The launcher then finds nothing to download (it compares SHA-256); tw / en players get only their language files.
Every file is checked against out/ota/published.json (the objects the update server has) - run it AFTER publish.bat.
Needs NSIS (makensis; Windows: https://nsis.sourceforge.io, or apt install nsis).  Script: deploy/sgalaxy_setup.nsi
usage: python tools/make_installer.py            (version = the last published one)"""
import hashlib, json, os, shutil, subprocess, sys

REPO = os.path.normpath(os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
BASE = ["Mss32.dll", "binkw32.dll", "chigamec.dll", "thidchk.dll", "mssmp3.asi", "msssoft.m3d"]   # no Patcher.exe (user 11-02 16:13): ddraw.dll answers SG.exe's check for it


def sha(p):
    h = hashlib.sha256()
    with open(p, "rb") as f:
        for b in iter(lambda: f.read(1 << 24), b""):
            h.update(b)
    return h.hexdigest()


def main():
    pub = json.load(open(os.path.join(REPO, "out", "ota", "published.json"), encoding="utf-8"))
    ver, objs = pub["version"], set(pub["objects"])
    ota = json.load(open(os.path.join(REPO, "deploy", "ota_files.json"), encoding="utf-8-sig"))
    files = dict(ota["common"]); files.update(ota["channels"]["cn"])
    stage = os.path.join(REPO, "out", "installer", "payload")
    shutil.rmtree(stage, ignore_errors=True)
    os.makedirs(stage)
    bad = []
    for dst, v in files.items():
        src = os.path.join(REPO, v["src"] if isinstance(v, dict) else v)
        shutil.copyfile(src, os.path.join(stage, dst))
        if sha(src) not in objs:
            bad.append(dst)
    shutil.copyfile(os.path.join(REPO, "out", "ota", "GOLauncher.exe"), os.path.join(stage, "GOLauncher.exe"))
    if sha(os.path.join(stage, "GOLauncher.exe")) not in objs:
        bad.append("GOLauncher.exe")
    for b in BASE:
        shutil.copyfile(os.path.join(REPO, "out", "orig_dat", "base", b), os.path.join(stage, b))
    if bad:
        sys.exit(f"not in the published release {ver} (publish first): {', '.join(bad)}")
    d = os.path.dirname(stage)
    with open(os.path.join(d, "uninstall_files.nsh"), "w", encoding="utf-8") as f:
        for n in sorted(os.listdir(stage)):
            f.write(f'  Delete "$INSTDIR\\{n}"\n')
    shutil.copyfile(os.path.join(REPO, "deploy", "sgalaxy_setup.nsi"), os.path.join(d, "sgalaxy_setup.nsi"))
    shutil.copyfile(os.path.join(REPO, "launcher", "go.ico"), os.path.join(d, "go.ico"))   # installer icon (11-02)
    mk = shutil.which("makensis") or r"C:\Program Files (x86)\NSIS\makensis.exe"
    if not os.path.exists(mk) and not shutil.which("makensis"):
        sys.exit(f"payload ready in {stage}; install NSIS to build the .exe")
    subprocess.run([mk, "-INPUTCHARSET", "UTF8", "-V2", f"-DVER={ver}", "sgalaxy_setup.nsi"], cwd=d, check=True)   # (the script is UTF-8: Chinese texts)
    out = os.path.join(REPO, "out", f"GalacticOverlord_Setup_{ver}.exe")
    shutil.move(os.path.join(d, f"GalacticOverlord_Setup_{ver}.exe"), out)
    print(f"{out}: {os.path.getsize(out) / 1e6:.0f} MB, release {ver}, {len(os.listdir(stage))} files")


if __name__ == "__main__":
    main()
