# 尚未實作的客戶端功能清單（2026-10-20 盤點）

方法：send_catalog.tsv（客戶端 250 個發送點）逐一對照 sgserver.py 已處理的封包；strings.txt 的 ks*/khi* 介面字串；
Ghidra 列出所有 RTTI 視窗類別的虛函數（slot 7 = +0x1C 封包處理）。

## 重要發現：封包走哪裡
- 戰場/全域封包：FUN_0054a590 → 全域 → 戰場 → 各視窗 slot 7。**只有少數視窗有 slot 7 處理**：
  CCtrlChatting（'*' 0x2a → 00439bb0）、CHallOfFameDlg（0x12 → 004f8820；'=' 0x3d → 004f7240）、
  CRoyalRumbleWnd（'5' 0x35 → 00587c70）。
- **信件（CMailDlg）與公告板（CBBSDlg）是 HTTP 網頁**：lsbbs01.asp / lsbbs01_t.asp / rmbbs01.asp / inbbs02.asp …（HTML 由 CMLViewer 顯示），
  基底網址來自客戶端設定（0xfe config 或 bbs.sgalaxy.com），需要另外做一個 HTTP 服務，不是遊戲封包。
- 這些功能的遊戲封包（客戶端發送、伺服器尚未處理）：
  | 功能 | 客戶端 type（發送點） |
  |---|---|
  | 聊天 | 0x2a【已完成】 |
  | 國家選舉/政策/外交（Vote、Domestic/Foreign Policy、Board=戰況、稅 khiTax、FHQ 領袖控制台） | 0x36（12 個發送點，最大宗）、0x32、0x34、0x35、0xce、0xcf、0xc0–0xc3 |
  | 師徒 Pyramid（導師/學生、經驗分配） | 0x55、0x5c（f4-bk 介面）、InviteStudent |
  | 好友 / 玩家資料 UserInfo / 搜尋玩家 | 0x22?、0x57、0x43 |
  | 名人堂 HallOfFame | 回應 0x12、0x3d；請求 0x3c/0x3d? |
  | 資源交換 Exchange（ExchangeRate0-3）、物品交換 CItemExchangeDlg | 0x56?、0x5d、0x5e |
  | 皇家大亂鬥 Royal Rumble | 回應 0x35；請求 0x4d? |
  | 密碼變更 | 0x07 / 0xd4 |
  | 整合商店 CIntegratedShopWnd | 0x44? |
  | 戰報/戰況總覽 "OVERALL WAR STATUS" | 0x0d、0x13 |
  （問號 = 尚未用反編譯確認功能）

## 已完成
- FHQ 封包骨架（0x36 → 0x37）：投票窗（競選/取消/支持/反對/提名/投票/聲明，24 小時任期，到期自動當選）、內政窗（稅率/國庫/議會名單，唯讀）、外交窗（同星球各國列，聲明）。封包結構完全照客戶端讀取順序；**欄位語意（稅、各 u8/u16 的意思）是暫定，需要你在遊戲內進入 FHQ 截圖校準**。尚未做：外交提案（結盟/停火）、議會任命、稅對收入的影響、戰況總覽 0x0d/0x13。
- 聊天（0x2a）：公開（同地圖/戰場）、盟友、私聊、群組、離線提示；格式見 server `handle_chat`。尚未在遊戲內確認畫面顯示。

## 建議順序（每項：反編譯 → 實作 → 模擬客戶端測試 → 請你在遊戲內驗證）
1. 外交與戰況：0x0d/0x13 戰況總覽、國家關係（目前 NATION_ALLIES 固定）→ Foreign Policy 視窗。
2. 選舉：Vote 視窗（提名、競選、支持/反對、投票、任期），國家領袖與 FHQ 領袖控制台。
3. 稅與國內政策：Domestic Policy（khiTax）→ 影響 income_cycle。
4. 名人堂、玩家資料/好友、師徒。
5. 資源交換、密碼變更、整合商店。
6. 信件/BBS：HTTP 服務（asp 路徑對應），最後做。

