#!/bin/bash
# verify-mu-mac.sh - READ-ONLY health check of a Mu The Matrix Wine prefix (free runtime, the default)
# or CrossOver bottle (--runtime crossover).
# Inspects files only: cxbottle.conf, *.reg, DLL headers/hashes, config files. It never runs
# wine/wineserver, never starts or stops processes and never writes anything.
# Prints PASS/WARN/FAIL/INFO per item; exit status 1 if any FAIL.
set -u

KIT_DIR=$(cd -- "$(dirname -- "$0")" && pwd -P)
# shellcheck source=lib/mukit.sh
source "$KIT_DIR/lib/mukit.sh"

RUNTIME=${MUKIT_RUNTIME:-free}
BOTTLE=MuMatrixKit
PREFIX_OPT=
while [ "$#" -gt 0 ]; do
    case "$1" in
        --runtime) [ "$#" -ge 2 ] || mukit_die '--runtime needs free or crossover'; RUNTIME=$2; shift 2 ;;
        --prefix) [ "$#" -ge 2 ] || mukit_die '--prefix needs a directory'; PREFIX_OPT=$2; RUNTIME=free; shift 2 ;;
        --bottle) [ "$#" -ge 2 ] || mukit_die '--bottle needs a name'; BOTTLE=$2; RUNTIME=crossover; shift 2 ;;
        -h|--help) printf 'Usage: verify-mu-mac.sh [--runtime free|crossover] [--prefix DIR | --bottle NAME]\n  default: free runtime, prefix ~/Library/Application Support/MuTheMatrix/prefix; --bottle implies crossover (default MuMatrixKit). Read-only.\n'; exit 0 ;;
        *) mukit_die "Unknown argument: $1" ;;
    esac
done
mukit_runtime_valid "$RUNTIME" || mukit_die '--runtime must be free or crossover'
if [ "$RUNTIME" = free ]; then
    P=${PREFIX_OPT:-$MUKIT_FREE_HOME/prefix}
    BOTTLE=$(basename "$P")
else
    mukit_valid_bottle_name "$BOTTLE" || mukit_die 'Invalid bottle name'
    P="$MUKIT_BOTTLES_DIR/$BOTTLE"
fi
UREG="$P/user.reg"; SREG="$P/system.reg"
SYS32="$P/drive_c/windows/system32"
GAME="$P/drive_c/MuTheMatrix"
MUTOOLS="$P/drive_c/mutools"
STATE="$P/.mukit"
NPASS=0 NWARN=0 NFAIL=0

out() {   # out STATUS ITEM DETAIL
    case "$1" in PASS) NPASS=$((NPASS + 1)) ;; WARN) NWARN=$((NWARN + 1)) ;; FAIL) NFAIL=$((NFAIL + 1)) ;; esac
    printf '%-4s  %-40s %s\n' "$1" "$2" "$3"
}
section() { printf '\n[%s]\n' "$1"; }
short() { printf '%s' "${1:0:12}"; }

if [ "$RUNTIME" = free ]; then printf 'verify-mu-mac v%s  runtime=free  prefix=%s  (read-only)\n' "$MUKIT_VERSION" "$P"
else printf 'verify-mu-mac v%s  runtime=crossover  bottle=%s  (read-only)\n' "$MUKIT_VERSION" "$BOTTLE"; fi
printf 'path: %s\n' "$P"
if [ ! -d "$P" ]; then out FAIL "$([ "$RUNTIME" = free ] && echo prefix || echo bottle) directory" 'missing'; exit 1; fi

RT_DIR=
if [ "$RUNTIME" = free ]; then
section 'free runtime and prefix'
cur=$(cat "$MUKIT_FREE_HOME/runtime/current" 2>/dev/null | tr -d '\r\n ')
RT_DIR="$MUKIT_FREE_HOME/runtime/$cur"
if [ -n "$cur" ] && mukit_rt_ok "$RT_DIR"; then out PASS 'Wine runtime' "$cur ($(sed -n 's/^source=//p' "$RT_DIR/.mu-runtime" | head -1))"
else out FAIL 'Wine runtime' "missing or incomplete (${cur:-no runtime/current}); rerun setup"; fi
for r in user system; do
    if grep -q '^#arch=win32' "$P/$r.reg" 2>/dev/null; then out PASS "$r.reg arch" 'win32'
    else out FAIL "$r.reg arch" "$(grep -m1 '^#arch=' "$P/$r.reg" 2>/dev/null || echo 'missing') (64-bit prefixes cannot run the game)"; fi
