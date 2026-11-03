"""Chinese chassis (unit class) names, applied per session when a packet is sent (user 2026-10-22 02:39).
The server keeps working with the English names; Session.send rewrites the name strings of the packets that carry
them, and the few client packets that send a chassis / unit name back are mapped back to English (to_english).
Packets: 0x44 unit catalogue (both lists), 0x2F 0x40 Factory shop, 0x16 sub 1/2/4 roster (unit name + chassis),
0x33 sub 2 upgrade tree, 0x33 sub 3 item sale (unit name), 0x18 / 0x50 PUT_UNIT (unit name).
The client matches a unit to its Lab category by the chassis STRING, so every packet must use the same language -
which they do, because the language is per session.  Art and equip slots go by art code (equip.txt), not by name."""
import struct, re

TW = {
    'Imp': '小鬼', 'Wraith': '怨靈', 'Sapper': '工兵', 'Shade': '暗影', 'Ghast': '惡鬼', 'Spirit': '精靈',
    'Pegasus': '天馬', 'Red-Eye': '赤眼', 'Behemoth': '巨獸', 'Manticore': '蠍獅', 'Triage': '救護車',
    'Arbalest': '弩砲', 'Hawk': '鷂鷹', 'Pelican': '鵜鶘', 'Eagle': '雄鷹', 'Roc': '大鵬',
    'Oizys': '歐伊茲', 'Ubik': '尤比克', 'Manta': '魟魚', 'Slanth': '斯蘭斯', 'Mamos': '瑪莫斯', 'Poda': '波達',
    'Larva': '幼蟲', 'Spitter': '噴吐獸', 'Ripper': '撕裂獸', 'Stinger': '刺蟲', 'Scorpid': '魔蠍', 'Arachnid': '魔蛛', 'Rayoks': '雷奧克斯', 'Charnal': '魔龍', 'Miasmal': '瘴蛛', 'Miasam': '瘴母', 'Wight': '屍妖', 'Quorg': '闊格', 'Daeva': '迪瓦', 'Mephit': '梅菲特', 'Spectre': '幽魂',
    'Liche': '巫妖', 'Medic': '醫療兵', 'Virus': '病毒', 'Banshee': '女妖', 'Phantom': '幻影', 'Revenant': '亡魂',
    'Apparition': '幽靈', 'Gryphon': '獅鷲', 'Gear-Doc': '修理機', 'Orbus': '歐伯斯', 'Leviathan': '利維坦',
    'Chimera': '奇美拉', 'Hydra': '九頭蛇', 'Volte': '沃爾特', 'Mantlet': '盾車', 'Ballista': '重弩',
    'Trebuchet': '投石車', 'Owl': '貓頭鷹', 'Falcon': '獵隼', 'War Pigeon': '戰鴿', 'Vulture': '禿鷹',
    'Phoenix': '鳳凰', 'Condor': '禿鷲', 'Albatross': '信天翁',
    'Hive Nest': '孵化巢', 'Hive': '孵化巢', 'Alien': '外星生物',
}
TW.setdefault('SatCom', '衛星通訊')
for _k in list(TW):
    for _n in range(2, 10):                     # Mk2..Mk9 (user 2026-10-24: full Mk line from the manual)
        TW[f'{_k}-MK{_n}'] = TW[_k] + f' MK{_n}'
