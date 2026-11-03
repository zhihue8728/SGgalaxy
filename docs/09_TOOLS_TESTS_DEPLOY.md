# 09 目录结构 / 工具 / 测试 / 部署

## 1. 目录结构
```
SGgalaxy/
├─ docs/                  ← 本知识库（先看 README.md）
├─ server/                ← 服务器（部署时只上传这层的 .py/.json/.tsv/.txt，排除执行期资料）
│   ├─ sgserver.py        主程序（约 1.2 万行，按「# ---- 区段标题」组织）
│   ├─ npc.py battle_ai.py battlesim.py battle_snap.py aliens.py progression.py damage_types.py
│   ├─ acctstore.py (game.db) ota.py i18n.py unitnames.py
│   ├─ *.json / *.tsv     静态资料（地图点、星门、物品、单位、走格…）
│   ├─ game.db            本机测试资料（帐号/世界/NPC，正式资料只在服务器上）
│   ├─ backups/           本机自动备份
│   └─ _history/          代码修改前备份 *.before_xxx（回滚用）
├─ tools/                 逆向 / 资料产生 / 客户端补丁 / 中文化 / 测试工具（_history/ 为旧版）
│   └─ mptest/            多人自动测试 test1..test43（README.md 说明每个测试）
├─ deploy/                deploy.bat/ps1（部署）、publish.bat/ps1（OTA 发布）、remote.sh、sgserver.service
├─ launcher/              启动器 SGLauncher / 发布器 SGPublish（C#）
├─ analysis/              Ghidra 导出（函数、字符串、handler 反编译、发送目录）
├─ ghidra_scripts/        Ghidra 无头脚本
├─ out/                   产出物（中文客户端 exe、翻译 dat、修正后的 pam2、校对表…）
├─ unpacked/ _scratch/    解包资料 / 草稿
├─ archive/               已淘汰的旧文件（旧 exe、一次性脚本、旧日志；不删除，清单 MOVED.tsv）
├─ SG.exe SG_debug.exe SGalaxy185.exe   根目录只留这三个：原版 1.8.5、补丁客户端（部署会上传）、原版安装包
└─ install_pam_fix.bat    OTA 清单引用，保留在根目录
   docs/PROTOCOL.md 封包目录（最常用）；docs/notes/ 早期总览与研究笔记
   tools/archive_patches/ 已不适用的旧修补脚本；out/_old/ 旧版输出
```

## 2. 常用工具（tools/）
| 类别 | 工具 |
|---|---|
| 帐号 | `acct.py`（create / setpw / hashpw-all …，服务器执行中也可用） |
| 客户端补丁 | `patch_sg_debug_f30.py`（最新，内含整条链）、`build_i18n_exe.py`（→ out/SG_cn.exe、SG_tw.exe） |
| 资源包 | `sgdat.py`、`sgdat_add.py`、`xpf*.py`、`build_hlp.py`、`build_i18n_dat(s).py`、`build_ntf2.py`、`build_zhfont.py`、`install_portraits.py` |
| 地图/星门 | `fix_stub_maps.py` → `fix_portals.py` → `fix_split_maps.py` → `fix_gate_dirs.py`；`gen_gate_spots.py`、`gen_poc_spots.py`、`gen_spawn_spots.py`、`gen_walk_grids.py`、`check_world_maps.py` |
| AI | `arena.py`（离线对战调参）、`test_battle_ai.py` |
| 稽核 | `audit_equip.py` |
| 旧补丁脚本 | 已搬到 `tools/archive_patches/`（直接改旧单一 sgserver.py 的一次性脚本、F12–F25 客户端补丁）；仍在用的是 `patch_sg.py`、`patch_sg_debug.py`、`patch_ota*.py`、`patch_sg_debug_f26`–`f32` |

## 3. 离线测试（tools/mptest）
```
# 在暂存资料夹（测试会改写资料，不要用正式 server 资料夹）
mkdir -p /tmp/mp && cp tools/*.py server/* tools/mptest/*.py /tmp/mp/
cp server/backups/<某次>/accounts.json /tmp/mp/accounts.base.json   # 需要测试帐号 jjjjjjjj / hhhhhhhh
cp /tmp/mp/accounts.base.json /tmp/mp/accounts.json; rm -f /tmp/mp/game.db
python tools/mptest/test33.py
```
- 每次重跑前还原 accounts.json、删 game.db / world.json / npcs.json。
- 已知长期失败（与近期修改无关）：test19 一项、test24 前两项、test35/36 的候选目标 fixture、test38「16 场模拟战」。test20「defenders march in」预期已过时（2026-10-23 起在省内的守军直接从星门进场）。
- 快速单元测试：直接 `import sgserver as S` 后呼叫函数（例：`S.build_battle_result`、`S.evict_province`、`S.npc_spawn_defenders`）。

