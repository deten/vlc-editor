# VLC Editor

Quick mobile-style video clipping (trim, crop, slow-mo) launched from VLC.

## Use

1. Open a video in VLC and choose **View > Edit Video**. VLC pauses and the editor opens
   at the same spot.
2. **Trim**: drag the yellow handles on the timeline, or play to a spot and click
   **Start here** / **End here** (keys **I** / **O**). Click or drag the strip to scrub.
   Playing from inside the clip loops it; playing from outside it plays freely, so you
   can go past the current end to pick a later one.
3. **Crop**: click **Crop**, then drag the box or its corners. Pick a shape (Free, Original,
   16:9, 9:16, 1:1, 4:3, 3:4). Click **Crop** again to see the cropped result.
4. **Slow-mo**: click **Slow-mo**, drag the purple bar under the timeline (or **Whole clip**),
   and pick ½×, ¼× or ⅛×. The slow part is muted by default; choose *Slow the audio too*
   to keep it. *Smooth motion* adds in-between frames (much slower to save).
5. **Save** (Ctrl+S) writes `<name>_edit.mp4` (H.264/AAC) next to the original; the
   original is never changed.

Keys: Space play/pause · ←/→ ±1 s · Shift+←/→ ±0.1 s · I / O set start / end.

## Install on a PC (packaged)

Download `VLC-Editor-<version>.zip`, unzip it, and double-click **Install.cmd**.
Only 64-bit VLC 3.x is needed; Python and ffmpeg are included. **Uninstall.cmd** removes it.

## Run from source

Requirements: Windows, 64-bit VLC 3.x, Python 3.12, ffmpeg
(`winget install Python.Python.3.12 Gyan.FFmpeg`).

```powershell
powershell -ExecutionPolicy Bypass -File install.ps1
```

This creates `.venv`, writes `editor\config.json` (ffmpeg / ffprobe / VLC paths), and
installs the VLC extension pointing at this folder. Re-run it if the folder moves, and
restart VLC afterwards. To run the editor without VLC:
`.venv\Scripts\pythonw.exe editor\vlc_editor.py`.

## Build the package

```powershell
powershell -ExecutionPolicy Bypass -File build.ps1
```

Bundles the editor with PyInstaller, adds a shared ffmpeg build
([BtbN/FFmpeg-Builds](https://github.com/BtbN/FFmpeg-Builds)) and the installer scripts
from `packaging\`, and writes `dist\VLC-Editor-<version>.zip`.

## How it works

- `vlc_extension/vlc_editor.lua` is a VLC Lua extension. VLC extensions can only show
  simple dialogs and can't add toolbar buttons, so it just hands the current file and
  position to the editor.
- `editor/vlc_editor.py` (PySide6 + python-vlc) plays the video through the installed
  VLC's libvlc, rendering frames into Qt so the crop box can be drawn over them.
- Saving runs ffmpeg: `trim`/`crop` + `setpts`/`atempo` per segment, joined with `concat`.
  Phone rotation flags are honoured (crop works in the upright picture).
- Errors from the editor are written to `last_error.log` next to the program.
