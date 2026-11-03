# i18n phase 4b: captions inside the UI Bink clips of odv.dat (see bikui.py).  Coordinates in clip pixels.
X = dict(exact=True, pad=4, thr=22)
XU = dict(exact=True, pad=(4, 0), thr=22)   # 2026-10-22 12:19: one line, never touch the button's top / bottom border
X3 = dict(exact=True, pad=(2, 2), thr=22, keep_lines=False)   # 2026-10-22 10:36: letter stems were kept as 'frame lines' -> blurred tabs
_TABS3 = [((15, 5, 58, 8), '單位檢視', X3), ((86, 5, 64, 8), '屬性檢視', X3), ((163, 5, 58, 8), '單位列表', X3)]
_IS = [((6, 13, 37, 9), '引擎', X), ((56, 13, 36, 9), '儲能', X), ((114, 13, 22, 9), '電腦', X), ((152, 13, 45, 9), '武器', X),
       ((206, 13, 37, 9), '裝甲', X), ((259, 13, 31, 9), '加成', X), ((311, 13, 26, 9), '雜項', X)]
_MB = [((19, 16, 35, 8), '完成', X), ((20, 51, 50, 9), '取消', X), ((20, 86, 68, 20), '前往單位升級', XU)]
_BT = [((22, 11, 64, 18), '完成升級', X), ((21, 80, 66, 21), '前往裝備物品', XU)]
CLIPS = {
    # Lab buttons (normal 3 frames / hover glow)
    'iu-b-ccn.bik': dict(mode='static', labels=[((20, 10, 46, 8), '取消', X)]),
    'iu-b-cch.bik': dict(mode='trackbox', max_shift=40, labels=[((20, 10, 46, 8), '取消', X)]),
    'iu-b-okn.bik': dict(mode='static', labels=[((20, 10, 30, 8), '完成', X)]),
    'iu-b-okh.bik': dict(mode='trackbox', max_shift=40, labels=[((20, 10, 30, 8), '完成', X)]),
    'iu-b-uun.bik': dict(mode='static', labels=[((20, 4, 67, 20), '前往單位升級', XU)]),
    'iu-b-uuh.bik': dict(mode='trackbox', max_shift=40, labels=[((20, 4, 67, 20), '前往單位升級', XU)]),
    'uu-iu-n.bik': dict(mode='static', labels=[((20, 4, 66, 20), '前往裝備物品', XU)]),
    'uu-iu-h.bik': dict(mode='trackbox', max_shift=40, labels=[((20, 4, 66, 20), '前往裝備物品', XU)]),
    'uu-ok-n.bik': dict(mode='static', labels=[((22, 10, 67, 19), '完成升級', X)]),
    'uu-ok-h.bik': dict(mode='trackbox', max_shift=40, labels=[((22, 10, 67, 19), '完成升級', X)]),
    # slide-in / slide-out panels (the last frame of *-si / the first of *-so is complete)
    'iu-3b-si.bik': dict(mode='freeze', labels=_TABS3),          # user: no slide-in, show at once
    'iu-3b-so.bik': dict(mode='freeze', labels=[], ref=-1),       # hide at once
    'iu-3b-fo.bik': dict(mode='freeze', labels=[], ref=-1),       # fold animation still had the KOREAN captions -> hide at once
    'iu-is-si.bik': dict(mode='freeze', labels=_IS),
    'iu-is-so.bik': dict(mode='freeze', labels=[], ref=-1),
    'iu-mb-si.bik': dict(mode='freeze', labels=_MB),
    'iu-mb-so.bik': dict(mode='freeze', ref=-1, labels=_MB),
    'uu-bt-si.bik': dict(mode='freeze', labels=_BT),
    'uu-bt-so.bik': dict(mode='freeze', ref=-1, labels=_BT),
}
# ---- Factory (user 2026-10-22 02:23)
Y = dict(pad=(4, 1), thr=22)
XF = dict(exact=True, pad=(4, 1), thr=22)
CLIPS.update({
    'ft-buy-n.bik': dict(mode='static', labels=[((23, 8, 81, 9), '購買', XF)]),
    'ft-buy-h.bik': dict(mode='trackbox', max_shift=40, labels=[((23, 8, 81, 9), '購買', XF)]),
    'ft-rpa-n.bik': dict(mode='static', labels=[((23, 8, 88, 9), '全部修理', XF)]),
    'ft-rpa-h.bik': dict(mode='trackbox', max_shift=40, labels=[((23, 8, 88, 9), '全部修理', XF)]),
    'ft-rep-n.bik': dict(mode='static', labels=[((20, 4, 95, 16), '修理', Y)]),
    'ft-rep-h.bik': dict(mode='static', labels=[((8, 4, 95, 16), '修理', Y)]),      # pressed: text sits further left
    'ft-sel-n.bik': dict(mode='static', labels=[((20, 4, 95, 16), '賣出', Y)]),
    'ft-sel-h.bik': dict(mode='static', labels=[((8, 4, 95, 16), '賣出', Y)]),
    'ft-yes-n.bik': dict(mode='static', labels=[((14, 6, 32, 16), '是', Y)]),
    'ft-yes-h.bik': dict(mode='static', labels=[((14, 6, 32, 16), '是', Y)]),
    'ft-no-n.bik': dict(mode='static', labels=[((14, 6, 30, 16), '否', Y)]),
    'ft-no-h.bik': dict(mode='static', labels=[((14, 6, 30, 16), '否', Y)]),
    'ft-yn-si.bik': dict(mode='freeze', labels=[((28, 6, 32, 16), '是', Y), ((80, 6, 30, 16), '否', Y)]),
    'ft-yn-so.bik': dict(mode='freeze', ref=-1, labels=[((28, 6, 32, 16), '是', Y), ((80, 6, 30, 16), '否', Y)]),
    'ft-bt-si.bik': dict(mode='freeze', labels=[((23, 9, 81, 9), '購買', XF), ((23, 34, 84, 9), '全部修理', XF), ((23, 59, 55, 9), '修理', XF), ((23, 84, 36, 9), '賣出', XF)]),
    'ft-com-b.bik': dict(mode='rot', labels=[(110, 54, 140, 20, 0, '你的單位', {'thr': 18, 'px': 15, 'both': True})]),
    'ft-mar-b.bik': dict(mode='rot', labels=[(83, 54, 164, 20, 0, '出售單位', {'thr': 18, 'px': 15, 'both': True})]),
})

