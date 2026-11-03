# Shattered Galaxy 逆向与服务器重建规划

## 0. 目标
以 SG.exe (v1.8.5.0, 2011-02-08) 为唯一事实来源,还原网络协议、游戏规则与数据格式,重建可让原版客户端连接的私服。

## 1. 已确认的初步事实(静态扫描,尚未用 rea/Ghidra 深入)
- SG.exe:PE32 x86,ImageBase 0x400000,入口 0x20F680,节 .text/.rdata/.data/.rsrc,未发现 UPX/ASPack/Themida/VMProtect 特征(仍需看入口代码确认)。.data 虚拟大小 8MB 而文件仅 128KB,说明有大块全局状态。
- 网络:导入 WSOCK32.dll(非 ws2_32);字符串含 SendEncryptedData、ConnectorKey、ksWaitServerConfirm、"Wrong Lump Packet"、"Server redirecting client..."、"MultiLogin"。结论:自定义二进制协议,带加密/密钥,含多服务器重定向。
- 服务器发现:注册表 SOFTWARE\KRU\Shattered Galaxy、SOFTWARE\Nexon\TacticalCommanders;键 MultiServerAddr%d / MultiServerName%d / MultiServerInfoVersion;硬编码域名 sg0.kru.com、game.kornetworld.com(均大概率已失效,可通过改注册表/hosts/补丁指向私服)。
- HTTP 部分:BBS/邮件走 lsbbs01.asp、lsbbs01_t.asp(HTTP,可单独用简单 Web 服务模拟);Patcher.exe 为 MFC HTTP 下载补丁(Patch\Info、Patch\Script),私服需提供假的"无更新"响应或绕过。
- 资源包:*.dat(dns/hlp/ntt/odv/oml/pam/pam2/pam3/NTF2/NTFB/tc/tc2),格式为"文件数 + 目录 + 名称/偏移"的简单归档,内含 WAV/BIK/XPF/JPG/TXT/NM/POR(Portals.por) 等,待写解包器。
- 反作弊/其他:thidchk.dll、chigamec.dll 为随包 COM DLL,需确认是否参与登录校验。

## 2. 工具链
- rea(morluto/rea):MCP 逆向工具,原生分析需 Ghidra 12.1.x + JDK21+ 或 Hopper/IDA。注意:32 位 x86 PE 支持只在仓库 main,npm 发布版(至 5.0.0)仅支持 x64 PE,所以需从源码/main 构建。
- Ghidra 12.1.x(静态反编译)、x32dbg/x64dbg(动态调试)、Wireshark/Fiddler(抓包)、Frida(Hook send/recv)、Python(协议与封包工具)。
- 云端容器已有 JDK 21 与 Node 22,可跑 rea+Ghidra;动态调试必须在你的 Windows 机器上做。

## 3. 阶段路线图
阶段 A 环境与基线(0.5 天)
 1. 构建 rea main,配置 GHIDRA_INSTALL_DIR/JAVA_HOME,rea doctor 通过。
 2. 对 SG.exe 建立 Ghidra 工程,记录哈希(SHA256)作为基线。
阶段 B 资源包解包(1 天)
 1. 写 dat 解包/封包脚本,导出所有资源;解析 Portals.por、.nm、.xpf、TXT/ASP 文本。
 2. 产出:游戏数据表(单位、地图、传送门)的可读格式。
阶段 C 网络层逆向(3–5 天)
 1. 用 rea 定位 WSOCK32 导入(connect/send/recv/select)的调用者,上溯到封包收发循环。
 2. 还原:封包头(长度/类型/序号)、"Lump Packet"拆包、SendEncryptedData 的加密算法与密钥交换(ConnectorKey)。
 3. 抓包验证(若无官方服,则以 Frida/调试器在 send 前、recv 后 dump 明文)。
 4. 产出:协议规格文档 + Python/Wireshark 解析器。
阶段 D 登录与大厅流程(3–5 天)
 1. 最小私服:能让客户端走通 连接→版本校验→登录→选服/重定向→选英雄→进大厅。
 2. 处理注册表 Server 列表、补丁检查、Patcher 绕过。
阶段 E 游戏逻辑(数周,迭代)
 1. 逐个封包类型实现:聊天、队伍、战场、单位生产/移动/战斗、传送门、经验与升级。
 2. 客户端是否做权威判定还是服务器权威:通过逆向战斗/移动函数确认,决定服务器模拟范围。
阶段 F 持久化与运营(之后)
 数据库(账号、英雄、物品)、管理工具、BBS/邮件 HTTP 模块。

## 4. 风险
- 加密/校验可能与时间或会话相关,需完整还原才能互通。
- 服务器权威逻辑(战斗公式、AI)只能从客户端侧推断,精度需靠对照测试。
- 版权/服务条款:仅限私人研究与互操作用途,不分发原版资源与客户端。

## 5. 下一步(待你确认)
1. 在云端构建 rea + 安装 Ghidra,对 SG.exe 跑首轮分析(需要 GitHub 下载 Ghidra;若被代理拦截,请在你的 Windows 机器上安装)。
2. 或者你在本机安装 Ghidra,我远程指导运行 rea。
