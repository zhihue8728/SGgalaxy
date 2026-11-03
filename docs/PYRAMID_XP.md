# Word of Honor「金字塔」：下屬 XP 回流與 Assign XP（2026-10-26 20:xx）

狀態：**待部署**（`deploy\deploy.bat`，不用發布客戶端）。測試 `tools/mptest/test74.py`（11 項）。

## 原版規則（出自客戶端文字 ntt.dat pyramid / HELPWND khiPyramid* / ETCTEXT）
- 宣誓後你是對方的 Subordinate（下屬），對方是 Superior（上級）。邀請的新玩家自動成為下屬（外部郵件邀請不做）。
- 上級好處：(1) 與下屬同戰場 XP 加成（`WOH_XP_BONUS`，暫定 25 %）；(2) 收到下屬冒險產生的額外 XP，自己在 Assign XP 視窗分配給**自己的單位**。
- 下屬等級高於上級 → 他的 XP 不能用（kPyramidStudentLevelOver）；單位等級太高 → 不能接收（ksLevelLimit）；沒有 XP → ksNoAvailableExp。
- 按鈕：Auto distribute / Undo / Clear；Whisper Superior / Whisper Subordinates（聊天頻道 ksChatMentor / ksChatApprentice）。

## 伺服器實作
- `progression.WOH_TRIBUTE = 0.10`（暫定）：下屬任何單位賺到 XP，`cmd["tribute"]` 加 10 %（不減少下屬自己的 XP）。分配進來的 XP 不再往上流。換上級或解除時歸零。
- `social.py`：`my_subordinates` / `tribute_rows` / `send_exp_window`（0x54 sub 3：`[03][u8 n]` + n×`{u8 等級, u32 可用 XP, u32 學生 id, s8 名字}`）/ `assign_exp` / `xp_command`。
- 客戶端 0x55 `[02]`（Quick Menu 的 Assign XP）→ 回名單視窗。客戶端 0x55 `[04]` = 視窗的 24 欄位回覆（0x5de820）：**欄位尚未解碼**，目前只記 log（`assign XP packet … hex`）並提示用指令。
- 聊天指令（可用）：`/xp` 列出各下屬可用 XP 與自己的單位；`/xp 單位# [數量]` 給指定單位；`/xp auto` 平均分給所有單位。

## 未確認（需遊戲內一次驗證）
- 名單封包兩個 u32 的順序（可用 XP / 學生 id）與視窗是否正確顯示；若欄位反了，把 log 裡 `assign XP window` 與截圖給我。
- 視窗確認時客戶端送回的 0x55 `[04]` hex（log 裡 `assign XP packet from …`）→ 之後可解碼並真正套用。
- Whisper to Subordinates 預期用客戶端名單送 chat sub 5（多人密語，服務器已支援）；Whisper to Superior 用一般密語。
