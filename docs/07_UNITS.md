# 07 单位

代码：`sgserver.py` 区段 `Factory unit catalogue`、`Lab upgrade tree`、`UNIT SKILLS`、`skill timing`、`TRANSPORT + SHIELD state`、`HOW THE NPCs USE THEIR UNITS`；`unitnames.py`（中英名）；资料 `units_manual.json`（官方手册各单位/Mk 等级的影响力、载重、空间、生命、护甲、速度、视野）。
项目文档：`research_skills.md`、Claude 项目 `claude/NPC_UNIT_ROLES.md`、`COMBAT_HIT_RULES.md`、`TRANSPORT_SHIELD_ENERGY.md`。

## 1. 底盘代码 [确认]
- 名称 = 客户端美术代码：`h` 英雄、`g` 地面、`a` 空中、`d` 其他。例：Imp=g004、Pegasus=g009、Hawk=a004、Behemoth=g020。
- `unit_kind(chassis)` → `(0x16 类型 1 地面/2 空中, 美术种类 h0 g1 a2 d3, 美术编号)`。
- 工厂分页（兵科）：0 INF、1 MOB、2 AVI、3 ORG；class id = 分页×100 + n；`unit_branch()`。
- 购买条件：影响力 = 兵科等级 + Clout/2 ≥ `UNITS` 表的 infl。
- 研究所升级 `ADVANCED`：(进阶名, 美术码, 基础名, 需要的 UQ, 中文名)。MK2 没有自己的美术，用基础单位的。

## 2. PUT_UNIT（0x18）战斗数值 stats9 [确认]
| 索引 | 意义 | 客户端偏移 |
|---|---|---|
| 0 | 护甲值 | +0x11c |
| 1 | 护甲类（伤害表的行） | +0x130 |
| 2 | 伤害代码 1xx..6xx（//100 = 伤害类） | +0x120 |
| 3 / 4 / 5 | 对地伤害 / 射程×20 / 冷却×100 | +0x134/138/13c |
| 6 / 7 / 8 | 对空伤害 / 射程×20 / 冷却×100 | +0x140/144/148 |
- 标头：速度 u16 +9（×10，默认 100 = 10 m/s）、视野 +0xb。
- `unit_stats9(u)` 由单位与装备计算；`unit_sight(st9)`。
- 0x16 名册纪录的 block A 是另一种格式（[0] 最大 HP、[1] 目前 HP、[4] 载重、[5] 空间、[7] 速度×10）。

## 3. 能力位（PUT +0x22 u64） [确认]
- 位 1 = 可攻击（`ABILITY_ATTACK = 0x2`），且需对应伤害 > 0 才有攻击按钮。
- 其他位 = 技能按钮（见 06 第 5 节）；位 27 = 可被运输/传送；位 31 = 安装状态。
- **支援单位不给攻击位**。

## 4. 空中 / 地面
- 空中单位 = 底盘码 `a` 开头（`put_args["kind"] == 2`）。护甲行用 aircraft hull。
- 目标层：打空中用 st9[6..8]，打地面用 st9[3..5]；伤害 0 就不能打该层。地空两用武器两层都能打（原版）。

## 5. NPC 单位角色（2026-10-23）
- `npc_unit_role(name, st9)` → line / melee / artillery / support / antiair / capturer。
- 支援单位清单 `NPC_SUPPORT_UNITS`（不攻击）；NPC 不使用的单位 `NPC_NO_UNITS`（Sapper、Virus、Medic …）。
- 支援技能 `NPC_SKILL_BITS`：g016 治疗；g023 修理+治疗；g056 治疗+修理；g035 传送+护盾；g002 护盾。
- 射程 `npc_weapon_range()`（像素）；炮兵保持 `NPC_ARTY_STANDOFF` 距离。
- 生物单位（inf/org）用治疗，机械单位用修理（`bio` 栏位）。
- NPC 可用兵种 `npc_pool()`：步兵、机动、**航空**（2026-10-23 起；航空只当第二兵种/反制兵种）；不用生物兵种。

