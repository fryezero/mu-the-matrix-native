#!/bin/bash
# Tests for Mu The Matrix.app (MAC-BUNDLE-001). Never touches a real bottle, a real CrossOver or a running
# game: every case uses a synthetic bottle directory, a stub CX_ROOT whose wine/wineserver only record their
# arguments, and a stub pgrep (so a game the user is playing does not change the results).
# Part 1 (any OS with bash): mu-launch.sh preflight errors, listings, dry run and a stubbed run.
# Part 2 (macOS with swiftc): builds the app, then checks bundle structure, plists, icon, signature and the
# app's command-line dry run. Set MU_BUNDLE_SKIP_BUILD=1 to skip part 2.
set -u
T_DIR=$(cd -- "$(dirname -- "$0")" && pwd -P)
BUNDLE_DIR=$(cd -- "$T_DIR/.." && pwd -P)
LAUNCH="$BUNDLE_DIR/mu-launch.sh"
TMPD=$(mktemp -d "${TMPDIR:-/tmp}/mubundle-test.XXXXXX") && TMPD=$(cd -- "$TMPD" && pwd -P)
[ -n "${MU_BUNDLE_TEST_KEEP:-}" ] && echo "keeping $TMPD" || trap 'rm -rf "$TMPD"' EXIT
NPASS=0 NFAIL=0 NSKIP=0
ok()   { NPASS=$((NPASS + 1)); printf 'ok    %s\n' "$1"; }
bad()  { NFAIL=$((NFAIL + 1)); printf 'FAIL  %s\n' "$1"; }
skip() { NSKIP=$((NSKIP + 1)); printf 'skip  %s\n' "$1"; }
eq()   { if [ "$2" = "$3" ]; then ok "$1"; else bad "$1: got [$2] want [$3]"; fi; }
has()  { case "$2" in *"$3"*) ok "$1" ;; *) bad "$1: [$3] not in output: $2" ;; esac; }
hasnt(){ case "$2" in *"$3"*) bad "$1: unexpected [$3] in output: $2" ;; *) ok "$1" ;; esac; }
digest() { find "$1" -type f -print | LC_ALL=C sort | while IFS= read -r f; do cksum "$f"; done | cksum; }

# ---------------------------------------------------------------- fixtures
FAKECX="$TMPD/CrossOver"; REC="$TMPD/rec"; mkdir -p "$FAKECX/bin" "$REC"
cat > "$FAKECX/bin/wine" <<'EOF'
#!/bin/bash
printf '%s\n' "$@" > "$MU_TEST_REC/wine.args"
printf '%s\n' "${TIMEWALKER_X87_ONLY:-unset}" > "$MU_TEST_REC/wine.x87"
echo "stub wine output"
exit "${MU_TEST_WINE_STATUS:-0}"
EOF
cat > "$FAKECX/bin/wineserver" <<'EOF'
#!/bin/bash
printf '%s %s\n' "${WINEPREFIX:-unset}" "$*" >> "$MU_TEST_REC/wineserver.calls"
EOF
chmod 755 "$FAKECX/bin/wine" "$FAKECX/bin/wineserver"
STUBBIN="$TMPD/stubbin"; mkdir -p "$STUBBIN"
printf '#!/bin/sh\n[ -n "${MU_TEST_RUNNING:-}" ] && exit 0\nexit 1\n' > "$STUBBIN/pgrep"; chmod 755 "$STUBBIN/pgrep"

BOTTLES="$TMPD/Bottles"
mkbottle() {   # NAME ARCH [nogame] [nomodes]
    local p="$BOTTLES/$1"
    mkdir -p "$p/drive_c/mutools"
    printf ';; synthetic\n[Bottle]\n"Template" = "win10"\n"WineArch" = "%s"\n' "$2" > "$p/cxbottle.conf"
    if [ "${3:-}" != nogame ]; then
        mkdir -p "$p/drive_c/MuTheMatrix"
        printf 'MZ synthetic launcher' > "$p/drive_c/MuTheMatrix/MuTheMatrix.exe"
        printf 'DevModeIndex:4\r\nWindowMode:1\r\nID:Player' > "$p/drive_c/MuTheMatrix/LauncherOption.if"
    fi
    [ "${4:-}" = nomodes ] || printf '960x600 1024x640 1280x800 1600x1000 1728x1080\n' > "$p/drive_c/mutools/mu-modes.txt"
}
mkbottle Good win32
mkbottle Wide win64
mkbottle Empty win32 nogame
mkbottle NoModes win32 game nomodes
mkdir -p "$BOTTLES/NotABottle"

TW="$TMPD/timewalker"; mkdir -p "$TW/scripts" "$TW/build"
: > "$TW/build/libtimewalker.dylib"
cat > "$TW/scripts/run-crossover.sh" <<'EOF'
#!/bin/bash
printf '%s\n' "$@" > "$MU_TEST_REC/tw.args"
printf '%s\n' "${TIMEWALKER_X87_ONLY:-unset}" > "$MU_TEST_REC/tw.x87"
exit 0
EOF
chmod 755 "$TW/scripts/run-crossover.sh"

