"""Server message translations (2026-10-21, phase 1 of the Chinese client: zh-TW / zh-CN).
MACHINE-TRANSLATED DRAFT - to be proofread by the user.  Every entry: (English template, Traditional, Simplified).
'{}' in the English template matches any text; the translations use {0}, {1} ... (order may change).
translate(text, lang) returns the translated text, or the English text unchanged when no template matches.
Resource / common words inside the matched values are translated with GLOSSARY."""
import re

CATALOG = [
    # ---- (2026-10-25 20:49) player commands that were still English
    ("Regiment name: 2-8 Chinese characters or 3-16 letters/digits.",
     "軍團名稱：2-8 個中文字，或 3-16 個字母／數字。", "军团名称：2-8 个中文字，或 3-16 个字母／数字。"),
    ("Invalid or taken name (2-8 Chinese characters or 3-16 letters/digits).",
     "名稱無效或已被使用（2-8 個中文字，或 3-16 個字母／數字）。", "名称无效或已被使用（2-8 个中文字，或 3-16 个字母／数字）。"),
    ("/regiment create|join|leave|rename|open|close|kick|list|who",
     "/regiment create 建立｜join 加入｜leave 離開｜rename 改名｜open 開放｜close 關閉｜kick 踢人｜list 列表｜who 成員",
     "/regiment create 建立｜join 加入｜leave 离开｜rename 改名｜open 开放｜close 关闭｜kick 踢人｜list 列表｜who 成员"),
    ("Your name is now {}.  Other players see it the next time you enter a map.",
     "你的名字已改為 {0}。其他玩家在你下次進入地圖時會看到。", "你的名字已改为 {0}。其他玩家在你下次进入地图时会看到。"),
    ("Your name: {}.  /nick NAME to change it (letters, digits or Chinese).",
     "你的名字：{0}。輸入 /nick 名字 可以更改（字母、數字或中文）。", "你的名字：{0}。输入 /nick 名字 可以更改（字母、数字或中文）。"),
    ("Name: letters, digits or Chinese, at most {} Chinese characters or {} letters.",
     "名字：字母、數字或中文，最多 {0} 個中文字或 {1} 個字母。", "名字：字母、数字或中文，最多 {0} 个中文字或 {1} 个字母。"),
    ("That name is taken.", "這個名字已經有人用了。", "这个名字已经有人用了。"),
    ("That name has characters the game cannot show.", "這個名字有遊戲無法顯示的字。", "这个名字有游戏无法显示的字。"),
    ("Changing your name costs {} Uranium.", "改名需要 {0} 鈾。", "改名需要 {0} 铀。"),
    ("Paid account: you always walk at the fast speed.", "付費帳號：一直都是快速移動。", "付费帐号：一直都是快速移动。"),
    ("Fast walking is active for another {} minute(s).", "快速移動還有 {0} 分鐘。", "快速移动还有 {0} 分钟。"),
    ("Fast walking ({} h) costs {} Uranium.", "快速移動（{0} 小時）需要 {1} 鈾。", "快速移动（{0} 小时）需要 {1} 铀。"),
    ("Fast walking for {} hours (-{} Uranium). It applies the next time you enter a map.",
     "快速移動 {0} 小時（-{1} 鈾），下次進入地圖時生效。", "快速移动 {0} 小时（-{1} 铀），下次进入地图时生效。"),
    ("client {} / release {}", "客戶端 {0} / 最新版本 {1}", "客户端 {0} / 最新版本 {1}"),
    # ---- battle simulation center (2026-10-22)
    ("BATTLE SIMULATION: units are not lost and no experience or resources are gained.",
     "模擬戰：單位不會損失，也不會獲得經驗或資源。", "模拟战：单位不会损失，也不会获得经验或资源。"),
    ("A battle simulation is running on this province. Try again later.",
     "此省份正在進行模擬戰，請稍後再試。", "此省份正在进行模拟战，请稍后再试。"),
    ("Simulations cannot be held in a capital.", "首都不能進行模擬戰。", "首都不能进行模拟战。"),
    ("A real battle is running on this province. Try again later.",
     "此省份正在進行實戰，請稍後再試。", "此省份正在进行实战，请稍后再试。"),
    ("Battle simulation over: everything is back as it was.", "模擬戰結束：一切已恢復原狀。", "模拟战结束：一切已恢复原状。"),
    # ---- aliens / raids / caves
    ("The alien raid on {} was repelled!", "{0} 的外星入侵已被擊退！", "{0} 的外星入侵已被击退！"),
    ("Demon star: {} was retaken by the demon-star monsters.", "魔星：{0} 被魔星怪物奪回了。", "魔星：{0} 被魔星怪物夺回了。"),
    ("Demon star: the monsters strike back at {}! Defend it within {} minutes or it is lost.",
     "魔星：魔星怪物反撲 {0}！請在 {1} 分鐘內進入防守，否則該省會被奪回。", "魔星：魔星怪物反扑 {0}！请在 {1} 分钟内进入防守，否则该省会被夺回。"),
    ("{} was lost to the aliens.", "{0} 已被外星生物奪走。", "{0} 已被外星生物夺走。"),
    ("Aliens are attacking {}! Defend it within {} minutes or it is lost.",
     "外星生物正在進攻 {0}！請在 {1} 分鐘內防守，否則將失去該省。", "外星生物正在进攻 {0}！请在 {1} 分钟内防守，否则将失去该省。"),
    ("Alien garrison of this province: {}%.", "本省外星駐軍：{0}%。", "本省外星驻军：{0}%。"),
    ("Alien garrison of this cave: {}%.  Destroy all {} hives to win!  To retreat, move your units back to the exit portal at your arrival point.",
     "本洞穴外星駐軍：{0}%。摧毀全部 {1} 個孵化巢即可獲勝！要撤退，請把單位帶回落點旁的出口傳送門。",
     "本洞穴外星驻军：{0}%。摧毁全部 {1} 个孵化巢即可获胜！要撤退，请把单位带回落点旁的出口传送门。"),
    ("[Level {} or over cannot gain XP here.]", "[{0} 級以上無法在此獲得經驗。]", "[{0} 级以上无法在此获得经验。]"),
    ("Your units will enter the battle in {} seconds.", "你的部隊將在 {0} 秒後進入戰場。", "你的部队将在 {0} 秒后进入战场。"),
    # ---- uranium / power / star
    ("Daily Uranium reward: +{} (stored {}).", "每日鈾獎勵：+{0}（累積 {1}）。", "每日铀奖励：+{0}（累积 {1}）。"),
    ("Your faction filled its power bar! Uranium +{} (stored {}).", "你的陣營國力已滿！鈾 +{0}（累積 {1}）。", "你的阵营国力已满！铀 +{0}（累积 {1}）。"),
    ("Your faction has no demon-star time. Fill the national power bar first.", "你的陣營沒有魔星時間，請先填滿國力。", "你的阵营没有魔星时间，请先填满国力。"),
    ("The demon stars are open 12:00-13:00 and 19:00-20:00 (server time).", "魔星開放時間為 12:00-13:00 與 19:00-20:00（伺服器時間）。", "魔星开放时间为 12:00-13:00 与 19:00-20:00（服务器时间）。"),
    ("Leave your current battle first.", "請先離開目前的戰鬥。", "请先离开当前的战斗。"),
    ("Black Tortoise: defeat the aliens for rich rewards; the Lab now sells Demon Fire armour.",
     "玄武魔星：擊敗外星生物可獲得豐厚獎勵；研究所現在販售 Demon Fire 裝甲。", "玄武魔星：击败外星生物可获得丰厚奖励；研究所现在贩售 Demon Fire 装甲。"),
    ("Teleport home: {} free use(s) left today.", "傳送回首都：今天還剩 {0} 次免費。", "传送回首都：今天还剩 {0} 次免费。"),
    # ---- chat / commands
    ("Unknown command. Type /help.", "未知的指令，請輸入 /help。", "未知的指令，请输入 /help。"),
    ("{} is not online.", "{0} 不在線上。", "{0} 不在线。"),
    ("Chat commands:  /help regiment  - regiment commands;  /help uranium  - what Uranium buys;  /help star  - demon stars",
     "聊天指令：/help regiment - 軍團指令；/help uranium - 鈾的用途；/help star - 魔星",
     "聊天指令：/help regiment - 军团指令；/help uranium - 铀的用途；/help star - 魔星"),
    ("/star    - enter the Black Tortoise demon star (needs faction demon-star time, 12:00 / 19:00 for 1 h)",
     "/star    - 進入玄武魔星（需要陣營魔星時間，12:00 / 19:00 開放 1 小時）", "/star    - 进入玄武魔星（需要阵营魔星时间，12:00 / 19:00 开放 1 小时）"),
    ("/power   - GM: national power and star status", "/power   - GM：國力與魔星狀態", "/power   - GM：国力与魔星状态"),
    ("Lab sells Demon Fire armour during your faction's 24 h demon-star time", "陣營魔星時間的 24 小時內，研究所販售 Demon Fire 裝甲", "阵营魔星时间的 24 小时内，研究所贩售 Demon Fire 装甲"),
    ("/reset              - return spent attribute points (15 Uranium)", "/reset              - 重置已分配的屬性點（15 鈾）", "/reset              - 重置已分配的属性点（15 铀）"),
    ("F8                  - 5 free teleports home per day, then 5 Uranium each", "F8                  - 每天 5 次免費傳送回首都，之後每次 5 鈾", "F8                  - 每天 5 次免费传送回首都，之后每次 5 铀"),
    ("StarCenter          - switch faction 150 Uranium, reincarnation 30 Uranium", "StarCenter          - 轉換陣營 150 鈾，轉生 30 鈾", "StarCenter          - 转换阵营 150 铀，转生 30 铀"),
    ("/wight, /quorg      - unlock the Wight (250) / Quorg (800 Uranium) in the Factory",
     "/wight、/quorg      - 在工廠解鎖 Wight（250 鈾）/ Quorg（800 鈾）", "/wight、/quorg      - 在工厂解锁 Wight（250 铀）/ Quorg（800 铀）"),
    ("The {} is already unlocked - buy it in the Factory.", "{0} 已解鎖，請到工廠購買。", "{0} 已解锁，请到工厂购买。"),
    ("Unlock the {} in the Factory for {} Uranium? Type /{} yes to confirm.",
     "要花 {1} 鈾在工廠解鎖 {0} 嗎？輸入 /{2} yes 確認。", "要花 {1} 铀在工厂解锁 {0} 吗？输入 /{2} yes 确认。"),
    ("Unlocking the {} costs {} Uranium (you have {}).", "解鎖 {0} 需要 {1} 鈾（你有 {2}）。", "解锁 {0} 需要 {1} 铀（你有 {2}）。"),
    ("The {} is unlocked (-{} Uranium). You can now buy it in the Factory.",
     "{0} 已解鎖（-{1} 鈾），現在可以在工廠購買。", "{0} 已解锁（-{1} 铀），现在可以在工厂购买。"),
    ("Unlock the {} first: type /{} ({} Uranium).", "請先解鎖 {0}：輸入 /{1}（{2} 鈾）。", "请先解锁 {0}：输入 /{1}（{2} 铀）。"),
    ("Alien garrison of this cave: {}%.  Aliens keep appearing around the cave - destroy all {} to win!  To retreat, move your units back to the exit portal at your arrival point.",
     "本洞穴外星駐軍：{0}%。外星生物會在洞穴各處陸續出現，消滅全部 {1} 隻即可獲勝！要撤退，請把單位帶回落點旁的出口傳送門。",
     "本洞穴外星驻军：{0}%。外星生物会在洞穴各处陆续出现，消灭全部 {1} 只即可获胜！要撤退，请把单位带回落点旁的出口传送门。"),
    ("/regiment rename    - 250 Uranium", "/regiment rename    - 250 鈾", "/regiment rename    - 250 铀"),
    ("/regiment create NAME  - found a regiment (money + ore + silicon); max 13 per faction", "/regiment create 名稱  - 建立軍團（金錢 + 礦 + 矽）；每陣營最多 13 個", "/regiment create 名称  - 建立军团（金钱 + 矿 + 硅）；每阵营最多 13 个"),
    ("/regiment rename NAME  - leader: rename (250 Uranium)", "/regiment rename 名稱  - 團長：改名（250 鈾）", "/regiment rename 名称  - 团长：改名（250 铀）"),
    ("/regiment join NAME    - join an open regiment of your faction", "/regiment join 名稱    - 加入本陣營開放中的軍團", "/regiment join 名称    - 加入本阵营开放中的军团"),
    ("/regiment leave        - leave your regiment", "/regiment leave        - 離開軍團", "/regiment leave        - 离开军团"),
    ("/regiment open|close   - leader: allow / stop new members", "/regiment open|close   - 團長：開放 / 停止招收新成員", "/regiment open|close   - 团长：开放 / 停止招收新成员"),
    ("/regiment kick HERO    - leader: remove a member", "/regiment kick 英雄    - 團長：移除成員", "/regiment kick 英雄    - 团长：移除成员"),
    ("/regiment list         - all regiments", "/regiment list         - 所有軍團", "/regiment list         - 所有军团"),
    ("/regiment who          - members of your regiment", "/regiment who          - 本軍團成員", "/regiment who          - 本军团成员"),
    # ---- regiments
    ("You already belong to regiment {}. /regiment leave first.", "你已經屬於軍團 {0}，請先 /regiment leave。", "你已经属于军团 {0}，请先 /regiment leave。"),
    ("You already belong to regiment {}.", "你已經屬於軍團 {0}。", "你已经属于军团 {0}。"),
    ("Regiment name: 3-16 letters/digits.", "軍團名稱：3-16 個英文字母或數字。", "军团名称：3-16 个英文字母或数字。"),
    ("That regiment name is taken.", "這個軍團名稱已被使用。", "这个军团名称已被使用。"),
    ("Your faction already has {} regiments.", "你的陣營已經有 {0} 個軍團。", "你的阵营已经有 {0} 个军团。"),
    ("Founding a regiment costs {} money, {} ore and {} silicon.", "建立軍團需要 {0} 金錢、{1} 礦、{2} 矽。", "建立军团需要 {0} 金钱、{1} 矿、{2} 硅。"),
    ("Regiment {} founded.", "軍團 {0} 已成立。", "军团 {0} 已成立。"),
    ("No such regiment.", "沒有這個軍團。", "没有这个军团。"),
    ("That regiment is closed to new members.", "這個軍團目前不招收新成員。", "这个军团目前不招收新成员。"),
    ("That regiment belongs to another faction.", "這個軍團屬於其他陣營。", "这个军团属于其他阵营。"),
    ("You joined regiment {}.", "你加入了軍團 {0}。", "你加入了军团 {0}。"),
    ("No regiments yet.", "目前還沒有軍團。", "目前还没有军团。"),
    ("{}: {} member(s), leader {}, {}", "{0}：{1} 名成員，團長 {2}，{3}", "{0}：{1} 名成员，团长 {2}，{3}"),
    ("You are not in a regiment. /regiment create NAME  or  /regiment join NAME  or  /regiment list",
     "你不在任何軍團。可用 /regiment create 名稱、/regiment join 名稱 或 /regiment list", "你不在任何军团。可用 /regiment create 名称、/regiment join 名称 或 /regiment list"),
    ("Regiment {} (leader {}, {}): {}", "軍團 {0}（團長 {1}，{2}）：{3}", "军团 {0}（团长 {1}，{2}）：{3}"),
    ("You left regiment {}.", "你離開了軍團 {0}。", "你离开了军团 {0}。"),
    ("Only the regiment leader can do that.", "只有團長可以這麼做。", "只有团长可以这么做。"),
    ("Invalid or taken name (3-16 letters/digits).", "名稱無效或已被使用（3-16 個英文字母或數字）。", "名称无效或已被使用（3-16 个英文字母或数字）。"),
    ("Renaming costs {} Uranium.", "改名需要 {0} 鈾。", "改名需要 {0} 铀。"),
    ("Regiment renamed to {} (-{} Uranium).", "軍團已改名為 {0}（-{1} 鈾）。", "军团已改名为 {0}（-{1} 铀）。"),
    ("No such member.", "沒有這名成員。", "没有这名成员。"),
    ("Done ({}).", "完成（{0}）。", "完成（{0}）。"),
    ("/regiment create|join|leave|rename|open|close|kick|list|who", "/regiment create|join|leave|rename|open|close|kick|list|who", "/regiment create|join|leave|rename|open|close|kick|list|who"),
    # ---- attributes / politics
    ("You have no spent attribute points to reset.", "你沒有已分配的屬性點可以重置。", "你没有已分配的属性点可以重置。"),
    ("Resetting attribute points costs {} Uranium.", "重置屬性點需要 {0} 鈾。", "重置属性点需要 {0} 铀。"),
    ("Attribute points reset: {} point(s) returned (-{} Uranium).", "屬性點已重置：退還 {0} 點（-{1} 鈾）。", "属性点已重置：退还 {0} 点（-{1} 铀）。"),
    ("Only citizens of this nation can take part in its election.", "只有本國國民可以參加選舉。", "只有本国国民可以参加选举。"),
    ("Only the president can change the council.", "只有總統可以變更議會。", "只有总统可以变更议会。"),
    # ---- presidential election (2026-10-26)
    ("Registration is closed: the vote has started.", "報名已截止：投票已經開始。", "报名已截止：投票已经开始。"),
    ("You need division level {} to run for president.", "兵科等級需達 {0} 級才能參選總統。", "兵科等级需达 {0} 级才能参选总统。"),
    ("You need division level {} to vote.", "兵科等級需達 {0} 級才能投票。", "兵科等级需达 {0} 级才能投票。"),
    ("You can only support or oppose the Overlord once per day.", "每天只能對總統表示一次支持或反對。", "每天只能对总统表示一次支持或反对。"),
    ("Voting has not started yet.", "投票尚未開始（目前是報名期）。", "投票尚未开始（目前是报名期）。"),
    ("Someone from your network has already voted.", "你的網路（同一個 IP）已經有人投過票了。", "你的网络（同一个 IP）已经有人投过票了。"),
    ("{} is not a citizen of this faction or below division level {}.", "{0} 不是本國國民，或兵科等級未達 {1} 級。", "{0} 不是本国国民，或兵科等级未达 {1} 级。"),
    ("Voting for president has started - vote in the FHQ (Vote).", "總統選舉投票開始了！請到 FHQ 大廳按「Vote」投票。", "总统选举投票开始了！请到 FHQ 大厅按“Vote”投票。"),
    ("{} was recalled by the citizens ({} oppose, {} support). A new election starts now - register in the FHQ (Vote).",
     "{0} 遭國民罷免（今日反對 {1}、支持 {2}）。新一屆選舉立即開始，請到 FHQ 大廳按「Vote」報名。",
     "{0} 遭国民罢免（今日反对 {1}、支持 {2}）。新一届选举立即开始，请到 FHQ 大厅按“Vote”报名。"),
    ("{} is the new president of the faction ({} votes).", "{0} 當選為新任總統（{1} 票）。", "{0} 当选为新任总统（{1} 票）。"),
    ("This planet is not open yet.", "這顆星球尚未開放。", "这颗星球尚未开放。"),
    # ---- demon-star notices (2026-10-27)
    ("This time your faction's demon star is {}.", "本次本陣營的魔星是 {0}。", "本次本阵营的魔星是 {0}。"),
    ("National power is FULL! Your faction has demon-star time for 24 hours (until {}).",
     "國力已滿！本陣營獲得 24 小時魔星時間（至 {0}）。", "国力已满！本阵营获得 24 小时魔星时间（至 {0}）。"),
    ("Your faction has demon-star time ({}h{}m left). The demon star is OPEN until {} - type /star to enter.",
     "本陣營魔星時間剩餘 {0} 小時 {1} 分。魔星現在開放到 {2}，輸入 /star 進入。",
     "本阵营魔星时间剩余 {0} 小时 {1} 分。魔星现在开放到 {2}，输入 /star 进入。"),
    ("Your faction has demon-star time ({}h{}m left). The demon star opens at {} for 1 hour - type /star then.",
     "本陣營魔星時間剩餘 {0} 小時 {1} 分。魔星將於 {2} 開放 1 小時，屆時輸入 /star 進入。",
     "本阵营魔星时间剩余 {0} 小时 {1} 分。魔星将于 {2} 开放 1 小时，届时输入 /star 进入。"),
    ("Your faction has demon-star time ({}h{}m left), but no demon-star window falls inside it.",
     "本陣營魔星時間剩餘 {0} 小時 {1} 分，但這段時間內沒有魔星開放時段。",
     "本阵营魔星时间剩余 {0} 小时 {1} 分，但这段时间内没有魔星开放时段。"),
    ("On a demon star you can only attack a province next to one your side holds.",
     "在魔星上只能進攻與本方省份相鄰的省。", "在魔星上只能进攻与本方省份相邻的省。"),
    ("Demon star: fight from your corner to the centre province - whoever holds the centre can buy demon-star equipment in its Lab.",
     "魔星：從你的角落一路打到中央的省，佔領中央省就能在它的研究所購買魔星裝備。",
     "魔星：从你的角落一路打到中央的省，占领中央省就能在它的研究所购买魔星装备。"),
    ("Only the Lab and the Factory are open in the centre of a demon star.", "魔星中心只開放研究所和工廠。", "魔星中心只开放研究所和工厂。"),
    ("The demon star has closed. You are back in your capital.", "魔星已關閉，你已回到首都。", "魔星已关闭，你已回到首都。"),
    ("Your faction holds the centre of the demon star! Its Lab now sells demon-star equipment.",
     "本陣營佔領了魔星中央省！它的研究所現在販售魔星裝備。", "本阵营占领了魔星中央省！它的研究所现在贩售魔星装备。"),
    ("The demon star is OPEN now until {} - use the Dimensional Matrix or type /star.",
     "魔星現已開放至 {0}，請從星門（次元矩陣）進入或輸入 /star。", "魔星现已开放至 {0}，请从星门（次元矩阵）进入或输入 /star。"),
    ("The demon star is OPEN now until {} - type /star to enter.",
     "魔星已開放，到 {0} 為止，輸入 /star 進入！", "魔星已开放，到 {0} 为止，输入 /star 进入！"),
    ("The demon star closes in {} minutes ({}).",
     "魔星將在 {0} 分鐘後（{1}）關閉。", "魔星将在 {0} 分钟后（{1}）关闭。"),
    # ---- lab
    ("This design was refused by the server: {}.", "伺服器拒絕了這個設計：{0}。", "服务器拒绝了这个设计：{0}。"),
    ("Some of these items are not on sale right now.", "部分裝備目前沒有販售。", "部分装备目前没有贩售。"),
    ("Not enough resources for this design (need {}).", "資源不足，無法完成此設計（需要 {0}）。", "资源不足，无法完成此设计（需要 {0}）。"),
    ("Sold: + {}", "賣出：+ {0}", "卖出：+ {0}"),
    ("Upgrade to {} failed: Unit Quality {} is below the required {}.", "升級為 {0} 失敗：單位品質 {1} 低於需求的 {2}。", "升级为 {0} 失败：单位品质 {1} 低于需求的 {2}。"),
    ("Upgrade to {} failed: not enough resources (need {}).", "升級為 {0} 失敗：資源不足（需要 {1}）。", "升级为 {0} 失败：资源不足（需要 {1}）。"),
    ("{} -> {}: {} removed (no such slot), sold for half price. Upgraded {}s have NO WEAPON - equip one in EQUIP ITEM.",
     "{0} → {1}：{2} 已移除（新底盤沒有此欄位），以半價賣出。升級後的 {3} 沒有武器，請到 EQUIP ITEM 裝備。",
     "{0} → {1}：{2} 已移除（新底盘没有此栏位），以半价卖出。升级后的 {3} 没有武器，请到 EQUIP ITEM 装备。"),
    ("{} -> {}: {} removed (no such slot), sold for half price.", "{0} → {1}：{2} 已移除（新底盤沒有此欄位），以半價賣出。", "{0} → {1}：{2} 已移除（新底盘没有此栏位），以半价卖出。"),
    ("{} -> {}: Upgraded {}s have NO WEAPON - equip one in EQUIP ITEM.", "{0} → {1}：升級後的 {2} 沒有武器，請到 EQUIP ITEM 裝備。", "{0} → {1}：升级后的 {2} 没有武器，请到 EQUIP ITEM 装备。"),
    # ---- system
    ("Unsupported or modified game client - please reinstall the official client.", "不支援或已被修改的遊戲客戶端，請重新安裝官方客戶端。", "不支持或已被修改的游戏客户端，请重新安装官方客户端。"),
    ("Language: {}", "語言：{0}", "语言：{0}"),
]


