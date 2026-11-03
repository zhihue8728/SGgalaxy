# 12 單位・裝備・技能・武器動畫 總整理（2026-10-24）

> 一份看完就知道：單位從哪來、能裝什麼、裝備給什麼屬性和技能、武器長什麼樣、技能怎麼生效。
> 標記：**[原版]** 對照客戶端反組譯或官方手冊確認；**[推定]** 有根據但未完全確認；**[佔位]** 原版數值找不到，暫用。
> 詳細逆向紀錄：01（客戶端地址）、06（裝備）、07（單位）、`claude/ATTACK_FX.md`、`SKILLS_EQUIP_AUDIT.md`、`ITEM_EFFECT_AUDIT.md`、`DAMAGE_ARMOR_DESIGN.md`、`TRANSPORT_SHIELD_ENERGY.md`。

---
## 1. 整體資料流
```
官方手冊 units_manual.json ─┐                 ┌─> 0x44 單位表（名稱、美術、載重/空間）
客戶端 equip.txt → unit_slots.json ─┤  伺服器   ├─> 0x2f 工廠（基礎單位、價格、影響力）
hlp.dat → items.json（1590 件）────┤  計算     ├─> 0x10 物品資料庫（Lab 顯示、裝備合法性）
damage_types.py（傷害×護甲表）────┘           └─> 0x18 PUT_UNIT（戰鬥真正用的數值與技能）
```
- **戰鬥中客戶端只用 PUT_UNIT 的數值** [原版]：HP、能量、能量回復、速度、視野、9 個戰鬥數值、能力位、技能清單。物品資料庫只用在 Lab 顯示和裝備合法性檢查。
- 所以「裝備有沒有效」= 伺服器有沒有把它換算進 PUT_UNIT。

---
## 2. 單位
### 2.1 兵科與框架 [原版：手冊]
| 兵科（工廠分頁） | 框架（frame） → 底盤（Mk1 影響力） |
|---|---|
| 步兵 INF | Geo-frame：**Imp 1** → Daeva 34 → Mephit 55；Cyclo-frame：**Wraith 2** → Spectre 36 → Liche 50；Sci-frame：**Sapper 2** → Medic 7 → Virus 32；Aero-frame：**Shade 3** → Banshee 25 → Phantom 36；Gaia-frame：**Ghast 3** → Revenant 48；Ghost-frame：**Spirit 10** → Apparition 50；Magna-frame：**Wight 35**（鈾購買） |
| 機動 MOB | Aero-rig：**Pegasus 1** → Gryphon 35；Gyro-rig：**Red-Eye 1 / SatCom 1** → Gear-Doc 22 → Orbus 26；Geo-rig：**Behemoth 2** → Leviathan 40；Cyclo-rig：**Manticore 3** → Chimera 25 → Hydra 47；Sci-rig：**Triage 5** → Volte 25 → Mantlet 50；Flak-rig：**Arbalest 14** → Ballista 30 → Trebuchet 50 |
| 航空 AVI | Cyclo-raptor：**Hawk 2** → Owl 30 → Falcon 60；Geo-raptor：**Pelican 4** → War Pigeon 16 → Vulture 55；Gaia-raptor：**Eagle 7** → Phoenix 30 → Condor 35；Gyro-raptor：**Roc 10** → Albatross 25 |
| 生物 ORG | 依手冊的 UQ 進化（第 9 節）：Oizys → Boreas → Eris → Lyssa；Ubik → Tyr → Haltyr；Slanth → Crudgin → Rouke；Poda → Kritsk → Mlortha；Manta → Onnir；Larva → Scave → Knell；Mamos（Momas，UQ 80 起）；Quorg（鈾購買，UQ 30/60/90/120 進化） |

粗體 = **工廠販賣的基礎單位**（每個框架影響力最低者）。