## 4. 部署（Windows → 腾讯云 43.135.15.91）
- `deploy\deploy.bat`：打包 server 顶层档案 + `tools/sgproto.py`、`acct.py` + `SG_debug.exe` → 服务器 `/opt/sgserver`，先备份 game.db（保留 30 份），**玩家资料不覆盖**，重启 `sgserver.service`。
- `deploy\deploy.bat -Account NAME`：建立 GM 帐号（密码只以哈希储存）。
- 日志：`/opt/sgserver/logs/sgserver.log`（`ssh -i $HOME\.ssh\game.pem ubuntu@43.135.15.91 "sudo grep ..."`）。
- OTA 客户端发布：`deploy\publish.bat`（详见 08 第 7 节）。

## 5. GM 指令（聊天输入；完整清单见 Claude 项目 `claude/GM_COMMANDS.md`）
- NPC：`/npc where [省]`、`/npc stand`、`/npc ambush 省 [国]`、`/npc ambushes`
- 网络/流量：`/lag net`、`/lag adapt`、`/traffic`
- 战斗/地图：`/poc …`、`/theme N`
- 活动：`/event redcoat on|off|auto`
- 政治：`/ally`、`/president`；版本：`/version`

## 6. 修改代码的惯例
- 改之前备份：`cp server/sgserver.py server/_history/sgserver.py.before_<主题>`。
- 改完：`python3 -c "import ast;ast.parse(open('server/sgserver.py').read())"` → 跑相关 mptest → 部署。
- 在注释里写明「user 日期时间：需求」与客户端地址，方便日后追溯。
- 新的设计决策同步写进 Claude 项目 `claude/*.md`，并更新本 docs 对应篇章。


## 戰場規則測試（2026-10-24）
- `tools/test_battlefield.py`：battlefield.judge 涵蓋每種戰鬥的勝負，不需要伺服器。
- `tools/test_battle_ai.py`：戰鬥 AI。
- `tools/arena.py N tier`：AI 對戰勝率。

## 伺服器程式結構（2026-10-24，ARCH_REVIEW 第 3 階段）
- **`server/sgserver.py`**：只剩說明、載入器和 `main()`。依 `PARTS` 的順序把 `server/sgs/*.py` 載入**同一個命名空間**，所以：
  - 所有名稱仍是 `sgserver.X`，測試、工具、GM 改全域變數都照舊；
  - 錯誤訊息會顯示是哪個 part 檔、第幾行。
- **`server/sgs/` 各檔**：
  | 檔案 | 內容 |
  |---|---|
  | core_net | 網路、連線、日誌、帳號快取、流量限制 |
  | world | 世界設定、國家、省份擁有者 |
  | units_items_lab | 工廠、研究所、物品、裝備 |
  | commander_deploy | 暱稱、指揮官、派兵、單位數值 |
  | battle_rules | 技能、勝負判定接口、死亡、技能時機、運輸 / 護盾、戰鬥幀、外星突襲 |
  | battle_flow | 外星怪生成與 AI step、師全滅 / 重派、結束戰鬥、撤退 |
  | results_field | 結算、經驗、收入、國力、領土、勳章、聲望、進場 enter_field |
  | battle_maps | 共用地圖 / 戰鬥、F7、戰鬥控制、模擬中心、快照、POC、battle_loop |
  | strategic_map | 大地圖、省份資訊 |
  | social | FHQ、名冊、聊天、軍團、信箱 |
  | gm_starcenter | 教學、GM 指令、星際中心、轉生 |
  | packets | 指令擁有權檢查、封包處理（`PACKET_HANDLERS`：封包類型對應處理函式 `_pkt_XX`） |
  | client_ota | 客戶端校驗碼、OTA、重啟、備份 |
  | npc_world | NPC 國家：名冊、決策、任務、模擬戰鬥、聊天、外交、攔截 |
  | npc_battle | 戰場上的 NPC、battle brain、`/npc` |
- **純規則模組**（可以單獨 import）：battlefield、battle_ai、battlesim、npc、aliens、progression、damage_types、i18n、acctstore、ota、battle_snap、unitnames。
- **`tools/check_server.py`**：把所有 part 接在一起跑 pyflakes，回報「part 檔:行」。每次改伺服器後都要跑（未定義名稱會讓它失敗）。
- **部署**：deploy.ps1 會一併打包 `server/sgs/*.py`；remote.sh 會編譯檢查 sgserver.py 和 sgs/。
- **舊的一次性修補腳本**已搬到 `tools/archive_patches/`，只保留作紀錄。
