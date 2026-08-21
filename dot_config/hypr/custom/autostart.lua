-------------------
---- AUTOSTART ----
-------------------

-- See https://wiki.hypr.land/Configuring/Basics/Autostart/

hl.on("hyprland.start", function ()
  -- Topbar: waybar (host-installed; container has no GUI, so NOT in packages.toml)
  hl.exec_cmd("waybar")
  -- Notifications: swaync (host-only; replaces wired). See docs/issues/2026-08-21-swaync-replace-wired.md
  hl.exec_cmd("swaync")
  hl.exec_cmd("/usr/lib/hyprpolkitagent/hyprpolkitagent")
  hl.exec_cmd("fcitx5 -d")

  -- Clipboard history (cliphist)
  hl.exec_cmd("wl-paste --type text --watch cliphist store")
  hl.exec_cmd("wl-paste --type image --watch cliphist store")
end)
