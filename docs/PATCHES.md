# Source patches

All applied by the **"Patch menus…"** step in `addendum-android.yml`, via `sed`,
against a fresh checkout each build. Each has a `test` guard so the build **fails
loudly** if upstream changes and a patch stops matching.

---

## Root cause they all address

Addendum is mid-migration from **pre-rendered word sprites** to a **dynamic
per-character font**. The dynamic path (`dynTextFrames` + `RSDK.DrawText`) **does
not render** — proven with a complete 205-entry string table and `Text.bin` present.

Every menu object has this shape:

```c
Localization_GetString(&self->string, self->stringID);
if (self->string.length > 0) { /* dynamic — BROKEN */ }
else                         { /* pre-rendered artwork — WORKS */ }
```

The patches steer everything to the `else` branch.

---

## Patch 1 — `UIButton.c`: prefer pre-rendered art

**Files:** `SonicMania/Objects/Menu/UIButton.c` (4 branches, incl. `UIButton_Draw`)

```sed
s/if (self->string.length > 0 && !self->disabled)/if (self->string.length > 0 \
  && self->listID == 0 && self->frameID == 0 && !self->disabled)/g

s/if (self->string.length > 0)/if (self->string.length > 0 \
  && self->listID == 0 && self->frameID == 0)/g
```

**Effect:** use the dynamic path *only* when a button has no pre-rendered artwork
configured (`listID`/`frameID` both 0). Everything with artwork uses it.

> **History:** the first version forced *all* buttons to the fallback
> (`if (0)`). That fixed the main menu but made the pause menu read **"CONFIRM"**
> everywhere — those buttons had `listID`/`frameID` of 0, so they landed on
> animation 0, frame 0, which is literally the word CONFIRM. Hence the conditional.

---

## Patch 2 — `UIButtonPrompt.c`: unconditional fallback

```sed
s/if (self->string.length > 0)/if (0)/g
```

Prompts (`CONFIRM` / `BACK` / `NEXT` in the corner bars) use `promptID` rather than
`listID`/`frameID`, and are verified correct on the pre-rendered path.

---

## Patch 3 — `PauseMenu.c`: record the sprite it already chose

**File:** `SonicMania/Objects/Global/PauseMenu.c`, in `PauseMenu_AddButton`

`PauseMenu` sets the correct animator directly but never records it, so
`UIButton_Setup` thinks the button has no artwork and clobbers it:

```c
RSDK.SetSpriteAnimation(UIWidgets->textFrames, 10, &button->animator, true, id);
button->listID = 10;      // ← added   (animation 10 = "Pause Menu")
button->frameID = id;     // ← added   (Continue / Restart / Exit)
```

Fixes: pause menu labels.

---

## Patch 4 — `UIDialog.c`: same defect

**File:** `SonicMania/Objects/Menu/UIDialog.c`, in `UIDialog_AddButton`

```c
RSDK.SetSpriteAnimation(UIWidgets->textFrames, 9, &button->animator, true, frame);
button->listID = 9;       // ← added   (animation 9 = "Dialog Buttons")
button->frameID = frame;  // ← added   (Yes / No / Continue)
```

Fixes: confirmation dialog buttons.

---

## Patch 5 — `EGLRenderDevice.cpp`: GLES3 `textureSize` uniform collision

**File:** `RSDKv5/RSDK/Graphics/EGL/EGLRenderDevice.cpp` (engine, not Addendum)

Unlike patches 1–4 this is an **engine** patch and is unrelated to menu text.

On this device the EGL context comes back as **GLES 3**, so the engine prepends
`_GLVERSION3` = `#version 300 es`. In GLSL ES 3.00 **`textureSize` is a built-in
function**, so every shader's `uniform vec2 textureSize;` is rejected:

```
ERROR: 0:23: 'textureSize' : redeclaring name
```

All 8 fragment shaders fail. `LoadShader` returns early on compile failure, so
`shaderCount` never increments, `maxShaders` stays 0, and `InitShaders` falls back
to the hardcoded `backupFragment` passthrough with **`videoSettings.shaderSupport
= false`**. The game still renders, which is why this went unnoticed.