# 2026-10-22 02:21 (user): no slide-in / slide-out animation - every slide clip shows its final state at once ('freeze')

# 2026-10-22 10:55 (user: button / tab text turns blurry on mouse-over): the MouseOn clips (*-n: frame 0 normal,
# frames 1-2 highlighted) got white smears and grey text in the highlighted frames, and letter stems kept as
# 'frame lines' left marks.  Normal frame: no line keeping; highlighted frames: hl=True (flat button colour,
# brightest text colour + glow, see relabel.py).
def _split_hl(name, nframes=3):
    spec = CLIPS[name]
    out = []
    for (rect, txt, *o) in spec['labels']:
        o = dict(o[0]) if o else {}
        o['keep_lines'] = False
        out.append((rect, txt, dict(o, frames=[0])))
        _p = o.get('pad', 2); _p = _p if isinstance(_p, (tuple, list)) else (_p, _p)
        out.append((rect, txt, dict(o, frames=list(range(1, nframes)), hl=True, pad=(_p[0] + 3, _p[1]))))
    spec['labels'] = out
for _n in ('iu-b-ccn.bik', 'iu-b-okn.bik', 'iu-b-uun.bik', 'uu-iu-n.bik', 'uu-ok-n.bik', 'ft-buy-n.bik', 'ft-rpa-n.bik',
           'ft-rep-n.bik', 'ft-sel-n.bik', 'ft-yes-n.bik', 'ft-no-n.bik'):
    _split_hl(_n)
for _n in ('iu-b-cch.bik', 'iu-b-okh.bik', 'iu-b-uuh.bik', 'uu-iu-h.bik', 'uu-ok-h.bik', 'ft-buy-h.bik', 'ft-rpa-h.bik',
           'ft-rep-h.bik', 'ft-sel-h.bik', 'ft-yes-h.bik', 'ft-no-h.bik'):
    CLIPS[_n]['labels'] = [(r, t, dict((o[0] if o else {}), keep_lines=False)) for (r, t, *o) in CLIPS[_n]['labels']]
for _n in ('ft-rep-h.bik', 'ft-sel-h.bik'):       # pressed clips (6 frames): glow residue in frames 1-5
    _split_hl(_n, 6)
    for _l in CLIPS[_n]['labels']:
        _l[2].pop('keep_lines', None); _l[2]['keep_lines'] = False