## 6. 外星怪单位
- 地面生物美术 g011/g015/g024/g025 等；空中 Oizys/Manta/Mamos（进阶星起）；孵化巢 Hive。
- 名称/等级/角色见 `aliens.py`；中文名 `unitnames.CN`。

## 8. 單位架構照官方手冊（2026-10-24）
- **來源**：`server/units_manual.json`（官方手冊 U-*.txt）：每個步兵 / 機動 / 航空底盤的**影響力（每個 Mk）**、所屬**框架**（frame，例如 Cyclo-rig = Manticore 3 / Chimera 25 / Hydra 47）、HP、護甲、速度、視野、載重、空間。
- **工廠（13:41 使用者修正）**：只賣**每個框架的基礎單位**（框架內 Mk1 影響力最低者：Imp、Wraith、Sapper、Shade、Ghast、Spirit、Pegasus、Red-Eye、SatCom、Behemoth、Manticore、Triage、Arbalest、Hawk、Pelican、Eagle、Roc）＋生物 / 付費單位（Wight、Quorg）；其他全部在研究所升級取得（測試確認每個底盤都升得到）。影響力 = 兵科等級 + Clout // 2。
  - 0x2f '@' 每筆前 3 byte：`[u8 ?][u8 你的影響力 → +0x2a][u8 需要的影響力 → +0x2b]`；客戶端在 +0x2a < +0x2b 時把該單位變灰（`00484239`），購買時拒絕並顯示需要的影響力（`00486238`）。以前三個 byte 都送 1 → 畫面一律「影響力 1 / 所需 1」。
- **研究所升級（只能往上）** `upgrade_options()`：下一個 Mk，或同框架中 Mk1 影響力更高的底盤；需要 UQ（單位等級 + Clout // 2）≥ 目標的手冊影響力。例：Manticore → Manticore-MK2 / Chimera / Hydra；Chimera → Chimera-MK2 / Hydra；不能往回。
- **Mk 上限 `MK_MAX = 9`**（14:20）：封包大小不受限；Mk1–Mk5 各有自己的 class id（每頁 ≤ 99），**Mk6–Mk9 共用同底盤 Mk5 的 class id**（客戶端只拿 class id ÷ 100 決定分頁，其他都用名稱比對），不需要客戶端補丁。若遊戲內研究所樹顯示異常，把 `MK_MAX` 改回 5 即可。
- 名稱沿用 `<底盤>-MK<n>`，中文 `unitnames` 自動加「 MK2…MK9」。NPC 單位池：新進工廠的進階底盤權重維持以前的「影響力 / 8」。測試 `test50`。

## 9. 2026-10-24 下午修正
- **SatCom 拿掉**（14:53）：和 Red-Eye 同框架（Gyro-rig）、同影響力，是重複的基礎單位。工廠、研究所、單位表都不再有它；已擁有的 SatCom 自動變成同 Mk 的 Red-Eye（`migrate_removed_chassis`）。`REMOVED_CHASSIS`。
- **研究所升級樹顯示完整路線**（14:54）：以前只送「擁有的單位」的下一步 → Hawk 只看得到 MK2 / Owl / Falcon。現在加送所有能到達的型號（`upgrade_reach`），可以直接點更深的節點，伺服器照最短路徑分步扣費（`upgrade_path_cost`），單位品質要達到路徑上最高的需求。各 Mk 上限照手冊：Hawk MK9、Owl MK7、Falcon MK5。
- **升級資訊的速度**：0x44 單位表 G4 = 速度 ×10（以前送診斷值 14 → 每個目標都顯示 1.4 m/s）。
- **升級後裝備自動調整** `fit_after_upgrade`：舊插槽的物品換成新底盤同名物品；沒有對應的才拆下退半價；缺引擎 / 電池 / 電腦補最便宜的；超重 / 超空間時先拆最重的武器 / 護甲 / 配件。
- **有機單位**（14:58）：影響力（UQ）、載重、空間都照手冊（例 Mamos = Momas-Primus UQ 80、120 kg / 200 L；Quorg UQ 1、104 kg / 16 L）。
  - 手冊的有機武器 / 護甲頁（I-G4311..4371、I-G5311..5341）是 19 階「(rare)」器官 W-3xx-000..180 / A-3xx，客戶端沒有物品紀錄 → 做成**天生器官**（`server/organs.py`）：階級 = 單位等級 1–60 對應 0–18，至少為進化階段 UQ ÷ 10。以前所有有機單位都只有預設 60 傷害 / 10 m、沒有護甲。
  - 各系：Oizys 火焰吐息（10 m、1 s）；Ubik 酸液對地對空（16.5 m）；Slanth 酸球長程（35 m）；Poda 近戰（4.5 m）；Manta 弱攻擊（15 m，特長是偵測）；Mamos 只能對空（30 m）；Larva 近戰（4.2 m）。護甲行用外星甲殼。
  - Quorg 用一般步兵插槽，武器槽 4049 以前是空的 → 加入手冊的 Razor 爪（客戶端已有 id 966–975 / 2966–2975）。
  - 尚未接上：各系的特殊器官（Manta 偵測眼 / 隱形、Slanth 射程延伸、Poda 酸囊…，見 organs.py 註解）。