CN = {'Imp': '小鬼', 'Wraith': '怨灵', 'Sapper': '工兵', 'Shade': '暗影', 'Ghast': '恶鬼', 'Spirit': '精灵', 'Pegasus': '天马', 'Red-Eye': '赤眼', 'Behemoth': '巨兽', 'Manticore': '蝎狮', 'Triage': '救护车', 'Arbalest': '弩砲', 'Hawk': '鹞鹰', 'Pelican': '鹈鹕', 'Eagle': '雄鹰', 'Roc': '大鹏', 'Oizys': '欧伊兹', 'Ubik': '尤比克', 'Manta': '魟鱼', 'Slanth': '斯兰斯', 'Mamos': '玛莫斯', 'Poda': '波达', 'Larva': '幼虫', 'Spitter': '喷吐兽', 'Ripper': '撕裂兽', 'Stinger': '刺虫', 'Scorpid': '魔蝎', 'Arachnid': '魔蛛', 'Rayoks': '雷奥克斯', 'Charnal': '魔龙', 'Miasmal': '瘴蛛', 'Miasam': '瘴母', 'Wight': '尸妖', 'Quorg': '阔格', 'Daeva': '迪瓦', 'Mephit': '梅菲特', 'Spectre': '幽魂', 'Liche': '巫妖', 'Medic': '医疗兵', 'Virus': '病毒', 'Banshee': '女妖', 'Phantom': '幻影', 'Revenant': '亡魂', 'Apparition': '幽灵', 'Gryphon': '狮鹫', 'Gear-Doc': '修理机', 'Orbus': '欧伯斯', 'Leviathan': '利维坦', 'Chimera': '奇美拉', 'Hydra': '九头蛇', 'Volte': '沃尔特', 'Mantlet': '盾车', 'Ballista': '重弩', 'Trebuchet': '投石车', 'Owl': '猫头鹰', 'Falcon': '猎隼', 'War Pigeon': '战鸽', 'Vulture': '秃鹰', 'Phoenix': '凤凰', 'Condor': '秃鹫', 'Albatross': '信天翁', 'Hive Nest': '孵化巢', 'Hive': '孵化巢', 'Alien': '外星生物'}
CN.setdefault('SatCom', '卫星通讯')
for _k in list(CN):
    for _n in range(2, 10):
        CN[f'{_k}-MK{_n}'] = CN[_k] + f' MK{_n}'
# (user 2026-10-24 20:23: "Oizys-Magna" stayed English after an organic evolution) ORGANIC lines: the other Xeno bases
# and the five evolution stages (-Prima/-Primus, -Ampla/-Amplus, -Magna/-Magnus, -Maxima/-Maximus, -Extrema/-Extremus)
_ORG_TW = {'Boreas': '玻瑞阿斯', 'Crudgin': '克拉金', 'Eris': '厄莉絲', 'Haltyr': '哈泰爾', 'Knell': '奈爾',
           'Kritsk': '克里斯克', 'Lyssa': '莉莎', 'Mlortha': '姆洛薩', 'Momas': '莫瑪斯', 'Onnir': '奧尼爾',
           'Rouke': '魯克', 'Scave': '斯凱夫', 'Tyr': '提爾', 'Abomination': '憎惡體'}
_ORG_CN = {'Boreas': '玻瑞阿斯', 'Crudgin': '克拉金', 'Eris': '厄莉丝', 'Haltyr': '哈泰尔', 'Knell': '奈尔',
           'Kritsk': '克里斯克', 'Lyssa': '莉莎', 'Mlortha': '姆洛萨', 'Momas': '莫玛斯', 'Onnir': '奥尼尔',
           'Rouke': '鲁克', 'Scave': '斯凯夫', 'Tyr': '提尔', 'Abomination': '憎恶体'}
_STAGE_TW = {'Prima': '初階', 'Primus': '初階', 'Ampla': '進階', 'Amplus': '進階', 'Magna': '強化', 'Magnus': '強化',
             'Maxima': '極致', 'Maximus': '極致', 'Extrema': '究極', 'Extremus': '究極'}
_STAGE_CN = {'Prima': '初阶', 'Primus': '初阶', 'Ampla': '进阶', 'Amplus': '进阶', 'Magna': '强化', 'Magnus': '强化',
             'Maxima': '极致', 'Maximus': '极致', 'Extrema': '究极', 'Extremus': '究极'}
for _tab, _org, _stg in ((TW, _ORG_TW, _STAGE_TW), (CN, _ORG_CN, _STAGE_CN)):
    for _k, _v in _org.items():
        _tab.setdefault(_k, _v)
    for _k in [k for k in list(_tab) if '-MK' not in k and ' ' not in k]:
        for _s, _z in _stg.items():
            _tab.setdefault(f'{_k}-{_s}', f'{_tab[_k]}{_z}')
