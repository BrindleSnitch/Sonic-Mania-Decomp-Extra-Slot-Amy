# Technical findings & dead ends

Read this before re-investigating anything. Each item below was established from
binaries, source, or engine logs — not inference.

---

## 1. Why `ManiaTouchControls` can never work with Addendum

**Two independent failures.**

**a) It never draws.** MTC *provides* `HUD_DrawTouchControls` and expects the game's
HUD to call it. Symbol counts in the port's binaries:

| Symbol | port `libGame.so` | `libManiaTouchControls.so` |
|---|---|---|
| `HUD_DrawTouchControls` | **0** | 1 |
| `BSS_/PBL_/UFO_` variants | **0** | 1 each |
| `CheckTouchRect` | **0** | 1 |
| `Player_Input_P1` | 2 | 2 |
| `TouchInfo` | 1 | 1 |

Addendum replaced `HUD` wholesale and dropped the call. Shared `Player_Input_P1`
and `TouchInfo` is why **input worked while nothing rendered**.

**b) It corrupts memory.** MTC hooks `Player_Input_P1` / `Player_CheckValidState`,
reaching into the `Player` struct at **stock Mania offsets**. Addendum's `Player`
differs (6th character, Miracle forms, new ability states). Result: clean stage
load, then a hard crash ~2s into gameplay once per-frame input processing runs.

