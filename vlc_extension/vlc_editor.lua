-- VLC Editor: adds "Edit Video" to VLC's menu.
-- The installer fills in LAUNCH.

local LAUNCH = [[@LAUNCH@]]

function descriptor()
  return {
    title = "Edit Video",
    version = "1.3",
    shortdesc = "Edit Video",
    description = "Trim, crop and slow-mo the current video.",
    capabilities = {},
  }
end

-- hex so the shell leaves it alone
local function hex(s)
  return (s:gsub(".", function(c) return string.format("%02x", c:byte()) end))
end

local function is_windows()
  return package ~= nil and package.config ~= nil and package.config:sub(1, 1) == "\\"
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
    -- microseconds
    ms = math.floor((vlc.var.get(input, "time") or 0) / 1000)
  end
  if vlc.playlist.status() == "playing" then
    vlc.playlist.pause()
  end

  local args = ' --hexuri ' .. hex(item:uri()) .. ' --time ' .. ms
  if is_windows() then
    os.execute('start "" ' .. LAUNCH .. args)
  else
    os.execute(LAUNCH .. args .. ' >/dev/null 2>&1 &')
  end
  vlc.deactivate()
end

function deactivate()
end

function close()
  vlc.deactivate()
end
