#!/usr/bin/env python3
"""pyflakes over the whole server as ONE namespace (sgserver.py loads server/sgs/*.py into a single module, so a part
alone shows false 'undefined name' warnings).  Concatenates the parts in PARTS order, runs pyflakes, maps every
warning back to part:line.  usage: python tools/check_server.py [--all]   (--all: also unused variables etc.)"""
import os, re, subprocess, sys, tempfile
SRV = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "server")
src = open(os.path.join(SRV, "sgserver.py"), encoding="utf-8").read()
names = re.findall(r'"(\w+)"', re.search(r"PARTS = \((.*?)\)", src, re.S).group(1))
lines, where = [], []
for n in names:
    for k, l in enumerate(open(os.path.join(SRV, "sgs", n + ".py"), encoding="utf-8").read().split("\n")):
        lines.append(l); where.append((f"sgs/{n}.py", k + 1))
tail = src.split("\n")
for k, l in enumerate(tail):
    lines.append(l); where.append(("sgserver.py", k + 1))
with tempfile.NamedTemporaryFile("w", suffix=".py", delete=False, encoding="utf-8") as f:
    f.write("\n".join(lines)); tmp = f.name
out = subprocess.run([sys.executable, "-m", "pyflakes", tmp], capture_output=True, text=True).stdout
os.unlink(tmp)
quiet = ("assigned to but never used", "f-string is missing placeholders", "redefinition of unused", "imported but unused",
         "unable to detect undefined names")
bad = 0
for ln in out.splitlines():
    m = re.match(r".*?:(\d+):(\d+):? (.*)", ln)
    if not m:
        continue
    msg = m.group(3)
    if "--all" not in sys.argv and any(q in msg for q in quiet):
        continue
    f_, k = where[int(m.group(1)) - 1]
    print(f"{f_}:{k}: {msg}"); bad += 1
print("check_server:", "OK" if not bad else f"{bad} problem(s)")
sys.exit(1 if bad else 0)
