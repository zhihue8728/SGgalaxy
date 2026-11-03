import asyncio, struct, sys, os, time
os.chdir('/tmp/mp'); sys.path.insert(0, '/tmp/mp')
import sgserver as S
from mpclient import Client, s8
S.LOG = open('/tmp/mp/server.log', 'w', encoding='utf-8')
PORT = 3999
def say(*a): print(*a, flush=True)

async def main():
    S.ensure_unique_unit_ids()
    srv = await asyncio.start_server(S.handle, '127.0.0.1', PORT)
    A, B = Client('jjjjjjjj'), Client('kkkkkkkk')
    await A.connect(PORT); await A.login()
    await B.connect(PORT); await B.login()
    await asyncio.sleep(1)
    say('A got types', sorted({b[0] for _, b in A.inbox}))
    say('A enter 0x17:', [b.hex()[:30] for b in A.got(0x17)])
    say('B enter 0x17:', [b.hex()[:30] for b in B.got(0x17)])
    say('A puts:', A.puts()[:6]); say('B puts:', B.puts()[:6])
    ha = S.hero_uid('jjjjjjjj'); hb = S.hero_uid('kkkkkkkk'); say('hero uids', ha, hb)
    t = time.monotonic()
    B.lumps(bytes([0x16]) + struct.pack('>IHHHB', hb, 0x300, 0x300, 0, 0))
    await asyncio.sleep(0.6)
    say('A relayed lumps after B move:', [(tk, m.hex()) for tk, m in A.lump_msgs(t)][:4])
    say('B relayed lumps:', [(tk, m.hex()) for tk, m in B.lump_msgs(t)][:4])
    A.close(); B.close(); await asyncio.sleep(0.3); srv.close()
asyncio.run(main())
