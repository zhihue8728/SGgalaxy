"""Minimal Shattered Galaxy 1.8.5 probe server.

Goal of this stage: let the real SG.exe connect, complete the first handshake, and LOG every
client packet (decoded) so the protocol notes in PROTOCOL.md can be verified against real traffic.

Handshake as recovered from SG.exe (FUN_005a5c50 / FUN_005a8900):
  1. server -> client : plain frame whose payload contains the text "SERVER CONNECTED"
                        (client then switches its receive side to encrypted mode)
  2. client -> server : type 0 = u16 version (0x00B9 = client 1.8.5), u8 0x57, u8 1, u8 nation   (+ trailing 0x00)
  3. server -> client : type 0 + sub-code ... (NOT implemented yet; this stage only logs)

Run:  python server/sgserver.py [--host 0.0.0.0] [--port 3000]
"""
# ---- STRUCTURE (2026-10-24, docs/11_ARCH_REVIEW.md B3) -----------------------------------------------------------------
# The server code lives in server/sgs/*.py, executed here in this order into this module's namespace (one namespace as
# before: every function and global is still sgserver.X for the tests and tools, GM commands can rebind globals, the
# tracebacks name the part file).  python tools/check_server.py runs pyflakes over all parts together.
import os as _os
PARTS = ("core_net", "world", "units_items_lab", "commander_deploy", "battle_rules", "unit_orders", "battle_flow", "results_field", "unit_hp",
         "battle_maps", "strategic_map", "social", "board_mail", "gm_starcenter", "packets", "client_ota", "npc_world", "npc_battle")
_SGS = _os.path.join(_os.path.dirname(_os.path.abspath(__file__)), "sgs")
for _part in PARTS:
    _path = _os.path.join(_SGS, _part + ".py")
    with open(_path, encoding="utf-8") as _fh:
        exec(compile(_fh.read(), _path, "exec"), globals())
del _part, _path, _fh

