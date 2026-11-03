# Shattered Galaxy 1.8.5 协议目录(自动提取 + 人工核对待办)

帧/加密见 FINDINGS.md。以下 type 均为解密后 payload[0]。字段编码:u8/u16/u32/u64 大端;s8=u8 长度前缀字符串;s16=u16 长度前缀字符串;raw=原始字节。
**客户端发出的包末尾会追加一个 0x00 字节**(FUN_005aa1e0 把 payload 长度 +1)。

## 服务器 → 客户端
分发顺序:FUN_0054a590 → ①FUN_0054a1d0(全局) → ②仅当战场状态 [0x6BA7CC]≠0 时 FUN_004b5670(战场) → ③各界面窗口的虚函数 +0x1C(FUN_00545ca0 递归遍历,未在前两级出现的类型(如 0、1、2)推测由界面窗口处理,待核实)。

| 级别 | type | 处理函数 | 函数体字节 | 引用字符串(线索) |
|---|---|---|---|---|
| 全局 | 0x03 | 0x00548c50 | 680 | [] |
| 全局 | 0x04 | 0x00547b00 | 93 | [] |
| 全局 | 0x05 | 0x00547bb0 | 382 | [] |
| 全局 | 0x06 | 0x00547370 | 112 | [] |
| 全局 | 0x0a | 0x00547d30 | 579 | [] |
| 全局 | 0x0e | 0x00547540 | 698 | [] |
| 全局 | 0x0f | 0x00547f80 | 1057 | ["%s Wrong Nation ID\n"] |
| 全局 | 0x10 | 0x00547b90 | 26 | [] |
| 全局 | 0x11 | 0x005c96b0 | 534 | ["uniudi"] |
| 全局 | 0x15 | 0x00549d30 | 1178 | ["mnsts"] |
| 全局 | 0x16 | 0x005461a0 | 3738 | ["%s Wrong hot key : %d (User : %s)", "%s got invalid unit of type %d", "%s hot key duplication (User : %s)",  |
| 全局 | 0x1f | 0x00545d40 | 699 | ["%s SET_INVENTORY on invalid ID %d. out of ", "(%d) "] |
| 全局 | 0x3a | 0x0057e400 | 470 | [] |
| 全局 | 0x3b | 0x0057e5e0 | 374 | [] |
| 全局 | 0x3c | 0x00547b60 | 47 | [] |
| 全局 | 0x3e | 0x0054fc10 | 399 | ["mrkminf"] |
| 全局 | 0x3f | 0x0054fdb0 | 472 | ["mrkmiu"] |
| 全局 | 0x44 | 0x005c8ff0 | 1307 | ["uniuni1", "uniuni2"] |
| 全局 | 0x5a | 0x00546000 | 152 | [] |
| 全局 | 0x66 | 0x005460a0 | 26 | [] |
| 全局 | 0x7c | 0x005473e0 | 119 | [] |
| 全局 | 0x7d | 0x00547470 | 205 | [] |
| 全局 | 0x8c | 0x005c9520 | 385 | [] |
| 全局 | 0xbf | 0x00547050 | 213 | [] |
| 全局 | 0xca | 0x005460c0 | 219 | [] |
| 全局 | 0xfe | 0x0042eb40 | 238 | ["config"] |
| 战场 | 0x12 | 0x0049e7f0 | 197 | [] |
| 战场 | 0x13 | 0x004aa340 | 258 | [] |
| 战场 | 0x14 | 0x0049ece0 | 148 | [] |
| 战场 | 0x17 | 0x004adf20 | 3206 | ["HR_BGM1.MP3/HR_BGM2.MP3", "HR_BGM8.MP3", "HR_BGM9.MP3", "S_FIELD", "atms.xpf", "atmsb.xpf"] |
| 战场 | 0x18 | 0x004ad4c0 | 20 | [] |
| 战场 | 0x19 | 0x004a5ee0 | 150 | [] |
| 战场 | 0x1c | 0x004a3fb0 | 266 | ["UnitManage Wnd"] |
| 战场 | 0x1d | 0x004a2500 | 189 | [] |
| 战场 | 0x1e | 0x004af1e0 | 1800 | ["fldbctrl"] |
| 战场 | 0x20 | 0x004ac360 | 1183 | ["%s User Name length invalid", "S_HERO_PUT"] |
| 战场 | 0x21 | 0x004a2730 | 135 | [] |
| 战场 | 0x22 | 0x004b0a20 | 5522 | ["%s ERROR On New Position. Unit doesn't exist ID : %d (cnt : %d / %d)", "%s Mission Objective ID doesn't exis |
| 战场 | 0x24 | 0x004a2090 | 447 | ["fldjb1", "fldjb2"] |
| 战场 | 0x25 | 0x004b0040 | 2517 | [] |
| 战场 | 0x27 | 0x004b4980 | 2943 | ["fldhinfo1", "fldhinfo2", "fldinfo5", "fldinfo6", "fldinfo7", "fldinfo9"] |
| 战场 | 0x2c | 0x00569e40 | 63 | [] |
| 战场 | 0x2d | 0x00569d90 | 164 | [] |
| 战场 | 0x2e | 0x00567ea0 | 1192 | [] |
| 战场 | 0x2f | 0x004a63d0 | 563 | ["HR_BGM10.MP3", "Shop Wnd"] |
| 战场 | 0x31 | 0x004a6350 | 61 | [] |
| 战场 | 0x32 | 0x004a5d20 | 114 | [] |
| 战场 | 0x33 | 0x004a6290 | 63 | [] |
| 战场 | 0x34 | 0x004a6310 | 61 | [] |
| 战场 | 0x36 | 0x004a27c0 | 164 | [] |
| 战场 | 0x37 | 0x004a62d0 | 61 | [] |
| 战场 | 0x38 | 0x004a6390 | 61 | [] |
| 战场 | 0x39 | 0x004a23b0 | 329 | [] |
| 战场 | 0x42 | 0x0049ebe0 | 242 | ["fldltu"] |
| 战场 | 0x43 | 0x00567300 | 226 | [] |
| 战场 | 0x45 | 0x004a6e20 | 252 | ["fldpmv1", "fldpmv2"] |
| 战场 | 0x47 | 0x004a2290 | 275 | ["fldhsts"] |
| 战场 | 0x48 | 0x004aadf0 | 566 | [] |
| 战场 | 0x49 | 0x004a1f80 | 267 | ["%s Mission Objective ID doesn't exist : %d\n"] |
| 战场 | 0x4b | 0x004a19b0 | 160 | [] |
| 战场 | 0x4c | 0x004a1a50 | 230 | [] |
| 战场 | 0x4d | 0x004a1b40 | 184 | [] |
| 战场 | 0x50 | 0x004ad4e0 | 163 | ["Delayed Put"] |
| 战场 | 0x51 | 0x004a6d70 | 167 | [] |
| 战场 | 0x52 | 0x004a4d20 | 28 | [] |
| 战场 | 0x53 | 0x004a9470 | 142 | [] |
| 战场 | 0x54 | 0x004ac000 | 810 | ["fldpyr1", "fldpyr2", "fldpyr3", "fldpyr4"] |
| 战场 | 0x56 | 0x004a4c00 | 129 | [] |
| 战场 | 0x57 | 0x004a4d40 | 122 | [] |
| 战场 | 0x5b | 0x004aaa80 | 509 | ["fldrie1", "fldrie2"] |
| 战场 | 0x5c | 0x004a1da0 | 138 | [] |
| 战场 | 0x80 | 0x004a8fd0 | 339 | [] |
| 战场 | 0xc5 | 0x004b2610 | 516 | ["%s has left this battle.", "fldsr"] |
| 战场 | 0xcb | 0x004a1e30 | 329 | ["fldbwl"] |
| 战场 | 0xcc | 0x004afd80 | 684 | ["fldcuo"] |
| 战场 | 0xfc | 0x004b4720 | 605 | [] |
| 战场 | 0xfd | 0x004390b0 | 1566 | ["chatcct", "ctrl0", "ctrl1", "runscript"] |

另有无参调用未被正则捕获的:战场 0x12→0x49E7F0,0x1C→0x4A3FB0,0x24→0x4A2090(已在表中)。

## 客户端 → 服务器(SendCatalog 自动提取,同 type 多行=不同发送点)

| type | 字段(去重) | 发送点数 | 示例函数 |
|---|---|---|---|
| 0x00 | [u16, u8, u8, u8] | 1 | 0x005a5c50 |
| 0x02 | [s8, s8, s8] | 2 | 0x00557ef0 |
| 0x03 | [s8, s8]<br>[s8, s8, u8, u32, u32] | 2 | 0x00432fc0 |
| 0x04 | [u32, u8, u8, u8] | 2 | 0x00558360 |
| 0x05 | [raw, u8, u32, u32] | 1 | 0x00548c50 |
| 0x07 | [s8, s8, s8] | 2 | 0x004323a0 |
| 0x09 | [u16] | 1 | 0x0055dde0 |
| 0x0a | [s16] | 2 | 0x0047e540 |
| 0x0b | [u8, u8]<br>[u8] | 2 | 0x0059b6b0 |
| 0x0c | [] | 1 | 0x00547b00 |
| 0x0d | [u16] | 2 | 0x00562370 |
| 0x0e | [u8, u32]<br>[u8] | 3 | 0x00547130 |
| 0x0f | [] | 1 | 0x00547820 |
| 0x11 | [u8, s8] | 1 | 0x004fec20 |
| 0x12 | [u8] | 6 | 0x0049e6e0 |
| 0x13 | [u16] | 1 | 0x005478f0 |
| 0x15 | [] | 2 | 0x004a2680 |
| 0x16 | [u32, u16, u16, u16, u8] | 1 | 0x004de6e0 |
| 0x17 | [u32, u8, u8] | 1 | 0x004de840 |
| 0x18 | [u8, u32, u16, u16, u16, u16, u8, u16, u16, u8, u16, u16, u16, u16, u16, u16, u16, u16, u16, u64, u32, s8, u32, u16] | 1 | 0x004e1cf0 |
| 0x19 | [u8, u8, u32, u8, u32, u8]<br>[u8] | 2 | 0x004ee510 |
| 0x1b | [u8, u32, u16, u16]<br>[u8, u32]<br>[u8, u32, u16, u16, u32] | 4 | 0x0049f760 |
| 0x1d | [u32, u16, u32, u16, u16, u8, u16, u16, u16, u8, u8, u8, u8, u32, u32, u16, u16, u32, u32, u32, u32, u32, u32, u8, u32, u8, u8, u32, u16, u32, u8, u16, u16, u16, u32, u32, u8, u32, u16, u16, u16, u32, u32, u8, u32, u16, u16, u16, u32, u32, u8, u8]<br>[u16, raw] | 2 | 0x004a9890 |
| 0x1e | [u32] | 1 | 0x004de930 |
| 0x1f | [u32, u8] | 1 | 0x004a4250 |
| 0x20 | [u8, u32]<br>[u8, u32, u32]<br>[u8, s8] | 7 | 0x0049f130 |
| 0x21 | [u32, u8, u16, u16] | 1 | 0x004e1f60 |
| 0x22 | [u32, u8, u16, u8, u16, s8] | 2 | 0x00513da0 |
| 0x23 | [u8, u32]<br>[u8, s8] | 2 | 0x0049e4e0 |
| 0x25 | [u8] | 1 | 0x005e0cf0 |
| 0x29 | [u32, u32] | 1 | 0x004e1be0 |
| 0x2a | [u8, s8, u8, u8, u8]<br>[u8, s8, s8, u8, u8, u8]<br>[u8, u8, s8, s8, s8, u8, u8, u8]<br>[u8, u8, s8, s8] … | 6 | 0x00401da0 |
| 0x2b | [u8, u8] | 2 | 0x00565530 |
| 0x2c | [u32] | 1 | 0x005656f0 |
| 0x2d | [u32, u8, u8, s8]<br>[u32, u8, u32]<br>[u32, u8] | 4 | 0x004842d0 |
| 0x2e | [u32, u16, u16, u8]<br>[u32, u8] | 7 | 0x004a6940 |
| 0x2f | [u32, u16, u32, u32, u16, u16, u16, u16] | 1 | 0x004e1990 |
| 0x30 | [u32, u8]<br>[u32, u8, u16, u16]<br>[u32, u8, u32]<br>[u32, u8, u8] … | 60 | 0x004dd860 |
| 0x32 | [u8, u32]<br>[u8, s8]<br>[u8] | 5 | 0x0049e460 |
| 0x33 | [u32, u8]<br>[u32, u8, s8, u8, u16, s8]<br>[u32, u8, u8, u16, u8, u16, u8, u32, u8, u16, u8, u16, u8, u16, s8]<br>[u32, u8, s8] … | 8 | 0x0049e9f0 |
| 0x34 | [u32, u8]<br>[u32, u8, u32] | 2 | 0x0049eb60 |
| 0x35 | [u8, u32]<br>[]<br>[u8, u32, u16, u16] | 3 | 0x004a9130 |
| 0x36 | [u32, u8, u8, u8, u16, s8, s8, s8, u32]<br>[u32, u8, u8]<br>[u32, u8, u8, s16]<br>[u32, u8, u8, s8] | 12 | 0x0047b7e0 |
| 0x37 | [u8]<br>[u8, u32]<br>[u8, u32, u8]<br>[u8, u32, u8, u8] | 4 | 0x0049eaf0 |
| 0x38 | [u32] | 1 | 0x004a6610 |
| 0x39 | [u8, u8]<br>[u8, u16, u16] | 2 | 0x0049ea70 |
| 0x3a | [u8] | 1 | 0x0049e110 |
| 0x3b | [] | 1 | 0x0057d410 |
| 0x3c | [u32, u16] | 1 | 0x0057d2d0 |
| 0x3d | [u16] | 1 | 0x00547880 |
| 0x3e | [u8, u16] | 1 | 0x004f57d0 |
| 0x3f | [] | 1 | 0x0054ecb0 |
| 0x40 | [u16, u16, u16, u8, u32, u32, u8, u16] | 1 | 0x00463880 |
| 0x41 | [u8, u8]<br>[u8, s8] | 2 | 0x00401ed0 |
| 0x42 | [] | 2 | 0x00556190 |
| 0x43 | [u8, s8, s8] | 1 | 0x00574960 |
| 0x44 | [u8] | 1 | 0x005a68f0 |
| 0x45 | [] | 1 | 0x00557af0 |
| 0x46 | [u16] | 1 | 0x005c5fc0 |
| 0x47 | [u8, u8] | 1 | 0x00547a60 |
| 0x48 | [u16] | 1 | 0x0049f800 |
| 0x4b | [u16, u16, u16] | 1 | 0x0049e090 |
| 0x4d | [u8, u8] | 1 | 0x005e7d00 |
| 0x52 | [u32, u16, u16] | 1 | 0x005e88c0 |
| 0x53 | [] | 1 | 0x004a6f20 |
| 0x54 | [] | 1 | 0x004a4f30 |
| 0x55 | [u8, u8, s8]<br>[u8, s8, s8, s8, s8, s16]<br>[u8]<br>[u8, u8, u32, u8, s8, u32, u32, u16, u8, s8, u16, u16, u8, u16, u16, s8, u32, u32, u16, u8, s8, u32, u8, u32] | 6 | 0x004a9670 |
| 0x56 | [u32, u8] | 1 | 0x004347d0 |
| 0x57 | [s8] | 2 | 0x0055c750 |
| 0x58 | [u32] | 1 | 0x0049eff0 |
| 0x59 | [] | 1 | 0x0049f0d0 |
| 0x5a | [u32, u8, u32, u8] | 1 | 0x004a41b0 |
| 0x5c | [u8, s8, u8]<br>[u8, u8, u32, u16]<br>[u8, u8]<br>[u8, s8] | 4 | 0x004aaa80 |
| 0x5d | [s8, u32, u16, u16, u32, u32, u32, u32] | 1 | 0x0058a7c0 |
| 0x5e | [u32, u32, u8, u32] | 1 | 0x0058ae10 |
| 0x60 | [u8, u8, u8, u8, u8, u8, u8, u8] | 1 | 0x004a2910 |
| 0x7b | [u32] | 1 | 0x00548bb0 |
| 0x7c | [u32, raw] | 1 | 0x005472c0 |
| 0x7e | [s8, u8] | 1 | 0x00548510 |
| 0x80 | [u8] | 1 | 0x00562260 |
| 0xc0 | [] | 1 | 0x00533590 |
| 0xc1 | [] | 1 | 0x00533530 |
| 0xc2 | [s8, u8] | 1 | 0x00533440 |
| 0xc3 | [s8] | 1 | 0x005334c0 |
| 0xc4 | [u32, u8] | 1 | 0x00590ce0 |
| 0xc5 | [u8] | 1 | 0x00590d60 |
| 0xc6 | [] | 1 | 0x00590dd0 |
| 0xc7 | [s8] | 1 | 0x00590e30 |
| 0xc8 | [] | 1 | 0x00590c80 |
| 0xc9 | [u8] | 1 | 0x005922b0 |
| 0xca | [] | 1 | 0x00590b30 |
| 0xcb | [u32, u16, u16] | 1 | 0x0049e3d0 |
| 0xcc | [] | 1 | 0x0049e370 |
| 0xce | [s8, u8, u32] | 3 | 0x00581780 |
| 0xcf | [s8] | 2 | 0x00538ef0 |
| 0xd0 | [u8, u8] | 1 | 0x00590c00 |
| 0xd4 | [s8] | 2 | 0x00432fc0 |
| 0xd5 | [u8] | 1 | 0x00590b90 |
| 0xd6 | [u8] | 1 | 0x005e0d80 |
| 0xfc | [] | 1 | 0x0049e560 |
| ? | []<br>[u8, s8]<br>[s8, s8, s8]<br>[u8, u16, raw] | 4 | 0x004017c0 |

## 已知的登录阶段(人工阅读)
- 客户端 type 3 = 登录:`s8 账号, s8 密码`(FUN_00432fc0 状态 6);type 0xD4 = 另一种登录:`s8 …`(通行证模式,后接 FUN_004328f0/4329b0 保存凭据)。
- 客户端 type 2 = `s8,s8,s8`(注册新账号,FUN_005a1690);type 7 = `s8,s8,s8`(带 "Failed to confirm password",改密)。
- 客户端 type 0 = 握手回应:`u16, u8, u8, u8`(FUN_005a5c50 内,疑似版本号/校验);type 0x0B `[u8 1]` = 校验失败回报。
- 服务器 type 0 带子码,FUN_005a5c50 中可见:子码 0(含校验计算,客户端回 0x0B 或继续)、1(客户端回 0x15)、2(启动参数含 "stunt3"/"stunt4");各子码含义为推测,待还原。
- FUN_005a5c50(370 行)是登录期的主接收函数,下一步完整还原它。

## 登录握手(第 3 轮,来自 FUN_005a5c50 / 548c50 / 5a8900 / 5485d0 反编译,尚未用真实流量验证)
1. 客户端 connect(IP 在 [0x6BA840+0x4C0],端口 [0x6BA840+0x4BC])。IP 可写成点分十进制,也可是主机名(gethostbyname)。
   主机名解析失败时回退:名称 "Galaxy"、端口 3000(0xBB8)、IP 64.124.47.70;失败后二次尝试用硬编码主机 sg0.kru.com(FUN_0042FFF0)。
2. 服务器先发一个**明文帧**,payload 含文本 `SERVER CONNECTED`(客户端用子串查找 FUN_0060AB80 判断)。
   客户端收到后调用 FUN_005A8900,把接收端切到"加密模式"([sock+0x20]=1):此后类型不在 {0,3,0xB,0xC,0xD} 的服务器包必须加密。
   (切换前所有包都按明文处理。)
3. 客户端立即回 type 0:`u16 版本号, u8 0x57('W'), u8 0x01, u8 国家码`,末尾 +0x00。
   **真实抓包(已验证)**:`aa 0007 00 00b9 57 01 4b 00`,即版本号 0x00B9(=185,客户端 1.8.5),国家码 0x4B('K',等于注册表 SG_TYPE=K)。
   (更正:早先读反编译误以为恒为 0x7B;Ghidra 在 free 调用处截断了流程,0x7B 只是读版本失败的默认值。)
4. 服务器应答(客户端接收端 FUN_005A5C50,按 payload[0],[1] 分派):
   - `00 00 <u32 校验>`:客户端用本地缓存的服务器列表算 16 位校验(FUN_004338E0)与之比较;相等→直接进入登录界面(FUN_005A28E0),
     不等或缓存为空→客户端回 type 0x0B `[u8 1]` 请求列表。
   - `00 01`:客户端回 type 0x15(空),并弹出消息(来自窗口内字符串),随后退出(FUN_005450C0 置退出标志)——疑为"服务器关闭/满员"。
   - `00 02`:客户端以 "stunt3"/"stunt4" 参数启动子流程(疑为更新/外部程序)。
   - `0x46 'F'`:服务器列表:`u16 压缩长度, zlib 数据`。解压后:`u8 条目数`,每条 = 8 字节头(b0..b4,b6,b7;b7 与客户端国家码比较,等于或客户端国家码==1 才入列)+ 以 0 结尾字符串
     (`名称;附加:...` 或 `名称:...`)。其余字段含义待还原(FUN_0042CC80 入列)。
   - `0x55 'U'`:FUN_005A55B0(待还原)。
5. 重定向:服务器 type 3 = `u32 IP(**字节序反转**:线上字节为 d,c,b,a 对应 IP a.b.c.d), u16 端口, u8 n, n 字节名称`。
   客户端 Sleep(1000) 后关闭旧连接、连新地址,成功则发 type 5:`name 原始字节, u8 1, u32 [0x6BA840+0x4C4], u32 OS 信息(平台ID/主版本/次版本 各 1 字节)`。
6. 登录(登录界面状态 6,FUN_00432FC0):type 3 `s8 账号, s8 密码`;通行证登录用 type 0xD4。

## 真实流量已验证(第 4 轮)
- 帧头 0xAA + u16 长度 ✔;客户端 type 0 为明文 ✔;客户端发出的 payload 末尾确有一个多余的 0x00 ✔。
- 客户端 type 0x0B(`0b 01 00`)不在明文集合内,需解密 ✔(我方自测;真实流量待证)。
- 服务器列表 0x46 条目格式(来自反编译,待游戏内验证):`u8 id, IP 字节倒序(d,c,b,a), u8 未用, u8 b6, u8 b7(国家过滤,默认 [d60]==1 全通过), "名称;说明:" \0`。

## Field/movement findings (session 3)
- Server 0x0E sub4 `[0E 04 flag u8][time u32]` (sent after entering field) sets client +0x25a4 = orders enabled. Without it no order is ever sent.
- 0x18 PUT_UNIT: u16 at "+0xc" (after the three u32 uid/nation/nation) must be non-zero, 0 = unit is killed on arrival (explB flame + corpse).
- kind 0 = hero (art H###, cls = hero class, e.g. cls 1 = H001), kind 1 = combat unit (g###).
- Client -> server orders are batched in 0x80: `[80][flag 0|1 (1=zlib)][b2][u16 count]{u16 len, msg}*`. Hero move msg = `16 [u32 uid][u16 x][u16 y][u16 p][u8 flag]` (pixels). Other periodic msg 0x18 = position report.
- Server -> client lump: `[80][00][b0][u32 time][u16 count]{u16 len, msg}*`, inner types 0x1a (move: `[u32 uid][u16 x][u16 y][u16 p][u8 flag]`), 0x1b, 0x23, 0x2b, 0x30 (`[u32 uid][u8 action]...`). Echoing the client's 0x16 as 0x1a makes the unit walk (confirmed).
- 0x22 = per-tick zlib world snapshot (u16 count, 0x38+4N byte records), 0x19 = remove unit.
- Left click sends 0x23 `[01][u32 uid]` (reply not yet known; info panel still empty).
- 0x40 start-planet list record: `u16 id, s8 name, u8 cls, u8 size, i32 angle(1/1000 deg), 3 x s8, u16, u16, u32, u16, u8, u8 OPEN, u32, u8 n, n x u32`, then u16 default planet. If no planet has OPEN!=0 the client (005a43b0) shows "此星球人数已满，不能注册，请换其他星球" (GBK; renders as garbled Hangul with the Korean font).
- Client 0x04 (create hero): `u32 nation, u8 look, u8 look, u8 tactics, u8 clout, u8 education, u8 mech`.
- 0x0F per-nation text records: `u16 n {u32 nation, s8 short, u8, s16 long}`, then `u16 n {u32, u32 nation, u8}` (territory tally into nation +0x158/+0x15c).
- 0x20 S_HERO_PUT trailing bytes: `u8 (+0x360), u8 (+0x364), u8 mark (1 prestige ui-pres*.xpf / 2 cabinet ui-cabi.xpf), u8 rank (insignia frame 0..30 left+right of the name, ui-rtl1/ui-rtr1.xpf, 0 = none)`. Only 0x20 writes mark/rank; a unit created by 0x18 alone shows a random insignia (uninitialised memory). The server now sends 0x18 then 0x20 for the commander.
- Map id -> file (client 00495e30 / 00497c70): 2xxxxxxxx exercise.nm, 4xxxxxxxx Cave1.nm, 5xxxxxxxx rr1.nm, 6xxxxxxxx nbattle.nm; otherwise digit (id/10000)%10: 9 sst.nm, 1..8 mon%d.nm, 0 province map "%08d.nm" % (id % 1e8) with fallback "000"+last 5 digits. Nation capital (+0x110) uses the same id: planet = (id/100000)%1000, province = id%10000.
- Planet record 3 x s8 = tilt vector (must not be (0,0,0)); the following u16 A, u16 B = orbit ellipse axes, u32 = orbital position (see 'Planet record orbit fields').
- 0x18 PUT_UNIT numeric header (after the two strings): `+4 u16 max HP (+0x110)`, `+6 u16 max energy = start energy (+0x108)`, `+8 s8 energy upkeep per second (+0x10c, client FUN_004cfea0; negative = regen; units kind 1/2 only)`, ... `u16 after the 3 u32 (uid, nation, nation) = current HP (0 = dead on arrival)`. A combat unit with 0 energy accepts orders but stops immediately.
- 0x17 also carries `byte +9 battle mode` (RTS controls; 0 = town) and `u32 +0xb battle start, u32 +0xf battle end` (game ticks 1/100 s; end-start must be non-zero or the battle timer divides by zero, 00429490). In battle mode the server must stream 0x80 lumps with the current game time (~10/s) or the client clock stalls.
- 0x2e (client): change map `u32 map id, u16 x, u16 y, u8, u8` (e.g. entering the CTF building -> 200000000 exercise.nm).

## Factory / Lab (confirmed 2026-10-20)

Client -> server
- 0x2d unit shop: `[u32 shop][u8 op]...`  op 1 = enter `[u8]`; op 2 = BUY `[u8][s8 chassis name][u8]`; op 3 = SELL `[u32 unit id][u8]`.
- 0x33 lab: `[u32 shop][u8 op]...`  op 1 = enter; op 6 = UNIT UPGRADE page; op 7 = EQUIP ITEM page `[s8 unit name]`;
  op 5 = COMPLETE UPGRADE `[u32 unit id][s8 target][s8 target][u8]`.

Server -> client
- class-A 0x44 unit table (answer to 0x46): `u16 n {u16 classid, s8 name}`, `u16 n {u8 art type (0 h,1 g,2 a,3 d), u8 art number,
  u16 classid (/100 = factory tab), s8 name, u16 WEIGHT, u16 SPACE, u16, u64, 5 x u16, u8, u16, u16}`.
  The name is what the client shows (no code->name table in SG.exe; real names only in hlp.dat InfoTbl.txt).
- 0x2f '@' shop: `u32 shop, u8 N {u8,u8,u8, s8 name, 5 x u32 price}, u8 M own {u32 unit id, 5 x u32, 5 x u32}`; pad art = (type, number) from 0x44.
- 0x15 commander: u32 slots 2..6 = money/ore/silicon/uranium/sulfur; byte +0x2a -> [0x471] = MAX UNITS ("UNITS (CUR/MAX)").
- 0x16 roster: sub 1 full list (u8 n), sub 2 add one, sub 3 remove `[u32 id]`, sub 4 update one. Record starts
  `u32 id, u8 art type (1 g/2 a), u8 art number, u16, ...` and ends with two s8 names.
- 0x33 sub 2 upgrade tree: `u32 shop, u16 n {u8 type, u8 num, s8 unit, u8 m {u8 type, u8 num, s8 target, u8 REQUIRED UQ, 5 x u32 price, u8}}`.
- 0x33 sub 1 `[u8 ok]`: result of an upgrade (1 = success path, 0 = failure message).  Re-sending sub 2 while the
  upgrade window points at the upgraded entry throws a C++ exception (crash report 0x0a: Focus UnitUpgradeWnd).
- 0x33 sub 0 item list: items are looked up in a client item database that the server has not sent yet -> nothing shows.

## Item database / unit stats (confirmed 2026-10-20 on the Lab screens)
- class-A 0x10 item DB (answer to client 0x13 [u16 cached crc]; cached as IINF.udf): `[0x10][u8 parts][u8 idx][u16 len][chunk]`;
  data `u16 n {s8 name, u16 id, u16 SLOT, u8 TECH LEVEL, u16 WEIGHT, u16 SPACE, u16 COMPLEXITY, u16 energy?, u16, u8 type,
  type extras}`, then `u8 a, u8 b, b*a u16` (damage modifier table, FUN_005261b0).  Weapon extras = `u16 damage,
  u16 range x20, u16 cooldown x100, u8 flags (1 ground, 2 air)`; engine extras = `u16 health, u16 power`.
- Slot ids = equip.txt per chassis art and the official manual page numbers (I-G4004 = Imp weapons).
- Lab item list = 0x33 sub 3 `u32 shop, s8 unit name, u16 n {u16 item id, u8 0 (must be 0), 5 x u32 buy, 5 x u32 sell}`.
- 0x16 unit record: 9 x u16 block A [0] Health, [4] max Weight, [5] max Space, [7] Speed x10; block B [0] Armor.

## Nation relations / hostility (class-A 0x05)
- Client handler FUN_00547bb0: `[05][u8 0][u8 n]{u32 nation a, u8 m, m x {u32 nation b, u8 state}}` (full list, clears the map first) or `[05][u8 1][u32 a][u32 b][u8 state]` (one entry). Stored in CNationInfo (DAT_006ba80c) map (a,b) -> state.
- Afterwards FUN_005521d0 rebuilds the group table (+0x18 int[max id+1], +0x1c max nation id from the 0x0F table): group[i] = i, pairs with state 1 (Ally) are merged. Player objects get +0x358/+0x35c = group(nation).
- PUT_UNIT (FUN_004d3050) stores unit +0x350/+0x354 = the two nation u32s and +0x358/+0x35c = their groups (0 when the table is empty or the id is out of range).
- Friend test FUN_004c52b0(a, b): in battle mode 3 with flag +0x29bdc -> same owner name; otherwise group(nation2 a) == group(nation2 b).
- => Without a 0x05 packet every nation is group 0 = all units friendly (no red units, no attack). The server now sends `05 00 00` after every 0x0F.

## PUT_UNIT battle stats (0x18 +0xe..+0x1e, 9 x u16) — CONFIRMED 2026-10-20
- CORRECTION: [0] ARMOR (+0x11c, FUN_004cb080 = defender armor used by damage calc FUN_004d0420)  [1] armor class (+0x130, damage table row)  [2] damage type 1xx..6xx (+0x120)
- Movement speed = header u16 +9 (+0x14), x10 (default 100 = 10 m/s).
- [3] ground damage (+0x134) [4] ground range x20 (+0x138) [5] ground cooldown x100 (+0x13c)
- [6] air damage (+0x140)    [7] air range x20 (+0x144)    [8] air cooldown x100 (+0x148)
- header +0xb = sight (+0x114); attack needs distance <= range+size AND <= sight+size (FUN_004cad50).
- Right-click attack = FUN_004db110: if target attackable (FUN_004c7d50: damage for target layer != 0) and in range -> lump 0x29 [uid][target]; otherwise the unit only walks to the target (lump 0x16). With damage 0 the client never sends 0x29.
- The 0x16 roster block A is a different layout ([0] health, [4] weight, [5] space, [7] speed x10).
- Right-click on a unit (FUN_004a8a10): hovered unit id at view+0x518; for each own selected unit FUN_004dc570 -> FUN_004db110. Units that can not attack are listed by name in a chat message.
- PUT_UNIT +0x22 u64 = ABILITY bits (+0x158/+0x15c). FUN_004d49a0 builds the unit's command list: 0 and 1 always; 2 = ATTACK if bit 1 set and damage > 0 (and bits 0x15/0x25/0x35/0x36/0x38 clear); every other bit adds a skill command (e.g. +0x158 bit 31 -> cmd 4/5, bit 21 -> 6/7, +0x15c bit 12 -> 0x2c/0x2d ...). Without bit 1 there is no attack button and right-click on an enemy only moves.

## Strategic map / provinces / caves (2026-10-20)
- Client 0x2b [u8 0][u8 same-planet] = open/refresh strategic map (FUN_00565530, throttled 5 s) -> server 0x2d.
- Client 0x2c [u32 province] = info on the selected province (FUN_005656f0; strategic map selection FUN_00461960). Reply = class-B 0x2e (see ARCHITECTURE.md section 6).
- Client 0x2e [u32 map][u16 x][u16 y][u8][u8] is sent by FUN_004a6940, called from the class-B 0x35 handler (004a9130): the server can order a map change with 0x35. Walking into portals also sends 0x2e.
- Server 0x2d now lists all 85 provinces of the planet (layout 2 grid) with owner (0 = aliens) and the commander's location; ownership persisted in server/world.json.
- Map kinds: <100000000 province (own nation = town, otherwise alien battle -> capture on victory), 2xxxxxxxx CTF/training (passive targets), 4/5/6xxxxxxxx caves (repeatable alien battles).
- Aliens: server-owned units, nation 0, organic ground art (g011/g015/g024/g025); the server AI sends lump 0x2b [alien][target] so the clients simulate their attacks. Player unit death = client lump 0x1e [uid] (expected; to verify). Own unit HP report = client lump 0x21 [uid][01][u16 hp] -> stored as the unit's HP after battle; repair cost = 40 % price x damage fraction.
- 0x16 roster record, CONFIRMED 2026-10-20: block A[0] = max HP, block A[1] = CURRENT HP (Factory "cur/max" and health bar). The u16 after the art bytes is not HP (1). Non-zero values in the other unknown slots made the Lab unit list empty ("You don't have any Infantry units").
- Client 0x25 [+tactics][+clout][+education][+mech] = F4 attribute points spent (FUN_005e0cf0).
- Server 0x27 sub 0 = F4 INTROSPECTION, fields confirmed on screen (see build_hero_info).

## Planet record orbit fields (CONFIRMED 00460d00/00459d30/00401270/00401560)
After the 3 x s8 orbit (tilt) vector: u16 A = ellipse semi-major, u16 B = semi-minor (focus sqrt(A^2-B^2); need A>=B>0),
u32 C = orbital position (1/1000 deg), u16 D, u8 flag (+0x7c, must be !=0 for star-gate travel), u8 open.
Planet pos = Rot(tilt) * ellipse(A,B) at angle C. Sun: size 20 at origin. Star gate range u16 is in the same units.
Client star gate travel checks: distance<=range (skipped for nation 5 or own-capital planet), header enabled,
+0x7c flag, not warping, target != current. No level/tier check client-side.
See also progression_tutorial_notes.md (StarCenter 0x31/0x37, tutorial state machine).

## StarCenter (Faction Pledge Center) - implemented 2026-10-20
client 0x37 [00] -> server 0x31 [00] u8 nPlanets {planet rec, detail flag 0} u8 nNations {u32 nation, u16, u8,
u16 WAIT, u8 PENALTY, s8 name, u8, s16 description, u8 MODE}; or 0x31 [01] s16 message box.
client 0x37 [05][u32 nation][u8 pen] join, [0a][u32 nation] visit, [0b][u32][u8][u8] reincarnate.
Strings: FUN_005a9ff0 = s8 (u8 len), FUN_005aa060 = s16 (u16 len).
0x15 [0x480] = founding planet (now sent = capital planet). Nations 11-14 (Advanced, planet 2), 21-24 (Elite, 3).
- 0x2e province info: u32 pid, u8 THEME (+0x48), u8 CAPITAL flag (+0x28), u8 (+0x29) -> preview map loaded with
  FUN_00498b20(pid, theme, capital, 1) (00437370). Capitals need CAPITAL=1 (else crash 0x8d533 on planet 2).
- 0x17: u32 map, u8 capital, u32 MAP OWNER nation (+0x29bd4; FHQ portal type 7 access + friendly territory).

## Map terrain theme & POCs (CONFIRMED 2026-10-20)
- .nm map = u8, u16 w, u16 h, w*h x {u16 tile, u8}, u16 n objects {u8 x, u8 y, u16 type}. Tiles with 0x4000 are
  abstract and remapped by FieldMap.mp theme (9..13). Maps using only indices <= 413 (A1-*, Capital, Z1/3/4, Free,
  rm01/2, E4-1, sst, rr1, nbattle) are the theme-13 family; others need 9..12. vinu.inf says 12 for A1-* -> server
  sends 13 for them (else mosaic).
- 0x17 full layout: u32 map, u8 capital, u32 owner, u8 battle, u8, u32 start, u32 end, u8 battle kind, u8 THEME,
  u8 nPOC, nPOC x {u32 id, u16 x px, u16 y px, u16 STRENGTH, u8 TYPE, u32 OWNER nation}.
- POC capture is simulated client-side (0048f340): progress starts at STRENGTH, -5 per update while an enemy-group
  unit stands on it, <0 -> owner = that unit's nation. Server 0x49 [u32 id][u16 progress][u32 owner][u8 capturing].
- Client 0x2f [u32 unit][u16][u32 0][i32 target map][4 x u16] = unit reached an exit portal (retreat).
- Server 0x19 [u32 uid][u32 0] = remove unit from the map.

## Implemented 2026-10-20 (details in research_skills.md / research_multiplayer.md / research_honor_medal.md)
- Battle result: class-B 0x25 (layout in sgserver.build_battle_result; RESULT 0 = victory, 1 = defeat).
- Skills: PUT u64 ability bits from item 'Special' (SPECIAL_BITS) + CHASSIS_SKILLS; client lump 0x30 relayed
  unchanged; server simulates skill damage on aliens (on_skill).
- Reincarnation: StarCenter MODE 1 rows on the Elite planet; 0x37 [0b][u32 nation][u8 pen][u8 pic];
  0x15 [0x47d] = count, 0x20 rank byte = count (name-side mark), unit cap +2 per reincarnation.
- Medals: 0x27 {u32 id = N*1000 (dcr-%03d.xpf), s8 text}.
- Multiplayer: unique hero uid per account, unique unit ids; MAP_PEERS / BATTLES; join permission 0x24 ->
  client 0x20 [type+2 accept | type+1 reject][s8 name]; leave = 0x19 [uid][0] + 0xc5 [s8 name];
  client 0x54 forced retreat; 0x0E [01][ms] -> [01][ms][game time]; client 0x5a POC report (logged).
- Reinforcement (F7): client 0x19 [00] -> server class-B 0x50 [u32 frame][PUT body] for reserve units (to all
  participants) or 0x5b [02][00][u16 s] "You can reinforce after %d seconds". (client 0x5c [02][k]... belongs to a
  3-item-slot battle window, not to reinforcement.)
- Battle control: class-B 0x1e [u32 map][u8][u8][u32 defender][s8 title][u8 n {s8, u32 nation, u32}][u8 timeout][u8]
  -> client 0x1b [01 ATTACK|02 ASSIST][u32 map][u16 x][u16 y] (+0x48), 0x20 [01|07|08][map] join, [0d][map] watch,
  [04][map][u32 side] mercenary offer.  0x24 [type][s8 name][s8] to the commander.
- Mercenary: client 0xd6 [u8 on/off].
