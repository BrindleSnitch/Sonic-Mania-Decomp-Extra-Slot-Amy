# Device setup & file layout

Captured 2026-08-17, matching the working build.

---

## Game folder

**`/sdcard/Download/SonicMania/SonicMania/`**

The app lets you pick this folder at launch. It is **not** the engine default
(`/sdcard/RSDK/v5/`) — an empty stray folder exists there and is harmless.

```
Data.rsdk              208,400,940   ← CORRECT (crc32 852ae394)
Data.rsdk.mar2019      208,368,695   ← old, kept for reference, DO NOT USE
Settings.ini                 1,159   ← from JonasYT's port
Achievements.bin / AddendumData.bin / SaveDataAddendum.bin   (regenerated)
mods/
_port_saves/    ← parked saves from the port build (see below)
_stale/         ← Vita Game.suprx + old AddendumOptions.bin (dead weight)
_unused/        ← ReplayDB.bin, HyperManiaSaveData.bin (pre-port leftovers)
log.txt         ← the engine log; primary diagnostic tool
```

---

## `modconfig.ini` (working configuration)

```ini
[Mods]
AddendumAndroid=y
Sonic Mania Addendum=y
Shaders=y
UltrawideMania=n
ManiaTouchControls=n
Mania Android=n
Mobile Friendly UI (Clean)=y
```

Verified 2026-08-18: **no asset conflicts between the enabled mods** — no two of them
ship the same file path.

**Order matters — the first mod listed wins asset conflicts.**

| Mod | State | Notes |
|---|---|---|
| `AddendumAndroid` | **on** | Flag mod, **no assets**. Addendum checks `Mod.LoadModInfo("AddendumAndroid", …)` to enable `HUD_DrawMobileHUD()` / `HUD_DrawTouchControls()`. **This is what turns touch controls on.** Folder name must match exactly. |
| `Sonic Mania Addendum` | **on** | 693 files from repo master. `mod.ini` **must not** contain `DisableGameLogic` or `LogicFile` (see below). |
| `Shaders` | on | **Contents replaced 2026-08-17** with the workflow's bundled `GLShaders` (= upstream RSDKv5 master `RSDKv5/Shaders/OGL`). JonasYT's originals were stale and failed to compile — see `FINDINGS.md` §7. Originals in `save-backup-2026-08-17/shaders-original-20260817/`. **Re-copy from `artifacts/mods/GLShaders` after every build** so shaders stay paired with the engine. |
| `UltrawideMania` | off | Widens canvas; shifts touch zones |
| `ManiaTouchControls` | **off** | **Crashes.** See `FINDINGS.md` §1 |
| `Mania Android` | **off — deliberately** | Ships **only** `Title/Logo.bin` + `Logo.gif`, i.e. the two files we rebuilt. Enabling it ahead of Addendum undoes the title-screen fix and restores stock-Mania branding; behind Addendum it does nothing. Its one real change (TOUCH TO START) has been **spliced into Addendum's sheet** instead — see below. |
| `Mobile Friendly UI (Clean)` | **on** (2026-08-18) | Ships only `UI/Buttons.gif` (256×512). Addendum ships no `Buttons.*`, so there is **no conflict**; frame defs come from the base game's `Buttons.bin` in `Data.rsdk`. Loaded last. If the icons look misaligned, set back to `n` — that is the whole fix. |

### "Touch to Start" without the mod

`Mania Android`'s entire effect is replacing the English Press Button art with
**TOUCH TO START**. Rather than let it override our fixed `Logo.*`, that art was blitted
into Addendum's sheet:

- source region `(1,421) 112×8` of `Mania Android/Data/Sprites/Title/Logo.gif`
- destination: same coordinates in Addendum's `Logo.gif`; the full old 120-wide region is
  cleared first, and the mod's `255` filler is remapped to `0` to match our sheet
- `Logo.bin` anim 8 ("Press Button") frame 0 width `120 → 112`; pivot `(-60,-4)` kept as
  the mod ships it

The prompt is accurate, not decorative: `TitleSetup.c:137` already synthesises
`keyStart.press` from a tap when the `AddendumAndroid` flag mod is active.

> Both sheets are 512×512 with identical animation coordinates (same base sheet), which
> is why a straight coordinate-for-coordinate blit works. Verify that before splicing
> anything else across.

### Critical: Addendum's `mod.ini`

Our APK compiles Addendum as `libGame.so`, so it must read:

```ini
Name=Sonic Mania Addendum
Description=A complete Sonic Mania full-game overhaul + expansion mod
Author=KiaraGale
Version=1.0.0
TargetVersion=5
modID=Sonic Mania Addendum
```

**If `DisableGameLogic=true` / `LogicFile=Addendum` are present**, the mod tries to
`dlopen libAddendum.so`, fails, and **none of its 693 assets load** — presenting as
"Amy.bin not found", the wrong title logo, and a crash leaving the title screen.
Redeploying master assets reintroduces those lines; strip them every time.