- **戰鴿 War Pigeon = 轟炸機**（15:11，原版手冊 U-a011：「用源源不絕的炸彈覆蓋地面部隊」）：原版**沒有武器頁**（I-G4211 不存在），雜項 = 後燃器（P- / PI- / Pimp-Afterburner），特殊 = Carpet Bomb 地毯轟炸系列（Genus CKB、Terminus Oliphant、Maxus Curler、Genus HR-N、Synker Clasher…）。火力 0 是正確的，靠地毯轟炸技能攻擊。
  - 新的 / 升級來的戰鴿自動裝最便宜的地毯轟炸（`STOCK_SKILL["a011"] = (40,)`；`fit_after_upgrade` 也補）；舊帳號的戰鴿在下次登入時補一次（`skill_mig` 2）。
  - NPC 不使用戰鴿（AI 不會放地毯轟炸）。
  - 其他沒有武器的機甲都是支援單位（Sapper、Medic、Red-Eye、Triage、Gear-Doc、Orbus、Roc），Trebuchet 用發射器 + 砲彈。
- **自走砲（15:17，對照原版手冊 U-g010 / U-g034 / U-g037）**：
  - 弩炮 Arbalest：武器 I-G4301 迫擊砲彈 10 + H- 10 件（Terminus Marauder … Maxus Mauler-X），數值與我們的完全一致；只打地面、範圍傷害（Bombard）。
  - 重弩 Ballista：武器 I-G4101 防空砲 9 + H- 9 件（Terminus N-Plunger … H-Diver），**只打空中**（Air Bombard），一致。所以屬性頁火力（對地）顯示 0 是正常的。
  - 投石車 Trebuchet：武器 I-G4137 只有發射器（Astral Rubberband … X-Astral Launch，只有射程 / 冷卻，沒有傷害），一致；原版手冊**沒有**投石車的雜項 / 特殊頁，砲彈（Astral Ram … Jolt、Astral Flak）是我們 10-24 設計的。
  - 雜項 I-G7101：原版就只有 Gryphon Cloak Detect（三種砲車共用）；Arbalest / Ballista 的特殊頁 I-G8210 / I-G8234 原版不存在。
  - 加成 I-G6201 砲兵感測器 TACS M1–M5 / RTS SG1–SG5：手冊射程欄 0、說明寫「目標射程 +N 公尺」→ 以前沒有加到射程，**現在照說明加**（Terminus Marauder 30 m + TACS M1 = 35 m）。
  - 物品圖示是客戶端原本的（由物品 id 決定），沒有改；砲彈飛行動畫的原版對應不明，仍用爆炸類圖案。

