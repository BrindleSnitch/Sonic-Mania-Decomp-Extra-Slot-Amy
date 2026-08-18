# Sonic Mania Addendum — Android (Pixel 10 Pro XL)

Working notes for resuming this project in a new session.
Last updated: **2026-08-17**

---

## Goal

Run **Sonic Mania Addendum** (KiaraGale) on Android with all three of:

1. **Amy playable** as a 6th character (the original ask)
2. **Native touch controls** (no secondary software — explicit user requirement)
3. **Working, readable menus**

The community position is that this combination is **not possible** — Addendum is a
source edit replacing `Game.dll`, so it cannot use the `ManiaTouchControls` mod.
We achieved it by **building Addendum from source with targeted patches**.

---

## Current state

| Feature | Status |
|---|---|
| Amy playable, full moveset | ✅ |
| Native touch controls (rendered + working) | ✅ |
| Main menu / options / save select text | ✅ |
| Pause menu labels | ✅ |
| Confirmation dialog buttons (Yes/No) | ✅ confirmed 2026-08-17 |
| Gameplay stability | ✅ |
| OpenGL shaders compiling | ✅ **confirmed on hardware 2026-08-17** (patch 5) |
| **"Addendum Options" opens** | ✅ **confirmed 2026-08-17** (patches 6–7) |
| Backing out of Addendum submenus | ✅ **confirmed 2026-08-17** — 2-finger tap (patch 9) |
| Special stage results soft-lock | ✅ **confirmed 2026-08-17** (patch 8) |
| Secrets menu reachable | ✅ **confirmed** — 3-finger tap (patch 9) |
| **Sidekick / character pairs per save** | 🔄 wired up (patch 10), **awaiting playtest** — see `FINDINGS.md` §11 |
| **Title screen textures** | ✅ **confirmed 2026-08-18** — rebuilt `PlusLogo.bin`/`Logo.bin` |
| Addendum Options crashes | ✅ **confirmed 2026-08-18** (patches 12–15) |
| 100% save files restored | ✅ 6 chars, all gems, all unlocks — `SETUP.md` |
| Addendum options persist across boots | ✅ **confirmed 2026-08-18** (patch 16) |
| "Touch to Start" title prompt | 🔄 spliced into Addendum's sheet, **awaiting playtest** |
| Mobile-friendly UI button icons | 🔄 mod enabled, **awaiting playtest** |
| Pre-filled save files | ⚠️ parked in `_port_saves/` (format differs) |

**Installed APK:** `/sdcard/Download/SonicMania/addendum_patched.apk`

**Every menu/input defect is closed.** This build achieves the stated goal in full:
Amy playable, native touch controls rendered and working, and every menu surface
readable — a combination the community documents as unavailable on Android.

**2026-08-17 evening session.** Two rounds of work beyond the original goal:

1. **Shaders (patch 5)** — all 8 OpenGL shaders had been failing silently, costing
   colour FMV, screen dimming and pixel filtering. Fixed and **confirmed on
   hardware**. See `FINDINGS.md` §7.
2. **Menus (patches 6–7)** — "Addendum Options" never worked because the shipped
   Menu scene is missing two `UIControl`s the code dereferences unguarded. This is
   the screen holding SPINDASH / MOVESET / PEELOUT / LIFE SYSTEM / SHIELD options.
   Fixed, **awaiting playtest**. See `FINDINGS.md` §8.

---

## The three artifacts that matter

| Thing | Where | Note |
|---|---|---|
| Our patched APK | `Download/SonicMania/addendum_patched.apk` | **current build** |
| Reference Android port | `Download/SonicMania/addendum_port.apk` | JonasYT's, older Addendum, menus work, **no touch** |
| Original stock engine | `Download/SonicMania/RSDKv5_1.1.1.apk` | vanilla Mania decomp |

All three share **no** signing key with each other except our own builds, which are
mutually installable. Switching between our build and the port requires an uninstall.

---

## Quick resume checklist

1. Read `FINDINGS.md` first — it prevents re-walking several dead ends
2. `BUILD.md` — how to rebuild the APK via GitHub Actions
3. `PATCHES.md` — the exact source patches and why each exists
4. `SETUP.md` — device file layout, backups, `Data.rsdk` identity
5. `BUILD.md` — credentials needed to dispatch a build (mint your own; none stored here)
   - `parse-sprite-bin.py` — dumps a `.bin` sprite animation's names, frame rects and
     sheet dimensions. Written for `FINDINGS.md` §12; use it before blaming sprite art.
6. `WORKING-NOTES.md` — user requirements and process lessons

---

## Environment

- Google Pixel 10 Pro XL, arm64-v8a
- Claude Code runs in Ubuntu via proot-distro under Termux
- **No local Android build tooling** — all APK builds run on GitHub Actions
- Game folder: `/sdcard/Download/SonicMania/SonicMania/`
  (the app lets you choose this folder; it is *not* the default `/sdcard/RSDK/v5/`)
