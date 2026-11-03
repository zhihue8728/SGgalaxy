#!/usr/bin/env python3
"""MPTEST RUNNER (2026-10-24, ARCH_REVIEW B5): every test starts from a CLEAN /tmp/mp - fresh copies of server/*.py and
data, tools/sgproto.py, these tests, fixtures/accounts.base.json as the account table, no game.db (world / NPC state
come from the repo files).  Before, tests ran on a drifted game.db and failed for reasons unrelated to the code.
usage: python3 run_tests.py [test33 test34 ...] [--timeout 120] [--server PATH_TO_OTHER_sgserver.py]
       (no names = every testN.py)   -> table: test, PASS, FAIL, traceback, seconds"""
import glob, os, re, shutil, subprocess, sys, time
HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.normpath(os.path.join(HERE, "..", ".."))
DEST = "/tmp/mp"
SKIP = {"test32": "needs /tmp/f22.exe + /tmp/f23.exe (two client builds)"}

def setup(server_override=None):
    shutil.rmtree(DEST, ignore_errors=True)
    os.makedirs(DEST)
    for f in glob.glob(os.path.join(REPO, "server", "*")):
        b = os.path.basename(f)
        if os.path.isfile(f) and re.search(r"\.(py|json|tsv|txt)$", b) and b not in ("game.db", "accounts.json"):
            shutil.copy(f, DEST)
    if os.path.isdir(os.path.join(REPO, "server", "sgs")):          # the server parts (sgserver.py loads them)
        shutil.copytree(os.path.join(REPO, "server", "sgs"), os.path.join(DEST, "sgs"),
                        ignore=shutil.ignore_patterns("__pycache__"))
    if server_override:
        shutil.copy(server_override, os.path.join(DEST, "sgserver.py"))
    shutil.copy(os.path.join(REPO, "tools", "sgproto.py"), DEST)
    shutil.copy(os.path.join(REPO, "tools", "sgnet.py"), DEST)
    test_net_key()
    for f in glob.glob(os.path.join(HERE, "*.py")):
        shutil.copy(f, DEST)
    base = os.path.join(HERE, "fixtures", "accounts.base.json")
    shutil.copy(base, os.path.join(DEST, "accounts.base.json"))
    shutil.copy(base, os.path.join(DEST, "accounts.json"))

def test_net_key():
    """(2026-11-02) the encrypted connection needs a server key: tests use their own (never the real one, which is only on
    the server and in %USERPROFILE%\\.sgota); the server and mpclient.py find it through SG_NETKEY_FILE"""
    p = os.path.join(DEST, ".netkey_test")
    if not os.path.exists(p):
        sys.path.insert(0, DEST)
        import sgnet
        from cryptography.hazmat.primitives.asymmetric.x25519 import X25519PrivateKey
        open(p, "w").write(sgnet.raw_priv(X25519PrivateKey.generate()).hex())
    os.environ[sgnet_env()] = p
    k = os.path.join(DEST, ".dbkey_test")             # (11-02) game.db rows are encrypted (server/acctstore.py)
    if not os.path.exists(k):
        open(k, "w").write(os.urandom(32).hex())
    os.environ["SG_DBKEY_FILE"] = k
    os.environ["SG_REPO"] = REPO                     # (test120: builds tools/sgcrypt_selftest.c with client/sgrender/sgcrypt.h)

def sgnet_env():
    return "SG_NETKEY_FILE"

def run(name, timeout, server_override=None):
    setup(server_override)
    t = time.time()
    try:
        p = subprocess.run([sys.executable, name + ".py"], cwd=DEST, capture_output=True, text=True, timeout=timeout,
                           errors="replace")
        out = p.stdout + p.stderr
    except subprocess.TimeoutExpired as e:
        out = ((e.stdout or b"").decode("utf-8", "replace") if isinstance(e.stdout, bytes) else (e.stdout or "")) + "\nTIMEOUT"
    fails = [l for l in out.splitlines() if l.startswith("FAIL")]
    return {"pass": sum(1 for l in out.splitlines() if l.startswith("PASS")), "fail": len(fails),
            "tb": out.count("Traceback (most recent call last)"), "timeout": "TIMEOUT" in out,
            "sec": time.time() - t, "fails": fails[:5]}

if __name__ == "__main__":
    args = sys.argv[1:]
    timeout, override = 120, None
    if "--timeout" in args:
        i = args.index("--timeout"); timeout = int(args[i + 1]); del args[i:i + 2]
    if "--server" in args:
        i = args.index("--server"); override = os.path.abspath(args[i + 1]); del args[i:i + 2]
    names = args or sorted((os.path.basename(f)[:-3] for f in glob.glob(os.path.join(HERE, "test*.py"))
                            if re.match(r"test\d+\.py$", os.path.basename(f))), key=lambda n: int(n[4:]))
    for n in names:
        if n in SKIP:
            print(f"{n:8s} SKIP  {SKIP[n]}", flush=True)
            continue
        r = run(n, timeout, override)
        flag = "OK " if r["fail"] == 0 and r["tb"] == 0 and not r["timeout"] and r["pass"] else "BAD"
        print(f"{n:8s} {flag} PASS {r['pass']:3d} FAIL {r['fail']:2d} TB {r['tb']} {'TIMEOUT ' if r['timeout'] else ''}"
              f"{r['sec']:5.0f}s  {' | '.join(r['fails'])[:160]}", flush=True)
