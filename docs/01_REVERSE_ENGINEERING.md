# 01 客户端逆向架构

## 1. 二进制与版本
| 文件 | 说明 |
|------|------|
| `SGalaxy185.exe` / `SG_original.exe`（游戏目录） | 原版 1.8.5 客户端，**唯一的逆向基准**（所有地址都以它为准，image base 0x400000） |
| `SG_debug.exe`（repo 根） | 当前**服务器校验用**的英文版补丁客户端（= 原版 + 补丁链），部署时一起上传，服务器用它算代码校验和 |
| `out/SG_cn.exe` / `out/SG_tw.exe` | 简/繁中文发布版 = `SG_debug.exe` + `tools/build_i18n_exe.py`（改写 .rdata 字符串） |
| `SG_debug_fNN*.exe`、`out/*_preNN.exe` | 各补丁阶段的旧版（回滚用） |

**补丁链**：每个 `tools/patch_sg_debug_fNN.py SG.exe OUT.exe` 都先调用上一版，所以只需跑最新的一个。
目前发布基准：**F27 → F29 → F30 → F31**（F28 timeBeginPeriod 未进入发布版）。

| 补丁 | 内容 |
|------|------|
| F1–F3 | 移动调试回报 0xF1 路径搜索 / 0xF2 站上传送点 / 0xF3 传送前置条件 |
| F4/F7 | 外星怪死亡回报（客户端只对自己控制的单位跑 think） |
| F5 | 单位死亡后迷雾立即恢复 |
| F6 | 外星怪追击 |
| F8 | Lab 升级后刷新树 |
| F9 | POC 状态回报 0xF4 |
| F10 | Ctrl+F6 TK 开关回报 0xF5 |
| F11 | 城镇中可部署 |
| F12–F15、F17 | Lab 引擎能力栏、资源不足红字、设计成本显示 |
| F16 | **反作弊**：每 5 s keep-alive 后送 0xF6 [代码校验和][补丁版本]（并带 GetACP 代码页） |
| F18 | 中文点阵字（`tools/build_zhfont.py` 产生字形） |
| F19 | Lab 单位树只列可用底盘 |
| F20 | 中文自动换行 |
| F21 | Acid Bura 死亡爆炸 |
| F22 | 中文输入（不关闭 IME） |
| F23 | 服务器 IP 读注册表（不用 hosts） |
| F24 | 登录框可输入数字 |
| F25 | 登录前回报代码页 |
| F26 | 省份信息刷新不切换 WAR/BATTLE/USERS 页 |
| F27 | TCP_NODELAY |
| F28 | timer 1 ms（**未发布**） |
| F29 | "DeployedUnitHealthSum is zero" 按 OK 崩溃：0x51cc56 → `EB 7E` 直接跳到清理 |
| F30 | NPC 友军 / 崩溃防护：0x609df5 `pop ebp; ret`（CRT invalid-parameter 不再终止）；0x4ada91..0x4adaae 单位列表循环防 NULL |
| F31 | 战斗小地图颜色（v2）：自己 0x5b6a44 `[0xd69314]`蓝→`[0xd69318]`绿；友军 0x5b6aae `[0xd69318]`绿→`[0xd69310]`黄；敌人红不变（2 字节） |
| F46 | 帧率上限（2026-10-27）：所有 UI / 特效动画是每画一帧前进一格；主循环 0054abf0 每圈 `Sleep(1)`，原版计时器 10–15.6 ms → 约 60 帧/秒。F28 的 timeBeginPeriod(1) 让 Sleep(1) 真的只睡 1 ms → 数百帧/秒、动画全部过快（研究所升级树、单位列表…）。00549640 开头加帧限制（16 ms，timeGetTime + Sleep，变量 0xEAFF60，stub 0xeb4940）；F40 的 80 ms 闸门改为 0（不再需要）。战斗模拟按时钟走，不受影响 |
| F47 | 战斗时钟缓冲 + 晚到指令回报（2026-10-28）：0x549037 刹车阈值 10→20 tick；0x548fe6 w 下限 20→30；.data 0x6a5394 w 初值 20→30；0x548f29 晚到分支 → 0xeb49a0 桩，每个 tick 最多送一次 0xF9 [u32 L][u32 tick][u32 w]（服务器记 LATE command / net … late commands），变量 0xEAFF64；平滑：晚到时只立刻退 5 tick，其余记入 0xEAFF68，由 F46 帧桩尾端跳到 0xeb4a40 每 2 帧还 1 tick（上限 200，战斗外清零，奇偶 0xEAFF6C）。v3：帧桩先记录帧间隔（0xEAFF70），战斗中 ≥150 ms 送 0xFA [u32 ms][u32 tick]（客户端卡住回报）。tools/patch_sg_debug_f47.py，test94 |
| F48 | 新绘图层 SGRender.dll 挂钩（2026-10-28，阶段 0）：表 0xEAFF80（+0 版本，+4 on_present，+8 on_create，+0x3c 已加载旗标）；0x4c0bd0 CGraph 初始化 → 0xeb4b40 桩 LoadLibraryA("SGRender.dll") + GetProcAddress("SGR_Init") 只做一次；0x4c4a60 CGraph::EndFrame（每帧，后缓冲仍锁着）→ 桩呼叫 on_present(CGraph)，返回非 0 = DLL 自己画完，跳过 Unlock+Present；0x5ecc50 CWnd::Create → on_create(wnd, 建立结构)，寄存器全保留。字串 0xeb4c40。无 DLL 时表为 0，行为不变。画布 = [CGraph+0x34]（RGB565，pitch [+0x60] 像素）；[+0x5c] 只是当前视口原点。tools/patch_sg_debug_f48.py，client/sgrender/，test98 |
| F49 | 宽屏画面（2026-10-28，阶段 1）：画面 W×600，W 由 SGRender.dll 按屏幕比例决定（TABLE+0x10，0 = 800）。游戏仍在 800×600 的「800 空间」里运作：SetViewport 00438100 把所有视口右移 DX=(W-800)/2、鼠标夹到 0..W-1 后减 DX、整屏裁切框 -DX..800+DX（帧根 5490f0、窗口树 5487d5、光标 549241/549255、淡出 4c499e）、TC Main / Field 对子窗口裁切（5487ff）与鼠标命中（545867）视为整幅；窗口/显示模式/缓冲宽 W（544d3e、4c0b60、4c0b7e、4c0c5d、窗口模式 present 4c04d2/4c05c3/4c05e2/4c05f2、4bae00、ClipCursor 54ba1e）；地块列 499d79 → W+32；快速选单滑动 4a4a87..4a4bd8 → 800+DX；右侧小单位卡 4afa94 +DX；战争迷雾绘制 499d90 / 可见判定 4b6120 交给 DLL（加宽版窗口，同样的柔化）；帧开始 54911a → on_frame（清空后缓冲）。桩在 .dbgmov 0xeb3f40..0xeb4400。tools/patch_sg_debug_f49.py，test99 |
| F50 | 宽屏下的像素点选（2026-10-28，HUD 上线后闪退 dump 005f5f01）：004bf400 / 005f0d70 / 005f4320 / 005f5ed0 用「鼠标 − 视口」在画布写标记像素再读回来判断点到哪个单位；F49 的视口是画面坐标、鼠标是 800 空间，差 DX → 点选偏左 DX，鼠标在画面最上方且离左缘不到 DX 时下标为负、写到画布前面而闪退。四处读鼠标 x（CMainSystem +0x2578）改为加 DX（F49 的 getdx，无 DLL 时 0）。桩在 0xeb4340（F49 桩之后）。tools/patch_sg_debug_f50.py，test102 |
| F51 | 战场地图全高（2026-10-28，使用者「战场画面应该要再拉高一点」）：MapWnd 高度 MH 由 SGRender.dll 决定（TABLE+0x34，462..600，0 / 超出 = 462 = 原版；有新 HUD 时 600，backend=cnc 或 [hud] enable=0 时 462）。00499d10 地块行数 0x10 → (MH+63)/32；快速选单 004a4a50、战略地图 004a6a50 滑动时 4 处把 MapWnd 改回 462 高 → MH；0049ba40 残骸绘制停止行 +0x11 → +0x16。单位裁切、镜头夹值（0049ab30）都用 MapWnd 自己的矩形，自动适应；迷雾（exe 窗口只有 0x40 行）由 DLL 画与判定，行数 (MH+32)/8+3。桩在 0xeb4390（F50 桩之后）。tools/patch_sg_debug_f51.py，test103 |
| F52 | 快速选单浮在地图上（2026-10-28，使用者「下方有个黑底是否能去掉」）：快速选单滑动 004a4a50 原本用地图右缘当滑动状态，把 MapWnd 缩到选单左缘，所以选单下方没有地图（黑块）。入口改为先呼叫 SGRender.dll（TABLE+0x38 qm_slide(field)）：DLL 用选单自己的 x 滑动（进 30 px、出 50 px，开在 587+DX、关在 800+DX，关上后隐藏），地图保持整个画面宽。无 DLL 时照原版。桩在 0xeb4c60（F49 的桩区已满，用 F48 字串后面的空位，到 0xeb4d00）。tools/patch_sg_debug_f52.py，test104 |

