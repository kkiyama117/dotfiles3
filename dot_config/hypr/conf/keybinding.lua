---------------------
---- KEYBINDINGS ----
---------------------

local mainMod = "SUPER" -- Sets "Windows" key as main modifier

local programs   = require("conf.programs")
local terminal   = programs.terminal
local fileManager = programs.fileManager
local menu        = programs.menu

-- Example binds, see https://wiki.hypr.land/Configuring/Basics/Binds/ for more
-- description を付けると Super+/ の cheatsheet に `[グループ] 説明` で表示される
hl.bind(mainMod .. " + Q", hl.dsp.exec_cmd(terminal), { description = "[System] Terminal" })
hl.bind(mainMod .. " + SHIFT + Q", hl.dsp.exec_cmd(terminal .. " --class floatingterm"), { description = "[System] Floating terminal (overlay)" })
local closeWindowBind = hl.bind(mainMod .. " + C", hl.dsp.window.close(), { description = "[Windows] Close window" })
-- closeWindowBind:set_enabled(false)
hl.bind(mainMod .. " + M", hl.dsp.exec_cmd("command -v hyprshutdown >/dev/null 2>&1 && hyprshutdown || hyprctl dispatch 'hl.dsp.exit()'"), { description = "[System] Exit / shutdown" })
hl.bind(mainMod .. " + E", hl.dsp.exec_cmd(fileManager), { description = "[System] File manager" })
hl.bind(mainMod .. " + F", hl.dsp.window.float({ action = "toggle" }), { description = "[Windows] Toggle float" })
hl.bind(mainMod .. " + V", hl.dsp.exec_cmd("cliphist list | rofi -dmenu | cliphist decode | wl-copy"), { description = "[System] Clipboard history" })
hl.bind(mainMod .. " + R", hl.dsp.exec_cmd(menu), { description = "[System] App launcher" })
hl.bind(mainMod .. " + P", hl.dsp.window.pseudo(), { description = "[Windows] Pseudo-tile" })
hl.bind(mainMod .. " + J", hl.dsp.layout("togglesplit"), { description = "[Windows] Toggle split" })

-- Cheatsheet: Super+/ でバインド一覧を表示/非表示（hypr-cheatsheet スクリプト）
hl.bind(mainMod .. " + slash", hl.dsp.exec_cmd("hypr-cheatsheet"), { description = "[System] Keybind cheatsheet" })

-- Move focus with mainMod + arrow keys
hl.bind(mainMod .. " + left",  hl.dsp.focus({ direction = "left" }),  { description = "[Windows] Focus left" })
hl.bind(mainMod .. " + right", hl.dsp.focus({ direction = "right" }), { description = "[Windows] Focus right" })
hl.bind(mainMod .. " + up",    hl.dsp.focus({ direction = "up" }),    { description = "[Windows] Focus up" })
hl.bind(mainMod .. " + down",  hl.dsp.focus({ direction = "down" }),  { description = "[Windows] Focus down" })

-- Move window to adjacent monitor with mainMod + SHIFT + arrow keys
hl.bind(mainMod .. " + SHIFT + left",  hl.dsp.window.move({ monitor = "left",  follow = true }), { description = "[Windows] Move window to left monitor" })
hl.bind(mainMod .. " + SHIFT + right", hl.dsp.window.move({ monitor = "right", follow = true }), { description = "[Windows] Move window to right monitor" })
hl.bind(mainMod .. " + SHIFT + up",    hl.dsp.window.move({ monitor = "up",    follow = true }), { description = "[Windows] Move window to top monitor" })
hl.bind(mainMod .. " + SHIFT + down",  hl.dsp.window.move({ monitor = "down",  follow = true }), { description = "[Windows] Move window to bottom monitor" })

-- Switch workspaces with mainMod + [0-9]
-- Move active window to a workspace with mainMod + SHIFT + [0-9]
for i = 1, 10 do
    local key = i % 10 -- 10 maps to key 0
    hl.bind(mainMod .. " + " .. key,         hl.dsp.focus({ workspace = i }), { description = "[Workspaces] Focus workspace " .. i })
    hl.bind(mainMod .. " + SHIFT + " .. key, hl.dsp.window.move({ workspace = i }), { description = "[Workspaces] Move window to workspace " .. i })
end

-- Example special workspace (scratchpad)
hl.bind(mainMod .. " + S",         hl.dsp.workspace.toggle_special("magic"), { description = "[Workspaces] Toggle scratchpad" })
hl.bind(mainMod .. " + SHIFT + S", hl.dsp.window.move({ workspace = "special:magic" }), { description = "[Workspaces] Move window to scratchpad" })

-- Scroll through existing workspaces with mainMod + scroll
hl.bind(mainMod .. " + mouse_down", hl.dsp.focus({ workspace = "e+1" }))
hl.bind(mainMod .. " + mouse_up",   hl.dsp.focus({ workspace = "e-1" }))

-- Move/resize windows with mainMod + LMB/RMB and dragging
hl.bind(mainMod .. " + mouse:272", hl.dsp.window.drag(),   { mouse = true })
hl.bind(mainMod .. " + mouse:273", hl.dsp.window.resize(), { mouse = true })

-- Laptop multimedia keys for volume and LCD brightness
hl.bind("XF86AudioRaiseVolume", hl.dsp.exec_cmd("wpctl set-volume -l 1 @DEFAULT_AUDIO_SINK@ 5%+"), { locked = true, repeating = true })
hl.bind("XF86AudioLowerVolume", hl.dsp.exec_cmd("wpctl set-volume @DEFAULT_AUDIO_SINK@ 5%-"),      { locked = true, repeating = true })
hl.bind("XF86AudioMute",        hl.dsp.exec_cmd("wpctl set-mute @DEFAULT_AUDIO_SINK@ toggle"),     { locked = true, repeating = true })
hl.bind("XF86AudioMicMute",     hl.dsp.exec_cmd("wpctl set-mute @DEFAULT_AUDIO_SOURCE@ toggle"),   { locked = true, repeating = true })
hl.bind("XF86MonBrightnessUp",  hl.dsp.exec_cmd("brightnessctl -e4 -n2 set 5%+"),                  { locked = true, repeating = true })
hl.bind("XF86MonBrightnessDown",hl.dsp.exec_cmd("brightnessctl -e4 -n2 set 5%-"),                  { locked = true, repeating = true })

-- Requires playerctl
hl.bind("XF86AudioNext",  hl.dsp.exec_cmd("playerctl next"),       { locked = true })
hl.bind("XF86AudioPause", hl.dsp.exec_cmd("playerctl play-pause"), { locked = true })
hl.bind("XF86AudioPlay",  hl.dsp.exec_cmd("playerctl play-pause"), { locked = true })
hl.bind("XF86AudioPrev",  hl.dsp.exec_cmd("playerctl previous"),   { locked = true })
