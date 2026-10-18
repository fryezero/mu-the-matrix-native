#!/bin/bash
# Authored setup only. Supply a legally acquired installation; no game is shipped.
set -euo pipefail
umask 077

die() { printf 'Error: %s\n' "$*" >&2; exit 1; }
note() { printf '%s\n' "$*"; }
usage() {
    cat <<'EOF'
Usage: setup-crossover-32bit.sh [--bottle NAME] [SOURCE_DIRECTORY]
Creates a NEW win10/win32 CrossOver bottle, or resumes one owned by this script.
Default bottle: MuTheMatrix
Default source: Windows10MU/drive_c/Program Files (x86)/Glitch Games Network/Mu The Matrix
Environment: CX_ROOT overrides the CrossOver runtime directory;
             WINETRICKS overrides the winetricks executable;
             MU_GL_BATCHING=0 disables default-on mugl (otherwise needs mingw-w64).
Logs, step markers and Play.command stay inside the new bottle.
EOF
}

SCRIPT_DIR=$(cd -- "$(dirname -- "$0")" && pwd -P)
CX_ROOT=${CX_ROOT:-/Applications/CrossOver.app/Contents/SharedSupport/CrossOver}
BOTTLES="$HOME/Library/Application Support/CrossOver/Bottles"
source "$SCRIPT_DIR/gl-batching.sh"
source "$SCRIPT_DIR/diagnostics/bottle.sh"
BOTTLE=MuTheMatrix
SOURCE=
while [ "$#" -gt 0 ]; do
    case "$1" in
        --bottle) [ "$#" -ge 2 ] || die '--bottle needs a name'; BOTTLE=$2; shift 2 ;;
        -h|--help) usage; exit 0 ;;
        --*) die "Unknown option: $1" ;;
        *) [ -z "$SOURCE" ] || die 'Supply only one source directory'; SOURCE=$1; shift ;;
    esac
done

preflight() {
    [ "$(uname -s)" = Darwin ] || die 'This setup requires macOS and CrossOver.'
    [[ "$BOTTLE" =~ ^[A-Za-z0-9][A-Za-z0-9_-]*$ ]] || die 'Use letters, digits, hyphens or underscores in the bottle name.'
    case "$(printf '%s' "$BOTTLE" | tr '[:upper:]' '[:lower:]')" in
        windows10mu|steam|mumatrixrecovery|mumatrix32) die "Protected existing bottle: $BOTTLE" ;;
    esac
    [ -x "$CX_ROOT/bin/cxbottle" ] && [ -x "$CX_ROOT/bin/wine" ] &&
        [ -x "$CX_ROOT/bin/wineserver" ] || die "CrossOver tools missing at $CX_ROOT"
    WINETRICKS=$(command -v "${WINETRICKS:-winetricks}") || die 'Install winetricks first, for example with Homebrew.'
    [ -x "$SCRIPT_DIR/cxwine" ] && [ -x "$SCRIPT_DIR/cxwineserver" ] &&
        [ -x "$SCRIPT_DIR/start-launcher.sh" ] || die 'Keep the executable helpers beside this script.'
    [ -f "$SCRIPT_DIR/fast-x87.sh" ] || die 'Missing fast-x87 helper.'
    [ -f "$SCRIPT_DIR/diagnostics/MonitorCheck.cs" ] || die 'Missing monitor diagnostic source.'
    SOURCE=${SOURCE:-$BOTTLES/Windows10MU/drive_c/Program Files (x86)/Glitch Games Network/Mu The Matrix}
    [ -d "$SOURCE" ] || die "Source directory not found: $SOURCE"
    SOURCE=$(cd -- "$SOURCE" && pwd -P)
    [ -f "$SOURCE/main.exe" ] && [ -f "$SOURCE/MuTheMatrix.exe" ] || die 'Source must contain main.exe and MuTheMatrix.exe.'
    [ -z "$(find "$SOURCE" -type l -print -quit)" ] || die 'Refusing source symlinks that could link the clone to another installation.'
    case "${MU_GL_BATCHING:-1}" in
        1) make -C "$SCRIPT_DIR/mugl" ;;
        0) ;;
        *) die 'MU_GL_BATCHING must be 0 or 1' ;;
    esac
    mkdir -p "$BOTTLES"
    BOTTLES=$(cd -- "$BOTTLES" && pwd -P)
    PREFIX="$BOTTLES/$BOTTLE"
    [ ! -L "$PREFIX" ] || die 'Refusing a symlink bottle.'
    case "$SOURCE/" in "$PREFIX/"*) die 'Source cannot be inside the destination bottle.' ;; esac
    STATE="$PREFIX/.mu-matrix-setup"
    # Include the bottle in the Windows path to distinguish parallel diagnostics.
    GAME="$PREFIX/drive_c/MuTheMatrix-$BOTTLE"
    # A separate lock prevents concurrent setup; no global wineserver operation.
    LOCK="$BOTTLES/.$BOTTLE.mu-setup-lock"
    mkdir "$LOCK" || die "Setup lock exists: $LOCK. Check for a running setup before removing a stale lock."
    trap 'rmdir "$LOCK"' EXIT
}