done
[ ! -e "$P/drive_c/windows/syswow64" ] && out PASS 'no syswow64' 'pure 32-bit prefix' ||
    out FAIL 'no syswow64' 'syswow64 exists (not a 32-bit prefix)'
[ "$(cat "$STATE/owner" 2>/dev/null)" = "$MUKIT_FREE_OWNER_MARKER" ] && out INFO 'created by' 'mu-mac-kit setup (free runtime)' ||
    out INFO 'created by' 'not mu-mac-kit (manual/other prefix)'
[ -d "/Applications/CrossOver.app" ] && out INFO 'CrossOver' 'installed (not used by this prefix)' || out INFO 'CrossOver' 'not installed (not needed)'
else
# ------------------------------------------------------------------ bottle
section bottle
arch=$(mukit_conf_get "$P/cxbottle.conf" WineArch)
[ "$arch" = win32 ] && out PASS 'WineArch' 'win32' ||
    out FAIL 'WineArch' "${arch:-unset} (64-bit bottles fail: rosetta invalid gdt selector index 6)"
tmpl=$(mukit_conf_get "$P/cxbottle.conf" Template)
[ "$tmpl" = win10 ] && out PASS 'template' 'win10' || out WARN 'template' "${tmpl:-unset} (tested: win10)"
for r in user system; do
    if grep -q '^#arch=win32' "$P/$r.reg" 2>/dev/null; then out PASS "$r.reg arch" 'win32'
    else out FAIL "$r.reg arch" "$(grep -m1 '^#arch=' "$P/$r.reg" 2>/dev/null || echo 'missing')"; fi
done
[ ! -e "$P/drive_c/windows/syswow64" ] && out PASS 'no syswow64' 'pure 32-bit prefix' ||
    out FAIL 'no syswow64' 'syswow64 exists (winetricks would treat the prefix as win64)'
cxv=$(mukit_conf_get "$P/cxbottle.conf" Version)
appv=$(defaults read /Applications/CrossOver.app/Contents/Info.plist CFBundleShortVersionString 2>/dev/null)
out INFO 'CrossOver' "bottle ${cxv:-?}, installed ${appv:-?}"
[ "$(cat "$STATE/owner" 2>/dev/null)" = "$MUKIT_OWNER_MARKER" ] && out INFO 'created by' 'mu-mac-kit setup' ||
    out INFO 'created by' 'not mu-mac-kit (manual/other bottle)'
fi

# ------------------------------------------------------------------ .NET
section '.NET / launcher runtime'
rel=$(mukit_reg_value "$SREG" 'Software\Microsoft\NET Framework Setup\NDP\v4\Full' Release 2>/dev/null)
ver=$(mukit_reg_value "$SREG" 'Software\Microsoft\NET Framework Setup\NDP\v4\Full' Version 2>/dev/null)
case "$ver" in 4.8.*) vok=1 ;; *) vok=0 ;; esac
if [[ "$rel" =~ ^[0-9]+$ ]] && [ "$rel" -ge "$MUKIT_DOTNET48_RELEASE_MIN" ] && [ "$vok" = 1 ]; then out PASS '.NET Framework 4.8' "Release $rel, $ver"
elif [ "$vok" = 0 ] && [ -n "$ver" ]; then out FAIL '.NET Framework 4.8' "Version $ver, Release ${rel:-missing}: Wine's placeholder registration, not Microsoft .NET 4.8"
else out FAIL '.NET Framework 4.8' "Release ${rel:-missing} (need >= $MUKIT_DOTNET48_RELEASE_MIN)"; fi
fw="$P/drive_c/windows/Microsoft.NET/Framework/v4.0.30319"
[ -f "$fw/clr.dll" ] && [ -d "$fw/WPF" ] && out PASS '.NET files' 'clr.dll + WPF present' || out FAIL '.NET files' "missing under $fw"
if [ -f "$SYS32/mscoree.dll" ] && ! mukit_pe_is_wine_builtin "$SYS32/mscoree.dll"; then out PASS 'system32 mscoree.dll' 'native (Microsoft)'
else out FAIL 'system32 mscoree.dll' 'missing or Wine builtin (.NET install incomplete)'; fi
mo=$(mukit_dll_override "$UREG" mscoree)
mukit_loadorder_eq "${mo:-}" native && out PASS 'override mscoree' 'native' || out FAIL 'override mscoree' "${mo:-unset} (winetricks dotnet48 sets native)"
pn=$(mukit_reg_value "$SREG" 'Software\Microsoft\Windows NT\CurrentVersion' ProductName 2>/dev/null)
case "$pn" in *"Windows 10"*) out PASS 'Windows version' "$pn" ;; *) out WARN 'Windows version' "${pn:-unknown} (working bottle: Windows 10)" ;; esac