# ---- (2026-10-27 21:44 "still many English messages - make sure they are Chinese"): messages found by the source
# scan (tools/mptest/test85) that had no template yet
CATALOG += [
    ("The {} on {} was repelled!", "{1} 的{0}已被擊退！", "{1} 的{0}已被击退！"),
    ("A division must reach level {} before you can move to the Advanced planet.",
     "需要有一個兵科達到 {0} 級，才能前往進階星球。", "需要有一个兵科达到 {0} 级，才能前往进阶星球。"),
    ("A division must reach level {} before you can move to the Elite planet.",
     "需要有一個兵科達到 {0} 級，才能前往精英星球。", "需要有一个兵科达到 {0} 级，才能前往精英星球。"),
    ("You cannot reincarnate more than {} times.", "轉生次數不能超過 {0} 次。", "转生次数不能超过 {0} 次。"),
    ("A division must reach level {} before you can reincarnate.",
     "需要有一個兵科達到 {0} 級才能轉生。", "需要有一个兵科达到 {0} 级才能转生。"),
    ("There are currently no factions open at this time.", "目前沒有開放的國家。", "目前没有开放的国家。"),
    ("Unknown faction.", "未知的國家。", "未知的国家。"),
    ("Switching faction costs {} Uranium.", "轉換國家需要 {0} 鈾。", "转换国家需要 {0} 铀。"),
    ("You cannot join this faction.", "你不能加入這個國家。", "你不能加入这个国家。"),
    ("You cannot reincarnate into this faction.", "你不能轉生到這個國家。", "你不能转生到这个国家。"),
    ("Your new incarnation will not be able to own more than {} units.",
     "轉生後最多只能擁有 {0} 個單位。", "转生后最多只能拥有 {0} 个单位。"),
    ("Reincarnation costs {} Uranium.", "轉生需要 {0} 鈾。", "转生需要 {0} 铀。"),
    ("Unknown planet.", "未知的星球。", "未知的星球。"),
    ("This planet is not open yet.", "這個星球尚未開放。", "这个星球尚未开放。"),
    ("You are already on this planet.", "你已經在這個星球上了。", "你已经在这个星球上了。"),
    ("Veteran commanders cannot return to the {} planet.", "資深指揮官不能回到{0}星球。", "资深指挥官不能回到{0}星球。"),
    ("To move to a more advanced planet, pledge to one of its factions at the StarCenter.",
     "要前往更高等級的星球，請在星際中心宣誓加入該星球的一個國家。", "要前往更高等级的星球，请在星际中心宣誓加入该星球的一个国家。"),
    ("A division must reach level {} before you can travel to {}.",
     "需要有一個兵科達到 {0} 級，才能前往 {1}。", "需要有一个兵科达到 {0} 级，才能前往 {1}。"),
    ("Travel to {} is not implemented yet.", "前往 {0} 尚未開放。", "前往 {0} 尚未开放。"),
    ("{} was lost!", "{0} 失守了！", "{0} 失守了！"),
    ("LAST STAND: your nation is down to {} province(s).  For {} hours your units have +{}% HP and more commanders fight for you.",
     "背水一戰：你的國家只剩 {0} 個省。接下來 {1} 小時，你的單位 HP +{2}%，並有更多指揮官為你作戰。",
     "背水一战：你的国家只剩 {0} 个省。接下来 {1} 小时，你的单位 HP +{2}%，并有更多指挥官为你作战。"),
    ("CAPITAL ALARM: the enemy holds {} next to our capital.  For {} hours up to {} commanders take the field and strike back.",
     "首都警報：敵軍佔領了首都旁的 {0}。接下來 {1} 小時，最多 {2} 名指揮官出戰反擊。",
     "首都警报：敌军占领了首都旁的 {0}。接下来 {1} 小时，最多 {2} 名指挥官出战反击。"),
    ("{} commanders ({}...) march on {}.", "{0} 名指揮官（{1}…）正向 {2} 進軍。", "{0} 名指挥官（{1}…）正向 {2} 进军。"),
    ("This is a battle simulation: leave it through your exit portal.",
     "這是模擬戰：請從你的出口傳送門離開。", "这是模拟战：请从你的出口传送门离开。"),
    ("H- equipment is only sold once your side has captured the centre province of the planet",
     "H- 裝備要在你方佔領本星球的中央省份後才會販售", "H- 装备要在你方占领本星球的中央省份后才会贩售"),
    ("unknown item ids {}", "未知的物品編號 {0}", "未知的物品编号 {0}"),
    ("not on sale for {}: {}", "{0} 不能購買：{1}", "{0} 不能购买：{1}"),
    ("tech level > {}: {}", "科技等級超過 {0}：{1}", "科技等级超过 {0}：{1}"),
    ("item in a slot this chassis does not have / two items in one slot",
     "物品放在這個底盤沒有的欄位，或同一欄位放了兩件", "物品放在这个底盘没有的栏位，或同一栏位放了两件"),
    ("op 3 list too long", "清單太長", "清单太长"),
    ("weight {}/{}", "重量 {0}/{1}", "重量 {0}/{1}"), ("space {}/{}", "空間 {0}/{1}", "空间 {0}/{1}"),
    ("complexity {}/{}", "複雜度 {0}/{1}", "复杂度 {0}/{1}"),
    ("{} -> {}: {} removed (no slot / too heavy), sold for half price. Upgraded {}s have NO WEAPON - equip one in EQUIP ITEM.",
     "{0} → {1}：{2} 已移除（沒有欄位或太重），以半價賣出。升級後的 {3} 沒有武器，請到 EQUIP ITEM 裝備。",
     "{0} → {1}：{2} 已移除（没有栏位或太重），以半价卖出。升级后的 {3} 没有武器，请到 EQUIP ITEM 装备。"),
    ("{} -> {}: {} removed (no slot / too heavy), sold for half price.",
     "{0} → {1}：{2} 已移除（沒有欄位或太重），以半價賣出。", "{0} → {1}：{2} 已移除（没有栏位或太重），以半价卖出。"),
    ("{} -> {}: Upgraded {}s have NO WEAPON - equip one in EQUIP ITEM.",
     "{0} → {1}：升級後的 {2} 沒有武器，請到 EQUIP ITEM 裝備。", "{0} → {1}：升级后的 {2} 没有武器，请到 EQUIP ITEM 装备。"),
    ("No such unit.", "沒有這個單位。", "没有这个单位。"),
    ("This unit's level is too high for you to distribute XP to it.", "這個單位等級太高，你不能分配經驗給它。", "这个单位等级太高，你不能分配经验给它。"),
    ("No XP received from your Subordinates", "沒有從部下收到經驗", "没有从部下收到经验"),
    ("+{} XP -> {} (level {})", "+{0} 經驗 → {1}（等級 {2}）", "+{0} 经验 → {1}（等级 {2}）"),
    ("Assign XP: type /xp to list, /xp UNIT# [AMOUNT] to distribute, /xp auto.",
     "分配經驗：輸入 /xp 列表，/xp 單位編號 [數量] 分配，/xp auto 自動分配。", "分配经验：输入 /xp 列表，/xp 单位编号 [数量] 分配，/xp auto 自动分配。"),
    ("You have no Subordinates (a player gives you his Word of Honor from your F4 window).",
     "你沒有部下（玩家要在你的 F4 視窗向你宣誓效忠）。", "你没有部下（玩家要在你的 F4 窗口向你宣誓效忠）。"),
    ("{} lv{}: {} XP  (outranks you - not usable)", "{0} 等級 {1}：{2} 經驗（等級比你高，無法使用）", "{0} 等级 {1}：{2} 经验（等级比你高，无法使用）"),
    ("{} lv{}: {} XP", "{0} 等級 {1}：{2} 經驗", "{0} 等级 {1}：{2} 经验"),
    ("Units: {}", "單位：{0}", "单位：{0}"),
    ("/xp UNIT# [AMOUNT]  - give to one unit;  /xp auto  - spread over all units",
     "/xp 單位編號 [數量] － 給一個單位；/xp auto － 平均分給所有單位", "/xp 单位编号 [数量] － 给一个单位；/xp auto － 平均分给所有单位"),
    ("Distributed {} XP.", "已分配 {0} 經驗。", "已分配 {0} 经验。"),
    ("/xp UNIT# [AMOUNT]", "/xp 單位編號 [數量]", "/xp 单位编号 [数量]"),
    ("On a demon star you can only attack a province next to one your side holds.",
     "在魔星上只能進攻與你方省份相鄰的省份。", "在魔星上只能进攻与你方省份相邻的省份。"),
]

