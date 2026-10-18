#!/bin/bash
# setup-mu-mac.sh - set up Mu The Matrix on an Apple Silicon Mac in a NEW 32-bit Wine prefix.
# Default runtime: free (no CrossOver): CodeWeavers' open-source Wine, downloaded and pinned by SHA-256,
# in ~/Library/Application Support/MuTheMatrix. Legacy: --runtime crossover uses a CrossOver bottle.
# Idempotent and step-wise: every step inspects the prefix first and skips when already done.
# The game comes from your own client folder (--game-dir) or the official installer (--game-installer).
#
# Bash 3.2 compatible. See README.md (this directory) for the step <-> manual-fix inventory.
# Lives in the repository as mac-play/installer; it reuses the sibling mac-play sources
# (cxwine/cxwineserver shims, mugl, mumodes) instead of copies. No third-party or client-derived
# binary ships with the repository: prebuilt DLLs come from a directory you supply (--dll-dir).
set -uo pipefail
umask 022

KIT_DIR=$(cd -- "$(dirname -- "$0")" && pwd -P)
MAC_PLAY=$(cd -- "$KIT_DIR/.." && pwd -P)          # the repository's mac-play/ (or the app's Resources)
# shellcheck source=lib/mukit.sh
source "$KIT_DIR/lib/mukit.sh"

usage() {
    cat <<'EOF'
Usage: setup-mu-mac.sh [options]

  --runtime R            free (default): no CrossOver; downloads the pinned open-source Wine runtime and
                         uses the prefix in --prefix. crossover: legacy CrossOver bottle (--bottle; --bottle
                         without --runtime also selects crossover).
  --prefix DIR           Free runtime: the Wine prefix (default: ~/Library/Application Support/MuTheMatrix/prefix).
  --runtime-archive SRC  Free runtime: use this runtime archive (local .tar.xz or https URL, e.g. one the server
                         owner hosts, built with runtime/build-wine.sh) instead of the default download.
  --runtime-sha256 HEX   SHA-256 of --runtime-archive (required with a URL).
  --bottle NAME          CrossOver runtime: bottle to create/resume (default: MuMatrixKit). Protected names
                         (MuMatrix32, Windows10MU, Steam, MuMatrixRecovery) are refused.
  --game-dir PATH        Your existing Mu The Matrix client folder (must contain main.exe and
                         MuTheMatrix.exe). Copied (APFS clone when possible) to C:\MuTheMatrix.
  --game-installer SRC   Install the game with the official Windows installer: a local .exe, an https URL, or
                         "official" (the server's download link, about 2.2 GB). One of --game-dir /
                         --game-installer is required until the prefix contains the game.
  --dry-run              Inspect and print every action without changing anything.
  --modes "WxH ..."      Display-mode list for C:\mutools\mu-modes.txt (default: picked from
                         the main screen; 1800x1169 gives "960x600 1024x640 1280x800 1600x1000 1728x1080").
  --mode-index N         LauncherOption.if DevModeIndex (default: largest mode that fits).
  --account ID           Prefill the launcher/game Account ID (never a password).
  --dll-source SRC       auto (default): prebuilt when --dll-dir is given, else build when MinGW is installed,
                         else none (no mugl: low fps; no mscoree proxy).
                         build: compile from this repository with MinGW (mac-play/mugl or, with
                         --mugl-build private, your own hotpatch build, plus mac-play/mumodes' mscoree proxy).
                         prebuilt: install the pinned DLLs from --dll-dir (see README: they are not in the repo).
  --dll-dir DIR          Directory with your prebuilt mugl-v75.dll (or v72/v71/v70) and mscoree.dll
                         (SHA-256 pinned; env MU_DLL_DIR). Required with --dll-source prebuilt.
  --mugl-dll FILE        Install exactly this opengl32.dll (mugl) build, e.g. the one bundled in Mu The Matrix.app;
                         pinned builds are recognised, others are installed with a warning (implies --dll-source files).
  --mscoree-dll FILE     Install exactly this mscoree.dll proxy (with --mugl-dll; built from source when omitted
                         and MinGW is present, otherwise skipped).
  --mugl-version V       v75 (default, current best) | v72 | v71 | v70 (rollbacks). Only with --dll-source prebuilt.
  --mugl-build B         public (default): the repository's batching-only mac-play/mugl. private: the DLL you
                         generated with mac-play/hotpatch (build/private/opengl32.dll; never redistribute it).
                         Only with --dll-source build.
  --dotnet-installer P   Optional local copy of Microsoft's ndp48-x86-x64-allos-enu.exe (SHA-256 checked) used
                         to seed winetricks' cache; otherwise winetricks downloads it (env MU_DOTNET48_INSTALLER).
  --helpers-dir DIR      Where muinput.exe / clickstart.exe come from (default: mac-play/diagnostics/build/diagnostics,
                         created by 'make mac-diagnostics'); optional, only autologin tools use them.
  --hotpatch-mask N      C:\mutools\mugl-hotpatch.txt (default 44916143 = v7.5 default; older builds read
                         fewer bits and see their own default: v7.4 875951, v7.3 23983, v7.1/v7.2 7599, v7.0 15).
                         A file holding an earlier kit default (15, 7599, 875951) is upgraded.
  --no-mugl              Do not install the OpenGL proxy (plain Wine OpenGL; ~4 fps in world).
  --no-stats             Do not set HKCU\Environment MUGL_STATS.
  --reset-config         Overwrite existing C:\mutools config files and LauncherOption.if values.
  --launcher-name NAME   Desktop .command file name (default: "Play Mu The Matrix (BOTTLE).command").
  --no-desktop           Do not install a Desktop launcher (Mu The Matrix.app does not need one).
  --fast-x87             Use rosetta-timewalker fast x87 for main.exe. Free runtime: installs it from
                         --fast-x87-dir or --timewalker-dir into the runtime folder (~45% less frame work).
                         CrossOver: uses an already built --timewalker-dir (see README).
  --fast-x87-dir DIR     Free runtime: folder with libtimewalker.dylib, runtime_loader and libRuntimeRosettax87
                         (runtime/package-fast-x87.sh; Mu The Matrix.app bundles it); implies --fast-x87.
  --timewalker-dir DIR   Existing rosetta-timewalker checkout/build, used only with --fast-x87.
  --ac-variant V         TODO hook: with-ac (default, unchanged client) | no-ac (not implemented).
  --skip-verify          Do not run verify-mu-mac.sh at the end.
  -h, --help             This help.

Environment: MUKIT_RUNTIME (free|crossover), MUKIT_FREE_HOME (free runtime folder), CX_ROOT (CrossOver
             runtime dir), WINETRICKS (winetricks executable; default: the pinned download for the free runtime),
             MINGW_CC (default i686-w64-mingw32-gcc), MU_DLL_DIR, MU_DOTNET48_INSTALLER,
             MU_TIMEWALKER_DIR, MUKIT_BOTTLES_DIR, MUKIT_BUILD_DIR, MUKIT_PRIVATE_BUILD_DIR, MUKIT_PYTHON (default python3, for the public mugl's gen.py),
             MUKIT_EXTRA_PROTECTED_BOTTLES.
EOF
}

RUNTIME=${MUKIT_RUNTIME:-}
PREFIX_OPT=
RT_ARCHIVE=
RT_ARCHIVE_SHA=
GAME_INSTALLER=
BOTTLE=MuMatrixKit
BOTTLE_SET=0
GAME_SRC=
DRY_RUN=0
MODES=
MODE_INDEX=
ACCOUNT=
ACCOUNT_SET=0
DLL_SOURCE=auto
DLL_DIR=${MU_DLL_DIR:-}
MUGL_DLL=
MSCOREE_DLL=
MUGL_BUILD=public
DOTNET_INSTALLER=${MU_DOTNET48_INSTALLER:-}
HELPERS_DIR=$MAC_PLAY/diagnostics/build/diagnostics
TIMEWALKER_DIR=${MU_TIMEWALKER_DIR:-}
MUGL_VERSION=$MUKIT_MUGL_DEFAULT_VERSION
HOTPATCH_MASK=$MUKIT_HOTPATCH_DEFAULT
NO_MUGL=0
NO_STATS=0
RESET_CONFIG=0
LAUNCHER_NAME=
NO_DESKTOP=0
FAST_X87=0
FAST_X87_DIR=
AC_VARIANT=with-ac
SKIP_VERIFY=0
MINGW_CC=${MINGW_CC:-i686-w64-mingw32-gcc}

need_arg() { [ "$2" -ge 2 ] || mukit_die "$1 needs a value"; }
while [ "$#" -gt 0 ]; do
    case "$1" in
        --runtime)       need_arg "$1" "$#"; RUNTIME=$2; shift 2 ;;
        --prefix)        need_arg "$1" "$#"; PREFIX_OPT=$2; shift 2 ;;
        --runtime-archive) need_arg "$1" "$#"; RT_ARCHIVE=$2; shift 2 ;;
        --runtime-sha256) need_arg "$1" "$#"; RT_ARCHIVE_SHA=$2; shift 2 ;;
        --game-installer) need_arg "$1" "$#"; GAME_INSTALLER=$2; shift 2 ;;
        --bottle)        need_arg "$1" "$#"; BOTTLE=$2; BOTTLE_SET=1; shift 2 ;;
        --game-dir)      need_arg "$1" "$#"; GAME_SRC=$2; shift 2 ;;
        --dry-run)       DRY_RUN=1; shift ;;
        --modes)         need_arg "$1" "$#"; MODES=$2; shift 2 ;;
        --mode-index)    need_arg "$1" "$#"; MODE_INDEX=$2; shift 2 ;;
        --account)       need_arg "$1" "$#"; ACCOUNT=$2; ACCOUNT_SET=1; shift 2 ;;
        --dll-source)    need_arg "$1" "$#"; DLL_SOURCE=$2; shift 2 ;;
        --dll-dir)       need_arg "$1" "$#"; DLL_DIR=$2; shift 2 ;;
        --mugl-dll)      need_arg "$1" "$#"; MUGL_DLL=$2; DLL_SOURCE=files; shift 2 ;;
        --mscoree-dll)   need_arg "$1" "$#"; MSCOREE_DLL=$2; shift 2 ;;
        --mugl-build)    need_arg "$1" "$#"; MUGL_BUILD=$2; shift 2 ;;
        --dotnet-installer) need_arg "$1" "$#"; DOTNET_INSTALLER=$2; shift 2 ;;
        --helpers-dir)   need_arg "$1" "$#"; HELPERS_DIR=$2; shift 2 ;;
        --timewalker-dir) need_arg "$1" "$#"; TIMEWALKER_DIR=$2; shift 2 ;;
        --mugl-version)  need_arg "$1" "$#"; MUGL_VERSION=$2; shift 2 ;;
        --hotpatch-mask) need_arg "$1" "$#"; HOTPATCH_MASK=$2; shift 2 ;;
        --no-mugl)       NO_MUGL=1; shift ;;
        --no-stats)      NO_STATS=1; shift ;;
        --reset-config)  RESET_CONFIG=1; shift ;;
        --launcher-name) need_arg "$1" "$#"; LAUNCHER_NAME=$2; shift 2 ;;
        --no-desktop)    NO_DESKTOP=1; shift ;;
        --fast-x87)      FAST_X87=1; shift ;;
        --fast-x87-dir)  need_arg "$1" "$#"; FAST_X87_DIR=$2; FAST_X87=1; shift 2 ;;
        --ac-variant)    need_arg "$1" "$#"; AC_VARIANT=$2; shift 2 ;;
        --skip-verify)   SKIP_VERIFY=1; shift ;;
        -h|--help)       usage; exit 0 ;;
        *)               mukit_die "Unknown argument: $1 (see --help)" ;;
    esac