## 2. 工具链
| 工具 | 用途 |
|------|------|
| `ghidra_scripts/*.java` | Ghidra 无头导出：Handlers、SendCatalog（发送点目录）、Callers、DecompRange、RefsTo、ScanScalar |
| `analysis/` | 导出结果：`functions.txt`、`strings.txt`（字符串 + 引用函数）、`handlers/*.c`（封包处理函数反编译）、`send_catalog.tsv`、`netcluster_decompiled/`、`vinu_provinces.tsv`、`unit_tree.tsv` |
| `tools/sgproto.py` | 封包分帧 + 加密（从 SG.exe 还原，服务器直接 import） |
| `tools/sgdat.py` / `sgdat_add.py` | `.dat` 资源包读/写（hlp.dat、ntt.dat、NTF2.dat、pam*.dat、tc.dat …） |
| `tools/xpf.py` / `xpf_render.py` | `.xpf` 精灵图解码（FUN_005f2540 / 005eebe0） |
| `tools/build_i18n_*.py`、`build_zhfont.py`、`build_ntf2.py`、`ocr_ui.py` | 中文化 4 个阶段（服务器讯息 → ntt/hlp → exe 字符串 → UI 图片） |
| Python + capstone（设备上 `~/rev/sgdis.py`） | 快速线性反汇编 `.text`，用来找常数/循环（例如 RGB565 颜色、结算窗口排版） |

