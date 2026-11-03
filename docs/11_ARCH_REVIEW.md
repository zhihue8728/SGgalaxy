# 代碼架構評估（2026-10-24）：簡潔與延遲

所有數字都是這次實際量到的。

## 一、現況

### 規模
- 伺服器程式共 16,535 行，其中 `sgserver.py` 佔 13,637 行，約 610 個函式。
- 已拆成獨立模組的：`battle_ai.py`（641）、`battlesim.py`（434）、`npc.py`（333）、`battlefield.py`（191）、`aliens.py`、`progression.py`、`acctstore.py` 等。

### 最大的函式
| 函式 | 行數 |
|---|---|
| `handle_packet` | 952（57 個 `elif t == 0x..` 分支） |
| `gm_command` | 358 |
| `enter_field` | 294 |
| `npc_ai` | 254 |
| `alien_ai` | 241 |
| `brain_npc_step` | 129 |

### 狀態沒有結構
- 玩家連線物件上有 114 種臨時欄位，`getattr(s, "...", 預設值)` 出現 528 次。
- 戰場字典 B 有 27 種鍵。

### 重複
- **單位決策有三套**：
  - 真人戰鬥：battle_ai；
  - 舊的逐單位 NPC AI：129 行，只在 battle_ai 出錯時才用；
  - 伺服器模擬戰鬥：battlesim 自己的選目標邏輯。
  - 「地面單位不追飛機」「自走砲」「隱形」這幾個修正都得在三處各改一次。
- **外星怪與 NPC 各跑一個每秒迴圈**（alien_ai、npc_ai），各自建一次戰場視角（位置、隱形、偵測器）。
- **重複的寫法**：
  - 三語字串直接寫在程式裡 21 處，`_say_lang` / `_notify_side` 17 處；
  - `json.load(open(os.path.join(...)))` 12 處；
  - `asyncio.get_event_loop().create_task(...)` 43 處；
  - 函式內部的 import 48 處；`except Exception:` 83 處。
- **已經不用的開關**：`ALIEN_CLIENT_CONTROL=False`、`SNAPSHOT_RELAY=False`、`NPC_GHOST_BATTLES=True`（舊的抽象攻城與突襲窗口），它們的分支仍留在程式裡。
- **`server/_history`**：248 個備份檔、83 MB，放在專案資料夾，沒有 .gitignore。部署時已排除。

### 伺服器端耗時（實測）
| 項目 | 結果 |
|---|---|
| NPC 世界運算（模擬 0.5 小時） | npc_tick 最壞 19 ms；伺服器模擬戰鬥一步最壞 41 ms（正式環境在子行程跑）；npc_save 16 ms（背景執行緒） |
| 戰鬥 AI 每秒一次 | 12 對 12：2.2 ms；36 對 36：10.4 ms；60 對 60：22 ms |
| 正式日誌 | 每 65 秒卡 110–160 ms：已在本機修好（客戶端 exe 校驗碼改成快取），伺服器還沒部署 |
| 正式日誌 | 06:21 一次 GC 暫停 114 ms（第 1 代） |
| 帳號存檔、NPC 存檔、OTA 雜湊 | 已在背景執行緒，不擋主迴圈 |

### 玩家感受到的延遲（主要不在伺服器 CPU）
- 測得 RTT 218 ± 23 ms。
- 鎖步指令延後：`RELAY_DELAY` 固定 10 tick = 100 ms，echo 封包也寫死 `game_time + 10`。
- 從點擊到單位開始動 ≈ RTT + 100 ms ≈ 320 ms，其中伺服器運算不到 5 ms。

## 二、建議（依「效果 ÷ 風險」排序）

### A. 降低延遲
1. **【效果最大】換到離玩家近的機房**：例如香港，或華東、華南的 BGP / CN2 線路。
   - RTT 預計從 220 ms 降到 30–60 ms，每個動作快 160 ms 以上，程式不用改。
   - 先在候選機房用 `ping` 或 `tcping` 量 RTT 再決定。
