# Battle control & multiplayer battle — reverse-engineering notes (SG.exe 1.8.5, 2026-10-20)
Confidence: [C] confirmed in decompile, [U] uncertain/inferred. "class-B" = battle-state dispatcher 004b5670,
"class-A" = global dispatcher 0054a1d0. All integers big-endian, s8 = u8-length string.

## Rule texts (ntt/BATTLE.TXT, FIELDWND.TXT) — the intended mechanics
- Permission policy (Ctrl+F7 / khiButtonAutoPermission): ksAutoPermission "Allow any allies to join battles you
  command", ksAutoReject "Prevent anyone…", ksManualSelect "Manually screen heroes who want to join".
- Requests shown to the Battlefield Commander: ksReinforcement "User %s is trying to enter this field",
  ksMercenaryHelp "Mercenary %s offers his services…", ksReinforcementInstant "…from far away, it will take some
  time for him to arrive", ksReinforcementForWatch "User %s is trying to watch this battle".
- Joiner side: ksPermitOK "The Battlefield Commander accepted your entrance. You will be viewing the battle in %d
  seconds", ksReject, ksRejectUserFull "The battle is full", ksRejectTimeEnd "cannot reinforce during the last few
  minutes", ksWait/ksRejectInstanceJoinByDustTime "dust is still settling … after %d seconds",
  ksRejectInstantJoinNoAlly "Your faction's defenders have been wiped out. You can only reinforce by walking there".
- khiBattleCtrlOK "The province is being contested. Press <ATTACK> or <ASSIST> to join the battle. Use 'Deploy
  troops'…"; ksNoUnitActive "must deploy your units before you can attack".
- Reinforcement squads: ksUnitArriveTime "Your units will enter the battle in %d seconds", ksReinforceTime "You can
  reinforce after %d seconds. Press <F7> to ready your next squad!", ksReinforceTimeElapsed "You must reinforce now
  or you will retreat in %d seconds", ksWaitingUserNo "%d users are waiting to reinforce".
- Retreat: ksRetreat "Unit %s is trying to escape… If you retreat a unit through this gate, every other unit has to
  retreat through this gate" (commander confirms), ksRetreatToEnemyField "destination field is owned by an enemy
  faction. Retreat through another portal".
- Mercenary = nation id 5 [C]: client special-cases nation 5 everywhere (0x1e dialog, star gate range, FHQ).
- ksOutOfSync0/1: 3 out-of-sync errors -> disconnect "and lose wealth and experience as if defeated".

## (A) Battle control
### Hotkeys (FUN_004b3680, VK codes, Ctrl state at DAT_006ba7c8+0x25b1) [C]
| key | effect |
|---|---|
| Ctrl+F11 (0x7a) | FORCED RETREAT -> client **0x54 []** (004a4f30). Without Ctrl: 004a5270 (local) |
| Ctrl+F7 (0x76) | toggles local flag +0x218f4 (permission window 005a7890). Without Ctrl in battle: 005b4cb0 -> client **0x19 [00]** (open reinforcement / F7 squad) |
| Ctrl+F5 (0x74) | TP toggle (units transportable by allies) -> client **0x47 [u8 opt][u8 TP]** (00547a60) |
| Ctrl+F6 (0x75) | TK toggle (units targetable by allies) – local only |
Permission mode used by 0x24 handler = byte at window +0x218f0: 0 auto-accept, 1 auto-reject, 2 manual dialog. [U: which UI sets 0/1/2]

### Server class-B 0x1e "BATTLE CONTROL" dialog (004af1e0, 'fldbctrl') [C layout]
Sent when the hero arrives at / looks at a contested province. Layout:
`u32 map, u8 a, u8 b, u32 DEFENDER nation(owner), s8 title, u8 n, n x {s8 hero name (<=0x40), u32 nation, u32 X},
 u8 TIMEOUT (seconds; deadline = n*100 lock-step frames), u8 c, [only if dialog still open: u8 m, m x {u32 uid,
 u8, u8} -> placeholder units FUN_004d3050]`.
Participants are split into "enemy of defender" vs "allied to defender" lists by alliance group. Results:
- player nation == 5 (mercenary): button 0x10 -> client **0x20 [04][u32 map][u32 defender nation]**; 0x11 ->
  0x20 [04][map][nation of first participant]; 0x12 -> 0x1b [01]..., 0x13 -> 0x1b [02]...
- player's nation already a participant: client **0x20 [01][u32 map]** (join) [event 0x20].
- not a participant: button 0x12 -> client **0x1b [01][u32 map][u16 x][u16 y]** (ATTACK), 0x13 ->
  **0x1b [02][u32 map][u16 x][u16 y]** (ASSIST) followed by client **0x48 [u16 0]**; 0x14 -> 0x19 [00].
### Battle end / objectives [C]
- Client **0x5a [u32 objective id][u8 new owner nation(low byte)][u32 map][u8 1]** (004a41b0 from 0048d640) when
  a POC changes owner -> server can use it as the authoritative capture report and rebroadcast 0x49.
