# SG.exe v1.8.5 逆向发现(第 1 轮)

目标:SG.exe,SHA256 3825326231cf4b63ce3bf4cf88a312b5930c88611d3897259f610289f680900b,PE32 x86,ImageBase 0x400000。
Ghidra 12.1.4 自动分析:16022 个函数、4179 个字符串。以下地址均为 Ghidra 中的虚拟地址。

## 1. 网络栈(纯客户端)
- WSOCK32 按序号导入:accept/bind/listen 均不存在(只有 client)。
  序号对应:19=send 16=recv 4=connect 23=socket 3=closesocket 9=htons 52=gethostbyname 57=gethostname
  101=WSAAsyncSelect 111=WSAGetLastError 115=WSAStartup 116=WSACleanup。
- 全部收发集中在 0x5A8530–0x5A9B60,类 CSocket(单例,全局指针 0xC32CC0,构造 0x5A9E80)。
- 连接线程 0x5A97C0:socket → connect → 按"连接模式"(全局 [0x6BA840+0xC3C])发握手 → WSAAsyncSelect。
  模式 1 发字符串 "taccom\n"(经 0xAA 帧);4 发角色/账号名(长度前缀 u16);5 加载 chigamec.dll!SendEncryptedData;
  8/9/10 加载系统目录 cjconnector.dll!ConnectorKey(合作方门户登录);0xB、0xD 为其他流程。
- 接收缓冲 0x40000 字节(0x5A8A80),异步消息:0x402=收到完整包,0x403=连接断开。
- 日志格式串 "S_%d O_%d Packet Too Long. Type : %d"、"CheckSumError at packet No : %d" 可用于定位对应分支。

## 2. 封包格式(已还原并往返测试)
    0xAA | len16 big-endian | payload[len]      len ≤ 0x3FFDF
