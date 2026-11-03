# i18n phase 4 label spec (see build_ui.py).  rect = (x, y, w, h) in sprite pixels, None = whole button.
LABELS = {
    # ---- Lab: equip / upgrade panels
    'iu-weit.xpf': [((38, 8, 70, 16), '重量'), ((38, 49, 60, 16), '空間'), ((38, 91, 82, 16), '複雜度')],
    'uu-weit.xpf': [((38, 8, 70, 16), '重量'), ((38, 49, 60, 16), '空間'), ((38, 91, 40, 16), '經驗')],
    'uu-res.xpf': [((40, 8, 62, 16), '金錢'), ((40, 33, 40, 16), '礦'), ((40, 58, 62, 16), '矽'),
                   ((40, 83, 66, 16), '鈾'), ((40, 108, 62, 16), '硫')],
    'iu-b-op.xpf': [(None, '讀取')],
    'iu-b-sea.xpf': [(None, '全賣')],
    'iu-b-sl.xpf': [((17, 5, 53, 9), '單位列表', dict(exact=True, keep_lines=False, pad=(2, 1), frames=[0, 2, 3])), ((17, 5, 53, 9), '單位列表', dict(exact=True, keep_lines=False, pad=(2, 1), frames=[1], color=(110, 235, 255)))],   # 2026-10-22 11:55 exact text box: the frame borders must stay (the Lab shows these sprites after the slide-in)
    'iu-b-sta.xpf': [(None, '全卸')],
    'iu-b-su.xpf': [((15, 5, 58, 9), '單位檢視', dict(exact=True, keep_lines=False, pad=(2, 1), frames=[0, 2, 3])), ((15, 5, 58, 9), '單位檢視', dict(exact=True, keep_lines=False, pad=(2, 1), frames=[1], color=(110, 235, 255)))],   # 2026-10-22 11:55 exact text box: the frame borders must stay (the Lab shows these sprites after the slide-in)
    'iu-b-sv.xpf': [(None, '儲存')],
    'iu-b-vs.xpf': [((13, 5, 60, 9), '屬性檢視', dict(exact=True, keep_lines=False, pad=(2, 1), frames=[0, 2, 3])), ((13, 5, 60, 9), '屬性檢視', dict(exact=True, keep_lines=False, pad=(2, 1), frames=[1], color=(110, 235, 255)))],   # 2026-10-22 11:55 exact text box: the frame borders must stay (the Lab shows these sprites after the slide-in)
    'iu-b-un0.xpf': [(None, '步兵')],
    'iu-b-un1.xpf': [(None, '機動')],
    'iu-b-un2.xpf': [(None, '航空')],
    'iu-b-un3.xpf': [(None, '有機')],
    'iu-is-b1.xpf': [(None, '引擎')],
    'iu-is-b2.xpf': [(None, '儲能')],
    'iu-is-b3.xpf': [(None, '電腦')],
    'iu-is-b4.xpf': [(None, '武器')],
    'iu-is-b5.xpf': [(None, '裝甲')],
    'iu-is-b6.xpf': [(None, '加成')],
    'iu-is-b7.xpf': [(None, '雜項')],
}
X = dict(exact=True)
T = dict(exact=True, pad=4, thr=15)      # glowing titles
_TABS4 = lambda y: [((10, y, 66, 10), '步兵', X), ((94, y, 48, 10), '機動', X), ((172, y, 59, 10), '航空', X), ((254, y, 60, 10), '有機', X)]
LABELS.update({
    'uu-4-on.xpf': _TABS4(6),
    'iu-4-on.xpf': _TABS4(6),
    'uu-cate.xpf': [(None, '步兵', dict(frames=[0, 1, 2])), (None, '機動', dict(frames=[3, 4, 5])),
                    (None, '航空', dict(frames=[6, 7, 8])), (None, '有機', dict(frames=[9, 10, 11]))],
    'uu-com.xpf': [((10, 2, 56, 10), '底盤', T), ((46, 400, 170, 16), '目前單位品質：')],
    'uu-comm.xpf': [((4, 0, 66, 16), '底盤', dict(frames=[1])),
                    ((10, 24, 74, 16), '步兵', dict(frames=[1])), ((96, 24, 58, 16), '機動', dict(frames=[1])),
                    ((176, 24, 66, 16), '航空', dict(frames=[1])), ((256, 24, 68, 16), '有機', dict(frames=[1])),
                    ((46, 400, 170, 16), '目前單位品質：', dict(frames=[1]))],
    'uu-info.xpf': [((10, 2, 100, 10), '升級資訊', T), ((6, 22, 70, 16), '增益'), ((178, 22, 60, 16), '損失')],
    'uu-infom.xpf': [((4, 2, 110, 16), '升級資訊', dict(frames=[1])), ((4, 24, 70, 16), '增益', dict(frames=[1])),
                     ((176, 24, 62, 16), '損失', dict(frames=[1]))],
    'uu-unit.xpf': [((6, 6, 110, 16), '升級單位'), ((82, 288, 180, 16), '所需單位品質：')],
    'uu-unitm.xpf': [((6, 6, 110, 16), '升級單位', dict(frames=[1])), ((82, 288, 180, 16), '所需單位品質：', dict(frames=[1]))],
    'iu-4-bk.xpf': [((6, 2, 92, 16), '目前單位')],
    'iu-cu-bk.xpf': [((6, 2, 92, 16), '目前單位'), ((280, 26, 62, 28), '最高科技\n等級'), ((286, 348, 32, 8), '讀取', X), ((286, 373, 32, 8), '儲存', X)],
    'uew-but0.xpf': [(None, '自動分配', dict(frames=[0, 1, 2])), (None, '復原', dict(frames=[3, 4, 5])),
                     (None, '清除', dict(frames=[6, 7, 8])), (None, '確定', dict(frames=[9, 10, 11])),
                     (None, '取消', dict(frames=[12, 13, 14]))],
    'uew-but1.xpf': [(None, '等級', dict(frames=[0, 1, 2])), (None, '步兵', dict(frames=[3, 4, 5])),
                     (None, '機動', dict(frames=[6, 7, 8])), (None, '航空', dict(frames=[9, 10, 11])),
                     (None, '有機', dict(frames=[12, 13, 14]))],
    'uew-but2.xpf': [(None, '名稱', dict(frames=[0, 1, 2])), (None, '等級', dict(frames=[3, 4, 5])),
                     (None, '直接\n經驗', dict(frames=[6, 7, 8])), (None, '間接\n經驗', dict(frames=[9, 10, 11]))],
})
V = dict(vertical=True)
_SIGN = [((0, 14, 80, 18), '裝備', dict(ttf=True, px=15, pad=3, thr=15, align='left')),
         ((0, 34, 22, 16), '', dict(pad=2, thr=15))]