# ------------------------------------------------------------------ registry
section registry
while IFS='|' read -r f k n v c; do
    item="${k##*\\}:$n"
    [ "$n" = MUGL_STATS ] && sev=WARN || sev=FAIL
    got=$(mukit_reg_value "$P/$f.reg" "$k" "$n" 2>/dev/null); rc=$?
    case "$n" in
        \*windowscodecs|\*windowscodecsext|\*gdiplus)
            dll=${n#\*}
            got=$(mukit_dll_override "$UREG" "$dll"); rc=$?
            if [ "$rc" = 0 ] && mukit_loadorder_eq "$got" builtin; then out PASS "builtin $dll" 'override builtin'
            elif [ "$rc" != 0 ] && { [ ! -f "$SYS32/$dll.dll" ] || mukit_pe_is_wine_builtin "$SYS32/$dll.dll"; }; then
                out PASS "builtin $dll" 'no override, system32 copy is Wine builtin'
            else out FAIL "builtin $dll" "override '${got:-unset}' with a native system32 copy (native WIC breaks GDI+)"; fi
            continue ;;
    esac
    if [ "$rc" != 0 ]; then out "$sev" "$item" "missing (want '$v')"; continue; fi
    if [ "$c" = order ]; then mukit_loadorder_eq "$got" "$v" && out PASS "$item" "$got" || out "$sev" "$item" "'$got' (want '$v')"
    else [ "$got" = "$v" ] && out PASS "$item" "${got:-<empty>}" || out "$sev" "$item" "'$got' (want '$v')"; fi
done < <(mukit_registry_expectations 1)

# ------------------------------------------------------------------ OpenGL
section 'OpenGL (system32 must stay Wine builtin)'
if mukit_pe_is_wine_builtin "$SYS32/opengl32.dll"; then out PASS 'system32 opengl32.dll' 'Wine builtin'
else out FAIL 'system32 opengl32.dll' 'missing or NOT builtin (mugl loads it by path; restore Wine builtin)'; fi
if [ "$RUNTIME" = free ]; then cxgl="$RT_DIR/wine/lib/wine/i386-windows/opengl32.dll"; rtname='runtime'; else cxgl="$CX_ROOT/lib/wine/i386-windows/opengl32.dll"; rtname='CrossOver'; fi
h=$(mukit_sha256 "$SYS32/opengl32.dll"); hc=$(mukit_sha256 "$cxgl")
if [ -n "$hc" ] && [ "$h" = "$hc" ]; then out PASS "opengl32 = $rtname i386 builtin" "$(short "$h")"
else out WARN "opengl32 = $rtname i386 builtin" "prefix $(short "$h") vs $rtname $(short "${hc:-missing}")"; fi

# ------------------------------------------------------------------ game
section 'game (C:\MuTheMatrix)'
if [ ! -d "$GAME" ]; then out FAIL 'game directory' 'missing'
else
    h=$(mukit_sha256 "$GAME/main.exe")
    [ "$h" = "$MUKIT_MAIN_EXE_SHA256" ] && out PASS 'main.exe' "tested client $(short "$h")" ||
        { [ -n "$h" ] && out WARN 'main.exe' "untested build $(short "$h")" || out FAIL 'main.exe' missing; }
    h=$(mukit_sha256 "$GAME/MuTheMatrix.exe")
    [ "$h" = "$MUKIT_LAUNCHER_EXE_SHA256" ] && out PASS 'MuTheMatrix.exe (launcher)' "tested $(short "$h")" ||
        { [ -n "$h" ] && out WARN 'MuTheMatrix.exe (launcher)' "untested build $(short "$h")" || out FAIL 'MuTheMatrix.exe (launcher)' missing; }
    grep -q 'supportedRuntime version="v4.0"' "$GAME/MuTheMatrix.exe.config" 2>/dev/null &&
        out PASS 'MuTheMatrix.exe.config' 'v4.0 runtime' || out FAIL 'MuTheMatrix.exe.config' 'missing v4.0 supportedRuntime'
    if [ -f "$GAME/Data/Launcher/Design/Template.design" ]; then out FAIL 'custom skin disabled' 'Template.design present (launcher ctor aborts)'
    else out PASS 'custom skin disabled' "$(cd "$GAME/Data/Launcher/Design" 2>/dev/null && ls -d Template.design.disabled* 2>/dev/null | tr '\n' ' ')"; fi

    # mugl proxy
    gl="$GAME/opengl32.dll"
    if [ ! -f "$gl" ]; then out FAIL 'mugl opengl32.dll' 'missing (plain Wine GL: ~4 fps in world)'
    elif mukit_pe_is_wine_builtin "$gl"; then out FAIL 'mugl opengl32.dll' 'is a Wine builtin copy, not mugl'
    else
        h=$(mukit_sha256 "$gl")
        MUGL_VER=$(mukit_mugl_identify "$h")
        if [ "$MUGL_VER" = v7.5 ]; then out PASS 'mugl opengl32.dll' "v7.5 (pinned, current best) $(short "$h")"
        elif [ "$MUGL_VER" = v7.2 ]; then out PASS 'mugl opengl32.dll' "v7.2 (pinned rollback; v7.5 is faster in crowded scenes) $(short "$h")"
        elif [ "$MUGL_VER" = v7.1 ]; then out PASS 'mugl opengl32.dll' "v7.1 (pinned rollback; v7.2 paces frames precisely in background) $(short "$h")"
        elif [ "$MUGL_VER" = v7.0 ]; then out PASS 'mugl opengl32.dll' "v7.0 (pinned rollback; v7.2 is faster) $(short "$h")"
        elif [ "$(cat "$STATE/opengl32.dll.sha256" 2>/dev/null)" = "$h" ]; then out PASS 'mugl opengl32.dll' "kit-installed build $(short "$h")"
        else out WARN 'mugl opengl32.dll' "unknown build $(short "$h")"; fi
    fi
    ms="$GAME/mscoree.dll"
    h=$(mukit_sha256 "$ms")
    if [ -z "$h" ]; then out FAIL 'mscoree proxy' 'missing (launcher Settings list != game DevModeIndex)'
    elif [ "$h" = "$MUKIT_MSCOREE_PROXY_SHA256" ] || [ "$(cat "$STATE/mscoree.dll.sha256" 2>/dev/null)" = "$h" ]; then out PASS 'mscoree proxy' "$(short "$h")"
    else out WARN 'mscoree proxy' "unknown build $(short "$h")"; fi
fi

# ------------------------------------------------------------------ config files
section 'config (C:\mutools, LauncherOption.if)'
modes=
if [ -f "$MUTOOLS/mu-modes.txt" ]; then
    modes=$(tr '\r\n' '  ' < "$MUTOOLS/mu-modes.txt" | sed 's/  */ /g; s/^ //; s/ $//')
    mukit_modes_valid "$modes" && out PASS 'mu-modes.txt' "$modes" || { out FAIL 'mu-modes.txt' "unparseable: $modes"; modes=; }
else out FAIL 'mu-modes.txt' 'missing (launcher/game use unfiltered mode lists)'; fi
lo="$GAME/LauncherOption.if"
if [ -f "$lo" ]; then
    idx=$(mukit_lopt_get "$lo" DevModeIndex); wm=$(mukit_lopt_get "$lo" WindowMode); id=$(mukit_lopt_get "$lo" ID)
    if [[ "$idx" =~ ^[0-9]+$ ]] && [ -n "$modes" ] && m=$(mukit_mode_at "$modes" "$idx"); then
        scr=$(mukit_screen_size)
        if [[ "$scr" =~ ^[0-9]+x[0-9]+$ ]] && ! mukit_mode_fits "$m" "${scr%x*}" "${scr#*x}"; then
            out WARN 'LauncherOption DevModeIndex' "$idx = $m does not fit screen $scr"
        else out PASS 'LauncherOption DevModeIndex' "$idx = $m${scr:+ (screen $scr)}"; fi
    else out FAIL 'LauncherOption DevModeIndex' "'${idx:-missing}' not an index into mu-modes.txt"; fi
    [ "$wm" = 1 ] && out PASS 'LauncherOption WindowMode' '1 (windowed)' || out WARN 'LauncherOption WindowMode' "'${wm:-missing}' (tested: 1)"
    out INFO 'LauncherOption ID' "$([ -n "$id" ] && echo 'account prefilled' || echo 'empty')"
else out FAIL 'LauncherOption.if' 'missing'; fi
if [ -f "$MUTOOLS/mugl-mode.txt" ]; then
    mm=$(head -1 "$MUTOOLS/mugl-mode.txt" | tr -d '\r ')
    mukit_mugl_mode_valid "$mm" && { [ "$mm" = full+vbo ] && out PASS 'mugl-mode.txt' "$mm" || out WARN 'mugl-mode.txt' "$mm (fastest tested: full+vbo)"; } ||
        out FAIL 'mugl-mode.txt' "invalid '$mm'"
else out WARN 'mugl-mode.txt' 'missing (mugl defaults to full, without VBO emulation)'; fi
# Hotpatch mask: 44916143 (v7.5 default) is the norm; the older defaults and any mask with the v7.0 base bits (1|2|4|8) pass.
D=$MUKIT_HOTPATCH_DEFAULT B70=$MUKIT_HOTPATCH_V70_BITS
if [ -f "$MUTOOLS/mugl-hotpatch.txt" ]; then
    hp=$(head -1 "$MUTOOLS/mugl-hotpatch.txt" | tr -d '\r ')
    if ! mukit_hotpatch_valid "$hp"; then out FAIL 'mugl-hotpatch.txt' "invalid '$hp' (0-$MUKIT_HOTPATCH_MAX)"
    elif [ "$hp" = "$D" ]; then out PASS 'mugl-hotpatch.txt' "$hp (v7.5 default: all patches, frame pacing fix, terrain sort, quad batching, deferred client state, culling, native shadows/decals)"
    elif [ $((hp & B70)) = "$B70" ]; then
        note=; miss=$(( D & ~hp )); extra=$(( hp & ~D ))
        case "$hp" in
            7599)  note='v7.1/v7.2 default: no terrain sort, quad batching, deferred client state or culling' ;;
            6575)  note='v7.1 default without the frame pacing fix' ;;
            23983) note='v7.3 default: no quad batching, deferred client state or culling' ;;
            875951) note='v7.4 default: no native shadows, decals or specialised mesh-draw append' ;;
            *) [ "$miss" = 1024 ] && note='v7.5 default without the frame pacing fix' ||
                   { [ "$miss" != 0 ] && note="v7.5 default bits off: $miss"; } ;;
        esac
        [ "$extra" != 0 ] && note="${note:+$note; }extra bits: $extra"
        [ "${MUGL_VER:-}" = v7.0 ] && note="v7.0 reads $((hp & 31))"
        out PASS 'mugl-hotpatch.txt' "$hp (v7.0 base patches on; $note)"
    else out WARN 'mugl-hotpatch.txt' "$hp (some v7.0 base patches 1|2|4|8 off; default $D)"; fi
