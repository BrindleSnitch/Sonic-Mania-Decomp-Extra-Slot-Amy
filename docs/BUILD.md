# Build pipeline

No local Android toolchain exists on this device (no NDK, no SDK, tight RAM).
**All APK builds run on GitHub Actions.**

---

## Repo

`BrindleSnitch/Sonic-Mania-Decomp-Extra-Slot-Amy` — used purely as a **CI host**.
Its own contents are irrelevant; the workflows check out everything they need by name.

### Workflows

| File | Purpose |
|---|---|
| **`.github/workflows/addendum-android.yml`** | **THE ONE WE USE.** Builds Addendum as the `Game` module → `libGame.so`. Includes all source patches. |
| `.github/workflows/addendum-mod.yml` | Builds Addendum as a mod-logic `libAddendum.so`. Superseded — kept for reference. |

---

## Credentials

Builds are dispatched through the GitHub API, so you need a **fine-grained personal
access token** for this repository:

| Property | Value |
|---|---|
| Scope | this repository **only** |
| Permissions | Contents RW, Actions RW, Workflows RW, Metadata R |

Mint one at `github.com/settings/personal-access-tokens/new`. Administration is *not*
needed — Actions is already enabled on the repo.

> Keep it out of the repository. Export it in your shell (`export GH_TOKEN=...`) or use
> a credential store, and revoke it when you no longer need to build.

---

## Dispatching a build

```bash
export GH_TOKEN='<new token>'
R=BrindleSnitch/Sonic-Mania-Decomp-Extra-Slot-Amy

curl -s -X POST -H "Authorization: Bearer $GH_TOKEN" \
  -H "Accept: application/vnd.github+json" \
  -d '{"ref":"master","inputs":{"disable_plus":"false","abis":"arm64-v8a"}}' \
  "https://api.github.com/repos/$R/actions/workflows/addendum-android.yml/dispatches"
```

### Inputs

| Input | Value | Why |
|---|---|---|
| `disable_plus` | **`false`** | **Critical.** `true` triggers the Non-Plus lock screen + boot loop |
| `abis` | `arm64-v8a` | The Pixel's architecture; faster than building all four |

Build time ≈ 4–6 minutes.

---

## Retrieving the APK

```bash
RUN=<run id>
URL=$(curl -s -H "Authorization: Bearer $GH_TOKEN" \
  "https://api.github.com/repos/$R/actions/runs/$RUN/artifacts" \
  | python3 -c "import json,sys;print(json.load(sys.stdin)['artifacts'][0]['archive_download_url'])")
curl -sL -H "Authorization: Bearer $GH_TOKEN" -o out.zip "$URL"
# contains addendum_mania.apk
```

Deploy to `/sdcard/Download/SonicMania/addendum_patched.apk` and install.

**All our builds share one signing key** (`CN=Retro Engine`, SHA-256
`BE:55:F5:DC:...:65:FC:E9`, from `release-key.jks` committed in RSDKv5-Decompilation),
so they install over each other. Switching to/from JonasYT's port needs an uninstall.

---

## What the workflow does

1. Checks out `RSDKModding/RSDKv5-Decompilation` (engine, submodules recursive)
2. Checks out `KiaraGale/Sonic-Mania-Addendum` → `Sonic-Mania-Addendum/`
3. Checks out `RSDKv5-Example-Mods` and `RSDKv5-GameAPI`
4. Downloads libogg / libtheora into `dependencies/android`
5. Symlinks Addendum into `android/app/jni/Game` (so it compiles as `libGame.so`)
6. **Applies the source patches** (see `PATCHES.md`) — build fails if they don't apply
7. Gradle assembles a signed release APK

---

## Gotchas hit while building

- `actions/checkout` needs a **full 40-char SHA** or a ref name — abbreviated SHAs fail
- `codeload.github.com` returns **429** under load; just retry
- Heredocs inside YAML `run:` blocks break on indentation — use `sed`
- The classifier blocks overwriting `Data.rsdk` from this environment; the user must
  run that copy themselves via `!` or their file manager