_SALE_INV = [((6, 74, 16, 96), '出售物品', V), ((6, 282, 16, 78), '庫存', V)]
_ROWS = [61, 126, 191, 256, 321, 386]
LABELS.update({
    'iu-it-bk.xpf': [(None, '重置')],
    'iu-it-cc.xpf': [(None, '取消')],
    'iu-it-ok.xpf': [(None, '完成')],
    'iu-op-cc.xpf': [(None, '取消')],
    'iu-op-op.xpf': [(None, '讀取')],
    'iu-sp-cc.xpf': [(None, '取消')],
    'iu-sp-sv.xpf': [(None, '儲存')],
    'iu-op-bk.xpf': [((5, 82, 40, 16), '讀取'), ((103, 82, 50, 16), '取消')],
    'iu-sp-bk.xpf': [((19, 32, 30, 9), '儲存', X), ((106, 32, 44, 9), '取消', X)],
    'iu-st-fz.xpf': [((16, 4, 68, 20), '前往單位升級', dict(exact=True, pad=(2, 0)))],
    'iu-ui-ss.xpf': [(None, '卸下', dict(frames=[0])), (None, '賣出', dict(frames=[1]))],
    'iu-b-cpi.xpf': [(None, '庫存', V)],
    'iu-b-rss.xpf': [(None, '出售物品', V)],
    'iu-fd-rs.xpf': _SALE_INV,
    'iu-rs-bk.xpf': _SALE_INV + _SIGN,
    'iu-ci-bk.xpf': _SALE_INV + _SIGN,
    'iu-rs-mv.xpf': [((6, 74, 16, 96), '出售物品', dict(vertical=True, frames=[1])),
                     ((6, 282, 16, 78), '庫存', dict(vertical=True, frames=[1, 3]))],
    'iu-ci-mv.xpf': [((11, 9, 82, 8), '目前單位', dict(exact=True, frames=[1])),
                     ((17, 35, 64, 9), '步兵', dict(exact=True, frames=[1])), ((103, 35, 47, 9), '機動', dict(exact=True, frames=[1])),
                     ((181, 35, 57, 9), '航空', dict(exact=True, frames=[1])), ((263, 35, 59, 9), '有機', dict(exact=True, frames=[1]))],
    'iu-ui-bk.xpf': [((310, 15, 112, 9), '更改單位名稱', X), ((6, 68, 16, 100), '單位庫存', V)],
    'iu-ui-mv.xpf': [((310, 15, 112, 9), '更改單位名稱', X), ((6, 66, 16, 110), '單位庫存', V),
                     ((111, 13, 25, 8), '名稱', X), ((172, 9, 24, 17), '全賣', X), ((218, 4, 32, 26), '全卸', X)]
                    + [((171, y, 25, 7), '賣出', X) for y in _ROWS] + [((211, y, 47, 7), '卸下', X) for y in _ROWS],
})
LABELS.update({
    'iu-main.jpg': [((335, 14, 115, 36), '裝備物品', dict(ttf=True, px=20, pad=3, thr=20))],
    'uu-back.jpg': [((334, 19, 123, 26), '升級單位', dict(ttf=True, px=20, pad=3, thr=30, exact=True, fill=(14, 10, 46)))],
})
# ---- F4 introspection window (batch 2)
# 2026-10-22 10:38 (user: Chinese not aligned): explicit alignment like the English original - row labels LEFT at the
# column's x, headings and the attribute names CENTRED on the English word (align 'auto' mixed both).
_L = dict(align='left'); _C = dict(align='center'); _R = dict(align='left', exact=True, pad=(1, 2))
_F4_LEFT = [((56, 42, 106, 16), '部隊資訊', _C), ((218, 42, 120, 16), '政治資訊', _C),
            ((282, 68, 44, 15), '名稱', _L), ((282, 101, 64, 15), '陣營', _L),
            ((46, 99, 52, 15), '等級', _L), ((46, 119, 28, 15), '經驗', _L), ((46, 139, 70, 15), '所需經驗', _L), ((46, 159, 50, 15), '軍階', _L),
            ((196, 145, 44, 15), '頭銜', _L), ((196, 162, 78, 15), '上級', _L), ((196, 180, 76, 15), '軍團', _L),
            ((196, 196, 74, 15), '聲望', _L), ((196, 214, 66, 15), '戰績', _L),
            ((114, 246, 146, 15), '功績', _C), ((77, 272, 68, 15), '經歷', _C), ((241, 272, 58, 15), '勳章', _C),
            ((47, 295, 114, 15), '轉生', _L), ((47, 316, 58, 15), '榮譽', _L)]