else out PASS 'mugl-hotpatch.txt' "absent (mugl built-in default: $D for v7.5, 875951 for v7.4, 23983 for v7.3, 7599 for v7.1/v7.2, $B70 for v7.0)"; fi
for t in muinput.exe clickstart.exe; do
    [ -f "$MUTOOLS/$t" ] && out PASS "$t" 'present (automation helper)' || out WARN "$t" 'missing (only needed by autologin scripts)'
done

# ------------------------------------------------------------------ runtime evidence (informational)
section 'runtime evidence (from previous runs; informational)'
if [ -f "$MUTOOLS/modehook.log" ]; then
    for e in main.exe MuTheMatrix.exe; do
        l=$(grep -i "\\\\$e:" "$MUTOOLS/modehook.log" | tail -1)
        out INFO "modehook $e" "${l:-no entry yet}"
    done
else out INFO 'modehook.log' 'none yet (created on first launch)'; fi
if [ -f "$MUTOOLS/mugl-stats.txt" ]; then
    out INFO 'mugl-stats.txt' "$(head -1 "$MUTOOLS/mugl-stats.txt" | tr -d '\r' | cut -c1-70)"
    l=$(tail -c 2000000 "$MUTOOLS/mugl-stats.txt" | LC_ALL=C grep -a '^=== hotpatch mask' | tail -1 | tr -d '\r')
    out INFO 'last hotpatch apply' "${l:-none in the last 2 MB}"
    l=$(tail -c 20000 "$MUTOOLS/mugl-stats.txt" | LC_ALL=C grep -a -o 'fps=[0-9.]*' | tail -1)
    w=$(tail -c 20000 "$MUTOOLS/mugl-stats.txt" | LC_ALL=C grep -a -o '^work=[0-9.]*ms' | tail -1)
    [ -n "$l$w" ] && out INFO 'last frame stats' "$w $l (written while the game runs)"