2. **【程式可做】縮短鎖步指令延後 RELAY_DELAY**（100 ms → 20–30 ms，每個動作省 70–80 ms）。
   - 依據：客戶端的時鐘只會推進到「收到的最後一個 0x80 幀的時間」。指令和幀走同一條 TCP 連線、依序到達，所以客戶端不可能在收到指令前就越過指令的執行時間。伺服器送幀時不加提前量，所以延後量理論上可以很小。
   - 做法：
     - 把三處寫死的 `game_time + 10` 統一改成 `RELAY_DELAY`；
     - 加 GM 指令 `/lag delay N`，在真人戰鬥裡從 10 往下試到 3；
     - 確認不失步、技能時機正常後，改成依 RTT 自動調整。
   - 風險：客戶端如何處理「執行時間已經過去」的指令還沒驗證過，所以要先用 GM 開關實測。
3. **GC 暫停**：
   - 目前已做 `gc.freeze` 和門檻 (20000, 20, 50)。
   - 再加：在 lag_monitor 記錄每次 GC 的世代與耗時（已有 GC pause 日誌）；在戰鬥空檔（每 10 秒的 NPC tick 後）主動 `gc.collect(1)`，避免在戰鬥中觸發。
4. **戰場只跑一個迴圈**（同時屬於 B-2）：
   - 現在每場戰鬥有 alien_ai（1 秒）、npc_ai（1 秒）、poc_loop（0.5 秒）、battle_timer，加上全域的快照迴圈（0.5 秒）。
   - 合成一個 `battle_loop(B)`（2 Hz）：每次只建一份戰場視角，依序做 POC → AI → 快照 → 勝負判定。
   - CPU 減半，每場戰鬥的事件順序也變得固定。
5. **熱路徑日誌**：
   - 每次命中的 `hit:`、每個 lump 的 `lump msg` / `echoed` 在大戰鬥裡每秒上百行，CPU 成本不大，但日誌檔很大，查問題也慢。
   - 改成 debug 等級，預設關閉，`/lag pkt` 打開。

### B. 簡潔
1. **一套單位決策**：
   - 刪掉舊的逐單位 NPC AI（129 行）；battle_ai 出錯時改成「這一秒不下新命令」。
   - battlesim 的選目標也改用 battle_ai（它已經有 `ctx.brain`）。
   - 外星怪全部交給 battle_ai 的 alien 模式。
   - 之後規則只要改一次。預估減少 300–400 行。
2. **戰場控制器**：
   - 把 B 字典與戰鬥中的連線欄位整理成 `Battle` / `Fighter` 資料類別（dataclass，欄位有名稱和預設值），取代大量的 `getattr(s, "...", 預設)`。
   - 戰鬥流程（開戰、加入、單位死亡、POC、計時、結束）集中到 `battlefield.py` 旁的 `battle_runtime.py`。
3. **拆分 sgserver.py**（只搬移程式，不改行為）：
   | 新檔案 | 內容 | 約多少行 |
   |---|---|---|
   | `net.py` | Session、封包、延遲 | 600 |
   | `items_lab.py` | 物品、研究所、裝備 | 1,200 |
   | `social.py` | 聊天、軍團、FHQ、信箱 | 1,500 |
   | `npc_world.py` | NPC 國家、任務、外交 | 4,000 |
   | `gm.py` | GM 指令 | 500 |
   | `handlers.py` | 封包分派表 | — |
   - `handle_packet` 改成 `HANDLERS = {0x2a: on_chat, ...}` 分派表，每種封包一個小函式。
4. **小清理**：
   - 三語字串集中到 `i18n.py` 的表（`T("giveup", lang, prov=...)`）；
   - `data_json(name)` 取代 12 處讀檔；`spawn(coro)` 取代 43 處 create_task；
   - 移除已經不用的開關分支（ALIEN_CLIENT_CONTROL、SNAPSHOT_RELAY、抽象攻城）；
   - `_history/` 移到專案外或加進 .gitignore。
5. **測試基礎**：
   - mptest 裡不少測試（test2/3/5/20/23/28/35）因為世界與帳號狀態變化跑不完（不是這次改動造成的）。
   - 要做「每次測試前重建乾淨的 world / npc / game.db」的固定步驟，重構才有可靠的對照。

## 三、建議順序
| 階段 | 內容 | 風險 |
|---|---|---|
| 1 | A2 先做 GM 開關、真人測試；A3；A5；B4 小清理；B5 測試基礎 | 低，半天 |
| 2 | B1 一套單位決策；A4 一個戰場迴圈 | 中，用 arena 與 mptest 對照 |
| 3 | B3 拆檔、B2 資料類別 | 只搬移，風險在 import；逐檔做、每步跑全套測試 |
| — | A1 換機房 | 與程式無關，越早越好 |

