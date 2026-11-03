# 06 装备 / 物品

代码：`sgserver.py` 区段 `Item database`、`EQUIPMENT VALIDITY + STOCK LOADOUT`、`PURCHASE SCENARIOS`、`Lab`、`UNIT SKILLS`；`damage_types.py`。资料：`server/items.json`（2702 项，hlp.dat InfoTbl）、`item_stats.json`、`extra_items.json`、`gold_ids.json`、`item_names_zh.json`、`equip.txt`（各底盘槽位）、`unit_slots.json`。
设计决策：Claude 项目 `claude/DAMAGE_ARMOR_DESIGN.md`、`ITEM_SHOP_RULES.md`、`ITEM_EFFECT_AUDIT.md`、`EQUIP_TIER_AUDIT.md`、`SKILLS_EQUIP_AUDIT.md`、`ENERGY_RULES.md`、`TRANSPORT_SHIELD_ENERGY.md`。

## 1. 物品数据库 class-A 0x10 [确认]
- 客户端 0x13 [u16 缓存 crc] 请求 → 服务器分块 `[0x10][u8 总块][u8 第几块][u16 长度][数据]`，客户端缓存为 `IINF.udf`。
- 数据：`u16 n × item`，再接伤害修正表（`damage_types.table_bytes()`）。
- item：`s8 名称, u16 id, u16 槽位, u8 科技等级, u16 重量, u16 空间, u16 复杂度, u16 ?, u16 ?, u8 类型, 类型附加栏位`。
  - 类型：1 引擎/生物驱动、2 储存、3 电脑、4 武器、5 护甲、6 地雷/炸弹、7 感应/杂项。
  - 武器附加：`u16 伤害, u16 射程×20, u16 冷却×100, u8 旗标 (1 对地, 2 对空)`；引擎：`u16 生命, u16 功率`。
- 图示 = `Item-%03d` / `Item%04d`（id % 2000）。

## 2. 装备合法性（部署窗口会拒绝不合法单位） [确认 005c5d10 / 005c54c0]
不合法：没有物品；没有引擎（类型 1）；物品科技等级 > 单位等级 + Education/2；总重量/空间超过单位上限；总复杂度 > 电脑的最大复杂度；放在底盘没有的槽位或同槽两件。
→ 新买的单位自动给**标准配装** `stock_loadout()`；`ensure_loadouts(a)` 登入时修正。

## 3. 伤害公式 [确认 004d0420 / 004cb080 / 005261b0]
```
伤害 = max(1, 武器伤害 - 护甲 × (100 + TABLE[目标护甲类][攻击伤害类]) / 100)
护甲类 = stats9[1]；伤害类 = stats9[2] // 100（stats9[2] % 100 = 弹道图片）
```
- 伤害类 7 种：none / ballistic / missile / flame / laser / armor piercing / explosive。
- 护甲类 26 种（chassis、ablative、kevlar、hybrid、morganan、steel、phasic … 四魔星护甲、alien carapace），表在 `damage_types.ROWS`。
- 攻击条件：距离 ≤ 射程 + 体积 且 ≤ 视野 + 体积（004cad50）；对该层（空/地）伤害为 0 就不能攻击。

## 4. 商店 / 研究所规则（PURCHASE SCENARIOS）
- 一般物品（基础 / H- / L- / A- / AH- / E- / I-、投石车弹药）：任何研究所，限单位最大科技等级。
- GOLD：只卖 `GOLD_ON_SALE` 里的 id；DEMON（魔星）：只在本国有魔星时间时卖；REDCOAT：独立日活动（7/1–7/7 或 GM `/event redcoat`）。
- 永不出售：Alien Biodrive。
- 价格多为 **[暂定]** 占位。Lab 物品清单 0x33 sub 3。

## 5. 技能来自装备 [确认能力位 → 按钮 004d49a0]
- 物品 `Special` → 能力位 `SPECIAL_BITS`（例：Heal 25、Repair 20、Teleport Unit 26、Shield 43、Grenade 8、Cloak 14、Transport 28 …）。
- 底盘自带 `CHASSIS_SKILLS`；只能安装状态使用的 `INSTALL_ONLY`（需能力位 31，且底盘要有安装美术 `INSTALL_ART`）。
- PUT_UNIT 在 u64 能力位之后：`u8 n × {u8 位, u16 A 能量, u16 B 威力}`；默认值 `SKILL_DEFAULT`。
- 技能 lump 0x30 `[u32 uid][u8 action][参数]`，服务器原样转发并对外星怪模拟伤害（`on_skill`）。