```sed
s|#define texture2D texture\n"|#define texture2D texture\n#define textureSize RSDK_texSize\n"|
s|"textureSize"), 1, \&textureSize\.x|"RSDK_texSize"), 1, \&textureSize.x|
```

The first extends the GLES3 preamble so the shader's declaration and all its uses
are renamed by the GLSL preprocessor; the second fixes the single matching
`glGetUniformLocation` call site (line ~707). **Engine-only** — the shader files on
`/sdcard` are untouched, so there is no APK/asset sync hazard.

Safe because **no shader calls the built-in `textureSize()`** — verified across all
9 upstream OGL files. A guard asserts the extended string still fits `_GLVERSION[128]`
(it comes to 108 bytes).

### Companion asset fix (not a source patch)

Patch 5 alone is not enough: the `Shaders` mod shipped by JonasYT's port predates
upstream's version guards, so `None.fs` also redefines built-in `round()`:

```
ERROR: 0:51: 'round' : cannot redeclare or overload built-in function
```

Upstream master already guards both (`#if GL_ES && __VERSION__ == 100`,
`#if __VERSION__ < 130`). The workflow **already bundles** matching shaders as
`artifacts/mods/GLShaders` — they just had never been deployed. Copy them over
`mods/Shaders/Data/Shaders/OGL/` after each build so code and assets stay paired.

---

## Patch 6 — `AddendumToggles.c` / `MainMenu.c`: NULL Multiplayer control

**Files:** `SonicMania/Objects/Menu/AddendumToggles.c`, `MainMenu.c`

The Menu scene has no `Multiplayer Options` UIControl, so
`MainMenu->multiplayerOptsControl` is NULL — yet
`MainMenu_YPressCB_GoToAddendumOptions` calls
`AddendumToggles_SetToggleButtons_Multiplayer()` *before* transitioning. Pressing
Y/H on the main menu therefore crashed instantly. See `FINDINGS.md` §8.

A shell helper inserts a guard into each of the 8 toggle functions:

```c
if (!control || control->buttonCount < N) return;
```

with `N` = 14 (Gameplay), 2 (Style), 2 (Music), 1 (Multiplayer) — the highest
`buttons[]` index each function touches, +1. Guarding on `buttonCount` as well as
NULL means a scene that is merely *short* on buttons degrades to "screen does
nothing" instead of crashing.

> `AddendumToggles_ChangeMenuSpriteStyle` also assigns `control` but never
> dereferences it — it must **not** be guarded or the diorama sprites stop loading.
> The sed is function-scoped for exactly this reason, and a `test` asserts it.

Plus, so the absent screen can't soft-lock the menu:

```c
if (control->buttonID == 3 && MainMenu->multiplayerOptsControl)
    UIControl_MatchMenuTag("Multiplayer Options");
else if (control->buttonID == 3)
    control->childHasFocus = false;   // no such screen — don't hand off focus
```

---

## Patch 7 — `MenuSetup.c`: NULL Secrets control

**File:** `SonicMania/Objects/Menu/MenuSetup.c`

Same defect class. No `Secrets` UIControl in the scene → `MenuSetup->secrets` is
NULL → `MenuSetup_OpenSecretsMenu` crashes on pressing Y/H over the **NO SAVE**
slot.

```c
// don't even start the transition
if (control->active == ACTIVE_ALWAYS && control->buttonID == 8 && MenuSetup->secrets) {
// and be defensive in the callback
EntityUIControl *control = MenuSetup->secrets;
if (!control) return;
```

> The second sed **must** be function-scoped: `MenuSetup_GetMedalMods` assigns the
> same pointer but returns `int32`, where a bare `return;` will not compile. A
> `test` asserts the guard landed only in `MenuSetup_OpenSecretsMenu`.

---

## Patch 8 — `SpecialClear.c`: special stage results soft-lock

**File:** `SonicMania/Objects/UFO/SpecialClear.c`

`SECONDGEMS_NONE == 0` is the default and neither `ShowTotalScore_Continues` nor
`_NoContinues` handles it, so the state never advances. See `FINDINGS.md` §9.

