# CODEMAP — 文件位置总览（2026-11-01 整理）

> 想知道「某个功能的代码 / 资料在哪个文件」先看这里；要查**每一个文件**的内容说明，看自动生成的 [CODEMAP_FILES.md](CODEMAP_FILES.md)（521 个文件，每个都有说明）。
> 重新生成：在 repo 根目录执行 `python tools/gen_codemap.py`；`python tools/gen_codemap.py --check` 只检查是否过期（过期回传 1）。
> 文件说明取自文件本身：Python 的 docstring、C/C# 的开头注释、Markdown 的第一个标题、JSON 的 `_comment`；取不到的在 `tools/gen_codemap.py` 的 `KNOWN` 表里补。**新增文件时请在文件开头写一行说明，然后重新生成。**

## 1. 顶层目录

| 目录 | 内容 | 是否发给玩家 / 部署 |
|---|---|---|
| `client/sgrender/` | 客户端渲染层：`ddraw.dll` 代理 + `SGRender.dll`（D3D9 显示、宽屏、新 HUD）、HUD 美术 `art/`、字体 `fonts/`、美术包 `SGHud.pak` | 是（OTA） |
| `server/` | Python 游戏服务器：入口 `sgserver.py`，主要逻辑在 `server/sgs/`，资料 JSON / `game.db` | 部署到服务器 |
| `launcher/` | C# 启动器 `SGLauncher`、发布工具 `SGPublish`、UDP 中继 `SGRelay`（源码 + 编好的 exe） | 启动器发给玩家 |
| `deploy/` | 部署 / 发布脚本（`deploy.bat`/`.ps1`、`publish.bat`/`.ps1`）、OTA 文件清单 `ota_files.json`、服务器 systemd 文件 | — |
| `tools/` | 建置、补丁（F 系列）、资料产生、帐号、测试工具；`tools/mptest/` 多人测试 | — |
| `docs/` | 知识库（总索引 [README.md](README.md)）、协议、本文件 | — |
| `analysis/` | 逆向输出：函数表、字符串、封包 handler 反编译、勋章 / 单位资料表 | — |
| `ghidra_scripts/` | Ghidra 分析脚本 | — |
| `third_party/` | `cnc-ddraw`（参考 / 备用） | — |
| `out/` | **建置产物**：各语言 exe（`SG_cn/tw/en.exe`）、修好的 dat、`SGLauncher_x.y.z.zip`、OTA 输出 `out/ota/`、校对表 | 部分经 OTA 发出 |
| `unpacked/` | 从游戏 dat 解出的原始资料（dns / hlp / ntf2 / ntt / oml / pam2） | — |
| `archive/` | 已不用的旧文件（旧 exe、一次性脚本、旧日志），清单 `archive/MOVED.tsv` | — |
| `_scratch/` | 临时截图、实验脚本、NPC 日志（可随时清掉，不被任何脚本引用） | — |
| 根目录文件 | `SG.exe`（参考原档）、`SG_debug.exe`（补丁基底，`deploy.ps1` 会复制到服务器当校验参考）、`SGalaxy185.exe`（原版安装包）、`install_pam_fix.bat`（旧手动安装） | — |

## 2. 依功能找文件

### 客户端（`client/sgrender/`，`sh build.sh` 建置）
| 要找 | 文件 |
|---|---|
| ddraw 代理、载入 SGRender | `ddraw_proxy.c` / `.def` |
| 加密：连线（SGX1）+ 读加密档案的 hook | `sgcrypt_hooks.h`（ddraw.dll 内）、`sgcrypt.h`（AES / SHA-256 / X25519）、`sgnet_pub.h`（服务器公钥）、`sgfile_key.h`（档案密钥） |
| D3D9 显示、上传、宽屏 | `sgd3d9.c`、`sgdraw.c`、`sgwindow.c`、`sgrender.c/.h` |
| HUD 入口 / 线程 | `sghud.c` |
| HUD 状态、视窗皮肤表 `SKIN_WINS`、hook | `sghud_state.h` |
| 读游戏状态（视窗、选项、登入） | `sghud_login_input.h` |
| 绘制线程、图层合成、脏矩形 | `sghud_paint.h`、`sghud_rec.h` |
| 每帧框架、聊天、装备监看 | `sghud_frame.h` |
| 各分页（指挥官信息、选项卡、勋章提示） | `sghud_pages.h`、`sghud_parts.h` |
| 荣誉 / 他人指挥官资料（HTTP） | `sghud_honor.h` |
| 单位卡、游标、滑鼠 | `sghud_units.h`、`sghud_cursor.h`、`sghud_mouse.h` |
| 画图基础、GDI+、美术包读取 | `sghud_draw.h`（`hud_pack_get`）、`sghud_gdip.h`、`sghud_login_paint.h` |
| 美术包产生 | `tools/make_hud_pack.py` → `client/sgrender/SGHud.pak` |