payload[0] 是封包类型。
- 客户端→服务器 明文类型:0,1,5,6,0x0D。其余类型走加密(见下)。
- 服务器→客户端 明文类型:0,3,0x0B,0x0C,0x0D。其余走解密。
- 加密载荷(原长 n)变为 n+3 字节:type | seq | body' | chk1 | chk2
  - seq:发送计数器(0x00D69270,从 0 起,每包 +1,字节回绕)
  - body = 原载荷去掉首字节;先与密钥按 u32 异或(密钥 = "NexonInc." 重复铺满,9 个 u32 字,下标 i%9,尾部不足 4 字节按字节),
    再把 body 切成 9 字节块,第 k 块异或字节 k(k==seq 的块跳过),最后整体异或字节 seq。
  - chk1 = -(type+seq+body' 的字节和);chk2 = -(原载荷全部字节和)。解码端校验失败会 Beep 并 _exit(0)。
- 密钥为静态字符串 "NexonInc.",没有握手期密钥交换 → 服务器可以直接实现。
- 实现与自测:tools/sgproto.py(往返测试通过;尚未用真实抓包验证,自洽性来自编码与解码两个独立函数互为逆运算)。

## 3. 外部依赖
- chigamec.dll(随包):导出 SendEncryptedData,模式 5 登录用。
- cjconnector.dll(系统目录,CJ 门户,通常不存在):模式 8/9/10,私服不需要。
- HTTP:lsbbs01.asp / lsbbs01_t.asp(论坛/邮件)、Patcher.exe(补丁)。

## 4. 下一步
1. 找到 WM 0x402 的处理函数,建立封包类型 → 处理函数的分发表(这是协议清单的入口)。
2. 逐个还原登录包:模式 4 的账号包结构、服务器确认 ksWaitServerConfirm、"Server redirecting client" 重定向包。
3. 分析 chigamec.dll!SendEncryptedData 的输出格式(登录模式 5)。
4. 写最小服务器(Python asyncio):监听、解帧、应答登录。

## 第 3 轮补充
- 加密是按"收到 SERVER CONNECTED 后开启"的模式;发送侧是否加密只由 type 决定(明文类型见上)。
- 客户端版本号 = 0x00B9(185,真实抓包验证);更正了早先的 0x7B 误判。国家码字节 = 'K'。
- 默认回退服务器 64.124.47.70:3000("Galaxy");硬编码备用主机 sg0.kru.com。
- server/sgserver.py:探测服务器——发 SERVER CONNECTED,记录并解码客户端发来的每个包。

## Round 5: login -> field (verified against real client)
- Server packet 0x02 `02 00` = ok, `02 <code!=0> <s8 text>` = error (register: FUN_0055d090, login: FUN_00431c30). The text is read from the packet, so error replies MUST carry an s8 string.
- Server 0x0F = nation table (FUN_00547f80); Continue waits until it arrives. New-commander "birth point" = nation. Server 0x40 = start-planet list (FUN_0055bea0).
- Client posts its own crash dump to the server as type 0x0A (s16 text), e.g. "ACCESS_VIOLATION ... EIP". Decode it in the log; it gives EIP and a call chain.
- Field (0x17) map file is chosen from the map id: 200M-300M exercise.nm, 400M-500M Cave1.nm, 500M-600M rr1.nm, 600M-700M nbattle.nm, digit(10^4)==9 sst.nm, else mon%d.nm or a table lookup (FUN_005dc190). Files live in pam.dat / pam3.dat. An unknown id crashes the renderer at 0x60AEAA (memcpy in FUN_0048e710).
- Client keep-alive 0x58 [u32 tick] every 5 s; after login it also asks 0x46, 0x3b, 0x3f, 0x2b.

## Round 6: resource archives (.dat) — tools/sgdat.py
- Format: u32 LE count; count x 17-byte entries (u32 LE start offset + name[13]); file i = [off_i, off_{i+1}), last = EOF; last entry is an empty-name sentinel.
- pam.dat = *.nm maps (ids like 00000000.nm + named ones: exercise.nm, Cave1.nm, mon*.nm), pam2.dat = portals.por, FIELDMAP.MP/TS, 188 x S####.sta/stb/stc (star systems), pl-*.xpf, sn*.xpf; pam3.dat = more .nm (rr1, nbattle, sst ...).
- ntt.dat / oml.dat / hlp.dat / dns.dat(.txt): string tables ("ksKey<TAB>text"), help, equip.txt (chassis g001..g059 -> slot layout), maplist.txt (map file -> name -> battle map id), mcf.txt / CNTRINFO.TXT (province coordinates on the world map).
- tc.dat / tc2.dat / NTF2.dat / NTFB.dat / odv.dat: .xpf/.jpg images, .bik videos. dns.dat: .wav/.mp3.
- Server 0x16 (FUN_005461a0): [sub u8 (1=list, 2=add one, 3=remove u32, 4=update)] [count u8] units...; chassis names are like "g001"/"a001".

## New commander "乱码" dialog — root cause (2026-10-20)

**Symptom.** Clicking *New commander* shows a dialog with garbled Hangul, always the same text
(`늪☒헷홍☒☒찮☒껫콘☒꿍☒헝뺏페☒☒헷`).

**Root cause.** It is not garbage: it is a hard-coded **GBK (Chinese)** string in SG.exe at VA 0x0065ce3c,
`此星球人数已满，不能注册，请换其他星球` ("this planet is full, cannot register, choose another planet"),
drawn with the Korean font. The client (FUN_005a43b0, parser of the 0x40 start-planet list) shows it when
**no planet in the 0x40 list has the OPEN flag set**. The flag is the second u8 after
`u16, u16, u32, u16` in each planet record (see PROTOCOL.md). Our server used to send 0 there.

**Red herrings during the hunt.** Capital ids, emblem frames, the +0x150/+0x154 ratio and the 3 extra bytes
were all suspected and bisected; none caused it. The dialog can be dismissed with OK, which is why one run
"worked" with identical data.

**Related client freeze.** The planet arrows (FUN_0055b730 / 0055b850) loop until they find a planet that
has a usable nation; if no nation capital lies on an open planet the loop never ends and the client hangs.

**How it is kept under control.** `server/sgserver.py` holds the data in `PLANETS` (id, name, cls, OPEN),
`NATIONS`, `CAPITALS`, `BEGINNER_PLANET`. `check_world()` runs at start-up and refuses to start the server
(logs `WORLD CONFIG ERROR: ...`) if: no planet is open, an open planet has no nation capital on it, a capital
province code is out of range, or the beginner planet is not open.

## Province grid (vinu.inf, pam2.dat)
`u32 systems {u32 planets {u32 n {i32 col, i32 row, i32 type(12/13), i32, i32 len, char name[len]}}}` (little endian).
1 system, 8 planets (0..7); planets are 8x8 grids except planet 2 (9x9). Province id = planet*100000 + col*100 + row,
the name is the .nm map (CornerA at the corners). Full table: analysis/vinu_provinces.tsv. Entering a map id that is not
in this table gives the client an empty map name -> garbled screen and crash.
The vinu.inf `type` (12/13) is the terrain theme: the client remaps every tile of the loaded map with it
(map object +0x101ca0, FUN_005b2d30 / FUN_005dc6a0; 0x17 can override it, 0 = take vinu's). A map shown with the
wrong theme looks broken/mixed. CornerA is a type-13 map; only planets 0 and 6 list their corners as 13, so the
server's beginner planet is planet 6. (UPDATE: all planets now use layout 2 via 0x43; capitals are the 9x9 corners x00000/x00800/x00008/x00808, see ARCHITECTURE.md.)

## Design decisions (2026-10-20)
- Item prices: NOT from the manual (it has none). Final prices will be derived later from the economy:
  how much money/resources a player earns from field (PvE) drops and from battles (PvP), so item cost
  is a fixed ratio of income per tech level. Until then server/sgserver.py ITEM_PRICE(tl) is a
  money-only placeholder (10 x tech level + 10). Unit prices (Factory) are also placeholders (_price()).
- TODO (UI): after renaming a unit in the Lab the unit list only refreshes after switching pages.
- Planet progression: tiers Novice (planet 6, open) -> Advanced (planet 2, closed) -> Elite (planet 3, closed).
  Commanders start on Novice; at a commander level they can advance to the next tier or reincarnate (rebirth).
  UPDATE: Novice->Advanced via StarCenter once a branch >= 20 (implemented); Elite threshold 50 is a placeholder; rebirth not implemented. See ARCHITECTURE.md section 7.