- Client **0x1f [u32 map][5..14 random bytes]** (004a4250) when all objectives are held (0048d640) or, in mode 2,
  when the idle timer expires; also from FieldWnd command 0x1a. Treat as "battle objectives complete".
- Battle timer: 0x17 u32 start/end (centiseconds). [U] at end time the server decides: attackers holding every POC
  -> attacker victory, else defender victory; send 0x25 to everyone and move them.
- FieldWnd command ids (004a9130): 0x16/0x17 -> client **0x35 [02|03][u32 map owner]** [U meaning: request
  assist/attack], 0x18 -> leave map (0x2e), 0x1c -> 0x38 found capital, 0x26 -> 0x54 forced retreat.

## (B) Multiplayer
### Join / permission handshake [C codes]
Client **0x20 [u8 type][...]**:
| type | payload | meaning |
|---|---|---|
| 1 | u32 map | join battle (hero walks in / own nation participates) |
| 4 | u32 map, u32 side nation | mercenary offers service to side |
| 7 | u32 map | quick-menu join (00531a20) [U] |
| 8 | u32 map | INSTANT join from strategic map (remote, arrives later) |
| 13 | u32 map | WATCH battle from strategic map |
| type+1 = 2,5,9,14 | s8 requester | commander REJECTS |
| type+2 = 3,6,10,15 | s8 requester | commander ACCEPTS |
Server class-B **0x24 [u8 type 1|4|8|13][s8 name 'fldjb1'][s8 'fldjb2']** -> asks the battle COMMANDER (004a2090):
policy auto -> client immediately answers 0x20 [type+2][name]; reject -> 0x20 [type+1][name]; manual -> dialog
(00402fc0) with accept/reject buttons. [U] reply to the joiner: probably 0x5b sub 1 [s8 name][u8 ok] (0 -> message
box) or a 0x24 to the joiner; JoinBattleWaitDlg shows khiJoinBattleOK/Cancel while waiting.
### Reinforcement window (F7) [C layout, U semantics]
Server class-B **0x5b [u8 sub]** (004aaa80 'fldrie1/2'):
- sub 0 [s8 name]: client auto-replies **0x5c [01][s8 name][01]** and lists the hero (004aa6f0).
- sub 1 [s8 name][u8 ok]: ok=0 -> message box; else list update.
- sub 2 [u8 k][u16 t]: k0 "You can reinforce after t s" (00524400), k1 "You must reinforce now or retreat in t s"
  (005241f0); k2 then 5 x u32 (window values).
- sub 3 [u8 1]: enable/flag (005241d0); sub 4 [u8 ok]: result message.
Client 0x5c: [02][u8][u16][u32] deploy squad (00524450), [03][u8] (00524520), [00][s8 name] (005e0c60).
Server class-B **0x50 "Delayed Put" [u32 lock-step time][same body as 0x18 PUT_UNIT]** (004ad4e0) [C]: puts a unit
at a future game time on every client -> use for reinforcements / late joiners so all clients add it at the same tick.
### Leaving
- Server class-B **0xc5 [s8 hero name]** "%s has left this battle." and removes him from the participant list [C].
- Server class-B **0x19 [u32 uid][u32 0]** removes a unit [C]. Exit portal = client 0x2f (already handled), forced
  retreat = client 0x54.
### Late-join world snapshot [C layout, U exact relay]
- Server class-A **0x0E [06][u32 T]** to an existing participant -> it sets its clock base to T and sends client
  **0x1d [u16 zlen][zlib(u32 T, u16 nUnits, unit records…, u8 nObjectives {u32 id,u16,u32,u8}, …)]** (004a9890).
- Server class-B **0x22 [u16 zlen][zlib(u16 nUnits, records 0x38+4N bytes: u32 uid, u16 x, u16 y, u8, u16, u16,
  u16, u8 x4, u32, u32, u16, u16, 6 x u32, u8 m, m x u32 …), u8 nObj {u32 id, u16, u32, u8}, then three u16-counted
  lists {u16, u16, u32, u32, u8, u32/u8}]** (004b0a20) rebuilds every unit/objective on the joiner. [U] whether the
  leading u32 T of 0x1d must be stripped before forwarding as 0x22 (0x22 parser starts with u16 n).
- Then 0x0E [04][01][u32 T] starts the joiner's clock at T.
### Time sync (lock-step) [C]
- Client class-A **0x0E [01][u32 client ms]** (00547130); server must answer **0x0E [01][u32 same ms][u32 game time
  (1/100 s)]**; client sets base +0x1c54 = now/10 - game time (keeps min RTT). Lock-step frame = 1/100 s;
  objectives & unit logic run once per frame (004ad690). Clients only advance to the last server time received
  (0x80 lumps; class-B 0x5c [u32 time][...] also sets the limit, 004a1da0).