### 服务器（`server/`）
| 要找 | 文件 |
|---|---|
| 启动 / 主循环（把 `sgs/*.py` 全部载入同一个命名空间，所以各段可互相呼叫；单独检查用 `tools/check_server.py`） | `sgserver.py` |
| 网路、连线（SGX1 加密握手 `sgx_hello`）、日志、帐号缓存、限流 | `sgs/core_net.py`；协议 `tools/sgnet.py` |
| 封包 handler 表 `PACKET_HANDLERS`、指令归属检查 | `sgs/packets.py` |
| 世界状态、国家、战略地图 | `sgs/world.py`、`sgs/strategic_map.py` |
| NPC 国家（名单、决策、任务、外交、拦截、城镇同步） | `sgs/npc_world.py`、`npc.py`（NPC 指挥官） |
| NPC 战斗 / 战斗 AI | `sgs/npc_battle.py`、`battle_ai.py` |
| 战斗流程、规则、地图、战场判定 | `sgs/battle_flow.py`、`sgs/battle_rules.py`、`sgs/battle_maps.py`、`battlefield.py`、`battlesim.py`、`battle_snap.py` |
| 指挥官、昵称、部署 | `sgs/commander_deploy.py` |
| 服务器单位（外星人 + NPC）指令的唯一出口 | `sgs/unit_orders.py` |
| 玩家单位 HP（唯一处） | `sgs/unit_hp.py` |
| 单位 / 装备 / 研究所 | `sgs/units_items_lab.py`、`items.json`、`item_stats.json`、`unit_slots.json` |
| 战斗结算、XP、收入、国力、领土、勋章（含勋章名称） | `sgs/results_field.py` |
| 公告板、邮件、HUD 资料页 `/b/.../honor/*.txt` | `sgs/board_mail.py` |
| FHQ、名录、指挥官信息、聊天、军团、信箱 | `sgs/social.py` |
| 教学、GM 指令、星际中心、转生、TP/TK | `sgs/gm_starcenter.py` |
| 客户端校验、OTA、重启、备份 | `sgs/client_ota.py`、`ota.py` |
| 帐号 | `acctstore.py`（资料在 `game.db`，每列 AES-GCM 加密） |
| 地图资料 | `map_sizes.json`、`gate_spots.json`、`portal_links.json`、`capital_spots.json`、`spawn_spots.json`、`poc_spots.json`、`walk_grids.json` |

### 发布 / 部署
| 要找 | 文件 |
|---|---|
| 部署服务器 | `deploy/deploy.bat` → `deploy.ps1`（`remote.sh` 在服务器端执行） |
| 发布 OTA | `deploy/publish.bat` → `publish.ps1`（第 0 步检查 `SGHud.pak`）→ `launcher/SGPublish.exe` |
| 哪些文件经 OTA 发出 / 删除 | `deploy/ota_files.json`（`files` 与 `remove`） |
| 加密的 .dat / SGHud.pak | `deploy/encrypt_files.json`（明文来源）→ `tools/sgcrypt_files.py` → `out/enc/`；原版档 `out/orig_dat/` |
| 发布记录 | `docs/OTA_PUBLISH_LOG.md` |

## 3. 备份与搬移的规矩
- 改动前的代码备份：`server/_history/`、`tools/_history/`、`deploy/_history/`，命名 `原文件名.before_<改动>`。部署脚本只拿顶层文件，不受影响。
- 旧 exe：`archive/old_exe/`、`archive/exe_before_f33/`；`out/` 的旧备份在 `out/_old/`（`exe_backups/`、`launcher_zips/`）。
- **不删除文件，只搬移**；每次搬移记入 `archive/MOVED.tsv`（原路径 → 新路径）。
- 刻意保留在原处的：`out/*.dat.before_portraits`（`patch_portraits_dat` 的来源）、`out/_portals/`、`out/_to_delete/`、`third_party/.../ddraw.ini.orig`、根目录 `SG.exe` / `SG_debug.exe`。
- `gen_codemap.py` 不收录：`_history`、`archive`、`out`、`unpacked`、`_scratch`、`__pycache__`、`server/backups`、日志、`*.before_*` / `.bak` / `.orig` / `.old`。

## 4. 机密（永远不进 repo）
- GM 密码只以加盐哈希存在服务器（`tools/acct.py setpw`）。
- OTA 私钥 `%USERPROFILE%\.sgota\ota_key.json`。
- 连线私钥 `%USERPROFILE%\.sgota\net_key.json`（服务器 `/opt/sgserver/.netkey`）、game.db 密钥 `%USERPROFILE%\.sgota\db_key`（服务器 `/opt/sgserver/.dbkey`）。**备份 `%USERPROFILE%\.sgota`**：少了 db_key 就读不出 game.db。详见项目文档 `claude/ENCRYPTION.md`。

## 5. 设计文件
- repo 内：`docs/00`–`12` 主题文件、`docs/PROTOCOL.md`。
- Claude 项目 "SGalaxy" 的 `claude/*.md`：各功能的决策记录（例如 `HUD_LAYERS.md`、`HUD_AUDIT_OPEN_CLOSE.md`、`HUD_ART_PACK_EVAL.md`、`EQUIP_LOSS_MAIL_OPTIONS_MEDALS.md`）。
- 架构总览文档「SGalaxy 架构总览」：客户端 / 服务器 / HUD 图层 / 封包格式。