export MU_TEST_REC="$REC" MUKIT_BOTTLES_DIR="$BOTTLES" CX_ROOT="$FAKECX" MU_LOG_DIR="$TMPD/logs"
export MU_FAST_X87_HOME="$TMPD/no-fast-x87-cache" MU_START_WAIT=1 PATH="$STUBBIN:$PATH" MUKIT_FREE_HOME="$TMPD/freehome"
unset MU_RUNTIME MU_PREFIX MU_BOTTLE MU_FAST_X87 MU_TIMEWALKER_DIR MU_RESOLUTION MU_DEBUGMSG MU_TEST_RUNNING MU_TEST_WINE_STATUS
L() { "$LAUNCH" "$@" 2>&1; }
code() { "$LAUNCH" "$@" >/dev/null 2>&1; echo $?; }

echo '# mu-launch.sh: syntax and usage'
if bash -n "$LAUNCH"; then ok 'bash -n mu-launch.sh'; else bad 'bash -n mu-launch.sh'; fi
[ -x "$LAUNCH" ] && ok 'mu-launch.sh is executable' || bad 'mu-launch.sh is executable'
eq 'help exits 0'               "$(code --help)" 0
has 'help lists exit codes'     "$(L --help)" '20 launcher exited right away'
eq 'unknown option'             "$(code --bogus)" 2

echo '# preflight errors'
eq 'no bottle selected'         "$(MU_RUNTIME=crossover code --check)" 2
has 'no bottle message'         "$(MU_RUNTIME=crossover L --check)" 'MU-ERROR 2 No bottle is selected'
eq 'invalid bottle name'        "$(MU_BOTTLE='../x' code --check)" 2
eq 'bad fast x87 value'         "$(MU_BOTTLE=Good MU_FAST_X87=yes code --check)" 2
eq 'bad resolution syntax'      "$(MU_BOTTLE=Good MU_RESOLUTION=big code --check)" 2
eq 'CrossOver missing'          "$(MU_BOTTLE=Good CX_ROOT="$TMPD/none" code --check)" 10
has 'CrossOver message'         "$(MU_BOTTLE=Good CX_ROOT="$TMPD/none" L --check)" 'MU-ERROR 10 CrossOver was not found'
eq 'bottle missing'             "$(MU_BOTTLE=Nope code --check)" 11
has 'bottle message names it'   "$(MU_BOTTLE=Nope L --check)" "bottle 'Nope' does not exist"
eq 'dir without cxbottle.conf'  "$(MU_BOTTLE=NotABottle code --check)" 11
eq '64-bit bottle'              "$(MU_BOTTLE=Wide code --check)" 12
eq 'game not installed'         "$(MU_BOTTLE=Empty code --check)" 13
eq 'already running'            "$(MU_TEST_RUNNING=1 MU_BOTTLE=Good code --check)" 14
has 'already running message'   "$(MU_TEST_RUNNING=1 MU_BOTTLE=Good L --check)" 'already running'
eq 'timewalker dir missing'     "$(MU_BOTTLE=Good MU_FAST_X87=1 MU_TIMEWALKER_DIR="$TMPD/none" code --check)" 15
eq 'no validated x87 cache'     "$(MU_BOTTLE=Good MU_FAST_X87=1 code --check)" 15
eq 'resolution not listed'      "$(MU_BOTTLE=Good MU_RESOLUTION=1920x1200 code --check)" 16
eq 'resolution without list'    "$(MU_BOTTLE=NoModes MU_RESOLUTION=1280x800 code --check)" 16
eq 'preflight ok'               "$(MU_BOTTLE=Good code --check)" 0
eq 'preflight ok, fast x87 dir' "$(MU_BOTTLE=Good MU_FAST_X87=1 MU_TIMEWALKER_DIR="$TW" code --check)" 0
eq 'one MU-ERROR line'          "$(MU_BOTTLE=Wide L --check | grep -c '^MU-ERROR ')" 1

echo '# listings'
LB=$(L --list-bottles)
has 'lists good bottle'         "$LB" "$(printf 'Good\twin32\tgame')"
has 'lists 64-bit bottle'       "$LB" "$(printf 'Wide\twin64\tgame')"
has 'lists bottle without game' "$LB" "$(printf 'Empty\twin32\tnogame')"
hasnt 'skips non-bottle dirs'   "$LB" NotABottle
eq 'no bottles dir is empty'    "$(MUKIT_BOTTLES_DIR="$TMPD/none" L --list-bottles)" ''
eq 'modes and current index'    "$(MU_BOTTLE=Good L --list-modes | tr '\n' ' ')" '960x600 1024x640 1280x800 1600x1000 1728x1080 current 4 '
eq 'no mode list'               "$(MU_BOTTLE=NoModes code --list-modes)" 16

