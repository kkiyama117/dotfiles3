-- Hyprland Lua config entry point.
-- Two layers (end-4 style):
--   conf/   = portable base config
--   custom/ = machine-specific overrides (monitors, env, autostart)
-- See https://wiki.hypr.land/Configuring/Start/

-- ### MONITORS ###
require("custom.monitors")

-- ### MY PROGRAMS ###
require("conf.programs")

-- ### AUTOSTART ###
require("custom.autostart")

-- ### ENVIRONMENT VARIABLES ###
require("custom.environment")

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
