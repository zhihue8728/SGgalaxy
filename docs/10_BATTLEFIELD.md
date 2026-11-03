# 10 戰場管理（battlefield.py）

> 本文件由 `tools/gen_battlefield_doc.py` 從 `server/battlefield.py` 產生；改規則要改程式，再重新產生本文件。

2026-10-24 起，戰場規則集中在 `server/battlefield.py`，和 `battle_ai.py` 一樣是純規則、不做網路 IO。計畫 `claude/BATTLEFIELD_PLAN.md` 的 P1–P4 已全部完成。

## 結構
- **`battlefield.KINDS`**：戰鬥種類總表（下表）。
- **`battlefield.judge(view)`**：唯一的勝負判定，回傳 None（繼續）或結果（tag、每位成員勝負、原因）。
  - 事件：`death`（伺服器單位死亡或離場）、`leave`（玩家離開）、`poc`（POC 擁有者改變）、`time`（30 分鐘到）、`tick`（NPC 戰鬥每一步）。
- **`battlefield.may_reinforce()`**：增援規則。NPC 全滅後不能再派部隊；玩家走原版的重新派兵視窗。
- **sgserver.py 的接口**：
  - `battle_kind()` 判斷戰鬥種類；`battle_view()` 把戰場狀態整理成一份資料；
  - `battle_judge(s, event, b)` 呼叫 judge；`finish_battle()` 依 tag 處理附帶動作，並對每個成員呼叫 end_battle。
- **呼叫點**：
  - `_all_dead_check`（death）、`check_attackers_gone`（leave）、`battle_timer`（time）、`poc_loop`（poc）；
  - NPC 戰鬥：`ghost_check_end`（tick）、`ghost_time_up`（time）。
- **結果的附帶動作（finish_battle 依 tag）**：
  - `npc_battle` → ghost_finish（省份易手、NPC 戰果、同盟國不佔領）；
  - `npc_raid_won` → npc_won_battle（突襲者佔領）；
  - `raid_repelled` → 解除突襲、通知；`time_up` → npc_time_up；`hive` → 洞穴勝利標記；`pocs_held` → poc_won。
- **個人結束**：自己的師全滅、重新派兵、強制撤退（squad_lost / redeploy / Ctrl+F11），只結束那位玩家自己的戰鬥，不經過 judge。

## 戰鬥種類

| 種類 | 名稱 | 勝負 | 可增援 |
|---|---|---|---|
| hive | 蜂巢洞穴 | every hive destroyed (the other aliens do not matter) | 是 |
| waves | 波次洞穴 | every wave destroyed | 是 |
| ambush | 伏擊 / 封鎖 | ambushed side: every ambusher dead or gone; ambushers: the time runs out (NPC ambush rules) or the ambushed players leave | 是 |
| raid | 突襲（外星怪 / NPC） | defenders: every raider dead; NPC raiders: every POC held | 是 |
| province | 省份攻防 | attackers: hold every POC; defenders: no attacker left or TIME UP with the POC majority (ties to the defender); killing every enemy is not enough | 是 |
| field | 無 POC 戰場（外星怪領地） | every enemy destroyed | 是 |
| npc | NPC 攻省（有或沒有玩家） | attackers: hold every POC, or (no POC) every defender dead; lose: wiped out with no reserve, or a third side holds every POC; TIME UP: POC majority (no POC: smaller share of losses) | 是 |

## 戰場常數（battlefield.py）