echo '# dry run changes nothing'
before=$(digest "$BOTTLES")
D=$(MU_BOTTLE=Good MU_RESOLUTION=1280x800 L --dry-run)
eq 'dry run exit'               "$(MU_BOTTLE=Good MU_RESOLUTION=1280x800 code --dry-run)" 0
has 'plans LauncherOption write' "$D" 'MU-PLAN write '"$BOTTLES/Good/drive_c/MuTheMatrix/LauncherOption.if"' DevModeIndex:2'
has 'plans scoped wineserver -k' "$D" "MU-PLAN WINEPREFIX=$BOTTLES/Good $FAKECX/bin/wineserver -k"
has 'plans the launcher command' "$D" "--bottle Good --workdir C:\\MuTheMatrix C:\\MuTheMatrix\\MuTheMatrix.exe"
has 'plans the log'             "$D" "$TMPD/logs/wine-Good.log"
hasnt 'plain wine without x87'  "$D" TIMEWALKER_X87_ONLY
D=$(MU_BOTTLE=Good MU_RESOLUTION=1728x1080 L --dry-run)
hasnt 'same index: no write'    "$D" 'MU-PLAN write'
has 'same index noted'          "$D" 'DevModeIndex 4 (already set)'
D=$(MU_BOTTLE=Good MU_FAST_X87=1 MU_TIMEWALKER_DIR="$TW" L --dry-run)
has 'x87 runner planned'        "$D" "TIMEWALKER_X87_ONLY=main.exe $TW/scripts/run-crossover.sh --bottle Good"
eq 'bottles unchanged'          "$(digest "$BOTTLES")" "$before"
[ ! -e "$TMPD/logs" ] && ok 'dry run writes no log' || bad 'dry run writes no log'
[ ! -e "$REC/wineserver.calls" ] && [ ! -e "$REC/wine.args" ] && ok 'dry run runs no wine' || bad 'dry run runs no wine'

