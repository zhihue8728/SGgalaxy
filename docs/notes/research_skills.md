# Unit skills (SG.exe 1.8.5) — research notes 2026-10-20

## 1. Ability bits -> commands (CONFIRMED FUN_004d49a0)
PUT_UNIT 0x18 +0x22 u64 abilities = (hi u32 -> unit +0x15c) << 32 | (lo u32 -> +0x158). Bit index n below = bit of
that u64 (n<32 -> +0x158 bit n, n>=32 -> +0x15c bit n-32).  Command id == index into the CMDDESC.TXT ks* table
(ksMove=0 ... ksFrenzy=54; CONFIRMED by the install/ambush/shield/snipe/patriot/air-ambush pairs and the registration
order in the command dispatcher FUN_0042b6c0).  Commands 0 Move, 1 Stop always present.

| bit | command id(s) | name (CMDDESC) | item "Special" that should grant it |
|---|---|---|---|
| 1 | 2 AttackObj | Attack (needs damage>0, hidden if bits 21/37/53/54/56 or 46 set) | (weapon) |
| 3 | 30 | Levitate (toggle) | Anti-Grav Harness |
| 4 | 29 | Self Destruct | Self Destruct |
| 5 | 28 | Disguise (toggle) | Disguise |
| 6 | 27 | EMP Grenade (target) | EMP Grenade |
| 7 | 23 | Psycho / Mind Warp (target bio) | Mind Warp |
| 8 | 22 | Grenade (target) | Grenade |
| 9 | 26 | AfterBurner (toggle) | After Burner |
| 10 | 25 | Neutron Shield / IronCurtain (toggle) | Neutron Shield |
| 11 | 24 | Stealth / Sensor Evasion (toggle) | Sensor Evasion |
| 12 | 21 | EMP Attack (target) | EMP Attack |
| 13 | 20 | EMP Mine | Charge EMP Mine |
| 14 | 19 | Cloak (toggle) | Cloak |
| 15 | 18 | Refuel (target) | Refuel |
| 16 | 17 | Mine Detect | Mine Detector |
| 17 | 16 | Radar Jam (only when installed: shown under cmd 4) | Radar Jammer |
| 20 | 13 | Repair (target mech) | (Repair Assembly / Repair Machine: no Special text; name match) |
| 21 | 6/7 | Ambush / Release (ground bombard, own install) | Bombard |
| 22 | 15 | Mine | Charge Mine |
| 25 | 12 | Heal (target bio) | Heal |
| 26 | 14 | Teleport (target unit -> location) | Teleport Unit |
| 28 | 10/11 | Transport load / unload | Transport Unit |
| 29 | 8 | Unit Identity (installed) | Identify |
| 30 | 9 | Radar (installed) | Radar |
| 31 | 4/5 | Install / Uninstall | (needed by 8/9/16/38/63 and by Teleport while installed) |
| 32 | 31 | Short Circuit / LockDown (target mech) | Short Circuit |
| 33 | 32 | IRBM (location; 5 min arm, ksICBMImp) | IRBM |
| 34 | 33 | Camouflage (toggle) | Camouflage |
| 36 | 34 | Air Mine | (none found) |
| 37 | 35/36 | Air Ambush / Release | Air Bombard |
| 38 | 37 | Booster (toggle) | Speed Boost |
| 39 | 38 | Tunnel / Link Gate (installed; target gate unit) | Link Gate |
| 40 | 39 | Carpet Bombing | Carpet Bomb |
| 41 | 40 | Defensive Matrix (target ally) | (none found) |
| 42 | 41 | Flare | Flare |
| 43 | 42/43 | Shield / Release | Shield |
| 44 | 44/45 | Dynamite / Blow | Altcharge (TBC) |
| 45 | 46 | Detector | Detect |
| 46 | 47/48 | Snipe / Release (hides Attack) | (sniper weapons, no Special) |
| 47 | 49 | Chemical Mine | Chemical Mine |
| 48 | 50 | Earthquake | Earthquake (items 'Frenzy'/'Earthquake'/'Rumble') |
| 49 | 51/52 | Patriot / Release (IRBM defence) | IRBM Defense |
| 50 | 53 | Fusion Storm / Yamato (target air) | Fusion Storm |
| 52 | 54 | Frenzy (location) | (TBC) |
| 53 | 55/56 + 59 | unnamed (install-type pair) | ? |
| 54 | 57/58 | unnamed pair | ? |
| 56 | 60/61 | unnamed pair | ? |
| 57 | 63 (installed) | unnamed | ? |
| 58 | 70, 59 | 69 | unnamed | ? |
| 60 | 72 | unnamed toggle (action 63) | ? |
| 61 | 73 (0x49, no handler registered) | ? | ? |
Bits 0, 2, 18, 19, 23, 24, 27, 35, 51, 55 add no command (passive flags; probably Allow Phase / Warp / biological /
mechanical etc. — UNKNOWN).  Item specials with no command: Allow Phase, Warp, Anti-Grav (=Levitate).

