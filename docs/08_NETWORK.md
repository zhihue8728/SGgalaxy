# 08 网络连接

完整封包目录：**`docs/PROTOCOL.md`**（服务器→客户端、客户端→服务器、各子格式）。本篇是架构与规则摘要。
代码：`tools/sgproto.py`、`sgserver.py` 区段 `NETWORK LATENCY`、`ANTI-CHEAT *`、`SHARED MAPS AND BATTLES`、`BATTLE SNAPSHOTS`、`OTA`；`ota.py`、`battle_snap.py`。
项目文档：`claude/NETWORK_LATENCY_EVAL.md`、`NETWORK_LATENCY_FIX.md`、`TRAFFIC_BUDGET.md`、`ANTI_CHEAT.md`、`OTA_PLAN.md`、`PROTOCOL_AUDIT.md`。

## 1. 分帧与加密 [确认，docs/notes/FINDINGS.md]
```
0xAA | len16 (big-endian) | payload[len]        payload[0] = 类型
```
- 明文类型：客户端→服务器 0,1,5,6,0x0D；服务器→客户端 0,3,0x0B,0x0C,0x0D。其余加密。
- 加密：`type | seq | body' | chk1 | chk2`，金钥固定 `"NexonInc."`（9 个 u32 循环 XOR）＋ 9 字节块 XOR 块号 ＋ 整体 XOR seq；两个负和校验，**校验失败客户端直接 _exit**。
- 字符串：s8 = u8 长度、s16 = u16 长度。多数整数 big-endian。
- 封包分「class-A」（世界/帐号）与「class-B」（战斗/视窗）两组处理函数。

## 2. 登入流程 [确认]
1. 0x00 握手（版本 0xB9 = 1.8.5）→ 伺服器清单 → 转址。
2. 国家表 0x0F（含 Neutral）＋ 关系 0x05 → 登入 0x03 → 0x02 ok ＋ 0x15 指挥官 ＋ 0x10 物品资料库。
3. 第一次 0x58 心跳后：0x43 星球布局 → 0x17 进入首都 → 0x16 名册 → 0x18/0x20 英雄 → 0x0E 允许下令。
- 代码页：F25 在登入前回报；F16 的 0xF6 也带 GetACP → 决定简/繁/英文（`session_lang_enc`）。

## 3. 锁步战斗（lock-step） [确认]
- **战斗由每个客户端自己模拟**；服务器只转发指令、发帧、估计位置。
- 服务器每 `FRAME_MS = 50 ms` 发帧（class-B 0x80）；自适应 `FRAME_ADAPT`：依连线品质 33–100 ms；连线积压超过 `FRAME_BACKLOG 16 KB` 就跳帧。
- 指令 lump：0x1A 移动、0x2B 攻击、0x30 技能、0x29 攻击（右键）、0x16 走向目标；服务器拥有的单位（外星怪/NPC）由服务器发 lump。
- 时钟：0x0E [01][ms] → 回 [01][ms][游戏时间]（1/100 s）。增援/新单位用共同游戏时间 0x50 让所有客户端同一帧加入。
- 单位死亡：客户端 lump 0x1e [uid]；重复回报丢弃。
- 世界快照：服务器 0x0E [06][u32 0]（T=0 不重设客户端时钟）→ 客户端 0x1d [u16 zlen][zlib(…)]，每 2.5 s 一次，用来校正 AI 的位置估计。

## 4. 延迟与 socket
- 服务器：TCP_NODELAY、QUICKACK、Linux thin-linear 重传、keep-alive（30/10/4）、USER_TIMEOUT 30 s（`tune_socket`）。
- 客户端：F27 TCP_NODELAY。
- `net SGxxx: rtt …, retransmits …` 日志每 10 s 一行；GM `/lag net`、`/lag adapt`。
- 事件循环卡顿 > 100 ms 会记 `!! event loop stalled`；NPC 模拟战放到工作进程（`NPC_WORKERS`）。
- **卡顿定位**（2026-10-23）：`start_stall_probe()` 看门狗线程，主循环超过 150 ms 没心跳就记 `!! stall at 档案:行 函数 <- …`（卡在哪里）。
- 已修的卡顿来源：NPC 名册检查每 10 s 对 240 名 NPC 全跑（约 70 ms）→ 只在名册变动后检查（`_ROSTER_OK`）；求援/换兵对全兵种池算伤害时冷启动装备搜寻（100–200 ms）→ `pool_st9()` 快取、等级取 5 的倍数、每秒最多 4 个新计算。
- **每 65 秒的固定卡顿（已修）**：`allowed_client_hashes()` 每分钟在主循环重算客户端 exe 校验和（2.8 MB，110–160 ms）→ `_exe_hash()` 依档案修改时间快取，只在档案变动时重算。
- 实测玩家延迟约 220–250 ms（主要是网络路线/机房距离，程式无法消除）。