TABLE = {'zh-tw': TW, 'zh-cn': CN}
_RE_LEVEL = re.compile(r'^(.*?)(\s*[:#]\s*\d+)?$')


def name_out(name, lang):
    t = TABLE.get(lang)
    if not t:
        return name
    if name in t:
        return t[name]
    m = _RE_LEVEL.match(name)                    # "Apparition:6" style labels
    if m and m.group(1) in t and m.group(2):
        return t[m.group(1)] + m.group(2)
    return name


def to_english(name, lang, enc):
    """a name string the client sent (decoded latin-1 by the server) -> English chassis name if it is a Chinese one."""
    if lang not in TABLE:
        return name
    try:
        u = name.encode('latin-1').decode(enc)
    except Exception:
        return name
    for en, zh in TABLE[lang].items():
        if u == zh:
            return en
    return name


def _s8(d, p, lang, enc):
    n = d[p]; s = bytes(d[p + 1:p + 1 + n]).decode('latin-1')
    out = name_out(s, lang)
    if out is s or out == s:
        return bytes(d[p:p + 1 + n]), p + 1 + n
    b = out.encode(enc, 'replace')[:255]
    return bytes([len(b)]) + b, p + 1 + n


def localize(payload, lang, enc):
    if lang not in TABLE or not payload:
        return payload
    t = payload[0]
    try:
        d = payload; out = bytearray(); p = 0
        if t == 0x44:
            out += d[:3]; p = 3; n = struct.unpack_from('>H', d, 1)[0]
            for _ in range(n):
                out += d[p:p + 2]; p += 2
                s, p = _s8(d, p, lang, enc); out += s
            out += d[p:p + 2]; n = struct.unpack_from('>H', d, p)[0]; p += 2
            for _ in range(n):
                out += d[p:p + 4]; p += 4
                s, p = _s8(d, p, lang, enc); out += s
                out += d[p:p + 29]; p += 29
            return bytes(out + d[p:])
        if t == 0x2F and len(d) > 1 and d[1] == 0x40:
            out += d[:7]; p = 7; n = d[6]
            for _ in range(n):
                out += d[p:p + 3]; p += 3
                s, p = _s8(d, p, lang, enc); out += s
                out += d[p:p + 20]; p += 20
            return bytes(out + d[p:])
        if t == 0x16 and len(d) > 1 and d[1] in (1, 2, 4):
            if d[1] == 1:
                out += d[:3]; p = 3; n = d[2]
            else:
                out += d[:2]; p = 2; n = 1
            for _ in range(n):
                out += d[p:p + 70]; p += 70
                for _k in range(2):
                    s, p = _s8(d, p, lang, enc); out += s
            return bytes(out + d[p:])
        if t == 0x33 and len(d) > 1 and d[1] == 2:
            out += d[:8]; p = 8; n = struct.unpack_from('>H', d, 6)[0]
            for _ in range(n):
                out += d[p:p + 2]; p += 2
                s, p = _s8(d, p, lang, enc); out += s
                m = d[p]; out += d[p:p + 1]; p += 1
                for _k in range(m):
                    out += d[p:p + 2]; p += 2
                    s, p = _s8(d, p, lang, enc); out += s
                    out += d[p:p + 22]; p += 22
            return bytes(out + d[p:])
        if t == 0x33 and len(d) > 1 and d[1] == 3:
            out += d[:6]; p = 6
            s, p = _s8(d, p, lang, enc); out += s
            return bytes(out + d[p:])
        if t in (0x18, 0x50):
            h = 5 if t == 0x18 else 9
            out += d[:h]; p = h
            s, p = _s8(d, p, lang, enc); out += s           # unit name (owner name follows, unchanged)
            return bytes(out + d[p:])
    except Exception:
        return payload
    return payload
