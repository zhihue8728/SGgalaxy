"""ENCRYPTED CONNECTION (2026-11-02, user 13:56 "1/2/3都要加密" + "立即只接受加密连线").
The whole TCP byte stream between SG.exe and the server is AES-128-CTR encrypted, under the game's own packet format
(the XOR cipher of sgproto.py still runs inside).  The client side lives in the game folder's ddraw.dll
(client/sgrender/ddraw_proxy.c: hooks of SG.exe's WSOCK32 connect / send / recv / closesocket); same primitives as
client/sgrender/sgcrypt.h.

Handshake (no round trip): right after connect the client sends HELLO = b"SGX1" + its new X25519 public key (32 bytes,
a fresh key per connection).  Both sides compute
    shared = X25519(client secret, SERVER public) = X25519(SERVER secret, client public)
    k      = SHA-256(b"SGX1" + shared + client public + server public)
    client -> server: AES-128-CTR key k[:16], server -> client: key k[16:], counter block 0 = 16 zero bytes, one stream
    per direction for the whole connection (no rekeying; a connection carries far less than 2^64 blocks).
The SERVER key is static: its public half is built into ddraw.dll (client/sgrender/sgnet_pub.h), its secret half exists
only on the server (/opt/sgserver/.netkey) and in the publisher's %USERPROFILE%\\.sgota\\net_key.json - NEVER in the repo.
Only the server can read a connection; a man in the middle cannot pretend to be the server.
The server reads HELLO before it sends anything ("SERVER CONNECTED" comes after it, encrypted); a connection that does
not start with b"SGX1" (a client without the new ddraw.dll) is closed.
Needs the 'cryptography' package (the server: apt python3-cryptography, installed by deploy/remote.sh).
usage: python tools/sgnet.py keygen     -> %USERPROFILE%\\.sgota\\net_key.json (once; prints only the PUBLIC key)
       python tools/sgnet.py header     -> client/sgrender/sgnet_pub.h from that file's public key"""
import hashlib, json, os, sys

MAGIC = b"SGX1"
HELLO_LEN = len(MAGIC) + 32
KEY_FILE_ENV = "SG_NETKEY_FILE"


def _crypto():
    from cryptography.hazmat.primitives.asymmetric.x25519 import X25519PrivateKey, X25519PublicKey
    from cryptography.hazmat.primitives.ciphers import Cipher, algorithms, modes
    from cryptography.hazmat.primitives import serialization as ser
    return X25519PrivateKey, X25519PublicKey, Cipher, algorithms, modes, ser


def raw_pub(priv):
    *_, ser = _crypto()
    return priv.public_key().public_bytes(ser.Encoding.Raw, ser.PublicFormat.Raw)


def raw_priv(priv):
    *_, ser = _crypto()
    return priv.private_bytes(ser.Encoding.Raw, ser.PrivateFormat.Raw, ser.NoEncryption())


class Stream:
    """one direction: AES-128-CTR from counter 0, stateful (bytes in order)"""
    def __init__(self, key):
        _, _, Cipher, algorithms, modes, _ = _crypto()
        self._c = Cipher(algorithms.AES(key), modes.CTR(bytes(16))).encryptor()

    def __call__(self, data):
        return self._c.update(data) if data else data


def derive(shared, cpub, spub):
    k = hashlib.sha256(MAGIC + shared + cpub + spub).digest()
    return k[:16], k[16:]                      # (client -> server, server -> client)


def default_key_files():
    here = os.path.dirname(os.path.abspath(__file__))
    out = []
    if os.environ.get(KEY_FILE_ENV):
        out.append(os.environ[KEY_FILE_ENV])
    out += [os.path.join(here, "..", ".netkey"), os.path.join(here, "..", "..", ".netkey"),
            os.path.expanduser(os.path.join("~", ".sgota", "net_key.json"))]
    return out


def load_server_key(path=None):
    """the server's X25519 secret: a file with 64 hex chars, or JSON {"private": hex}."""
    X25519PrivateKey = _crypto()[0]
    for p in ([path] if path else default_key_files()):
        if p and os.path.exists(p):
            t = open(p, encoding="utf-8").read().strip()
            hx = json.loads(t)["private"] if t.startswith("{") else t
            return X25519PrivateKey.from_private_bytes(bytes.fromhex(hx)), p
    return None, None


def server_accept(priv, hello):
    """-> (decrypt client->server, encrypt server->client) for a HELLO; ValueError when it is not one"""
    if len(hello) != HELLO_LEN or hello[:4] != MAGIC:
        raise ValueError("not an SGX1 hello")
    X25519PublicKey = _crypto()[1]
    cpub = hello[4:]
    shared = priv.exchange(X25519PublicKey.from_public_bytes(cpub))
    c2s, s2c = derive(shared, cpub, raw_pub(priv))
    return Stream(c2s), Stream(s2c)


def client_hello(server_pub):
    """(the test client) -> (HELLO bytes, encrypt client->server, decrypt server->client)"""
    X25519PrivateKey, X25519PublicKey = _crypto()[:2]
    me = X25519PrivateKey.generate()
    cpub = raw_pub(me)
    shared = me.exchange(X25519PublicKey.from_public_bytes(server_pub))
    c2s, s2c = derive(shared, cpub, server_pub)
    return MAGIC + cpub, Stream(c2s), Stream(s2c)


def _keygen():
    X25519PrivateKey = _crypto()[0]
    p = os.path.expanduser(os.path.join("~", ".sgota", "net_key.json"))
    if os.path.exists(p):
        sys.exit(f"{p} exists - not replaced (a new key needs a new ddraw.dll for every player)")
    os.makedirs(os.path.dirname(p), exist_ok=True)
    k = X25519PrivateKey.generate()
    with open(p, "w", encoding="utf-8") as f:
        json.dump({"private": raw_priv(k).hex(), "public": raw_pub(k).hex(),
                   "_comment": "SGalaxy connection key (tools/sgnet.py). NEVER put this file in the repo. "
                               "deploy.ps1 copies it to /opt/sgserver/.netkey"}, f, indent=1)
    print("public key:", raw_pub(k).hex())


def _header():
    p = os.path.expanduser(os.path.join("~", ".sgota", "net_key.json"))
    pub = bytes.fromhex(json.load(open(p, encoding="utf-8"))["public"])
    out = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "client", "sgrender", "sgnet_pub.h")
    body = ", ".join(f"0x{b:02x}" for b in pub)
    open(out, "w", encoding="utf-8").write(
        "/* the server's X25519 PUBLIC key for the encrypted connection (tools/sgnet.py header; secret half only on the\n"
        "   server and in %USERPROFILE%\\.sgota\\net_key.json) */\n"
        f"static const unsigned char SGNET_SERVER_PUB[32] = {{ {body} }};\n")
    print(out, pub.hex())


if __name__ == "__main__":
    {"keygen": _keygen, "header": _header}.get((sys.argv[1:] or ["?"])[0], lambda: sys.exit(__doc__))()