## 10. 與 fandom wiki 對照（2026-10-24 15:49，使用者決定：全部維持官方手冊）
- 來源：https://shattered-galaxy.fandom.com/wiki/Category:Units（70 頁，485 列 Upgrade Stats）對照 `units_manual.json` 320 個單位等級。
- **一致**：影響力 / 單位品質、視野、載重全部一致；145 個等級全部欄位一致。
- **HP**：172 筆 wiki 較高（低 Mk 高 5–25%，高 Mk 差距變小）。wiki 註明「HP needs proof」，並把較高 Mk 的舊 HP 劃線為過時，而劃線的舊數字＝我們手冊的數字 → wiki 記的是後期版本的數值。各單位第一筆（手冊 → wiki）：daeva 1200→1413、imp 1680→1911、shade 1200→1476、ghast 1128→1410、spirit 1110→1394、liche 1575→2100、spectre 1440→1977、manticore 2376→2956、orbus 1728→2182、chimera 2895→3302、hawk 984→1210、roc 1680→2044、ballista 1440→1623 …
- **Wraith**：wiki 是另一套設定（HP 4462–18102、護甲 1–5、空間 9–14），手冊 HP 1680–8280、護甲 12–63、空間 17–29。
- **其他少數差異**（手冊 → wiki）：arbalest-mk3 速度 1.2→1.3；vulture 速度 1.2→1.3、mk2 1.4→1.5；eagle-mk9 速度 5.5→5.2；falcon-mk2 護甲 3→9；liche 空間 18→16（wiki 已劃線）。
- 決定：**全部維持 1.8.5 官方手冊數值**（與我們的 1.8.5 客戶端同一時代）；以上差異只記錄。
- **研究所升級樹改成真正的樹**（16:06，圖片重疊）：升級關係不是樹（Arbalest → Ballista → Trebuchet，同時 Arbalest → Trebuchet；同框架擁有多台），14:54 起送出所有可到達型號 → 同一型號畫好幾次、圖片疊在一起。`lab_tree()`：每個擁有的型號列出直接選項（已在別處出現的不再列），每個選項底下只接它自己的 Mk 線（Hawk → Hawk-MK2 → … → MK9；Owl → Owl-MK2 …），任何型號只出現一次。伺服器仍接受點更深的節點（最短路徑分步扣費）。
- **（已撤回 16:26）研究所左側底盤清單只顯示自己有的（16:10，客戶端補丁 F33）**：上線後研究所顯示「你沒有任何航空單位」→ 旗標 +0x3cc 判斷「有單位」用的資料在升級頁不是單位清單，F33 已撤回（exe 還原為 archive/exe_before_f33，壞版與腳本在 archive/exe_f33_bad）。原文：：清單（00449cc0 建、004482a0 排版）是依 0x44 單位表列出該分頁「所有」底盤；類別內建一個旗標 +0x3cc，設了就跳過沒有單位的底盤（00444360）與沒有單位的型號（00448483），但 1.8.5 客戶端從不設（00443e1f 寫 0）。F33 改成寫 1。`tools/patch_sg_debug_f33.py`（輸入目前的 F32 版 SG_debug.exe；舊的整條鏈從 SG.exe 已跑不起來）；舊檔備份 `archive/exe_before_f33/`。升級清單（0x33 sub 2）也改回只送擁有的型號。
- **升級後單位「消失」（16:18）**：伺服器紀錄顯示 War Pigeon → War Pigeon-MK2 都成功；研究所左側清單每個 class id 一項、依 class id 排序，而 Mk / 進化型的 id 以前排在所有基礎底盤之後（War Pigeon 205、War Pigeon-MK2 228）→ 升級後的單位跑到清單很下面。所有兵科、所有 Mk / 進化型都一樣。現在 class id 依「底盤線」連號（Hawk 201、Hawk-MK2 202 … MK5 205、Pelican 206 …；Mk6–9 仍共用 Mk5 的 id；生物依進化順序）。配合 F33 只顯示擁有的型號。
- **研究所只顯示自己有的單位（16:32，伺服器端，取代 F33）**：反組譯確認研究所左側清單只用 0x44 的**第一份名單**（class id + 名稱；00449cc0 / 0044a560 建樹、005c6390 名稱→id，只有研究所用），工廠和單位用第二份 0x68 紀錄。所以第一份名單只放玩家擁有的型號，紀錄保持完整（`build_unit_catalog(owned)`、`send_unit_catalog()`）。送出時機：登入（0x46）、進研究所（0x33 op 1，擁有的型號有變才送）、研究所升級成功前（新型號要先在名單裡）。工廠開著時不送（買的新單位下次進研究所出現）。測試 test50。
- **「此單位無法在此星球升級」（16:41）**：16:06 的去重把「已擁有的型號」從其他單位的升級選項拿掉 → 第二台戰鴿沒有 MK2 選項（甚至沒有任何選項），客戶端就顯示這句。已改回：每個擁有的型號都列出完整選項（重疊只來自已移除的深層鏈）。這句本身是原版訊息（kGraphCantUpgrade），已到最高 Mk / 最後進化階段的單位仍會顯示。
- **升級樹（16:48）**：每個框架的**根**＝工廠賣的基礎底盤（Mk1）：可以沿自己的 Mk 線升，或分支成框架內任一其他底盤；**其他底盤與所有 Mk2+ 只能沿自己的 Mk 線**（`_FRAME_ROOTS`）。生物進化不變。
  | 框架 | 根 → 分支 |
  |---|---|
  | Geo-frame | Imp → Imp-MK2 / Daeva / Mephit |
  | Cyclo-frame | Wraith → MK2 / Spectre / Liche |
  | Aero-frame | Shade → MK2 / Banshee / Phantom |
  | Gaia-frame | Ghast → MK2 / Revenant |
  | Ghost-frame | Spirit → MK2 / Apparition |
  | Sci-frame | Sapper → MK2 / Medic / Virus |
  | Magna-frame | Wight → MK2 |
  | Aero-rig | Pegasus → MK2 / Gryphon |
  | Cyclo-rig | Manticore → MK2 / Chimera / Hydra |
  | Flak-rig | Arbalest → MK2 / Ballista / Trebuchet |
  | Geo-rig | Behemoth → MK2 / Leviathan |
  | Gyro-rig | Red-Eye → MK2 / Gear-Doc / Orbus |
  | Sci-rig | Triage → MK2 / Volte / Mantlet |
  | Cyclo-raptor | Hawk → MK2 / Owl / Falcon |
  | Gaia-raptor | Eagle → MK2 / Phoenix / Condor |
  | Geo-raptor | Pelican → MK2 / War Pigeon / Vulture |
  | Gyro-raptor | Roc → MK2 / Albatross |