Adds an explicit `SECONDGEMS_NONE` branch ahead of the existing two (2 sites), which
does what every other terminal path does:

```c
self->timer    = 0;
self->showFade = true;
RSDK.PlaySfx(SpecialClear->sfxSpecialWarp, false, 0xFF);
self->state    = SpecialClear_State_ExitResults;
```

and closes the `specialStageID > 6` hole by opening an `else` after the
`ExitFinishMessageSuper` assignment — **the original block's closing brace becomes
the `else`'s**, so braces stay balanced without a multi-line sed.

> The two `ExitFinishMessageSuper` sites are distinguished **by indentation**: 24
> spaces in the SUPEREMERALD branch (the broken one), 20 in the TIMESTONE branch
> (which already has its `else`). Don't relax that anchor.

---

## Patch 9 — `UIControl.c`: menu back gesture for touch-only devices

**File:** `SonicMania/Objects/Menu/UIControl.c`

Menus can only raise Back/Y through a `UIButtonPrompt` positioned inside the
control's bounds, and several Addendum screens ship without one — see
`FINDINGS.md` §10. Adds a global gesture in the per-frame input assembly, right
after `anyBackPress |= forceBackPress` (so the existing
`if (anyBackPress) { anyConfirmPress = false; anyYPress = false; }` still arbitrates):

```c
static int32 maxTouchCount = 0;
if (TouchInfo->count > maxTouchCount) maxTouchCount = TouchInfo->count;
if (!TouchInfo->count && maxTouchCount) {
    if (maxTouchCount == 2)      UIControl->anyBackPress = true;
    else if (maxTouchCount >= 3) UIControl->anyYPress    = true;
    maxTouchCount = 0;
}
```

**2-finger tap = Back, 3+-finger tap = Y.** Tracking the *maximum* touch count over
the whole contact and acting on release is what keeps a 3-finger tap from also
registering as a 2-finger one on the way down.

This is an invented control scheme, not upstream behaviour — it is the fallback that
makes every menu escapable regardless of what the scene provides. Tap an empty area:
a finger landing on a menu entry may also trigger that entry's `touchCB`.

---

## Patch 10 — `UISaveSlot.c`: sidekick selection on single-input devices

**File:** `SonicMania/Objects/Menu/UISaveSlot.c`

`UISaveSlot_NextCharacter_ExtraPlayers(playerID)` **already existed** and already did
the whole job — cycles player 2/3/4's character and persists it to
`AddendumData.player2ID/3ID/4ID`. It was simply unreachable:

```c
if (ControllerInfo[CONT_P2].keyY.press) UISaveSlot_NextCharacter_ExtraPlayers(1);
if (ControllerInfo[CONT_P3].keyY.press) UISaveSlot_NextCharacter_ExtraPlayers(2);
if (ControllerInfo[CONT_P4].keyY.press) UISaveSlot_NextCharacter_ExtraPlayers(3);
```

The design is *each extra player picks on their own controller*. A phone has one
input device, so `ControllerInfo[CONT_P2..P4]` never register anything.

Patch adds a fourth trigger — a Y that did **not** come from a physical button, i.e.
the patch-9 multi-touch gesture or a tap on the `SIDEKICK` prompt:

```c
if (UIControl->anyYPress && !ControllerInfo->keyY.press) {
    UIControl->anyYPress = false;              // consume: one gesture = one step
    UISaveSlot_NextCharacter_ExtraPlayers(1);
}
```

Only `buttons[control->buttonID]` gets `processButtonCB`, so this fires for the
highlighted slot only; the consume is belt-and-braces against a second active control.

Players 3/4 remain unreachable on one device, so a cascade ties them to the sidekick —
cycling P2 round to "none" clears them too:

```c
if (playerID == 1 && !self->p2Active) {
    self->buddyFrameID1 = 7; self->buddyFrameID2 = 7;
    self->p3Active = false;  self->p4Active = false;
}
```

Placed **before** the existing `if (saveRAM->saveState != SAVEGAME_BLANK)` block so
its `addendumData` writes pick up the cleared values.

