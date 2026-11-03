import asyncio, os, json, time, sys
sys.path.insert(0,'/tmp/mp'); import sgserver as S
S.ACCOUNTS_FILE='/tmp/mp/_acc_t.json'
open(S.ACCOUNTS_FILE,'w').write(json.dumps({"a":{"password":"x"+"y"*120}}))
async def main():
    asyncio.get_event_loop().create_task(S.accounts_flusher()); await asyncio.sleep(0.1)
    a=S.load_accounts(); a["b"]={"password":"p","n":1}; S.save_accounts(a)
    print("not yet on disk:", "b" not in json.load(open(S.ACCOUNTS_FILE)))
    await asyncio.sleep(2.6)
    print("flushed:", "b" in json.load(open(S.ACCOUNTS_FILE)))
    a["b"]["n"]=2; S.save_accounts(a); await asyncio.sleep(2.6)
    print("update:", json.load(open(S.ACCOUNTS_FILE))["b"]["n"]==2)
    d=json.load(open(S.ACCOUNTS_FILE)); d["c"]={"password":"q"}; time.sleep(0.05); json.dump(d,open(S.ACCOUNTS_FILE,'w'))
    os.utime(S.ACCOUNTS_FILE,(time.time()+5,time.time()+5))
    print("external edit seen:", "c" in S.load_accounts())
    # lag
    asyncio.get_event_loop().create_task(S.lag_monitor()); await asyncio.sleep(0.2); time.sleep(0.3); await asyncio.sleep(0.2)
    print("lag detected:", S.LAG_STATS["n"]>=1, round(S.LAG_STATS["max"],2))
asyncio.run(main())
