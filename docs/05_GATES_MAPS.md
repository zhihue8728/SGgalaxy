# 05 星门 / 传送点 / 地图资料

设计决策：Claude 项目 `claude/GATE_PLACEMENT.md`、`NPC_GATE_ENTRY.md`、`PROVINCE_MOVEMENT.md`。

## 1. 客户端资料文件
| 文件 | 内容 |
|---|---|
| `vinu.inf` | 星系 → 星球 → 省份（col,row,theme,名称 = .nm 地图名）。表：`analysis/vinu_provinces.tsv`。**地图 id 不在表里 → 客户端乱码崩溃** |
| `pam.dat` / `pam3.dat` | 省份地图 `.nm`：`u8, u16 w, u16 h, w*h×{u16 tile, u8 flag}, u16 n×{u8 x,u8 y,u16 type}`。flag 0x01 = 不可走 |
| `pam2.dat` | 内含 `Portals.por` / `Capital.por`（传送点记录） |
| `FieldMap.mp` | 地形主题 9..13 的贴图重映射 |

## 2. 传送点记录 Portals.por [确认类型]
记录 = `u32 类型, u32 参数, u32 x, u32 y, u32 w, u32 h`（类型 1/9 另有 3 个 u32：目标偏移、抵达点）。座标 ×32 = 像素。

| 类型 | 用途 | 客户端送出 |
|---|---|---|
| 1 | 野外星门（相对目标 ±100/±1 = 相邻省） | 0x2e |
| 2–6 | 首都设施（工厂、研究所…） | 各自 handler |
| 7 | FHQ 国家总部（只限本国/同盟，看 0x17 的 MAP OWNER） | — |
| 8 | CTF | 0x2e 200000000 |
| 9 | 洞穴 | 0x2e 400000000 |
| 10 | StarCenter 星盟中心 | 0x37 [00] |
| 11 | Dimensional Matrix 星门（跨星球） | 0x39 [00][01] |
| 12 | 天文台 | 0x39 [00][00] |

## 3. 我们对地图/星门做的修正（产生 `out/pam2_fixed.dat`、`pam3` 修正版）
按顺序：
1. `tools/fix_stub_maps.py`：10 张被挡住的占位地图换成可玩的。
2. `tools/fix_portals.py`：新手星 6、精英星 3 套用进阶星 2 的传送网（原版是 8×8 网，有 21 省没有星门）。首都只用画出来的 6 个门 `CAP_GATES`。
3. `tools/fix_split_maps.py`：被河/悬崖切开的地图挖 3 格宽通道，保证每个入口能走到每个出口。
4. `tools/fix_gate_dirs.py`：**星门朝向修正**：通往相邻省的星门放在**画面方向**（等距 45°）朝向该邻省的可走点；`TARGET_MODE` = 取最靠近面向邻省边界点的空地，`EDGE_TARGET 5`。规则：4×4 全可走、英雄可达（2×2 净空）、离边界 ≥ 2 格、离其他门/洞口 ≥ `GATE_SEP 14` 格、离 POC ≥ `POC_SEP 10` 格。反向门的抵达点设在新门上（**相邻两省的门互相对着**）。
发布：`deploy\publish.bat`（OTA 1.0.12 = pam2 星门修正）。

## 4. 服务器端由地图产生的资料（`server/`）
| 文件 | 产生工具 | 用途 |
|---|---|---|
| `portal_links.json` | （由修正后的 portals.por 产生） | 省份连通图 → `PORTAL_LINKS`、`_route()`，所有 NPC/玩家路线与相邻判定 |
| `gate_spots.json` | `tools/gen_gate_spots.py` | `{CCRR: [[邻省CCRR, x_px, y_px], …]}` → `GATE_SPOTS`、`gate_starts()`（NPC 从哪个门进场）、`retreat_target()` 的落点 |
| `poc_spots.json` | `tools/gen_poc_spots.py` | 每张图的 POC 位置（可走地面） |
| `spawn_spots.json` | `tools/gen_spawn_spots.py` | 外星怪出生点 |
| `walk_grids.json` | `tools/gen_walk_grids.py` | 32 px 可走格，`battlesim.py` 用来寻路 |
| `capital_spots.json` | — | 首都可走点（NPC 在城里走动、预览小地图点） |
| `map_sizes.json` | — | 地图尺寸（外星怪数量系数） |
⚠️ **改了 portals.por / 地图后，以上 json 要重新产生**，否则 NPC 会从错的位置进场、路线错误。