done
export DRY_RUN CX_ROOT
# --bottle without --runtime keeps the earlier behaviour (CrossOver); otherwise the free runtime.
[ -n "$RUNTIME" ] || { [ "$BOTTLE_SET" = 1 ] && RUNTIME=crossover || RUNTIME=free; }
mukit_runtime_valid "$RUNTIME" || mukit_die '--runtime must be free or crossover'

FREE_HOME=$MUKIT_FREE_HOME
RT_DIR=; RT_ID=; WINE_BIN=; WINESERVER_BIN=
if [ "$RUNTIME" = free ]; then
    PREFIX=${PREFIX_OPT:-$FREE_HOME/prefix}
    case "$PREFIX" in /*) ;; *) PREFIX="$PWD/$PREFIX" ;; esac
    if [ -z "$RT_ARCHIVE" ] && [ -n "$MUKIT_RT_ARCHIVE_URL" ]; then RT_ARCHIVE=$MUKIT_RT_ARCHIVE_URL; RT_ARCHIVE_SHA=$MUKIT_RT_ARCHIVE_SHA256; fi
    if [ -n "$RT_ARCHIVE" ]; then
        case "$RT_ARCHIVE" in
            https://*) [[ "$RT_ARCHIVE_SHA" =~ ^[0-9a-f]{64}$ ]] || mukit_die '--runtime-archive URL needs --runtime-sha256 (64 hex digits)' ;;
            *) [ -f "$RT_ARCHIVE" ] || mukit_die "--runtime-archive not found: $RT_ARCHIVE"
               [ -n "$RT_ARCHIVE_SHA" ] || RT_ARCHIVE_SHA=$(mukit_sha256 "$RT_ARCHIVE") ;;
        esac
        RT_ID="archive-${RT_ARCHIVE_SHA:0:12}"
    else
        RT_ID=cx24.0.7-7
    fi
    RT_DIR="$FREE_HOME/runtime/$RT_ID"
    WINE_BIN=$(mukit_rt_wine "$RT_DIR"); WINESERVER_BIN=$(mukit_rt_wineserver "$RT_DIR")
    [ "$BOTTLE_SET" = 0 ] || mukit_warn '--bottle applies to --runtime crossover only; ignored.'
    BOTTLE=$(basename "$PREFIX")
else
    PREFIX="$MUKIT_BOTTLES_DIR/$BOTTLE"
fi
STATE="$PREFIX/.mukit"
GAME="$PREFIX/drive_c/MuTheMatrix"
MUTOOLS="$PREFIX/drive_c/mutools"
SYS32="$PREFIX/drive_c/windows/system32"
OWNER_MARKER=$MUKIT_OWNER_MARKER; [ "$RUNTIME" = free ] && OWNER_MARKER=$MUKIT_FREE_OWNER_MARKER
WINE_USED=0
BUILD_DIR=${MUKIT_BUILD_DIR:-$KIT_DIR/build}     # ignored by git; holds the cache of locally built DLLs
PRIVATE_BUILD_DIR=${MUKIT_PRIVATE_BUILD_DIR:-$MAC_PLAY/hotpatch/build/private}   # make -C mac-play/hotpatch private
# winetricks 20260125 sets XDG_CACHE_HOME=~/.cache before its macOS branch, so on a Mac its cache is
# ~/.cache/winetricks, not ~/Library/Caches/winetricks. Pin it (W_CACHE overrides).
WT_CACHE=${W_CACHE:-${XDG_CACHE_HOME:-$HOME/.cache}/winetricks}
DOTNET_APPLIED=0
LOCK=

say()  { printf '%s\n' "$*"; }
skip() { printf '  [ok]   %s\n' "$*"; }
todo() { printf '  [do]   %s\n' "$*"; }

# steplog NAME CMD...: run a Wine/winetricks step with output appended to its log.
# The commands themselves go through mukit_run, so dry-run prints them instead.
steplog() {
    local name=$1; shift
    WINE_USED=1
    if [ "$DRY_RUN" = 1 ]; then "$@"; return 0; fi
    mkdir -p "$STATE"
    say "         log: $STATE/$name.log"
    "$@" >> "$STATE/$name.log" 2>&1
}

# Never hand agent/session variables to Wine processes (they show up in Windows command lines).
WINE_ENV=(env -u WINEARCH -u WINEDLLOVERRIDES)
for _v in $(env | sed -n 's/^\(CLAUDE[A-Za-z0-9_]*\)=.*/\1/p'); do WINE_ENV+=(-u "$_v"); done; unset _v

wine_bottle() {
    if [ "$RUNTIME" = free ]; then mukit_run "${WINE_ENV[@]}" WINEPREFIX="$PREFIX" WINEDEBUG=-all "$WINE_BIN" "$@"
    else mukit_run "$CX_ROOT/bin/wine" --bottle "$BOTTLE" "$@"; fi
}
wineserver_wait() {
    if [ "$RUNTIME" != free ]; then WINEPREFIX="$PREFIX" "$CX_ROOT/bin/wineserver" -w; return; fi
    # In a 32-bit prefix in wow64 mode the service processes (services, svchost, winedevice) stay up after the
    # last program exits, so "wineserver -w" would wait forever. Wait a while, then stop the prefix's
    # wineserver; it saves the registry when it exits.
    local t=0 w
    WINEPREFIX="$PREFIX" "$WINESERVER_BIN" -w & w=$!
    while kill -0 "$w" 2>/dev/null && [ "$t" -lt "${MUKIT_WINESERVER_WAIT:-20}" ]; do sleep 1; t=$((t + 1)); done
    if kill -0 "$w" 2>/dev/null; then
        WINEPREFIX="$PREFIX" "$WINESERVER_BIN" -k 2>/dev/null
        t=0; while kill -0 "$w" 2>/dev/null && [ "$t" -lt 30 ]; do sleep 1; t=$((t + 1)); done
        kill "$w" 2>/dev/null
    fi
    wait "$w" 2>/dev/null
    return 0
}

winetricks_bottle() {
    local wt
    if [ "$RUNTIME" = free ] && [ -z "${WINETRICKS:-}" ]; then
        wt="$FREE_HOME/tools/winetricks"
        [ -x "$wt" ] || [ "$DRY_RUN" = 1 ] || mukit_die "winetricks missing at $wt"
        # Plain Wine needs no shims; WINEARCH stays unset (the prefix already is 32-bit).
        mukit_run "${WINE_ENV[@]}" WINEPREFIX="$PREFIX" WINEDEBUG=-all W_CACHE="$WT_CACHE" \
            WINE="$WINE_BIN" WINESERVER="$WINESERVER_BIN" /bin/bash "$wt" -q "$@"
        return
    fi
    wt=$(command -v "${WINETRICKS:-winetricks}") || {
        [ "$DRY_RUN" = 1 ] || mukit_die 'winetricks not found (brew install winetricks).'
        mukit_warn 'winetricks not found (brew install winetricks)'; wt=winetricks; }
    if [ "$RUNTIME" = free ]; then
        mukit_run "${WINE_ENV[@]}" WINEPREFIX="$PREFIX" WINEDEBUG=-all W_CACHE="$WT_CACHE" \
            WINE="$WINE_BIN" WINESERVER="$WINESERVER_BIN" "$wt" -q "$@"
        return
    fi
    [ -x "$MAC_PLAY/cxwine" ] && [ -x "$MAC_PLAY/cxwineserver" ] || mukit_die "Missing cxwine/cxwineserver shims in $MAC_PLAY"
    # CrossOver's WoW64 runtime rejects WINEARCH=win32 even for win32 bottles; never export it.
    # W_CACHE is passed explicitly so the cache the kit seeds is the one winetricks reads.
    mukit_run env -u WINEARCH CX_BOTTLE="$BOTTLE" WINEPREFIX="$PREFIX" WINEDEBUG=-all W_CACHE="$WT_CACHE" \
        WINE="$MAC_PLAY/cxwine" WINESERVER="$MAC_PLAY/cxwineserver" "$wt" -q "$@"
}