GLOSSARY = {   # words inside matched values (resources, states)
    "Money": ("金錢", "金钱"), "Ore": ("礦", "矿"), "Silicon": ("矽", "硅"), "Uranium": ("鈾", "铀"), "Sulfur": ("硫", "硫"),
    "open": ("開放", "开放"), "closed": ("關閉", "关闭"), "you have": ("你有", "你有"),
    "alien raid": ("外星入侵", "外星入侵"), "raid": ("突襲", "突袭"),
}

_COMPILED = None

def _compile():
    global _COMPILED
    _COMPILED = []
    for en, tw, cn in CATALOG:
        parts = en.split("{}")
        rx = "^" + "(.*?)".join(re.escape(p) for p in parts) + "$"
        _COMPILED.append((re.compile(rx, re.S), tw, cn, en.count("{}")))
    _COMPILED.sort(key=lambda c: -len(c[0].pattern))      # longest (most specific) template first

def _gloss(v, k):
    for w, tr in GLOSSARY.items():
        v = re.sub(r"\b%s\b" % re.escape(w), tr[k], v)
    return v

def _inner(v, lang):
    """a value inside a matched template that is itself a whole message (e.g. the reason in 'This design was
    refused by the server: {}.'): translated by a template with at least two literal words, else unchanged."""
    if not v or not re.search(r"[A-Za-z]{2,}.*[A-Za-z]{2,}", v):
        return v
    k = 0 if lang == "zh-tw" else 1
    for rx, tw, cn, n in _COMPILED:
        if len(re.findall(r"[A-Za-z]{2,}", rx.pattern.replace("(.*?)", ""))) >= 1:
            m = rx.match(v)
            if m:
                try:
                    return (tw if k == 0 else cn).format(*[_gloss(g, k) for g in m.groups()])
                except (IndexError, KeyError):
                    return v
    return v

