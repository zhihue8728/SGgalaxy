# Honor / Medals / Reincarnation — client research (SG.exe 1.8.5, 2026-10-20)

## 1. HONOR
Client facts:
- F4 (0x27 sub 0) u32 HONOR, shown /100 with a bar (f4-st-hn.xpf). Help: khiUserInfoHonor
  "Honor. Your units will earn extra health for every 100 honor."  -> the effect is server-side (unit max HP).
- Faction change (StarCenter 0x31 nation row u8 PENALTY): 0 -> plain join text; !=0 -> ksSCJoinNationPenalty
  "WARNING YOU WILL LOSE URANIUM AND HONOR IF YOU JOIN THIS FACTION". Other texts: kssCPenaltyText
  "...LOSE ALL YOUR UNITS AND HONOR...", ksSCPenaltyAll "LOSE ALL UNITS", ksSCPenaltyZero "No Penalty".
  (UNCERTAIN which PENALTY value selects "all units"; client only tests 0 / non-0 for the confirm text.)
- khiStarCenterWeakestNation: joining the weakest faction of a planet gives "50% of bonus for each of your units".
- No client check of honor for voting/FHQ/cabinet was found; the name decorations are driven by the 0x20 bytes
  (below), not by honor. "Word of Honor" texts belong to the Superior/Subordinate (pyramid) system, not honor points.
- Design doc text in data: "Prestige will provide a system of ranking between players (USCF-like)";
  "Medals, honors, etc. Currently not implemented." (old design notes, hlp) -> original rules mostly server-defined.
Proposed rules:
- Gain: victory per battle kind (existing HONOR_GAIN), capture +100, kills small (+1 x enemy lvl / 10).
- Loss: defeat -20, faction change with PENALTY!=0: lose all honor (and uranium, e.g. 50 %); retreat 0.
- Effect: unit max HP x (1 + 1 % per 100 honor) (cap e.g. +50 %), applied in PUT_UNIT / roster.
- Decorations: 0x20 mark byte 1 = president (ui-pres1/2.xpf, animated), 2 = cabinet (ui-cabi.xpf) — only for
  political offices; not honor based.

## 2. MEDALS
- 0x27 sub 0: u8 n {u32 MEDAL ID, s8 TEXT}. Stored in a vector at window +0x10a58 (FUN_005e3320), drawn in a grid
  of 3 per row, 0x30 px apart, scroll list "ScrollMedalList" (scrolls when > 9). FUN_005e21f0 draws each:
    file  = "dcr-%03d.xpf" % (id // 1000)   (fallback dcr-000.xpf)
    group = (id % 1000) >> 5, frame = (id % 1000) & 31  (FUN_005ef180(view, x, y, group, frame))
  Text = the medal's name/tooltip (UNCERTAIN where shown: tooltip).
- Art (NTF2.dat): dcr-000 .. dcr-029.xpf (+ dcr-fame.xpf), each 44x16 ribbon. dcr-000..022 are single-image files
  (5852 B each), dcr-023 (~2 frames), 024 (~5), 025 (~3-4), 026 (~6), 027/028 (~4), 029 (~2) (frame counts
  estimated from size; UNCERTAIN). CORRECTION (2026-10-20, NTF2.dat decoded + in-game test): frame 0 of every dcr file is EMPTY (2 bytes), so ids N*1000 draw nothing. Valid ids N*1000+f, f>=1. dcr-000..020 have 4 frames (1-2 unique ribbons, 3-4 shared placeholders), 021/022: 4, 023: 8, 024: 20, 025: 14, 026: 24, 027: 16, 028: 16, 029: 8 -> 198 frames, ~156 unique designs. Frame format: u16 0 + 16 rows x {u8 skip, u8 count, count x RGB565 LE}. Contact sheet: analysis/medals/medal_sheet.png
- Help: khiUserInfoAccomplishments "Medals and Accomplishments earned during this hero's adventures. Some medals
  provide special bonuses." No medal names/conditions exist in the client -> define them server-side.
Proposed medal table (id -> name, condition):
  1000 First Blood (first kill), 2000 Veteran (100 kills), 3000 Conqueror (first province captured),
  4000 Warlord (10 provinces captured), 5000 Survivor (win without losing a unit), 6000 Explorer (reach Advanced),
  7000 Elite (reach Elite), 8000 Reborn (first reincarnation), 9000 Honor Guard (1000 honor),
  10000 Cave Raider (10 cave wins), 11000 POC Master (50 POCs captured), 12000 Centurion (division level 100).

## 3. REINCARNATION
Rules (ntf2/rtn-desc.txt, Korean, summarized): after reaching the MAX level you restart from level 1 and on later
level ups can go one level higher (max level +1 per reincarnation); a gift alien unit that cannot be bought in
shops; base unit capacity +2 per reincarnation; a special mark next to the name; ranked above non-reincarnated
level-100 heroes (=> max level 100); you may pick a new hero appearance.
Client flow:
- StarCenter 0x31 sub 0 nation row u8 MODE (+0x50): 1 = reincarnate row -> button opens the rtn dialog
  (FUN_00586940: rtn-frm.xpf, rtn-desc.txt; FUN_005862f0: rtn-arr/rtn-buts). Hero picture starts at commander
  +0x450 (look) and cycles every existing h%03dmo.xpf (1..N).
- Checks before sending (005ae640): owned units (FUN_004edae0 + FUN_004eda90) <= reinc*2 + 25 else
  ksSCReturnMaxUnit (%d = reinc*2+25); reinc count (commander +0x47d) < 11 else ksSCReturnCountMax (10).
- Send: 0x37 [0b][u32 nation][u8 penalty (row +0x10)][u8 hero picture].
- Display: 0x15 byte [0x47d] = reincarnation count (F4 also has u8 REINCARNATION in 0x27; khiUserInfoReturnCount).
  The rtn dialog previews the name with ui-rtl/ui-rtr.xpf frame (count+1) (FUN_00585e70) -> the "special mark"
  is the name-side frame. In the field (FUN_004ce920) the unit name is flanked by ui-rtl1/ui-rtr1.xpf (31 frames,
  fallback ui-rtl/ui-rtr 16 frames) using frame = unit +0x36c = the 0x20 S_HERO_PUT "rank" byte (capped 30, 0 =
  none). => send 0x20 rank byte = reincarnation count to show the mark (previous notes called it "insignia").
Implementation spec:
- Offer MODE 1 rows when commander max division level >= 100 (REINC_LEVEL, placeholder; any planet tier or Elite
  only - design choice) and reinc < 10; list the Novice planet nations (rebirth starts on the novice planet).
- On 0x37 [0b]: validate (level, count < 10, units <= 25 + 2*count); count += 1; branches -> level 1, xp 0;
  units -> level 1 (keep or not: design; client text implies units kept up to the cap); look = hero picture;
  nation = chosen; tier = 1; MAX_UNITS (0x15 +0x2a) = base + 2*count; branch level cap = 100 + count;
  gift one alien unit (ALIEN_TYPES art, not sold); honor kept; send 0x15 (with [0x47d]), 0x27, roster 0x16,
  enter the new capital; 0x20 rank byte = count.
