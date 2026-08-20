-------------------
---- AUTOSTART ----
-------------------

-- See https://wiki.hypr.land/Configuring/Basics/Autostart/

hl.on("hyprland.start", function ()
  hl.exec_cmd("/usr/lib/hyprpolkitagent/hyprpolkitagent")
  hl.exec_cmd("fcitx5 -d")

  -- Clipboard history (cliphist)
  hl.exec_cmd("wl-paste --type text --watch cliphist store")
  hl.exec_cmd("wl-paste --type image --watch cliphist store")
end)