**没有 Ghidra 时的快速做法**：`sgdis.py SG_debug.exe` → `dis.pkl`（约 79 万条指令），再按地址范围或立即数搜索。

## 3. 崩溃诊断流程（已验证有效）
1. 让玩家在 Windows「事件查看器 → 应用程序」找 **Application Error（Id 1000）**，取 **错误偏移**：
   `Get-WinEvent -FilterHashtable @{LogName='Application';Id=1000} -MaxEvents 5 | fl`
2. 偏移 + 0x400000 = 原版地址，对照 `analysis/functions.txt` 找所属函数。
3. 已知偏移：
   - `0x209e0f` = CRT `_invalid_parameter`（0xC000000D）：通常是 STL vector 越界（客户端用 `FUN_00609e03` 做边界检查） → 找服务器送了比客户端预期更多/更少的元素。F30 已让它不再终止。
   - `0x4adaa8` = 单位列表循环取到 NULL → F30。
   - `0x00008749` = `00408749` 战场加入对话框攻方名单查国家表得到 NULL（2026-10-24 已查明，见文末 0x1e 一节；服务器改送国家 id 后不再发生）。
4. 客户端 vector 边界检查样式：`if (begin==0 || (end-begin)/size <= i) FUN_00609e03();` —— 读到这个就代表服务器给的数量必须符合客户端已分配的大小。

