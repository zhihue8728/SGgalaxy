# BOARD + SGMAIL（2026-10-26，用户："board 以及 mail 的功能沒辦法使用"）

## 原理（SG.exe 1.8.5 逆向）
- 游戏内 BOARD / SGMAIL 窗口不是服务器协议，而是**原站 ASP 网页**：exe 用 urlmon（IE 栈）GET 页面，用 `strstr` 在固定标记字串之间切字段（`FUN_00416730` / `00540d10`），没有 HTML 解析器。
- 基址字串在 `.rdata 0x64eae0`：`http://bbs.sgalaxy.com/tc_new/gamebbs/`（≤38 字符，缓冲 0x27，`FUN_004300d0` 复制到 `[this+0xb1c]`）。其下：看板目录 `notice/ qna/ free/ bug/ nation/`（客户端 5 个 tab，标题图 `../image/title01..05.gif`），信件 `mail_box/`（标题图 title06）。
- 我们把基址改成 `http://43.135.15.91:3001/b/<c|t|e>/`（c=GBK 简体，t=Big5 繁体，e=其他；端口 = 更新端口，已对外开放；`tools/board_url.json` 可改主机）。写入 `tools/build_i18n_exe.py`（改 .rdata，不影响代码校验和）；英文版新增 `out/SG_en.exe`（`deploy/ota_files.json` en 频道 SG.exe/SG_debug.exe 改用它）。
- 服务端：`server/sgs/board_mail.py`（`board_http`），由 `ota.py` 的 UpdateServer 在路径 `/b/` 下转交（GET/HEAD/POST，no-cache）。存档 `server/board.json`（deploy 不覆盖）；信件存在帐号 `a["mail"]`（和 /mail 指令共用）。

## 请求（文件名）
| 功能 | URL（基址后） | 参数 |
|---|---|---|
| 列表 | `<dir>/lsbbs01.asp?nat=&server=`；搜索 `?t=1标题/2内容/3作者&q=&nat=&server=`；翻页 `?t=0&q=&p=N`（p 从 0） | 每页 15 篇 |
| 阅读 | `<dir>/atbbs01.asp?sn=ID`（列表行里的链接，由页面给出，≤49 字符） | |
| 发文 | `<dir>/inbbs02_t.asp`（POST） | `f_name`=登录帐号 `f_subject f_contents nat server f_passwd1 f_passwd2`（`f_passwd1` = 登录密码，见「身份验证」） |
| 改/删 | `<dir>/mdbbs02_t.asp` / `rmbbs02_t.asp` | `sn`(阅读页作者链接 `rmbbs01.asp?` 后的文字) + `f_name …` |
| 信件列表 | `mail_box/lsbbs01_t.asp?server=&owner=ACCOUNT&passwd=`（搜索 `t=&q=`） | owner = 登录帐号，`passwd` = 玩家登录密码（客户端明文放在 URL 里） |
| 登录后查新信 | `personal/lsbbs01_t.asp?owner=&passwd=`（无 server 参数） | 与信件列表同一页面（2026-10-26 日志发现，原先 404） |
| 投票 | `poll/lsbbs01.asp` | 原站功能，未实现，回空列表 |
| 读信/删信/寄信 | `mail_box/atbbs01.asp?sn=` / `rmbbs02.asp` / `inbbs02.asp` | 寄信 `f_sender f_receiver(帐号或昵称) f_subject f_contents` |
- **15 级门槛是客户端检查**（`00419f48` 发文 / `00543c64` 寄信）：读 `[0x6ba7d8]+0x47c`（指挥官等级，字节）**< 15 且** `+0x47d`（转生次数）**< 1** 就弹 "You cannot post … until you reach level 15"。`+0x47c` 由服务器的 0x15 指挥官包（`units_items_lab.build_commander` 的 "+0x2f" 字节）给；以前写死 1，所以兵科 15 级也被拒（2026-10-26 修：改为各兵科最高等级）。≥5 级时客户端还会多读一次注册表（`0049e8c0`），无害。
- 注意：这个弹窗文字**也**会在页面回应为空（长度 0）时出现（`00419fb6 cmp [esp+24],1`），所以日志里没有请求、弹窗又出现时，要先查是不是请求没到服务器。
- 公告板（notice）只有 GM 可发；国家板（nation）按 `nat` 分开；作者可改删自己的文，GM 可改删全部。