## FHQ 投票（Vote）在 1.8.5 客戶端不可達（2026-10-20 反編譯確認）
- 大廳（CPreCityHallWnd 建立函式 56ea20）只建立 Domestic(0x11)、Foreign(0x12)、Exit(0x13) 三個按鈕；處理函式 56efc0 雖有 0x10=Vote，但沒有任何按鈕使用此 id。
- Domestic 視窗（47c360）處理 0x14=Vote、Foreign 視窗（4b9420）處理 0x17=Vote，但兩個視窗的建立函式（479e00、4b7fe0）都沒有建立這兩個 id 的按鈕，只有一條 id 0x13/0x16 的頁籤圖。
- 結論：投票視窗是客戶端內的殘留程式碼，遊戲內無法進入，「Vote 點不了」不是伺服器問題。選舉若要做，只能在伺服器端（GM 指令或定時結算），不需要再追客戶端 UI。
- 附帶：Foreign 視窗的聲明編輯鈕（id 0x13/0x14，fq-b-eda）只對總統（FUN_004ee6a0 且本人名字等於國家領袖）建立。

## 外交與戰況（2026-10-20 確認）
- "OVERALL WAR STATUS"（FUN_00435030）完全由客戶端用戰略地圖省份資料（0x2d）計算，**不需要伺服器封包**。
- 0x13 [u16]（登入時送出）與 0x0d [u16]（資料分塊請求，0xffff=完成）目前不影響畫面，伺服器忽略即可。
- 結盟/停火提案：客戶端**沒有**對應的發送點（ksTheyOfferRally* / ksWeOfferCF* 等字串沒有程式碼引用），1.8.5 不可操作。盟友關係只透過 0x05 關係表（build_relations）下發。
- 已實作：GM 指令 `/ally N`（與自己國家切換結盟/解除，存進 world.json "allies"，立即對所有在線玩家重送 0x05；新盟約只影響之後放下的單位）、`/president [名字]`（把自己國家的總統設為指定玩家，預設自己）。
- 已實作：總統在內政視窗儲存議會名單（0x36 kind 1 op 1：`[u8 n]` + n×`{u16 slot, s8, s8, s8, u32}`），伺服器存檔並回傳；非總統被拒絕。測試：tools/mptest/test10.py。
- 下一步：稅率/國庫對 income_cycle 的影響、名人堂、玩家資料/好友/師徒。

## 玩家名冊與名人堂（2026-10-20，待遊戲內驗證）
- 玩家名冊：客戶端以 (u32 uid, u16 k) 為鍵快取。客戶端 0x3c [u32 uid][u16 k] → 伺服器 0x3b 單筆；客戶端 0x3b [] → 伺服器 0x3a [u16 n]+n 筆。單筆 = `[u32 uid][u16 k][u8 a][s8 名字][u16 b][s8 c]`（a=國家、b=聲望，c 暫空；a/b/c 的畫面用途未確認）。uid = 帳號名小寫的 crc32 & 0x7fffffff。
- 名人堂 0x12 [u8 kind] → 伺服器 0x12 [kind][u16 n] 列。kind 1–4 列 = `u32 uid, u16 k, u8, u8, u8, u32, u32, u8, u16 勝, u16 敗`（kind 1 每列多一個 u16，並在最後多一個 u16 總數）。畫面（FUN_004f5a50）：第 1、3 個 u8 以 %d 顯示、第 2 個 u8 為短字串、第一個 u32 為數字、第二個 u32 除以 100 顯示、第 4 個 u8 小於 5 為圖示索引、勝/敗顯示成 "%5d /%5d" 並算勝率。kind 5/6 目前回空列表（版面已知，意義未知）。
- 目前 kind 1=按聲望、2=按勝場、3=按榮譽、4=按國家排序；欄位對應是猜測。GM 指令 `/hofdebug` 會把每個欄位換成容易辨認的標記值（u8=11/2/13、u32=100001/20000200、圖示=3、勝/敗=7777/8888），截圖後即可確認對應。測試：tools/mptest/test11.py。