### 2.2 取得與升級規則（2026-10-24 使用者確認）
- **工廠**：只賣基礎單位＋生物 / 付費單位。需要影響力 = 兵科等級 + Clout ÷ 2。客戶端會把影響力不夠的單位變灰並拒買（0x2f 每筆 byte：你的影響力 / 需要的影響力）[原版]。
- **研究所（只能往上）**：下一個 Mk，或同框架中影響力更高的底盤。條件：單位品質 UQ（單位等級 + Clout ÷ 2）≥ 目標的手冊影響力。保留等級；新底盤沒有的欄位裝備自動拆下並退半價。
- **Mk 等級**：**Mk1–Mk9 全開**（`MK_MAX = 9`，14:20）。封包大小不是限制（第 8 節）；每頁 99 個 class id 的限制用「Mk6–Mk9 共用同底盤 Mk5 的 class id」解決（客戶端只用 class id ÷ 100 決定分頁，其餘都用名稱），不需要客戶端補丁。若研究所樹顯示異常，`MK_MAX` 改回 5。
- 價格 [設計值，見第 9 節]：依各底盤的手冊數值計算；研究所轉換 = 價值差的一半（至少目標的 1/4）；Wight / Quorg 照原版：聊天輸入 /wight（250 鈾）、/quorg（800 鈾）一次性解鎖，之後在工廠用一般資源購買、不限數量（2026-10-24 19:16）。

### 2.3 底盤數值 [原版：手冊]
每個底盤、每個 Mk：HP、護甲、速度（m/s）、視野（m）、最大載重、最大空間、單位重量。伺服器直接用手冊值（名稱不分大小寫對照）。

### 2.4 能裝什麼 [原版：客戶端 equip.txt]
每個底盤 8 種欄位：1 引擎 / 生物驅動、2 儲能、3 電腦、4 武器、5 護甲、6 彈藥 / 地雷、7 雜項（感應器等）、8 特殊。欄位代碼 = 類型 × 1000 + 編號，物品的欄位代碼必須等於底盤的欄位代碼（例如 Chimera 武器欄 4108）。同一框架的不同 Mk 用同一套欄位。

---
## 3. 裝備
### 3.1 物品資料庫（items.json，1590 件，來自 hlp.dat）
| 類型 | 數量 | 給什麼 |
|---|---|---|
| 1 引擎 / 生物驅動 | 129 | HP、功率（決定能不能動）、部分給 Speed Boost |
| 2 儲能 | 75 | 能量上限、充能方式（太陽 / 核能 / 電池 / 甲烷）、部分給 Self Destruct |
| 3 電腦 | 13 | 最大複雜度、XP Bonus |
| 4 武器 | 865 | 對地 / 對空：傷害、射程、冷卻、每發耗能；傷害類別 |
| 5 護甲 | 164 | HP、護甲值、**護甲類**（決定抗性） |
| 6 彈藥 / 地雷 | 67 | 地雷技能、Trebuchet 砲彈 |
| 7 雜項 | 136 | 感應器（視野、加射程）、醫療包等 |
| 8 特殊 | 141 | 技能（隱形、傳送、護盾…） |
- 欄位 [原版]：名稱、id、欄位、科技等級、重量、空間、複雜度、能量、類型、類型專屬欄位。圖示 `Item-%03d`。

### 3.2 裝備合法性（派兵視窗會拒絕） [原版]
沒裝備；沒引擎；科技等級 > 單位等級 + Education ÷ 2；總重量 / 空間超過底盤；總複雜度 > 電腦上限；裝在底盤沒有的欄位或同欄位兩件。→ 新單位自動給**標準配裝**（引擎、儲能、電腦，放得下再加武器、護甲、感應器）。