| 類別 | 名稱 | 值 |
|---|---|---|
| 時間 | `BATTLE_SECONDS` | 1800 |
| 時間 | `REINFORCE_COOLDOWN` | 60 |
| 時間 | `REDEPLOY_WAIT` | 20 |
| 時間 | `REDEPLOY_WINDOW` | 60 |
| POC | `POC_RADIUS` | 48 |
| POC | `POC_RATE` | 100 |
| POC | `POC_TICK` | 0.5 |
| POC | `TAB_POINTS_PER_POC` | 50 |
| 死亡 / 防作弊 | `ALIEN_DEATH_FALLBACK` | 6.0 |
| 死亡 / 防作弊 | `TTK_SAFETY` | 3.0 |
| 死亡 / 防作弊 | `KILL_RATE_WINDOW` | 60 |
| 死亡 / 防作弊 | `KILL_RATE_MAX` | 40 |
| 死亡 / 防作弊 | `GRENADE_SPLASH` | 128 |
| 隱形 | `STEALTH_ACTIONS` | (15, 32) |
| 隱形 | `NPC_DETECT_R` | 480 |
| 隱形 | `NPC_CLOAK_NEAR` | 1000 |
| 伺服器單位選目標 | `FUTILE_SECONDS` | 12.0 |
| 伺服器單位選目標 | `FUTILE_IGNORE` | 15.0 |
| 客戶端快照 | `SNAP_ON` | True |
| 客戶端快照 | `SNAP_PERIOD` | 2.5 |
| 客戶端快照 | `SNAP_MAX_BAD` | 3 |
| 客戶端快照 | `SNAP_FRESH` | 4.0 |
| NPC 在戰場 | `NPC_GIVEUP_RATIO` | 0.3 |
| NPC 在戰場 | `NPC_GIVEUP_AFTER` | 20.0 |
| NPC 在戰場 | `NPC_WITHDRAW_MAX` | 45.0 |
| NPC 在戰場 | `NPC_WAVES_MAX` | 99 |
| NPC 在戰場 | `NPC_WAVE_AT` | 0.5 |
| 經驗 / 結算 | `VICTORY_XP` | 20 |
| 經驗 / 結算 | `VICTORY_KILL_BONUS` | 0.5 |
| 經驗 / 結算 | `CAPTURE_XP` | 30 |
| 經驗 / 結算 | `JOIN_XP_BONUS` | 0.5 |
| 經驗 / 結算 | `WOH_XP_BONUS` | 0.25 |
| 經驗 / 結算 | `XP_LEVEL_CAP` | {1: 35, 2: 60, 3: 999} |
| 經驗 / 結算 | `ARMY_BONUS_PER_RATIO` | 25 |
| 經驗 / 結算 | `ARMY_BONUS_MAX` | 50 |
| 經驗 / 結算 | `PARTICIPATION_BONUS` | 5 |
| 經驗 / 結算 | `PARTICIPATION_MAX` | 25 |
| 經驗 / 結算 | `COMMANDER_BONUS` | 10 |
| 經驗 / 結算 | `FACTION_CONTROLLED_BONUS` | 5 |
| 經驗 / 結算 | `MERCENARY_BONUS_PCT` | 20 |

## 戰場狀態欄位（BATTLE_FIELDS / BATTLE_RUNTIME）

戰場仍是一般的 dict。開戰時欄位由 `new_battle()` 建立（未列出的欄位名稱會報錯）；執行中才加入的欄位列在 BATTLE_RUNTIME。

| 欄位 | 預設 | 意義 |
|---|---|---|
| `map` | None | province / map id |
| `t0` | None | game clock origin (time.monotonic) shared by every member |
| `targets` | None | server-owned units {uid: tg} (aliens, NPC units, training targets) |
| `pocs` | None | {poc id: {x, y, owner, strength, progress, capturing}} |
| `members` | None | set of player sessions on the map |
| `owner` | None | session that commands the battle (Ctrl+F7, AI loop, snapshots) |
| `ghost` | None | the server's stand-in session of a simulated NPC battle (None = a player opened it) |
| `hive_marks` | [] | hive minimap markers |
| `won` | False | decided (battlefield.judge) - set only by finish_battle / ghost_finish / npc_won_battle |
| `defender` | 0 | nation that owns / defends the province (0 = none) |
| `sim` | False | battle simulation center (no losses) |
| `npc_attacker` | None | NPC nation that attacks (kind 'npc') |
| `hunt` | False | NPC hunt of an alien province (never captures) |
| `ambush` | None | province id of an ambush / blockade |
| `opened` | None | time.time() the NPC battle was opened |
| `npc_side` | （執行中） | NPC nation of the raiders / defenders on a player's battle |
| `npc_raid` | （執行中） | the NPC side attacks |
| `npc_ally` | （執行中） | the NPC side is allied to the players |
| `npc_ids` | （執行中） | NPC commanders on the map |
| `npc_meta` | （執行中） | NPC meta |
| `reinf` | （執行中） | NPC reinforcement squads sent |
| `reinf_at` | （執行中） | next NPC reinforcement time |
| `sos` | （執行中） | NPC calls for help |
| `brains` | （執行中） | battle_ai.Brain per NPC side |
| `alien_brain` | （執行中） | battle_ai.Brain of the aliens |
| `giveup` | （執行中） | NPC give-up timers |
| `_loop` | （執行中） | the battle_loop task |
| `_bw` | （執行中） | brain_world cache of this AI second |
| `dead_aliens` | （執行中） | dead server unit ids |
| `snap_req` | （執行中） | last snapshot request |
| `snap_t` | （執行中） | last snapshot |
| `snap_n` | （執行中） | snapshots applied |
| `snap_bad` | （執行中） | unreadable snapshots |
| `faction_recorded` | （執行中） | faction record written |

## 新增一種戰鬥
1. 在 `KINDS` 加一列。
2. 在 `judge()` 加規則，NPC 類放在 `_judge_npc()`。
3. 在 sgserver 的 `battle_kind()` 辨認這種戰鬥。
4. 如果結果有附帶動作，在 `finish_battle()` 依 tag 處理。
5. 在 `tools/test_battlefield.py` 補檢查，然後重新產生本文件。

## 測試
- `tools/test_battlefield.py`：每種戰鬥、每種結束方式都有一項檢查。
- 改戰場規則後跑：`test_battlefield.py`、`test_battle_ai.py`、mptest 的 test33 / test34 / test37。
