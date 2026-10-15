# Sets up VLC Editor from source.
# Run: powershell -ExecutionPolicy Bypass -File install.ps1
$ErrorActionPreference = 'Stop'
$root = $PSScriptRoot
$venvPy = Join-Path $root '.venv\Scripts\python.exe'
$pythonw = Join-Path $root '.venv\Scripts\pythonw.exe'
$editor = Join-Path $root 'editor\vlc_editor.py'
$utf8 = New-Object System.Text.UTF8Encoding($false)

function Find-Exe($name, $patterns) {
    $cmd = Get-Command $name -ErrorAction SilentlyContinue
    if ($cmd) { return $cmd.Source }
    foreach ($p in $patterns) {
        $hit = Get-ChildItem $p -ErrorAction SilentlyContinue | Select-Object -First 1
        if ($hit) { return $hit.FullName }
    }
    return $null
}

# 1. Python environment
if (-not (Test-Path $venvPy)) {
    $basePy = Find-Exe 'python3.12' @("$env:LOCALAPPDATA\Programs\Python\Python3*\python.exe", "$env:ProgramFiles\Python3*\python.exe")
    if (-not $basePy) { throw 'Python 3 not found. Install it with: winget install Python.Python.3.12' }
    Write-Host "Creating venv with $basePy"
    & $basePy -m venv (Join-Path $root '.venv')
}
Write-Host 'Installing Python packages...'
& $venvPy -m pip install --quiet --disable-pip-version-check -r (Join-Path $root 'requirements.txt')

# 2. Tool paths
$wingetFfmpeg = "$env:LOCALAPPDATA\Microsoft\WinGet\Packages\Gyan.FFmpeg*\*\bin"
$config = [ordered]@{
    ffmpeg  = Find-Exe 'ffmpeg'  @("$wingetFfmpeg\ffmpeg.exe")
    ffprobe = Find-Exe 'ffprobe' @("$wingetFfmpeg\ffprobe.exe")
    vlc     = Find-Exe 'vlc'     @("$env:ProgramFiles\VideoLAN\VLC\vlc.exe", "${env:ProgramFiles(x86)}\VideoLAN\VLC\vlc.exe")
}
if (-not $config.ffmpeg) { throw 'ffmpeg not found. Install it with: winget install Gyan.FFmpeg' }
[IO.File]::WriteAllText((Join-Path $root 'editor\config.json'), ($config | ConvertTo-Json), $utf8)

# 3. VLC extension
$extDir = Join-Path $env:APPDATA 'vlc\lua\extensions'
New-Item -ItemType Directory -Force $extDir | Out-Null
$lua = [IO.File]::ReadAllText((Join-Path $root 'vlc_extension\vlc_editor.lua'))
$lua = $lua.Replace('@LAUNCH@', "`"$pythonw`" `"$editor`"")
[IO.File]::WriteAllText((Join-Path $extDir 'vlc_editor.lua'), $lua, $utf8)

Write-Host ''
Write-Host 'Installed.'
Write-Host "  ffmpeg : $($config.ffmpeg)"
Write-Host "  VLC    : $($config.vlc)"
Write-Host "  Extension: $extDir\vlc_editor.lua"
Write-Host ''
Write-Host 'Restart VLC, open a video, then choose View > Edit Video.'