else out INFO 'mugl-stats.txt' 'none yet'; fi

# ------------------------------------------------------------------ launchers
section 'Mac launchers'
if [ "$RUNTIME" = free ]; then
    app=
    for d in /Applications "$HOME/Applications"; do [ -d "$d/Mu The Matrix.app" ] && app="$d/Mu The Matrix.app"; done
    [ -n "$app" ] && out PASS 'Mu The Matrix.app' "$app" || out INFO 'Mu The Matrix.app' 'not installed (Desktop launcher or play-mu.sh also work)'
    found=
    for c in "$HOME"/Desktop/*.command; do
        [ -f "$c" ] && grep -q "MU_RUNTIME=free" "$c" 2>/dev/null && grep -qF "MU_PREFIX='$P'" "$c" && found="${found:+$found, }$(basename "$c")"
    done
    [ -n "$found" ] && out PASS 'Desktop launcher' "$found" || out INFO 'Desktop launcher' 'none (optional)'
else
[ -x "$KIT_DIR/play-mu.sh" ] && out PASS 'play-mu.sh' 'kit launcher script present' || out FAIL 'play-mu.sh' 'missing'
found= lx87=0 ltw=
for c in "$HOME"/Desktop/*.command; do
    [ -f "$c" ] || continue
    if [ "$(mukit_launcher_bottle "$c" 2>/dev/null)" = "$BOTTLE" ]; then
        found="${found:+$found, }$(basename "$c")"
        grep -q 'MU_FAST_X87=1' "$c" && lx87=1
        ltw=$(sed -nE "s/.*MU_TIMEWALKER_DIR='([^']*)'.*/\\1/p" "$c" | head -1)
    fi
done
[ -n "$found" ] && out PASS 'Desktop launcher' "$found" || out WARN 'Desktop launcher' "none on ~/Desktop targets $BOTTLE"
tw_ok() { [ -n "$1" ] && [ -x "$1/scripts/run-crossover.sh" ] && [ -f "$1/build/libtimewalker.dylib" ]; }
if [ "$lx87" = 1 ]; then
    # The launcher asks play-mu.sh for fast x87; play-mu.sh exits if the timewalker build is gone.
    tw_ok "$ltw" && out PASS 'fast x87 (timewalker)' "launcher uses $ltw" ||
        out WARN 'fast x87 (timewalker)' "launcher sets MU_FAST_X87=1 but '${ltw:-<no MU_TIMEWALKER_DIR>}' is not a built rosetta-timewalker; rerun setup"
else
    tw=${MU_TIMEWALKER_DIR:-}
    tw_ok "$tw" && out INFO 'fast x87 (timewalker)' 'built; setup --fast-x87 --timewalker-dir enables it' || out INFO 'fast x87 (timewalker)' 'off (optional)'
fi

fi

printf '\nSummary: %d PASS, %d WARN, %d FAIL\n' "$NPASS" "$NWARN" "$NFAIL"
[ "$NFAIL" = 0 ]
