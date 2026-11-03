#!/usr/bin/env python3
"""Generate docs/CODEMAP_FILES.md: every source / data / doc file of the repo with its location, size and a one-line
description taken from the file itself (module docstring, leading comment, first heading, JSON "_comment").
The hand-written overview is docs/CODEMAP.md; this file is the complete per-file list behind it.
Run after adding, moving or renaming files:   python tools/gen_codemap.py        (from the repo root)
                                              python tools/gen_codemap.py --check  (exit 1 when the file is stale)
Skipped: backups (_history, archive, out/_old, *.before_*), build output (out/, unpacked/), caches, _scratch."""
import os, re, sys, json, ast

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT = os.path.join(ROOT, 'docs', 'CODEMAP_FILES.md')
SKIP_DIRS = {'_history', 'archive', 'out', 'unpacked', '_scratch', '__pycache__', '.git', 'archive_patches',
             'netcluster_decompiled', 'extract', 'node_modules'}
SKIP_RE = re.compile(r'\.(before_|bak|pre)|\.orig$|\.old$|~$')
TEXT_EXT = {'.py', '.c', '.h', '.cs', '.ps1', '.bat', '.sh', '.md', '.json', '.txt', '.tsv', '.def', '.ini', '.service',
            '.java', '.manifest'}
# sections in the order the list is written: (title, path prefix)
SECTIONS = [
    ('Repo root', ''),
    ('client/sgrender - SGRender.dll, ddraw.dll proxy, HUD', 'client/'),
    ('server - Python game server', 'server/'),
    ('launcher - SGLauncher / SGPublish / SGRelay (C#)', 'launcher/'),
    ('deploy - deploy / publish scripts, OTA file list', 'deploy/'),
    ('tools - build, patch, data and test tools', 'tools/'),
    ('docs - knowledge base', 'docs/'),
    ('analysis - reverse-engineering output', 'analysis/'),
    ('ghidra_scripts', 'ghidra_scripts/'),
    ('third_party', 'third_party/'),
]


