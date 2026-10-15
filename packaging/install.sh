#!/usr/bin/env bash
# VLC Editor installer for Linux.
#   ./install.sh               install / update
#   ./install.sh --uninstall   remove
set -euo pipefail
HERE=$(cd "$(dirname "$0")" && pwd)
DATA=${XDG_DATA_HOME:-$HOME/.local/share}
DEST=$DATA/vlc-editor
DESKTOP=$DATA/applications/vlc-editor.desktop
EXT=$DATA/vlc/lua/extensions/vlc_editor.lua

if [ "${1:-}" = "--uninstall" ]; then
    rm -rf "$DEST" "$DESKTOP" "$EXT"
    echo "VLC Editor has been removed."
    exit 0
fi

LDCONFIG=$(command -v ldconfig || echo /sbin/ldconfig)
has_lib() { "$LDCONFIG" -p 2>/dev/null | grep -q "$1"; }

# needs the system VLC
if ! has_lib 'libvlc\.so\.5'; then
    echo "VLC is not installed (or only as a Flatpak/Snap, which other programs can't use)."
    echo "Install it from your distribution, then run this again:"
    echo "  Ubuntu / Debian:  sudo apt install vlc"
    echo "  Fedora:           enable RPM Fusion (https://rpmfusion.org/Configuration), then"
    echo "                    sudo dnf swap ffmpeg-free ffmpeg --allowerasing"
    echo "                    sudo dnf install vlc vlc-plugins-freeworld"
    exit 1
fi
if command -v flatpak >/dev/null 2>&1 && flatpak info org.videolan.VLC >/dev/null 2>&1; then
    echo "Note: the Flatpak VLC can't show the Edit Video menu item. Use the distribution's VLC"
    echo "(the 'VLC media player' that isn't the Flatpak one), or open VLC Editor from the app menu."
fi

echo "Installing to $DEST ..."
rm -rf "$DEST"
mkdir -p "$DEST" "$(dirname "$DESKTOP")"
cp -R "$HERE/app/." "$DEST/"
"$DEST/vlc-editor" --install-extension >/dev/null

cat > "$DESKTOP" <<EOF
[Desktop Entry]
Type=Application
Name=VLC Editor
Comment=Trim, crop and slow-mo videos
Exec="$DEST/vlc-editor" %f
Icon=vlc
Terminal=false
Categories=AudioVideo;Video;AudioVideoEditing;
MimeType=video/mp4;video/quicktime;video/x-matroska;video/webm;video/x-msvideo;video/3gpp;
EOF
command -v update-desktop-database >/dev/null 2>&1 && update-desktop-database "$(dirname "$DESKTOP")" || true

echo
echo "VLC Editor is installed."
echo "  In VLC: open a video, then View > Edit Video (restart VLC first if it is open)."
echo "  Or start \"VLC Editor\" from your applications menu."
# Qt needs libxcb-cursor on X11
if [ "${XDG_SESSION_TYPE:-}" != wayland ] && ! has_lib 'libxcb-cursor\.so\.0'; then
    echo
    echo "If VLC Editor doesn't open, install this library and try again:"
    echo "  Ubuntu / Debian:  sudo apt install libxcb-cursor0"
    echo "  Fedora:           sudo dnf install xcb-util-cursor"
fi
