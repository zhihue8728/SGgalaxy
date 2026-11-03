# 多人戰鬥自動測試（模擬客戶端）
在一個暫存資料夾放 server/ 的 .py/.json/.tsv/.txt 與 tools/sgproto.py，再放這些檔案，然後
`python test2.py`（測試會改寫該資料夾的 accounts.json / world.json，請勿在正式 server 資料夾執行）。
需要測試帳號 kkkkkkkk（國家 1）、llllllll（國家 2）：可由 jjjjjjjj 複製（伺服器啟動時會自動修正重複的單位與英雄 uid）。
- test1：同一地圖互相看到、移動轉發
- test2：開戰、加入請求/同意、共用時鐘、命令同 tick 轉發、雙方擊殺與死亡廣播、無 POC 不勝利、佔領勝利、結算
- test3：觀戰、撤退、指揮官斷線後戰鬥繼續、外星怪 AI、觀戰者不結算並回首都
- test4：損失後 F7 增援（0x50 同步給全員）、敵國進入己方省份（觀察）
- test5：有主人的省份——不出現外星怪、通知防守方（0x31）、攻方佔領 POC 勝利、攻方全部撤退則守方勝、時間到守方勝
- test6：客戶端強制斷線（RST）後不再送資料、攻擊任務取消、無 asyncio 警告
- test7：傭兵——非傭兵的請求被拒、傭兵向指揮官申請（0x24 型別 4）、為所服務的一方戰鬥並佔領、獎勵加成、合約結束後還原
每次重跑前把 accounts.base.json 複製回 accounts.json、世界檔 world.json 還原（測試會改省份擁有者）。
- test8：聊天——公開（同地圖）、盟友、私聊、群組、離線提示、GM 指令不外傳
- test9：FHQ 選舉/內政/外交（0x36→0x37，解析方式照客戶端讀取順序）
- test10：總統（/president）、議會名單儲存、/ally 結盟與 0x05 推送
- test11：玩家名冊（0x3c→0x3b、0x3b→0x3a）與名人堂 0x12（解析方式照客戶端讀取順序）
- test12：登入畫面改密碼（0x07 → 02 00 / 02 01），舊密碼錯被拒、新密碼可登入