## 密碼變更、宣誓（Word of Honor）、資源交換（2026-10-20）
- 密碼變更：登入畫面送 0x07 `[s8 帳號][s8 舊密碼][s8 新密碼]`，回 `02 00`（成功，客戶端顯示 "Successfully changed ...."）或 `02 01 [s8 訊息]`。**已實作**（test12）。0xd4 `[s8]` 是登入流程內部送出的字串，不需要回應。
- 宣誓系統（"Word of Honor"，上級/下屬，XP 加成）：客戶端送 0x55 `[u8 op=0][u8 0][s8 對象]`（宣誓）、`0x55 [2]`、`0x5c [0][s8]`、`0x5c [2][5×u32]`、`0x5c [3][u8]` 等多種子操作，伺服器回應的封包型別與格式**尚未找到**（0x55/0x5c 不在全域與戰場分派表內）。工程量大且需要兩個客戶端才能驗證，暫緩。
- 資源交換 0x5d/0x5e/0x56、整合商店 0x44、玩家搜尋 0x57：僅確認發送格式，回應未逆向，暫緩。

## 玩家资料、宣誓、玩家搜索、资源交换、战场图示（2026-10-20，已实现，待游戏内验证）
- **大地图战斗图示**：build_strategic_map 现在直接从 BATTLES 产生省份战斗区块（state 0=进行中，人数>=10 送 3=额满；1=开放/2=封闭 服务器暂无对应设定），剩余秒数至少为 1。
- **名人堂**：每列以 s8 名字开头（kind 1-4）。
- **玩家资料（别人的 F4 窗）**：客户端 0x23 [02][s8 名字]（名人堂/名册点击）或 [01][u32 id] → 服务器 0x27 sub 1：`[01][s8 名字][u8 国家][u32 uid][u16 k]` + 与 sub 0 相同的主体（s8 称号、u8、4×分支、u8 转生、3×u32、勋章）+ `[u16 胜][u16 败][s8 上级][u16 n][n 字节简介]`。（来自 FUN_004b4980 的 cVar3==1 分支。）
- **Word of Honor（宣誓，上级/下属）**：F4 窗按钮 0x1a/0x1b（窗口 vtable 0x661150）。客户端 0x55 `[00][00][s8 目标]` → 服务器向目标送 0x54 `[05][u8][s8 发起者]`（目标客户端弹出确认框，函数 4a9670）；目标回 0x55 `[03][u8 代码][s8 发起者]`（1 同意、0 拒绝、2..10 忙碌）→ 服务器给发起者 0x54 `[06][代码]`（代码 1 再加 `[s8 目标]`）；客户端等待 30 秒，超时显示 "They do not respond..."，所以一定要回复。释放：客户端 0x5c `[00][s8 名字]`。上级名存在 commander["superior"]，F4 窗显示 "Superior :%s"。**XP 加成尚未实现**（"fight with your Superior" 的加成）。
- 0x54 其他 sub（客户端 4ac000）：sub 0 `[u8][u8][s8 名字]` 好友列表加入/更新（4f32c0，列表项 0x58 字节）；sub 1 `[s8]` 移除（4f2120）；sub 3 开 "UseExpWnd"（经验分配窗，4a3520）；sub 5 `[u8][s8]` 弹出邀请确认；sub 6 `[u8 结果]...` 邀请结果。UseExpWnd / 师徒经验分配（客户端发 0x55 的 24 栏位大包 5de820）尚未实现。
- **玩家搜索**：客户端 0x57 `[s8 名字]`（WHO 窗搜索框）。回复格式未在客户端找到专用处理，暂以目录条目 0x3b + 好友行 0x54 sub 0 `[00][01][u8 国家][s8 名字]` 回应（猜测）。
- **资源交换（ResourceExchangeShop）**：进入建筑时客户端发 0x34 `[u32 商店][01]` → 服务器 0x34 `[00][u32 商店]` + 4×`{u16 最大数量, u32 汇率}`（矿/硅/铀/硫，汇率 = 每单位金钱）。客户端本地计算 S=Σ数量×汇率，手续费=Σ|数量×汇率|/3，剩余金钱=金钱−S−手续费 必须 >=0；确认时发 0x34 `[u32 商店][02]` + 4×i32（正买负卖），服务器回 0x34 `[01][u8 ok]`（0=失败文字，1=成功文字并关窗）。汇率与上限是占位值（EXCHANGE_RATE=[4,6,12,8]，上限 9999）。
- **整合商店（IntegratedShop）** 就是已完成的研究所（0x33）；全局类型 0x44/0x8c/0x11 是单位表（已完成），不是商店。
- 仍未逆向：好友列表的添加请求（"ksInputYourFriendName"）与 0x57 的真实回应；0x5d/0x5e 属于皇家大乱斗（CRoyalRumbleWnd 0x587f30/0x588b90，建立/加入房间）；师徒经验分配 UseExpWnd。
- 测试：tools/mptest/test13.py（14 项 PASS，只验证服务器自洽，格式正确与否需游戏内确认）。

