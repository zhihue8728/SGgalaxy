"""test85 (user 2026-10-27 "still many English messages in the game - make sure they are Chinese"): every English
message template in the server code (literal / f-string, outside log / audit / GM commands / functions with their own
Chinese branch) must have a translation in server/i18n.py CATALOG.  A NEW untranslated message fails this test: add
its (English, 繁體, 简体) entry to CATALOG - or, for an internal string that never reaches a player, to ALLOW below.
Also: an untranslated system line for a Chinese client is recorded (I18N.MISSING / logs/i18n_missing.log)."""
import os, sys
os.chdir('/tmp/mp'); sys.path.insert(0, '/tmp/mp')
import i18n as I
def chk(n, ok, i=''): print(('PASS ' if ok else 'FAIL ') + n, i, flush=True)
import ast, glob, os, re
SKIP_FILES = {'battlefield.py', 'board_mail.py', 'core_net.py', 'client_ota.py', 'battle_ai.py'}
SKIP_CALLS = {'log', 'clog', 'audit', 'print', 'chk', 'debug', 'warn', 'Exception', 'ValueError', 'RuntimeError',
              'SystemExit', 'KeyError', 'AssertionError', '_say_lang', 'npc_say', 'format_exc'}
GM_FUNCS = {'gm_command', 'npc_gm'}
def tmpl(n):
    if isinstance(n, ast.Constant) and isinstance(n.value, str):
        return n.value
    if isinstance(n, ast.JoinedStr):
        return ''.join(str(v.value) if isinstance(v, ast.Constant) else '{}' for v in n.values)
def english(t):
    t2 = t.replace('{}', 'X')
    if re.search(r'[一-鿿]', t2) or not re.search(r'[a-z]', t2):
        return False
    if len(re.findall(r'[A-Za-z]{2,}', t2)) < 2 or len(t2.split()) < 2:
        return False
    return True
def scan(root, I):
    out = {}
    files = glob.glob(os.path.join(root, 'sgs', '*.py')) + [os.path.join(root, x) for x in ('aliens.py', 'npc.py')]
    for f in sorted(files):
        if not os.path.exists(f) or os.path.basename(f) in SKIP_FILES:
            continue
        src = open(f, encoding='utf-8').read(); L = src.split('\n'); tree = ast.parse(src)
        parent = {}
        for n in ast.walk(tree):
            for c in ast.iter_child_nodes(n):
                parent[c] = n
        funcs = [n for n in ast.walk(tree) if isinstance(n, ast.FunctionDef)]
        for n in ast.walk(tree):
            t = tmpl(n)
            if t is None or isinstance(parent.get(n), (ast.JoinedStr, ast.Expr)) or not english(t):
                continue
            q, skip = n, False
            while q in parent:
                q = parent[q]
                if isinstance(q, ast.Call):
                    fn = q.func.attr if isinstance(q.func, ast.Attribute) else getattr(q.func, 'id', '')
                    if fn in SKIP_CALLS:
                        skip = True; break
                if isinstance(q, (ast.Assert, ast.Raise)):
                    skip = True; break
            if skip:
                continue
            fd = [d for d in funcs if d.lineno <= n.lineno <= d.end_lineno]
            if not fd:
                continue                                    # module-level data tables (names, item data)
            fd = max(fd, key=lambda d: d.lineno)
            if fd.name in GM_FUNCS or any(re.search(r'[一-鿿]', L[i]) for i in range(fd.lineno - 1, fd.end_lineno)):
                continue                                    # GM-only, or a function with its own Chinese branch
            sample = t
            i = 0
            while '{}' in sample:
                sample = sample.replace('{}', f'Q{i}Z', 1); i += 1
            if I.translate(sample, 'zh-cn') != sample:
                continue
            out.setdefault(t, f'{os.path.basename(f)}:{n.lineno} [{fd.name}]')
    return out

ALLOW = set([
"  (outranks you - not usable)",
" (not open)",
"/mail  |  /mail N  |  /mail del N",
"Acid Bura",
"Air Bombard",
"Air Cooldown",
"Air Damage",
"Air Range",
"Energy Drain",
"Energy Recharge",
"Energy Use",
"Fusion Storm",
"Grenade splash",
"Ground Cooldown",
"Ground Damage",
"Ground Range",
"HP 0 in the client",
"Hive Nest",
"Max Complexity",
"Max Energy",
"Range Bonus",
"Self Destruct",
"TK: {} -> {} refused (both players need TK on)",
"Tech Level",
"This design was refused by the server: ",
"Upgraded {}s have NO WEAPON - equip one in EQUIP ITEM.",
"View Range",
"Virus infection",
"Virus kill",
"XP Bonus",
"alien AI",
"alien raid",
"blockade / interception",
"both biological and mechanical",
"commander {} left",
"decreases the cooldown",
"defence: win by time",
"fight back",
"gone from the client",
"heal injured biological",
"help is marching to this battle",
"mark an enemy unit to explode",
"model hp {} left, team can deal {} in {}s",
"nation {} is not the reporter's side {}",
"never hit by any unit (server model)",
"no engine",
"no items",
"no units",
"not on sale",
"not replenish",
"order 0x{} for alien {}",
"order 0x{} for unit {} of {}",
"own side",
"repair damaged mechanical",
"reward {} -> resources {}",
"server saw {}s of capture by {}, needs {}s",
"tech level > {}",
"unit {} has no skill for action {} (bit {})",
"{} has TP off (units not transportable by allies)",
"{} is an allied nation (allies never attack each other)",
"{} removed (no slot / too heavy), sold for half price. ",
"{} {} (you have {})"
])
miss = scan('/tmp/mp', I)
new = {k: v for k, v in miss.items() if k not in ALLOW}
chk('every player message template has a Chinese translation (i18n.py CATALOG)', not new,
    '\n' + '\n'.join(f'   {v}  {k!r}' for k, v in sorted(new.items(), key=lambda kv: kv[1])))
for t in ("This design was refused by the server: weight 120/100.", "Switching faction costs 50 Uranium.",
          "The alien raid on X-1 was repelled!"):
    out = I.translate(t, 'zh-cn')
    chk(f'translated: {t[:40]}', out != t and not I.looks_english(out), out)
I.MISSING.clear()
r = I.translate_checked('Some brand new untranslated words', 'zh-tw')
chk('an untranslated line for a Chinese client is recorded', 'Some brand new untranslated words' in I.MISSING)
I.MISSING.clear()
I.translate_checked('Some brand new untranslated words', 'en')
chk('English clients are not recorded (MISS_ALL off)', I.MISS_ALL or not I.MISSING)