create_bottle() {
    if [ -e "$PREFIX" ]; then
        [ -f "$STATE/owner" ] && [ "$(cat "$STATE/owner")" = 'mu-matrix-crossover-32bit-v2' ] ||
            die "Refusing existing bottle without our ownership marker: $PREFIX"
        [ -f "$STATE/source" ] && [ "$(cat "$STATE/source")" = "$SOURCE" ] || die 'Resume requires the same source directory.'
    else
        "$CX_ROOT/bin/cxbottle" --bottle "$BOTTLE" --create --template win10
        mkdir "$STATE"
        printf '%s\n' 'mu-matrix-crossover-32bit-v2' > "$STATE/owner"
        printf '%s\n' "$SOURCE" > "$STATE/source"
    fi
    # Check the actual bottle before letting winetricks touch it.
    grep -Eq '^"?WineArch"?[[:space:]]*=[[:space:]]*"?win32"?[[:space:]]*$' "$PREFIX/cxbottle.conf" ||
        die 'Expected WineArch=win32 in cxbottle.conf.'
    export CX_ROOT CX_BOTTLE="$BOTTLE" WINEPREFIX="$PREFIX"
    # CrossOver's new WoW64 runtime rejects WINEARCH=win32 even for its win32 bottle.
    unset WINEARCH
    export WINE="$SCRIPT_DIR/cxwine" WINESERVER="$SCRIPT_DIR/cxwineserver"
    export WINEDEBUG=-all
}

remove_empty_syswow64() {
    local dir="$PREFIX/drive_c/windows/syswow64"
    [ ! -L "$dir" ] || die 'Refusing symlink syswow64.'
    if [ -d "$dir" ]; then
        # rmdir is the emptiness check too. Never recursively delete this directory.
        rmdir "$dir" || die 'syswow64 is not empty; refusing to change it or run misdetected win64 installers.'
    fi
}

install_dotnet() {
    remove_empty_syswow64
    "$WINETRICKS" -q dotnet48
}

configure_graphics() {
    "$WINE" reg add 'HKCU\Software\Microsoft\Avalon.Graphics' /v DisableHWAcceleration /t REG_DWORD /d 1 /f
}

configure_browser() {
    "$WINE" reg add 'HKCU\Software\Microsoft\Internet Explorer\Main\FeatureControl\FEATURE_BROWSER_EMULATION' /v MuTheMatrix.exe /t REG_DWORD /d 11001 /f
}

disable_custom_skin() {
    local design="$GAME/Data/Launcher/Design" file backup n=1 component
    # The server's official skin needs the mscoree proxy's WIC stream fix under Wine 11
    # (mac-play/mumodes/wicfix.c, docs/research/mac-launcher-skin.md). This legacy script installs no
    # mscoree proxy, so it keeps the skin disabled; mac-play/installer restores it.
    # Updates may restore the custom skin. Recheck every run, without a step marker.
    for component in "$GAME" "$GAME/Data" "$GAME/Data/Launcher" "$design"; do
        [ ! -L "$component" ] || die "Refusing symlink in cloned skin path: $component"
    done
    file="$design/Template.design"
    [ ! -L "$file" ] || die 'Refusing symlink Template.design.'
    if [ -f "$file" ]; then
        backup="$file.disabled"
        # Preserve an earlier disabled skin if an update installed another one.
        while [ -e "$backup" ] || [ -L "$backup" ]; do
            backup="$file.disabled.$n"
            n=$((n + 1))
        done
        mv "$file" "$backup"
        note "Disabled cloned official skin (needs the mscoree proxy v3, which this script does not install): $backup"
    else
        note 'Custom skin absent; using the built-in default IGCN skin.'
    fi
}