- **部署（17:01）**：客戶端指令表 0069b9a0（0x48 一筆；指令 id = 索引 + 4），按鈕由 004d49a0 依能力位開：Install 31 → 4/5；bombArd 21 → 6/7；Flak Attack 37 → 35/36；Heal install mode 56 → 60/61；sHield install 43；Unit / Energy production 53 / 54；sNipe 46。
  - 自走砲（Arbalest / Ballista / Trebuchet）**不再給通用 Install**，用武器 / 砲彈帶的 bombArd、Flak Attack 部署。
  - 野戰醫院改用原版的「U Heal install mode」（位 56），不給通用 Install；能量 / 效果取自它的治療或修理物品（帶哪個技能就是哪個）。部署後在平台上的治療 / 修理與動畫由客戶端處理（待遊戲內確認）。
  - 重弩 Flak Attack 打的是地面上的一點，客戶端用**對地射程**判斷距離，以前防空武器的對地射程送 0 → 打不到；現在 Air Bombard 武器的對地射程 = 對空射程（含感測器加成）。
- **技能稽核（17:07）**：能力位 → 指令（004d49a0；unit+0x15c = u64 的高 32 位）：Fusion Storm 50、IRBM Defense 49、Detect 45 = tachyon sWeep、Snipe 46、Unit production 53、Energy production 54、Heal install 56、Bunker 57、Virus kill 58、Virus attack 59、Overload 60、Frenzy 61、Shield install 43、Flak 37、Link Gate 39、Warp 52、Earthquake 48、Altcharge 36、Chemical mine 47、Carpet bomb 40、Booster 38、Defense field 41、Flare 42。
  - 修正：Wight 的 Overloader M1 / M2（「武器冷卻減少 30% / 60%」）原本沒有任何技能 → Overload（位 60），並列入 Wight 的預設裝備；Vulture（bombArd）、Apparition（sNipe）、Orbus（sHield install）用自己的部署指令，不再給通用 Install。Red-Eye（雷達 / 識別）、Condor（掃雷器）是「部署後才能用」的技能，保留 Install。
  - 待遊戲內確認、未改：Volte（說明是補充能量 → 原版可能是 Energy production mode 54）、Mantlet（步兵碉堡 → Bunker 57）、Virus（感染爆炸 → Virus attack 59 / kill 58，目前用 Virus Decay 武器攻擊）、Imp / Spirit / Spectre 的通用 Install 用途不明；生物各系的特殊器官（Manta 偵測眼、Slanth Air Lob / 射程延伸、Oizys Angel Harness / Bulwark Wing / Acid Burn、Poda Acid Pod / Corrosive Burn，客戶端都有名稱）尚未加入。