### Character IDs

`0`–`5` are characters (the save select draws the portrait, so the roster order is
visible in use); **`7` = none**. `UISaveSlot` treats `<= 5` as an active player.
Blank saves default all three to `7`.

---

## Patch 11 — `TitleLogo.c`: title screen logo corruption

**File:** `SonicMania/Objects/Title/TitleLogo.c`

`PlusLogo.bin` has 6 animations; the code asked for `6 + reverseColor`, so
`SetSpriteAnimation` bailed and left `plusAnimator` uninitialised while
`PlusShine` processed and `Draw` drew it. See `FINDINGS.md` §12.

```sed
s|plusFrames, 6 + TitleLogo->reverseColor, &self->plusAnimator, true, 0|
  plusFrames, 1, &self->plusAnimator, true, TitleLogo->reverseColor|
```

This makes `TitleLogo_State_PlusLogo` identical to the already-correct call in
`TitleLogo_State_PlusShine` — animation 1, `reverseColor` as the frame index.

Plus a defensive init in `TitleLogo_Create`'s `TITLELOGO_PLUS` case, which
previously set only `storeY`:

```c
RSDK.SetSpriteAnimation(TitleLogo->plusFrames, 0, &self->plusUnderlayAnimator, true, 0);
RSDK.SetSpriteAnimation(TitleLogo->plusFrames, 1, &self->plusAnimator, true, 0);
self->mainAnimator.frames = NULL;   // Draw skips NULL frames
```

so no draw can ever read an uninitialised animator. `mainAnimator` is deliberately
left NULL rather than pointed at "Game Title" — the `GAMETITLE` entity already draws
that until `swapDrawPriority` flips, and initialising it would double-draw the title.

### Verifying sprite assets

`FINDINGS.md` §12 has a parser recipe. The `SPR` layout is in the engine at
`RSDKv5/RSDK/Graphics/Animation.cpp :: LoadSpriteAnimation`. Frame records are
`sheetID u8, duration u16, unicodeChar u16, sprX/sprY/width/height/pivotX/pivotY i16`,
followed by `hitboxCount * 4 * i16`. Animation **names are plain strings** — a quick
`strings -a` on a `.bin` lists them in index order, which is enough to catch an
out-of-range index without writing a parser at all.

---

## Patch 12 — `Debug.cpp`: JNI local-reference leak in `PrintLog`

**File:** `RSDKv5/RSDK/Dev/Debug.cpp` (engine)

```sed
s|jni->env->CallVoidMethod(jni->thiz, writeLog, array, as);|
  &\n            jni->env->DeleteLocalRef(array);|
```

Every `PrintLog` call leaked one JNI local ref; the table overflows and the VM aborts
the process. See `FINDINGS.md` §14. **This is the load-bearing fix** — patch 13 only
removes the loudest caller.

---

## Patch 13 — `UIButton.c`: remove per-frame debug log

**File:** `SonicMania/Objects/Menu/UIButton.c`

```sed
/drawing sprite %d from listID/d
```

Leftover debug print inside `UIButton_Draw`, on the branch patch 1 sends nearly every
button down. One JNI call + log write per button per frame.

---

## Title sheet asset fixes (no rebuild — `.bin` edits only)

`PlusLogo.bin` and `PlusLogo.gif` are from different Addendum versions (see
`FINDINGS.md` §13). Both `.bin` files were **rebuilt on-device**, not patched in CI,
so they live in the mod folder and are **not reproduced by a rebuild** — they are
backed up in `save-backup-2026-08-17/title-sheets-original-20260818/`.

| Animation | Corrected to |
|---|---|
| `PlusLogo` Plus Base | (1,22) 160×37, pivot (-80,2) |
| `PlusLogo` Plus Shine | 42 frames, cells (1\|162, 22+38r) 160×37 |
| `PlusLogo` Eggman | (323,43) / (355,43) 31×25 |
| `PlusLogo` Chain | (387,43) 4×4 |
| `PlusLogo` Capsule | (323,1) 35×41, (359,1) 59×41 |
| `PlusLogo` Smoke | (323+17i, 69) 16×16 |
| `Logo` Ribbon Center f1 | → f0's rect (1,194) 176×52 |

