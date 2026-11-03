"""test120 (2026-11-02, user "1/2/3都要加密"): the ENCRYPTED CONNECTION (tools/sgnet.py, SGX1 hello + AES-128-CTR) and the
ENCRYPTED game.db rows (server/acctstore.py, AES-256-GCM)."""
import asyncio, os, sys, json, sqlite3, struct
os.chdir('/tmp/mp'); sys.path.insert(0, '/tmp/mp')
import sgserver as S
import sgnet, acctstore
from mpclient import Client
from sgproto import parse_frames
S.LOG = open('/tmp/mp/server120.log', 'w', encoding='utf-8')
PORT = 3988
def chk(n, ok, i=''): print(('PASS ' if ok else 'FAIL ') + n, i, flush=True)

async def raw_conn(first=b''):
    r, w = await asyncio.open_connection('127.0.0.1', PORT)
    if first:
        w.write(first)
    return r, w

async def read_all(r, t=1.5):
    out = b''
    try:
        while True:
            c = await asyncio.wait_for(r.read(65536), t)
            if not c:
                return out, True                 # closed by the server
            out += c
    except asyncio.TimeoutError:
        return out, False

def selftest_c():
    """client/sgrender/sgcrypt.h (the DLLs' AES-CTR, SHA-256, X25519) against Python's cryptography: same bytes.
    Built with the host gcc (sgcrypt.h is plain C) from tools/sgcrypt_selftest.c; skipped without gcc / repo."""
    import shutil, subprocess, hashlib, random
    repo = os.environ.get('SG_REPO', '')
    src = os.path.join(repo, 'tools', 'sgcrypt_selftest.c')
    if not (repo and os.path.exists(src) and shutil.which('gcc')):
        print('SKIP C self-test (no gcc or repo)'); return
    exe = '/tmp/mp/sgcrypt_selftest'
    r = subprocess.run(['gcc', '-O2', '-o', exe, '-I', os.path.join(repo, 'client', 'sgrender'), src], capture_output=True, text=True)
    if r.returncode:
        chk('C self-test builds', False, r.stderr[:300]); return
    from cryptography.hazmat.primitives.ciphers import Cipher, algorithms, modes
    from cryptography.hazmat.primitives.asymmetric.x25519 import X25519PrivateKey, X25519PublicKey
    rnd = random.Random(120)
    lines, want = [], []
    for i in range(200):
        key, non = rnd.randbytes(16), rnd.randbytes(8)
        off, data = rnd.randrange(0, 5000), rnd.randbytes(rnd.randrange(1, 300))
        full = Cipher(algorithms.AES(key), modes.CTR(non + bytes(8))).encryptor().update(bytes(off) + data)[off:]
        lines.append(f'ctr {key.hex()} {non.hex()} {off} {data.hex()}'); want.append(full.hex())
        m = rnd.randbytes(rnd.randrange(1, 200))
        lines.append(f'sha {m.hex()}'); want.append(hashlib.sha256(m).hexdigest())
    for i in range(20):
        a, b = X25519PrivateKey.generate(), X25519PrivateKey.generate()
        ar = sgnet.raw_priv(a); bp = sgnet.raw_pub(b)
        lines.append(f'pub {ar.hex()}'); want.append(sgnet.raw_pub(a).hex())
        lines.append(f'x25519 {ar.hex()} {bp.hex()}'); want.append(a.exchange(X25519PublicKey.from_public_bytes(bp)).hex())
    # an encrypted game file (tools/sgcrypt_files.py format 2) read at random offsets, as ddraw.dll does
    sys.path.insert(0, os.path.join(repo, 'tools'))
    import sgcrypt_files as CF
    fk = CF.file_key()
    plain = rnd.randbytes(150000) + bytes(90000) + rnd.randbytes(120000)
    open('/tmp/mp/enc_test.dat', 'wb').write(CF.encrypt_bytes(plain, fk))
    for i in range(60):
        o = rnd.randrange(0, len(plain)); l = rnd.randrange(1, 70000)
        lines.append(f'fdec {fk.hex()} /tmp/mp/enc_test.dat {o} {l}'); want.append(plain[o:o + l].hex())
    out = subprocess.run([exe], input='\n'.join(lines) + '\n', capture_output=True, text=True).stdout.split()
    bad = sum(1 for x, y in zip(out, want) if x != y) + abs(len(out) - len(want))
    chk('C crypto (sgcrypt.h) = Python: AES-CTR at any offset, SHA-256, X25519, encrypted files at any offset', bad == 0, f'{bad} of {len(want)} differ')

