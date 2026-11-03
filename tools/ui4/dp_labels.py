# Deploy screen captions (dp-st-bk.jpg coordinates): (cx, cy, w, h, angle_deg_ccw, '繁體', opts)
DP = {
    'ls_level': (94, 541, 66, 26, -16, '依等級排序\n(F3)', {}),
    'ls_name':  (94, 541, 66, 26, -16, '依名稱排序\n(F3)', {}),
    'type':     (220, 570, 70, 24, -14, '依類型排序\n(F4)', {}),
    'clear':    (614, 510, 46, 10, 24, '清除', {}),
    'auto':     (650, 541, 56, 26, 30, '自動\n部署', {}),
    'orig':     (699, 455, 56, 26, 38, '原始\n設定', {}),
    'ok':       (736, 479, 30, 10, 38, '確定', {}),
    'reserves': (432, 566, 152, 24, 9.5, '預備單位', {'px': 18, 'pad': 5}),
    'deployed': (447, 362, 100, 24, 21, '已部署單位', {'color': (40, 150, 160)}),
    'mini_res': (700, 334, 34, 9, -18, '預備', {'px': 9, 'glow': False, 'thr': 20}),
    'mini_dep': (686, 363, 32, 10, -23, '部署', {'px': 9, 'glow': False, 'thr': 20}),
    'ts':       (363, 136, 104, 11, 14, '單位部署', {'px': 11, 'thr': 20}),
}
JPG = ['ls_level', 'type', 'clear', 'auto', 'orig', 'ok', 'reserves', 'deployed', 'mini_res', 'mini_dep']   # 'ts' stays English (user)
# button clips (odv.dat): position in the jpg, captions they show
CLIP_POS = {'ad': (591, 502), 'cs': (152, 547), 'dr': (653, 418), 'ls': (31, 510), 'ok': (688, 442), 'rs': (556, 476),
            'dp': (668, 340), 'st': (682, 313)}
CLIP_KEYS = ['ls_name', 'type', 'clear', 'auto', 'orig', 'ok', 'mini_res', 'mini_dep']

def clip_labels(name, w, h):
    ox, oy = CLIP_POS[name]; out = []
    for k in CLIP_KEYS:
        cx, cy, lw, lh, ang, t, o = DP[k]
        x, y = cx - ox, cy - oy
        if -lw / 2 < x < w + lw / 2 and -lh / 2 < y < h + lh / 2:
            out.append((x, y, lw, lh, ang, t, o))
    return out

# Factory background (ft_back.jpg, NTF2.dat): (cx, cy, w, h, angle, text, opts)
FT_JPG = [(405, 25, 152, 30, 0, '工廠', {'px': 24, 'thr': 18, 'both': True}),
          (76, 52, 152, 22, 0, '出售單位', {'px': 15, 'thr': 18, 'both': True}), (724, 52, 114, 22, 0, '你的單位', {'px': 15, 'thr': 18, 'both': True}),
          (259, 391, 70, 13, 0, '步兵', {'thr': 15}), (352, 391, 44, 13, 0, '機動', {'thr': 15}),
          (456, 391, 66, 13, 0, '航空', {'thr': 15}), (555, 391, 78, 13, 0, '特種', {'thr': 15})]   # resource labels: hidden under FT-CTRP.XPF