Also: both `.gif`s had index **255** (opaque olive `(59,75,59)` in the scene palette)
as sheet filler and cell grid lines, where RSDK only treats **index 0** as
transparent. Remapped 255→0 in both.

> **Tooling:** `docs/parse-sprite-bin.py` dumps a `.bin`. The scratch work also built
> a GIF LZW decoder/encoder and a `.bin` reader/writer (round-trip verified
> byte-identical before any edit) — rebuild them from the format notes in
> `Animation.cpp :: LoadSpriteAnimation` if needed again.

---

## Patch 14 — `UIButton.c`: NULL choice pointer on selection

**File:** `SonicMania/Objects/Menu/UIButton.c`

```sed
s|^        newChoice->active         = ACTIVE_NORMAL;$|
  if (newChoice)\n            newChoice->active = ACTIVE_NORMAL;|
```

Mirrors the guard its sibling `UIButton_SetChoiceSelectionWithCB` already has. This is
the Addendum Options exit crash — see `FINDINGS.md` §15.

---

## Patch 15 — `Drawing.hpp`: bounds-check `AddDrawListRef`

**File:** `RSDKv5/RSDK/Graphics/Drawing.hpp` (engine)

`AddDrawListRef` validated `drawGroup` but never `entityCount` against `ENTITY_COUNT`,
so it could write past `DrawList::entries[]`. `GetDrawListRefSlot` right below it does
check. `UIControl_MenuChangeButtonInit` calls it for every in-bounds entity on **every**
menu activation, on top of the normal per-frame pass.

```c
if (drawGroups[drawGroup].entityCount < ENTITY_COUNT)
    drawGroups[drawGroup].entries[drawGroups[drawGroup].entityCount++] = entityID;
```

---

## Patch 16 — `ManiaModeMenu.c`: load `AddendumOptions.bin` at boot

**File:** `SonicMania/Objects/Menu/ManiaModeMenu.c`

`Addendum_LoadOptions` was never called, so Addendum options reset every boot. See
`FINDINGS.md` §17.

```c
Addendum_LoadFile(Addendum_SaveLoadedCB);
Addendum_LoadOptionsData();   // sets addendumMods; LoadOptions bails without it
Addendum_LoadOptions(NULL);   // NULL callback is handled
```

> Order matters. `Addendum_LoadOptions` early-returns when `SaveGame->addendumMods` is
> NULL, and only `Addendum_LoadOptionsData()` sets it.

### Diagnostic probes — removed 2026-08-18

The temporary `SRTP >>` probes on the Addendum Options enter/exit paths were deleted
once the menus were confirmed stable. Re-add the same way if another hard crash needs
localising: bracket the suspect calls with `LogHelpers_Print`, read the last line
written. Once per menu action is fine; **never per frame** (`FINDINGS.md` §14).

---

## If another screen has blank buttons

Same signature. Find it with:

```bash
grep -rn "SetSpriteAnimation(UIWidgets->textFrames" SonicMania/Objects/
```

Any call site that sets `&button->animator` but never assigns `button->listID` /
`button->frameID` will render blank. Add the two lines using that call's animation
index and frame. Candidates not yet verified: save-deletion confirm, competition
exit prompt, Time Attack reset.

`TextEN.bin` animation indices (20 total):

```
0 Navigation      5 Sound          10 Pause Menu          15 Language
1 Main Menu       6 Controls       11 Leaderboards        16 Time Attack
2 Save Select     7 Extras         12 Competition         17 PC Menu
3 Options         8 Character Names 13 Competition Results 18 Data Options
4 Filter          9 Dialog Buttons 14 Secrets             19 Addendum Options
```

---

## Not patched (upstream defects)

- **"Addendum Options" crash** — newest in-dev feature; its assets
  (`Char-Add.gif`, `SaveSelectEN-Add.gif`) were never shipped in any release.
- **Title screen texture glitch** — persists even with matched `Logo`/`PlusLogo`
  pairs from master, so it's Addendum's own logo animation code. Cosmetic.