# ======================================================================= steps
# Each step = check_X (returns 0 when nothing to do, printing why) + apply_X.

# --- 1. preflight -----------------------------------------------------------
preflight() {
    if [ "$RUNTIME" = free ]; then say "mu-mac-kit setup v$MUKIT_VERSION  runtime=free ($RT_ID)  prefix=$PREFIX  dry-run=$DRY_RUN"
    else say "mu-mac-kit setup v$MUKIT_VERSION  runtime=crossover  bottle=$BOTTLE  dry-run=$DRY_RUN"; fi
    # MUKIT_SKIP_PLATFORM_CHECK=1 exists only so the synthetic test suite can run on Linux CI.
    [ "$(uname -s)" = Darwin ] || [ "${MUKIT_SKIP_PLATFORM_CHECK:-0}" = 1 ] || mukit_die 'macOS required.'
    [ "$(uname -m)" = arm64 ] || [ "${MUKIT_SKIP_PLATFORM_CHECK:-0}" = 1 ] || mukit_warn 'Not Apple Silicon; only arm64 + Rosetta has been tested.'
    [ "$(id -u)" != 0 ] || mukit_die 'Do not run the setup as root (sudo); run it as your normal user.'
    if [ "$RUNTIME" = free ]; then
        if [ "${MUKIT_SKIP_PLATFORM_CHECK:-0}" != 1 ] && ! mukit_rosetta_ok; then
            mukit_die 'Rosetta 2 is not installed. Install it with: softwareupdate --install-rosetta --agree-to-license (then rerun).'
        fi
        [ ! -L "$PREFIX" ] || mukit_die 'Refusing a symlinked prefix.'
        case "$PREFIX" in "$MUKIT_BOTTLES_DIR"/*) mukit_die "Refusing a prefix inside CrossOver's bottle folder ($PREFIX)." ;; esac
        if [ -e "$PREFIX" ] && [ -n "$(ls -A "$PREFIX" 2>/dev/null)" ]; then
            [ "$(cat "$STATE/owner" 2>/dev/null)" = "$OWNER_MARKER" ] ||
                mukit_die "Prefix $PREFIX exists but was not created by this setup (no $STATE/owner). Choose a new --prefix."
        fi
        local kb need=$((6 * 1024 * 1024))
        [ -n "$GAME_INSTALLER" ] && need=$((12 * 1024 * 1024))
        mkdir -p "$FREE_HOME" 2>/dev/null || [ "$DRY_RUN" = 1 ] || mukit_die "Cannot create $FREE_HOME"
        kb=$(mukit_free_kb "$FREE_HOME" 2>/dev/null || mukit_free_kb "$HOME")
        if [[ "$kb" =~ ^[0-9]+$ ]] && [ "$kb" -lt "$need" ] && [ ! -f "$GAME/main.exe" ]; then
            mukit_die "Not enough free disk space: $((kb / 1024 / 1024)) GB free, about $((need / 1024 / 1024)) GB needed."
        fi
    else
        mukit_valid_bottle_name "$BOTTLE" || mukit_die 'Bottle name: letters, digits, _ and - only.'
        mukit_is_protected_bottle "$BOTTLE" && mukit_die "Refusing protected bottle '$BOTTLE' (the kit never modifies it)."
        if [ ! -x "$CX_ROOT/bin/cxbottle" ] || [ ! -x "$CX_ROOT/bin/wine" ] || [ ! -x "$CX_ROOT/bin/wineserver" ]; then
            [ "$DRY_RUN" = 1 ] && mukit_warn "CrossOver tools missing at $CX_ROOT" || mukit_die "CrossOver tools missing at $CX_ROOT"
        fi
        [ ! -L "$PREFIX" ] || mukit_die 'Refusing a symlinked bottle.'
        if [ -e "$PREFIX" ]; then
            [ "$(cat "$STATE/owner" 2>/dev/null)" = "$OWNER_MARKER" ] ||
                mukit_die "Bottle $PREFIX exists but was not created by this kit (no $STATE/owner). Choose a new --bottle name."
        fi
    fi
    case "$DLL_SOURCE" in
        auto)
            if [ -n "$DLL_DIR" ]; then DLL_SOURCE=prebuilt
            elif command -v "$MINGW_CC" >/dev/null 2>&1 && [ -f "$MAC_PLAY/mugl/Makefile" ] && [ -f "$MAC_PLAY/mumodes/mscoree_proxy.c" ]; then DLL_SOURCE=build
            else DLL_SOURCE=none; fi ;;
        prebuilt|build) ;;
        files) [ -f "$MUGL_DLL" ] || mukit_die "--mugl-dll not found: $MUGL_DLL"
               [ -z "$MSCOREE_DLL" ] || [ -f "$MSCOREE_DLL" ] || mukit_die "--mscoree-dll not found: $MSCOREE_DLL" ;;
        *) mukit_die '--dll-source must be auto, build or prebuilt' ;;
    esac
    if [ "$DLL_SOURCE" = none ]; then
        mukit_warn "No prebuilt DLLs (--dll-dir) and no MinGW ($MINGW_CC): installing without mugl and the mscoree proxy. Expect low fps; the launcher's own resolution list is used."
        NO_MUGL=1
    fi
    case "$MUGL_BUILD" in public|private) ;; *) mukit_die '--mugl-build must be public or private' ;; esac
    if [ "$DLL_SOURCE" = prebuilt ]; then
        [ -n "$DLL_DIR" ] || mukit_die '--dll-source prebuilt needs --dll-dir (or MU_DLL_DIR) with your pinned mugl/mscoree DLLs; the repository does not ship them. Use the default --dll-source build otherwise.'
        [ -d "$DLL_DIR" ] || mukit_die "--dll-dir not found: $DLL_DIR"
    fi
    mukit_mugl_version_sha "$MUGL_VERSION" >/dev/null || mukit_die '--mugl-version must be v75, v72, v71 or v70'
    mukit_hotpatch_valid "$HOTPATCH_MASK" || mukit_die "--hotpatch-mask must be 0-$MUKIT_HOTPATCH_MAX"
    [ $((HOTPATCH_MASK & MUKIT_HOTPATCH_V70_BITS)) = "$MUKIT_HOTPATCH_V70_BITS" ] ||
        mukit_warn "--hotpatch-mask $HOTPATCH_MASK turns off some of the v7.0 base patches (bits 1|2|4|8); expect lower fps."
    case "$AC_VARIANT" in with-ac|no-ac) ;; *) mukit_die '--ac-variant must be with-ac or no-ac' ;; esac
    [ -z "$GAME_SRC" ] || [ -z "$GAME_INSTALLER" ] || mukit_die 'Use either --game-dir or --game-installer, not both.'
    if [ -n "$GAME_INSTALLER" ]; then
        [ "$GAME_INSTALLER" != official ] || GAME_INSTALLER=$MUKIT_GAME_INSTALLER_URL
        case "$GAME_INSTALLER" in
            https://*) ;;
            *) [ -f "$GAME_INSTALLER" ] || mukit_die "--game-installer not found: $GAME_INSTALLER"
               GAME_INSTALLER=$(cd -- "$(dirname -- "$GAME_INSTALLER")" && pwd -P)/$(basename -- "$GAME_INSTALLER") ;;
        esac
    fi
    if [ -n "$GAME_SRC" ]; then
        [ -d "$GAME_SRC" ] || mukit_die "--game-dir not found: $GAME_SRC"
        GAME_SRC=$(cd -- "$GAME_SRC" && pwd -P)
        [ -f "$GAME_SRC/main.exe" ] && [ -f "$GAME_SRC/MuTheMatrix.exe" ] || mukit_die '--game-dir must contain main.exe and MuTheMatrix.exe'
        case "$GAME_SRC/" in "$PREFIX/"*) mukit_die '--game-dir cannot be inside the target prefix.' ;; esac
        [ -z "$(find "$GAME_SRC" -type l -print -quit)" ] || mukit_die '--game-dir contains symlinks; refusing (the copy could point back into another install).'
    fi
    pick_display_modes
    if [ "$DRY_RUN" = 0 ]; then
        local lockdir=$MUKIT_BOTTLES_DIR
        [ "$RUNTIME" = free ] && lockdir=$FREE_HOME
        mkdir -p "$lockdir"
        LOCK="$lockdir/.$BOTTLE.mukit-lock"
        mkdir "$LOCK" 2>/dev/null || mukit_die "Setup lock exists: $LOCK (another setup running? remove it if stale)."
        trap 'rmdir "$LOCK" 2>/dev/null' EXIT
    fi
}

# The repository's public mugl (mac-play/mugl) has no display-mode hook.
mugl_is_public() { [ "$NO_MUGL" = 0 ] && [ "$DLL_SOURCE" = build ] && [ "$MUGL_BUILD" = public ]; }
# Without the mscoree proxy (no DLLs at all) neither program sees the curated mode list either.
modes_uncurated() { [ "$DLL_SOURCE" = none ]; }
# A --mugl-dll that is not a pinned v7.x build is treated like the public build (no mode hook).
mugl_files_unpinned() { [ "$DLL_SOURCE" = files ] && ! mukit_mugl_identify "$(mukit_sha256 "$MUGL_DLL")" >/dev/null; }

pick_display_modes() {
    local scr sw sh picked auto_idx
    if [ -z "$MODES" ]; then
        scr=$(mukit_screen_size)
        if [[ "$scr" =~ ^[0-9]+x[0-9]+$ ]]; then sw=${scr%x*}; sh=${scr#*x}; else sw=1800; sh=1169; mukit_warn 'Screen size unknown; assuming 1800x1169.'; fi
        picked=$(mukit_pick_modes "$sw" "$sh")
        MODES=${picked%|*}; auto_idx=${picked#*|}
        say "Display: ${sw}x${sh} -> modes \"$MODES\""
    else
        mukit_modes_valid "$MODES" || mukit_die "--modes must be 1-16 tokens like 1728x1080"
        auto_idx=$(( $(mukit_modes_count "$MODES") - 1 ))
    fi
    [ -n "$MODE_INDEX" ] || MODE_INDEX=$auto_idx
    [[ "$MODE_INDEX" =~ ^[0-9]+$ ]] || mukit_die '--mode-index must be a number'
    mukit_mode_at "$MODES" "$MODE_INDEX" >/dev/null || mukit_die "--mode-index $MODE_INDEX is outside the mode list"
    if { mugl_is_public || modes_uncurated || mugl_files_unpinned; } && [ "$MODE_INDEX" -gt 2 ]; then
        mukit_warn 'Public mugl build has no display-mode hook: main.exe uses its own list, capping DevModeIndex at 2 (1280x800).'
        MODE_INDEX=2
    fi
    say "DevModeIndex $MODE_INDEX = $(mukit_mode_at "$MODES" "$MODE_INDEX")"
}

# --- free runtime: Wine, winetricks, prefix -----------------------------------------
# The runtime folder: wine/{bin,lib,share} (the engine) plus the x86_64 dylibs it loads. For the default
# cx24 runtime the engine's binaries look for dylibs two levels up from bin/ and lib/wine/x86_64-unix/,
# i.e. in the runtime folder and in wine/lib; the template's dylibs go to the first and are linked
# from the second. An --runtime-archive already has this layout (see runtime/build-wine.sh).
check_runtime() {
    if mukit_rt_ok "$RT_DIR"; then skip "Wine runtime $RT_ID ($("$WINE_BIN" --version 2>/dev/null || echo '?'))"; return 0; fi
    [ "$DRY_RUN" = 1 ] && [ -x "$WINE_BIN" ] && return 0
    return 1
}
extract_into() {   # extract_into ARCHIVE DIR
    mukit_run mkdir -p "$2"
    mukit_run tar -xf "$1" -C "$2" || mukit_die "could not unpack $1"
}
apply_runtime() {
    local dl="$FREE_HOME/downloads" tmp="$RT_DIR.partial" f
    [ ! -e "$tmp" ] || mukit_run rm -rf -- "$tmp"
    if [ -n "$RT_ARCHIVE" ]; then
        todo "install the Wine runtime from $RT_ARCHIVE"
        f=$RT_ARCHIVE
        case "$RT_ARCHIVE" in https://*)
            f="$dl/runtime-$RT_ID.tar.xz"
            mukit_fetch "$RT_ARCHIVE" "$RT_ARCHIVE_SHA" "$f" || mukit_die "runtime download failed: $RT_ARCHIVE" ;;
        *) [ "$(mukit_sha256 "$f")" = "$RT_ARCHIVE_SHA" ] || mukit_die "$f does not match --runtime-sha256" ;;
        esac
        extract_into "$f" "$tmp"
        if [ "$DRY_RUN" = 0 ] && [ ! -x "$tmp/wine/bin/wine" ]; then
            mukit_die "runtime archive has no wine/bin/wine (expected layout: wine/{bin,lib,share} + dylibs)"
        fi
    else
        todo "download the free Wine runtime (CrossOver 24.0.7 open-source Wine, ~265 MB, LGPL) and its libraries"
        mukit_fetch "$MUKIT_RT_CX24_ENGINE_URL" "$MUKIT_RT_CX24_ENGINE_SHA256" "$dl/$(basename "$MUKIT_RT_CX24_ENGINE_URL")" || mukit_die 'runtime download failed'
        mukit_fetch "$MUKIT_RT_TEMPLATE_URL" "$MUKIT_RT_TEMPLATE_SHA256" "$dl/$(basename "$MUKIT_RT_TEMPLATE_URL")" || mukit_die 'runtime library download failed'
        extract_into "$dl/$(basename "$MUKIT_RT_CX24_ENGINE_URL")" "$tmp.engine"
        extract_into "$dl/$(basename "$MUKIT_RT_TEMPLATE_URL")" "$tmp.template"
        mukit_run mkdir -p "$tmp"
        mukit_run mv "$tmp.engine/wswine.bundle" "$tmp/wine"
        if [ "$DRY_RUN" = 0 ]; then
            local fw; fw=$(find "$tmp.template" -maxdepth 3 -type d -name Frameworks -path '*/Contents/*' | head -1)
            [ -n "$fw" ] || mukit_die 'runtime library archive has no Contents/Frameworks'
            cp -a "$fw"/*.dylib "$tmp/" || mukit_die 'could not copy runtime libraries'
            (cd "$tmp/wine/lib" && for f in ../../*.dylib; do ln -sf "$f" .; done) || mukit_die 'could not link runtime libraries'
        fi
        mukit_run rm -rf -- "$tmp.engine" "$tmp.template"
    fi
    # Downloaded with curl, so no quarantine flag; clear one anyway if a browser fetched the archive.
    [ "$DRY_RUN" = 1 ] || xattr -dr com.apple.quarantine "$tmp" 2>/dev/null || true
    mukit_write_file "$tmp/.mu-runtime" "id=$RT_ID"$'\n'"source=${RT_ARCHIVE:-$MUKIT_RT_CX24_ENGINE_URL}"$'\n'
    [ ! -e "$RT_DIR" ] || mukit_run rm -rf -- "$RT_DIR"
    mukit_run mv "$tmp" "$RT_DIR"
    [ "$DRY_RUN" = 1 ] || mukit_rt_ok "$RT_DIR" || mukit_die "runtime at $RT_DIR is incomplete"
    [ "$DRY_RUN" = 1 ] || "$WINE_BIN" --version >/dev/null 2>&1 || mukit_die "the Wine runtime does not start ($WINE_BIN --version); is Rosetta 2 installed?"
}
step_runtime_current() {   # which runtime the launcher uses
    local cur; cur=$(cat "$FREE_HOME/runtime/current" 2>/dev/null)
    [ "$cur" = "$RT_ID" ] && return 0
    todo "select runtime $RT_ID for the launcher ($FREE_HOME/runtime/current)"
    mukit_write_file "$FREE_HOME/runtime/current" "$RT_ID"$'\n'
}

check_winetricks_tool() {
    [ -n "${WINETRICKS:-}" ] && { skip "winetricks from WINETRICKS=$WINETRICKS"; return 0; }
    local wt="$FREE_HOME/tools/winetricks"
    if [ -f "$wt" ] && [ "$(mukit_sha256 "$wt")" = "$MUKIT_WINETRICKS_SHA256" ]; then skip "winetricks 20260125 (pinned)"; return 0; fi
    return 1
}
apply_winetricks_tool() {
    todo "download winetricks 20260125 (pinned SHA-256)"
    mukit_fetch "$MUKIT_WINETRICKS_URL" "$MUKIT_WINETRICKS_SHA256" "$FREE_HOME/tools/winetricks" || mukit_die 'winetricks download failed'
    mukit_run chmod 755 "$FREE_HOME/tools/winetricks"
}

# The 32-bit prefix: Wine's wow64 loader refuses WINEARCH=win32, but CodeWeavers' wineserver creates a
# 32-bit registry ("#arch=win32") when it is started with it, and the loader then runs the prefix in
# "32-bit prefix in Wow64 mode". 64-bit prefixes fail (the protected client far-jumps to selector 0x33).
check_prefix() {
    if [ -f "$PREFIX/system.reg" ]; then
        local arch; arch=$(mukit_prefix_arch "$PREFIX")
        [ "$arch" = win32 ] || mukit_die "Prefix $PREFIX is '${arch:-unknown}', not win32. Delete it and rerun (64-bit prefixes cannot run the game)."
        skip "prefix exists, #arch=win32"
        return 0
    fi
    return 1
}
apply_prefix() {
    todo "create the 32-bit Wine prefix $PREFIX"
    mukit_run mkdir -p "$PREFIX"
    mukit_run mkdir -p "$STATE"
    mukit_write_file "$STATE/owner" "$OWNER_MARKER"$'\n'
    if [ "$DRY_RUN" = 1 ]; then
        mukit_run env WINEARCH=win32 WINEPREFIX="$PREFIX" "$WINESERVER_BIN" -p 5
        wine_bottle wineboot -i
        return 0
    fi
    WINEARCH=win32 WINEPREFIX="$PREFIX" "$WINESERVER_BIN" -p 5 || mukit_die 'could not start the wineserver'
    # wine-mono/gecko would only be replaced by .NET 4.8 later; skip their install prompts.
    steplog prefix mukit_run "${WINE_ENV[@]}" WINEPREFIX="$PREFIX" WINEDEBUG=-all WINEDLLOVERRIDES='mscoree,mshtml=' \
        "$WINE_BIN" wineboot -i || mukit_die "wineboot failed (see $STATE/prefix.log)"
    wineserver_wait
    [ "$(mukit_prefix_arch "$PREFIX")" = win32 ] || mukit_die "New prefix is not 32-bit (see $STATE/prefix.log); delete $PREFIX and rerun."
    [ ! -e "$PREFIX/drive_c/windows/syswow64" ] || mukit_die 'New prefix has syswow64 (not a 32-bit prefix).'
}

# --- 2. bottle ---------------------------------------------------------------
check_bottle() {
    if [ -f "$PREFIX/cxbottle.conf" ]; then
        local arch; arch=$(mukit_conf_get "$PREFIX/cxbottle.conf" WineArch)
        [ "$arch" = win32 ] || mukit_die "Bottle WineArch is '${arch:-unset}', not win32. 64-bit bottles fail with 'rosetta error: invalid gdt selector index 6'. Create a new bottle."
        skip "bottle exists, WineArch=win32, template $(mukit_conf_get "$PREFIX/cxbottle.conf" Template)"
        return 0
    fi
    return 1
}
apply_bottle() {
    todo "create 32-bit CrossOver bottle '$BOTTLE' from the win10 template"
    local log="$MUKIT_BOTTLES_DIR/.$BOTTLE.mukit-create.log"
    [ "$DRY_RUN" = 1 ] || say "         log: $STATE/bottle.log"
    if [ "$DRY_RUN" = 1 ]; then
        mukit_run "$CX_ROOT/bin/cxbottle" --bottle "$BOTTLE" --create --template win10 --description "Mu The Matrix 32-bit (mu-mac-kit)"
    else
        "$CX_ROOT/bin/cxbottle" --bottle "$BOTTLE" --create --template win10 \
            --description "Mu The Matrix 32-bit (mu-mac-kit)" > "$log" 2>&1 || { cat "$log" >&2; mukit_die 'cxbottle --create failed'; }
    fi
    mukit_run mkdir -p "$STATE"
    mukit_write_file "$STATE/owner" "$MUKIT_OWNER_MARKER"$'\n'
    [ "$DRY_RUN" = 1 ] || mv "$log" "$STATE/bottle.log"
    if [ "$DRY_RUN" = 0 ]; then
        [ "$(mukit_conf_get "$PREFIX/cxbottle.conf" WineArch)" = win32 ] ||
            mukit_die "New bottle is not WineArch=win32 (see README troubleshooting). Delete it: cxbottle --bottle $BOTTLE --delete"
    fi
}

# --- 3. .NET Framework 4.8 ---------------------------------------------------
check_dotnet48() {
    local st; st=$(mukit_dotnet48_state "$PREFIX")
    case "$st" in ok*) set -- $st; skip ".NET 4.8 present (Release $2, $3)"; return 0 ;; esac
    say "  [need] .NET 4.8: ${st#missing }"
    return 1
}
apply_dotnet48() {
    if [ "$RUNTIME" = free ]; then todo 'install .NET Framework 4.8 with winetricks (downloads Microsoft'"'"'s installers, several minutes)'
    else todo 'install .NET Framework 4.8 with winetricks through the cxwine/cxwineserver shims (several minutes)'; fi
    local s64="$PREFIX/drive_c/windows/syswow64" cache="$WT_CACHE/dotnet48" local_exe=$DOTNET_INSTALLER
    # winetricks infers win64 from syswow64's existence; remove it only when empty.
    if [ -d "$s64" ]; then mukit_run rmdir "$s64" || mukit_die 'syswow64 is not empty; this is not a clean 32-bit bottle.'; fi
    # Pre-seed winetricks' cache from your own copy of Microsoft's installer (only if its SHA-256 matches).
    if [ ! -f "$cache/ndp48-x86-x64-allos-enu.exe" ] && [ -n "$local_exe" ]; then
        if [ -f "$local_exe" ] && [ "$(mukit_sha256 "$local_exe")" = "$MUKIT_DOTNET48_INSTALLER_SHA256" ]; then
            mukit_run mkdir -p "$cache"
            mukit_run cp "$local_exe" "$cache/ndp48-x86-x64-allos-enu.exe"
        else
            mukit_warn "--dotnet-installer $local_exe is missing or does not match the pinned SHA-256; winetricks will download it."
        fi
    fi
    DOTNET_APPLIED=1
    steplog dotnet48 winetricks_bottle dotnet48 || mukit_die "winetricks dotnet48 failed (see $STATE/dotnet48.log)"
    [ "$DRY_RUN" = 1 ] || check_dotnet48 || mukit_die "winetricks finished but .NET 4.8 is not installed (see $STATE/dotnet48.log)"
}

# --- 4. Windows version ------------------------------------------------------
check_winver() {
    local pn; pn=$(mukit_reg_value "$PREFIX/system.reg" 'Software\Microsoft\Windows NT\CurrentVersion' ProductName 2>/dev/null)
    case "$pn" in *"Windows 10"*) skip "Windows version: $pn"; return 0 ;; esac
    return 1
}
apply_winver() {
    # winetricks dotnet48 runs "w_set_winver win7"; the working bottle reports Windows 10.
    todo 'set Windows version back to win10 (winetricks dotnet48 leaves win7)'
    steplog winver winetricks_bottle win10 || mukit_die 'winetricks win10 failed'
}

# --- 5. registry -------------------------------------------------------------
check_registry() {
    local f k n v c file got missing=0
    while IFS='|' read -r f k n v c; do
        file="$PREFIX/$f.reg"
        got=$(mukit_reg_value "$file" "$k" "$n" 2>/dev/null) || { missing=1; break; }
        if [ "$c" = order ]; then mukit_loadorder_eq "$got" "$v" || { missing=1; break; }
        else [ "$got" = "$v" ] || { missing=1; break; }; fi
    done < <(mukit_registry_expectations "$((1 - NO_STATS))")
    if [ "$NO_STATS" = 1 ] && mukit_reg_get "$PREFIX/user.reg" Environment MUGL_STATS >/dev/null 2>&1; then missing=1; fi
    [ "$missing" = 0 ] && { skip 'registry values present'; return 0; }
    return 1
}
apply_registry() {
    todo "import registry/mu-mac.reg with regedit (WPF software rendering, DLL overrides, AeDebug off, MUGL_STATS $([ "$NO_STATS" = 1 ] && echo removed || echo set))"
    local reg="$KIT_DIR/registry/mu-mac.reg" content
    content=$(cat "$reg") || mukit_die "missing $reg"
    if [ "$NO_STATS" = 1 ]; then
        content=$(printf '%s\n' "$content" | sed 's/^"MUGL_STATS"=.*/"MUGL_STATS"=-/')
    fi
    mukit_run mkdir -p "$MUTOOLS"
    # regedit reads CRLF REGEDIT4 text from inside the bottle.
    mukit_write_file "$MUTOOLS/mu-mac.reg" "$(printf '%s\n' "$content" | sed 's/$/\r/')"$'\n'
    steplog registry wine_bottle regedit /S 'C:\mutools\mu-mac.reg' || mukit_die 'regedit import failed'
}