---

## Save files (2026-08-18)

| File | Holds | Notes |
|---|---|---|
| `SaveDataAddendum.bin` | the 8 save slots + `ProgressRAM` @ byte 9216 | medals/unlocks live here |
| `AddendumData.bin` | per-slot Addendum data + `AddendumProgress` @ 9216 | time stones, super emeralds, `player2ID` |
| `AddendumOptions.bin` | the `AddendumOptions` struct at offset 0 | **new format** — see `FINDINGS.md` §16 |
| `Achievements.bin`, `TimeAttackDB.bin`, `Options.bin`, `ReplayDB.bin` | as named | |

`savedata.bin` is **not used** by this build — a stock-engine leftover.

Current state: 6 complete files (Sonic&Tails / Sonic / Tails / Knuckles / Mighty / Ray),
each 7/7 emeralds + 7/7 time stones + 7/7 super emeralds; 32/32 gold medallions, 12/12
zones, good ending, every unlock. Options pinned to Infinite lives / Time Stones /
Shield Transfer on.

Backups: `save-backup-2026-08-18-prerestore/` (pre-restore state, plus
`*.restored-preunlock` copies taken before the unlock-all edit).

> **Trap:** old-format `AddendumOptions.bin` files (in the 2026-08-17 backups) contain
> *per-slot save data*, not options. Do not copy one into the game folder on this build.

---

## On-device asset edits (NOT reproduced by a rebuild)

Some fixes live in the mod folder, not in the CI workflow. **A fresh install of the
mod's assets will reintroduce these bugs** — re-apply from the backup or redo them.

| File | Change | Why |
|---|---|---|
| `Data/Sprites/Title/PlusLogo.bin` | all 6 animations repointed | `.bin`/`.gif` from different versions — `FINDINGS.md` §13 |
| `Data/Sprites/Title/Logo.bin` | Ribbon Center f1 → f0's rect; **Press Button f0 width 120 → 112** | f1 pointed at blank sheet space; width for the spliced TOUCH TO START art |
| `Data/Sprites/Title/PlusLogo.gif` | index 255 → 0 | filler/grid lines were opaque |
| `Data/Sprites/Title/Logo.gif` | index 255 → 0; **TOUCH TO START spliced in @ (1,421) 112×8** | same; see "Touch to Start" below |
| `mods/Shaders/Data/Shaders/OGL/*` | replaced with build's `GLShaders` | `FINDINGS.md` §7 |

Originals: `save-backup-2026-08-17/title-sheets-original-20260818/` and
`.../shaders-original-20260817/`.

---

## Backups

| Location | Contents |
|---|---|
| `Download/SonicMania/save-backup-2026-08-17/` | Original saves + `Settings.ini` + `modconfig.ini`, checksum-verified |
| `…/save-backup-2026-08-17/pre-port-saves/` | Saves as they were before switching to the port |
| `…/save-backup-2026-08-17/addendum-text-originals/` | Untouched `TextEN.gif`, `TextENAdd.gif`, `TextPlusEN.gif` |
| `SonicMania/_port_saves/` | Port's saves — **the completed-file data** |
| `SonicMania-old/` | Entire pre-project install incl. old `Data.rsdk` and `Extra Slot Amy` mod |

### Restoring the completed save files

Not yet attempted. Old and new Addendum save formats differ, and mixing them
crashed earlier. Try **one file at a time**, starting with:

```bash
cp "SonicMania/_port_saves/savedata.bin" "SonicMania/savedata.bin"
```

If it crashes, delete `savedata.bin` and relaunch to regenerate.

---

## Touch control geometry (if ever needed)

Canvas is 424×240. From `ManiaTouchControls/modSettings.ini` (negative X = from
right edge):

- Movement D-pad ≈ 13% across, 77% down
- Jump ≈ 87% across, 78% down

Only relevant if returning to the MTC route, which is a dead end.

---

## Useful diagnostics

```bash
GAME=/sdcard/Download/SonicMania/SonicMania

# log is cumulative — isolate the latest boot first
BOOT=$(grep -n "Loaded file Data.rsdk\|Loaded data file Data.rsdk" "$GAME/log.txt" | tail -1 | cut -d: -f1)
awk -v s="$BOOT" 'NR>=s' "$GAME/log.txt" | grep -iE "not found|ERROR" | grep -v "Objects/Static"

# a crash leaves the log ending abruptly with no shutdown lines
tail -20 "$GAME/log.txt"

# mod link failures (the single most common self-inflicted breakage)
grep -n "dlopen\|link logic" "$GAME/log.txt" | tail

# shader health — MUST be empty on a good boot (see FINDINGS.md §7)
awk -v s="$BOOT" 'NR>=s' "$GAME/log.txt" | grep -c "Fragment shader compiling failed"
```

`Data file not found: Data/Objects/Static/<hash>.bin` lines are **normal** — base
game object lookups that appear in healthy runs too.