## 页面格式（客户端切字串的顺序，页面必须依序含有）
- 列表：`<img src=../image/title0N.gif border=0>` → `검색된 전체 글 수  : ` N `</b>`（cp949 原字节）→ 每行：`<td align=center><font size=2 color=#000000>编号</font>`、`<td><font size=2 color=#000000>日期</font>`、`<td align=center>…作者</font>`、`<td><font size=2 color=#000000><a href=URL>标题</a></font></td>`、`<td align=center>…点击</font></td>`；**信件列表**行少「作者」格，最后一格是状态：含 `NEW`/`미개봉` = 未读。翻页：`<b><a href=URL>页码</a></b>`，文字 ◀/▶（cp949 `a2b8/a2ba`）会被换成 `<`/`>`。
- 阅读：表头 `<td width=30>…<b>编号</b>`、`width=130` 作者、`width=30` 点击、`width=170` 日期；`<font size=3 color=#483010><b>标题</b></font>`；正文 `<font size=2>…</font>`（换行 `<br>\r\n`）；`<b>이전글 : </b><a href=URL>`、`<b>다음글 : </b><a href=URL>`；`<a href=lsbbs01.asp?…>`（返回列表）；作者本人另有 `<a href=rmbbs01.asp?sn=ID>`，且表头作者必须等于登录帐号（客户端据此启用 修改/删除）。
- 信件阅读：标题图 title06，表头 `width=130` 寄件人、`width=170` 日期、`width=250` 收件人，其余同上，返回链接 `lsbbs01_t.asp`。
- 用户文字里的 `<` `>` 换成全角/括号（客户端不解码 HTML 实体）。

## 测试 / 发布
- `tools/mptest/test73.py`：用与客户端相同的 strstr 切法解析本服务输出的所有页面（列表/阅读/翻页/搜索/发删改/信件/NEW 状态/HTTP POST），64 项（含防护：密码/令牌/配额/洪水/日志脱敏）。
- 部署：`deploy\deploy.bat`（服务器）→ `build_i18n_exe.py SG_debug.exe`（已跑，产出 out/SG_cn/tw/en.exe）→ `deploy\publish.bat -Version 1.0.31 -Notes "..."`。旧客户端（原站网址）不受影响，但看不到我们的公告板。

## 身份验证（`bw_auth`，2026-10-26）
网页请求本身不带登录，所以逐级判断，返回 (帐号, 方式)：
1. **`pw`**：请求里的密码（`passwd` / `f_passwd` / `f_passwd1`）通过 `acctstore.pw_check`（PBKDF2，与游戏登录同一函数）→ 任何 IP 都认；该帐号被标记 `web_pw=True`。
2. **`ip`**：该帐号有在线游戏连线且来自同一 IP。
3. **`tag` / `name`**（实际在用）：该帐号有在线游戏连线（任何 IP）。原因：同一玩家的游戏连线和网页请求可来自**不同公网 IP**（实测 60.250.152.229 / 220.128.128.151 / 220.128.135.193 / 60.250.80.130，运营商 NAT），只认 IP 会让所有发文被拒。**实测客户端的 `passwd` 不是登录密码**（第 1 级从未命中，日志里一直是 `(name)`），但它**跨登录不变**（99248101250，两次登录的 SHA-256 前缀相同）。所以采用**首次信任（TOFU）**：帐号第一次网页请求时把 `passwd` 的 SHA-256 存进帐号 `web_tag`（日志 `BOARD web tag learned`）；之后来自其他 IP 的请求必须带同一个值（`tag`），只知道帐号名的陌生人（空值或猜测值）被拒；与游戏连线同 IP 的请求永远放行并重新学习该值（`ip`，值变了也不会锁死）。残留风险：在车主第一次网页请求之前就先打到服务器的人；`passwd` 若可由公开信息推出则等于没有防护（值的来源尚未逆向）。
- 帐号一旦发来**登录密码**（第 1 级）则标记 `web_pw`，之后只认密码或同 IP。
- 若玩家换电脑/重装导致值变化：在游戏里登录后，用与游戏连线同 IP 的网页请求会自动重新学习；GM 也可在帐号表里删除 `web_tag` 重置。
- 读信 / 删信请求只带名字：我们给出的每个信件链接都带**签名令牌** `&k=`（HMAC-SHA256(帐号|信件号, 密钥) 前 16 位；密钥在 `board.json` 的 `_secret`，随机，不进 repo）。令牌对得上就放行（无需 IP），对不上则回空页 / 拒绝。

