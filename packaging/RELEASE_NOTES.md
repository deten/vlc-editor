Trim, crop, rotate and slow-mo videos from VLC. Needs VLC 3.x.

| System | File |
|---|---|
| Windows | `VLC-Editor-*-windows-x64.zip` |
| Mac (Apple chip) | `VLC-Editor-*-macos-arm64.zip` |
| Mac (Intel) | `VLC-Editor-*-macos-intel.zip` |
| Linux (Ubuntu 22.04+, Fedora 40+) | `VLC-Editor-*-linux-x86_64.tar.gz` |

### Windows
Unzip, run **Install.cmd**, restart VLC. Then **View > Edit Video**.

### Mac
1. Drag **VLC Editor** into Applications.
2. macOS blocks it the first time. Run this in Terminal:
   `xattr -dr com.apple.quarantine "/Applications/VLC Editor.app"`
   Or open the app, click **Done**, then **Open Anyway** in **System Settings > Privacy & Security**.
   On macOS 14 or earlier, Control-click the app and choose **Open**.
3. Open VLC Editor once, restart VLC. Then **VLC > Extensions > Edit Video**.

### Linux
1. Install VLC (not Flatpak or Snap):
   - Ubuntu: `sudo apt install vlc`
   - Fedora: enable [RPM Fusion](https://rpmfusion.org/Configuration), then
     `sudo dnf swap ffmpeg-free ffmpeg --allowerasing` and `sudo dnf install vlc vlc-plugins-freeworld`
2. `tar -xzf VLC-Editor-*-linux-x86_64.tar.gz && ./vlc-editor/install.sh`
3. Restart VLC. Then **View > Edit Video**.