def translate(text, lang):
    if lang not in ("zh-tw", "zh-cn") or not text:
        return text
    if _COMPILED is None:
        _compile()
    k = 0 if lang == "zh-tw" else 1
    for rx, tw, cn, n in _COMPILED:
        m = rx.match(text)
        if m:
            vals = [_gloss(_inner(g, lang), k) for g in m.groups()]
            try:
                return (tw if k == 0 else cn).format(*vals)
            except (IndexError, KeyError):
                return text
    return text

# ---- MISSING TRANSLATIONS (user 2026-10-27 "still many English messages in the game - make sure they are Chinese")
# Every system line / message box that reaches a Chinese client untranslated is written ONCE to
# logs/i18n_missing.log (and kept in MISSING) - GM /i18nmiss lists them.  tools/mptest/test85 runs every message
# template of the code through translate() and fails on English-only ones.  MISS_ALL (env SG_I18N_MISS_ALL=1):
# record for English clients too (tests).
import os as _os
MISSING = {}
MISS_ALL = _os.environ.get("SG_I18N_MISS_ALL") == "1"
MISS_FILE = _os.path.join(_os.path.dirname(_os.path.abspath(__file__)), "logs", "i18n_missing.log")

def looks_english(text):
    t = re.sub(r"<[^>]*>", "", text or "")
    if re.search(r"[\u4e00-\u9fff]", t):
        return False
    return len(re.findall(r"[A-Za-z]{2,}", t)) >= 2