# --- 6. game files -----------------------------------------------------------
check_game() {
    if [ -f "$GAME/main.exe" ] && [ -f "$GAME/MuTheMatrix.exe" ]; then
        local h; h=$(mukit_sha256 "$GAME/main.exe")
        [ "$h" = "$MUKIT_MAIN_EXE_SHA256" ] || mukit_warn "C:\\MuTheMatrix\\main.exe SHA-256 $h differs from the tested client $MUKIT_MAIN_EXE_SHA256"
        skip 'game present in C:\MuTheMatrix'
        return 0
    fi
    return 1
}
apply_game() {
    if [ -z "$GAME_SRC" ] && [ -n "$GAME_INSTALLER" ]; then apply_game_installer; return; fi
    [ -n "$GAME_SRC" ] || {
        local hint="$MUKIT_BOTTLES_DIR/Windows10MU/drive_c/Program Files (x86)/Glitch Games Network/Mu The Matrix"
        [ -d "$hint" ] && mukit_note "Hint: your Windows install looks like --game-dir '$hint'"
        mukit_die 'Game not installed in the prefix yet: pass --game-dir with your Mu The Matrix client folder, or --game-installer official to download and run the official installer.'
    }
    todo "copy client from $GAME_SRC to C:\\MuTheMatrix (APFS clone when possible)"
    local partial="$GAME.mukit-partial"
    [ ! -e "$partial" ] || mukit_die "Incomplete copy at $partial; inspect and remove it, then rerun."
    [ ! -e "$GAME" ] || [ -z "$(ls -A "$GAME" 2>/dev/null)" ] || mukit_die "$GAME exists without main.exe/MuTheMatrix.exe; inspect it first."
    mukit_run mkdir -p "$PREFIX/drive_c"
    # macOS: APFS clone (cp -c). Elsewhere (the Linux test run) a plain copy.
    local clone=; [ "$(uname -s)" = Darwin ] && clone=-c
    if ! mukit_run cp $clone -R "$GAME_SRC" "$partial" 2>/dev/null; then
        mukit_warn 'APFS clone failed (different volume?); doing a full copy.'
        [ ! -e "$partial" ] || mukit_run rm -rf -- "$partial"
        if command -v ditto >/dev/null 2>&1; then mukit_run ditto "$GAME_SRC" "$partial" || mukit_die 'copy failed'
        else mukit_run cp -R "$GAME_SRC" "$partial" || mukit_die 'copy failed'; fi
    fi
    # Never carry over the 3 GB recovery transfer archive (APFS clones it for free; drop it).
    mukit_run rm -f -- "$partial/.mu-recovery-transfer.tar"
    [ ! -d "$GAME" ] || mukit_run rmdir "$GAME"
    mukit_run mv "$partial" "$GAME"
    mukit_write_file "$STATE/game-source" "$GAME_SRC"$'\n'
    check_game >/dev/null || [ "$DRY_RUN" = 1 ]
}

