# cnc-ddraw v7.1.0.0（MIT，https://github.com/FunkyFr3sh/cnc-ddraw）
2026-10-24 為了大型戰鬥的客戶端效能下載（使用者 22:04 要求，選擇「只下載，先不加 OTA」）。
來源：官方 Release `cnc-ddraw.zip`，sha256 0b13ab89a64c9918189b1dadd449ef6ed3cb3b7b19cabd96d8adbd95505bb908。

## 手動測試
1. 把 `ddraw.dll`、`ddraw.ini` 複製到遊戲資料夾（SG.exe 旁邊）。
2. 正常用啟動器進遊戲，比較大型戰鬥的流暢度。
3. 可用 `cnc-ddraw config.exe`（同樣放在遊戲資料夾）改設定：視窗 / 全螢幕、renderer（auto / opengl / direct3d9 / gdi）、maxfps。
4. 還原：刪掉遊戲資料夾裡的 `ddraw.dll`（和 `ddraw.ini`）。

不影響客戶端校驗：伺服器只檢查 SG.exe 的程式碼。
確認有效後，把 ddraw.dll / ddraw.ini 加到 deploy/ota_files.json 的三個頻道，再 publish。

## SGalaxy 設定（2026-10-24 22:36，使用者要 1920×1080）
遊戲原生解析度是 800×600（4:3，SG.exe 有 5 處 push 600 / push 800），沒辦法真的多顯示地圖。這裡改的是放大顯示：
- `fullscreen=true` + `windowed=true`：無邊框全螢幕，用玩家桌面的解析度（1920×1080 螢幕就是 1920×1080）。
- `maintas=true`：保持 4:3，左右留黑邊（1080p 上實際畫面是 1440×1080），不會被拉寬變形。
- `shader=Lanczos`：內建縮放濾鏡，放大後比較銳利。沒有附 Shaders 資料夾，所以用內建名稱，不用檔案路徑。
- 原始檔留在 `ddraw.ini.orig`。
