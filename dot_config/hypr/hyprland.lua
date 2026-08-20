-- Hyprland Lua config entry point.
-- Split into modules under conf/ (mirrors the classic source-based layout).
-- See https://wiki.hypr.land/Configuring/Start/

-- ### MONITORS ###
require("conf.monitors")

-- ### MY PROGRAMS ###
require("conf.programs")

-- ### AUTOSTART ###
require("conf.autostart")

-- ### ENVIRONMENT VARIABLES ###
require("conf.environment")

-- ### LOOK AND FEEL ###
require("conf.appearance")
require("conf.animation")
require("conf.layout")
require("conf.misc")

-- ### INPUT ###
require("conf.input")

-- ### KEYBINDINGS ###
require("conf.keybinding")

-- ### WINDOWS RULE ###
require("conf.windowrule")

-- ### WORKSPACES RULE ###
require("conf.workspaces")