### 2026-10-24 補充（按技能表落實）
- Volte：去掉通用 Install，改為 E = Energy production（bit 54，數值取自 Refuel 道具 15）。
- Mantlet：R = Bunker（bit 57）。
- Virus：V = Virus attack（bit 59）、D = Virus kill（bit 58），數值取自武器耗能 / 對地傷害。
- 有機特殊器官（type 8，Organic Specials）：Oizys Bulwark Wing 2976（+600 HP）；Manta 偵測眼 6924/6948/6928/4924/4948/4928/4862（Detect，150 kJ/s，TL30/TL60 進階）。說明文字 EN/TW/CN 已加入 hlp。
- 仍未做：Acid 系道具、Air Lob、Range Extender、Manta Cloak。
- **（17:27）升級後新型號不在研究所**：Triage → Volte 後研究所看不到 Volte／Mantlet。原因：研究所升級（0x33 op 5）沒有重送 0x44 第一份名單，新型號不在名單裡；只有裝備（op 3）和進研究所（op 1）會送。已在 op 5 的成功結果前補上 `send_unit_catalog(s)`。test50 第 62 項。
- **（17:35）Volte 能量生產**：反組譯確認 E = Energy production mode 進入狀態 55；Refuel（加能量）動作 004dca20 只在「已部署（狀態 6）或能量生產模式（狀態 55）」時可用，是點選友軍施放，不是範圍自動補。Volte 原本沒有 Refuel 道具 → `STOCK_SKILL` 加 `"g055": (15,)`（Surge Coupler），`skill_mig` 3 讓既有 Volte 補一次；`add_stock_skill` 放不下時依序拿掉裝甲／感應器／雜項、換大電腦，最後才拿武器。test50 第 63 項。
- **（17:35）Mantlet 部署**：R = Bunker（位 57）。
- **（17:36）砲兵開迷霧**：迷霧繪製 0048ea50：bombArd 模式（狀態 9，解除送動作 9）與 Flak Attack 模式（狀態 11，解除送動作 34）以「單位視野半徑 +0x114」在「前方一個對地射程 +0x138」處開一個圓（004c5500 / 004c7700）。Trebuchet 視野 0、沒有砲兵感應器欄 → 半徑只有 1 m。砲兵（Arbalest／Ballista／Trebuchet）視野至少 7 m（= Arbalest 2 m + TACS M1 5 m）。Ballista 防空砲以前對地射程 0 → 開圈在自己身上；17:01 已改為用對空射程。test50 第 64 項。
- **（17:58）魔星專屬怪物**：客戶端未使用的美術依使用者指定改為魔星（`social.STAR_MAP` 400000004）專屬外星怪，其他星球、省份、洞穴都不出現。`aliens.py` `STAR_SPECIES` / `ROLES`：地面 Spitter g026（遠程）、Ripper g031（近戰）、Stinger g033、Scorpid g047、Arachnid g048、Rayoks g050；空中 Charnal a020、Miasmal a012；最後一波王 Miasam a019。魔星用洞穴 3 的等級加成、空中隊 35%。中文名在 `unitnames.py`（噴吐獸、撕裂獸、刺蟲、魔蠍、魔蛛、雷奧克斯、魔龍、瘴蛛、瘴母）。數值為佔位。test50 第 65 項。
  - 待決定：洞穴孵化巢（Hive）目前也用 g026 美術，與魔星專屬衝突。
  - 其他未用美術：Abomination g049、Dythe a021、Charise a022、Vytyr g052、Jorias g022、a003、a025、g007、g053、d001、h001–h011。