# files that cannot carry their own description (binaries, data) or have none: path or glob -> description
KNOWN = {
    '.gitignore': 'git ignore rules',
    'SG.exe': 'Shattered Galaxy client exe kept in the repo root (reference copy)',
    'deploy/sgalaxy_setup.nsi': 'NSIS script of the full client installer (tools/make_installer.py builds SGalaxy_Setup_<version>.exe)',
    'SG_debug.exe': 'patched debug client: the F-patch tools patch it; deploy.ps1 copies it to the server as the checksum reference',
    'SGalaxy185.exe': 'original Shattered Galaxy 1.8.5 installer',
    'install_pam_fix.bat': 'old manual installer of the fixed pam*.dat (before the launcher)',
    'client/sgrender/SGHud.pak': 'HUD art pack built by tools/make_hud_pack.py (shipped by OTA)',
    'client/sgrender/SGRender.dll': 'built SGRender.dll (build.sh; shipped by OTA)',
    'client/sgrender/ddraw.dll': 'built ddraw.dll proxy that loads SGRender.dll (shipped by OTA)',
    'client/sgrender/ddraw_proxy.def': 'export list of the ddraw.dll proxy',
    'client/sgrender/art/SGHud-advisor.jpg': 'login screen: advisor portrait',
    'client/sgrender/art/SGHud-login.jpg': 'login screen: background',
    'client/sgrender/art/SGHud-insg.png': 'atlas: rank insignia (4 branches x 22 ranks, cells 140 x 44)',
    'client/sgrender/art/SGHud-dcr.png': 'atlas: commander medal ribbons (32 x 30 cells of 44 x 16)',
    'client/sgrender/art/SGHud-brn.png': 'atlas: the four branch pictures INF / MOB / AVI / ORG (34 x 42)',
    'client/sgrender/art/SGHud-hero-*.png': 'commander portraits 01..11 (small, HUD cards and F4)',
    'client/sgrender/art/SGHud-heroport-*.png': 'commander portraits 01..09 (large, new-commander page)',
    'client/sgrender/fonts/SGHud-Cinzel.ttf': 'Cinzel font (numbers, Latin titles in the HUD)',
    'client/sgrender/fonts/OFL-Cinzel.txt': 'Cinzel font licence (SIL OFL)',
    'server/game.db*': 'SQLite store (accounts, world, NPCs) - the production one lives on the server, this is a local copy',
    'tools/gate_layout.json': 'per map: gate (portal) tile layout made by gate_layout.py',
    'tools/i18n_exe.json': 'English -> Chinese strings patched into SG.exe (build_i18n_exe.py)',
    'tools/mptest/fixtures/accounts.base.json': 'test accounts used by the multiplayer tests (mptest)',
    'server/capital_spots.json': 'capital town maps: walk spots and gate doors (NPC commanders wandering)',
    'server/gate_spots.json': 'per planet: gate (portal) positions on the province maps',
    'server/item_stats.json': 'per unit: item stat fields the Lab shows (with field descriptions)',
    'server/map_sizes.json': 'size of every map (tiles)',
    'server/portal_links.json': 'per planet: which province gate leads where',
    'server/unit_slots.json': 'per chassis code: equipment slot ids',
    'server/world.json': 'old world state (owners, politics, power, garrison) - migrated into game.db kv "world"',
    'server/accounts.json.migrated': 'old JSON account store, migrated into game.db',
    'server/npcs.json': 'old NPC state (migrated into game.db kv "npcs")',
    'server/audit.log': 'local audit log (logins, GM, anti-cheat events)',
    'server/client_errors.log': 'local client crash / error reports (packet 0x0A)',
    'server/client_hashes.json': 'extra allowed client code checksums',
    'server/gm_accounts.json': 'GM account names (no passwords)',
    'server/equip.txt': 'per chassis: its equipment slots (slot id, kind, art position)',
    'server/extra_items.json': 'items added on top of the original item list',
    'server/gold_ids.json': 'ids of gold (premium) items',
    'server/item_names_zh.json': 'item names in Chinese (cn / tw)',
    'server/items.json': 'item database (stats, slots, prices) sent as packet 0x10',
    'server/items_guess.json': 'guessed item fields (fallback for items.json)',
    'server/poc_spots.json': 'POC positions per province map',
    'server/spawn_spots.json': 'spawn positions per province map',
    'server/units_manual.json': 'unit chassis stats from the official manual',
    'server/vinu_provinces.tsv': 'province list of vinu.inf (id, planet, map file)',
    'server/walk_grids.json': '32 px walkability grids per map (battlesim / NPC pathing)',
    'launcher/SGLauncher.exe': 'built launcher (stamped with key and URLs by SGPublish when published)',
    'launcher/SGPublish.exe': 'built publish tool (run by deploy/publish.ps1)',
    'launcher/SGRelay.exe': 'built UDP relay',
    'launcher/app.manifest': 'Windows manifest of the launcher (asInvoker, supported OS)',
    'launcher/launcher.res': 'the manifest as a Win32 resource (for mcs builds)',
    'launcher/使用说明.txt': 'player instructions shipped in the launcher zip',
    'tools/f34_build.py': 'assembles the F34 code-challenge stub (keystone) used by patch_sg_debug_f34.py',
    'tools/i18n_ui.json': 'UI text translations used by the i18n dat / exe builders',
    'tools/make_cmdbtn.py': 'builds the CmdBtn.xpf commander buttons from the new portraits',
    'tools/xpf_probe.py': 'helpers: load an .xpf from a .dat and decode its frames',
    'tools/xpf_render.py': 'renders .xpf frames to PNG (sprite sheets for checking art)',
    'tools/mptest/mpclient.py': 'test client: speaks the game protocol (cipher, frames) against a local server',
    'tools/mptest/test*.py': 'offline server test (mpclient against an in-process sgserver)',
    'tools/mptest/sim24.py': 'offline NPC / battle simulation test',
    'tools/ui4/*.py': 'UI art tools of the 2026-10 UI pass (Bink / sprite sheets, measuring, tuning)',
    'docs/NPC_NAMES_ZH.md': 'Chinese names of the NPC commanders',
    'docs/OTA_PUBLISH_LOG.md': 'log of published client releases',
    'analysis/functions.txt': 'Ghidra function list of SG.exe',
    'analysis/imports.txt': 'imports of SG.exe',
    'analysis/strings.txt': 'strings of SG.exe with addresses',
    'analysis/net_callers.txt': 'callers of the client send function',
    'analysis/send_catalog.tsv': 'every client packet send site (type, function)',
    'analysis/unit_tree.tsv': 'unit upgrade tree',
    'analysis/vinu_provinces.tsv': 'provinces of vinu.inf',
    'analysis/handlers/*.c': 'decompiled client packet handlers (file name = address)',
    'analysis/handlers/summary.tsv': 'list of the decompiled packet handlers',
    'analysis/login/*.c': 'decompiled login / register functions',
    'analysis/login/summary.tsv': 'list of the decompiled login functions',
    'analysis/manual/*.json': 'data scraped from the official manual (units, weapons, items)',
    'analysis/marks/*.png': 'game art sheets for marks / badges',
    'analysis/medals/*.png': 'sheet of all medal ribbons',
    'ghidra_scripts/*.java': 'Ghidra script (cross references / scans of SG.exe)',
    'third_party/cnc-ddraw/v7.1.0.0/*': 'cnc-ddraw 7.1 (fallback DirectDraw, OTA ddraw_cnc.dll)',
}
SKIP_PATHS = ('server/backups/', 'server/logs/', 'server/updates/', 'server/run/')


