# Builds the Windows package into dist\.
# Run: powershell -ExecutionPolicy Bypass -File build.ps1
$ErrorActionPreference = 'Stop'
$version = (Get-Content (Join-Path $PSScriptRoot 'VERSION') -TotalCount 1).Trim()
$root = $PSScriptRoot
$py = Join-Path $root '.venv\Scripts\python.exe'
$build = Join-Path $root 'build'
$pyi = Join-Path $build 'pyinstaller'
$stage = Join-Path $build 'VLC-Editor'
$dist = Join-Path $root 'dist'
$ffmpegZip = Join-Path $build 'cache\ffmpeg-shared.zip'
$ffmpegUrl = 'https://github.com/BtbN/FFmpeg-Builds/releases/download/latest/ffmpeg-n9.0-latest-win64-gpl-shared-9.0.zip'

# 1. Editor
& $py -m pip install --quiet --disable-pip-version-check pyinstaller
& $py -m PyInstaller --noconfirm --clean --windowed --name 'VLC Editor' `
    --distpath (Join-Path $pyi 'dist') --workpath (Join-Path $pyi 'work') --specpath $pyi `
    --exclude-module tkinter --exclude-module unittest `
    (Join-Path $root 'editor\vlc_editor.py')
if ($LASTEXITCODE) { throw 'PyInstaller failed' }

if (Test-Path $stage) { Remove-Item $stage -Recurse -Force }
New-Item -ItemType Directory -Force $stage | Out-Null
$app = Join-Path $stage 'app'
Copy-Item (Join-Path $pyi 'dist\VLC Editor') $app -Recurse
# not needed, saves ~20 MB
Get-ChildItem $app -Recurse -Filter 'opengl32sw.dll' | Remove-Item -Force

# 2. ffmpeg
if (-not (Test-Path $ffmpegZip)) {
    New-Item -ItemType Directory -Force (Split-Path $ffmpegZip) | Out-Null
    Write-Host "Downloading $ffmpegUrl"
    Invoke-WebRequest $ffmpegUrl -OutFile $ffmpegZip -UseBasicParsing
}
$ffx = Join-Path $build 'cache\ffmpeg-x'
if (-not (Get-ChildItem $ffx -Recurse -Filter ffmpeg.exe -ErrorAction SilentlyContinue)) {
    Expand-Archive $ffmpegZip $ffx -Force
}
$ffbin = (Get-ChildItem $ffx -Recurse -Filter ffmpeg.exe | Select-Object -First 1).DirectoryName
$ffdest = Join-Path $app 'ffmpeg'
New-Item -ItemType Directory -Force $ffdest | Out-Null
Copy-Item (Join-Path $ffbin '*') $ffdest -Exclude 'ffplay.exe'
Copy-Item (Join-Path (Split-Path $ffbin) 'LICENSE.txt') (Join-Path $ffdest 'LICENSE.txt') -ErrorAction SilentlyContinue

# 3. Installer files
Copy-Item (Join-Path $root 'vlc_extension\vlc_editor.lua') $stage
Copy-Item (Join-Path $root 'packaging\setup.ps1') $stage
Copy-Item (Join-Path $root 'packaging\README-windows.txt') (Join-Path $stage 'README.txt')
foreach ($cmd in 'Install.cmd', 'Uninstall.cmd') {
    # batch files need CRLF
    $text = [IO.File]::ReadAllText((Join-Path $root "packaging\$cmd")) -replace "`r?`n", "`r`n"
    [IO.File]::WriteAllText((Join-Path $stage $cmd), $text, (New-Object System.Text.ASCIIEncoding))
}

# 4. Zip
New-Item -ItemType Directory -Force $dist | Out-Null
$zip = Join-Path $dist "VLC-Editor-$version-windows-x64.zip"
if (Test-Path $zip) { Remove-Item $zip -Force }
Compress-Archive -Path $stage -DestinationPath $zip -CompressionLevel Optimal
'{0}  ({1:N0} MB)' -f $zip, ((Get-Item $zip).Length / 1MB)
