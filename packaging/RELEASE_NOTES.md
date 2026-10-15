Trim, crop and slow-mo videos straight from VLC, on Windows, macOS and Linux.

| System | Download |
|---|---|
| Windows 10/11 (64-bit) | `VLC-Editor-*-windows-x64.zip` |
| Mac with Apple chip (M1 or later) | `VLC-Editor-*-macos-arm64.zip` |
| Mac with Intel processor | `VLC-Editor-*-macos-intel.zip` |
| Linux: Ubuntu 22.04+, Fedora 40+ | `VLC-Editor-*-linux-x86_64.tar.gz` |

All versions need VLC 3.x installed. Python and ffmpeg are included.

### Windows
1. Unzip, then double-click **Install.cmd** (no admin rights needed).
2. Restart VLC, open a video, then choose **View > Edit Video**.

### macOS
1. Unzip and drag **VLC Editor** into **Applications**.
2. macOS blocks apps that aren't from a paid Apple developer account the first time. Either:
   - open **Terminal** and run
     `xattr -dr com.apple.quarantine "/Applications/VLC Editor.app"`, or
   - **macOS 15+:** double-click the app, click **Done**, then go to **System Settings > Privacy & Security**,
     click **Open Anyway** next to "VLC Editor was blocked", and confirm, or
   - **macOS 14 and earlier:** Control-click the app, choose **Open**, then **Open**.
3. Open VLC Editor once (it adds itself to VLC), restart VLC, open a video, then choose
   **VLC > Extensions > Edit Video**.

### Linux (Ubuntu and Fedora)
1. Install VLC from your distribution, not Flatpak/Snap:
   - Ubuntu: `sudo apt install vlc`
   - Fedora: enable [RPM Fusion](https://rpmfusion.org/Configuration), then
     `sudo dnf swap ffmpeg-free ffmpeg --allowerasing` and `sudo dnf install vlc vlc-plugins-freeworld`
2. `tar -xzf VLC-Editor-*-linux-x86_64.tar.gz && ./vlc-editor/install.sh`
3. Restart VLC, open a video, then choose **View > Edit Video**.

### Features
- Trim with drag handles or *Start here* / *End here* (I / O)
- Rotate 90° clockwise per click
- Crop with free or fixed shapes (16:9, 9:16, 1:1, 4:3 ...)
- Slow-mo (1/2x, 1/4x, 1/8x) for part or all of the clip, audio muted or slowed
- Saves `<name>_edit.mp4` next to the original