## 战力等级 PR、军衔图、器官系头像、XPF 解码（2026-10-20，待游戏内验证）
- **PR**（F4/玩家资料/名人堂的 PRESTIGE 栏）改为"战力等级"：由四项属性点总和查表（40–60→1 … 226–240→10，之后每 15 点 +1，466 起 26 封顶）；原 Elo 保留在内部（elo_of）。属性每项上限 120。转生每次 +2 个未分配点。单位等级上限维持原设计（固定 60，`progression.UNIT_MAX_LEVEL`；"10 只兵 LVL50…60 只兵 LVL60" 的表按用户要求不采用）。名人堂有两列仍用 PR÷100，待调。
- **POC 规划**（poc_count/poc_seconds/poc_spots.json，`/pocs N [秒]`）、**占领后留在战场的修复**（end_battle 胜利时先 leave_map）、**转生礼物改为 Ubik（g011）**：见 sgserver.py 注释，待验证。
- **军衔图**：ui-insg.xpf 共 21 种军衔图 × 4 种兵科颜色（行 0-1 = 符号 A 数量 1–6，行 2-3 = 符号 B，行 4-5 = 符号 C，行 6 = 符号 D 数量 1–3）。分支记录里 rank 文字后的两个 u8 = 军衔图序号 0..20（客户端自行选兵科颜色）。rank_icon(level) 把 12 个军衔名铺到 0..20（General = 20）。之前填 11 恰好是"6 根柱子"。
- **XPF 格式（已解）**：见 tools/xpf.py。头 14 字节（u16 type,w,h,cx,cy, 3×u8 flags, u8 rows），后接 (rows×24+1) 个 u32 偏移；每帧 = u8 上跳过行数, u8 下跳过行数，之后每行 `{u8 skip, u8 count, count×RGB565}` 循环到行宽。
- **器官系头像缺失**：g011/g015/g024/g025/a006/a010/a017 在所有 dat 里都没有 jpg（工厂/研究所图像是黑的）。`python tools\install_portraits.py "<游戏目录>"` 会从 st.xpf 渲染 276×344 / 80×100 的 jpg 并写入 tc.dat / tc2.dat（先备份成 .orig，可重复执行）。

