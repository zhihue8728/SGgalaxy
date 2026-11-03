# SGalaxy 私服 — 知识库总索引（2026-10-23 整理）

> 目的：把逆向成果、系统框架与现行机制集中在一处，**改功能前先查这里**，避免重复研究 / 重复造轮子。
> 每篇都标注「代码位置」：`sgserver.py` 用**函数名 / 区段标题**定位（行号会变，搜区段标题 `# ---- XXX`）。
> 状态标记：**[确认]** 已对照客户端反编译或游戏画面验证；**[暂定]** 数值/行为是占位或推测。

| # | 文件 | 内容 |
|---|------|------|
| 1 | [01_REVERSE_ENGINEERING.md](01_REVERSE_ENGINEERING.md) | 客户端逆向架构、补丁链 F1–F30、工具、崩溃诊断流程、已知客户端地址 |
| 2 | [02_NATIONS.md](02_NATIONS.md) | 星系/星球/国家框架、省份 id、首都、领土、同盟、国力、阵营战绩 |
| 3 | [03_MECHANICS.md](03_MECHANICS.md) | 战斗（POC、部署、增援、撤退、结算）、经济、成长、伏击、模拟中心等现行规则 |
| 4 | [04_NPC_AI.md](04_NPC_AI.md) | NPC 国家（战略层：思考/出兵/行军/拦截/巡防/守军）＋ 战斗 AI（battle_ai 大脑、模拟战） |
| 5 | [05_GATES_MAPS.md](05_GATES_MAPS.md) | 星门 / 传送点、省份图连通、gate_spots、POC 位置、地图资料产生流程 |
| 6 | [06_EQUIPMENT.md](06_EQUIPMENT.md) | 物品数据库、装备合法性、伤害/护甲公式、商店规则、技能来源 |
| 7 | [07_UNITS.md](07_UNITS.md) | 底盘代码、单位种类、stats9、能力位、技能、NPC 单位角色、升级树 |
| 8 | [08_NETWORK.md](08_NETWORK.md) | 封包格式、锁步战斗、帧率自适应、合并发送、快照、流量预算、反作弊、OTA |
| 9 | [09_TOOLS_TESTS_DEPLOY.md](09_TOOLS_TESTS_DEPLOY.md) | 目录结构、工具清单、离线测试、部署 / 发布流程、GM 指令 |
| 10 | [10_BATTLEFIELD.md](10_BATTLEFIELD.md) | 战场管理：战斗种类总表、唯一胜负判定 judge()、增援规则、战场常数（battlefield.py） |
| 11 | [11_ARCH_REVIEW.md](11_ARCH_REVIEW.md) | 代碼架構評估與優化進度（延遲、簡潔、拆檔） |
| 12 | [12_UNITS_EQUIP_SKILLS_FX.md](12_UNITS_EQUIP_SKILLS_FX.md) | **單位・裝備・技能・武器動畫總整理**（取得與升級、欄位、屬性換算、能力位、技能效果、外觀碼、已知缺口） |
| 0 | [00_LOCKED_SETTINGS.md](00_LOCKED_SETTINGS.md) | 已确认的设定（锁定，不得随意变更） |
| — | [CODEMAP.md](CODEMAP.md) | **文件位置总览**：每个目录 / 功能对应哪个文件；逐文件说明见 [CODEMAP_FILES.md](CODEMAP_FILES.md)（`python tools/gen_codemap.py` 自动生成） |

## 其他既有文档（仍有效，本知识库会引用）
- `docs/PROTOCOL.md`（封包目录，**最完整的协议参考**）。
- `docs/notes/`（早期总览与研究笔记）：`ARCHITECTURE.md`、`FINDINGS.md`、`research_multiplayer.md`、`research_skills.md`、`research_honor_medal.md`、`GAPS.md`、`UX_BACKLOG.md`、`HIT_DELAY_PLAN.md`、`PLAN.md`、`progression_tutorial_notes.md`。
- `archive/`：已不再使用的旧文件（旧版 exe、一次性脚本、旧日志），清单见 `archive/MOVED.tsv`；`tools/archive_patches/`、`out/_old/` 同理。
- Claude 项目文档（claude.ai 项目 "SGalaxy"，路径 `claude/*.md`）：各功能的设计决策记录，例如 `NPC_NATIONS_PLAN.md`、`NPC_BATTLE_AI_ARCH.md`、`DAMAGE_ARMOR_DESIGN.md`、`GATE_PLACEMENT.md`、`TRAFFIC_BUDGET.md`、`OTA_PLAN.md`、`DEPLOY_STEPS.md`、`GM_COMMANDS.md`、`ANTI_CHEAT.md`。

## 资料夹整理（2026-10-23）
- `server/_history/`、`tools/_history/`：所有 `*.before_xxx` / `*.bak` 代码备份（改动前的版本）。部署脚本只拿 `server/` 顶层文件，不受影响。
- 新增 `docs/`（本目录）。

## 安全约束（永久）
- GM 密码只以加盐哈希存在服务器（`tools/acct.py setpw`），**绝不写入文件或 repo**。
- OTA 私钥 `%USERPROFILE%\.sgota\ota_key.json` **绝不进 repo**。