echo '# stubbed run'
R=$(MU_BOTTLE=Good MU_RESOLUTION=1280x800 L --run); rc=$?
eq 'run exit'                   "$rc" 0
has 'run reports start'         "$R" 'MU-INFO launcher started'
sleep 1
eq 'wineserver -k scoped to bottle' "$(cat "$REC/wineserver.calls" 2>/dev/null)" "$BOTTLES/Good -k"
eq 'wine arguments'             "$(tr '\n' ' ' < "$REC/wine.args" 2>/dev/null)" '--bottle Good --workdir C:\MuTheMatrix C:\MuTheMatrix\MuTheMatrix.exe '
eq 'no x87 filter on plain run' "$(cat "$REC/wine.x87" 2>/dev/null)" unset
LO="$BOTTLES/Good/drive_c/MuTheMatrix/LauncherOption.if"
eq 'LauncherOption.if rewritten in launcher format' "$(od -An -c "$LO" | tr -d ' \n')" 'DevModeIndex:2\r\nWindowMode:1\r\nID:Player'
eq 'backup keeps the original'  "$(od -An -c "$LO.mu-app-backup" | tr -d ' \n')" 'DevModeIndex:4\r\nWindowMode:1\r\nID:Player'
[ ! -e "$LO.mu-app-tmp" ] && ok 'no temp file left' || bad 'no temp file left'
has 'log has header and output' "$(cat "$TMPD/logs/wine-Good.log" 2>/dev/null)" 'stub wine output'
MU_BOTTLE=Good MU_RESOLUTION=1024x640 L --run >/dev/null
eq 'second change keeps first backup' "$(od -An -c "$LO.mu-app-backup" | tr -d ' \n')" 'DevModeIndex:4\r\nWindowMode:1\r\nID:Player'
eq 'second change applied'      "$(od -An -c "$LO" | tr -d ' \n')" 'DevModeIndex:1\r\nWindowMode:1\r\nID:Player'
rm -f "$REC"/*
eq 'early launcher exit'        "$(MU_TEST_WINE_STATUS=3 MU_BOTTLE=Good code --run)" 20
has 'early exit names the log'  "$(MU_TEST_WINE_STATUS=3 MU_BOTTLE=Good L --run)" "status 3). See $TMPD/logs/wine-Good.log"
rm -f "$REC"/*
eq 'fast x87 run'               "$(MU_BOTTLE=Good MU_FAST_X87=1 MU_TIMEWALKER_DIR="$TW" code --run)" 0
sleep 1
eq 'timewalker gets the bottle' "$(head -2 "$REC/tw.args" 2>/dev/null | tr '\n' ' ')" '--bottle Good '
eq 'x87 only for main.exe'      "$(cat "$REC/tw.x87" 2>/dev/null)" main.exe
[ ! -e "$REC/wine.args" ] && ok 'plain wine not used with x87' || bad 'plain wine not used with x87'
rm -f "$REC"/*
eq 'refused start runs nothing' "$(MU_TEST_RUNNING=1 MU_BOTTLE=Good code --run)" 14
[ ! -e "$REC/wineserver.calls" ] && ok 'refused start resets no server' || bad 'refused start resets no server'

# ---------------------------------------------------------------- part 2: the app bundle
echo '# free runtime (no CrossOver): synthetic runtime and prefix'
FHM="$TMPD/freehome"; RTD="$FHM/runtime/rt1"; FPX="$FHM/prefix"
eq 'free: runtime missing'      "$(code --check)" 30
has 'free: install hint'        "$(L --check)" 'Click Install... to set it up'
eq 'free: status all missing'   "$(L --status | tr '\n' ' ')" 'runtime missing prefix missing game missing '
mkdir -p "$RTD/wine/bin" "$RTD/wine/lib/wine/x86_64-unix"; : > "$RTD/wine/lib/wine/x86_64-unix/ntdll.so"; echo 'id=rt1' > "$RTD/.mu-runtime"
printf 'rt1\n' > "$FHM/runtime/current"
cat > "$RTD/wine/bin/wine" <<'EOS'
#!/bin/bash
printf '%s\n' "$PWD" "${WINEPREFIX:-unset}" "$@" > "$MU_TEST_REC/free-wine.args"
printf '%s\n' "${TIMEWALKER_X87_ONLY:-unset}" > "$MU_TEST_REC/free-wine.x87"
exit 0
EOS
cat > "$RTD/wine/bin/wineserver" <<'EOS'
#!/bin/bash
printf '%s %s\n' "${WINEPREFIX:-unset}" "$*" >> "$MU_TEST_REC/free-wineserver.calls"
EOS
chmod 755 "$RTD/wine/bin/wine" "$RTD/wine/bin/wineserver"
eq 'free: prefix missing'       "$(code --check)" 31
mkdir -p "$FPX/drive_c/mutools"; printf 'WINE REGISTRY Version 2\n\n#arch=win64\n' > "$FPX/system.reg"
eq 'free: 64-bit prefix refused' "$(code --check)" 31
printf 'WINE REGISTRY Version 2\n\n#arch=win32\n' > "$FPX/system.reg"
eq 'free: game missing'         "$(code --check)" 13
mkdir -p "$FPX/drive_c/MuTheMatrix"; printf 'MZ synthetic launcher' > "$FPX/drive_c/MuTheMatrix/MuTheMatrix.exe"
printf 'DevModeIndex:4\r\nWindowMode:1\r\nID:Player' > "$FPX/drive_c/MuTheMatrix/LauncherOption.if"
printf '960x600 1024x640 1280x800 1600x1000 1728x1080\n' > "$FPX/drive_c/mutools/mu-modes.txt"
eq 'free: status ready'         "$(L --status | tr '\n' ' ')" 'runtime ok rt1 prefix ok game ok '
eq 'free: preflight ok'         "$(code --check)" 0
eq 'free: CrossOver not needed' "$(CX_ROOT="$TMPD/none" code --check)" 0
eq 'free: modes listed'         "$(L --list-modes | tr '\n' ' ')" '960x600 1024x640 1280x800 1600x1000 1728x1080 current 4 '
eq 'fps counter off without a file' "$(L --fps-counter)" 'fps-counter off'
eq 'fps counter on'             "$(L --fps-counter on)" 'fps-counter on'
eq 'fps counter file'           "$(cat "$FPX/drive_c/mutools/mugl-fps.txt")" '1 tl'
printf '1 br\n' > "$FPX/drive_c/mutools/mugl-fps.txt"
eq 'fps counter off keeps the corner' "$(L --fps-counter off; cat "$FPX/drive_c/mutools/mugl-fps.txt")" "$(printf 'fps-counter off\n0 br')"
eq 'fps counter refuses other values' "$(L --fps-counter maybe >/dev/null; echo $?)" 2
D=$(MU_RESOLUTION=1280x800 L --dry-run)
has 'free: plans prefix reset'  "$D" "MU-PLAN WINEPREFIX=$FPX $RTD/wine/bin/wineserver -k"
has 'free: plans game folder'   "$D" "MU-PLAN cd $FPX/drive_c/MuTheMatrix"
has 'free: plans launcher'      "$D" "$RTD/wine/bin/wine MuTheMatrix.exe"
R=$(MU_RESOLUTION=1280x800 L --run); rc=$?
eq 'free: run exit'             "$rc" 0
sleep 1
eq 'free: launcher args'        "$(tr '\n' '|' < "$REC/free-wine.args" 2>/dev/null)" "$FPX/drive_c/MuTheMatrix|$FPX|MuTheMatrix.exe|"
eq 'free: prefix wineserver reset' "$(cat "$REC/free-wineserver.calls" 2>/dev/null)" "$FPX -k"
eq 'free: DevModeIndex written' "$(LC_ALL=C sed -n 's/^DevModeIndex:\([0-9]*\).*/\1/p' "$FPX/drive_c/MuTheMatrix/LauncherOption.if" | tr -d '\r')" 2
has 'free: fast x87 falls back without the translator' "$(MU_FAST_X87=1 L --check)" 'fast x87 not available'
eq 'free: fast x87 missing is not an error' "$(MU_FAST_X87=1 code --check)" 0
FX="$FHM/fast-x87"; mkdir -p "$FX"
for f in x87-main-only-wrapper runtime_loader libRuntimeRosettax87; do printf '#!/bin/bash\nprintf "%%s\\n" "$@" > "$MU_TEST_REC/fx-%s.args"\nprintf "%%s|%%s|%%s\\n" "${TIMEWALKER_X87_ONLY:-unset}" "${WINELOADER:-unset}" "${TIMEWALKER_X87_REAL_LOADER:-unset}" > "$MU_TEST_REC/fx.env"\n' "$f" > "$FX/$f"; chmod 755 "$FX/$f"; done
: > "$FX/libtimewalker.dylib"
has 'free: no inner loader -> plain' "$(MU_FAST_X87=1 L --check)" 'fast x87 not available'
printf '#!/bin/bash\nexit 0\n' > "$RTD/wine/lib/wine/x86_64-unix/wine"; chmod 755 "$RTD/wine/lib/wine/x86_64-unix/wine"
has 'free: fast x87 on'         "$(MU_FAST_X87=1 L --check)" 'fast x87 on'
D=$(MU_FAST_X87=1 L --dry-run)
has 'free: x87 wrapper planned' "$D" "$FX/x87-main-only-wrapper MuTheMatrix.exe"
has 'free: x87 only for main.exe' "$D" 'TIMEWALKER_X87_ONLY=main.exe'
MU_FAST_X87=1 L --run > /dev/null; sleep 1
eq 'free: x87 env at start'     "$(cat "$REC/fx.env" 2>/dev/null)" "main.exe|$FX/x87-main-only-wrapper|$RTD/wine/lib/wine/x86_64-unix/wine"
eq 'free: MU_BOTTLE alone keeps CrossOver' "$(MU_BOTTLE=Good L --check | grep -c 'CrossOver')" 1

