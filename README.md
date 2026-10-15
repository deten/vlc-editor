# VLC Editor

Quick mobile-style video clipping (trim, crop, slow-mo) launched from VLC.

![Trimming a clip](docs/screenshots/trim.png)

| Crop | Slow-mo |
|------|---------|
| ![Cropping to 9:16](docs/screenshots/crop.png) | ![Slowing part of the clip to 1/4 speed](docs/screenshots/slowmo.png) |

## Use

1. Open a video in VLC and choose **View > Edit Video** (macOS: **VLC > Extensions >
   Edit Video**). VLC pauses and the editor opens at the same spot.
2. **Trim**: drag the yellow handles on the timeline, or play to a spot and click
   **Start here** / **End here** (keys **I** / **O**). Click or drag the strip to scrub.
   Playing from inside the clip loops it; playing from outside it plays freely, so you
   can go past the current end to pick a later one.
3. **Rotate**: each click on **⟳ Rotate** (key **R**) turns the picture 90° clockwise;
   click twice for 180°, three times for 90° anticlockwise.
4. **Crop**: click **Crop**, then drag the box or its corners. Pick a shape (Free, Original,
   16:9, 9:16, 1:1, 4:3, 3:4). Click **Crop** again to see the cropped result. The crop
   box turns with the picture when you rotate.
5. **Slow-mo**: click **Slow-mo**, drag the purple bar under the timeline (or **Whole clip**),
   and pick ½×, ¼× or ⅛×. The slow part is muted by default; choose *Slow the audio too*
   to keep it. *Smooth motion* adds in-between frames (much slower to save).
6. **Save** (Ctrl+S) writes `<name>_edit.mp4` (H.264/AAC) next to the original; the
   original is never changed.

Keys: Space play/pause · ←/→ ±1 s · Shift+←/→ ±0.1 s · I / O set start / end · R rotate.

## Install

Download the package for your system from
[Releases](https://github.com/deten/vlc-editor/releases). Every version needs VLC 3.x;
Python and ffmpeg are included.

| System | Download | Install |
|---|---|---|
| Windows 10/11 (64-bit) | `…-windows-x64.zip` | Unzip, double-click **Install.cmd** |
| Mac with Apple chip | `…-macos-arm64.zip` | Drag **VLC Editor** to Applications, then see below |
| Mac with Intel processor | `…-macos-intel.zip` | Drag **VLC Editor** to Applications, then see below |
| Linux (Ubuntu 22.04+, Fedora 40+) | `…-linux-x86_64.tar.gz` | `tar -xzf …tar.gz && ./vlc-editor/install.sh` |

Then restart VLC and choose **View > Edit Video** (macOS: **VLC > Extensions > Edit Video**).

**macOS:** the app isn't signed with a paid Apple developer account, so macOS blocks it
the first time. Either run
`xattr -dr com.apple.quarantine "/Applications/VLC Editor.app"` in Terminal, or
double-click the app, click **Done**, and choose **Open Anyway** in
**System Settings > Privacy & Security** (macOS 14 and earlier: Control-click the app >
**Open**). Open it once so it can add itself to VLC.

**Linux:** use VLC from your distribution, not Flatpak/Snap (they're sandboxed).
Ubuntu: `sudo apt install vlc`. Fedora: enable [RPM Fusion](https://rpmfusion.org/Configuration),
then `sudo dnf swap ffmpeg-free ffmpeg --allowerasing` and
`sudo dnf install vlc vlc-plugins-freeworld` (needed to play phone H.264/HEVC video).

## Run from source

**Windows:** needs 64-bit VLC 3.x, Python 3.12 and ffmpeg
(`winget install Python.Python.3.12 Gyan.FFmpeg`), then:

```powershell
powershell -ExecutionPolicy Bypass -File install.ps1
```

This creates `.venv`, writes `editor\config.json` (ffmpeg / ffprobe / VLC paths), and
installs the VLC extension pointing at this folder. Re-run it if the folder moves, and
restart VLC afterwards.

**macOS / Linux:** needs VLC 3.x, Python 3.10+ and ffmpeg on the PATH, then:

```sh
python3 -m venv .venv
.venv/bin/pip install -r requirements.txt
.venv/bin/python editor/vlc_editor.py --install-extension
```

Run the editor without VLC with `editor/vlc_editor.py` (it asks for a file).

## Build the packages

- Windows: `powershell -ExecutionPolicy Bypass -File build.ps1`
- macOS / Linux: `./build.sh` (on the system you're building for)

Each bundles the editor with PyInstaller, adds ffmpeg
([BtbN/FFmpeg-Builds](https://github.com/BtbN/FFmpeg-Builds) on Windows/Linux,
[martin-riedl.de](https://ffmpeg.martin-riedl.de) on macOS) and the installer files from
`packaging/`, and writes the package to `dist/`. The version comes from `VERSION`.

Pushing a `v*` tag runs `.github/workflows/release.yml`, which builds all four packages,
self-tests each one against a real VLC (`--selftest`), checks the Linux package on Fedora
and Ubuntu 24.04, and publishes the release.

## How it works

- `vlc_extension/vlc_editor.lua` is a VLC Lua extension. VLC extensions can only show
  simple dialogs and can't add toolbar buttons, so it just hands the current file and
  position to the editor.
- `editor/vlc_editor.py` (PySide6 + python-vlc) plays the video through the installed
  VLC's libvlc, rendering frames into Qt so the crop box can be drawn over them.
- Saving runs ffmpeg: `trim`/`crop` + `setpts`/`atempo` per segment, joined with `concat`.
  Phone rotation flags are honoured (crop works in the upright picture).
- Errors from the editor are written to `last_error.log`: next to the program on Windows,
  in `~/Library/Logs/VLC Editor` on macOS, and in `~/.local/state/vlc-editor` on Linux.