## 4. 常用客户端地址（原版 1.8.5）
| 地址 | 功能 |
|------|------|
| 004b0040 | 战斗结算封包 0x25 解析 → CBattleResultWnd 0040a430；绘制 0040a950（阵营信息循环 0040ce40，每条 30 px，**面板只放得下 1 条「对 X 国战绩」**） |
| 004d3050 / 004ac800 | PUT_UNIT（0x18）处理；能力位 → 指令按钮 004d49a0 |
| 004d0420 / 004cb080 / 005261b0 | 伤害公式 / 防御方护甲 / 伤害修正表 |
| 004cad50 | 攻击距离判定（≤ range+size 且 ≤ sight+size） |
| 0048f340 | POC 客户端模拟占领 |
| 004d0b30 / 004c6900 / 0051cbb0 | 走进传送点 → 前置检查 → "DeployedUnitHealthSum is zero" |
| 004e1990 | 单位到达出口传送点 → 0x2f（撤退） |
| 00547bb0 / 005521d0 | 0x05 国家关系 → 敌友分组表（不送 0x05 = 全部同组 = 都是友军） |
| 00463440 → 00407e80 | 省份记录里有己方国家才显示 JOIN |
| 00547540 case 5 / 004a9890 | 0x0E[06] 请求世界快照 → 客户端回 0x1d |
| 004bfe10 | 点阵文字渲染（中文 F18） |
| 00550380 | 自动换行（F20） |
| 0045a4e0 | 星球轨道向量 → 3D 位置（向量不可为 0） |
| 004c0cd0 附近 | 像素格式/颜色遮罩初始化（不是小地图颜色） |
| 005b66d0 | **战斗小地图**绘制：颜色表 原版：0xd69314 蓝 = **自己**（0x5093a0(unit+0xb9) 为真 = 自己的单位）、0xd69318 绿 = **友军**；F31 后自己绿、友军黄、0xd69310/0xd6930c 黄、0xd69308 蓝、0xd69304 红(可见敌人)、0xd69300 黑；单位循环 005b6930，友方旗标 unit+0x69，0x5093a0(unit+0xb9) 判断是否他人单位；每单位画 2×2 像素 |
| 005b6480 | 另一个小地图（城镇/预览）：0xd692ec 绿、0xd692e8 蓝（未改） |
| 00402f40 | RGB → 16 位颜色（参数 r,g,b）；很多 UI 以内联方式用 [0xc36dcc]/[0xc36e16] 组色 |

## 5. 未完成的逆向项目
- 客户端快照（0x1d）各栏位含义尚未全部确认（`battle_snap.py`）。
- ~~0x00008749 崩溃~~（2026-10-24 已查明：0x1e 名单的国家 id）。

### F32（2026-10-23）城鎮小地圖自己的點
- 005b6a21 `cmp [win+0xa0e9],0`：win+0xa0e9 = 主視窗「戰鬥中」旗標（005b7230 設定）。非戰鬥時會跳過「是不是自己」的判斷 0x5093a0(unit+0xb9)，所有友方點都用友軍色。
- F32：005b6a28 `0f 84 80 00 00 00` → 6 個 NOP。城鎮裡也是自己綠、其他人黃。
- 小地圖單位狀態：unit+0x378[word unit+0x77a]->+4 旗標，bit1/bit2（mask 6）= 隱形類狀態，非友方的單位不畫。

## 戰場加入對話框 0x1e（BATTLE INFO，2026-10-24 確認）
解析 `004af1e0`，名單繪製 `00408630`，國家表查找 `00551ec0`（表 `[0x6ba80c]`，由 0x0F 填入，每筆 0x168），自己國家 = 指揮官 `+0x3ac`（`004ee830`，來自 0x15 的 nation 欄位）。
```
u32 map, u8, u8, u32 DEFENDER nation, s8 標題(<=0x100),
u8 n × { s8 名字(<=0x40，清單顯示 18 字), u32 NATION（參戰者自己的國家）, u32 SIDE（為哪一方作戰） },
u8 WAIT 秒, u8 CAN ENTER（0 = 戰場已滿）
```
- **SIDE**：與守方同一同盟組（0x0F 同盟組陣列）→ 守方清單，否則攻方清單。
- **NATION**：拿去國家表查名字顏色（記錄 +0x10a）。守方繪製查不到會跳過；**攻方繪製沒有檢查（`00408749`）→ 查不到就閃退**。以前伺服器在這裡送的是英雄單位 uid / NPC id 40000+，所以名單一直是空的，放 NPC 會閃退（10-23）。
- **NATION == 自己的國家** → 「本國已在此戰鬥」：按鈕後客戶端送 `0x20 [01][u32 map]`，否則送 `0x1b [01|02][map][x][y]`；伺服器兩者同樣處理（含剛離開的等待時間）。自己國家 5（傭兵）→ 選邊按鈕 `0x20 [04][map][side]`。
- 伺服器現在：玩家送 (帳號, 自己國家, 作戰方)；NPC 指揮官（場上還有單位的）送 (名字, 國家, 國家)；外星駐軍一行 (外星駐軍, 0, 0)（0 = Neutral，登入後的 0x0F 才有）。測試 `tools/mptest/test46.py`、`test36.py`。

