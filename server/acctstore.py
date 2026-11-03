"""Game data storage for the SGalaxy server (2026-10-22): one SQLite file (game.db) instead of the JSON files.

* table accounts: one row per account (units, resources, commander ... as JSON) - a save writes only changed accounts
* table kv: the other data the server writes - "world" (owners, garrisons, power, politics), "npcs", "regiments"

* one row per account (name, JSON text); a save writes only the accounts that changed, whatever the number of accounts
* passwords are stored as salted PBKDF2 hashes ("pw"), never as plain text; old plain "password" fields are converted
  the first time the account logs in (or at once by tools/acct.py hashpw-all)
* WAL mode: the server keeps writing while tools/acct.py reads or edits; the server notices outside edits
  (PRAGMA data_version) and reloads them
* (2026-11-02, user "1/2/3都要加密") every row's data is ENCRYPTED: "E1:" + base64(nonce 12 | AES-256-GCM ciphertext+tag),
  the table and row name are the associated data (a row cannot be moved to another name).  Key: 32 random bytes as hex in
  SG_DBKEY_FILE, or <server dir>/../.dbkey (/opt/sgserver/.dbkey, owner sg, mode 600 - deploy/remote.sh puts it there
  from %USERPROFILE%\.sgota\db_key), or %USERPROFILE%\.sgota\db_key; NEVER in the repo.  Without the key the data is lost
  - keep a copy of %USERPROFILE%\.sgota.  Plain rows (before the switch) are encrypted when the database is opened.
Used by server/sgserver.py and tools/acct.py.  Python standard library + 'cryptography' (apt python3-cryptography)."""
import base64, hashlib, hmac, json, os, sqlite3, threading, time

LOCK = threading.RLock()     # one connection, used by the event loop and the writer thread

PBKDF2_ITER = 60000          # ~20-40 ms per login on a small cloud CPU


# ---- passwords -------------------------------------------------------------------------------------------------
def pw_hash(pw, iters=PBKDF2_ITER):
    salt = os.urandom(16)
    h = hashlib.pbkdf2_hmac("sha256", pw.encode("latin-1", "replace"), salt, iters)
    return f"pbkdf2_sha256${iters}${salt.hex()}${h.hex()}"


def pw_check(rec, pw):
    """True when pw is the password of this account record (hash "pw", or an old plain "password")."""
    if not isinstance(rec, dict) or pw is None:
        return False
    st = rec.get("pw")
    if st:
        try:
            algo, iters, salt, h = st.split("$")
            got = hashlib.pbkdf2_hmac("sha256", pw.encode("latin-1", "replace"), bytes.fromhex(salt), int(iters))
            return hmac.compare_digest(got.hex(), h)
        except Exception:
            return False
    plain = rec.get("password")
    return plain is not None and hmac.compare_digest(str(plain), str(pw))


def pw_set(rec, pw):
    rec["pw"] = pw_hash(pw)
    rec.pop("password", None)


def pw_upgrade(rec, pw):
    """after a successful login with an old plain password: store the hash instead.  True if changed."""
    if "password" in rec and not rec.get("pw"):
        pw_set(rec, pw)
        return True
    return False


# ---- row encryption (2026-11-02) ----------------------------------------------------------------------------------
ENC_PREFIX = "E1:"
KEY_ENV = "SG_DBKEY_FILE"
_AEAD = {}                   # db path -> AESGCM


def key_files(db_path):
    out = [os.environ[KEY_ENV]] if os.environ.get(KEY_ENV) else []
    d = os.path.dirname(os.path.abspath(db_path))
    out += [os.path.join(d, "..", ".dbkey"), os.path.expanduser(os.path.join("~", ".sgota", "db_key"))]
    return out


def load_key(db_path):
    """-> (32-byte key, file).  RuntimeError when there is none: the server must not start without it (it would write
    plain rows) - tools/sgdbkey or deploy/remote.sh create it."""
    for p in key_files(db_path):
        if os.path.exists(p):
            k = bytes.fromhex(open(p, encoding="ascii").read().strip())
            if len(k) != 32:
                raise RuntimeError(f"{p}: the database key must be 64 hex characters")
            return k, p
    raise RuntimeError("no database key (" + " / ".join(key_files(db_path)) + "): game.db is encrypted; "
                       "deploy/remote.sh installs it, or set " + KEY_ENV)


def _aead(c):
    return _AEAD[id(c)]


def seal(c, table, name, text):
    n = os.urandom(12)
    ct = _aead(c).encrypt(n, text.encode("utf-8"), f"{table}:{name}".encode("utf-8"))
    return ENC_PREFIX + base64.b64encode(n + ct).decode("ascii")


def unseal(c, table, name, data):
    if not data.startswith(ENC_PREFIX):
        return data                                  # a plain row (before the switch; encrypt_all converts them)
    raw = base64.b64decode(data[len(ENC_PREFIX):])
    return _aead(c).decrypt(raw[:12], raw[12:], f"{table}:{name}".encode("utf-8")).decode("utf-8")


