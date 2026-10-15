VLC Editor for Linux
====================

Works on Ubuntu 22.04+ and Fedora 40+.

Install VLC first (not the Flatpak or Snap version):
  Ubuntu:  sudo apt install vlc
  Fedora:  enable RPM Fusion (https://rpmfusion.org/Configuration), then
           sudo dnf swap ffmpeg-free ffmpeg --allowerasing
           sudo dnf install vlc vlc-plugins-freeworld

Install
  tar -xzf VLC-Editor-*-linux-x86_64.tar.gz
  ./vlc-editor/install.sh
  Then restart VLC.

Use
  In VLC, open a video and choose View > Edit Video.
  Or open "VLC Editor" from your applications menu.

  Clip      drag the yellow handles, or use Start here / End here. Click Clip when done.
  Rotate    turns the video 90° clockwise per click
  Crop      click Crop and drag the box. Click Crop again to see the result.
  Slow-mo   click Slow-mo, drag the purple bar, pick a speed
  Save      writes <name>_edit.mp4 next to the original

  Keys: Space play/pause, Left/Right seek, I / O start / end, R rotate, Ctrl+S save

If it won't open
  Ubuntu:  sudo apt install libxcb-cursor0
  Fedora:  sudo dnf install xcb-util-cursor

Uninstall
  ./vlc-editor/install.sh --uninstall

Includes ffmpeg (https://github.com/BtbN/FFmpeg-Builds).
