# VLC Editor installer (run by Install.cmd / Uninstall.cmd).
param([switch]$Uninstall)
$ErrorActionPreference = 'Stop'

$src = $PSScriptRoot
$dest = Join-Path $env:LOCALAPPDATA 'Programs\VLC Editor'
$extFile = Join-Path $env:APPDATA 'vlc\lua\extensions\vlc_editor.lua'
$shortcut = Join-Path ([Environment]::GetFolderPath('Programs')) 'VLC Editor.lnk'
$utf8 = New-Object System.Text.UTF8Encoding($false)

if (Get-Process 'VLC Editor' -ErrorAction SilentlyContinue) {
    throw 'VLC Editor is open - close it and run this again.'
}

if ($Uninstall) {
    Remove-Item $dest -Recurse -Force -ErrorAction SilentlyContinue
    Remove-Item $extFile, $shortcut -Force -ErrorAction SilentlyContinue
    Write-Host 'VLC Editor has been removed.'
    return
}

# needs 64-bit VLC
$vlcDir = $null
try { $vlcDir = (Get-ItemProperty 'HKLM:\SOFTWARE\VideoLAN\VLC' -ErrorAction Stop).InstallDir } catch {}
if (-not ($vlcDir -and (Test-Path (Join-Path $vlcDir 'libvlc.dll')))) { $vlcDir = "$env:ProgramFiles\VideoLAN\VLC" }
if (-not (Test-Path (Join-Path $vlcDir 'libvlc.dll'))) {
    if (Test-Path "${env:ProgramFiles(x86)}\VideoLAN\VLC\libvlc.dll") {
        throw 'Only 32-bit VLC is installed. Install the 64-bit VLC from https://www.videolan.org (or: winget install VideoLAN.VLC) and run this again.'
    }
    throw 'VLC is not installed. Install it from https://www.videolan.org (or: winget install VideoLAN.VLC) and run this again.'
}

Write-Host "Installing to $dest ..."
if (Test-Path $dest) { Remove-Item $dest -Recurse -Force }
New-Item -ItemType Directory -Force $dest | Out-Null
Copy-Item (Join-Path $src 'app\*') $dest -Recurse -Force
# unblock downloaded files
Get-ChildItem $dest -Recurse -File | Unblock-File

$exe = Join-Path $dest 'VLC Editor.exe'
$launchPath = $exe
if ($launchPath -match '[^\x00-\x7F]') {
    # short path for non-ASCII user names
    $launchPath = (New-Object -ComObject Scripting.FileSystemObject).GetFile($exe).ShortPath
}
New-Item -ItemType Directory -Force (Split-Path $extFile) | Out-Null
$lua = [IO.File]::ReadAllText((Join-Path $src 'vlc_editor.lua')).Replace('@LAUNCH@', "`"$launchPath`"")
[IO.File]::WriteAllText($extFile, $lua, $utf8)

$link = (New-Object -ComObject WScript.Shell).CreateShortcut($shortcut)
$link.TargetPath = $exe
$link.WorkingDirectory = $dest
$link.Description = 'Trim, crop and slow-mo videos'
$link.Save()

Write-Host ''
Write-Host 'VLC Editor is installed.'
Write-Host '  In VLC: open a video, then View > Edit Video.'
Write-Host '  Or start "VLC Editor" from the Start menu and pick a file.'
if (Get-Process vlc -ErrorAction SilentlyContinue) {
    Write-Host ''
    Write-Host 'VLC is running - close and reopen it so the Edit Video menu item appears.'
}
