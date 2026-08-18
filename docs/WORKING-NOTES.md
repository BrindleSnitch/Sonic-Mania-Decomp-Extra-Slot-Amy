# Working notes — user preferences & process feedback

Guidance the user gave during this session, worth carrying forward.

---

## Explicit requirements

- **No secondary software for input.** Ruled out `Game Keyboard+` (which JonasYT's
  port bundles and expects). This is why native touch controls mattered enough to
  justify patching and rebuilding from source.
- **Touch controls are not optional.** When offered "working menus without touch
  controls" vs "touch controls without menus", the user rejected the trade and
  asked for a path to both — correctly, as one existed.
- Cosmetic issues (title logo) are acceptable; functional ones are not.

---

## Corrections the user made that changed the outcome

Both were right and both overturned my conclusions.

### 1. `Data.rsdk` — the alt file was correct

I dismissed the newer/larger file early on the basis of a date and a filename, and
an A/B test that *looked* decisive. The user pushed back:

> *"is it possible that the other data file that you initially disregarded as the
> wrong file … is in fact the correct data file we need? I only ask because it seems
> like you stumbled upon other, more likely culprits for the error since making that
> decision."*

Exactly right. That A/B test was **confounded** — Addendum was independently broken
at the time, so it couldn't distinguish the files. Container analysis later showed
the newer file is a strict superset, and JonasYT's working port ships a
**CRC-identical** copy.

**Lesson:** an A/B test run while another variable is broken proves nothing. Don't
bank an elimination made under those conditions.

### 2. Finding the existing Android port

The user found JonasYT's GameJolt port and asked to use it diagnostically. That
single artifact:
- confirmed the correct `Data.rsdk` (CRC match)
- proved the working Addendum is the **older, pre-migration** version
- provided a correct `Shaders` mod (`OGL/`) and clean save files
- gave a stable fallback build

**Lesson:** when a working reference build of the thing exists, diff against it
before theorising from source.

---

## Process notes (mine, for next time)

- **Read the source earlier.** `UIButton.c` and `Localization.h` were the
  authoritative answers and I reached them very late, after long detours through
  palette forensics and a hand-written GIF encoder. When rendered output is
  confusing, go to the drawing code.
- **Pair code and assets from the same commit.** Twice I mixed July code with May
  assets, producing symptoms that looked like data corruption.
- **`Data file not found: Data/Sprites/UI/Text.bin`** was in the very first
  Addendum log. I classified it as a benign probe. It was the actual defect.
- **One variable at a time.** Several confusing rounds came from changing the APK,
  assets, and config together.
- The user tests on real hardware and reports precisely, including screenshots.
  Their observations (e.g. "menu items say CONFIRM instead of their value") were
  consistently accurate and diagnostic — take them literally.
- **Check the scene data, not just the code.** Addendum's menus are `UIControl`
  entities matched by tag in `Data/Stages/Menu/Scene1.bin`. Twice now the shipped
  scene has been *behind* the shipped code, leaving pointers NULL that the code
  dereferences unguarded. `strings -a -e l` (UTF-16!) on the scene lists every tag
  in seconds — do that before assuming a screen is unfinished in the source.
- **Ask for a screen recording early.** `ffmpeg` is now installed in the proot
  (`apt-get install -y --no-install-recommends ffmpeg`). Extracting frames settled the
  title screen in minutes after three rounds of source-reading had got it wrong: the
  logo was *perfect* at t=4s and broken at t=5.3s, which localised everything to
  `swapDrawPriority`. Frames beat theories.
- **Check what a mod actually ships before enabling it.** `find <mod> -type f` takes
  seconds and settles whether it can conflict. `Mania Android` turned out to ship nothing
  but the two title-logo files we had spent hours repairing — enabling it either undid
  that work or did nothing, depending on load order. Extracting its one real change and
  splicing it in was both safer and reversible. Generalise: when a mod's payload overlaps
  files you have hand-fixed, prefer merging its delta over letting it win.
- **Parse the asset, don't trust the code's assumptions about it.** Three separate bugs
  (§12, §13, and the shader one) were code indexing past what the shipped asset
  actually contained. `docs/parse-sprite-bin.py`, `gifdec.py`, `gifenc.py`, `sprrw.py`
  are saved for this — always round-trip verify a writer before editing.
- **A screenshot of a working build is a spec.** Diffing the user's PC screenshots
  against the Android ones is what localised this: `[H] GAME OPTS.` vs
  `[H] SIDEKICK` on the same screen said "different code generation", not
  "broken rendering".

---

## Open items

| Item | Status |
|---|---|
| Shader fix (patch 5 + refreshed `Shaders` mod) | ✅ **confirmed 2026-08-17** — 0 compile failures in log |
| Addendum Options opens (patches 6–7) | ✅ **confirmed 2026-08-17** |
| Special stage soft-lock (patch 8) | ✅ **confirmed 2026-08-17** |
| Menu back gesture (patch 9) | ✅ **confirmed 2026-08-17** — 2-finger = Back, 3+-finger = Y |
| Sidekick selection (patch 10) | ✅ **confirmed 2026-08-18** |
| Title screen (rebuilt sprite `.bin`s) | ✅ **confirmed 2026-08-18** |
| **Addendum Options exit crash (patches 12–13)** | **deployed, NOT playtested** — enter Addendum Options, change something, two-finger tap out; the exit animation should play and survive |
| **Polish mods (2026-08-18)** | **deployed, NOT playtested** — TOUCH TO START spliced into the title sheet; `Mobile Friendly UI (Clean)` enabled. If the button icons look wrong, set that mod back to `n` |
| Gameplay submenu's own back prompt | still inert — scene-level (prompt not adopted by the control). Patch 9 works around it rather than fixing it |
| Save-select `SIDEKICK` → sidekick picker | upstream never implemented; would need new UI or direct `AddendumData.bin` editing |
| Confirm dialog buttons render | ✅ **confirmed working 2026-08-17** — patch 4 verified |
| Restore completed save files | not attempted — see `SETUP.md` |
| Re-enable `Mania Android` / `Mobile Friendly UI` | the original "polish" goal, untested on this build |
| "Addendum Options" crash | upstream; would need KiaraGale |
| Title screen texture glitch | upstream; cosmetic |
| Other blank dialogs | none found; mechanical fix if any appear — see `PATCHES.md` |

**All four source patches are verified working on real hardware.** The project's
stated goal is met.

## Housekeeping

- **The GitHub token is being KEPT active** — the user chose not to revoke it, so
  builds can resume without re-minting. See `BUILD.md` for its scopes and expiry
  (~2026-08-24). The secret is not stored on disk; it lives in the original chat
  transcript.
- Workflows persist in the fork, so rebuilding needs only a valid token.
