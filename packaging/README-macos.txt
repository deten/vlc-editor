VLC Editor for Mac
==================

Needs VLC 3.x in Applications (https://www.videolan.org).
Use the arm64 download for Apple chips (M1 and later), intel for Intel Macs.

Install
  1. Drag "VLC Editor" into Applications.

  2. macOS blocks it the first time. Do one of these:

     - In Terminal, run:
         xattr -dr com.apple.quarantine "/Applications/VLC Editor.app"

     - macOS 15 or later: open the app, click Done, then go to
       System Settings > Privacy & Security and click Open Anyway.

     - macOS 14 or earlier: Control-click the app and choose Open.

  3. Open VLC Editor once, then restart VLC.

Use
  In VLC, open a video and choose VLC > Extensions > Edit Video.

  Clip      drag the yellow handles, or use Start here / End here. Click Clip when done.
  Rotate    turns the video 90° clockwise per click
  Crop      click Crop and drag the box. Click Crop again to see the result.
  Slow-mo   click Slow-mo, drag the purple bar, pick a speed
  Save      writes <name>_edit.mp4 next to the original

  Keys: Space play/pause, Left/Right seek, I / O start / end, R rotate, Cmd+S save

Uninstall
  Move VLC Editor to the Bin, and delete
  ~/Library/Application Support/org.videolan.vlc/lua/extensions/vlc_editor.lua

Includes ffmpeg (https://ffmpeg.martin-riedl.de).