async def main():
    global LOG
    ap = argparse.ArgumentParser()
    ap.add_argument("--host", default="0.0.0.0")
    ap.add_argument("--port", type=int, default=3000)
    ap.add_argument("--log", default="sgserver.log")
    # deployment (2026-10-22): the address the clients are sent to after picking the server (0x46 list + 0x03 redirect).
    # 127.0.0.1 only works on the same PC; on the cloud host it is the public IP (deploy/sgserver.service)
    ap.add_argument("--public-ip", default=os.environ.get("SG_PUBLIC_IP", ""))
    ap.add_argument("--server-name", default=os.environ.get("SG_SERVER_NAME", ""))
    # OTA (2026-10-22): launcher downloads (0 = off) with a global bandwidth limit in KB/s
    ap.add_argument("--update-port", type=int, default=int(os.environ.get("SG_UPDATE_PORT", "0")))
    ap.add_argument("--update-rate", type=int, default=int(os.environ.get("SG_UPDATE_RATE", "1500")))
    # UDP relay for the players' SGRelay.exe (claude/UDP_RELAY.md), 0 = off
    ap.add_argument("--relay-port", type=int, default=int(os.environ.get("SG_RELAY_PORT", "0")))
    a = ap.parse_args()
    global PUBLIC_IP, PUBLIC_PORT, SERVERS
    if a.public_ip:
        PUBLIC_IP, PUBLIC_PORT = a.public_ip, a.port
        SERVERS = [(1, a.public_ip, a.server_name or "SGalaxy", "")]
    LOG = open(a.log, "a", encoding="utf-8")
    # WARM-UP (user 2026-10-24 19:51: units stuttered; log: "event loop stalled 1900 ms" at npc_pool -> npc_unit ->
    # stock_loadout, the first NPC unit pool after every restart, and 140 ms at client_code_hash on the first login).
    # Both are built ONCE here, before the port opens, instead of in the middle of the first battles.
    import time as _wt
    _w0 = _wt.monotonic()
    load_accounts()          # (11-02) opens game.db first: no database key / wrong key stops here, before the port opens
    for _wf in ("npc_pool", "allowed_client_hashes"):
        try:
            globals()[_wf]()
        except Exception as _we:
            log(f"   warm-up {_wf} failed: {_we!r}")
    log(f"   warm-up done in {(_wt.monotonic() - _w0) * 1000:.0f} ms (NPC unit pool, client hashes)")
    # (2026-11-02) encrypted connections only: no key = no game (the clients' ddraw.dll holds its public half)
    if net_key() is None:
        raise SystemExit("no connection key: put it in /opt/sgserver/.netkey (deploy.ps1 copies %USERPROFILE%\\.sgota\\net_key.json) "
                         "or set SG_NETKEY_FILE (tools/sgnet.py keygen makes one)")
    log(f"   connection key {NET_KEY_FILE} (public {sgnet.raw_pub(NET_KEY).hex()[:16]}...)")
    srv = await asyncio.start_server(handle, a.host, a.port)
    if a.update_port:
        global UPDATE_SRV
        def _launcher_lang(ip, ch):
            # the client reports its code page (0xF6) only once in the game; the launcher's manifest download
            # (manifest-cn / -tw / -en) tells the language of this IP before login -> New-commander screen in Chinese
            LAST_ACP_BY_IP[ip] = {"cn": 936, "tw": 950}.get(ch, 1252)
        UPDATE_SRV = OTA.UpdateServer(UPDATE_DIR, rate_kb=a.update_rate, log=log, on_manifest=_launcher_lang, board=board_http)
        await UPDATE_SRV.start(a.host, a.update_port)
        log(f"update downloads on {a.host}:{a.update_port} from {os.path.realpath(UPDATE_DIR)} (max {a.update_rate} KB/s)")
    errs = check_world()
    for e in errs:
        log(f"WORLD CONFIG ERROR: {e}")
    if errs:
        raise SystemExit("fix PLANETS / NATIONS / CAPITALS in sgserver.py (see errors above)")
    try:
        province_owner(0)          # loads WORLD
        NATION_ALLIES[:] = [tuple(x) for x in WORLD.get("allies", [])]
    except Exception:
        pass
    try:
        _own = sum(1 for k, v in world_state()["owners"].items() if int(v) and int(k) not in set(CAPITALS.values()))
        log(f"world loaded from {DB_FILE}: {_own} occupied province(s) (capitals not counted)")
    except Exception as e:
        log(f"   world load check error: {e!r}")
    log(f"world ok: planets={[(p[0], p[1], 'open' if p[3] else 'closed') for p in PLANETS]} capitals={CAPITALS}")
    log(f"listening on {a.host}:{a.port}")
    ensure_unique_unit_ids()
    try:
        drop_all_pending()
    except Exception as e:
        log(f"   pending account cleanup error: {e!r}")
    try:                                     # commanders that already played have seen the tutorial (15:30 change)
        _accs = load_accounts(); _n = 0
        for _k, _v in _accs.items():
            if isinstance(_v, dict) and "commander" in _v and _v.get("acp") and not _v.get("tutorial_seen"):
                _v["tutorial_seen"] = time.time(); _n += 1
            if isinstance(_v, dict) and "commander" in _v and not _v.get("mail"):
                mail_add(_v, "welcome"); _n += 1
        if _n:
            save_accounts(_accs)
    except Exception as e:
        log(f"   tutorial / mail migration error: {e!r}")
    spawn(backup_cycle())
    spawn(income_cycle())
    spawn(settlement_cycle())
    spawn(star_notice_cycle())
    spawn(election_cycle())
    spawn(raid_cycle())
    spawn(honor_tick())
    spawn(map_push_cycle())
    spawn(npc_cycle())
    spawn(ghost_cycle())
    spawn(snapshot_cycle())
    spawn(traffic_logger())
    spawn(npc_warm_units())
    spawn(accounts_flusher())
    spawn(log_flusher())
    spawn(lag_monitor())
    spawn(net_monitor())
    spawn(jitter_buffer_loop())
    spawn(ota_cycle())
    if a.relay_port:
        import udp_relay as UDPR
        await UDPR.start_relay_server(a.relay_port, a.port, log)
    _install_gc_probe()
    try:
        async with srv:
            await srv.serve_forever()
    finally:
        accounts_flush_now()
        npc_save(True)
        if LOG:
            LOG.flush()


if __name__ == "__main__":
    asyncio.run(main())