## 荣誉、单位数量、供应器 STOCK（2026-10-20 用户规则，待游戏内验证）
- **荣誉 HP 加成**：每显示 100 荣誉 +1% 单位最大 HP，2000 显示荣誉封顶 +20%（HONOR_PER_PCT=100、HONOR_HP_CAP=20）。**战场内每 2 分钟 +1 显示荣誉**（honor_tick，每分钟检查一次，非观战者）。
- **荣誉扣点机制（保留）**：honor_drain_due()。付费账号：进入异型洞窟每分钟 −1，转换国家荣誉归零。免费账号：荣誉未满（≥2000 显示）→ 进入任何战场每分钟 −1；荣誉已满 → 只有异型战场（洞窟、狩猎场、无主领土省份）每分钟 −1。付费标记 account["paid"]（GM `/paid [on|off]`，预设免费）。"满"定为 2000 显示荣誉（假设）。
- **单位数量**：每场最多控制 12 个（Tactics 120 → 12）；拥有上限随最高兵科等级线性从 25（1 级）涨到 48（60 级），每次转生两端各 +2，最高 100（roster_cap）。客户端转生检查（005ae640）：已拥有单位 > 25+2×已转生次数 时拒绝，提示 ksSCReturnMaxUnit；转生满 10 次拒绝。服务器也做同样检查。
- **供应器 STOCK**（用户说明 → items.json 数据已吻合）：太阳能电池（Photovoltaic/Solar/Gamma：电量少、随时充电、太阳能板处加倍）、电浆电池（Crowfoot/Leclanche/Daniell/Gravity Cell：电量大、不可充电）、沼气（Methane：电量大、中速、只在沼气区充）、核能（Fallout A/B/C：电量少、慢速、随时充、自爆）、硫酸（Sodium-Sulfur/Lovinac/Lead-acid Accumulator：电量中、快速、只在充电板上充）。目前服务器只模拟 Fallout 的每秒能量变化（Energy Drain），战斗进入时能量恒为满；太阳能加倍、沼气区、充电板的战场区域充电尚未实现（需要先确认地图上这些区域的物件类型）。

## Ctrl+F5 / F6 / F7 与多人战场规则（2026-10-20，待游戏内验证）
- 按键处理在 FUN_004b3680（Ctrl 状态 DAT_006ba7c8+0x25b1）。**Ctrl+F5 = TP**：切换 TP 旗标（对象 +0x10），提示 "Units TRANSPORTABLE/NOT TRANSPORTABLE by allies"，在战场中发送 **0x47 [u8 选项字节][u8 TP]**（00547a60；选项字节 = 选项记录 +0xd，意义未知）。**Ctrl+F6 = TK**：切换 +0x459 旗标，提示 "Units TARGETABLE/NOT TARGETABLE by allies"，**该旗标除切换函数外没有其他读取处**，也没有自己的封包——可能只是残留功能；服务器预设 TK 关闭。**Ctrl+F7** = 战场接受策略窗（"Set your battlefield acceptance policy" / "Allow any allies to join battles you command"），完全在客户端内：策略（自动接受/拒绝/手动）决定收到 0x24 询问后是否自动回 0x20 [type+2 / type+1]，服务器无需改动（我们已有 15 秒无回应自动同意）。
- 服务器规则（ally_order_refused，多人战场的指令转发前过滤）：盟友的攻击指令（0x29）若目标是另一位盟友玩家的单位且对方 TK 关闭（预设）→ 丢弃；盟友的传送（0x30 动作 5）/装载（动作 10）若目标属于 TP 关闭的盟友 → 丢弃。TP 旗标取自 0x47（预设开启）；TK 旗标目前只能用 GM `/tk on|off` 设置。待验证：按 Ctrl+F6 时 0x47 的选项字节是否变化（日志 "option 0x47: opt byte …"）——若变化，它就是 TK 旗标，改为直接取用。

