"""test117 (user 2026-10-31 17:14 "person and portrait differ" / "commander info HUD", plan confirmed 17:31):
A. 0x15 commander packet byte [0x450] (client: portrait Hero-%02d.xpf) = the commander's look (body art H<look>);
B. /b/c/honor/cmd.txt: I / B / A / R / U / N / L / M lines for the HUD's F4 page."""
import sys, os, time
os.chdir('/tmp/mp'); sys.path.insert(0, '/tmp/mp')
import sgserver as S
import progression as PG
S.LOG = open('/tmp/mp/server117.log', 'w', encoding='utf-8')
def chk(n, ok, i=''): print(('PASS ' if ok else 'FAIL ') + n, i, flush=True)
accs = S.load_accounts(); key = next(iter(accs)); a = accs[key]
cmd = PG.ensure_commander(a.setdefault("commander", {}))
cmd["look"] = 7; cmd["attrs"] = [12, 5, 9, 3]; cmd["points"] = 4
cmd["unit_hall"] = {"1": {"name": "Ace", "chassis": "Hawk", "star": 3, "kills": 120, "bt": 10, "bw": 7, "marks": []},
                    "2": {"name": "Bob", "chassis": "Imp", "star": 1, "kills": 5, "bt": 2, "bw": 1, "marks": []}}
a["last_report"] = {"id": 1, "t": time.time() - 30, "res": 1, "map": 600003, "units": [], "cmd": {"honor0": 100, "honor": 350}}
S.save_accounts(accs)
S.BOARD_REQUIRE_ONLINE = False
pk = S.build_commander(key, cmd.get("nation", 1))
chk('A1 0x15 [0x450] = look 7', pk[13] == 7, pk[:16].hex())
st, body = S.board_http("GET", "c/honor/cmd.txt", "acc=" + key, b"", "127.0.0.1")
L = [l.split("\t") for l in body.decode("gbk").split("\n") if l]
by = {}
for l in L: by.setdefault(l[0], []).append(l)
chk('B1 I line: name, title, nation, honor, look', "I" in by and len(by["I"][0]) == 16 and by["I"][0][11] == "7", by.get("I"))
chk('B2 four branch lines with rank and the next rank', len(by.get("B", [])) == 4 and all(len(l) == 9 and l[7] for l in by["B"]), by.get("B"))
chk('B3 attributes + points', by.get("A") == [["A", "12", "5", "9", "3", "4"]], by.get("A"))
chk('B4 resources', "R" in by and len(by["R"][0]) == 6, by.get("R"))
chk('B5 units: best star unit, lifetime kills, battles', "U" in by and by["U"][0][4] == "3" and by["U"][0][5] == "Ace" and by["U"][0][6] == "125" and by["U"][0][7] == "12", by.get("U"))
chk('B6 nation line', "N" in by and len(by["N"][0]) == 3, by.get("N"))
chk('B7 last battle: victory, honor +250', "L" in by and by["L"][0][1] == "1" and by["L"][0][3] == "250", by.get("L"))