def encrypt_all(c):
    """plain rows -> encrypted, one transaction; -> number of rows converted"""
    n = 0
    with LOCK:
        c.execute("BEGIN IMMEDIATE")
        try:
            for table, col in (("accounts", "name"), ("kv", "key")):
                rows = c.execute(f"SELECT {col}, data FROM {table} WHERE data NOT LIKE 'E1:%'").fetchall()
                c.executemany(f"UPDATE {table} SET data=? WHERE {col}=?", [(seal(c, table, k, d), k) for k, d in rows])
                n += len(rows)
            c.execute("COMMIT")
        except Exception:
            c.execute("ROLLBACK")
            raise
    return n


# ---- database ----------------------------------------------------------------------------------------------------
def connect(db_path):
    from cryptography.hazmat.primitives.ciphers.aead import AESGCM
    key, _ = load_key(db_path)
    c = sqlite3.connect(db_path, timeout=30, check_same_thread=False, isolation_level=None)
    _AEAD[id(c)] = AESGCM(key)
    c.execute("PRAGMA journal_mode=WAL")
    c.execute("PRAGMA synchronous=NORMAL")          # WAL + NORMAL: safe against crashes of the program
    c.execute("CREATE TABLE IF NOT EXISTS accounts (name TEXT PRIMARY KEY, data TEXT NOT NULL, updated REAL)")
    c.execute("CREATE TABLE IF NOT EXISTS kv (key TEXT PRIMARY KEY, data TEXT NOT NULL, updated REAL)")
    CONVERTED[db_path] = encrypt_all(c)
    return c


CONVERTED = {}               # db path -> plain rows encrypted when it was opened (logged by the server)


def kv_get(c, key):
    with LOCK:
        r = c.execute("SELECT data FROM kv WHERE key=?", (key,)).fetchone()
    return json.loads(unseal(c, "kv", key, r[0])) if r else None


def kv_put(c, key, obj=None, text=None):
    text = text if text is not None else json.dumps(obj, ensure_ascii=False, separators=(",", ":"))
    with LOCK:
        c.execute("INSERT INTO kv(key, data, updated) VALUES(?,?,?) "
                  "ON CONFLICT(key) DO UPDATE SET data=excluded.data, updated=excluded.updated",
                  (key, seal(c, "kv", key, text), time.time()))


def migrate_kv(c, key, json_path):
    """first start: world.json / npcs.json / regiments.json -> kv row, old file kept as *.migrated."""
    if not os.path.exists(json_path):
        return False
    with LOCK:
        have = c.execute("SELECT 1 FROM kv WHERE key=?", (key,)).fetchone()
    if not have:
        with open(json_path, encoding="utf-8") as f:
            kv_put(c, key, json.load(f))
    os.replace(json_path, json_path + ".migrated")
    return True


def migrate_json(c, json_path):
    """first start after the switch: copy accounts.json into the database, keep the old file as *.migrated."""
    if not os.path.exists(json_path):
        return 0
    with LOCK:
        n = c.execute("SELECT COUNT(*) FROM accounts").fetchone()[0]
    if n:
        os.replace(json_path, json_path + ".migrated")
        return 0
    with open(json_path, encoding="utf-8") as f:
        d = json.load(f)
    write(c, {k: json.dumps(v, separators=(",", ":")) for k, v in d.items()}, [])
    os.replace(json_path, json_path + ".migrated")
    return len(d)


def load_all(c):
    out = {}
    with LOCK:
        rows = c.execute("SELECT name, data FROM accounts").fetchall()
    for name, data in rows:
        try:
            out[name] = json.loads(unseal(c, "accounts", name, data))
        except Exception as e:
            if isinstance(e, ValueError) and not str(data).startswith(ENC_PREFIX):
                continue                             # (a broken plain row: skipped, as before)
            raise RuntimeError(f"game.db: account {name!r} cannot be decrypted ({type(e).__name__}) - wrong database "
                               "key?  The server stops rather than run without the account") from e
    return out


def write(c, changed, deleted):
    """changed = {name: json text}; deleted = [names]; one transaction."""
    if not changed and not deleted:
        return
    now = time.time()
    with LOCK:
        _write(c, changed, deleted, now)


def _write(c, changed, deleted, now):
    c.execute("BEGIN IMMEDIATE")
    try:
        c.executemany("INSERT INTO accounts(name, data, updated) VALUES(?,?,?) "
                      "ON CONFLICT(name) DO UPDATE SET data=excluded.data, updated=excluded.updated",
                      [(k, seal(c, "accounts", k, v), now) for k, v in changed.items()])
        if deleted:
            c.executemany("DELETE FROM accounts WHERE name=?", [(k,) for k in deleted])
        c.execute("COMMIT")
    except Exception:
        c.execute("ROLLBACK")
        raise


def data_version(c):
    with LOCK:
        return c.execute("PRAGMA data_version").fetchone()[0]


def count_accounts(c):
    with LOCK:
        return c.execute("SELECT COUNT(*) FROM accounts").fetchone()[0]


def backup_to(c, path):
    """consistent copy of the live database (also while the server writes)."""
    dst = sqlite3.connect(path)
    with LOCK, dst:
        c.backup(dst)
    dst.close()


def export_json(accs, path):
    with open(path, "w", encoding="utf-8") as f:
        json.dump(accs, f, ensure_ascii=False, separators=(",", ":"))