### 3.3 裝備怎麼變成戰鬥數值
| PUT_UNIT 欄位 | 來源 |
|---|---|
| 最大 HP | 底盤 + 引擎 + 護甲 + Biostimulator（+300）[原版] |
| 能量上限 / 每秒變化 | 儲能；每秒耗能 = 道具 Energy Drain 總和（只有 Fallout 反應爐會回能）[原版] |
| 速度 | 底盤手冊速度；Booster 技能 ×(100+POWER)/100 [原版] |
| 視野 | (底盤視野 + 所有道具 View Range + Biostimulator 0.5) × 20 px；**只能打視野內的目標** [原版] |
| 9 個戰鬥數值 | 護甲值、護甲類、傷害代碼、對地傷害 / 射程×20 / 冷卻×100、對空同上 [原版格式] |
| 射程加成 | 非武器道具的 Ground/Air Range 加到有傷害的那一面 [原版說明] |
| 能力位 + 技能清單 | 見第 4 節 |

### 3.4 傷害公式與護甲類 [原版]
`傷害 = max(1, 武器傷害 − 護甲 × (100 + 表[護甲類][傷害類]) ÷ 100)`
- 傷害類 7 種：無、彈道、飛彈、火焰、雷射、穿甲、爆炸（由武器說明判斷）。
- 護甲類 26 種：chassis、ablative、kevlar、hybrid、morganan、steel、phasic、tantalum carbide、alien composite、生物系（derma、sheathing、husk、grafted）、Mantlet 三種、aircraft hull、Hafnium 四種盾、四魔星、alien carapace。**表中數值 [推定]**（`DAMAGE_ARMOR_DESIGN.md`）。
- 武器數值（傷害 / 射程 / 冷卻 / 耗能）= hlp.dat 原版說明。
- **穿甲加強（14:30 使用者選 A）**：穿甲這一欄改成多數護甲只算 10–25%（鋼、凱夫拉、消融、機體、飛機機體 −90；混合、相位、碳化鉭、Mantlet −85；Morganan、外星複合、生物系、Hafnium 盾 −75；能量場、魔星護甲 −50）。原因：客戶端每一發都先扣護甲，Falcon 這種每 0.3 秒一發、每發 6–49 的穿甲武器被削到 1–4 點。模擬（NPC 標準裝備，每秒實際傷害）：Falcon 單位等級 30 打 Eagle 15 → 28、打 Leviathan 3.3 → 21.7；單位等級 60 純對空約 146–153。影響全部 265 把穿甲武器（Phantom、Falcon、Mephit、Leviathan、Gryphon、Eagle 的部分武器）。精英級 AI 對戰勝率 73%（30 場，正常範圍）。
- **資料修正**：Surge AK256 Cap（+ Gold）對地射程原資料 0.1 m（明顯打錯），改為 14 m（同對空射程與 H- 版）。

### 3.5 商店規則
一般物品（基礎 / H- / L- / A- / AH- / E- / I-）：任何研究所，限科技等級。GOLD：限定清單。魔星：本國魔星時間才賣。Redcoat：活動期間。Alien Biodrive 永不出售。價格 [佔位]。

---
## 4. 技能
### 4.1 技能從哪來 [原版機制]
- 物品的 Special 文字 → **能力位**（`SPECIAL_BITS`），能力位 → 指令按鈕（客戶端 004d49a0）。
- **底盤自帶技能只剩兩個**（14:06 決定依裝備、14:18 例外保留）：Gear-Doc 自帶 Repair（最低的修理道具要科技 45）、Daeva 自帶 Grenade（手榴彈超過它的載重）；其他全部依裝備。支援單位新買時，標準配裝會含角色道具（`STOCK_SKILL`：Triage Regen、Medic 醫療包、Gear-Doc 修理、Orbus 傳送、Sapper 地雷、Daeva 手榴彈，放得下且科技等級夠才給）；已有的單位登入時補一次。NPC 依角色配裝（治療、修理、傳送、護盾、偵測）。
- **安裝 / 部署（位 31）**（14:34 起）：有安裝美術的底盤一律可以部署（Triage、Mantlet、Volte、Orbus、Red-Eye、SatCom、Arbalest、Ballista、Trebuchet、Imp、Spectre、Spirit、Apparition、Condor、Vulture…）；沒有安裝美術的不給（會隱形卡住）。部署後的額外效果（例如治療範圍）尚未從客戶端確認。
- 只能「安裝」狀態使用：Mine Detector、Radar Jammer、Identify、Radar、Link Gate（要能力位 31，且底盤有安裝美術：Red-Eye、SatCom、Imp、Spectre、Arbalest、Ballista、Orbus、Trebuchet、Spirit、Apparition、Volte、Triage、Mantlet、Condor、Vulture…）。
- 位 1 = 攻擊（要有傷害）；支援單位不給攻擊位。
- PUT 技能清單：`{能力位, A 能量, B 威力}` = 物品的 Energy Use / Effectiveness [原版]。A = 單次耗能（一次性技能）或每秒耗能（開關型）。