## 進度
### 第 1 階段（2026-10-24 05:00 完成）
- **A2**：`+ 10` 統一改為 RELAY_DELAY；新增 GM `/lag delay N`。預設不變，等真人測試。
- **A3**：NPC tick 後主動回收第 1 代（gc_idle）。
- **A5**：命中與 lump 日誌預設關閉，`/lag combat` 打開。
- **B4**：
  - `spawn()` 取代 43 處 create_task；`data_json()` 取代 14 處讀檔；
  - 移除 ALIEN_CLIENT_CONTROL / SNAPSHOT_RELAY 的死碼分支，以及 4 個沒用到的 import；
  - .gitignore 加入 _history。
- **B5**：`tools/mptest/run_tests.py`：每個測試前重建乾淨環境；新增 fixtures/accounts.base.json；基準結果見 mptest/README。
- **順帶修正的錯誤**：
  - enter_field 函式裡的 `import time` 讓 time 變成區域變數，玩家進場遇到己方 NPC 時會當掉（test28 抓到）；
  - 隱形單位攻擊外星怪 / NPC 時，被攻擊方會直接下 0x2B 反擊，即使沒有偵測器（damage_target）。現在依照隱形規則不反擊。
- **驗證**：21 個回歸測試新舊結果相同，test_battle_ai、test_battlefield 全過。

### 第 2 階段（2026-10-24 05:40 完成）
- **B1 一套 NPC 單位決策**：
  - 刪除舊的逐單位 NPC AI（只在 battle_ai 出錯時才用，約 130 行），以及只有它用到的感知、選目標程式；
  - battle_ai 出錯時，那一秒不下 NPC 命令；
  - 以後 NPC 行為只改 battle_ai 一處（battlesim 的 NPC 方本來就用 battle_ai）。
- **A4 每場戰鬥一個迴圈**：
  - 原本三個工作（alien_ai、npc_ai、poc_loop）改成 `alien_step` / `npc_step` / `poc_step`，由 `battle_loop` 依序呼叫：POC 每 0.5 秒，外星怪與 NPC 每 1 秒；
  - 每場戰鬥只開一個工作（舊名字只負責確保迴圈在跑；中途加入的 NPC 不再另開工作）；
  - `brain_world`（AI 看到的戰場）每秒只建一次，外星怪和 NPC 共用。
- **驗證**：
  - 回歸測試集 21 個全過，結果和改動前相同；
  - test35 從 13/1 變成 14/0；
  - test20 調整一處等待時間：迴圈已經在跑，AI 一秒後就會移動剛抵達的單位，所以改成檢查剛進場的位置；
  - test_battle_ai、test_battlefield 全過。
- sgserver.py 13,637 → 13,483 行（新增的 battle_judge / battle_loop 之後的淨減少）。

### 第 3 階段（2026-10-24 06:10 完成）
- **B3 拆檔**：
  - sgserver.py 13,483 行 → 119 行（載入器 + main），其餘依功能分成 `server/sgs/` 下 15 個檔（305–2,993 行）；
  - 共用同一個命名空間，行為不變（拆分前後非空白行逐行相同，共 12,867 行）。
- **B3 封包分派表**：950 行的 handle_packet 改成 51 個處理函式 `_pkt_XX`，經由 `PACKET_HANDLERS` 對應 55 種封包；條件與順序都和原本相同，沒有對應的情況交給 `_pkt_default`。
- **B2 戰場狀態**：
  - `battlefield.BATTLE_FIELDS`（開戰欄位與預設值）+ `BATTLE_RUNTIME`（執行中欄位）+ `new_battle()`，兩個開戰的地方都改用它；
  - 欄位表收錄在 docs/10_BATTLEFIELD.md。
  - 玩家連線上的 114 種臨時欄位這次**沒有**改：測試涵蓋不夠，而且有幾種假連線物件也會傳進同一批函式，改成直接讀屬性的風險高。之後要改，應該先補測試，一次改一組欄位。
- **工具**：`tools/check_server.py`（pyflakes，整個伺服器當成同一個命名空間檢查）；run_tests、deploy.ps1、remote.sh 都支援 sgs/。
- **驗證**：21 個回歸測試全過；test_battle_ai、test_battlefield 全過；arena 精英 38:22。