## 2. Lump formats (CONFIRMED client senders 004dd860..004e1a90 and server-lump handler 004dcec0)
- Client lump 0x30 = [u32 uid][u8 ACTION][args];  server lump 0x30 (004a5da0 -> 004dcec0, switch ACTION-1) reads the
  SAME [u8 ACTION][args] after the uid -> the server just RELAYS the body unchanged (current RELAY 0x30->0x30 is right),
  like 0x16->0x1a, with the usual frame delay, to every client in the battle (sender included).
- Client lump 0x17 = [u32 uid][u8][u8] (004de840, mode/order changes; 18 callers incl. targeted skill execution
  004e24a0..004e3730) -> relay as server 0x1b (already done).
- Args per ACTION (pt = u16 x, u16 y pixels):
  1 u8 Install on/off | 3 u32 | 4 - TransportOut | 5 u32 unit + pt Teleport | 6 u32 | 8 - Mine | 9 u8 Ambush |
  10 u32 TransportIn | 11 pt MineDetect | 12 u32 (Heal?) | 13 - | 14 u8 | 15 u8 toggle | 16 - EMPMine | 17 u32 |
  18 u8 | 19 u8 | 20 u8 AfterBurner | 21 u32 | 22 u32 | 23 u32 | 24 u8 | 25 - SelfDestruct | 26 - (misc) |
  27 u8 Levitate | 28 u32 | 29 pt IRBM | 30 pt | 31 pt | 32 u8 Camouflage | 33 - AirMine | 34 u8 AirAmbush |
  35 u8 Booster | 36 u32 Tunnel | 37 u8 toggle | 38 u32 | 39 pt | 40 u8 Shield | 41 - Dynamite | 42 pt Blow |
  43 u8 | 44 u8 Snipe | 45 - ChemMine | 46 - Earthquake | 47 u8+pt Patriot | 48 u32 FusionStorm | 49 u32 |
  50 pt Frenzy | 51 u8 (cmd55/56) | 52 u8 (cmd57/58) | 53 u8 | 54 u8 | 55 u8 (cmd60/61) | 56 u32 | 57 - |
  58 u32 | 59 u32 | 60 u32 | 61 pt | 62 u8 (cmd71) | 63 u8 (cmd72).
  u32 target actions (3,6,10,12,17,21,22,23,28,38,56,59,60) are sent when the unit reaches the clicked target
  (pending orders 0x68..0x79 in 004cc220); exact action<->command for 3/6/12/17/21/22/23/28/38/56/59/60 is TBC
  (likely Heal/Repair/Refuel/EMP/Grenade/Psycho/EMPGrenade/LockDown/DefMatrix/Identity).
- Toggles (u8 1/0) are also switched OFF by the client itself when energy runs out (004cfea0 sends actions
  15,20,27,32,35,37,62 with 0).

## 3. Server-side work needed
1. Give units their bits: compute from equipped items' "Special" (server/items.json stats) with the table above,
   plus bit 31 Install for units that have an installed-only skill.  Keep bit 1 for armed units.
2. Relay 0x30 and 0x17 unchanged (already).  Energy is simulated by the client (PUT energy/upkeep; the per-use
   cost is probably the item DB type-7 u16 (+0x5c), u8 (+0x58) unknown - TBC) -> put item 'Energy Use' there.
3. Server-owned units (aliens/targets) only die when the server says so (0x23): skill damage on them must be
   simulated server-side from the relayed actions (Grenade/EMP/IRBM/Earthquake/SelfDestruct/mines/Fusion Storm/
   Carpet Bomb/Dynamite: area damage = item 'Effectiveness' around the target point/unit).
4. POC capture: units with Neutron Shield (action 37/15? TBC) or Camouflage (action 32 on) cannot capture.
5. Teleport/Transport/Tunnel move units: the server's unit_pos follows the client 0x18 position reports.

## Uncertain
- names of commands 55-73; exact action ids of the target skills; meaning of passive bits; item type-7 u8.
- Which chassis have innate skills (hlp texts only hint: g001 Daeva grenades, g017 Sapper mines, g021 Liche IRBM
  defence, g023 Gear Doc repair, g035 Orbus teleport, g045 Leviathan shields, g055 Volte refuel, g056 Triage heal+repair,
  g059 Wight overload) - in the original these came from their default equipment.