### 4.2 能力位對照（SPECIAL_BITS）
| 位 | 技能 | 位 | 技能 | 位 | 技能 |
|---|---|---|---|---|---|
| 3 | Anti-Grav Harness | 15 | Refuel | 34 | Camouflage |
| 4 | Self Destruct | 16 | Mine Detector* | 35 | Allow Phase（被動） |
| 5 | Disguise | 17 | Radar Jammer* | 36 | Altcharge（空雷） |
| 6 | EMP Grenade | 20 | Repair | 37 | Air Bombard |
| 7 | Mind Warp | 21 | Bombard | 38 | Speed Boost / Booster |
| 8 | Grenade | 22 | Charge Mine | 39 | Link Gate* |
| 9 | After Burner | 25 | Heal | 40 | Carpet Bomb |
| 10 | Neutron Shield | 26 | Teleport Unit | 42 | Flare |
| 11 | Sensor Evasion | 28 | Transport Unit | 43 | Shield |
| 12 | EMP Attack | 29 | Identify* | 45 | Detect |
| 13 | Charge EMP Mine | 30 | Radar* | 46 | Snipe |
| 14 | Cloak | 32 | Short Circuit | 47 | Chemical Mine |
| 48 | Earthquake | 49 | IRBM Defense | 50 | Fusion Storm |
| 33 | IRBM | 52 | Warp | 31 | Install（安裝） |

\* 只能安裝狀態使用。

### 4.3 技能效果（客戶端執行器，技能傷害**無視護甲**）[原版]
| 技能 | 效果 |
|---|---|
| Grenade | 目標 −威力，目標 128 px 內所有單位 −威力/2 |
| Earthquake | 施放者視野半徑內所有單位（除自己）−威力 |
| Self Destruct | 280 px 內 −威力，自己死亡（威力 930；Acid Bura 死亡時自動觸發，F21） |
| IRBM | 10 秒後落點 210 px 內 −威力 |
| Fusion Storm | 目標 −最大 HP × 威力 % |
| EMP Attack / EMP Grenade | 只扣能量 |
| Mind Warp / Short Circuit | 癱瘓目標 威力 時間 |
| Heal / Repair | 每秒回復（生物用 Heal、機械用 Repair；同一單位共用數值欄位） |
| Booster | 速度 ×(100+威力)/100（威力 = 說明中的 %，沒寫用 45） |
| Radar Jammer | 干擾敵方小地圖（威力當開關，至少 1） |
| Cloak / Camouflage / Sensor Evasion / Disguise / Neutron Shield / Anti-grav | 開關型，每秒耗能；隱形單位只能被手動指定攻擊（NPC 需開啟 Detect 才會打）[鎖定] |
| Teleport / Link Gate | 只傳送有 Allow Phase（位 35）的單位 |
| Transport | 伺服器追蹤狀態（`TRANSPORT_SHIELD_ENERGY.md`） |
| Shield（護盾，Red-Eye 的 Shield Generator TL50 / Orbus 的 B Shield Generator TL75） | 原地形成半徑 160 px 的護盾，每秒耗能 200 / 150。客戶端 004d0420 → 004d01a0：**攻擊者與目標都是地面單位、且不在同一個護盾裡 → 一般武器傷害 0**，與傷害類別無關（飛彈、雷射、彈道、自走砲的一般射擊都擋）；外面打不進、裡面也打不出。**不擋**：空中單位打的、打空中的、技能傷害（手榴彈、IRBM、Earthquake 等直接扣 HP）。安裝狀態時不能開。 |
| Bombard / Air Bombard / Carpet Bomb / 地雷 | 範圍傷害，半徑 = 攻擊者視野；擊殺由客戶端回報 |
- 伺服器對**外星怪**要自己模擬技能傷害（外星怪由伺服器判死），用同樣規則（`on_skill`）。共用冷卻 200 tick。反作弊：單位沒有該能力位不能用技能。

