#!/usr/bin/env python3
"""docs/10_BATTLEFIELD.md from server/battlefield.py (the table of battle kinds is generated, never edited by hand).
usage: python tools/gen_battlefield_doc.py"""
import os, sys
ROOT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..")
sys.path.insert(0, os.path.join(ROOT, "server"))
import battlefield as BF

CONST = [("時間", ["BATTLE_SECONDS", "REINFORCE_COOLDOWN", "REDEPLOY_WAIT", "REDEPLOY_WINDOW"]),
         ("POC", ["POC_RADIUS", "POC_RATE", "POC_TICK", "TAB_POINTS_PER_POC"]),
         ("死亡 / 防作弊", ["ALIEN_DEATH_FALLBACK", "TTK_SAFETY", "KILL_RATE_WINDOW", "KILL_RATE_MAX", "GRENADE_SPLASH"]),
         ("隱形", ["STEALTH_ACTIONS", "NPC_DETECT_R", "NPC_CLOAK_NEAR"]),
         ("伺服器單位選目標", ["FUTILE_SECONDS", "FUTILE_IGNORE"]),
         ("客戶端快照", ["SNAP_ON", "SNAP_PERIOD", "SNAP_MAX_BAD", "SNAP_FRESH"]),
         ("NPC 在戰場", ["NPC_GIVEUP_RATIO", "NPC_GIVEUP_AFTER", "NPC_WITHDRAW_MAX", "NPC_WAVES_MAX", "NPC_WAVE_AT"]),
         ("經驗 / 結算", ["VICTORY_XP", "VICTORY_KILL_BONUS", "CAPTURE_XP", "JOIN_XP_BONUS", "WOH_XP_BONUS", "XP_LEVEL_CAP",
                       "ARMY_BONUS_PER_RATIO", "ARMY_BONUS_MAX", "PARTICIPATION_BONUS", "PARTICIPATION_MAX",
                       "COMMANDER_BONUS", "FACTION_CONTROLLED_BONUS", "MERCENARY_BONUS_PCT"])]

L = ["# 10 戰場管理（battlefield.py）", "",
     "> 本文件由 `tools/gen_battlefield_doc.py` 從 `server/battlefield.py` 產生；改規則要改程式，再重新產生本文件。", "",
     "2026-10-24 起，戰場規則集中在 `server/battlefield.py`，和 `battle_ai.py` 一樣是純規則、不做網路 IO。"
     "計畫 `claude/BATTLEFIELD_PLAN.md` 的 P1–P4 已全部完成。", "",
     "## 結構",
     "- **`battlefield.KINDS`**：戰鬥種類總表（下表）。",
     "- **`battlefield.judge(view)`**：唯一的勝負判定，回傳 None（繼續）或結果（tag、每位成員勝負、原因）。",
     "  - 事件：`death`（伺服器單位死亡或離場）、`leave`（玩家離開）、`poc`（POC 擁有者改變）、`time`（30 分鐘到）、`tick`（NPC 戰鬥每一步）。",
     "- **`battlefield.may_reinforce()`**：增援規則。NPC 全滅後不能再派部隊；玩家走原版的重新派兵視窗。",
     "- **sgserver.py 的接口**：",
     "  - `battle_kind()` 判斷戰鬥種類；`battle_view()` 把戰場狀態整理成一份資料；",
     "  - `battle_judge(s, event, b)` 呼叫 judge；`finish_battle()` 依 tag 處理附帶動作，並對每個成員呼叫 end_battle。",
     "- **呼叫點**：",
     "  - `_all_dead_check`（death）、`check_attackers_gone`（leave）、`battle_timer`（time）、`poc_loop`（poc）；",
     "  - NPC 戰鬥：`ghost_check_end`（tick）、`ghost_time_up`（time）。",
     "- **結果的附帶動作（finish_battle 依 tag）**：",
     "  - `npc_battle` → ghost_finish（省份易手、NPC 戰果、同盟國不佔領）；",
     "  - `npc_raid_won` → npc_won_battle（突襲者佔領）；",
     "  - `raid_repelled` → 解除突襲、通知；`time_up` → npc_time_up；`hive` → 洞穴勝利標記；`pocs_held` → poc_won。",
     "- **個人結束**：自己的師全滅、重新派兵、強制撤退（squad_lost / redeploy / Ctrl+F11），只結束那位玩家自己的戰鬥，不經過 judge。",
     "", "## 戰鬥種類", "", "| 種類 | 名稱 | 勝負 | 可增援 |", "|---|---|---|---|"]
for k, zh, win, rf in BF.rules_table():
    L.append(f"| {k} | {zh} | {win} | {'是' if rf else '否'} |")
L += ["", "## 戰場常數（battlefield.py）", "", "| 類別 | 名稱 | 值 |", "|---|---|---|"]
for cat, names in CONST:
    for n in names:
        L.append(f"| {cat} | `{n}` | {getattr(BF, n)!r} |")
L += ["", "## 戰場狀態欄位（BATTLE_FIELDS / BATTLE_RUNTIME）", "",
      "戰場仍是一般的 dict。開戰時欄位由 `new_battle()` 建立（未列出的欄位名稱會報錯）；執行中才加入的欄位列在 BATTLE_RUNTIME。", "",
      "| 欄位 | 預設 | 意義 |", "|---|---|---|"]
for k, (d, doc) in BF.BATTLE_FIELDS.items():
    L.append(f"| `{k}` | {d!r} | {doc} |")
for k, doc in BF.BATTLE_RUNTIME.items():
    L.append(f"| `{k}` | （執行中） | {doc} |")
L += ["", "## 新增一種戰鬥",
      "1. 在 `KINDS` 加一列。",
      "2. 在 `judge()` 加規則，NPC 類放在 `_judge_npc()`。",
      "3. 在 sgserver 的 `battle_kind()` 辨認這種戰鬥。",
      "4. 如果結果有附帶動作，在 `finish_battle()` 依 tag 處理。",
      "5. 在 `tools/test_battlefield.py` 補檢查，然後重新產生本文件。", "",
      "## 測試",
      "- `tools/test_battlefield.py`：每種戰鬥、每種結束方式都有一項檢查。",
      "- 改戰場規則後跑：`test_battlefield.py`、`test_battle_ai.py`、mptest 的 test33 / test34 / test37。"]
open(os.path.join(ROOT, "docs", "10_BATTLEFIELD.md"), "w", encoding="utf-8").write("\n".join(L) + "\n")
print("docs/10_BATTLEFIELD.md written:", len(BF.KINDS), "kinds")
