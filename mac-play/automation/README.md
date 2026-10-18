# Existing-session helpers

These are Claude's authored input and measurement helpers, adapted to select an
explicit test bottle or log. Nothing here was executed against the game during
publication. Build muinput through `make mac-hotpatch`. The existing input
protocol includes `mclick` for the MU Helper middle-button toggle. MAC-PERF-007 adds
`kdown`/`kup` (hold a key) and `wheel FX FY STEPS`. The zoomed-out benchmark view is
`key 75` (F6, 3D camera) then `kdown 10 wheel 0.5 0.5 -60 kup 10` (Shift+wheel out);
the camera returns to normal after a client restart.

`mu-autologin.sh` operates an already running server-list window. It picks the MTM-1 sub-server by default
(`SUBSERVER_FX`/`SUBSERVER_FY` = 0.498/0.468 window fractions; MTM-3 is 0.498/0.519). Set
`MU_BOTTLE`, `MU_GAME_DIR` to the host path of that bottle's clone, `MU_ACCOUNT`
and `MU_KEYCHAIN_SERVICE`. The password comes from `security find-generic-password`
at runtime, passes to muinput as a process argument, and is then unset. It is
never stored in the script or printed. Avoid shell tracing and process-command
capture while logging in. This is the original Keychain mechanism, not a new
credential store. No personal account name or Keychain item name is published.

The original restart/server helper is intentionally omitted. It killed game
processes and depended on machine-specific launcher scripts. Login and movement
scripts refuse MuMatrix32. `mu-step.sh` selects an existing window, clicks a
location and middle-clicks the helper; `mu-coords.sh` crops a matching window's
HUD through `winshot.swift`. Screen capture needs the user's existing macOS
permission. Logs/screenshots stay local. Do not run these scripts during work
that prohibits game interaction.

`MU_STATS_FILE=/private/mugl-stats.txt zsh wkwin.sh 20` reads new FPS/work
samples for twenty seconds. `fpswin.sh` prints FPS samples and their mean.
These helpers average interval samples without weighting by frame count.