## 防护（hack 对策）
| 威胁 | 对策 |
|---|---|
| 冒名发文 / 看别人信 | 首次信任的 `passwd` 值绑定（`web_tag`）；密码验证；信件链接签名令牌；改/删只限作者或 GM；公告板只限 GM |
| 往敌国国家板灌水 / 伪造 `nat` | 国家板发文的 `nat` 取自**发文者帐号的国籍**，不信请求参数 |
| 刷屏 | 每帐号 10 秒间隔 + 每小时 20 帖；每 IP 3 秒间隔；寄信每帐号每小时 20 封；同一寄件人在同一信箱最多留 5 封（挤掉真信的洪水无效） |
| HTTP 洪水 | `/b/` 每 IP 10 秒 40 个请求（超过 429）；URL > 4096 字符拒绝（414）；POST 体 ≤ 64 KB、20 秒读完；板数据每板最多 400 帖 |
| 伪造页面标记 / 注入 | 用户文字的 `<` `>` 换成全角或括号；控制字符（除换行）删除；客户端用来切字段的 3 个韩文标记字串在文字输出里被打成 `?`；标题/正文长度限制 60 / 1500 字 |
| 密码泄露到日志 | `ota.py` 记录请求时把 `passwd=` / `f_passwd*=` 的值换成 `***`；失败日志只记「有无密码」，不记值 |
| 数据外泄 | `board.json` 在 `deploy.ps1` 的 runtime 排除表里，不被覆盖，不进 repo；GM 密码仍只以加盐哈希存在服务器 |
**已知局限（需要 HTTPS 才能消除）**：原客户端把登录密码明文放在 GET 的 URL 里（urlmon / HTTP，更新端口 3001 没有 TLS），线路上任何人都能看到。我们只能保证服务器端不记录它。若要根治：给 3001 加 TLS（客户端 urlmon 支持 https，但基址字串长度只有 38 字符，要换短域名）。还有：国家板的**读取**请求不带身份（客户端只给 `nat=`），知道 `nat` 编号的人能读该国家板。

## 日志（排查用）
- 游戏服务器日志在 `/opt/sgserver/logs/sgserver.log`（不是 journalctl）：`ssh -i $HOME\.ssh\game.pem ubuntu@43.135.15.91 'sudo grep -i board /opt/sgserver/logs/sgserver.log | tail -n 30'`。
- 每个 `/b/` 请求一行：`board GET /b/c/free/lsbbs01.asp q=... ip=... -> 200 1112B`；发文成功 `BOARD free: #N by 'acc' (pw|ip|name): subject`；被拒 `BOARD post denied: ... online=[...] pw=yes|no`。
- PowerShell 注意：ssh 命令用单引号包外层，内层不要再放双引号。

## 排障记录（2026-10-26，当天依序发现）
1. 中文输入：多行输入框（vtable 0x64f724）不在 F22 范围，新补丁 `tools/patch_sg_debug_f35.py`（钩 `00443ad5`，桩在 `.dbgmov 0xeb4400`，首字节存 `0xEAFF04`）。
2. 15 级：见上，服务器等级字节。
3. 发文被拒：IP 不同（上节）。
4. `personal/` 404、`poll/` 404：已补。
5. 注意：仓库根目录的 `SG_debug.exe` 是基础档（旧网址）；板面网址只在 `out/SG_cn|tw|en.exe`（经 OTA 发布后由启动器安装）。