## 5. 流量预算（云主机月流量 512 GB）
- `COALESCE = True`：**仅战斗中、已登入的玩家**把同一轮的封包合并成一次写入（全局合并曾导致登入前闪退）。
- 有指令封包刚送出时，空帧可省略（`last80`）。
- 统计：`TRAFFIC` 计数（含 `TCP_OVERHEAD 54 B/段`），`traffic_logger()` 定期写日志，GM `/traffic`。
- 快照只在需要时请求（`SNAP_ON`、`SNAP_PERIOD`）。

## 6. 反作弊
- 封包频率：每秒 > 400 丢弃，10 s > 1500 断线；聊天 10 s ≤ 8 句；登入失败 5 次 / 5 分钟封锁 IP。
- lump 所有权：只能指挥自己的单位、只能用单位有的技能。
- 外星怪死亡验证（`ANTI-CHEAT: alien deaths`）。
- 客户端代码校验和（F16 0xF6）：`CLIENT_HASH_MODE = "enforce"`，对照服务器上的 `SG_debug.exe` 与各已发布版本（`client_hashes.json`）。

## 7. OTA 更新
- `ota.py`：内建 HTTP/1.1 档案伺服器（Range、keep-alive、**全域频宽上限**，避免挤掉游戏流量），只服务 `updates/`。
- `updates/release.json`（版本、最低版本、期限、各语言说明）、`manifest-<cn|tw|en>.json` + `.sig`（RSA 签章）、`objects/<sha256>`。
- 服务器用客户端校验和对照版本表 → 知道玩家版本、旧版提示、低于 min_version 阻挡。
- 发布：`deploy\publish.bat`（`launcher/SGPublish.exe`）；启动器 `launcher/SGLauncher.exe`。已发布：1.0.10 (F29)、1.0.11 (F30)、1.0.12 (pam2 星门)；待发布 1.0.13 (F31 小地图友军黄色)。
- **私钥 `%USERPROFILE%\.sgota\ota_key.json` 永不进 repo。**

## 指令延後 RELAY_DELAY（2026-10-24，ARCH_REVIEW A2）
- 所有轉發的指令和伺服器發出的 lump 都在 `game_time + RELAY_DELAY` 執行。以前有 3 處寫死 `+ 10`，已統一改用這個常數；`send_lumps` 預設也用它。
- **GM `/lag delay N`（1–20 tick）**：執行中直接修改，用來 A/B 測試；預設仍是 10（100 ms）。
- **理論依據**：客戶端時鐘只推進到最後收到的 0x80 幀時間，而指令和幀走同一條依序的 TCP 連線，所以延後量可以很小。
- **建議測法**：
  - 真人 2 人以上進同一場戰鬥，`/lag delay 5` → `3`；
  - 檢查：單位動作同步（兩邊看到的位置一致）、手榴彈等技能命中時機正常、沒有「單位跳格」；
  - 有問題就 `/lag delay 10` 回復。