def delta_check():
    """(11-02 "改") an edited file costs the launcher a few chunks, not the whole encrypted file"""
    import hashlib, random
    repo = os.environ.get('SG_REPO', '')
    if not repo:
        print('SKIP delta check (no repo)'); return
    sys.path.insert(0, os.path.join(repo, 'tools'))
    import sgcrypt_files as CF
    fk, rnd = CF.file_key(), random.Random(7)
    a = rnd.randbytes(3_000_000)
    b = a[:1_500_000] + rnd.randbytes(700) + a[1_500_000:]
    b = b[:200_000] + b'\x55' * 20 + b[200_020:]
    ea, eb = CF.encrypt_bytes(a, fk), CF.encrypt_bytes(b, fk)
    def keys(d):
        s, out = 0, []
        for e in CF.cut_points(d):                   # = the launcher's cutting (launcher/Ota.cs Cdc)
            out.append((hashlib.sha256(d[s:e]).digest()[:16], e - s)); s = e
        return out
    have = {k for k, _ in keys(ea)}
    miss = sum(n for k, n in keys(eb) if k not in have)
    chk('edited encrypted file: launcher downloads only a few chunks', miss < 300_000, f'{miss} of {len(eb)} B')
    chk('encrypted file decrypts back', CF.decrypt_bytes(eb, fk) == b)