## PUT_UNIT +0x20 / +0x21（2026-10-24）
- +0x20 u8 → `unit+0x14c`（意義未明，送 0）。
- +0x21 u8 → `unit+0x150` = **行為模式**，think 處理 1–6（`004cc491`、`004cf5b4`、`004cf775`）；客戶端自己建立的單位在 `004d2ebc` 設為 2。
- 伺服器：玩家單位送 2（`UNIT_MODE_PLAYER`），伺服器單位送 0（`put_server_unit`）。

## 戰況排名 0xFC（TAB，2026-10-24 確認）
- 解析 `004b4720`、加一列 `004b46a0`、繪製 `00426c4e`（視窗類別 CCombatRankingWnd，vtable `0x64dee4`）。
- `u8 攻方國家, u8 守方國家, u8 n × {s8 名字, u8 國家, u16 POINT, u16 KILL, u8 Avg Kill Lvl, u8 POC, u8 REINS}`。
- 開頭兩個 byte **不是分數**：存在視窗 +0x2e4 / +0x2e8；每加一列，國家等於其中一個就把 +0x2ec / +0x2f0 加 1 → 畫面下方 TOTAL ATTACKER / DEFENDER = 各方**指揮官人數**。只比對一個國家 id，同盟國家的列不會算進去。
- 伺服器以前送分數總和 → 一直是 0；現在送國家 id，NPC 指揮官也列出（擊殺、REINS = 派出的波數）。測試 `test49`。

## F6 名單 0x12 kind 1 的列（2026-10-24 確認）
- 解析 `004f8820` → 存列 `004f8770`，繪製 `004f5a50`。列：`s8 名字, u32, u16, u8 p5, u8 p6, u8 p7, u32 p8, u32 p9, u8 p10, u16 勝, u16 敗`（kind 1 每列再加 u16，結尾 u16 = ACTIVE HEROES）。
- u32 → +0x40 = **國家 id**（FACTION 欄 = 國家表 `00551ec0` 的名字與顏色）；u16 → +0x44 = 軍團 key（`0057e310` 只比對 u16，和 F4 視窗一樣）。以前送名字的 crc → FACTION 空白。
- p5 → LEVEL（"%d"）；p7 = 兵科 0–3：視窗旗標 +0x764 開啟時 LEVEL 欄改顯示軍階名 `0057a550(兵科, 等級)`，顏色 `0057a520`。
- p8 = PR、p9/100 = PRE、p6 圖示（檢查 0 / 9）、p10 圖示（< 5）。
- F6 各頁要求的 kind（`004f3cd0`）：WHO-LIST = 1（開啟時 `0049e6e0`），HALL OF FAME 三頁 = 2 / 3 / 4 → **新手 / 進階 / 精英星**。伺服器以前三頁都送同一份混合名單；現在每頁只送該星球等級國家的指揮官（玩家 + NPC），依 PR 排序，最多 100 名（test49）。客戶端每頁有「已要求過」旗標（`0xc530b8..ba`），何時清除未確認。

## Lab 底盤樹（2026-10-24 16:10）
- 類別 vtable 檔案位址 0x24f820，init 00443de0，建樹 00449cc0（由 0052d607 裝備頁、005d5d6d 升級成功呼叫），排版 004482a0。
- 0xc32cec = 單位表（0x44）：+0x24 清單 1（32 bytes：u16 class id + 名稱），+0x14 紀錄（0x68）。分頁 = class id ÷ 100；每個分頁一個 map（+0x3d0 + tab×12），key = class id。
- 旗標 +0x3cc：跳過「沒有子資料」的底盤 / 型號（00444360 / 00448483 檢查子項 +0x6c）；原版不開。補丁 F33 打開後升級頁全部變空（「你沒有任何航空單位」）→ +0x6c 不是單位清單，F33 已撤回（16:26）。單位是用名稱比對掛到型號下（00448040：unit+0x68 名稱 vs 型號名稱）。
- 0x44 第一份名單（+0x24，32 bytes：u16 class id + 名稱）的使用者：00449cc0、0044a560（研究所建樹）、00449c62→005c6390（點分類展開：名稱→id）；其他（工廠、單位 0x16、部署）用第二份 0x68 紀錄（+0x14）。0x44 解析 005c8ff0 會先清空舊名單，可以重送。單位掛到型號下：00447e10 把師團 12 格 + 預備隊依 class id ÷ 100 分到 4 個分頁清單（+0x40c），00448040 再用名稱（unit+0x68）比對型號紀錄。