_BIG = dict(ttf=True, px=15, pad=3, thr=20)
_TITLE = dict(ttf=True, px=15, pad=0, thr=10, exact=True, fill=(0, 0, 0), color=(246, 170, 41))
LABELS.update({
    'f4-bk-mi.xpf': [((215, 14, 132, 18), '指揮官資訊', _TITLE)] + _F4_LEFT + [
        ((408, 42, 94, 16), '屬性', _C), ((400, 67, 54, 15), '點數', _C), ((394, 88, 68, 15), '戰術', _C), ((399, 110, 56, 15), '影響力', _C),
        ((387, 132, 88, 15), '教育', _C), ((389, 154, 80, 15), '機械', _C), ((412, 188, 86, 15), '資源', _C),
        # resources: exact boxes of the English words (x 415), the icons end at x 412 -> refine() took icon pixels
        ((415, 226, 40, 10), '金錢', _R), ((415, 254, 27, 10), '礦', _R), ((415, 280, 45, 10), '矽', _R),
        ((415, 307, 45, 10), '鈾', _R), ((415, 334, 46, 10), '硫', _R), ((284, 381, 104, 18), '傭兵', _C)],
    'f4-bk-nm.xpf': [((133, 14, 132, 18), '指揮官資訊', _TITLE)] + _F4_LEFT,
    'f4-b-mer.xpf': [(None, '開', dict(frames=[0, 1, 2])), (None, '關', dict(frames=[3, 4, 5]))],
    'f4-b-ok.xpf': [(None, '關閉')],
    'f4-b-stc.xpf': [(None, '效力')],
    'f4-b-un.xpf': [(None, '步', dict(frames=[0, 1, 2])), (None, '機', dict(frames=[3, 4, 5])),
                    (None, '航', dict(frames=[6, 7, 8])), (None, '有', dict(frames=[9, 10, 11]))],
    'f4-fd-st.xpf': [((6, 4, 26, 10), '步兵', X), ((43, 4, 25, 10), '機動', X), ((79, 4, 24, 10), '航空', X), ((116, 4, 26, 10), '有機', X)],
})
# ---- battle result window (batch 3, user 2026-10-22 02:21); INF / MOB / AVI / ORG stay English (too small)
_TITLE2 = dict(ttf=True, px=13, pad=0, thr=10, exact=True, fill=(0, 0, 0))
LABELS.update({
    'brw-frm.xpf': [((170, 8, 140, 14), '戰鬥結算', dict(_TITLE2, color=(246, 170, 41), frames=[0])),
                    ((115, 32, 102, 15), '指揮官', dict(frames=[0])), ((280, 32, 108, 15), '陣營資訊', dict(frames=[0])),
                    ((183, 54, 50, 15), '名稱', dict(frames=[0])), ((172, 88, 74, 15), '聲望', dict(frames=[0])),
                    ((115, 132, 108, 15), '部隊資訊', dict(frames=[0])), ((288, 132, 88, 15), '資源', dict(frames=[0])),
                    ((273, 180, 50, 15), '金錢', dict(frames=[0], align='center')), ((273, 218, 50, 15), '礦', dict(frames=[0], align='center')),
                    ((273, 256, 52, 15), '矽', dict(frames=[0], align='center')), ((273, 294, 52, 15), '鈾', dict(frames=[0], align='center')),
                    ((273, 331, 52, 15), '硫', dict(frames=[0], align='center')),
                    ((49, 44, 44, 15), '單位', dict(frames=[1])), ((111, 44, 40, 15), '等級', dict(frames=[1])),
                    ((151, 44, 50, 15), '擊殺', dict(frames=[1])), ((213, 44, 74, 15), '平均等級', dict(frames=[1]))],
    'brw-titl.xpf': [((5, 1, 74, 11), '勝利', dict(exact=True, pad=1, fill=(0, 0, 0), frames=[0])),
                     ((5, 1, 74, 11), '戰敗', dict(exact=True, pad=1, fill=(0, 0, 0), frames=[1])),
                     ((5, 1, 74, 11), '撤退', dict(exact=True, pad=1, fill=(0, 0, 0), frames=[2]))],
    'brw-clos.xpf': [((4, 7, 54, 13), '關閉', dict(exact=True, pad=2))],
    'brw-exp.xpf': [((3, 3, 23, 10), '經驗', dict(exact=True, pad=1))],
})
del LABELS['f4-b-un.xpf']          # user 2026-10-22 02:21: branch tabs stay English (one Chinese character is too small)
# ---- Factory (batch 4)
XG = dict(exact=True, pad=6, thr=20)
XL = dict(exact=True, pad=3, align='left')
LABELS.update({
    'ft-bt-f0.xpf': [((23, 8, 82, 9), '購買', X)], 'ft-bt-f1.xpf': [((23, 8, 87, 9), '全部修理', X)],
    'ft-bt-f2.xpf': [((23, 8, 54, 9), '修理', X)], 'ft-bt-f3.xpf': [((23, 8, 37, 9), '賣出', X)],
    'ft-cate0.xpf': [((20, 12, 62, 10), '步兵', XG)], 'ft-cate1.xpf': [((20, 12, 62, 10), '機動', XG)],
    'ft-cate2.xpf': [((20, 12, 62, 10), '航空', XG)], 'ft-cate3.xpf': [((20, 12, 62, 10), '有機', XG)],
    'FT-CTRP.XPF': [((455, 33, 40, 9), '金錢', XL), ((455, 58, 25, 9), '礦', XL), ((455, 82, 42, 9), '矽', XL),
                    ((455, 107, 49, 9), '鈾', XL), ((455, 131, 44, 9), '硫', XL)],
})

# 2026-10-22 12:18: the three Lab view-tab sprites are cut from the translated strip by tabsprites.py (no relabel)
for _k in ('iu-b-su.xpf', 'iu-b-vs.xpf', 'iu-b-sl.xpf'):
    LABELS.pop(_k, None)