# The official installer (Actual Installer) run silently inside the prefix with /S. It installs to its
# default folder (C:\Program Files\Glitch Games Network\Mu The Matrix in a 32-bit prefix; verified with
# MuTheMatrix-21.1.2.12.exe, 206 s), which is then moved to C:\MuTheMatrix where the kit expects the game.
GAME_INSTALLER_DEFAULT_DIRS="Program Files/Glitch Games Network/Mu The Matrix|Program Files (x86)/Glitch Games Network/Mu The Matrix"
apply_game_installer() {
    local exe=$GAME_INSTALLER d found=
    case "$GAME_INSTALLER" in https://*)
        exe="$FREE_HOME/downloads/$(basename "${GAME_INSTALLER%%\?*}")"
        todo "download the official game installer $GAME_INSTALLER (about 2.2 GB; resumes if interrupted)"
        mukit_fetch "$GAME_INSTALLER" - "$exe" || mukit_die "game installer download failed: $GAME_INSTALLER" ;;
    esac
    [ "$DRY_RUN" = 1 ] || mukit_write_file "$STATE/game-installer" "$(basename "$exe") sha256=$(mukit_sha256 "$exe")"$'\n'
    [ ! -e "$GAME" ] || [ -z "$(ls -A "$GAME" 2>/dev/null)" ] || mukit_die "$GAME exists without main.exe/MuTheMatrix.exe; inspect it first."
    todo "run the official installer silently in the prefix (about 4 minutes)"
    steplog game-installer wine_bottle "$exe" /S || mukit_warn "the installer returned an error (see $STATE/game-installer.log)"
    [ "$DRY_RUN" = 1 ] && return 0
    wineserver_wait
    if [ ! -f "$GAME/main.exe" ]; then
        local IFS='|'
        for d in $GAME_INSTALLER_DEFAULT_DIRS; do
            [ -f "$PREFIX/drive_c/$d/main.exe" ] && { found="$PREFIX/drive_c/$d"; break; }
        done
        unset IFS
        [ -n "$found" ] || mukit_die "The installer finished, but main.exe was not found (see $STATE/game-installer.log)."
        todo "move the installed game from ${found#$PREFIX/drive_c/} to C:\\MuTheMatrix"
        [ ! -d "$GAME" ] || rmdir "$GAME" 2>/dev/null || mukit_die "$GAME is in the way"
        mv "$found" "$GAME" || mukit_die "could not move $found"
    fi
    mukit_write_file "$STATE/game-source" "installer:$(basename "$exe")"$'\n'
    check_game >/dev/null || mukit_die "game files incomplete after the installer (see $STATE/game-installer.log)"
}