---
## 5. 武器動畫與命中特效
### 5.1 客戶端規則 [原版]
- 武器外觀碼 = PUT 數值[2] = **傷害類 × 100 + 圖編號**；類別同時決定外觀和傷害欄。
| 類別 | 飛行物 | 命中特效 |
|---|---|---|
| 0 無 | 無 | 依單位美術：ef-dmga / ef-dmgb / explD / explC，其他沒有 |
| 1 彈道 | 曳光線（碼 1TW：T 顏色 0 灰 1 橙 2 綠 3 藍，W 寬 1–9） | explG |
| 2 飛彈、5 穿甲、6 爆炸 | `m%03dk.xpf` 飛行、`m%03df` 尾焰、`m%03dke` 爆炸（m001–m044） | — |
| 3 火焰 | `ft%03d.xpf`（ft001–003） | ef-ftr |
| 4 雷射 | 光束 + `lsp%03d.xpf` 火花 | — |
- 單位圖：`<g|a|h><編號><動作><層>.xpf`；動作 st 站立、mo 移動、at 攻擊、da 死亡…；攻擊圖有槍口點，投射物從那裡射出。

### 5.2 目前的對應
- **彈道** [推定]：傷害 < 150 灰色細線；150–449 橙色 2 寬；≥ 450 橙色 3 寬。
- **飛彈 / 穿甲 / 爆炸 / 火焰 / 雷射** [佔位]：原版每把武器用哪張圖不明，同一系列武器（含 H- / L- / Gold）固定挑一張現有的圖：飛彈 13 張、穿甲 3 張（10、12、14）、爆炸 3 張（4、8、11）、火焰 3 張、雷射 2 張。
- **外星怪** [使用者決定]：飛彈類＋綠色酸液圖（Ubik 205、Slanth 209、Poda 206、Larva 207、Oizys 231、Manta / Mamos 230）。

---
## 6. 已知缺口（依影響排序）
1. **Mk6–Mk9** 未開放：工廠每頁最多 99 種的限制（Mk1–Mk5 已開放，待遊戲內確認）。
2. **Mk6–Mk9** 已開放（共用 class id），**待遊戲內確認**研究所樹與升級畫面正常。
3. **武器圖編號**：除彈道外都是佔位。
4. **傷害×護甲表數值**是推定（公式是原版）。
5. **Trebuchet 砲彈與所有價格**：原版查不到，改為依特性設計（第 9 節）。
6. 0x16 單位紀錄、0x10 物品資料庫還有幾個不明欄位（只影響 Lab 顯示，見協定稽核 B 節）。

## 7. 相關程式
| 主題 | 位置 |
|---|---|
| 單位表、工廠、升級路線 | `server/sgs/units_items_lab.py`（`UNITS`、`upgrade_options`、`build_unit_shop`、`build_unit_catalog`） |
| 裝備合法性、標準配裝、戰鬥數值 | `units_items_lab.py` / `commander_deploy.py`（`equip_problems`、`stock_loadout`、`unit_stats9`） |
| 技能、能力位、技能效果 | `server/sgs/battle_rules.py`（`SPECIAL_BITS`、`CHASSIS_SKILLS`、`ACTION_BIT`、`on_skill`） |
| 傷害類、護甲類、武器外觀碼 | `server/damage_types.py` |
| 中文名 | `server/unitnames.py`、`item_names_zh.json` |
| 測試 | `tools/mptest/test50.py`（單位架構）、`test18`（Acid Bura）等 |