async def main():
    S.ensure_unique_unit_ids()
    S.HELLO_WAIT = 2.0
    srv = await asyncio.start_server(S.handle, '127.0.0.1', PORT)
    # 1. a client without the encrypted connection (an old ddraw.dll): its first frame is 0xAA ... -> closed, nothing sent
    r, w = await raw_conn(bytes.fromhex('aa0003010203'))
    got, closed = await read_all(r)
    chk('plain client: closed at once', closed, got[:20])
    chk('plain client: nothing sent (not even SERVER CONNECTED)', got == b'', got[:20])
    # 2. a silent connection is closed after HELLO_WAIT
    r, w = await raw_conn()
    got, closed = await read_all(r, 4.0)
    chk('no hello: closed after the wait', closed and got == b'')
    # 3. a real hello: everything that comes back is encrypted (no plain "SERVER CONNECTED" on the wire) and decrypts
    priv, _ = sgnet.load_server_key()
    hello, enc, dec = sgnet.client_hello(sgnet.raw_pub(priv))
    r, w = await raw_conn(hello)
    got, closed = await read_all(r)
    chk('hello: connection stays open', not closed)
    chk('hello: no plain text on the wire', b'SERVER CONNECTED' not in got, got[:24].hex())
    fr, _ = parse_frames(dec(got))
    chk('hello: decrypts to SERVER CONNECTED', fr and fr[0][:16] == b'SERVER CONNECTED', fr[:1])
    w.close()
    # 4. hello split over several writes (TCP may cut it anywhere) + the first game frame in the same segment
    hello, enc, dec = sgnet.client_hello(sgnet.raw_pub(priv))
    r, w = await raw_conn(hello[:3]); await asyncio.sleep(0.2); w.write(hello[3:20]); await asyncio.sleep(0.2)
    w.write(hello[20:] + enc(bytes.fromhex('aa000158')))
    got, closed = await read_all(r)
    fr, _ = parse_frames(dec(got))
    chk('split hello accepted', not closed and fr and fr[0][:16] == b'SERVER CONNECTED')
    w.close()
    # 5. a hello for ANOTHER server key: the client cannot read the server (wrong stream keys)
    other = __import__('cryptography.hazmat.primitives.asymmetric.x25519', fromlist=['x']).X25519PrivateKey.generate()
    hello, enc, dec = sgnet.client_hello(sgnet.raw_pub(other))
    r, w = await raw_conn(hello)
    got, closed = await read_all(r)
    chk('wrong server key: nothing readable', b'SERVER CONNECTED' not in dec(got))
    w.close()
    # 6. the UDP relay line (from this host) before the hello
    hello, enc, dec = sgnet.client_hello(sgnet.raw_pub(priv))
    r, w = await raw_conn(b'SGRELAY 203.0.113.9 4567\n' + hello)
    got, closed = await read_all(r)
    fr, _ = parse_frames(dec(got))
    chk('relay line + hello', not closed and fr and fr[0][:16] == b'SERVER CONNECTED')
    w.close()
    # 7. a full login + game through mpclient (encrypted both ways, inner packet cipher unchanged)
    A = Client('jjjjjjjj'); await A.connect(PORT); await A.login(); await asyncio.sleep(1.5)
    chk('login through the encrypted connection', A.got(0x17) and A.bad == 0, (len(A.inbox), A.bad))
    # 8. mpclient with sgx=False is refused
    B = Client('kkkkkkkk'); await B.connect(PORT, sgx=False); await B.login(); await asyncio.sleep(1.0)
    chk('old client refused (no login reply)', not B.got(0x02) and not B.got(0x17), len(B.inbox))
    A.close()
    S.accounts_flush_now()
    # ---- game.db -------------------------------------------------------------------------------------------------
    c = sqlite3.connect('/tmp/mp/game.db')
    rows = c.execute("SELECT name, data FROM accounts").fetchall() + c.execute("SELECT key, data FROM kv").fetchall()
    chk('every game.db row is encrypted', rows and all(d.startswith('E1:') for _, d in rows), [n for n, d in rows if not d.startswith('E1:')][:5])
    chk('no account data readable in the file', all('commander' not in d and 'pbkdf2' not in d for _, d in rows))
    # a plain row (a database from before the switch) is encrypted when the database is opened
    c.execute("INSERT INTO kv(key, data, updated) VALUES('plain_test', '{\"a\":1}', 0)"); c.commit(); c.close()
    c2 = acctstore.connect('/tmp/mp/game.db')
    chk('plain row converted on open', acctstore.CONVERTED.get('/tmp/mp/game.db') == 1 and acctstore.kv_get(c2, 'plain_test') == {'a': 1})
    # a row moved to another name does not decrypt (name is the associated data)
    d = c2.execute("SELECT data FROM accounts WHERE name='jjjjjjjj'").fetchone()[0]
    try:
        acctstore.unseal(c2, 'accounts', 'kkkkkkkk', d); ok = False
    except Exception:
        ok = True
    chk('row bound to its name', ok)
    # the wrong key: load_all refuses (the server does not start with an empty account table)
    open('/tmp/mp/.dbkey_wrong', 'w').write(os.urandom(32).hex())
    old = os.environ['SG_DBKEY_FILE']; os.environ['SG_DBKEY_FILE'] = '/tmp/mp/.dbkey_wrong'
    c3 = acctstore.connect('/tmp/mp/game.db')
    try:
        acctstore.load_all(c3); ok = False
    except RuntimeError:
        ok = True
    chk('wrong key: load_all raises (no empty table)', ok)
    os.environ['SG_DBKEY_FILE'] = old
    del os.environ['SG_DBKEY_FILE']
    for p in acctstore.key_files('/tmp/mp/game.db'):
        pass
    try:
        acctstore.load_key('/nonexistent/x/game.db') if not os.path.exists(os.path.expanduser('~/.sgota/db_key')) else (_ for _ in ()).throw(RuntimeError())
        ok = False
    except RuntimeError:
        ok = True
    chk('no key: refused', ok)
    os.environ['SG_DBKEY_FILE'] = old
    selftest_c()
    delta_check()
    S.LOG.flush()
    log = open('/tmp/mp/server120.log', encoding='utf-8').read()
    chk('log: plain client named', 'not an encrypted client' in log)
    srv.close()

asyncio.run(main())