# --- 7. launcher .NET config -------------------------------------------------
LAUNCHER_CONFIG=$'<?xml version="1.0" encoding="utf-8"?>\r\n<configuration>\r\n  <configSections />\r\n  <startup useLegacyV2RuntimeActivationPolicy="true">\r\n    <supportedRuntime version="v4.0" sku=".NETFramework,Version=v4.8"/>\r\n  </startup>\r\n</configuration>\r\n'
check_launcher_config() {
    local f="$GAME/MuTheMatrix.exe.config"
    if [ -f "$f" ] && grep -q 'supportedRuntime version="v4.0"' "$f"; then skip 'MuTheMatrix.exe.config selects the v4.0 runtime'; return 0; fi
    [ "$DRY_RUN" = 1 ] && [ ! -f "$GAME/MuTheMatrix.exe" ] && { skip '(after game copy) MuTheMatrix.exe.config will be checked'; return 0; }
    return 1
}
apply_launcher_config() {
    todo 'write MuTheMatrix.exe.config selecting .NET 4.8 (original kept as .mukit-orig)'
    local f="$GAME/MuTheMatrix.exe.config"
    [ ! -f "$f" ] || [ -f "$f.mukit-orig" ] || mukit_run cp "$f" "$f.mukit-orig"
    mukit_write_file "$f" "$LAUNCHER_CONFIG"
}

# --- 8. launcher skin (every run; game updates may restore it) ---------------
check_skin() {
    if [ "$DRY_RUN" = 1 ] && [ ! -d "$GAME" ] && [ -f "$GAME_SRC/Data/Launcher/Design/Template.design" ]; then
        return 1   # dry-run: the copied client will still contain the custom skin
    fi
    if [ ! -f "$GAME/Data/Launcher/Design/Template.design" ]; then skip 'custom launcher skin Template.design disabled/absent'; return 0; fi
    return 1
}
apply_skin() {
    local file="$GAME/Data/Launcher/Design/Template.design" backup n=1
    backup="$file.disabled"
    while [ -e "$backup" ]; do backup="$file.disabled.$n"; n=$((n + 1)); done
    todo "rename Template.design -> $(basename "$backup") (custom GIF skin aborts the launcher constructor)"
    mukit_run mv "$file" "$backup"
}

# --- 9. C:\mutools -------------------------------------------------------------
# want_file PATH CONTENT LABEL [OLD_DEFAULTS]: create when missing; overwrite a different file only
# with --reset-config, or when it still holds a value an earlier kit version wrote (OLD_DEFAULTS,
# space-separated first lines), since that was never the user's choice.
want_file() {
    local path=$1 content=$2 label=$3 olds=${4:-} cur first o
    if [ -f "$path" ]; then
        cur=$(cat "$path"; printf x); cur=${cur%x}
        [ "$cur" = "$content" ] && return 0
        first=$(printf '%s' "$cur" | head -1 | tr -d '\r ')
        for o in $olds; do
            [ "$first" = "$o" ] && { todo "upgrade $label from earlier kit default '$o'"; mukit_write_file "$path" "$content"; return 0; }
        done
        if [ "$RESET_CONFIG" = 0 ]; then
            say "  [keep] $label differs ($(printf '%s' "$cur" | head -1 | tr -d '\r')); --reset-config overwrites"
            return 0
        fi
    fi
    todo "write $label"
    mukit_write_file "$path" "$content"
}
want_copy() {
    local src=$1 dst=$2 label=$3 optional=${4:-}
    if [ ! -f "$src" ] && [ "$optional" = optional ]; then return 0; fi
    if [ ! -f "$src" ]; then mukit_warn "$label source missing: $src (automation helpers unavailable; 'make mac-diagnostics' builds muinput.exe)"; return 0; fi
    [ -f "$dst" ] && [ "$(mukit_sha256 "$src")" = "$(mukit_sha256 "$dst")" ] && return 0
    todo "copy $label"
    mukit_run cp "$src" "$dst"
}
step_mutools() {
    [ -d "$MUTOOLS" ] || { todo 'create C:\mutools'; mukit_run mkdir -p "$MUTOOLS"; }
    want_file "$MUTOOLS/mu-modes.txt" "$MODES"$'\n' 'C:\mutools\mu-modes.txt'
    want_file "$MUTOOLS/mugl-mode.txt" $'full+vbo\n' 'C:\mutools\mugl-mode.txt'
    want_file "$MUTOOLS/mugl-hotpatch.txt" "$HOTPATCH_MASK"$'\n' 'C:\mutools\mugl-hotpatch.txt' \
        "$([ "$HOTPATCH_MASK" = "$MUKIT_HOTPATCH_DEFAULT" ] && echo "$MUKIT_HOTPATCH_OLD_DEFAULTS")"
    want_copy "$HELPERS_DIR/muinput.exe" "$MUTOOLS/muinput.exe" 'C:\mutools\muinput.exe' "$([ "$RUNTIME" = free ] && echo optional)"
    want_copy "$HELPERS_DIR/clickstart.exe" "$MUTOOLS/clickstart.exe" 'C:\mutools\clickstart.exe' optional
    skip 'C:\mutools checked'
}

# --- 10. LauncherOption.if ---------------------------------------------------
step_launcher_options() {
    local f="$GAME/LauncherOption.if" cur_idx= cur_wm= cur_id= want
    if [ "$DRY_RUN" = 1 ] && [ ! -d "$GAME" ]; then todo "write LauncherOption.if DevModeIndex:$MODE_INDEX WindowMode:1${ACCOUNT:+ ID:$ACCOUNT}"; return 0; fi
    if [ -f "$f" ]; then
        cur_idx=$(mukit_lopt_get "$f" DevModeIndex); cur_wm=$(mukit_lopt_get "$f" WindowMode); cur_id=$(mukit_lopt_get "$f" ID)
    fi
    [ "$ACCOUNT_SET" = 1 ] || ACCOUNT=$cur_id
    # A DevModeIndex different from the wanted one is kept only if the user chose it (in the
    # launcher's Settings): i.e. it differs from the index the kit itself wrote last time
    # (recorded in launcher-options.done). A kit-written value, such as the --mugl-repo cap, follows the options.
    local kit_idx=; [ -f "$STATE/launcher-options.done" ] && kit_idx=$(head -1 "$STATE/launcher-options.done" | tr -d ' \r')
    if [ -f "$f" ] && [ "$cur_wm" = 1 ] && [ "$cur_id" = "$ACCOUNT" ] && [[ "$cur_idx" =~ ^[0-9]+$ ]] &&
       mukit_mode_at "$MODES" "$cur_idx" >/dev/null &&
       { [ "$cur_idx" = "$MODE_INDEX" ] || { [ "$RESET_CONFIG" = 0 ] && [ -f "$STATE/launcher-options.done" ] && [ "$cur_idx" != "$kit_idx" ]; }; }; then
        skip "LauncherOption.if DevModeIndex:$cur_idx ($(mukit_mode_at "$MODES" "$cur_idx")) WindowMode:1"
        return 0
    fi
    want=$(mukit_lopt_render "$MODE_INDEX" 1 "$ACCOUNT")
    todo "write LauncherOption.if DevModeIndex:$MODE_INDEX WindowMode:1 ID:${ACCOUNT:-<empty>} (original kept as .mukit-orig)"
    [ ! -f "$f" ] || [ -f "$f.mukit-orig" ] || mukit_run cp "$f" "$f.mukit-orig"
    mukit_write_file "$f" "$want"
    [ "$DRY_RUN" = 1 ] || printf '%s\n' "$MODE_INDEX" > "$STATE/launcher-options.done"
}