## 4. Skill energy / power (CONFIRMED 2026-10-20, client 004ac800 -> 004c4fa0, 004cfea0, 4e0acb/4e629b)
PUT_UNIT +0x2a: u8 n + n x {u8 ABILITY BIT, u16 A, u16 B} -> unit +0x160[bit] = A, +0x258[bit] = B.
- A = energy: per use for one-shot skills (Grenade: 'energy >= A' check, then 4cb4b0 spends A); per second while a
  toggle is active (004cfea0 adds A for Cloak/Camouflage/Afterburner/... to the s8 upkeep at PUT +8).
- B = power (damage / heal amount, passed to the effect 4cb3d0). Bit 20 Repair / 25 Heal: B -> unit +0x374 (heal
  rate); bit 18 -> 004c4b90; bit 55 -> replaces the sight value.
- No entries (as before) = every skill free and with 0 power (explains "no energy used", and Heal/Repair healing 0).
Server: A = item 'Energy Use', B = item 'Effectiveness'; chassis/GM skills use the lowest-tech item with that Special.
PUT +8 s8 upkeep: negative = regeneration (capped at max energy). ORIGINAL data: = sum of items' 'Energy Drain' (0 for almost all items, -4/-5 Fallout reactors) -> only reactors regenerate in battle. 'Energy Recharge' (storage items) = refill outside battle (battle entry starts full).
Server skill damage on aliens = unit skill power (item Effectiveness) for confirmed actions 29 IRBM, 25 Self Destruct, 46 Earthquake, 48 Fusion Storm, 42 Blow, 50 Frenzy; radii and other actions still PLACEHOLDER.
In-game: Cloak toggle CONFIRMED working (units turn translucent); Heal on mechs refused by the client (bio only).

## 5. ACTION -> ability bit and original effects (CONFIRMED 2026-10-20)
Senders 004dd860..004e1a90 each check energy at +0x160[bit] and push their ACTION:
3->28 Transport-in, 6->25 Heal, 8->22 Mine, 10->20 Repair, 12->15 Refuel, 13->30 Radar, 14->17 Radar Jam,
16->13 EMP Mine, 17->12 EMP Attack, 21->8 Grenade, 22->7 Mind Warp, 23->6 EMP Grenade, 25->4 Self Destruct,
28->32 Short Circuit, 29->33 IRBM, 33->36 Air Mine, 38->41 Defensive Matrix, 41->44 Dynamite, 45->47 Chem Mine,
46->48 Earthquake, 48->50 Fusion Storm, 59->59, 60->58.  (Toggles 9,15,18..20,24,27,32,34..37,43,62,63 check no cost.)
Received actions -> event types (004dcec0 case n = action n+1 -> 005c2xxx queue event); unit order executor
switch 004e9060.  Effect rules (skill damage ignores armor; 004cb3d0 subtracts from HP, skipped for shielded units):
- Grenade 4e6190: target -B, then EVERY unit within 128 px of the target (target included, so target -1.5B) -B/2; 2 s cooldown. (CONFIRMED in-game 2026-10-20: server without the target splash left aliens alive at 0 HP.)
- Earthquake 4e6cf0: all units except caster within caster sight (+0x114) -B (not levitating units); eff_qk.xpf.
- Self Destruct 4d8c10: units within 280 px -B, caster dies.
- IRBM impact 4d78c0: units within 210 px of the point -B (impact delay not measured).
- Fusion Storm 4cd9a0: -B % of target max HP (x0.3 in some state).
- EMP Grenade 4e6400: energy -B on target, -B/2 within 64 px; EMP Attack 4e6b60: energy -B.
- Mind Warp 4e6800 -> 4cd600(B); Short Circuit 4e69b0 -> 4cd8d0(B) (durations).
Server implements Grenade, Earthquake, Self Destruct, IRBM, Fusion Storm on aliens; mines not simulated server-side.

## 6. Skill timing (CONFIRMED 2026-10-20) - server mirrors the client in game ticks
The client sends 0x30 at every click; nothing runs locally until the relayed lump's tick (echo = game_time + 10).
Grenade/EMP Grenade/Mind Warp/Short Circuit/EMP Attack share one per-unit timer (unit +0xb876, 004cd3f0(now)):
fire when last_use + 200 < now and energy >= cost; a newer order (click/move/attack/stop) replaces a pending one.
Server: s.lump_exec_t = tick of the batch; _run_skill waits until fire_tick - 10, re-checks the order is still the
latest, spends energy, sets the shared timer, applies damage and stamps 0x23 deaths with the fire tick.
Test (offline): 6 clicks 50 ticks apart -> fires at 1010, 1211, 1412; death lump stamp 1211 sent at 1201.
