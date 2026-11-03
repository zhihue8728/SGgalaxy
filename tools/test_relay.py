"""loss test of udp_relay: game stub <- TCP -> server relay <- UDP (lossy shim: loss, 107 ms +- jitter one way) -> client
relay <- TCP -> test client.  Checks byte integrity both ways and the delivery delay of 33 ms frames."""
import asyncio, random, struct, sys, time
import udp_relay as R
LOSS = float(sys.argv[1]) if len(sys.argv) > 1 else 0.05
ONEWAY, JIT = 0.1075, 0.010
SECS = float(sys.argv[2]) if len(sys.argv) > 2 else 20
G, RP, SP, CP = 39100, 39101, 39102, 39103
res = {"frames": [], "up": [], "hdr": None, "bad": 0}

async def game(reader, writer):
    hdr = await reader.readline()
    res["hdr"] = hdr
    async def up():
        buf = b""
        exp = 0
        while True:
            d = await reader.read(4096)
            if not d: return
            buf += d
            while len(buf) >= 12:
                n, ts = struct.unpack_from(">Id", buf); buf = buf[12:]
                if n != exp: res["bad"] += 1
                exp = n + 1
                res["up"].append(time.monotonic() - ts) if n > 10 else None
    asyncio.get_event_loop().create_task(up())
    n = 0
    while True:
        writer.write(struct.pack(">Id", n, time.monotonic()) + bytes(20)); n += 1
        if n % 150 == 0:
            writer.write(bytes(range(256)) * 40)          # a 10 KB burst now and then (battle entry, maps)
        await asyncio.sleep(0.033)

class Shim(asyncio.DatagramProtocol):
    def __init__(s): s.client = None
    def connection_made(s, tr): s.tr = tr
    def datagram_received(s, d, addr):
        if addr[1] != RP: s.client = addr; to = ("127.0.0.1", RP)
        else: to = s.client
        if random.random() < LOSS or to is None: return
        asyncio.get_event_loop().call_later(max(0.0, ONEWAY + random.gauss(0, JIT)), s.tr.sendto, d, to)

async def main():
    random.seed(7)
    await asyncio.start_server(game, "127.0.0.1", G)
    await R.start_relay_server(RP, G, log=lambda m: None, host="127.0.0.1")
    loop = asyncio.get_event_loop()
    await loop.create_datagram_endpoint(Shim, local_addr=("127.0.0.1", SP))
    if len(sys.argv) > 3 and sys.argv[3] == "cs":        # the C# client (mono SGRelay.exe)
        p = await asyncio.create_subprocess_exec("mono", "SGRelay.exe", "--server", "127.0.0.1", "--port", str(SP),
                                                 "--listen", str(CP), "--no-registry", stdout=asyncio.subprocess.PIPE)
        line = await asyncio.wait_for(p.stdout.readline(), 10)
        print("SGRelay:", line.decode().strip())
    else:
        cl = R.RelayClient(("127.0.0.1", SP))
        await loop.create_datagram_endpoint(lambda: cl, local_addr=("127.0.0.1", 0))
        loop.create_task(cl.ticker())
        await asyncio.start_server(cl.serve_tcp, "127.0.0.1", CP)
    r, w = await asyncio.open_connection("127.0.0.1", CP)
    t_end = time.monotonic() + SECS
    async def send_up():
        n = 0
        while time.monotonic() < t_end:
            w.write(struct.pack(">Id", n, time.monotonic())); n += 1
            await asyncio.sleep(random.uniform(0.05, 0.4))      # clicks
    loop.create_task(send_up())
    buf = b""; exp = 0
    while time.monotonic() < t_end:
        try:
            d = await asyncio.wait_for(r.read(65536), 1)
        except asyncio.TimeoutError:
            continue
        buf += d
        while len(buf) >= 32:
            if buf[:4] == b"\x00\x01\x02\x03":
                if len(buf) < 10240: break
                if buf[:10240] != bytes(range(256)) * 40: res["bad"] += 1
                buf = buf[10240:]; continue
            n, ts = struct.unpack_from(">Id", buf)
            if n != exp: res["bad"] += 1; print("seq", n, exp)
            exp = n + 1
            (res["frames"].append(time.monotonic() - ts) if n > 60 else None); buf = buf[32:]
    f = sorted(res["frames"]); u = sorted(res["up"])
    q = lambda a, p: a[min(len(a) - 1, int(len(a) * p))] * 1000
    late = sum(1 for x in f if x > ONEWAY + 0.100) / len(f) * 100
    print(f"loss {LOSS*100:.0f}% each way, one-way {ONEWAY*1000:.0f}+-{JIT*1000:.0f} ms, {SECS:.0f} s")
    print(f"header {res['hdr']!r}, integrity errors {res['bad']}")
    print(f"down: {len(f)} frames  p50 {q(f,.5):.0f}  p99 {q(f,.99):.0f}  p99.9 {q(f,.999):.0f}  max {f[-1]*1000:.0f} ms;"
          f"  >100 ms over the one-way delay: {late:.2f}%")
    print(f"up:   {len(u)} msgs    p50 {q(u,.5):.0f}  p99 {q(u,.99):.0f}  max {u[-1]*1000:.0f} ms")
asyncio.run(main())