# --- 11. proxy DLLs ------------------------------------------------------------
# mscoree proxy from mac-play/mumodes (public source, no client-derived data): sets MSCOREE_SRC.
build_mscoree() {
    mukit_run mkdir -p "$BUILD_DIR"
    # Same flags as mac-play/hotpatch/Makefile 'modes'. SSE is mandatory.
    # No PE timestamp, so a rerun produces the same bytes and the installed copy stays "up to date".
    mukit_run sh -c 'cd "$1" && "$2" -O2 -msse2 -mfpmath=sse -ffp-contract=off -Wall -shared mscoree_proxy.c mstubs.S mscoree.def -o "$3" -Wl,--enable-stdcall-fixup -Wl,--no-insert-timestamp -static-libgcc' \
        sh "$MAC_PLAY/mumodes" "$MINGW_CC" "$BUILD_DIR/mscoree.dll" || mukit_die 'mscoree proxy build failed'
    MSCOREE_SRC="$BUILD_DIR/mscoree.dll"
}
resolve_dlls() {   # sets MUGL_SRC / MSCOREE_SRC (may build)
    MUGL_SRC=; MSCOREE_SRC=
    if [ "$DLL_SOURCE" = files ]; then
        MUGL_SRC=$MUGL_DLL
        local id; id=$(mukit_mugl_identify "$(mukit_sha256 "$MUGL_SRC")") ||
            mukit_warn "$MUGL_SRC is not a pinned mugl build; installing it as given."
        [ -z "${id:-}" ] || say "  [note] $MUGL_SRC is mugl $id (pinned)"
        if [ -n "$MSCOREE_DLL" ]; then MSCOREE_SRC=$MSCOREE_DLL
        elif command -v "$MINGW_CC" >/dev/null 2>&1; then build_mscoree
        else mukit_warn 'No --mscoree-dll and no MinGW: the launcher keeps its own resolution list.'; fi
        return 0
    fi
    if [ "$DLL_SOURCE" = build ]; then
        command -v "$MINGW_CC" >/dev/null || mukit_die "$MINGW_CC not found (brew install mingw-w64)"
        build_mscoree
        if [ "$NO_MUGL" = 1 ]; then
            :
        elif [ "$MUGL_BUILD" = private ]; then
            # Built by you from your own dump: python3 mac-play/hotpatch/generate.py ... && make -C mac-play/hotpatch private
            MUGL_SRC="$PRIVATE_BUILD_DIR/opengl32.dll"
            [ -f "$PRIVATE_BUILD_DIR/generation.json" ] && [ -f "$MUGL_SRC" ] ||
                mukit_die "--mugl-build private needs your own private build: $MUGL_SRC (see mac-play/hotpatch/README.md)"
            mukit_warn 'Installing a private hotpatch build: it contains client-derived bytes. Do not commit or redistribute it.'
        else
            # Build from a copy so the checkout's own mac-play/mugl/build is never written.
            local rb="$BUILD_DIR/mugl-public"
            [ -f "$MAC_PLAY/mugl/Makefile" ] || mukit_die "Missing $MAC_PLAY/mugl/Makefile"
            mukit_run rm -rf -- "$rb"
            mukit_run mkdir -p "$rb"
            mukit_run cp -R "$MAC_PLAY/mugl/." "$rb/"
            mukit_run rm -rf -- "$rb/build"
            # env -u and an explicit PYTHON: do not inherit a parent make's relative PYTHON=... or flags ('make test')
            mukit_run env -u MAKEFLAGS -u MAKELEVEL -u MFLAGS make -C "$rb" MINGW_CC="$MINGW_CC" PYTHON="${MUKIT_PYTHON:-python3}" || mukit_die 'public mugl build failed'
            MUGL_SRC="$rb/build/opengl32.dll"
        fi
    else
        MUGL_SRC="$DLL_DIR/mugl-$MUGL_VERSION.dll"; MSCOREE_SRC="$DLL_DIR/mscoree.dll"
        [ "$NO_MUGL" = 1 ] || [ -f "$MUGL_SRC" ] || mukit_die "Missing $MUGL_SRC (supply your own mugl-$MUGL_VERSION.dll in --dll-dir)"
        [ "$NO_MUGL" = 1 ] || [ "$(mukit_sha256 "$MUGL_SRC")" = "$(mukit_mugl_version_sha "$MUGL_VERSION")" ] || mukit_die "$MUGL_SRC does not match the pinned $MUGL_VERSION SHA-256"
        if [ -f "$MSCOREE_SRC" ]; then
            [ "$(mukit_sha256 "$MSCOREE_SRC")" = "$MUKIT_MSCOREE_PROXY_SHA256" ] || mukit_die "$MSCOREE_SRC does not match the pinned mscoree proxy SHA-256"
        else
            # The mscoree proxy is public source (mac-play/mumodes); a mugl-only --dll-dir
            # (such as a folder of mugl builds) is fine: build the proxy instead of refusing.
            command -v "$MINGW_CC" >/dev/null ||
                mukit_die "Missing $MSCOREE_SRC and $MINGW_CC to build it (put your mscoree.dll in --dll-dir, or brew install mingw-w64)"
            say "  [note] no mscoree.dll in --dll-dir; building the mscoree proxy from mac-play/mumodes"
            build_mscoree
        fi
    fi
}
deploy_dll() {   # deploy_dll SRC DST LABEL
    local src=$1 dst=$2 label=$3 hs hd
    hs=$( [ -f "$src" ] && mukit_sha256 "$src" || echo "(to be built)")
    hd=$(mukit_sha256 "$dst")
    if [ -n "$hd" ] && [ "$hs" = "$hd" ]; then
        skip "$label up to date (${hd:0:12})"
        # Already the wanted build (e.g. it came with the copied client): record it as kit-managed,
        # so switching builds later does not "back up" the kit's own file.
        [ "$DRY_RUN" = 1 ] || [ "$(cat "$STATE/$(basename "$dst").sha256" 2>/dev/null)" = "$hs" ] ||
            printf '%s\n' "$hs" > "$STATE/$(basename "$dst").sha256"
        return 0
    fi
    if [ -n "$hd" ] && [ ! -f "$STATE/$(basename "$dst").sha256" ]; then
        todo "back up existing $label to $(basename "$dst").mukit-backup-${hd:0:8}"
        mukit_run cp "$dst" "$dst.mukit-backup-${hd:0:8}"
    fi
    todo "install $label from $src (${hs:0:12})"
    mukit_run cp "$src" "$dst" || mukit_die "could not install $label from $src"
    mukit_write_file "$STATE/$(basename "$dst").sha256" "$hs"$'\n'
}
step_dlls() {
    if [ "$DRY_RUN" = 1 ] && [ ! -d "$SYS32" ]; then
        todo 'check system32\opengl32.dll is the Wine builtin (after bottle creation)'
    else
        mukit_pe_is_wine_builtin "$SYS32/opengl32.dll" ||
            mukit_die 'C:\windows\system32\opengl32.dll is not the Wine builtin; mugl would recurse into itself. Recreate the bottle.'
    fi
    [ "$DLL_SOURCE" = none ] && { say '  [skip] no DLLs (no --dll-dir, --mugl-dll or MinGW)'; return 0; }
    resolve_dlls
    [ "$DRY_RUN" = 1 ] || [ -d "$GAME" ] || mukit_die 'game directory missing'
    if [ "$NO_MUGL" = 1 ]; then
        say '  [skip] mugl disabled (--no-mugl); main.exe will use plain Wine OpenGL'
    else
        deploy_dll "$MUGL_SRC" "$GAME/opengl32.dll" 'mugl C:\MuTheMatrix\opengl32.dll'
    fi
    if [ -n "$MSCOREE_SRC" ]; then deploy_dll "$MSCOREE_SRC" "$GAME/mscoree.dll" 'mscoree proxy C:\MuTheMatrix\mscoree.dll'
    else say '  [skip] no mscoree proxy'; fi
}