- test13.py: user info (0x23 -> 0x27 sub 1), Word of Honor (0x55/0x54/0x5c), player search (0x57), resource exchange (0x34).
- test32.py: OTA - version table, old-client notice, /version, release broadcast, min_version block, countdown restart, update HTTP (Range, bandwidth limit). Needs /tmp/f22.exe + /tmp/f23.exe (two client builds).
- test33.py: NPC interception of reinforcements - support squad ambushed on its route (abstract), blockade on a walking player's road (real battle, blockers hostile, defenders win when they are dead), ambushed NPC reinforcement + player of its side (both NPC sides on one map), GM /npc ambush.
- test34.py: NPC doctrine (main / second / capturer kinds, old rosters re-formed, renewal keeps the shape, battle units in blocks of one kind) and F7-like NPC squads (half a squad left -> next squad after the cooldown, until the reserve is empty).
- test35.py: NPC battles are always REAL (server-simulated ghost battles, battlesim.py): neutral assault with aliens (units walk on the walk grid, fight, capture POCs, result), a player joins (every unit where the simulation has it), leaves (simulation goes on), owned province with NPC defenders, a hunt never captures, NPC-vs-NPC ambush.  test20/23/28/33 were updated: no abstract sieges / raid windows any more.
- sim_npc3.py HOURS: NPC world with real battles (10-s ticks, dt=10 s steps).  Needs walk_grids.json + battlesim.py in /tmp/mp.
- test36.py: NPCs shown in a province on the strategic map stand on its town map; BATTLE INFO (0x1e) lists NPC commanders + Aliens.
- lag_probe.py HOURS: times the NPC tick parts and the simulated battle steps (event-loop stalls).
- test37.py: NPC commanders follow the player rules (novice: no reincarnation, branch <= 35, deploy Tactics//20+6; kinds within influence; unit levels <= branch+3).
- test38.py: simulated NPC battles step in worker processes; max game-loop stall measured (in the loop vs workers), results applied.
- test39.py: network latency - battle frames every FRAME_MS (50 ms, drift-free), frames skipped behind a stalled link, socket tuning (NODELAY / keep-alive), TCP_INFO stats, GM /lag net.
- test40.py: adaptive battle frame interval (congested -> 100 ms, retransmits / rtt variance -> 33 ms, quiet -> 50 ms, hysteresis, /lag adapt).
test41 - GM /amove /aatk (walking animation A/B test lumps)
- test42.py: NPC aggression / cooperation (rally, join capped campaigns)
- test43.py: carry weight follows the account Mech (mech_for)
- test44.py: allied NPCs that answer a call for help enter the running battle (enemy defenders do not use their slots; full battle -> short wait, they say so and go home)
- test45.py: NPC_RT entries without a nation no longer crash the end check; NPCs that get no unit onto the map go home; one bad tick does not stop the battle loop
- test73.py: BOARD + SGMAIL web pages parsed with the client's own strstr cutter (see docs/BOARD_MAIL.md)
- test46.py: battle-control dialog 0x1e lists NPC commanders and the alien garrison with valid nation ids (parsed like 004af1e0); NPC commanders without units leave the battle

## 一鍵執行（2026-10-24）：`python3 run_tests.py [testN ...] [--timeout 120] [--server 其他版本的 sgserver.py]`
- 每個測試開始前都會重建乾淨的 /tmp/mp：從 repo 複製 server/*.py 與資料、tools/sgproto.py、本資料夾的測試，帳號表用 `fixtures/accounts.base.json`（含 jjjjjjjj / kkkkkkkk 國 1 / llllllll 國 2），不放 game.db。
- 以前測試共用一個越跑越亂的 game.db，常因狀態漂移而失敗，跟程式碼無關。
- 對照新舊版本：先複製一份舊版 repo（或用 `--server` 指定舊的 sgserver.py），兩邊跑同一批測試，比較每列的 PASS / FAIL。
- 注意：每次執行工具呼叫只能跑約 3 分鐘，請分批，例如一次 4–8 個。

### 2026-10-24 基準
- **通過（回歸測試集）**：test17 18 19 21 22 23 25 26 27 29 30 33 34 36 37 38 39 40 41 42 43。
- **已過時，要改測試本身**（遊戲規則已變：NPC 國家、國別編號、中文訊息、己方 NPC 在玩家加入時撤出等）：
  - test1–16；
  - test20：防守 NPC 改成「巡邊」；
  - test24：出擊冷卻；
  - test28：玩家加入時己方 NPC 會撤出，見伺服器日誌「client cannot show NPC allies」；
  - test31：外部編輯重載的路徑；
  - test35：第 92 行 task 為 None，另有一隻幼蟲站在不可走格。
- **跳過**：test32（需要兩個客戶端 exe）。
- test28 順帶抓到一個真的錯誤：enter_field 裡多了一行 `import time`，讓整個函式的 time 變成區域變數，玩家進場遇到己方 NPC 時會 UnboundLocalError。已修正。
- test82.py: aliens walk (0x1A move, walk animation) to a target out of range before the 0x2B attack; re-aim; re-chase when the target runs (ALIEN_APPROACH, claude/ALIEN_WALK_ANIM.md).
- test83.py: an NPC unit attacking a target that walks out of range (snapshot position) walks after it (0x1A) instead of the F6 attack-state slide.
- test84.py: battle-flow rules - 0x2B only built in sgs/unit_orders.py, both AIs leave through dispatch_orders, attack guard (raw far 0x2B -> walk), one chase rule for aliens and NPC units.
- test85.py: i18n - every English message template of the server code has a Chinese translation (CATALOG) unless allow-listed as internal; recursive translation of inner reasons; untranslated lines for Chinese clients are recorded (logs/i18n_missing.log).
- test86.py: NPC aggression 2 - idle NPCs reinforce comrades already fighting, border patrols strike next door, patrols last resort.
- test87.py: NPC aircraft - aviation branch for most NPCs, an air platoon in every roster that can field aircraft, fielded in battle.
- test88.py: idle NPCs join running surface battles of their side first (defence / assist), hunts rare.
- test89.py: NPC enclaves - the province between an own enclave and the home land (bridge) is attacked first, from the enclave.
- test90.py: PUT max/current HP for wounded units; blockades are real battles at once; NPCs walk home only over own land.
- test91.py: NPC helpers come without a call (by how the side is doing), a call hurries helpers on the way and new ones march faster.
- test92.py: an NPC released in a province its side lost falls back to the nearest own province next door and holds it (not the capital).
- test93.py: the owner's defender NPCs entering a player's attack do not turn the owner's POC into "raiders captured every POC".
- test94.py: client F47 - late-command report 0xF9, client freeze report 0xFA (frame gap >= 150 ms), smooth push-back (5 ticks at once, the rest 1 tick / 2 frames from the F46 frame stub), bigger clock buffer bytes (x86 emulation); server sums the reports.
- test95.py: sgs/unit_hp.py - one HP rule: roster in equipment units, battle full with bonus, wound share kept, 0x21 kind 2 ignored, repair, dead stays dead.
- test96.py: one logic per mechanism - prices (list = charge, sale = half), res_pay / res_add, capture_province (old side told, ally rule), notify_side, hit formula, walk time, battle_units.
- test97.py: delayed_put - the one 0x50 path: sent after the wait, stamped game_time(receiver) + RELAY_DELAY (a 3 s-ahead stamp made the client clock jump -> rollback storm), cancelled when the unit / battle is gone.
- test98.py: client F48 - SGRender.dll hooks (x86 emulation of the release exe): loader (LoadLibrary/GetProcAddress/SGR_Init once, no DLL = no change), EndFrame 004c4a60 call-out (0 = original present, 1 = DLL drew the frame), CWnd::Create call-out (registers kept); the DLL exports SGR_Init and the OTA list ships it.
- test99.py: client F49 widescreen (x86 emulation of the release exe): without the DLL every stub = the original 800 x 600; with W 1060 the frame / CreateWindow / SetDisplayMode are W wide, SetViewport moves every viewport DX right (its own body runs), the mouse is clamped to W-1 and moved back by DX, the whole-screen clip rects are -DX..800+DX (flags kept), TC Main / Field clip their children and take hit tests over the whole frame, quick menu / terrain / right unit cards are 800+DX based, fog draw + visibility go to the DLL, the cursor clip is widened.
- test100.py: phase 2 own display layer - the ddraw.dll proxy (exports, fallback order SGRender -> ddraw_cnc.dll -> system), SGRender.dll exports SGR_DirectDrawCreate and imports neither ddraw nor d3d9 (d3d9 loaded at run time), OTA ships proxy + cnc-ddraw as ddraw_cnc.dll.
- test101.py: phase 3 battlefield HUD (sghud.c) - sources + build, sghud_units.h (unit name -> branch, EN/CN/TW) up to date with the server data (tools/gen_sghud_units.py --check), SGRender.dll contains the HUD and loads GDI+ at run time, OTA ships the Cinzel font (+ OFL licence), radar / enemy count only where the fog is clear, old panel hidden only while the HUD is active, [hud] enable switch, painting on its own thread.
- test102.py: client F50 (x86 emulation): the four pixel-pick routines read the mouse x + DX (W 0 / 900 / 1060); the crash case (mouse -44,0 in 800-space, viewport 0,0) now indexes inside the canvas.
- test103.py: client F51 (x86 emulation + DLL source): terrain rows (MH+63)/32, the 4 MapWnd re-sizes of the quick menu / strategic map slides push MH, wreck rows +0x16; the DLL creates MapWnd MH high (600 with the HUD), fog rows (MH+32)/8+3, floating HUD panels.
- test105.py: NPCs follow the battlefield rule - never placed in another nation's province without a battle there (npc_may_stand): marchers / walkers whose next step changed hands re-route over own land or call the march off; 3 h of ticks without a violation.
- test104.py: client F52 (x86 emulation + DLL source): 004a4a50 calls TABLE+0x38 qm_slide(field) when the DLL set it (else the original code); the DLL keeps the map full width and slides the quick menu by its own x.
- test106.py: login screen design A (SGRender.dll HUD): main menu / CONTINUE / CREATE ID / CHANGE PASSWORD forms, briefing room (war records), select commander (portraits copied out of the frame, stats, points), select nation (the game's live viewer shown through the overlay, tabs, friend ID), the advisor's OK; the mouse sent to the game's own controls; intro movies not opened (BinkOpen import hook), logo / server-select fly-in skipped ([hud] skip_intro); the art ships through OTA.
- test107.py: capital alarm - an enemy holds a province next to a nation's capital: for 12 h up to 30 NPCs (roster grows), decisions twice as often, worse odds accepted, never stays home, no pause after a conquest, the enemy land next to the capital first; a new alarm while still threatened, back to 20 when it is gone.
- test108.py: no min_win gate (every persona accepts a hopeless target, the score only drops); a damaged NPC goes home after its task (no fallback post) and is repaired at once at the capital's factory (not on the road); idle reasons logged every 10 min.
- test109.py: NPC teamwork - pincer from other own provinces next to the target (own groups / gates, arriving together, ally-channel call + answers); 4 helpers per call, weaker side calls; battle brain: least defended POC next to own ground, losing with POCs / help coming digs in (defend) instead of falling back.
