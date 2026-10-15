VLC Editor for Linux - trim, crop and slow-mo videos from VLC
=============================================================

Works on Ubuntu 22.04+ and Fedora 40+ (64-bit Intel/AMD), and other distributions
of similar age.

Requirements
  VLC 3.x installed from your distribution - not the Flatpak or Snap version
  (those are sandboxed, so VLC Editor can't use them or add the menu item):

    Ubuntu / Debian:  sudo apt install vlc
    Fedora:           enable RPM Fusion (https://rpmfusion.org/Configuration), then
                      sudo dnf swap ffmpeg-free ffmpeg --allowerasing
                      sudo dnf install vlc vlc-plugins-freeworld
                      (RPM Fusion lets VLC play phone videos: H.264 / HEVC)

Install
  tar -xzf VLC-Editor-*-linux-x86_64.tar.gz
  ./vlc-editor/install.sh

  No sudo needed; it installs for your user. Restart VLC if it was open.

Use
  In VLC: open a video, then View > Edit Video.
  Or start "VLC Editor" from your applications menu and pick a file.

  Trim      drag the yellow handles, or play to a spot and click Start here / End here (I / O)
  Rotate    click Rotate to turn the picture 90° clockwise (click again for 180°, 270°)
  Crop      click Crop, drag the box; pick a shape (16:9, 9:16, 1:1 ...)
  Slow-mo   click Slow-mo, drag the purple bar under the timeline, pick 1/2x, 1/4x, 1/8x
  Save      writes <name>_edit.mp4 next to the original (the original is never changed)

  Keys: Space play/pause, Left/Right seek 1 s (Shift = 0.1 s), I / O start / end here, R rotate, Ctrl+S save

If it doesn't open
  On X11 desktops Qt needs one extra library:
    Ubuntu / Debian:  sudo apt install libxcb-cursor0
    Fedora:           sudo dnf install xcb-util-cursor
  Errors are written to ~/.local/state/vlc-editor/last_error.log

Uninstall
  ./vlc-editor/install.sh --uninstall

Installed files
  ~/.local/share/vlc-editor                          the program (includes ffmpeg)
  ~/.local/share/vlc/lua/extensions/vlc_editor.lua   the VLC menu item
  ~/.local/share/applications/vlc-editor.desktop     the applications-menu entry

ffmpeg (static GPL build from https://github.com/BtbN/FFmpeg-Builds) is included.