---
## 8. 查證結果（2026-10-24 13:48）
| 項目 | 查證方式 | 結果 |
|---|---|---|
| 單位表封包大小（Mk3 以上） | 反組譯客戶端收包 | **不受限**：接收緩衝 256 KB（`005a8a80` 0x40000）、每個封包依長度配置解密緩衝（`005a9424` malloc(長度×2+10)）、單位表存成可增長的陣列（`005c8ff0`）。上限只有 u16 長度 65535 與每頁 99 種 → **MK_MAX 改為 5**（13 KB）。 |
| 研究所的原版結構 | 客戶端字串 LABTEXT（ntt） | 1.8.5 的研究所只有兩個功能：左鍵「單位升級」（選單位 → 雙擊目標完成）、右鍵「裝備升級」。**沒有「New 從零設計」**（舊版手冊有）→ 「工廠賣基礎單位、其他在研究所升級」符合 1.8.5。另有字串 `kGraphCantUpgrade`「這個單位在這個星球不能升級」→ 原版升級**有星球限制**，目前沒有實作。 |
| 影響力 / 科技等級 / 機械能力 | 官方舊版手冊 s5、s6 | 影響力 = 兵科等級 + Clout÷2 ✔；可裝科技等級 = 單位等級 + Education÷2 ✔；Mech Apt 約每點 +1% 載重（120 點 = +100%）✔（我們是 ×(1+mech/120)）。手冊另說「影響力差 10 以內的底盤顯示為灰色可預覽」。 |
| 底盤自帶技能 | 對照各底盤欄位可裝的物品 | Daeva Grenade、Sapper Charge Mine、Liche IRBM Defense、Gear-Doc Repair、Orbus Teleport、Leviathan Neutron Shield、Volte Refuel、Triage Heal/Repair **全部都有對應裝備**（手冊：技能來自引擎、感應器、雜項等裝備）→ 原版應是「裝了才有」。**待決定**：拿掉 CHASSIS_SKILLS 會讓沒裝該道具的玩家單位失去技能（NPC 要改成配裝）。 |
| 治療 / 修理道具沒有技能 | 道具說明 | **已修正**：Medic 的 Tool Kit、Assembly Arm、Restoration Gear 等只有說明「repair damaged mechanical units」，以前只認名稱含 repair 的；Triage 的 Regen Pad / Pod / Foci / Aura / Field「回復生物與機械友軍」以前**完全沒給技能** → 現在給 Heal + Repair，數值用道具的 Energy Use / Effectiveness。 |
| 傷害 × 護甲表 | hlp 說明、官方手冊、網路 | **原版數值查不到**：表是伺服器在物品資料庫最後送給客戶端的，客戶端裡沒有；手冊只說護甲分「消耗型」與「偏折型」、Reflec 護甲擋雷射強（1.8.5 已無此護甲）；Hafnium 盾說明「開啟時無敵、不能佔 POC」。維持推定值。 |
| 武器動畫圖編號 | 客戶端 | **客戶端裡沒有對應表**：圖編號由伺服器在放單位時送（數值[2] % 100），原版伺服器資料已不存在，只能靠原版截圖 / 影片比對。 |
| Trebuchet 砲彈、價格 | hlp、手冊、網路 | 查不到數值。手冊只說「高影響力底盤購買與修理較貴」「高科技道具主要花資源、低科技主要花金錢」。 |

來源：官方舊版手冊 www.sgalaxy.com/manual/s5.html、s6.html；客戶端 `unpacked/ntt/LABTEXT.TXT`、`unpacked/hlp/*`。

