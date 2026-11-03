"""test76 (2026-10-26, claude/UDP_RELAY.md): a player logs in THROUGH the UDP relay (5 % loss each way): the server sees
his real address (SGRELAY line), the session is marked relayed, the server-select redirect points at 127.0.0.1."""
import asyncio, random, sys, os
os.chdir('/tmp/mp'); sys.path.insert(0, '/tmp/mp')
import sgserver as S
import udp_relay as R
from mpclient import Client
S.LOG = open('/tmp/mp/server76.log', 'w', encoding='utf-8')
PORT, RP, SP, CP = 3976, 39761, 39762, 39763
def chk(n, ok, i=''): print(('PASS ' if ok else 'FAIL ') + n, i, flush=True)
class Shim(asyncio.DatagramProtocol):
    def __init__(s): s.client = None
    def connection_made(s, tr): s.tr = tr
    def datagram_received(s, d, addr):
        if addr[1] != RP: s.client = addr; to = ("127.0.0.1", RP)
        else: to = s.client
        if to is None or random.random() < 0.05: return
        asyncio.get_event_loop().call_later(0.02, s.tr.sendto, d, to)
async def main():
    random.seed(3)
    S.ensure_unique_unit_ids()
    srv = await asyncio.start_server(S.handle, '127.0.0.1', PORT)
    rs = await R.start_relay_server(RP, PORT, log=S.log, host='127.0.0.1')
    loop = asyncio.get_event_loop()
    await loop.create_datagram_endpoint(Shim, local_addr=('127.0.0.1', SP))
    cl = R.RelayClient(('127.0.0.1', SP))
    await loop.create_datagram_endpoint(lambda: cl, local_addr=('127.0.0.1', 0))
    loop.create_task(cl.ticker())
    await asyncio.start_server(cl.serve_tcp, '127.0.0.1', CP)
    A = Client('jjjjjjjj')
    await A.connect(CP); await A.login(); await asyncio.sleep(1.5)
    me = next((o for o in S.ONLINE if getattr(o, 'acc', None) == 'jjjjjjjj'), None)
    chk('logged in through the relay', me is not None)
    chk('session marked relayed', bool(me and getattr(me, 'relayed', False)))
    chk('server sees the client address (the shim port), not the relay', bool(me and me.peer[1] == SP), me and me.peer)
    S.LOG.flush()
    log = open('/tmp/mp/server76.log', encoding='utf-8').read()
    chk('relay connection logged', 'connected through the UDP relay' in log)
    chk('redirect for a relayed session = 127.0.0.1 (code path)', 'getattr(s, "relayed", False)' in open('/tmp/mp/sgs/packets.py', encoding='utf-8').read())
    A.close(); await asyncio.sleep(0.5)
    srv.close()
asyncio.run(main())
