# Sonic Mania Addendum — Android port

A working Android build of **Sonic Mania Addendum** with **Amy playable**, **native
touch controls**, and readable menus — a combination the community generally documents
as unavailable on Android.

Built and debugged on a **Google Pixel 10 Pro XL** (Tensor G5, `arm64-v8a`, Android 16).

---

## What you need

| | |
|---|---|
| **Your own copy of Sonic Mania** | for `Data.rsdk` — **not distributed here**, see below |
| An arm64-v8a Android device | the APK is built for `arm64-v8a` only |
| ~500 MB free storage | mostly `Data.rsdk` |

### `Data.rsdk` is not included and never will be

`Data.rsdk` is Sonic Mania's retail asset archive. It is commercial data and is not
redistributable. You must supply it from a copy of the game you own — the PC (Steam)
release is the usual source.

**Use the December 2022 / RSDKv5c file.**

```
size 208,400,940   crc32 852ae394   <- CORRECT
size 208,368,695                    <- older RSDKv5a, causes sprite corruption + crashes
```

The older file produces "SONIC" rendering as a second "MANIA", corrupted sprites, and a
crash when entering a stage as Amy. If you hit those, you have the wrong one.

---

## Install

1. **Install the APK** from this repo's
   [Releases](../../releases). It is signed with the RSDKv5 decompilation's own
   `release-key.jks`, so it installs over other builds from this project but *not* over
   unrelated RSDKv5 APKs — uninstall those first.

2. **Build the data folder.** From a machine with `bash`, `curl` and `tar`:

   ```sh
   ./setup.sh /path/to/output/SonicMania
   ```

   This downloads Addendum's assets from the official
   [KiaraGale/Sonic-Mania-Addendum](https://github.com/KiaraGale/Sonic-Mania-Addendum)
   repository, applies the fixes in `overrides/`, and writes the mod layout and configs.
   It does **not** fetch `Data.rsdk`.

3. **Copy `Data.rsdk`** into that folder yourself.

4. **Put the folder on your device** anywhere you like — e.g.
   `/sdcard/Download/SonicMania/SonicMania/`. It does *not* have to be the engine default
   (`/sdcard/RSDK/v5/`).

5. **Launch the APK and pick that folder** when it asks.

Final layout:

```
SonicMania/
├── Data.rsdk              <- you supply this
├── Settings.ini
├── AddendumOptions.bin
└── mods/
    ├── modconfig.ini
    ├── AddendumAndroid/       flag mod — turns ON the touch controls
    ├── Sonic Mania Addendum/  fetched from upstream + overrides applied
    └── Shaders/               OGL shaders matched to the engine build
```

---

## Controls

Touch controls are drawn by Addendum's own HUD during gameplay (D-pad, jump, pause,
super, swap). **Menus have no on-screen buttons**, so this build adds gestures:

| Gesture | Action |
|---|---|
| **Two-finger tap** | Back / cancel |
| **Three-finger tap** | Y — cycles the sidekick on the save select, opens Secrets on NO SAVE |
| Tap | Confirm / select |

Tap an empty area — a finger landing on a menu entry may also trigger that entry.

---

## What's fixed relative to a naive build

Everything below is applied automatically — by the CI workflow (source patches, baked
into the APK) or by `setup.sh` (asset fixes).

**Engine (upstream RSDKv5 bugs, not port-specific):**

- **All 8 OpenGL shaders failed to compile** on GLES3 — `textureSize` collides with a
  GLES3 built-in, so the engine silently fell back to a passthrough shader. Cost colour
  FMV, screen dimming and pixel filtering.
- **`PrintLog` leaked a JNI local reference per call** — the local reference table
  overflows and the VM aborts the process. Any sustained logging killed the game.
- **`AddDrawListRef` had no bounds check** on `entityCount`, so it could write past
  `DrawList::entries[]`.

**Addendum (code/asset mismatches in the in-dev repo):**

- Addendum Options crashed on open — the scene ships no `Multiplayer Options` or
  `Secrets` control, and the code dereferenced them unguarded.
- `UIButton_SetChoiceSelection` dereferenced a pointer its own helper returns NULL for.
- Special stage results soft-locked — `SECONDGEMS_NONE` (the default) matched no branch.
- Title screen corruption — `PlusLogo.bin` and `PlusLogo.gif` are from different
  versions (33 px vs 38 px cell pitch), and `Logo.bin`'s ribbon-centre frame 1 pointed at
  blank sheet space.
- Addendum options never persisted — `Addendum_LoadOptions` is never called.
- Menus rendered blank — Addendum's dynamic text path doesn't work; patches force the
  pre-rendered artwork path.

Full write-ups: [`docs/FINDINGS.md`](../docs/FINDINGS.md),
[`docs/PATCHES.md`](../docs/PATCHES.md).

---

## Known issues

- **The Gameplay Options back prompt is inert.** Scene data problem — the prompt isn't
  adopted by its control. Use the two-finger tap.
- **Sidekick selection is limited to player 2.** Players 3/4 need real controllers; they
  follow player 2 and clear when it's set to none.
- **`Mania Android` mod is deliberately disabled.** It ships only the two title-logo
  files this port repairs; its one real change (TOUCH TO START) is merged into the
  Addendum sheet instead. Do not enable it.
- **Avoid the in-game mod manager** — it rewrites `modconfig.ini`, and load order
  matters (first listed wins asset conflicts).

---

## Credits

- **Sonic Mania Addendum** — [KiaraGale](https://github.com/KiaraGale/Sonic-Mania-Addendum)
- **RSDKv5 Decompilation** — [RSDKModding](https://github.com/RSDKModding/RSDKv5-Decompilation)
- **Shaders mod** — chuliRMG · **Mobile Friendly UI** — Sameer Raza
- **Touch to Start** artwork — from the *Mania Android* mod
- Android port fixes and packaging — this repo

Sonic the Hedgehog and Sonic Mania are trademarks of SEGA. This is an unofficial fan
project, is not affiliated with or endorsed by SEGA, and distributes no game data.