---
## 9. 設計值（14:03 使用者：查不到原版的，依特性創建，要有獨特性、屬性合理）
### 9.1 價格（`server/pricing.py`）
- 資源價值換算：金錢 1、礦 4、矽 4、鈾 40、硫 8。
- **單位** = 18 ×（影響力 + 4）^1.3 + 0.05 × HP + 8 × 護甲 + 0.6 × 載重 + 15 ×（速度 − 3）。影響力越高金錢比例越低（80% → 35%），其餘依**框架**的材料分配：步兵多金錢、裝甲車多礦、電子 / 科學框架多矽、航空矽 + 鈾、砲兵硫。例：Imp 250 金 / 10 礦 / 3 矽 / 2 硫；Chimera 1150 / 83 / 28 / 0 / 14；Hydra 1855 / 214 / 71 / 0 / 36；Trebuchet 1890 / 129 / 64 / 0 / 97。
- **研究所轉換** = （目標價值 − 目前價值）÷ 2，至少目標價值的 1/4。例：Manticore → Chimera 425 / 31 / 10 / 0 / 5。
- **修理** = 價格 × 40% × 損傷比例；**賣出** = 半價（以前研究所取得的單位賣出拿不到錢，已修正）。
- **物品** = 類型係數 ×（科技等級 + 8）^1.35 ×（和同類型、同科技等級道具相比的強度比）^0.7；H- 版 ×1.8。金錢比例隨科技等級下降（85% → 25%，符合手冊「高科技主要花資源」），其餘依類型：彈道武器礦、飛彈 / 火焰 / 爆炸硫、雷射矽 + 鈾、穿甲礦 + 鈾、護甲礦（高科技護甲加矽、鈾）、核能引擎鈾、儲能 / 電腦 / 感應器矽、特殊道具矽 + 鈾。武器中位數：科技 0–19 約 170、50–69 約 1400、110+ 約 3600（換算金錢）。
- **Gold** = 一般價 × 2.5；**魔星** = × 3 + 20 鈾 + 100 硫；**Redcoat** = × 2。
### 9.2 Trebuchet 砲彈（發射器決定射程、冷卻 2 秒；砲彈決定傷害）
同科技等級每秒傷害約 Arbalest 迫擊砲的 1.3–1.6 倍，代價是能量和重量；可同時裝迫擊砲彈（對地）和防空彈（對空）是它的特色。
| 砲彈 | 科技 | 傷害 | 能量 | 重量 / 空間 | 特色 |
|---|---|---|---|---|---|
| Astral Ram | 2 | 170 | 40 | 14 / 5 | 標準彈 |
| Astral Maul | 20 | 225 | 60 | 22 / 7 | 重擊 |
| Astral Toss | 45 | 200 | 35 | 10 / 4 | 輕量遠拋 **射程 +6 m** |
| Astral Slam | 75 | 300 | 85 | 28 / 9 | 攻城（最重、最耗能） |
| Astral Jolt | 105 | 290 | 50 | 16 / 6 | 高科技高效 **射程 +4 m** |
| Astral Flak（防空） | 10 | 160 | 70 | 20 / 6 | 近炸引信 **對空射程 +5 m** |
H- 版：傷害 +30%、能量 ×2、重量 ×1.8、複雜度 +4。
### 9.3 生物進化（手冊原版資料）
每一階段有 UQ（取代影響力）：一般線 Primus 0 → Amplus 10 → Magnus 20 → Maximus 30 → 下一種 Primus 40 … 最高 120。研究所一次升一階，條件 UQ（單位等級 + Clout ÷ 2）≥ 目標 UQ。手冊沒有提到要魔星才能升級。工廠仍賣第一階（Mamos = Momas-Primus 需要 UQ 80）。Evo 系列（Jorias、Vytyr、Charise、Dythe、Miasmal、Miasam、Charnal、Rayoks）來源不明，未加入。
### 9.4 升級與角色屬性
UQ = 單位等級（最高 60）+ Clout ÷ 2（Clout 最高 120）→ 屬性越高能升到越高的 Mk / 進化階段；轉生角色每次多 2 點屬性。Mk 已開到 Mk9（最高影響力 114–120），屬性高的轉生角色可以升到最高階。