- **日誌**：每次命中、每個轉發的 lump 不再預設寫入，需要時用 `/lag combat` 打開。`/lag` 會顯示目前的指令延後與日誌狀態。
- **GC**：每次 NPC tick（10 秒）之後主動回收第 1 代（gc_idle），避免自動回收剛好落在戰鬥中。
- **（2026-10-24 19:52）啟動預熱**：日誌顯示每次重啟後第一次建 NPC 單位池（`npc_pool` → `npc_unit` → `stock_loadout`）在遊戲迴圈裡卡 1.8–2.0 秒（16:01 … 19:51 每次部署後各一次，玩家感覺操控卡頓），第一次登入算客戶端雜湊卡 130–170 ms。現在 `sgserver.main()` 在開埠前先建好（`warm-up done in N ms`，約 3 秒，玩家連不上前完成）。同時量到 SG001 的 rtt 約 220 ms（穩定，每 10 秒重傳 1–4 個）＝ 網路本身的延遲，不是新問題。
- **（2026-10-24 20:02）指令延後 10 → 4 tick、幀預留 2 tick**：下令到單位動作 ≈ rtt（SG001 約 220 ms）+ `RELAY_DELAY`。客戶端 0x80 處理（004a1e14）把每個收到的時間「直接存」為時鐘上限；幀與指令走同一條有序 TCP，所以指令時間只要大於已送出的幀時間（`RELAY_DELAY > FRAME_LEAD`）就不會失步。`RELAY_DELAY = 4`（少 60 ms），`FRAME_LEAD = 2`（幀時間戳提前 20 ms，客戶端不會因幀抖動在最後一幀時間停住，移動較順）。GM：`/lag delay N`、`/lag lead N`；若出現兩邊畫面不同步，`/lag delay 10` 立即改回。test39/40/17/18/33/37 通過（test24/28 失敗在改動前就有）。

## 2026-10-24 22:04 AI 指令閘門（大型戰鬥減輕客戶端負擔）
- 伺服器送出的每個 NPC / 外星單位指令（0x1A 移動、0x1B 停止、0x2B 攻擊、0x30 技能），每台客戶端都要模擬一次，移動和攻擊還要重新尋路。
- 新增 `order_gate()`（battle_rules.py），NPC AI（npc_battle.npc_step）與外星 AI（battle_flow.alien_step）送出前都要經過它：
  - **合併**：同一單位只保留最新的移動 / 攻擊意圖；技能各自獨立。
  - **去重**：同一單位在 `ORDER_REPEAT_S`（4 秒）內的相同指令丟棄。
  - **預算**：每場戰鬥每秒最多 `ORDER_BUDGET`（40）個，依技能 → 攻擊 / 停止 → 移動排序。超出的等下一秒，期間只保留最新意圖；已死亡或已離場單位的指令丟棄。
  - 大型戰鬥每 30 秒在記錄寫一行統計：`order gate (NPC AI, map …): N orders in 30 s -> sent, repeats dropped, delayed, waiting`。
- GM：`/lag orders N` 調整預算，`/lag orders 0` 關閉閘門。
- 測試：test53（8 項）。回歸 test17/18/22/23/33/36/37/40/44/45/51/52 全過；test20 的 1 項是已知的過時預期。
- 客戶端繪圖層：`third_party/cnc-ddraw/v7.1.0.0/`（cnc-ddraw，MIT）已下載，先讓使用者手動測試，尚未加入 OTA（見該資料夾 README.md）。

## 2026-10-24 22:20 單位移動一頓一頓（幀時鐘停頓）
- 客戶端的戰鬥時鐘以實際時間前進，但不能超過最後收到的 0x80 幀時間。它比伺服器時鐘慢約 rtt/2，所以每收到一幀，只剩 FRAME_LEAD 個 tick 可以走。
- 舊設定是每 50 ms 一幀、lead 2 tick（20 ms）：每 50 ms 裡跑 20 ms、停 30 ms，畫面上就是移動卡頓。
- 新設定：`FRAME_MS = 33`、`FRAME_LEAD = 6`（60 ms，可吸收約 27 ms 抖動）、`RELAY_DELAY = 7`（必須大於 lead）。每個指令多 30 ms，相對 rtt 很小。
- 自適應：線上超過 200 人時改用 50 ms（必須小於 lead）。壅塞時仍會退到 100 ms，這時會再出現停頓。
- 每位玩家的幀流量約 30 幀/秒，約 1.5 KB/s（含 TCP/IP 標頭）。
- 現場 A/B 測試（不用部署）：`/lag frame 33`、`/lag delay 7`、`/lag lead 6`。
- 測試：test39、40、18、22、33、52、53 全過。
