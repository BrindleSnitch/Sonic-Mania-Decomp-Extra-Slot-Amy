#!/usr/bin/env bash
# Build a ready-to-use Sonic Mania Addendum data folder for the Android port.
#
#   ./setup.sh /path/to/output/SonicMania
#
# Fetches Addendum's assets from the official upstream repo, applies this port's fixes,
# and writes the mod layout + configs. Does NOT fetch Data.rsdk -- you supply that from
# your own copy of Sonic Mania (see README.md).
set -euo pipefail

DEST="${1:-}"
if [ -z "$DEST" ]; then
  echo "usage: $0 <output-dir>" >&2
  exit 2
fi
HERE="$(cd "$(dirname "$0")" && pwd)"
UPSTREAM="https://codeload.github.com/KiaraGale/Sonic-Mania-Addendum/tar.gz/refs/heads/master"
MODNAME="Sonic Mania Addendum"

for c in curl tar; do
  command -v "$c" >/dev/null || { echo "error: '$c' is required" >&2; exit 1; }
done

echo "==> output: $DEST"
mkdir -p "$DEST/mods"

TMP="$(mktemp -d)"
trap 'rm -rf "$TMP"' EXIT

echo "==> downloading Addendum assets from upstream"
# codeload returns 429 under load; retry a few times
for attempt in 1 2 3 4 5; do
  if curl -fsSL "$UPSTREAM" -o "$TMP/addendum.tar.gz"; then break; fi
  echo "    attempt $attempt failed, retrying..." >&2
  sleep $((attempt * 3))
  [ "$attempt" = 5 ] && { echo "error: download failed" >&2; exit 1; }
done

mkdir -p "$TMP/x"
tar -xzf "$TMP/addendum.tar.gz" -C "$TMP/x" --strip-components=1
[ -d "$TMP/x/$MODNAME" ] || { echo "error: upstream layout changed: '$MODNAME/' not found" >&2; exit 1; }

echo "==> installing mod: $MODNAME"
rm -rf "$DEST/mods/$MODNAME"
mkdir -p "$DEST/mods/$MODNAME"
cp -R "$TMP/x/$MODNAME/." "$DEST/mods/$MODNAME/"

# The APK compiles Addendum as libGame.so. If mod.ini still asks the loader to dlopen
# libAddendum.so it fails -- and Android cannot dlopen from /sdcard at all -- so NONE of
# the mod's 693 assets load. Presents as "Amy.bin not found" + a crash leaving the title.
echo "==> stripping DisableGameLogic / LogicFile from mod.ini"
if [ -f "$DEST/mods/$MODNAME/mod.ini" ]; then
  sed -i.bak -e '/^DisableGameLogic[[:space:]]*=/d' -e '/^LogicFile[[:space:]]*=/d' \
    "$DEST/mods/$MODNAME/mod.ini"
  rm -f "$DEST/mods/$MODNAME/mod.ini.bak"
fi

# Windows build of the mod logic. Android compiles Addendum into libGame.so instead, and
# cannot dlopen from /sdcard anyway -- so this is dead weight that only invites confusion.
rm -f "$DEST/mods/$MODNAME/Addendum.dll"

echo "==> applying port fixes (overrides/)"
cp -R "$HERE/overrides/." "$DEST/mods/"

echo "==> installing configs, flag mod and shaders"
cp -R "$HERE/data/." "$DEST/"

cat <<EOF

==> done: $DEST

Remaining step -- copy your own Data.rsdk into:
    $DEST/Data.rsdk

  Use the Dec-2022 / RSDKv5c file:
    size 208,400,940   crc32 852ae394

Then put the folder on your device, launch the APK, and select it.
EOF
