# New commander progression & tutorial (reversed from SG.exe 1.8.5)

## Novice -> Advanced -> Elite
- StarCenter portal (Portals.por type 10, "Faction Pledge Center - Allows you to move to a more advanced planet")
  is the real route. Star gate (type 11) = transport/visit; Observatory (type 12) = 0x39 [00][00] view only.
- Client 0x37 [00] -> server 0x31 sub0 (FUN_005afa50): u8 nPlanets {planet rec without detail},
  u8 nNations {u32 nation, u16, u8, u16 WAIT(!=0 -> ksSCTimeNoReach), u8 PENALTY(0 none / else uranium+honor loss),
  s8, u8, s16 description, u8 MODE(0 join,1 reincarnate)}; 0 nations -> ksSCNoFaction. sub1 = s16 message box.
- Client 0x37 [05][u32 nation][u8 penalty] = pledge/join; [0a][u32 nation] = visit;
  [0b][u32 nation][u8 penalty][u8 heroPic] = reincarnate (client: units <= 25+2*reinc, reinc < 11).
- Arrival: server 0x17 into a province map whose planet (id/100000)%1000 differs -> client shows ksPlanetMove.
- Commander 0x15: [0x480] u32 founding planet (capital must be on it), [0x47d] reincarnation count,
  [0x474] u16 used by tutorial gating.
- Star gate novice text ksSGNewbieDistance ("too far ... but because it's a novice planet, travel is possible.
  You will not be able to return") exists but is not used by client code -> probably server 0x38 sub1 message.
- No level/tier check in the client: the level-20 / cap-35 rules are server-side.

## Tutorial ("mission") after character creation
- Client-side CInteractiveHelpMan state machine (ctor FUN_0051f590, ~368 transitions), texts kStep_01a..35a in
  ntt/helpmsg.txt: capital intro -> accept mission -> CTF practice -> Factory purchase -> F7 deploy -> Zoo ->
  Spoils of War -> repair -> Subterranean Cavern -> strategic map -> reinforce a real battle.
- Starts when hero is placed on a town map (server 0x20, event 0x1d) and the "interactive help" option is on.
  Events posted by FUN_0051d1f0 from ~60 sites (windows, portals, server '$' chat commands).
- Sends NO packets and gives no rewards; server 0x7d [u32 lo][u32 hi] = bitmask of tutorial items to skip/mark done.
- Any mission rewards must be server-side on the real events.