## 5. 相关规则
- **玩家进入战斗的星门**（2026-10-23 22:31，`entry_gate()`，在 `enter_field` 里覆盖客户端给的抵达点）：从相邻省走进来 → 通往**来路省**的那个门；从大地图加入/远处来 → 通往**己方/同盟省**、离自己首都最近的门；都没有才用客户端的位置。日志 `enters X at the gate from …`。
- NPC 进场 `gate_starts()` 排序：来路省的门 > 己方/同盟邻省的门 > 离首都近的门（不会从敌国那一侧的门进场）；加入进行中战斗时用任务路线的上一省。
- NPC 进场：`gate_starts(mapid, n, nid, avoid, frm)`：面向来路省（或首都方向）的门优先，避开玩家抵达点 900 px，**永不放在 POC 上**。
- 撤退落点：目标省中「通往战斗省的那个门」。
- 省份图走入星门：客户端检查是否有活着的已部署单位（`DeployedUnitHealthSum is zero` → F29 修正崩溃）。
- 被截断（敌方占领/封锁）的省：NPC 不经过；玩家撤退到那里要再打一场。
- 检查工具：`tools/check_world_maps.py`（离线检查每个星球/省份客户端会怎么处理）。

## 6. 星門與相鄰省的綁定（2026-10-24 12:29 檢查）
- 每個門只通往一個相鄰省：`gate_spots.json` 由已發佈的 `out/_portals/portals.por` 重新產生，內容完全相同；85 省、440 個門，和 `portal_links.json` 一一對應，連線都是雙向的（`tools/mptest/test47.py`）。
- **問題**：`gate_starts()` 以前把 n 支 NPC 部隊**依偏好順序分到所有門**：第 1 支走最好的門，第 2、3… 支就輪到通往敵國省的門。例：600001 國家 1 只有通往 00 號省的門是己方，6 支部隊卻用了 0、2、101、102 四個門 → 藍色 NPC 從紅國那一側的門進場。
- **現在**只用最好的一類門：①來路省的門 →②通往己方 / 同盟省的門 →③都沒有才用離首都 / 出發地最近的一個門。避開玩家抵達點只在同一類裡挑，不會換到別類。
- 進攻方 NPC 開戰（模擬戰鬥）也用任務路線的上一省當來路。日誌 `gates for nation N on MAP: k squad(s) via the gate(s) to [...]`。


## 7. 星門按六角形六個面擺放（2026-10-24 18:40）
- 每個省是六角形（平頂）：N、NE、SE、S、SW、NW 六個面。相鄰省屬於哪一面由 CCRR 六角格決定（`fix_gate_dirs.hex_side()`，奇數欄高半格）。星門放在**小地圖上**那一面的中點附近：N 上中、NE 右上、SE 右下、S 下中、SW 左下、NW 左上（`HEX_SLOT`，比例 (0.5,0) (0.875,0.25) (0.875,0.75) (0.5,1) (0.125,0.75) (0.125,0.25)）。例：首都 00 → 0100 右上、0101 右下、0001 下方。
- 以前的做法換算成 45° 畫面方向（`TILE_DIR=False`），結果首都三個門都在小地圖右邊。
- 選點：方向優先（35/60/90°），再挑離該面中點最近、周圍可走 ≥ 0.9 的空地；**不可擋路**（`NO_SPLIT`：門的 4×4 + 外圍 2 格擋住後，英雄可走區不能被切成兩塊）；仍保留離其他門/洞口 ≥ 14 格、離 POC ≥ 10 格、小地圖 5×5 每格最多一個門。
- 邊界中心方向（`strat_borders.py`：客戶端戰略圖省份形狀 `nb%02d%02d.xpf`，每張圖以戰略圖原點對齊）保留做參考（`BORDER_DIR`），六面模式下不用。
- 地圖本身擋住的情況：0806→0807（下方不可達）、0200→0201、0301→0300 等放在該方向的內側。
- `check_world_maps.py`：planets 2/3/6 各 440 門 ALL OK。已重產 `out/pam2_fixed.dat`、`out/_portals/portals.por`、`server/gate_spots.json`、`spawn_spots.json`、`walk_grids.json`。備份 `out/pam2_fixed.dat.before_border_dir`、`out/_portals/portals.por.before_hex`、`server/_history/*.before_hex`。
- 檢視圖：`out/artcheck/gate_view.py CCRR ...`（黃色 = 星門，藍色 = 洞口）。

## 8. 星門位置資料檔（2026-10-24 18:58）
- `tools/gate_layout.json`：每個省份地圖的星門（85 省、440 門，三顆星共用）：`{"CCRR": {"map": ..., "gates": {"鄰省CCRR": {"side": "NE", "x": 115, "y": 30}}}}`，x / y = 4×4 星門矩形左上格（小地圖座標）。
- 快速調整：改 json 的 x / y →
  `python tools/gate_layout.py apply out/pam2_fixed.dat tools/gate_layout.json out/pam2_fixed.dat` → `check_world_maps.py` → 取出 portals.por → `gen_gate_spots.py` / `gen_spawn_spots.py` / `gen_walk_grids.py` → publish（pam2）+ deploy。
- 重新匯出：`python tools/gate_layout.py export out/pam2_fixed.dat analysis/vinu_provinces.tsv tools/gate_layout.json`（export → apply 為原樣，已驗證）。