## 2026-10-20 晚：七项清单进度
1. 加入阵营 +50% XP（ksJoinNationBonus）：加入成员最少的阵营时记 `commander["xp_bonus_nation"]`，留在该阵营期间击杀/胜利 XP ×1.5（`xp_multiplier`，同一函数预留限时加成 `xp_boost_until/xp_boost_mult` 和誓言加成）。客户端是否在同一条件下显示该文字未验证（可能由客户端依成员数判断）。
2. F8 回首都：客户端 0x3a 早已处理；新增 `go_home()` 与开关 `HOME_TELEPORT_GATED`（默认 False=免费；True=付费账号或 5 Ura），GM `/home`。
3. 军团（REGIMENT）：客户端用内嵌网页（rmbbs01.asp / lsbbs01.asp 等 ASP 页）+ ksJoin/Leave/Open/CloseRegiment 对话框；需要自己搭 HTTP 服务器，**未做**。
4. Word of Honor：与上级同战场时 XP +25%（`WOH_XP_BONUS`，数值待定）。UseExpWnd 经验分配窗仍未做。
5. 好友/搜索：好友添加对话框（0x55c750）发送的就是 0x57 `[s8 名字]`，与玩家搜索同一封包；回复仍是猜测的 0x3b + 0x54 sub0，需游戏内验证。
6. 等级冲突：F4 帮助 "Maximum is 60" 为旧文字（教学稿写 99，rtn-desc 写 100）；采用部门等级上限 100 + 每次转生 1（`progression.branch_cap`），单位等级仍固定 60。
7. 省份经验上限：`XP_LEVEL_CAP`{1:35,2:60,3:无}（占位），单位达到上限不再得 XP，并在聊天栏提示 ksLevelLimit。经验曲线与领土加成原始数据未知，沿用占位值。
- 军团改用聊天指令实现（2026-10-20）：`/regiment create|join|leave|open|close|kick|list|who`，数据存 server/regiments.json，创建扣 250 Ura（resources[3]）；同国才能加入。F4 军团栏位的封包位置尚未确认，暂未显示。网页版（方案 B）留待以后。

## 2026-10-21 Ura 系统（服务器已实现，未进游戏验证）
- 收入：付费账号每 24 h 打一场战斗 +PR/3（`ura_on_battle`）；国力值满 30000 后 24 h 内登录 +PR×3（`ura_on_login`，付费/免费都有）；存量 >600 时减半；小数累计在 `ura_frac`。
- 国力值：每 30 分钟每个国家每占一省 +10（占位，原版规则未找到），满 30000 → 24 h 魔星时间，每天 12:00、19:00 各开 1 小时（`star_open`）。魔星地图/怪物/商店未做。GM `/power`、`/ura`。
- 消费：换国 150（StarCenter 同星球其它阵营行，`switch_targets`）；转生 30；`/reset` 点数重置 15（按 `spent_attrs` 退还，旧账号无记录）；工厂 Wight 250、Quorg 800（`URA_PRICE`）；军团改名 250；F8 每天 5 次免费，之后 5 Ura；`/help uranium`。
- 未做：黄金武器（缺物品名单）、移动加速 ×2（3 小时）、经验加成道具、额外加速、特殊兵种其它项。
- 魔星最小版（玄武星）：`/star`（国家有魔星时间且在 12:00/19:00 窗口内）进入复用的洞窟地图 400000004，击杀奖励 ×5；研究所仅在国家魔星时间内出售 Demon Fire(5102)/H-Demon Fire(7102)（属性与价格为占位）。其余三颗星、专用地图、专属怪物未做。
- 玄武星特殊装备（用户清单）：人类隐形引擎 Terminus Biodrive(862/2862)、Mutated Biodrive(334/2334)、Mutated Biocase(352/2352)；异型装 Minor Carpace、Phasic Implant、Tendon Enhancer（已有数据）+ Alien Flame Tongue(1133)、Angel Harness(2923)、Alien Power(30001)、Monster Power(30002)（有美术无数据，占位属性）。均只在魔星时间内于研究所出售（`DEMON_FLAG_IDS` / `DEMON_ITEMS`）。"Acid Bura（死亡爆炸）" 在客户端物品表中找不到同名项，未加入。Angel Harness 的 B 键加速、Acid 死亡爆炸等效果需另行实现。
- Gold 武器：`server/gold_ids.json`（来自 hlp.dat infotbl 的 758 个基础武器编号）；服务器启动时生成 "Gold X"（id+10000，伤害×1.3，`GOLD_DAMAGE_MULT`），客户端用基础图标 + 金色调（FUN_0050e520）。目前只上架测试项 Gold Autorifle(10054)（Daeva 系，价格 100 金）；`GOLD_ON_SALE` 控制上架，正式价格/Ura 待定。Grimwell 18 件无基础数据，未生成。
