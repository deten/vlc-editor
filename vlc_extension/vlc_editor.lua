-- VLC Editor: adds "View > Edit Video" to VLC.
-- Pauses playback and opens the editor on the current file at the current position.
-- The installer copies this into %APPDATA%\vlc\lua\extensions and fills in LAUNCH:
-- the quoted editor command, e.g. "C:\...\VLC Editor.exe" or "...\pythonw.exe" "...\vlc_editor.py".

local LAUNCH = [[@LAUNCH@]]

function descriptor()
  return {
    title = "Edit Video",
    version = "1.0",
    shortdesc = "Edit Video",
    description = "Trim, crop and slow-mo the current video.",
    capabilities = {},
  }
end

-- Hex-encode so the URI survives cmd.exe untouched (no %, &, ^ or non-ASCII characters).
local function hex(s)
  return (s:gsub(".", function(c) return string.format("%02x", c:byte()) end))
end

function activate()
  local item = vlc.input.item()
  if not item then
    vlc.osd.message("Edit Video: open a video first", nil, "center", 3000000)
    vlc.deactivate()
    return
  end

  local ms = 0
  local input = vlc.object.input()
  if input then
    -- VLC 3 reports "time" in microseconds
    ms = math.floor((vlc.var.get(input, "time") or 0) / 1000)
  end
  if vlc.playlist.status() == "playing" then
    vlc.playlist.pause()
  end

  local cmd = 'start "" ' .. LAUNCH .. ' --hexuri ' .. hex(item:uri()) .. ' --time ' .. ms
  os.execute(cmd)
  vlc.deactivate()
end

function deactivate()
end

function close()
  vlc.deactivate()
end
