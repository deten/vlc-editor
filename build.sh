#!/usr/bin/env bash
# Builds the macOS or Linux package into dist/ (run on the system you are building for):
#   macOS: dist/VLC-Editor-<version>-macos-arm64.zip / -macos-intel.zip   (VLC Editor.app)
#   Linux: dist/VLC-Editor-<version>-linux-x86_64.tar.gz                  (folder with install.sh)
# Uses .venv/bin/python (or $PYTHON) with requirements.txt installed.
set -euo pipefail
ROOT=$(cd "$(dirname "$0")" && pwd)
VERSION=$(head -n1 "$ROOT/VERSION" | tr -d '[:space:]')
PY=${PYTHON:-$ROOT/.venv/bin/python}
BUILD=$ROOT/build
CACHE=$BUILD/cache
DIST=$ROOT/dist
FF=$BUILD/ffmpeg-bin
mkdir -p "$CACHE" "$DIST"
rm -rf "$FF" "$BUILD/stage" && mkdir -p "$FF"

# download once into the cache; verify the checksum when one is given
fetch() {
    local url=$1 sum=$2 dest=$3
    [ -f "$dest" ] || curl -fsSL -o "$dest" "$url"
    if [ -n "$sum" ]; then
        echo "$sum  $dest" | shasum -a 256 -c - >/dev/null || { rm -f "$dest"; echo "checksum mismatch: $url"; exit 1; }
    fi
}

# ffmpeg 9.0.2 builds: martin-riedl.de (macOS, signed static) / BtbN (Linux, static GPL)
case "$(uname -s)-$(uname -m)" in
    Darwin-arm64)
        PLATFORM=macos-arm64
        MR=arm64/1789931890_9.0.2
        SUMS="ffmpeg=c8ed4c4e6978a03c485edbfe4e0a5dc2380f8a30bba5150531b31b094492d924 ffprobe=fcbe839537485eaee7a7a8bc5cbc0f90d53617e80943e8a5b2e31cb851197ea6" ;;
    Darwin-x86_64)
        PLATFORM=macos-intel
        MR=amd64/1789931006_9.0.2
        SUMS="ffmpeg=7c6b4125b191cbf773832dc51f424cf2b6bb7da43007d1e066f95909e47cacd4 ffprobe=2322438ed2f6319a691291b247d09c69dcaa3a982460d1f269a7e1af335cfdfd" ;;
    Linux-x86_64)
        PLATFORM=linux-x86_64 ;;
    *)
        echo "Unsupported system: $(uname -s) $(uname -m)"; exit 1 ;;
esac

if [ "$(uname -s)" = Darwin ]; then
    for entry in $SUMS; do
        tool=${entry%%=*}
        fetch "https://ffmpeg.martin-riedl.de/download/macos/$MR/$tool.zip" "${entry#*=}" "$CACHE/$PLATFORM-$tool.zip"
        unzip -o -q "$CACHE/$PLATFORM-$tool.zip" -d "$FF"
    done
else
    fetch "https://github.com/BtbN/FFmpeg-Builds/releases/download/latest/ffmpeg-n9.0-latest-linux64-gpl-9.0.tar.xz" "" \
        "$CACHE/ffmpeg-linux.tar.xz"
    rm -rf "$BUILD/ffmpeg-linux" && mkdir -p "$BUILD/ffmpeg-linux"
    tar -xJf "$CACHE/ffmpeg-linux.tar.xz" -C "$BUILD/ffmpeg-linux" --strip-components=1
    cp "$BUILD/ffmpeg-linux/bin/ffmpeg" "$BUILD/ffmpeg-linux/bin/ffprobe" "$FF/"
    cp "$BUILD/ffmpeg-linux/LICENSE.txt" "$FF/LICENSE.txt" 2>/dev/null || true
fi
chmod +x "$FF/ffmpeg" "$FF/ffprobe"

# editor -> app bundle (Python + Qt + ffmpeg inside; libvlc comes from the installed VLC)
NAME="VLC Editor"
[ "$(uname -s)" = Linux ] && NAME=vlc-editor
"$PY" -m pip install --quiet --disable-pip-version-check pyinstaller
EXTRA=()
[ -f "$FF/LICENSE.txt" ] && EXTRA+=(--add-data "$FF/LICENSE.txt:ffmpeg")
"$PY" -m PyInstaller --noconfirm --clean --windowed --name "$NAME" \
    --distpath "$BUILD/pyinstaller/dist" --workpath "$BUILD/pyinstaller/work" --specpath "$BUILD/pyinstaller" \
    --osx-bundle-identifier io.github.deten.vlc-editor \
    --add-binary "$FF/ffmpeg:ffmpeg" --add-binary "$FF/ffprobe:ffmpeg" \
    --add-data "$ROOT/vlc_extension/vlc_editor.lua:." \
    ${EXTRA[@]+"${EXTRA[@]}"} \
    --exclude-module tkinter --exclude-module unittest \
    "$ROOT/editor/vlc_editor.py"

STAGE=$BUILD/stage
if [ "$(uname -s)" = Darwin ]; then
    mkdir -p "$STAGE"
    ditto "$BUILD/pyinstaller/dist/VLC Editor.app" "$STAGE/VLC Editor.app"
    cp "$ROOT/packaging/README-macos.txt" "$STAGE/README.txt"
    OUT=$DIST/VLC-Editor-$VERSION-$PLATFORM.zip
    rm -f "$OUT"
    ditto -c -k "$STAGE" "$OUT"
else
    PKG=$STAGE/vlc-editor
    mkdir -p "$PKG"
    cp -R "$BUILD/pyinstaller/dist/vlc-editor" "$PKG/app"
    cp "$ROOT/packaging/install.sh" "$PKG/install.sh"
    chmod +x "$PKG/install.sh"
    cp "$ROOT/packaging/README-linux.txt" "$PKG/README.txt"
    OUT=$DIST/VLC-Editor-$VERSION-$PLATFORM.tar.gz
    tar -czf "$OUT" -C "$STAGE" vlc-editor
fi
echo "$OUT  ($(du -h "$OUT" | cut -f1))"