def note_missing(text, lang="?"):
    if text in MISSING:
        MISSING[text] += 1
        return
    MISSING[text] = 1
    try:
        _os.makedirs(_os.path.dirname(MISS_FILE), exist_ok=True)
        with open(MISS_FILE, "a", encoding="utf-8") as f:
            f.write(f"{lang}\t{text}\n")
    except OSError:
        pass

def translate_checked(text, lang):
    """translate() + record an English-only result for a Chinese client (or every client with MISS_ALL)."""
    out = translate(text, lang)
    if out == text and (lang in ("zh-tw", "zh-cn") or MISS_ALL) and looks_english(text):
        note_missing(text, lang)
    return out

def codec(lang_or_acp):
    """byte encoding of the client's text: its Windows ANSI code page."""
    return {950: "cp950", 936: "gbk", 949: "cp949"}.get(lang_or_acp, "latin-1")

def lang_of_acp(acp):
    return {950: "zh-tw", 936: "zh-cn"}.get(acp, "en")

# ---- rank titles (F4 / battle result): English full + short form -> (Traditional, Simplified); 21 ranks
RANKS_ZH = [("新兵", "新兵"), ("列兵", "列兵"), ("一等兵", "一等兵"), ("下士", "下士"), ("中士", "中士"), ("上士", "上士"),
            ("准尉", "准尉"), ("少尉", "少尉"), ("中尉", "中尉"), ("上尉", "上尉"), ("大尉", "大尉"), ("少校", "少校"),
            ("中校", "中校"), ("上校", "上校"), ("大校", "大校"), ("准將", "准将"), ("少將", "少将"), ("中將", "中将"),
            ("上將", "上将"), ("大將", "大将"), ("元帥", "元帅")]

def rank(index, lang):
    return RANKS_ZH[index][0 if lang == "zh-tw" else 1]