def known(p):
    import fnmatch
    for k in sorted(KNOWN, key=len, reverse=True):
        if p == k or ('*' in k and fnmatch.fnmatch(p, k)):
            return KNOWN[k]
    return ''


def first_sentence(s, n=170):
    s = ' '.join(s.split())
    m = re.match(r'(.{20,}?[.。:：])(\s|$)', s)
    full = s
    s = m.group(1) if m else s
    if s.endswith((':', '：')) or len(s) < 60:        # "sgserver part x:" - the sentence goes on
        s = full
    return s if len(s) <= n else s[:n - 1] + '…'


def describe(path):
    ext = os.path.splitext(path)[1].lower()
    if ext not in TEXT_EXT:
        return ''
    try:
        raw = open(path, 'rb').read(24000)
    except OSError:
        return ''
    for enc in ('utf-8-sig', 'gbk', 'latin-1'):
        try:
            t = raw.decode(enc); break
        except UnicodeDecodeError:
            continue
    if ext == '.py':
        try:
            d = ast.get_docstring(ast.parse(open(path, encoding='utf-8', errors='replace').read()))
            if d:
                return first_sentence(d)
        except (SyntaxError, ValueError):
            pass
        lines = [l.strip('# ').strip() for l in t.splitlines()[:12] if l.startswith('#') and not l.startswith('#!')
                 and 'coding' not in l]
        return first_sentence(' '.join(lines)) if lines else ''
    if ext in ('.c', '.h', '.cs', '.java', '.def'):
        m = re.search(r'/\*(.*?)\*/', t, re.S)
        lead = [l.strip()[2:].strip() for l in t.splitlines()[:15] if l.strip().startswith('//')]
        if lead and (not m or t.find('//') < t.find('/*')):
            return first_sentence(' '.join(lead))
        if m:
            return first_sentence(re.sub(r'^\s*\*+', '', m.group(1), flags=re.M))
        return ''
    if ext in ('.ps1', '.sh', '.bat', '.ini', '.service'):
        lead = []
        for l in t.splitlines()[:20]:
            s = l.strip()
            if s.startswith('#!') or s.lower() in ('@echo off',):
                continue
            if s.startswith('#') or s.lower().startswith('rem ') or s.startswith(';') or s.startswith('::'):
                lead.append(re.sub(r'^(#|rem\s|;|::)\s*', '', s, flags=re.I))
            elif lead:
                break
        return first_sentence(' '.join(lead)) if lead else ''
    if ext == '.md':
        for l in t.splitlines():
            if l.startswith('#'):
                return l.lstrip('#').strip()[:170]
        return ''
    if ext == '.json':
        try:
            j = json.loads(t) if len(raw) < 24000 else None
        except ValueError:
            j = None
        if isinstance(j, dict):
            c = j.get('_comment') or j.get('comment')
            if isinstance(c, str):
                return first_sentence(c)
            return 'keys: ' + ', '.join(list(j)[:8])
        m = re.search(r'"_comment"\s*:\s*"([^"]{10,300})', t)
        return first_sentence(m.group(1)) if m else ''
    return ''


