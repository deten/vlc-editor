VLC Editor - trim, crop and slow-mo videos from VLC
=====================================================

Requirements
  - Windows 10 or 11, 64-bit
  - VLC media player 3.x, 64-bit  (https://www.videolan.org, or: winget install VideoLAN.VLC)

Install
  1. Unzip this folder anywhere.
  2. Double-click Install.cmd. (No admin rights needed. Installs for the current user.)
  3. Restart VLC if it was open.

Use
  In VLC open a video, then choose View > Edit Video.
  You can also start "VLC Editor" from the Start menu and pick a file.

  Trim      drag the yellow handles, or play to a spot and click Start here / End here (I / O)
  Rotate    click Rotate to turn the picture 90° clockwise (click again for 180°, 270°)
  Crop      click Crop, drag the box; pick a shape (16:9, 9:16, 1:1 ...)
  Slow-mo   click Slow-mo, drag the purple bar under the timeline, pick 1/2x, 1/4x, 1/8x
  Save      writes <name>_edit.mp4 next to the original (the original is never changed)

  Keys: Space play/pause, Left/Right seek 1 s (Shift = 0.1 s), I / O start / end here, R rotate, Ctrl+S save

Uninstall
  Double-click Uninstall.cmd in this folder.

Installed files
  %LOCALAPPDATA%\Programs\VLC Editor            the program (includes ffmpeg)
  %APPDATA%\vlc\lua\extensions\vlc_editor.lua   the VLC menu item
  Start menu > VLC Editor

ffmpeg (GPL build from https://github.com/BtbN/FFmpeg-Builds) is included in the
program's ffmpeg folder with its licence.