echo '# app bundle'
APP="$TMPD/build/Mu The Matrix.app"   # own build directory: never replaces a build/ made with custom defaults
if [ "$(uname -s)" != Darwin ] || [ -n "${MU_BUNDLE_SKIP_BUILD:-}" ] || ! command -v xcrun >/dev/null || ! xcrun --find swiftc >/dev/null 2>&1; then
    skip 'app build and bundle checks (need macOS with swiftc)'
else
    if make -C "$BUNDLE_DIR" B="$TMPD/build" all >"$TMPD/build.log" 2>&1; then ok 'make builds the app'; else bad "make builds the app: $(tail -5 "$TMPD/build.log")"; fi
    C="$APP/Contents"
    for f in Info.plist PkgInfo MacOS/MuTheMatrix Resources/AppIcon.icns Resources/mu-launch.sh Resources/mukit.sh Resources/fast-x87.sh _CodeSignature/CodeResources; do
        [ -e "$C/$f" ] && ok "bundle has $f" || bad "bundle has $f"
    done
    eq 'only expected top-level entries' "$(ls "$C" | LC_ALL=C sort | tr '\n' ' ')" 'Info.plist MacOS PkgInfo Resources _CodeSignature '
    if plutil -lint "$C/Info.plist" >/dev/null; then ok 'Info.plist lints'; else bad 'Info.plist lints'; fi
    px() { plutil -extract "$1" raw -o - "$C/Info.plist" 2>/dev/null; }
    eq 'CFBundleExecutable'      "$(px CFBundleExecutable)" MuTheMatrix
    eq 'CFBundlePackageType'     "$(px CFBundlePackageType)" APPL
    eq 'CFBundleName'            "$(px CFBundleName)" 'Mu The Matrix'
    eq 'CFBundleIconFile'        "$(px CFBundleIconFile)" AppIcon
    eq 'bundle id'               "$(px CFBundleIdentifier)" io.github.fryezero.mu-the-matrix.launcher
    has 'version is set'         "$(px CFBundleShortVersionString)" .
    eq 'no unexpanded template'  "$(grep -c '@[A-Z_]*@' "$C/Info.plist")" 0
    [ -n "$(px MUDefaultBottle)" ] && ok 'default bottle key' || bad 'default bottle key'
    eq 'default fast x87 is bool' "$(plutil -extract MUDefaultFastX87 raw -o - "$C/Info.plist" | grep -cE '^(true|false)$')" 1
    eq 'PkgInfo'                 "$(cat "$C/PkgInfo")" 'APPL????'
    [ -x "$C/MacOS/MuTheMatrix" ] && ok 'executable bit' || bad 'executable bit'
    has 'native Mach-O'          "$(file "$C/MacOS/MuTheMatrix")" "Mach-O 64-bit executable"
    for r in mu-launch.sh:mu-launch.sh mukit.sh:../installer/lib/mukit.sh fast-x87.sh:../fast-x87.sh; do
        if cmp -s "$C/Resources/${r%%:*}" "$BUNDLE_DIR/${r#*:}"; then ok "Resources/${r%%:*} matches source"; else bad "Resources/${r%%:*} matches source"; fi
    done
    if codesign --verify --strict "$APP" 2>/dev/null; then ok 'signature verifies'; else bad 'signature verifies'; fi
    has 'ad-hoc signature'       "$(codesign -dv "$APP" 2>&1)" 'Signature=adhoc'
    rm -rf "$TMPD/icon.iconset"
    if iconutil -c iconset -o "$TMPD/icon.iconset" "$C/Resources/AppIcon.icns" 2>/dev/null; then ok 'icns converts back'; else bad 'icns converts back'; fi
    eq 'icon has 10 renditions'  "$(ls "$TMPD/icon.iconset" 2>/dev/null | wc -l | tr -d ' ')" 10
    eq '1024 px rendition'       "$(sips -g pixelWidth "$TMPD/icon.iconset/icon_512x512@2x.png" 2>/dev/null | awk '/pixelWidth/ {print $2}')" 1024

    echo '# app command line'
    BIN="$C/MacOS/MuTheMatrix"
    export MU_SETTINGS_FILE="$TMPD/settings/Launcher.plist"
    rm -rf "$TMPD/logs" "$REC"/*
    has 'app --version'          "$("$BIN" --version)" 'Mu The Matrix.app '
    "$BIN" --bogus >/dev/null 2>&1; eq 'app unknown option' "$?" 2
    eq 'settings path override'  "$("$BIN" --settings-path)" "$MU_SETTINGS_FILE"
    P=$("$BIN" --print-settings)
    has 'defaults without file'  "$P" '(missing; defaults)'
    has 'default bottle shown'   "$P" "Bottle = $(px MUDefaultBottle)"
    has 'default runtime is free' "$P" 'Runtime = free'
    has 'app --status ready (synthetic free home)' "$("$BIN" --status)" 'free runtime: installed'
    eq 'app --fps-counter on'  "$("$BIN" --fps-counter on)" 'fps-counter on'
    eq 'app --fps-counter reads the file' "$("$BIN" --fps-counter)" 'fps-counter on'
    eq 'app --fps-counter off' "$("$BIN" --fps-counter off)" 'fps-counter off'
    eq 'app --fps-counter refuses other values' "$("$BIN" --fps-counter maybe >/dev/null 2>&1; echo $?)" 2
    eq 'app --fps-counter without a game' "$(MUKIT_FREE_HOME="$TMPD/emptyhome" "$BIN" --fps-counter >/dev/null 2>&1; echo $?)" 1
    ID=$(MUKIT_FREE_HOME="$TMPD/emptyhome" "$BIN" --install-dry-run 2>&1)
    has 'app install plan: official installer' "$ID" 'download https://dl.muthematrix.com/MuTheMatrix-21.1.2.12.exe'
    has 'app install plan: free runtime' "$ID" 'runtime=free'
    eq 'app install plan exit' "$(MUKIT_FREE_HOME="$TMPD/emptyhome" "$BIN" --install-dry-run >/dev/null 2>&1; echo $?)" 0
    printf 'synthetic runtime archive' > "$TMPD/rt-file.tar.xz"
    RD=$(MUKIT_FREE_HOME="$TMPD/emptyhome" "$BIN" --install-dry-run --runtime-archive "$TMPD/rt-file.tar.xz" 2>&1)
    has 'app install plan: runtime from a local file' "$RD" "install the Wine runtime from $TMPD/rt-file.tar.xz"
    hasnt 'app install plan: no default runtime download with a file' "$RD" 'WS12WineCX24'
    has 'app install plan: game still from the official installer' "$RD" 'download https://dl.muthematrix.com/MuTheMatrix-21.1.2.12.exe'
    eq 'app refuses --runtime-archive without a file' "$("$BIN" --install-dry-run --runtime-archive >/dev/null 2>&1; echo $?)" 2
    mkdir -p "$TMPD/settings"
    cat > "$MU_SETTINGS_FILE" <<EOF
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0"><dict>
<key>Runtime</key><string>crossover</string>
<key>Bottle</key><string>Good</string>
<key>FastX87</key><true/>
<key>TimewalkerDir</key><string>$TW</string>
<key>Resolution</key><string>1600x1000</string>
<key>StartImmediately</key><false/>
</dict></plist>
EOF
    P=$("$BIN" --print-settings)
    has 'settings file read: bottle' "$P" 'Bottle = Good'
    has 'settings file read: x87'    "$P" 'FastX87 = true'
    has 'settings file read: res'    "$P" 'Resolution = 1600x1000'
    before=$(digest "$BOTTLES")
    D=$("$BIN" --dry-run); rc=$?
    eq 'app dry run exit'        "$rc" 0
    has 'app dry run: resolution' "$D" 'DevModeIndex:3'
    has 'app dry run: x87 runner' "$D" "TIMEWALKER_X87_ONLY=main.exe $TW/scripts/run-crossover.sh --bottle Good"
    eq 'app dry run changes no bottle' "$(digest "$BOTTLES")" "$before"
    [ ! -e "$REC/wine.args" ] && [ ! -e "$REC/tw.args" ] && ok 'app dry run starts nothing' || bad 'app dry run starts nothing'
    has 'app log written'        "$(cat "$TMPD/logs/app.log" 2>/dev/null)" 'cli --dry-run runtime=crossover bottle=Good fastX87=true resolution=1600x1000 -> status 0'
    CX_ROOT="$TMPD/none" "$BIN" --check >/dev/null 2>&1; eq 'app check: CrossOver missing' "$?" 10
    sedx() { sed -e "$1" "$MU_SETTINGS_FILE" > "$MU_SETTINGS_FILE.tmp" && mv "$MU_SETTINGS_FILE.tmp" "$MU_SETTINGS_FILE"; }
    sedx 's|<string>Good</string>|<string>Missing</string>|'
    has 'app check: bottle missing' "$("$BIN" --check)" 'MU-ERROR 11'
    printf 'not a plist' > "$MU_SETTINGS_FILE"
    has 'corrupt settings fall back to defaults' "$("$BIN" --print-settings)" "Bottle = $(px MUDefaultBottle)"
    unset MU_SETTINGS_FILE

    echo '# app: an app without the pinned DLLs says so'
    CB=$("$BIN" --check-bundle); rc=$?
    eq 'development build: --check-bundle exit 1' "$rc" 1
    has 'development build: names the missing mugl' "$CB" 'mugl (opengl32.dll, EMBED_MUGL)'
    has 'development build: names the missing fast x87' "$CB" 'fast x87 translator (EMBED_FAST_X87)'
    has 'development build: points to make player-app' "$CB" 'make player-app'
    has 'development build notice' "$(cat "$TMPD/build.log")" 'Do not give it to players'

    echo '# app: Rosetta 2 check and install (stubbed; never runs softwareupdate)'
    has 'rosetta present'            "$(MU_ROSETTA_CHECK=true "$BIN" --rosetta-status)" 'rosetta: installed'
    MU_ROSETTA_CHECK=false "$BIN" --rosetta-status >/dev/null; eq 'rosetta missing: exit 1' "$?" 1
    has 'rosetta missing: Terminal command' "$(MU_ROSETTA_CHECK=false "$BIN" --rosetta-status)" 'sudo softwareupdate --install-rosetta --agree-to-license'
    RF="$TMPD/rosetta-installed"; rm -f "$RF"
    R=$(MU_ROSETTA_CHECK="test -f '$RF'" MU_ROSETTA_INSTALL="touch '$RF'; echo Install of Rosetta 2 finished successfully" "$BIN" --install-rosetta); rc=$?
    eq 'rosetta install: exit 0' "$rc" 0
    has 'rosetta install: installed' "$R" 'rosetta: installed'
    [ -f "$RF" ] && ok 'rosetta install: the install command ran' || bad 'rosetta install: the install command ran'
    R=$(MU_ROSETTA_CHECK=false MU_ROSETTA_INSTALL="echo 'execution error: User canceled. (-128)' >&2; exit 1" "$BIN" --install-rosetta); rc=$?
    eq 'rosetta prompt declined: exit 1' "$rc" 1
    has 'rosetta prompt declined: said so' "$R" 'the administrator prompt was cancelled'
    R=$(MU_ROSETTA_CHECK=true MU_ROSETTA_INSTALL="touch '$TMPD/should-not-run'" "$BIN" --install-rosetta)
    has 'rosetta already there: nothing to do' "$R" 'already installed'
    [ ! -e "$TMPD/should-not-run" ] && ok 'rosetta already there: install not run' || bad 'rosetta already there: install not run'

    echo '# app: Cancel stops the whole installer tree (fake long-running installer)'
    # The fake installer starts two children: one that dies on SIGTERM and one that ignores it (needs the SIGKILL).
    # With FAKE_IGNORE_TERM=1 the installer itself ignores SIGTERM too, so only the escalation after the grace stops it.
    FAKE="$TMPD/fake-setup.sh"; CR="$TMPD/cancelrec"
    cat > "$FAKE" <<'EOS'
#!/bin/bash
case " $* " in *" --stop "*) printf '%s\n' "$*" >> "$MU_TEST_REC/stop.calls"; echo 'Stopped. (fake clean-up)'; exit 0 ;; esac
[ "${FAKE_IGNORE_TERM:-0}" = 1 ] && trap '' TERM
printf '%s %s %s\n' "$$" "$(ps -o pgid= -p $$ | tr -d ' ')" "${MUKIT_PROGRESS:-unset}" > "$MU_TEST_REC/setup.pid"
sleep 1000 & echo $! > "$MU_TEST_REC/child1.pid"
bash -c 'trap "" TERM; exec sleep 1001' & echo $! > "$MU_TEST_REC/child2.pid"
echo '== 7/14 game files'
i=0; while :; do i=$((i + 1)); echo "MU-PROGRESS $((i * 1000000)) 10000000 fake.exe"; sleep 1; done
EOS
    chmod 755 "$FAKE"
    cancel_case() {   # LABEL [env...]: start --install, cancel it with SIGINT once it runs, check that everything stopped
        local label=$1 app t=0 rc s c1 c2 alive
        shift; rm -rf "$CR"; mkdir -p "$CR"
        env MU_TEST_REC="$CR" MU_SETUP_SCRIPT="$FAKE" MU_CANCEL_GRACE=2 MUKIT_FREE_HOME="$TMPD/cancelhome" "$@" "$BIN" --install > "$CR/out" 2>&1 &
        app=$!
        while [ ! -s "$CR/child2.pid" ] && [ "$t" -lt 100 ]; do sleep 0.1; t=$((t + 1)); done
        sleep 1.5
        read -r s pg mp < "$CR/setup.pid"; c1=$(cat "$CR/child1.pid"); c2=$(cat "$CR/child2.pid")
        eq "$label: installer leads its own process group" "$pg" "$s"
        [ "$pg" != "$(ps -o pgid= -p $$ | tr -d ' ')" ] && ok "$label: not the caller's group" || bad "$label: not the caller's group"
        eq "$label: installer asked for progress lines" "$mp" lines
        t=$(date +%s); kill -INT "$app"; wait "$app"; rc=$?; t=$(( $(date +%s) - t ))
        eq "$label: app exit status" "$rc" 130
        alive=; for p in "$s" "$c1" "$c2"; do kill -0 "$p" 2>/dev/null && alive="$alive $p"; done
        eq "$label: installer and children stopped" "$alive" ''
        for p in "$s" "$c1" "$c2"; do kill -9 "$p" 2>/dev/null; done
        eq "$label: clean-up run for this prefix" "$(cat "$CR/stop.calls" 2>/dev/null)" '--runtime free --stop'
        has "$label: tells how to continue" "$(cat "$CR/out")" 'Run it again to continue'
        has "$label: condensed download progress" "$(cat "$CR/out")" 'downloading fake.exe: '
        CANCEL_SECONDS=$t
    }
    cancel_case 'cancel'
    [ "$CANCEL_SECONDS" -lt 2 ] && ok 'cancel: no wait when the installer stops at once' || bad "cancel: took $CANCEL_SECONDS s"
    cancel_case 'cancel (installer ignores SIGTERM)' FAKE_IGNORE_TERM=1
    [ "$CANCEL_SECONDS" -ge 2 ] && [ "$CANCEL_SECONDS" -lt 8 ] && ok 'cancel: SIGKILL after the 2 s grace' || bad "cancel escalation took $CANCEL_SECONDS s"
    has 'app log records the escalation' "$(cat "$TMPD/logs/app.log")" 'still running after 2 s, SIGKILL'

    echo '# make player-app: refuses an app without the pinned files'
    PB="$TMPD/pbuild"
    if make -C "$BUNDLE_DIR" B="$PB" player-app >"$TMPD/player1.log" 2>&1; then bad 'player-app without embeds fails'; else ok 'player-app without embeds fails'; fi
    has 'player-app names EMBED_MUGL'   "$(cat "$TMPD/player1.log")" 'EMBED_MUGL=/path/to/opengl32.dll'
    has 'player-app names EMBED_FAST_X87' "$(cat "$TMPD/player1.log")" 'EMBED_FAST_X87=/path/to/fast-x87'
    [ ! -e "$PB/Mu The Matrix.app" ] && ok 'player-app built nothing' || bad 'player-app built nothing'
    EMB="$TMPD/embeds"; mkdir -p "$EMB/fx"
    printf 'MZ synthetic mugl' > "$EMB/opengl32.dll"; printf 'MZ synthetic mscoree' > "$EMB/mscoree.dll"
    for f in libtimewalker.dylib runtime_loader libRuntimeRosettax87; do printf 'stub' > "$EMB/fx/$f"; done
    if make -C "$BUNDLE_DIR" B="$PB" player-app EMBED_MUGL="$EMB/opengl32.dll" EMBED_MSCOREE="$EMB/mscoree.dll" EMBED_FAST_X87="$EMB" >"$TMPD/player2.log" 2>&1; then
        bad 'player-app refuses a fast x87 folder without the translator'; else ok 'player-app refuses a fast x87 folder without the translator'; fi
    if make -C "$BUNDLE_DIR" B="$PB" player-app EMBED_MUGL="$EMB/opengl32.dll" EMBED_MSCOREE="$EMB/mscoree.dll" EMBED_FAST_X87="$EMB/fx" >"$TMPD/player3.log" 2>&1; then
        ok 'player-app with all three embeds'; else bad "player-app with all three embeds: $(tail -5 "$TMPD/player3.log")"; fi
    PBIN="$PB/Mu The Matrix.app/Contents/MacOS/MuTheMatrix"
    has 'player app: bundle complete' "$("$PBIN" --check-bundle)" 'bundle complete'
    ID=$(MUKIT_FREE_HOME="$TMPD/emptyhome" "$PBIN" --install-dry-run 2>&1)
    has 'player app installs the bundled mugl' "$ID" 'is not a pinned mugl build'
    has 'player app installs the bundled fast x87' "$ID" 'install fast x87 file x87-main-only-wrapper'
fi

echo
echo "test-bundle: $NPASS passed, $NFAIL failed, $NSKIP skipped"
[ "$NFAIL" = 0 ]
