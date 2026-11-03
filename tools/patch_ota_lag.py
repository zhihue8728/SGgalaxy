"""start-up stall (user 2026-10-22 22:31: "!! event loop stalled 1862 ms" right after "OTA: release ..."): the OTA version
table computed the code checksum of every published client exe in the game loop (~0.5 s each, pure Python).  Now the
checksums are cached on disk by object sha256 (updates/code_hash_cache.json) and the table is (re)loaded in a thread."""
import sys
P = sys.argv[1] if len(sys.argv) > 1 else "server/sgserver.py"
src = open(P, encoding="utf-8").read()
def rep(old, new, cnt=1):
    global src
    if new in src:
        return
    n = src.count(old)
    assert n == cnt, (n, old[:90])
    src = src.replace(old, new)

rep('''OTA_V = OTA.Versions(UPDATE_DIR, client_code_hash)''', '''_CODE_HASH_CACHE = os.path.join(UPDATE_DIR, "code_hash_cache.json")

def cached_code_hash(path):
    """client_code_hash of an update object, remembered by its file name (= sha256 of the content)."""
    key = os.path.basename(path)
    try:
        cache = json.load(open(_CODE_HASH_CACHE))
    except Exception:
        cache = {}
    if key in cache:
        return cache[key]
    h = client_code_hash(path)
    cache[key] = h
    try:
        tmp = _CODE_HASH_CACHE + ".tmp"
        json.dump(cache, open(tmp, "w"))
        os.replace(tmp, _CODE_HASH_CACHE)
    except Exception:
        pass
    return h

OTA_V = OTA.Versions(UPDATE_DIR, cached_code_hash)''')
rep('''    try:
        OTA_V.reload()
    except Exception as e:
        log(f"   OTA reload error: {e!r}")
    if OTA_V.current:''', '''    try:
        await asyncio.get_event_loop().run_in_executor(None, OTA_V.reload)     # not in the game loop (hashing)
    except Exception as e:
        log(f"   OTA reload error: {e!r}")
    if OTA_V.current:''')
rep('''            if OTA_V.reload():
                log(f"   OTA: new release {OTA_V.current}")''', '''            if await asyncio.get_event_loop().run_in_executor(None, OTA_V.reload):
                log(f"   OTA: new release {OTA_V.current}")''')
open(P, "w", encoding="utf-8").write(src)
print("patched")