clone_installation() {
    local partial="$GAME.partial"
    [ ! -e "$GAME" ] && [ ! -L "$GAME" ] || die 'Unmarked destination game directory exists; inspect it before resuming.'
    [ ! -e "$partial" ] && [ ! -L "$partial" ] || die "Incomplete clone exists at $partial; inspect/remove it before resuming."
    # APFS copy-on-write clone. No fallback writes or patches to the source.
    cp -c -R "$SOURCE" "$partial"
    mv "$partial" "$GAME"
}

check_identity() {
    local expected=3cf91f3c203d305a771b04d00b271871f7ce1c6779b22e30fbae8c4f35b5527a actual
    actual=$(shasum -a 256 "$GAME/main.exe" | awk '{print $1}')
    note "main.exe SHA-256: $actual"
    if [ "$actual" != "$expected" ]; then
        note "WARNING: expected $expected; this installation is outside the validated client identity." >&2
    fi
}

install_display_check() {
    local tools="$PREFIX/drive_c/MuMatrixTools" file
    [ ! -L "$tools" ] || die 'Refusing symlink diagnostic directory.'
    mkdir -p "$tools"
    for file in "$tools/MonitorCheck.cs" "$tools/MonitorCheck.exe"; do
        [ ! -L "$file" ] || die "Refusing symlink diagnostic file: $file"
    done
    cp "$SCRIPT_DIR/diagnostics/MonitorCheck.cs" "$tools/MonitorCheck.cs"
    "$WINE" "$PREFIX/drive_c/windows/Microsoft.NET/Framework/v4.0.30319/csc.exe" \
        /nologo /platform:x86 /target:exe '/out:C:\MuMatrixTools\MonitorCheck.exe' \
        'C:\MuMatrixTools\MonitorCheck.cs'
}

write_launcher() {
    local launcher="$STATE/Play.command"
    cp "$SCRIPT_DIR/start-launcher.sh" "$STATE/start-launcher.sh"
    cp "$SCRIPT_DIR/fast-x87.sh" "$STATE/fast-x87.sh"
    chmod 700 "$STATE/start-launcher.sh"
    # %q preserves spaces and shell metacharacters without evaluating user paths.
    {
        printf '#!/bin/bash\nset -euo pipefail\nunset WINEARCH\n'
        printf 'export CX_ROOT=%q CX_BOTTLE=%q WINEPREFIX=%q\n' "$CX_ROOT" "$BOTTLE" "$PREFIX"
        printf 'export MU_GAME_DIR=%q\n' "$GAME"
        printf 'exec %q\n' "$STATE/start-launcher.sh"
    } > "$launcher"
    chmod 700 "$launcher"
    note "Double-click launcher: $launcher"
}

run_step() {
    local name=$1 action=$2
    if [ -f "$STATE/$name.done" ]; then
        note "Already completed: $name"
        return
    fi
    note "Running: $name (log: $STATE/$name.log)"
    # Run outside an if/&& condition so errexit applies to every command in action.
    "$action" > "$STATE/$name.log" 2>&1
    touch "$STATE/$name.done"
}

main() {
    preflight
    create_bottle
    # Add later compatibility fixes as named functions and versioned steps here.
    run_step dotnet48 install_dotnet
    # Keep Wine builtin windowscodecs and gdiplus. Native WIC breaks encoding.
    run_step software-rendering configure_graphics
    run_step browser-emulation configure_browser
    run_step display-check-v1 install_display_check
    run_step clone-installation clone_installation
    note "Checking cloned custom skin (log: $STATE/default-skin.log)"
    disable_custom_skin >> "$STATE/default-skin.log" 2>&1
    check_identity
    note "Checking mugl deployment (log: $STATE/mugl.log)"
    install_gl_batching >> "$STATE/mugl.log" 2>&1
    write_launcher
    note 'Setup complete. Play.command resets this idle bottle and checks its monitor before starting. See the research report for validation limits.'
}
main