- **（18:05）取消孵化巢**：洞穴（CAVE 1–3）不再放孵化巢，也沒有小地圖巢標記。開場放一半怪；之後每 `HIVE_SPAWN_SECONDS`（25 秒）在離玩家單位 ≥800 px 的隨機出生點冒出 `streams` 隊（原本巢的數量，多人時增加），直到本次總數（budget）用完。勝利條件改為「總數全部出現且全部死亡」（battlefield `hive` 規則看 `budget`）。魔星仍是 3 波 + 瘴母王。測試 test19（改寫）、test16 第 3 段（改寫）。
- **（18:25）Mantlet 改回 Install 部署**：客戶端 004d49a0（004d53a5）：能力位 57 不產生獨立按鈕，而是把指令 63「B Dispose bUnker」放進指令 4（Install）的清單＝已部署狀態的指令。所以 Mantlet 用 I 部署，部署後變碉堡（004cfe16 設 +0x1e），出現 B 解除碉堡；Install release 帶位 57 會先把裡面的單位放出來（004da079 → 004d9530）。指令 62「R Bunker」不是由位 57 打開（推測是步兵進碉堡用，待遊戲內確認）。test50 第 66 項。
- **（19:10 遊戲內確認）Mantlet**：按 I 部署成碉堡、步兵能進入、按 R 能正確退出。

- **（19:16）Wight / Quorg 照原版取得**：原版（wiki）：與轉生無關，聊天框輸入 `/wight`（250 鈾）或 `/quorg`（800 鈾）在工廠解鎖。現在：`/wight` 顯示價格，`/wight yes` 付鈾解鎖（存在 commander `unlocked`）；解鎖前工廠不列出、購買被拒；解鎖後用一般資源價格購買、不限數量。已經擁有該單位的帳號視為已解鎖。test50 第 67 項。轉生（原版）：+2 單位上限、+2 永久屬性點等，與這兩隻單位無關。
- **（20:23）有機單位進化後中文名**：`unitnames.py` 補上其餘有機基底（Boreas 玻瑞阿斯、Crudgin 克拉金、Eris 厄莉絲、Haltyr 哈泰爾、Knell 奈爾、Kritsk 克里斯克、Lyssa 莉莎、Mlortha 姆洛薩、Momas 莫瑪斯、Onnir 奧尼爾、Rouke 魯克、Scave 斯凱夫、Tyr 提爾、Abomination 憎惡體）與五個進化階段（Prima/Primus 初階、Ampla/Amplus 進階、Magna/Magnus 強化、Maxima/Maximus 極致、Extrema/Extremus 究極），例：Oizys-Magna → 歐伊茲強化。單位表 405 個型號繁 / 簡全部有中文。hlp_tw / hlp_cn 已重建。
- **（21:24）有機單位的器官變成真正的道具**：客戶端研究所的數值（火力、射程、裝甲、冷卻）是由「已裝備的道具」算的，以前天生武器 / 外皮只在伺服器加成 → 顯示 0。現在 `with_alien_engine` 自動裝上：Alien Biodrive + 天生武器 W-3LL-ttt（id = 客戶端 InfoTbl 的 30100…30718，原版說明文字）+ 外皮 A-3LL-ttt（id 31100…31718），等級（organ_tier）隨單位等級 / 進化階段。不賣、不進倉庫、不退款（price 0），研究所設計中出現也不算購買。進化（fit_after_upgrade）後換成新形態的器官。伺服器的虛擬加成在有器官道具時停用（數值與以前相同，另 +150 HP 為 Biodrive）。