- One battle = ONE clock: all participants must receive the same 0x80 lumps (same time stamps). Every client order
  (client 0x80 lumps 0x16/0x17/0x1e/0x29/0x30/0x21/0x18) must be relayed to ALL participants with
  time = battle_now + delay (>= worst RTT), including back to the sender.
### Other players on a map [C from existing handlers]
- Show another hero: 0x18 PUT_UNIT (kind 0) + 0x20 S_HERO_PUT with that hero's unique uid, nation, name; units the
  same with 0x18. Moves: relay their 0x16 as server lump 0x1a to everyone on the map; remove with 0x19.
- IMPORTANT: uids must be globally unique per battle/map. The server currently gives every commander uid 1 and
  per-account unit ids that can collide between accounts -> must allocate global ids (e.g. hero = 0x40000000 +
  account no., units remapped per battle).
- Friend/foe = alliance group of the nation in PUT (class-A 0x05 relations). Defender = province owner (0x17 owner).
### Misc client packets (ignore safely)
- 0x60 [8 x u8] anti-cheat hash report ("Bad ACD/SHA", 004a2910); 0x7c [u32][junk] keep-alive; 0x47 options;
  0x12 [01] (F6 related, 0049e6e0) [U].

## Minimal viable flow for 2 players in one battle
1. A attacks neutral province P (current server flow). Create Battle{map P, clock t0, participants, units, pocs,
   commander = A}. All timing from Battle clock.
2. B (same nation) opens strategic map, sees battle flag; walks/clicks -> client 0x20 [01|08][P] (or 0x1b [01][P][x][y]
   when arriving by portal; server may first send 0x1e dialog).
3. Server -> A: 0x24 [type][B name][""]. A answers 0x20 [type+2][B] (auto policy) -> accepted.
4. Server -> A: 0x0E [06][T]; A -> 0x1d snapshot. Server -> B: 0x17 (P, battle, same start/end, POCs), 0x22 snapshot,
   0x0E [04][01][T]. (Fallback without snapshot: send B 0x18 for every live unit/alien with current positions.)
5. Server -> A and B: 0x50 Delayed Put [T+300] for B's hero + units (unique uids), and 0x18/0x20 of A's units to B.
6. Relay every lump from A or B to both with Battle clock time; aliens' AI lumps to both; per-session XP/HP as now.
7. POCs: accept 0x5a from any participant (owner change) -> broadcast 0x49; all held -> victory for all
   participants (0x25 each, capture for the nation).
8. Reinforce: F7 -> 0x19 [00]; server 0x5b sub 2 timers; squad deploy 0x5c [02]… -> 0x50 Delayed Put for new units.
9. Leave: 0x2f per unit / commander, or 0x54 forced retreat -> 0x19 [uid][0] for each of his units to the others,
   0xc5 [name] to the others, move him out.

## Alien control / death authority (2026-10-20, ALIEN_CLIENT_CONTROL)
- Every client simulates all units (lock-step, rewindable history buffers, 004ca320). HP bars, projectiles, splash
  and movement (A* + collisions, 004e42b0) come from that simulation; the server cannot reproduce it exactly.
- Unit death is reported by its CONTROLLER: unit think 004cc220 sends lump 0x1e [uid] when its HP reaches 0.
  Controller = PUT owner name equals the local commander (004ac800 -> unit +0x69).
- Server-owned aliens ("Alien" owner) therefore never died in the client (stuck at 0 HP) unless the server sent 0x23.
- Now aliens are PUT with the battle creator as owner: his client reports 0x1e at the exact simulated tick, server
  relays 0x1e -> 0x23 to everyone, credits the kill to the last unit that hit it (server log model).
- Player commands for alien uids (0x16/0x17/0x30) are dropped by the relay; alien AI attacks (0x29) pass.
- Creator leaves: class-B 0xcc 'fldcuo' (004afd80) [s8 owner][u8 n][u32 uid]* hands control to the new commander.

## Simulated multi-client verification (2026-10-20, tools/mptest/test1-7)
- Fake clients speak the real protocol (login, 0x2e map change, 0x1b/0x20 join, 0x80 lumps, 0x5a POC, 0x2f retreat).
- Rules verified: join permission (own side asks the commander, enemy side enters directly); shared clock; lumps relayed
  at the same tick; deaths broadcast to all and XP credited to the killer; no victory without POC capture;
  spectators get no result window and return to their capital; F7 reinforcement (0x50 future time) reaches everyone.
- Owned province (original rule): no aliens, defenders notified (class-B 0x31), POC owner = defender, attackers win by
  capturing, defenders win by time-up or when every attacker has left.
- Mercenary (client 0xd6 on, 0x20 [04][map][side]): commander is asked, merc fights for that side (PUT nation, POC
  capture, province goes to the side served), +20% bonus, contract ends with the battle.
- Bugs found and fixed: shared hero uid between accounts (units of one account moved by another);
  new unit ids only unique per account; commander leaving could pass command to a SPECTATOR (now a fighter of the
  same side); attack loops of a disconnected session are cancelled.