def size(n):
    return f'{n / 1048576:.1f} MB' if n >= 1048576 else f'{n / 1024:.0f} KB' if n >= 1024 else f'{n} B'


def collect():
    rows = []
    for dp, dns, fns in os.walk(ROOT):
        rel = os.path.relpath(dp, ROOT).replace('\\', '/')
        rel = '' if rel == '.' else rel
        dns[:] = sorted(d for d in dns if d not in SKIP_DIRS and not d.startswith('.') and
                        not (rel == '' and d in ('out', 'unpacked', 'archive', '_scratch')))
        if rel == '':
            dns[:] = [d for d in dns if any(p.startswith(d + '/') for _, p in SECTIONS if p)]
        for f in sorted(fns):
            if SKIP_RE.search(f) or f.endswith('.pyc'):
                continue
            p = os.path.join(dp, f)
            rp = (rel + '/' if rel else '') + f
            if rp.startswith(SKIP_PATHS):
                continue
            rows.append((rp, os.path.getsize(p), known(rp) or describe(p)))
    return rows


def render(rows):
    out = ['# CODEMAP_FILES - every file, where it is and what it holds', '',
           'Generated by `python tools/gen_codemap.py` from the files themselves (docstring / leading comment / first heading).',
           'Do not edit by hand: change the description at the top of the file and run the tool again.',
           'The overview (what lives where, which file to open for which job) is [CODEMAP.md](CODEMAP.md).', '']
    done = set()
    for title, pre in SECTIONS:
        sec = [r for r in rows if (r[0].startswith(pre) if pre else '/' not in r[0]) and r[0] not in done]
        if not sec:
            continue
        out += [f'## {title}', '', '| File | Size | Content |', '| --- | --- | --- |']
        for p, n, d in sec:
            done.add(p)
            out.append(f'| `{p}` | {size(n)} | {d.replace("|", "/") or "-"} |')
        out.append('')
    rest = [r for r in rows if r[0] not in done]
    if rest:
        out += ['## Other', '', '| File | Size | Content |', '| --- | --- | --- |']
        out += [f'| `{p}` | {size(n)} | {d.replace("|", "/") or "-"} |' for p, n, d in rest]
        out.append('')
    return '\n'.join(out)


if __name__ == '__main__':
    text = render(collect())
    if '--check' in sys.argv:
        old = open(OUT, encoding='utf-8').read() if os.path.exists(OUT) else ''
        print('CODEMAP_FILES.md', 'up to date' if old == text else 'STALE - run python tools/gen_codemap.py')
        sys.exit(0 if old == text else 1)
    open(OUT, 'w', encoding='utf-8', newline='\n').write(text)
    print(f'{OUT}: {text.count(chr(10) + "| `")} files')