# --- 12. Desktop launcher -----------------------------------------------------
step_desktop() {
    [ "$NO_DESKTOP" = 0 ] || { say '  [skip] --no-desktop'; return 0; }
    local name=${LAUNCHER_NAME:-"Play Mu The Matrix ($BOTTLE).command"} f content x87=0 rtenv
    [ "$RUNTIME" = free ] && name=${LAUNCHER_NAME:-"Play Mu The Matrix.command"}
    f="$HOME/Desktop/$name"
    [ -x "$KIT_DIR/play-mu.sh" ] || mukit_die "Missing $KIT_DIR/play-mu.sh"
    local twenv=
    if [ "$RUNTIME" = free ]; then [ "$FAST_X87" = 1 ] && x87=1
    else hook_fast_x87 && { x87=1; twenv=" MU_TIMEWALKER_DIR='$(cd -- "$TIMEWALKER_DIR" && pwd -P)'"; }; fi
    if [ "$RUNTIME" = free ]; then rtenv="MU_RUNTIME=free MU_PREFIX='$PREFIX'"; else rtenv="MU_BOTTLE='$BOTTLE'"; fi
    content=$(cat <<EOF
#!/bin/zsh
# mu-mac-kit launcher ($([ "$RUNTIME" = free ] && echo "free runtime, prefix $PREFIX" || echo "bottle $BOTTLE")). Double-click to play Mu The Matrix.
# play-mu.sh refuses a second instance, resets this bottle's wineserver (stale display state
# after sleep breaks the launcher) and starts C:\\MuTheMatrix\\MuTheMatrix.exe.
export $rtenv MU_FAST_X87=$x87$twenv
setopt NO_BG_NICE   # zsh runs '&' jobs at nice +5 by default; the game must run at normal priority
nohup '$KIT_DIR/play-mu.sh' >/dev/null 2>&1 &
sleep 1
osascript -e 'tell application "Terminal" to close (every window whose name contains "Play Mu The Matrix")' >/dev/null 2>&1 &
exit 0
EOF
)
    content="$content"$'\n'
    if [ -f "$f" ]; then
        grep -q '^# mu-mac-kit launcher' "$f" || mukit_die "$f exists and was not written by this kit; use --launcher-name"
        if [ "$(cat "$f"; printf x)" = "${content}x" ]; then skip "Desktop launcher $name"; return 0; fi
    fi
    todo "write Desktop launcher '$name' (MU_FAST_X87=$x87)"
    mukit_write_file "$f" "$content"
    mukit_run chmod 755 "$f"
}

# --- free runtime: fast x87 ---------------------------------------------------------
# Copies rosetta-timewalker's x87 translator (MIT) into the runtime folder and builds the authored main.exe-only
# loader wrapper (mac-play/x87-main-only-wrapper.c) unless the source folder already has it. play-mu.sh and
# Mu The Matrix.app use it when the runtime has the inner loader (the CrossOver 26.3 build does; cx24 does not).
step_fast_x87_free() {
    [ "$FAST_X87" = 1 ] || { say '  [skip] fast x87 not requested (--fast-x87 / --fast-x87-dir)'; return 0; }
    local src=$FAST_X87_DIR fx="$FREE_HOME/fast-x87" f s d
    if [ -z "$src" ] && [ -n "$TIMEWALKER_DIR" ]; then src="$TIMEWALKER_DIR/build"; fi
    [ -n "$src" ] || { mukit_warn 'fast x87 requested without --fast-x87-dir or --timewalker-dir; skipped.'; return 0; }
    local missing=0
    for f in libtimewalker.dylib runtime_loader libRuntimeRosettax87; do
        s="$src/$f"; [ -f "$s" ] || s="$src/x87/bin/$f"
        [ -f "$s" ] || { mukit_warn "fast x87: $f not found in $src"; missing=1; }
    done
    [ "$missing" = 0 ] || { mukit_warn 'fast x87 skipped (incomplete translator folder).'; return 0; }
    mukit_run mkdir -p "$fx"
    for f in libtimewalker.dylib runtime_loader libRuntimeRosettax87 x87-main-only-wrapper LICENSE LICENSE-rosettax87_jit THIRD_PARTY_NOTICES.md; do
        s="$src/$f"; [ -f "$s" ] || s="$src/x87/bin/$f"
        [ -f "$s" ] || continue
        d="$fx/$f"
        [ -f "$d" ] && [ "$(mukit_sha256 "$s")" = "$(mukit_sha256 "$d")" ] && continue
        todo "install fast x87 file $f"
        mukit_run cp "$s" "$d"
    done
    if [ ! -x "$fx/x87-main-only-wrapper" ] || [ "$DRY_RUN" = 1 ]; then
        if [ -f "$MAC_PLAY/x87-main-only-wrapper.c" ] && command -v xcrun >/dev/null 2>&1; then
            todo 'build the main.exe-only loader wrapper (mac-play/x87-main-only-wrapper.c)'
            mukit_run xcrun clang -arch arm64 -O2 -o "$fx/x87-main-only-wrapper" "$MAC_PLAY/x87-main-only-wrapper.c" || mukit_die 'wrapper build failed'
            mukit_run codesign -f -s - "$fx/x87-main-only-wrapper" >/dev/null 2>&1
        elif [ ! -x "$fx/x87-main-only-wrapper" ]; then
            mukit_warn 'fast x87: no x87-main-only-wrapper and no compiler; skipped.'; return 0
        fi
    fi
    # Copied out of a downloaded app: drop the quarantine flag, or macOS refuses to run the helpers.
    [ "$DRY_RUN" = 1 ] || xattr -dr com.apple.quarantine "$fx" 2>/dev/null || true
    [ -x "$RT_DIR/wine/lib/wine/x86_64-unix/wine" ] || [ "$DRY_RUN" = 1 ] ||
        mukit_warn "fast x87 installed, but runtime $RT_ID has no inner loader: the game runs with plain Rosetta (use the CrossOver 26.3 runtime archive)."
    skip "fast x87 translator in $fx"
}

# --- 13. TODO hooks -------------------------------------------------------------
# Fast x87 (rosetta-timewalker). Returns 0 when the launcher should enable it.
hook_fast_x87() {
    [ "$FAST_X87" = 1 ] || return 1
    local tw=$TIMEWALKER_DIR
    if [ -n "$tw" ] && [ -x "$tw/scripts/run-crossover.sh" ] && [ -f "$tw/build/libtimewalker.dylib" ]; then
        say '  [ok]   fast x87: using existing rosetta-timewalker build (TIMEWALKER_X87_ONLY=main.exe via play-mu.sh)'
        return 0
    fi
    # TODO(fast-x87): build/validate rosetta-timewalker here. The published, self-checking
    # installer is mac-play/install-fast-x87.sh (pinned commit ab1a6a03, cache
    # ~/Library/Caches/MuTheMatrix/fast-x87), but it only accepts bottles created by
    # mac-play/setup-crossover-32bit.sh and play-mu.sh expects a plain timewalker checkout in
    # --timewalker-dir / MU_TIMEWALKER_DIR.
    mukit_warn "TODO hook: fast x87 requested but no rosetta-timewalker build at '${tw:-<unset: pass --timewalker-dir>}'; launcher uses plain Rosetta (MU_FAST_X87=0)."
    return 1
}
hook_ac_variant() {
    case "$AC_VARIANT" in
        with-ac) return 0 ;;   # unchanged client, nothing to do
        no-ac)
            # TODO(ac-variant): intentionally NOT implemented. This kit does not bypass or
            # disable the client's anti-cheat; a no-AC test build is an owner-side deliverable.
            mukit_die 'TODO hook: --ac-variant no-ac is not implemented by this kit.' ;;
    esac
}

# ======================================================================= main
run_step() {   # run_step LABEL NAME  (check_NAME / apply_NAME)
    say "== $1"
    if "check_$2"; then return 0; fi
    "apply_$2"
}

main() {
    preflight
    hook_ac_variant
    local n=12; [ "$RUNTIME" = free ] && n=14
    if [ "$RUNTIME" = free ]; then
        run_step "1/$n free Wine runtime" runtime
        step_runtime_current
        run_step "2/$n winetricks" winetricks_tool
        run_step "3/$n Wine prefix (32-bit)" prefix
    else
        run_step "1/$n bottle (win10 template, WineArch=win32)" bottle
    fi
    local i=$(( n - 11 ))
    # Registry first: AeDebug must be off before anything that could crash (the .NET installer
    # included); winedbg once killed the game's threads.
    run_step "$((i + 1))/$n registry (AeDebug off, overrides)" registry
    run_step "$((i + 2))/$n .NET Framework 4.8" dotnet48
    run_step "$((i + 3))/$n Windows version" winver
    if [ "$DOTNET_APPLIED" = 1 ] && [ "$DRY_RUN" = 0 ]; then
        say "== $((i + 3))b/$n registry re-check after .NET"
        wineserver_wait   # flush the registry to disk first
        if ! check_registry; then apply_registry; fi
    fi
    run_step "$((i + 4))/$n game files" game
    run_step "$((i + 5))/$n launcher .NET config" launcher_config
    run_step "$((i + 6))/$n launcher skin" skin
    say "== $((i + 7))/$n C:\\mutools";             step_mutools
    say "== $((i + 8))/$n LauncherOption.if";      step_launcher_options
    say "== $((i + 9))/$n proxy DLLs";            step_dlls
    if [ "$RUNTIME" = free ]; then say "== $((i + 10))/$n fast x87 and Desktop launcher"; step_fast_x87_free; step_desktop
    else say "== $((i + 10))/$n Desktop launcher"; step_desktop; fi
    say "== $n/$n verify"
    local vargs=(--bottle "$BOTTLE"); [ "$RUNTIME" = free ] && vargs=(--runtime free --prefix "$PREFIX")
    if [ "$DRY_RUN" = 1 ]; then
        say "  [dry-run] would wait for the prefix's wineserver to exit, then run verify-mu-mac.sh ${vargs[*]}"
        return 0
    fi
    if [ "$WINE_USED" = 1 ]; then
        say "  waiting for the prefix's wineserver to exit (flushes registry to disk)"
        wineserver_wait
    fi
    [ "$SKIP_VERIFY" = 1 ] || "$KIT_DIR/verify-mu-mac.sh" "${vargs[@]}"
}
main
