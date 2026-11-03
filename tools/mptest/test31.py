"""test31: game.db storage - hashed passwords, write-behind of changed accounts only, outside edits reload, world in db."""
import asyncio, os, sys, time, json, sqlite3, subprocess, struct
os.chdir('/tmp/mp'); sys.path.insert(0, '/tmp/mp')
import sgserver as S
from mpclient import Client
S.LOG = open('/tmp/mp/server31.log', 'w', encoding='utf-8')
PORT = 3998
def chk(n, ok, i=''): print(('PASS ' if ok else 'FAIL ') + n, i, flush=True)
def row(name):
    c = sqlite3.connect('/tmp/mp/game.db'); r = c.execute("SELECT data, updated FROM accounts WHERE name=?", (name,)).fetchone(); c.close()
    # (11-02) rows are encrypted: decrypted with the server's own connection (acctstore.unseal)
    return (json.loads(S.STORE.unseal(S.db(), 'accounts', name, r[0])), r[1]) if r else (None, None)
async def main():
    accs = S.load_accounts(); accs['hhhhhhhh'].pop('pw', None); accs['hhhhhhhh']['password'] = 'ji3g4go6'; S.save_accounts(accs)
    asyncio.get_event_loop().create_task(S.accounts_flusher())
    srv = await asyncio.start_server(S.handle, '127.0.0.1', PORT)
    t = time.monotonic()
    B = Client('hhhhhhhh', pw='wrong'); await B.connect(PORT); await B.login(); await asyncio.sleep(0.5)
    chk('wrong password refused', any(b[:2] == b'\x02\x01' for b in B.got(0x02, t)))
    B = Client('hhhhhhhh'); await B.connect(PORT); await B.login(); await asyncio.sleep(3.0)
    d, _ = row('hhhhhhhh')
    chk('plain password converted to a salted hash on login', d and d.get('pw', '').startswith('pbkdf2_sha256$') and 'password' not in d)
    chk('hash is not the password', 'ji3g4go6' not in json.dumps(d))
    _, u_j = row('jjjjjjjj')
    accs = S.load_accounts(); accs['hhhhhhhh']['resources'][0] += 1; S.save_accounts(accs); await asyncio.sleep(2.6)
    d2, u_h = row('hhhhhhhh'); _, u_j2 = row('jjjjjjjj')
    chk('write-behind stores the change', d2['resources'][0] == accs['hhhhhhhh']['resources'][0])
    chk('only the changed account is rewritten', u_j2 == u_j and u_h > u_j)
    r = subprocess.run([sys.executable, 'tools/acct.py', 'give', 'hhhhhhhh', 'ura', '7'], env=dict(os.environ, SG_SERVER_DIR='/tmp/mp'),
                       capture_output=True, text=True)
    before = d2['resources'][3]
    await asyncio.sleep(2.6)
    chk('outside edit (tools/acct.py) is reloaded by the running server', S.load_accounts()['hhhhhhhh']['resources'][3] == before + 7, r.stdout + r.stderr)
    t = time.monotonic()
    B.send(bytes([7]) + bytes([8]) + b'hhhhhhhh' + bytes([8]) + b'ji3g4go6' + bytes([5]) + b'newpw'); await asyncio.sleep(0.5)
    ok1 = S.STORE.pw_check(S.load_accounts()['hhhhhhhh'], 'newpw')
    S.STORE.pw_set(S.load_accounts()['hhhhhhhh'], 'ji3g4go6'); S.save_accounts(S.load_accounts()); S.accounts_flush_now()
    chk('password change works with the hash', ok1)
    S.set_province_owner(600101, 2)
    c = sqlite3.connect('/tmp/mp/game.db'); w = json.loads(S.STORE.unseal(S.db(), 'kv', 'world', c.execute("SELECT data FROM kv WHERE key='world'").fetchone()[0])); c.close()
    chk('world (province owners) stored in game.db', w['owners'].get('600101') == 2)
    chk('no JSON data files written any more', not any(os.path.exists(f) for f in ('accounts.json', 'world.json', 'npcs.json', 'regiments.json')))
    S.set_province_owner(600101, 0)
    srv.close()
asyncio.run(main())