Community sources independently confirm this ("you wouldn't be able to use
ManiaTouchControls due to mod conflicts causing crashes").

**Conclusion:** touch controls must come from Addendum's *own* HUD, compiled into
the same binary. That is what the newer Addendum has and what we build.

---

## 2. The engine has no built-in touch controls

`libRetroEngine.so` contains only:
- `DevMenu_HandleTouchControls` (dev menu only)
- raw plumbing: `TouchScreen.Down/XPos/YPos`

The Java layer has **no** `TouchControl`/`VirtualPad`/`Joystick` classes.
JonasYT's port bundles **Game Keyboard+** because the porter expected an external
virtual keyboard — its `Settings.ini` has only keyboard maps.

---

## 3. Addendum's public repo is mid-migration and internally inconsistent

`KiaraGale/Sonic-Mania-Addendum` master is an in-dev dump
("mass-upload old in-dev REMS build code").

- The `1.5.0-indev` tag and `master` have **byte-identical symbol sets** (334 each).
  Building the tag gains nothing — only assets differ between them.
- The code loads `UI/Text.bin` into `dynTextFrames` (a new per-character font).
  **No release ships it**; only the repo does.
- `Localization.h`'s enum resolves to **~205 strings**; every shipped
  `StringsEN.txt` has **68**. `SplitStringList` ranges prove the code expects
  **204** (0–203).
- Referenced but never shipped anywhere: `UI/SaveSelectEN-Add.gif`,
  `Players/Char-Add.gif`, `Sprites/Android/Loading.bin`.
- The **release `Addendum.dll` was built from code that is not in the repo**
  (older, pre-migration). That's why the PC release works and no repo build matches
  the release assets.

**The dynamic text path (`DrawText` + `dynTextFrames`) does not render.** Proven:
with a full 205-entry string table and `Text.bin` present, buttons were still blank.
This is why the fix is to force the *pre-rendered* path, not to fix the strings.

---

## 4. `Data.rsdk` — the correct file

**Use the Dec-2022 / 208,400,940-byte file.** It is CRC-identical to the one
JonasYT's working port ships.

```
size 208,400,940   crc32 852ae394   ← CORRECT (RSDKv5c)
size 208,368,695                    ← older (RSDKv5a), causes frame mismatches
```

Container header: `"RSDKv5"` + version char at offset 6, `uint16` file count at
offset 6–7. The Dec-2022 file is a **strict superset**: 1891 entries vs 1889,
with **zero** files present only in the older one.

Symptoms of the wrong (older) file: "SONIC" rendering as a second "MANIA",
sprite corruption, crash entering a stage as Amy.

> The user identified this. An earlier A/B test appeared to exonerate the newer
> file, but that test was confounded — Addendum was independently broken at the time.

---

## 5. Build flags

- **`RETRO_DISABLE_PLUS` must be OFF.** It sets `RSDK_AUTOBUILD`, the decomp's
  "public release" switch that strips Plus. With it on, Addendum shows its
  *"Non-Plus Lock Screen"* and the launcher relaunches forever.
  (`option(RETRO_DISABLE_PLUS "Disable plus. Should be set on for any public releases." OFF)`)
- **`RETRO_REVISION` makes no difference here** — rev 2 and rev 3 both request
  `UI/Text.bin`. The Origins-vs-Steam theory was wrong.
- `GAME_VERSION = VER_106 = 6` → `MANIA_USE_PLUS` true, `MANIA_USE_EGS` false.

---

## 6. Mod loading rules learned the hard way

- **First mod listed in `modconfig.ini` wins** asset conflicts.
- Android **cannot `dlopen` a library from `/sdcard`**. Mod logic must be compiled
  into the APK. This is why `LogicFile=` fails unless the matching `lib<Name>.so`
  is inside the APK.
- **`mod.ini` must match the build architecture:**
  - Addendum compiled as `libGame.so` (our build) → **strip** `DisableGameLogic`
    and `LogicFile`, or the mod fails to link and **none of its 693 assets load**
    (presents as "Amy.bin not found" + crash leaving the title screen).
  - Addendum compiled as `libAddendum.so` (mod build) → keep both lines.
- The in-app mod manager **rewrites `modconfig.ini`**. To reliably disable a mod,
  delete its folder.
- Save formats differ between old and new Addendum. Mixing them crashes.
  Park saves when switching builds.

---

## 7. All OpenGL shaders were silently failing (found 2026-08-17, late)

Discovered by reading the boot log while resuming the project — **not** previously
suspected. All 8 fragment shaders failed to compile on this device:

| Shader | Error |
|---|---|
| `None.fs` | `textureSize` redeclaring name; `round` cannot redeclare built-in |
| `Clean.fs`, `CRT-Yee64`, `CRT-Yeetron` | `textureSize` + cascading `invalid` operand errors |
| `YUV-420/422/444`, `RGB-Image` | `textureSize` redeclaring name |

**Two independent causes:**

1. **GLES3 built-in collision.** The Tensor G5 gives a GLES **3** context, so the
   engine uses `#version 300 es`, where `textureSize` is a built-in *function*.
   Every shader declares `uniform vec2 textureSize;`. Affects **upstream shaders
   too** — this is a device/driver-strictness issue, not an Addendum bug.
2. **Stale mod assets.** The `Shaders` mod (from JonasYT's port) predates upstream's
   `#if __VERSION__ < 130` guard around the ES2 `round()` polyfill.

**Why it was invisible:** `LoadShader` bails on compile failure without incrementing
`shaderCount`; `InitShaders` sees `maxShaders == 0` and installs the hardcoded
`backupFragment` (`gl_FragColor = texture2D(texDiffuse, ex_UV);`), setting
`videoSettings.shaderSupport = false`. The screen still draws, just unfiltered.

**What it actually cost:**

- **FMV/cutscenes rendered greyscale.** The engine's own comment:
  `// No shader support means no YUV support! at least use the brightness to show it in grayscale!`
- **`screenDim` never applied** — pause/fade dimming dead (only bound inside
  `if (videoSettings.shaderSupport)`)
- **No pixel filtering** — raw nearest-neighbour 424×240 → 1344×2992, hence shimmer

**Fix:** see `PATCHES.md` patch 5 (engine) + deploy the workflow's bundled
`GLShaders` over `mods/Shaders/Data/Shaders/OGL/`.

> **Lesson (again):** the log had this from the very first boot, same as the
> `Text.bin` defect in §3. `Fragment shader compiling failed` was scrolling past
> in every session. Grep the boot log for `ERROR` before theorising.

---

## 8. "Addendum Options" crashes because the Menu scene is behind the code

**This supersedes the earlier "upstream, assets never shipped" diagnosis in §3.**
The missing `-Add` GIFs are real but are *not* what breaks this screen.

Addendum's menus are `UIControl` entities placed in
`Data/Stages/Menu/Scene1.bin`, matched by **tag**. The shipped scene is behind
the shipped code — it is missing two controls the code unconditionally uses:

| Tag the code looks for | In `Scene1.bin`? |
|---|---|
| `Main Menu`, `Addendum Options` | yes |
| `Gameplay Options`, `Style Options`, `Music Options` | yes |
| **`Multiplayer Options`** | **NO** |
| **`Secrets`** | **NO** |

(Scene tags are UTF-16 — use `strings -a -e l`, plain `strings` finds nothing.)

So `MainMenu->multiplayerOptsControl` and `MenuSetup->secrets` stay **NULL**, and
three separate call paths dereference them without a check:

1. `MainMenu_YPressCB_GoToAddendumOptions` calls
   `AddendumToggles_SetToggleButtons_Multiplayer()` **before** transitioning →
   NULL deref **the instant you press Y/H on the main menu**. *This is the actual
   "Addendum Options crash."*
2. `MainMenu_StartReturnToParentScreen` calls the same pair again on the way out.
3. `MenuSetup_OpenSecretsMenu` derefs `MenuSetup->secrets` → crash on pressing
   Y/H over the **NO SAVE** slot in the save select.

**This matters because `Gameplay Options` is where the good stuff lives** — it is a
strict superset of the PC build's "Game Options" screen (14 rows):

```
TIME LIMIT   DEBUG MODE   SONIC/TAILS/KNUX/MIGHTY/RAY/AMY MOVESET
PEELOUT ABILITY   SPINDASH TYPE (Mania/CD/None)   LIFE SYSTEM
SECONDARY GEMS   SHIELD TRANSFER   ITEMBOX SHIELDS
```

Fixed by `PATCHES.md` patches 6 and 7 — NULL/`buttonCount` guards, no new assets.

### The save-select `SIDEKICK` prompt is an unimplemented feature

The PC build's save select shows `[H] GAME OPTS.`; this build shows `[H] SIDEKICK`.
That is **not** a mislabel — in-dev Addendum moved sidekick choice to a per-save
setting (`AddendumData.player2ID/3ID/4ID`) and the prompt art changed with it. But
`MenuSetup_SaveSel_YPressCB` was never written for normal slots — it still only
handles `buttonID == 8` (NO SAVE → Secrets). So the prompt is real and the feature
behind it does not exist yet.

There is **no** sidekick/"& Knuckles" field in `AddendumOptions` (20 fields, see
`SaveGame.h`); it is per-save data. Enabling it would mean either writing a save-slot
picker UI (no scene support for one) or editing `AddendumData.bin` directly.

---

## 9. Special stage results soft-lock — `SECONDGEMS_NONE` is unhandled

**Not a touch-controls problem.** A pure state-machine hole, reproducible for anyone
running default options.

`GameVariables.h`:

```c
SECONDGEMS_NONE        = 0   // <-- the DEFAULT in a fresh options file
SECONDGEMS_SUPEREMERALD = 1
SECONDGEMS_TIMESTONE    = 2
```

Both `SpecialClear_State_ShowTotalScore_Continues` and `_NoContinues` branch only on
`SUPEREMERALD` and `TIMESTONE`. With the default value **neither branch runs, so
`self->state` is never reassigned** — the state re-executes forever. The results
screen sits there with no input that can escape it.

A second hole in the same functions: `SUPEREMERALD` + all 7 emeralds +
`specialStageID > 6` falls through an inner `if` that has no `else`.

Fixed by `PATCHES.md` patch 8 (both holes).

> This was masked by the Addendum Options crash (§8): the user could not reach
> Gameplay Options to change `secondaryGems` off the default, so every special
> stage ended in a soft lock.

---

## 10. The touch input model outside gameplay

`HUD_DrawTouchControls` / `HUD_DrawMobileHUD` are **gameplay-only** — they read
`player->stateInput` and draw dpad / jump / super / swap / pause. Nothing draws them
in menus or on results screens.

So outside gameplay the *only* touch affordances are:

| Affordance | Mechanism | Requirement |
|---|---|---|
| Tap a menu entry | `UIButton->touchCB`, driven from `UIControl_ProcessInputs` | button inside the control |
| Tap an on-screen prompt | `UIButtonPrompt_CheckTouch` → `UIControl_ClearInputs(buttonID)` → sets `anyBackPress` / `anyYPress` | **`prompt->parent` must be set** |

`prompt->parent` is only assigned in `UIControl_Create`, and only to prompts whose
**position lies inside the control's bounds** (`UIControl_ContainsPos`). A screen
whose scene ships no prompt — or one placed outside the bounds — has **no way to
issue Back or Y at all**. Observed:

- **Music Options submenu** — no back prompt in the scene, inescapable
- **Gameplay Options submenu** — prompt visible but inert
- **Secrets** (Y over the NO SAVE slot) — no Y affordance

`SpecialClear_State_TallyScore` is the one place upstream handles this, gated on the
`AddendumAndroid` mod flag:

```c
if (TouchInfo->count && !ControllerInfo->keyStart.down)
    ControllerInfo->keyStart.press = true;
```

**The engine has no Android Back-key path at all** — `RSDK.java` (a `GameActivity`)
declares no key handling, and neither `KBInputDevice.cpp`, `RetroEngine.cpp` nor
`EGLRenderDevice.cpp` reference `AKEYCODE_*`. Mapping the system Back gesture would
mean writing new input glue, so patch 9 uses multi-touch gestures instead.

---

## 11. The sidekick system was complete — just gated behind extra controllers

**This supersedes §8's "unimplemented upstream feature" conclusion.** That was wrong:
`MenuSetup_SaveSel_YPressCB` really is a stub for normal slots, but character
selection does not live there.

`UISaveSlot_NextCharacter_ExtraPlayers(playerID)` (UISaveSlot.c) fully implements
per-slot character choice for players 2–4 and persists to `AddendumData`. It is
called from `UISaveSlot_ProcessButtonCB` — but only from
`ControllerInfo[CONT_P2/P3/P4].keyY.press`.

The design is **local multiplayer**: P1 presses Y to assign the next input slot to a
newly-connected pad (`API_AssignInputSlotToDevice`), then *that* player presses Y on
*their* pad to pick their character. Entirely reasonable on console/PC, and
completely unreachable with one touchscreen.

Fixed by `PATCHES.md` patch 10 — no new UI, just a fourth call site.

> **Lesson:** before concluding a feature is unimplemented, grep for its *worker
> function*, not just the callback the UI prompt points at. §8 looked at
> `MenuSetup_SaveSel_YPressCB`, found a stub, and stopped. The real implementation
> was in a different object, complete, one grep away.

---

## 12. Title screen corruption — out-of-range "plus shine" animation

**Not a palette, sheet, or logo-art problem.** Earlier notes blamed "Addendum's own
logo animation code" and called it unfixable; the real cause is one wrong index.

Parsing the mod's `Data/Sprites/Title/PlusLogo.bin` (RSDKv5 `SPR` format) gives
**6 animations**:

```
0 Plus Base | 1 Plus Shine (35 frames) | 2 Eggman | 3 Chain | 4 Capsule | 5 Smoke
```

`TitleLogo_State_PlusLogo` asks for animation **`6 + reverseColor`** — out of range.
`RSDK::SetSpriteAnimation` bounds-checks:

```c
if (animationID >= spr->animCount)
    return;          // <-- returns WITHOUT touching the animator
```

So `plusAnimator` is **never initialised**. `TitleLogo_Create` doesn't initialise it
either (the `TITLELOGO_PLUS` case only stores `storeY`). Yet
`TitleLogo_State_PlusShine` calls `ProcessAnimation()` on it and `TitleLogo_Draw`
draws it **every frame** — walking whatever the entity slot happened to contain.
Hence solid blocks (frame rects into empty atlas regions) plus drifting coloured
fragments (stale frame data, re-read each frame).

Timing matches exactly: `TitleLogo_State_HandleSetup` hands over to
`TitleLogo_State_PlusLogo` when the bounce finishes — *"only after the logo bounce."*

**The correct call is 20 lines below, in `TitleLogo_State_PlusShine`:**

```c
RSDK.SetSpriteAnimation(TitleLogo->plusFrames, 1, &self->plusAnimator, true, TitleLogo->reverseColor);
```

Animation **1**, with `reverseColor` as the **frame** index. Line 287 mistakenly folds
`reverseColor` into the animation slot instead. Fixed by `PATCHES.md` patch 11.

> **Lesson:** parse the asset, don't eyeball it. `animCount = 6` versus a requested
> index of 6 is a five-minute check that a year of "it's just cosmetic" never made.
> The RSDKv5 `SPR` layout is in `RSDKv5/RSDK/Graphics/Animation.cpp :: LoadSpriteAnimation`.

---

## 13. Title screen: `PlusLogo.bin` and `PlusLogo.gif` are from different versions

Superseded §12's diagnosis. Patch 11 fixed a real bug (out-of-range shine animation)
but **not** the visible corruption.

Measured directly from the assets:

| | cell size | row pitch |
|---|---|---|
| `PlusLogo.gif` (actual) | **160×37**, 2 columns at x=1 / x=162 | **38 px** |
| `PlusLogo.bin` (expected) | 137×32, 1 column at x=0 | **33 px** |

Every rect the `.bin` cut was offset and wrong-sized. **Eggman's rect landed inside
the ADDENDUM text strip**, which is why Robotnik flew around as scrambled lettering —
the user's observation that "the garbage is supposed to be Dr. Robotnik" is what
made this findable.

Rendering the sheet with the scene palette showed the true layout: a 42-frame
ADDENDUM shine strip in two columns, with Eggman / Chain / Capsule / Smoke in the
top-right corner.

Separately, `Logo.bin` anim 3 "Ribbon Center" **frame 1** points at blank sheet
space, and `TitleLogo_Draw` switches to exactly that frame when `swapDrawPriority`
flips — that was the missing red SONIC banner (the black area behind it is the
emblem's own interior, normally covered).

Fixed by rebuilding both `.bin` files — see `PATCHES.md` "Title sheet asset fixes".
Sizes for Eggman (31×25), Chain (4×4), Capsule (35×41 / 59×41) and Smoke (16×16)
**already matched** the real sprites, which independently confirmed the mapping.

> **Lesson:** extracting video frames settled in minutes what three rounds of
> source-reading got wrong. `ffmpeg` is now installed in the proot. At t=4s the logo
> was perfect and at t=5.3s it broke — that one fact localised everything to
> `swapDrawPriority`. Ask for a recording earlier.

---

## 14. Sustained logging hard-crashes the game (JNI local-ref leak)

**An upstream RSDKv5 engine bug affecting every Android build, not port-specific.**

`RSDK::PrintLog`, Android branch (`RSDKv5/RSDK/Dev/Debug.cpp`):

```c
jbyteArray array = jni->env->NewByteArray(len); // "as per research, this gets freed automatically"
jni->env->SetByteArrayRegion(array, 0, len, (jbyte *)outputString);
jni->env->CallVoidMethod(jni->thiz, writeLog, array, as);
```

The comment is wrong. JNI local references are reclaimed only when a native call
**returns to Java**; the engine's game loop never does. So **every log line leaks one
local ref**, and when the local reference table overflows the VM aborts the process.

Symptom: lag → freeze → hard crash, with music still playing (audio is a separate
thread). No error in `log.txt` — it simply stops mid-line.

The trigger was `UIButton.c:111`, a leftover debug print inside `UIButton_Draw` on
the pre-rendered branch that **patch 1 routes nearly every button through**. It fires
per button per frame — 33,225 lines for `listID 19` (Addendum Options) in one
session, and `log.txt` grew 7 MB → 30 MB.

Fixed by `PATCHES.md` patches 12 (engine, `DeleteLocalRef`) and 13 (remove the print).
Patch 12 is the important one: without it any chatty logging can kill the game.

> Note `engineDebugMode` is hardcoded `true` in `Debug.cpp` — the `devMenu=y` setting
> in `Settings.ini` does **not** gate logging, so there is no runtime workaround.

---

## 15. Addendum Options exit crash — unguarded NULL in `UIButton_SetChoiceSelection`

§14's JNI/logging fixes were real bugs but **did not** cause this crash; it survived
them (confirmed: `drawing sprite` spam gone, boot log 42,893 → 576 lines, still crashed).

`UIButton_SetChoiceSelection` (UIButton.c) ends:

```c
button->selection         = selection;
EntityUIButton *newChoice = UIButton_GetChoicePtr(button, selection);
newChoice->active         = ACTIVE_NORMAL;   // <-- no NULL check
```

`UIButton_GetChoicePtr` returns **NULL** when the entity in the slot before the button
is not a `UIChoice` / `UIVsRoundPicker` / `UIResPicker` / `UIWinSize`:

```c
if (choice->classID == UIChoice->classID || ...) return choice;
return NULL;
```

The sibling `UIButton_SetChoiceSelectionWithCB` guards this correctly (`if (newChoice)`);
this variant does not. `AddendumToggles` calls the unguarded one **54 times**, including
all 14 Gameplay Options buttons from `MainMenu_StartReturnToParentScreen` — exactly the
path taken when leaving Addendum Options.

Same root theme as §8: the Addendum Options screens exist in the scene **without the
`UIChoice` entities the code assumes accompany them**.

Fixed by `PATCHES.md` patch 14.

### Debugging notes for next time

- **`ffmpeg` and `logcat` are both available**, but `logcat` only exposes Termux's own
  UID — the game's native crash never appears there. Don't waste time on it.
- A hard native crash leaves `log.txt` ending mid-line with **no error**. The way to
  localise it is to bracket the suspect path with `LogHelpers_Print` and read the last
  line (safe now that §14's leak is fixed, provided it is not per-frame).
- **sed replacement `&` is the whole match; `\&` is a literal ampersand.** Using `\&`
  silently *deletes* the line you meant to keep. A build was lost to this. Always assert
  the original code still exists, not just that the new code was added:
  `test "$(grep -c '^&$' file.c)" -eq 0`

---

## 16. Save-file naming changed between Addendum versions

The **old** Addendum stored per-slot Addendum data (time stones, super emeralds,
`player2ID`…) in **`AddendumOptions.bin`**. The **current** build stores per-slot data
in **`AddendumData.bin`** and uses `AddendumOptions.bin` for the *options struct*.

Same filename, completely different contents. Consequences:

- The user's time stones were never lost — they sat in the old `AddendumOptions.bin`
  while the new build looked in `AddendumData.bin` and found nothing. Recovering them
  was a straight `cp AddendumOptions.bin AddendumData.bin` from the 2026-08-17 backup.
- **Never copy an old-format `AddendumOptions.bin` into the game folder** on this build
  — it would be read as the options struct and produce garbage settings.

### Save data layout (verified by parsing, offsets confirmed against real data)

| | |
|---|---|
| Slot stride | `0x100` int32 = **1024 bytes**, slots 0–7; encore at `0x100*(slot%3+10)` |
| `SaveRAM` | pad `0x58`, then saveState, characterID, zoneID, lives, score, score1UP, **collectedEmeralds @ 0x70**, … medalMods @ 0x84 |
| `AddendumData` | pad `0x62`→ aligned `0x64`; actID, **timeStones @ 0x68**, **superEmeralds @ 0x6C**, nextTS, emeraldsTransferred @ 0x74 |
| `ProgressRAM` | `saveRAM[0x900]` = **byte 9216** of `SaveDataAddendum.bin`; pad 86, medals[32], allGold@120, allSilver@124, zoneCleared[12]@128, allZones@176, emeraldObtained[7]@180, allEm@208, unreadNotifs[9]@212, specialCleared[7]@248, allSpec@276, ending@280, **goldMedalCount@284, silverMedalCount@288** |
| `AddendumProgress` | `addendumVar->saveRAM[0x900]` = byte 9216 of `AddendumData.bin`; pad 84, timeStoneObtained[7]@84, allTimeStones@112, superEmeraldObtained[7]@116, allSuper@144 |

All unlocks are gated purely on `silverMedalCount`: Peel-out ≥1, Insta-shield ≥6,
**& Knuckles ≥11**, Debug Mode ≥16, Mean Bean ≥21, D.A. Garden ≥26, Blue Spheres ≥32.
`GameProgress_UnlockAll()` in `GameProgress.c` is the authoritative recipe — replicate
it rather than inventing values.

---

## 17. Addendum options never persisted — the loader is never called

`Addendum_SaveOptions` writes `AddendumOptions.bin`, and `Addendum_LoadOptions` exists
and is declared in `SaveGame.h` — but **nothing calls it**. `ManiaModeMenu_InitAPI`
loads only `Options.bin`, `SaveDataAddendum.bin`, `AddendumData.bin` and `ReplayDB.bin`
(confirmed in `log.txt`: `AddendumOptions.bin` never appears as a load attempt).

So `addendumOpt->optionsRAM` stays zeroed every boot and every option falls back to its
`= 0` enum value — life system Mania, **secondary gems NONE**, shield transfer OFF.
Nothing set in the Addendum Options menu survived a restart.

> This is also the final piece of §9: `secondaryGems` could never be anything but NONE
> across a restart, so the special-stage soft lock was guaranteed on every fresh boot.

Fixed by `PATCHES.md` patch 16. `Addendum_LoadOptionsData()` must be called first — it
sets `SaveGame->addendumMods`, which `Addendum_LoadOptions` early-returns on if NULL.

---

## 18. Dead ends (do not repeat)

| Attempted | Outcome |
|---|---|
| Palette-row analysis (bank 0 rows 0/11) | Real anomaly, **not** the cause |
| Custom GIF re-encoder to remap palette indices | Worked perfectly, fixed nothing |
| Swapping to the older `Data.rsdk` | Wrong direction; newer is correct |
| Building at the `1.5.0-indev` tag | Identical code to master |
| `RETRO_REVISION=2` | No behavioural difference |
| Reconstructing the 205-entry string table | Correct work, but `DrawText` is broken |
| Blanking string index 0 | Removed `TEST STRING`, buttons still blank |
| Master asset pack wholesale | Sprite corruption *with the wrong `Data.rsdk`* |
| `Refined MTC` | Crashed; left persistent damage until saves restored |