## 6. NPC 装备
- `npc_unit(name, level)`：标准配装 + 等级允许的最好武器（`_w_score` = 对地伤害 + 0.5×对空伤害 / 冷却）和最好护甲（`_a_score`）。
- 装备了地空两用武器的 NPC 单位**照原版可以对空**；只有对地武器的单位，AI 不会让它去打空中目标。

## 物品圖示 / 說明一致性稽核（2026-10-24 15:28）
- 客戶端畫圖示只看物品 id（id % 2000 → `Item-NNN.xpf`），說明文字由 hlp.dat 的 InfoTbl（名稱 → 代碼）查。
- 稽核（`_scratch/audit_icons.py`）：伺服器 2432 件物品中，客戶端原本就認得的 2224 件 **id 全部等於原版代碼** → 圖示與說明都是原版的。
- 客戶端不認得的 208 件：護甲（`fix_armor_ids.py` 依外觀挑的護甲圖）、手冊才有的 39 件（借同類武器的圖）。
- 修正：
  - 手冊才有的 38 件武器（Apparition 狙擊槍、Manticore / Owl / Pegasus 的 Terminus 飛彈、Hawk 的 Terminus 雷射）**沒有說明 → 沒有傷害類型**（沒有彈道動畫、不套護甲表）→ 依該單位武器家族補上類型；Alien Flame Tongue = 火焰。
  - H-Repair Machine 用了急救包（First-Aid Kit, 187）的圖 → id 4187 改成 2186（= Repair Machine 186 + 2000，和原版 H- 規則一樣）；舊帳號登入時自動換 id（`ITEM_ID_REMAP`）。
  - 重新產生 `out/hlp_fixed.dat` / `hlp_tw.dat` / `hlp_cn.dat`（新 id 的說明）→ 需要 OTA 發佈。
- 原版就是這樣、不用改的：
  - 投石車「加成」欄（I-G6137）只有 **Advanced Cloak Module 高端隱形模塊**（原版手冊如此）；欄位名稱 / 欄位圖示（感應器）是客戶端依插槽種類固定顯示的，物品圖示 Item-453 與說明「讓單位隱形」一致，伺服器也給隱形技能。
  - 重弩的防空彈（Plunger / Flake）圖示是彈藥架，原版 id 114/119/116/698/120。
- **15:42 追加**：
  - 投石車砲彈在研究所看不到：研究所的分頁只列「類型」符合的物品，砲彈以前是類型 9（彈藥）放在雜項 / 特殊插槽 7137 / 8137 → 哪一頁都不出現。改成迫擊砲彈 = 類型 7（雜項，技能 Bombard）、防空彈 = 類型 8（特殊，技能 Air Bombard），`"ammo": True` 給戰鬥 / 價格程式辨認。
  - 加成欄的非感應器物品（投石車隱形模塊、Tachyon Scanner、Radar Jammer）以前送感應器種類 1 → 顯示「定向感應器」；沒有視野的改送 0。
  - 圖示確認：遊戲資料夾的 tc.dat 與原版 tc.dat.orig 的 ITEM-114（重弩 N-Plunger）、ITEM-091（弩炮 Terminus Marauder）完全相同，我們沒有改過；弩炮原版就是 Terminus 系列畫砲彈、Maxus 系列畫砲管。
- **15:58 投石車砲彈說明**：客戶端原本 12 顆砲彈的說明全都是「Flak rounds … air units」（迫擊砲彈也一樣）而且只有英文 → `build_hlp.py` 的 `ammo_texts()` 改寫為「只攻擊地面 / 空中、每發傷害、射程加成、需搭配星界發射器」，繁 / 簡中文寫進 `tools/i18n_ui.json`；名稱加註「(對地)/(對空)」（`item_names_zh.json`）；研究所「效率」欄顯示砲彈傷害（只是顯示）。需要 OTA 發佈 hlp / 名稱。
- **16:01 投石車砲彈照原版重分**：客戶端說明顯示原版是 **7 種 Cougar 迫擊砲彈**（M1 M2 M3 S1 S2 S3 T，打地面，id 694 702 711 762 728 776 745）+ **6 種 Astral 防空彈**（Ram Maul Flak Toss Slam Jolt，打空中），各有 H- 版。以前把 Astral 當成迫擊砲彈、Cougar 沒有加入 → 已更正：Cougar = 雜項 7137（Bombard），Astral = 特殊 8137（Air Bombard）。數值為設計值（M 標準、S 攻城、T 頂級高效；Toss 射程 +8 m、Jolt 高效）。舊投石車登入時自動整理（保留可用的砲彈，缺迫擊砲彈補最便宜的 Cougar，`shell_mig`）。
