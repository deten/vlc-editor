VLC Editor for macOS - trim, crop and slow-mo videos from VLC
==============================================================

Requirements
  - macOS 12 or later
  - VLC media player 3.x in the Applications folder (https://www.videolan.org)
  - The right download for your Mac (Apple menu > About This Mac):
      "Chip: Apple M..."   -> VLC-Editor-...-macos-arm64.zip
      "Processor: Intel"   -> VLC-Editor-...-macos-intel.zip

Install
  1. Drag "VLC Editor" into the Applications folder.

  2. Let macOS open it. VLC Editor isn't from the App Store or a paid Apple
     developer account, so macOS blocks it the first time. Use ONE of these:

     A) Terminal (works on every macOS version). Open Terminal
        (Applications > Utilities), paste this line and press Return:

            xattr -dr com.apple.quarantine "/Applications/VLC Editor.app"

        Then open VLC Editor normally.

     B) macOS 15 Sequoia and later, without Terminal:
        - Double-click VLC Editor. A message says Apple could not verify it.
          Click "Done".
        - Open System Settings > Privacy & Security, scroll down to
          "VLC Editor was blocked..." and click "Open Anyway".
        - Enter your password, then click "Open Anyway" once more.

     C) macOS 14 Sonoma and earlier, without Terminal:
        - Control-click (or right-click) VLC Editor, choose "Open",
          then click "Open" in the message.

     You only need to do this once.

  3. VLC Editor opens with a file picker and adds itself to VLC.
     Quit VLC if it's open, start it again, then open a video and choose
     VLC > Extensions > Edit Video.

Use
  Trim      drag the yellow handles, or play to a spot and click Start here / End here (I / O)
  Rotate    click Rotate to turn the picture 90° clockwise (click again for 180°, 270°)
  Crop      click Crop, drag the box; pick a shape (16:9, 9:16, 1:1 ...)
  Slow-mo   click Slow-mo, drag the purple bar under the timeline, pick 1/2x, 1/4x, 1/8x
  Save      writes <name>_edit.mp4 next to the original (the original is never changed)

  Keys: Space play/pause, Left/Right seek 1 s (Shift = 0.1 s), I / O start / end here, R rotate, Cmd+S save

Uninstall
  Move "VLC Editor" from Applications to the Bin, and delete
  ~/Library/Application Support/org.videolan.vlc/lua/extensions/vlc_editor.lua

ffmpeg (static build from https://ffmpeg.martin-riedl.de) is included inside the app.
