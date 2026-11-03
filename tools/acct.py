#!/usr/bin/env python3
"""Player account management for the SGalaxy server (server/game.db; works while the server runs - it reloads changes).

  python tools/acct.py list [TEXT]              all accounts (optionally filtered by name/e-mail)
  python tools/acct.py show NAME                full summary of one account
  python tools/acct.py create NAME PASSWORD [--gm]   new account (nation 1 commander); --gm also makes it a GM
  python tools/acct.py gm NAME on|off           add / remove NAME in server/gm_accounts.json
  python tools/acct.py paid NAME on|off         mark an account as paid / free
  python tools/acct.py give NAME money|ore|silicon|ura|sulfur N   add (or subtract) resources
  python tools/acct.py setpw NAME PASSWORD      change a password (stored as a salted hash)
  python tools/acct.py hashpw-all               convert every old plain-text password to a hash
  python tools/acct.py export [FILE]            CSV of all accounts
  python tools/acct.py delete NAME              delete an account (asks to type the name again)
  python tools/acct.py backup                   consistent copy of game.db -> game.db.YYYYmmdd-HHMMSS
  Environment SG_DB = other database file."""
import csv, json, os, sys, time

SERVER = os.environ.get("SG_SERVER_DIR") or os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "server")
sys.path.insert(0, SERVER)
import acctstore as STORE  # noqa: E402

DB = os.environ.get("SG_DB") or os.path.join(SERVER, "game.db")
GM = os.path.join(SERVER, "gm_accounts.json")
RES = {"money": 0, "ore": 1, "silicon": 2, "ura": 3, "uranium": 3, "sulfur": 4}
START_RESOURCES = [5000, 500, 500, 100, 100]


def regiment_of(name, regs):
    return next((n for n, r in regs.items() if name in r.get("members", [])), "")


def row(name, a, regs):
    c = a.get("commander", {})
    lv = max([v.get("level", 1) for v in (c.get("branches") or {}).values()] or [1])
    res = a.get("resources", [])
    return [name, a.get("nick", ""), a.get("email", ""), "paid" if a.get("paid") else "free", c.get("nation", ""),
            c.get("tier", ""), lv, c.get("reincarnations", 0), c.get("honor", 0) // 100, len(a.get("units", [])),
            res[3] if len(res) > 3 else "", regiment_of(name, regs)]


HEAD = ["account", "nick", "email", "type", "nation", "tier", "top level", "reinc", "honor", "units", "ura", "regiment"]


def find(accs, name):
    k = next((n for n in accs if n.lower() == name.lower()), None)
    if k is None:
        sys.exit(f"no such account: {name}")
    return k


PW_MAX = 8      # the game's login box takes at most 8 characters


def check_pw(pw):
    if not 1 <= len(pw) <= PW_MAX:
        sys.exit(f"password must be 1-{PW_MAX} characters (the game's login box takes at most {PW_MAX})")


def set_gm(name, on):
    try:
        gms = json.load(open(GM, encoding="utf-8"))
    except Exception:
        gms = []
    gms = [g for g in gms if g.lower() != name.lower()] + ([name] if on else [])
    with open(GM, "w", encoding="utf-8") as f:
        json.dump(gms, f)
    print("GM list:", gms)


def main(argv):
    if not argv:
        print(__doc__); return
    c = STORE.connect(DB)
    STORE.migrate_json(c, os.path.join(SERVER, "accounts.json"))
    accs = STORE.load_all(c)
    regs = STORE.kv_get(c, "regiments") or {}
    cmd = argv[0]

    def save(*names):
        STORE.write(c, {n: json.dumps(accs[n], separators=(",", ":")) for n in names}, [])

    if cmd == "list":
        q = argv[1].lower() if len(argv) > 1 else ""
        rows = [row(n, a, regs) for n, a in accs.items() if q in (n + a.get("email", "") + a.get("nick", "")).lower()]
        print("\t".join(HEAD))
        for r in rows:
            print("\t".join(str(x) for x in r))
        print(f"{len(rows)} account(s)")
    elif cmd == "show":
        n = find(accs, argv[1]); a = accs[n]; cmd_ = a.get("commander", {})
        for k, v in zip(HEAD, row(n, a, regs)):
            print(f"{k:10}: {v}")
        print("password  :", "hash" if a.get("pw") else ("PLAIN TEXT" if "password" in a else "none"))
        print("resources :", a.get("resources"))
        print("attrs     :", cmd_.get("attrs"), "points", cmd_.get("points"))
        print("branches  :", {k: v.get("level") for k, v in (cmd_.get("branches") or {}).items()})
        print("units     :", [(u.get("uid"), u.get("chassis"), u.get("level", 1)) for u in a.get("units", [])])
    elif cmd == "create":
        name, pw = argv[1], argv[2]
        check_pw(pw)
        if any(n.lower() == name.lower() for n in accs):
            sys.exit(f"account {name} already exists")
        a = {"email": "", "units": [], "resources": list(START_RESOURCES),
             "commander": {"nation": 1, "look": 1, "attrs": [0, 0, 0, 0]}}
        STORE.pw_set(a, pw)
        accs[name] = a; save(name)
        print("created", name)
        if "--gm" in argv:
            set_gm(name, True)
    elif cmd == "gm":
        set_gm(find(accs, argv[1]), argv[2].lower() == "on")
    elif cmd == "paid":
        n = find(accs, argv[1]); accs[n]["paid"] = argv[2].lower() == "on"; save(n); print("ok")
    elif cmd == "give":
        n = find(accs, argv[1]); a = accs[n]
        a.setdefault("resources", list(START_RESOURCES))[RES[argv[2].lower()]] += int(argv[3]); save(n)
        print("resources now", a["resources"])
    elif cmd == "setpw":
        check_pw(argv[2]); n = find(accs, argv[1]); STORE.pw_set(accs[n], argv[2]); save(n); print("password changed for", n)
    elif cmd == "hashpw-all":
        ch = [n for n, a in accs.items() if "password" in a and not a.get("pw")]
        for n in ch:
            STORE.pw_set(accs[n], str(accs[n]["password"]))
        save(*ch); print(f"{len(ch)} password(s) hashed")
    elif cmd == "export":
        out = argv[1] if len(argv) > 1 else "accounts.csv"
        with open(out, "w", newline="", encoding="utf-8-sig") as f:
            w = csv.writer(f); w.writerow(HEAD)
            for n, a in accs.items():
                w.writerow(row(n, a, regs))
        print("wrote", out)
    elif cmd == "delete":
        n = find(accs, argv[1])
        if "--yes" not in argv and input(f"type {n} again to delete it: ").strip() != n:
            sys.exit("not deleted")
        STORE.write(c, {}, [n]); print("deleted", n)
    elif cmd == "backup":
        dst = DB + "." + time.strftime("%Y%m%d-%H%M%S"); STORE.backup_to(c, dst); print("wrote", dst)
    else:
        print(__doc__)


if __name__ == "__main__":
    main(sys.argv[1:])
