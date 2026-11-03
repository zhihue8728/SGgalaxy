"""test32: OTA - version table from updates/versions, old-client notice, blocked client, release broadcast,
countdown restart, update HTTP server (claude/OTA_PLAN.md)."""
import asyncio, hashlib, json, os, shutil, struct, sys, time, urllib.request
os.chdir('/tmp/mp'); sys.path.insert(0, '/tmp/mp')
import sgserver as S
import ota as OTA
from mpclient import Client
S.LOG = open('/tmp/mp/server32.log', 'w', encoding='utf-8')
PORT, UPORT = 3995, 3994
OLD_EXE, NEW_EXE = '/tmp/f22.exe', '/tmp/f23.exe'      # two client builds (F22 / F23)
def chk(n, ok, i=''): print(('PASS ' if ok else 'FAIL ') + n, i, flush=True)

U = '/tmp/mp_updates'
shutil.rmtree(U, ignore_errors=True)
def publish(ver, exe, release):
    os.makedirs(f'{U}/objects', exist_ok=True); os.makedirs(f'{U}/versions/{ver}', exist_ok=True)
    sha = hashlib.sha256(open(exe, 'rb').read()).hexdigest()
    shutil.copy(exe, f'{U}/objects/{sha}')
    m = {"version": ver, "channel": "cn", "files": [{"path": "SG.exe", "sha256": sha, "client": True}], "launcher": {"sha256": sha}}
    json.dump(m, open(f'{U}/versions/{ver}/manifest-cn.json', 'w'))
    json.dump(m, open(f'{U}/manifest-cn.json', 'w'))
    json.dump(release, open(f'{U}/release.json.tmp', 'w')); os.replace(f'{U}/release.json.tmp', f'{U}/release.json')
publish('1.0.0', OLD_EXE, {"version": "1.0.0"})
time.sleep(0.05)
publish('1.0.1', NEW_EXE, {"version": "1.0.1", "min_version": "", "deadline": time.time() + 3600, "notes": {"zh-cn": "测试说明"}})
S.UPDATE_DIR = U
S.OTA_V = OTA.Versions(U, S.client_code_hash)
S.OTA_V.reload()
H_OLD, H_NEW = S.client_code_hash(OLD_EXE), S.client_code_hash(NEW_EXE)
chk('version table: old build -> 1.0.0, new build -> 1.0.1', S.OTA_V.version_of(H_OLD) == '1.0.0' and S.OTA_V.version_of(H_NEW) == '1.0.1',
    {f'{k:08x}': v for k, v in S.OTA_V.by_hash.items()})

def texts(c, since):
    out = []
    for d in c.got(0x2A, since):
        n = d[2]; out.append(d[3:3 + n].decode('gbk', 'replace'))
    return out

async def login(name):
    A = Client(name); await A.connect(PORT); await A.login(); await asyncio.sleep(0.8)
    s = next(o for o in S.ONLINE if getattr(o, 'acc', '') == name and not o.w.is_closing())
    s.lang, s.enc = 'zh-cn', 'gbk'
    return A, s

async def main():
    srv = await asyncio.start_server(S.handle, '127.0.0.1', PORT)
    up = OTA.UpdateServer(U, rate_kb=200); usrv = await up.start('127.0.0.1', UPORT)
    # 1. old client (1.0.0) inside the deadline: plays, gets the update notice
    A, s = await login('jjjjjjjj'); t = time.monotonic()
    A.send(bytes([0xF6]) + struct.pack('>II', H_OLD, 0x22)); await asyncio.sleep(9)
    tx = texts(A, t)
    chk('old client: release recorded', getattr(s, 'client_release', None) == '1.0.0', getattr(s, 'client_release', None))
    chk('old client: still connected', not s.w.is_closing())
    chk('old client: update notice with deadline', any('有新版本 1.0.1' in x and '之后旧版将无法登录' in x for x in tx), tx[-2:])
    # 2. /version
    t = time.monotonic(); S.version_command(s); await asyncio.sleep(0.2)
    chk('/version shows client + release', any('client 1.0.0 / release 1.0.1' in x for x in texts(A, t)), texts(A, t))
    # 3. new release published -> online old clients told within one ota_cycle (15 s)
    task = asyncio.get_event_loop().create_task(S.ota_cycle())
    await asyncio.sleep(1); t = time.monotonic()
    publish('1.0.2', NEW_EXE, {"version": "1.0.2", "notes": {"zh-cn": "第三版"}})
    await asyncio.sleep(16)
    chk('release broadcast to the old client', any('新版本 1.0.2 已发布：第三版' in x for x in texts(A, t)), texts(A, t)[-1:])
    task.cancel()
    A.close(); await asyncio.sleep(0.3)
    # 4. min_version 1.0.1 -> the 1.0.0 client is refused with the update message
    publish('1.0.3', NEW_EXE, {"version": "1.0.3", "min_version": "1.0.1"}); S.OTA_V.reload()
    B, s = await login('jjjjjjjj'); t = time.monotonic()
    B.send(bytes([0xF6]) + struct.pack('>II', H_OLD, 0x22)); await asyncio.sleep(3.5)
    tx = texts(B, t)
    chk('blocked: update message', any('过旧' in x and '1.0.3' in x for x in tx), tx)
    chk('blocked: disconnected', s.w.is_closing())
    # 5. current client is fine
    C, s = await login('jjjjjjjj'); t = time.monotonic()
    C.send(bytes([0xF6]) + struct.pack('>II', H_NEW, 0x23)); await asyncio.sleep(1)
    chk('current client: no notice, connected', not s.w.is_closing() and not any('版本' in x for x in texts(C, t)), texts(C, t))
    # 6. countdown restart (os.kill replaced)
    killed = []
    real_kill = os.kill; os.kill = lambda pid, sig: killed.append(sig)
    t = time.monotonic(); S.restart_countdown(12, '测试'); await asyncio.sleep(15)
    tx = texts(C, t)
    chk('restart: countdown messages', any('12 秒' in x and '测试' in x for x in tx) and any('10 秒' in x for x in tx), tx)
    chk('restart: "restarting now" + exit signal', any('正在重启' in x for x in tx) and killed, killed)
    os.kill = real_kill
    t = time.monotonic(); S.restart_countdown(60); await asyncio.sleep(0.3); ok = S.restart_cancel(); await asyncio.sleep(0.3)
    chk('restart cancel', ok and any('已取消' in x for x in texts(C, t)))
    # 7. update downloads
    def get(path, rng=None):
        r = urllib.request.Request(f'http://127.0.0.1:{UPORT}/{path}', headers={'Range': rng} if rng else {})
        with urllib.request.urlopen(r) as f: return f.status, f.read()
    st, body = await asyncio.get_event_loop().run_in_executor(None, get, 'release.json')
    chk('http: release.json', st == 200 and json.loads(body)['version'] == '1.0.3')
    sha = json.load(open(f'{U}/manifest-cn.json'))['files'][0]['sha256']
    st, body = await asyncio.get_event_loop().run_in_executor(None, get, f'objects/{sha}', 'bytes=100-199')
    chk('http: range', st == 206 and body == open(NEW_EXE, 'rb').read()[100:200])
    t0 = time.monotonic(); st, body = await asyncio.get_event_loop().run_in_executor(None, get, f'objects/{sha}')
    dt = time.monotonic() - t0
    chk('http: bandwidth limit (200 KB/s)', len(body) == os.path.getsize(NEW_EXE) and dt > (len(body) - 200 * 1024) / (200 * 1024) * 0.8, f'{len(body)} B in {dt:.1f}s')
    srv.close(); usrv.close()
asyncio.run(main())
