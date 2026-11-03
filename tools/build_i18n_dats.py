#!/usr/bin/env python3
"""i18n phase 4: put the Chinese-captioned UI files into copies of the game archives.
  NTF2.dat <- out/ui_tw | out/ui_cn   (sprites / jpg, tools/ui4/build_ui.py, bik_build.py)
  odv.dat  <- out/bik_tw | out/bik_cn (Bink clips re-encoded by tools/ui4/binkenc.py)
-> out/NTF2_tw.dat, out/NTF2_cn.dat, out/odv_tw.dat, out/odv_cn.dat
usage: build_i18n_dats.py "<game folder>"   (reads <name>.dat.orig when it exists)"""
import os, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from build_ntf2 import replace
gd = sys.argv[1]; here = os.path.dirname(os.path.abspath(__file__)); outd = os.path.join(here, '..', 'out')
for dat, sub in (('NTF2', 'ui'), ('odv', 'bik')):
    src = os.path.join(gd, dat + '.dat.orig')
    if not os.path.exists(src): src = os.path.join(gd, dat + '.dat')
    for lang in ('tw', 'cn'):
        fd = os.path.join(outd, f'{sub}_{lang}')
        files = {f: open(os.path.join(fd, f), 'rb').read() for f in os.listdir(fd)}
        dst = os.path.join(outd, f'{dat}_{lang}.dat')
        print(dat, lang, 'replaced', replace(src, dst, files), 'of', len(files), '->', dst)
