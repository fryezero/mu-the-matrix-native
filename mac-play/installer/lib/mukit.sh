#!/bin/bash
# mu-mac-kit shared helpers. Sourced by setup-mu-mac.sh, verify-mu-mac.sh and tests.
# Bash 3.2 compatible (stock macOS /bin/bash): no associative arrays, no ${x,,}, no mapfile.
# Everything here is read-only except mukit_run (which honours DRY_RUN).
# Part of the repository's mac-play/installer (MAC-KIT-001). Publication rule: only SHA-256 pins
# of third-party or client-derived files live here, never the files themselves.

MUKIT_VERSION=1
MUKIT_OWNER_MARKER="mu-mac-kit-v$MUKIT_VERSION"
CX_ROOT=${CX_ROOT:-/Applications/CrossOver.app/Contents/SharedSupport/CrossOver}
MUKIT_BOTTLES_DIR=${MUKIT_BOTTLES_DIR:-$HOME/Library/Application Support/CrossOver/Bottles}

# Pinned identities (see README.md, "Expected hashes"). Each pin can be overridden by an environment
# variable of the same name; that exists for the synthetic test suite (which has no real DLLs) and
# defeats the check, so do not set these for a real install.
MUKIT_MAIN_EXE_SHA256=${MUKIT_MAIN_EXE_SHA256:-3cf91f3c203d305a771b04d00b271871f7ce1c6779b22e30fbae8c4f35b5527a}
MUKIT_LAUNCHER_EXE_SHA256=${MUKIT_LAUNCHER_EXE_SHA256:-c32e99ee98fc0773f850f9e76b160a9a00c867f4d745bf9e66c4b15d7f74bc3e}
# Prebuilt mugl DLLs (supplied by the user with --dll-dir, never in this repository): v7.6 is the default
# (MAC-PERF-010: native JPEG decode, faster map loads), v7.5 (MAC-PERF-009: native shadows, decals, mesh append); v7.2 (precise frame pacing waits, MAC-PERF-006),
# v7.1 and v7.0 stay selectable as rollbacks.
MUKIT_MUGL_V76_SHA256=${MUKIT_MUGL_V76_SHA256:-8419f0915cbad211af06b7bb70e41f00b2cf39505ae0b46d708efbdd1baf6dc5}
MUKIT_MUGL_V75_SHA256=${MUKIT_MUGL_V75_SHA256:-95e43657c677170e0ea7335ebb63f303d882367229e7a0b5e0849992e8f343b5}
MUKIT_MUGL_V72_SHA256=${MUKIT_MUGL_V72_SHA256:-e37cf5d52c990cf38c18137ba3faacb339bb0a949816297a40027fd7203d5a60}
MUKIT_MUGL_V71_SHA256=${MUKIT_MUGL_V71_SHA256:-85a8e3b6ea2f7d2602b14fc27e33496cfe136f14f4488e3dc5baffd4f15d3ca2}
MUKIT_MUGL_V70_SHA256=${MUKIT_MUGL_V70_SHA256:-c06534dfe7a101856028153c7ed9f4db1f33cd497a9e012a5ae872a0896db31c}
MUKIT_MUGL_DEFAULT_VERSION=v76
# Hotpatch masks (C:\mutools\mugl-hotpatch.txt). The kit default 112025007 is v7.5's 44916143 plus 67108864 native
# JPEG decode (v7.6, MAC-PERF-010; the kit's own --mugl-build private needs LJT_DIR from
# mac-play/hotpatch/build-libjpeg-turbo.sh for it), deliberately without v7.6's CRC bit 268435456.
# v7.5's built-in default is 44916143: v7.4's 875951 plus
# 2097152 native body shadows, 8388608 native terrain decals and 33554432 the specialised mesh-draw append
# (MAC-PERF-009). v7.4's 875951 is v7.1's 7599
# (1|2|4|8 helpers/inlining/peephole/xform, 32|128|256 meshdraw, 1024 frame pacing fix,
# 2048|4096 zero-copy/strided batches) plus 16384 terrain face sorting (v7.3), 65536 sprite/grass quad
# batching, 262144 deferred client-array enables and 524288 off-screen culling (v7.4). Older builds read
# fewer bits of the same value and see their own default: v7.4 21 bits (875951), v7.3 16 bits (23983), v7.1/v7.2 14 bits (7599),
# v7.0 5 bits (15). 6575 = v7.1's default without the frame pacing fix.
MUKIT_HOTPATCH_DEFAULT=112025007
MUKIT_HOTPATCH_V70_BITS=15
MUKIT_HOTPATCH_MAX=2147483647          # 31 bits; v7.6 reads 30 (v7.5 masks the value with 67108863, 26 bits)
MUKIT_HOTPATCH_OLD_DEFAULTS="15 7599 875951 44916143"  # values earlier kit versions wrote; upgraded without --reset-config
MUKIT_MSCOREE_PROXY_SHA256=${MUKIT_MSCOREE_PROXY_SHA256:-6f2d2acea2a48eb789ab7867a6c0a4e97d6db3263d1ae3b1a729f9cc7a5639ac}
# CrossOver 26.3 i386 builtin opengl32.dll (informational; verify compares to the installed CrossOver).
MUKIT_CX263_OPENGL32_SHA256=0965d21be959f804d0dedaa4a52da952befbc9b73df573229c0074390823ec56
MUKIT_DOTNET48_INSTALLER_SHA256=${MUKIT_DOTNET48_INSTALLER_SHA256:-95889d6de3f2070c07790ad6cf2000d33d9a1bdfc6a381725ab82ab1c314fd53}
MUKIT_DOTNET48_RELEASE_MIN=528040   # NDP\v4\Full Release for .NET 4.8 (0x80eb1 = 528049 observed)

# mukit_dotnet48_state PREFIX -> prints "ok RELEASE VERSION" or "missing REASON"; returns 0 only for a
# real Microsoft .NET 4.8 install. A fresh CrossOver bottle already registers NDP\v4\Full
# Release=533320 Version=4.7.03190 for Wine's builtin mscoree, so the Release value alone lies.
mukit_dotnet48_state() {
    local p=$1 rel ver fw="$1/drive_c/windows/Microsoft.NET/Framework/v4.0.30319"
    rel=$(mukit_reg_value "$p/system.reg" 'Software\Microsoft\NET Framework Setup\NDP\v4\Full' Release 2>/dev/null)
    ver=$(mukit_reg_value "$p/system.reg" 'Software\Microsoft\NET Framework Setup\NDP\v4\Full' Version 2>/dev/null)
    if ! [[ "$rel" =~ ^[0-9]+$ ]] || [ "$rel" -lt "$MUKIT_DOTNET48_RELEASE_MIN" ]; then echo "missing Release ${rel:-unset}"; return 1; fi
    case "$ver" in 4.8.*) ;; *) echo "missing Version ${ver:-unset} (Release $rel is Wine's placeholder)"; return 1 ;; esac
    [ -f "$fw/clr.dll" ] || { echo "missing clr.dll"; return 1; }
    { [ -f "$p/drive_c/windows/system32/mscoree.dll" ] && ! mukit_pe_is_wine_builtin "$p/drive_c/windows/system32/mscoree.dll"; } ||
        { echo "missing native system32\mscoree.dll"; return 1; }
    echo "ok $rel $ver"
}

# Bottles the kit must never modify (case-insensitive).
# (the same names mac-play/setup-crossover-32bit.sh protects). Add your own with MUKIT_EXTRA_PROTECTED_BOTTLES="Name1 Name2".
MUKIT_PROTECTED_BOTTLES="mumatrix32 windows10mu steam mumatrixrecovery $(printf '%s' "${MUKIT_EXTRA_PROTECTED_BOTTLES:-}" | tr '[:upper:]' '[:lower:]')"

# Verified 16:10 ladder (game's own round modes + the two injected ones). 1920x1200 is a
# native game mode but overflowed the 1800x1169 screen; it is offered only when it fits.
MUKIT_MODE_LADDER="960x600 1024x640 1280x800 1600x1000 1728x1080 1920x1200"
MUKIT_MODE_BASE_COUNT=3          # always offered, so small screens still get a list
MUKIT_MODE_W_MARGIN=16           # window frame
MUKIT_MODE_H_MARGIN=89           # menu bar + title bar (1169 - 1080 on the reference Mac)

mukit_die()  { printf 'Error: %s\n' "$*" >&2; exit 1; }
mukit_note() { printf '%s\n' "$*"; }
mukit_warn() { printf 'WARNING: %s\n' "$*" >&2; }

mukit_lower() { printf '%s' "$1" | tr '[:upper:]' '[:lower:]'; }

mukit_is_protected_bottle() {
    local b w
    b=$(mukit_lower "$1")
    for w in $MUKIT_PROTECTED_BOTTLES; do [ "$b" = "$w" ] && return 0; done
    return 1
}

mukit_valid_bottle_name() { [[ "$1" =~ ^[A-Za-z0-9][A-Za-z0-9_-]*$ ]]; }

# mukit_run CMD...: execute, or print when DRY_RUN=1.
mukit_run() {
    if [ "${DRY_RUN:-0}" = 1 ]; then
        printf '[dry-run]'; printf ' %q' "$@"; printf '\n'
        return 0
    fi
    "$@"
}

# mukit_write_file PATH CONTENT: write exact bytes (printf %s), or print in dry-run.
mukit_write_file() {
    if [ "${DRY_RUN:-0}" = 1 ]; then
        printf '[dry-run] write %q (%d bytes): %q\n' "$1" "${#2}" "$2"
        return 0
    fi
    printf '%s' "$2" > "$1"
}

mukit_sha256() {
    if command -v shasum >/dev/null 2>&1; then shasum -a 256 "$1" 2>/dev/null | awk '{print $1}'
    else sha256sum "$1" 2>/dev/null | awk '{print $1}'; fi
}

# Wine's PE builtin marker sits in the DOS stub at offset 64.
mukit_pe_is_wine_builtin() {
    [ -f "$1" ] && [ "$(LC_ALL=C dd if="$1" bs=1 skip=64 count=16 2>/dev/null)" = 'Wine builtin DLL' ]
}

# ---------------------------------------------------------------- cxbottle.conf
# mukit_conf_get CONF KEY -> value of "KEY" = "VALUE" (first match, any section).
mukit_conf_get() {
    [ -f "$1" ] || return 1
    local v
    v=$(sed -nE "s/^[[:space:]]*\"?$2\"?[[:space:]]*=[[:space:]]*\"?([^\"]*)\"?[[:space:]]*\$/\\1/p" "$1" | head -1)
    [ -n "$v" ] || return 1
    printf '%s\n' "$v"
}

# ---------------------------------------------------------------- Wine .reg files
# mukit_reg_get FILE KEY NAME -> raw right-hand side of "NAME"=... under [KEY].
# KEY uses single backslashes and is relative to the file's root (user.reg = HKCU,
# system.reg = HKLM). Key and value names compare case-insensitively. NAME "@" = default.
# Returns 1 when the key or value is absent.
mukit_reg_get() {
    local file=$1 key=$2 name=$3 kesc
    [ -f "$file" ] || return 2
    kesc=$(printf '%s' "$key" | sed 's/\\/\\\\/g')
    MUKIT_K="$kesc" MUKIT_N="$name" LC_ALL=C awk '
    BEGIN { k = tolower(ENVIRON["MUKIT_K"]); n = tolower(ENVIRON["MUKIT_N"]); inkey = 0; found = 0 }
    /^\[/ {
        if (inkey) exit
        if (match($0, /\][^\]]*$/)) { line = substr($0, 2, RSTART - 2) } else { line = substr($0, 2) }
        inkey = (tolower(line) == k)
        next
    }
    inkey {
        if (n == "@") { if (substr($0, 1, 2) == "@=") { print substr($0, 3); found = 1; exit } next }
        if (substr($0, 1, 1) != "\"") next
        i = 2; nm = ""; L = length($0)
        while (i <= L) {
            c = substr($0, i, 1)
            if (c == "\\") { nm = nm substr($0, i + 1, 1); i += 2; continue }
            if (c == "\"") break
            nm = nm c; i++
        }
        if (tolower(nm) == n && substr($0, i + 1, 1) == "=") { print substr($0, i + 2); found = 1; exit }
    }
    END { exit(found ? 0 : 1) }' "$file"
}

# mukit_reg_norm RAW -> decimal for dword:, unescaped text for strings, raw otherwise.
mukit_reg_norm() {
    local raw=$1
    case "$raw" in
        dword:*) printf '%d\n' "0x${raw#dword:}" ;;
        str\(*\):\"*) raw=${raw#str(*):}; printf '%s\n' "$raw" | sed -e 's/^"//' -e 's/"$//' -e 's/\\"/"/g' -e 's/\\\\/\\/g' ;;
        \"*) printf '%s\n' "$raw" | sed -e 's/^"//' -e 's/"$//' -e 's/\\"/"/g' -e 's/\\\\/\\/g' ;;
        *) printf '%s\n' "$raw" ;;
    esac
}

# mukit_reg_value FILE KEY NAME -> normalized value (returns 1 if absent).
mukit_reg_value() {
    local raw
    raw=$(mukit_reg_get "$1" "$2" "$3") || return 1
    mukit_reg_norm "$raw"
}

# Load-order strings compare without spaces ("native, builtin" == "native,builtin").
mukit_loadorder_eq() { [ "$(printf '%s' "$1" | tr -d ' ' | tr '[:upper:]' '[:lower:]')" = "$(printf '%s' "$2" | tr -d ' ' | tr '[:upper:]' '[:lower:]')" ]; }

# mukit_dll_override USERREG DLL -> effective global override (checks "*dll" then "dll").
mukit_dll_override() {
    mukit_reg_value "$1" 'Software\Wine\DllOverrides' "*$2" 2>/dev/null ||
        mukit_reg_value "$1" 'Software\Wine\DllOverrides' "$2" 2>/dev/null
}

# mukit_registry_expectations [WITH_STATS=1] -> "file|key|name|value|compare" lines.
# file: user (HKCU, user.reg) or system (HKLM, system.reg); compare: eq | order (load order).
# Must stay in sync with registry/mu-mac.reg (tests/test-mukit.sh checks this).
mukit_registry_expectations() {
    cat <<'EOF'
user|Software\Microsoft\Avalon.Graphics|DisableHWAcceleration|1|eq
user|Software\Microsoft\Internet Explorer\Main\FeatureControl\FEATURE_BROWSER_EMULATION|MuTheMatrix.exe|11001|eq
user|Software\Wine\DllOverrides|*windowscodecs|builtin|order
user|Software\Wine\DllOverrides|*windowscodecsext|builtin|order
user|Software\Wine\DllOverrides|*gdiplus|builtin|order
user|Software\Wine\AppDefaults\main.exe\DllOverrides|opengl32|native,builtin|order
user|Software\Wine\AppDefaults\MuTheMatrix.exe\DllOverrides|mscoree|native|order
system|Software\Microsoft\Windows NT\CurrentVersion\AeDebug|Auto|0|eq
system|Software\Microsoft\Windows NT\CurrentVersion\AeDebug|Debugger||eq
EOF
    [ "${1:-1}" = 0 ] || printf '%s\n' 'user|Environment|MUGL_STATS|C:\mutools\mugl-stats.txt|eq'
}

# ---------------------------------------------------------------- LauncherOption.if
# The shipped file has a UTF-8 BOM and a CR-only separator; the launcher rewrites it as
# "DevModeIndex:N\r\nWindowMode:N\r\nID:account" without BOM or trailing newline.
mukit_lopt_normalize() { LC_ALL=C sed $'1s/^\xef\xbb\xbf//' "$1" 2>/dev/null | tr '\r' '\n'; }

# mukit_lopt_get FILE KEY -> value ("" if key present but empty; returns 1 if absent).
mukit_lopt_get() {
    [ -f "$1" ] || return 1
    local line
    line=$(mukit_lopt_normalize "$1" | grep -m1 "^$2:") || return 1
    printf '%s\n' "${line#*:}"
}

# mukit_lopt_render DEVMODEINDEX WINDOWMODE ID -> canonical bytes (launcher's own format).
mukit_lopt_render() { printf 'DevModeIndex:%s\r\nWindowMode:%s\r\nID:%s' "$1" "$2" "$3"; }

# ---------------------------------------------------------------- display modes
mukit_mode_valid() { [[ "$1" =~ ^[1-9][0-9]{2,4}x[1-9][0-9]{2,4}$ ]]; }

# mukit_modes_valid "LIST": every token WxH, 1..16 tokens (modehook.c keeps at most 16).
mukit_modes_valid() {
    local m n=0
    for m in $1; do mukit_mode_valid "$m" || return 1; n=$((n + 1)); done
    [ "$n" -ge 1 ] && [ "$n" -le 16 ]
}

mukit_modes_count() { local m n=0; for m in $1; do n=$((n + 1)); done; printf '%d\n' "$n"; }

# mukit_mode_at "LIST" INDEX -> WxH at zero-based INDEX (returns 1 if out of range).
mukit_mode_at() {
    local m i=0
    for m in $1; do [ "$i" = "$2" ] && { printf '%s\n' "$m"; return 0; }; i=$((i + 1)); done
    return 1
}

# mukit_mode_fits WxH SCREEN_W SCREEN_H
mukit_mode_fits() {
    local w=${1%x*} h=${1#*x}
    [ $((w + MUKIT_MODE_W_MARGIN)) -le "$2" ] && [ $((h + MUKIT_MODE_H_MARGIN)) -le "$3" ]
}

# mukit_pick_modes SCREEN_W SCREEN_H -> "LIST|INDEX": base modes always, larger ladder
# modes only when the window fits; INDEX = largest fitting mode (0 if none fits).
mukit_pick_modes() {
    local sw=$1 sh=$2 m i=0 list= idx=0 n=0
    for m in $MUKIT_MODE_LADDER; do
        if [ "$i" -lt "$MUKIT_MODE_BASE_COUNT" ] || mukit_mode_fits "$m" "$sw" "$sh"; then
            list="${list:+$list }$m"
            mukit_mode_fits "$m" "$sw" "$sh" && idx=$n
            n=$((n + 1))
        fi
        i=$((i + 1))
    done
    printf '%s|%s\n' "$list" "$idx"
}

# Logical main-screen size as Wine sees it (CrossOver default, non-Retina mode).
mukit_screen_size() {
    osascript -l JavaScript -e 'ObjC.import("AppKit"); var f = $.NSScreen.mainScreen.frame; Math.round(f.size.width) + "x" + Math.round(f.size.height)' 2>/dev/null
}

# ---------------------------------------------------------------- mutools config values
mukit_mugl_mode_valid() { [[ "$1" =~ ^(full|nomerge|nofilter|off|nodraw)(\+vbo)?(\+time)?(\+finish)?(\+samples)?(\+cull)?$ ]]; }
# Bits 268435456 and 536870912 belonged to an experimental native CRC-32 for the client's file-integrity module.
# That module is out of scope (this project does not modify it) and current mugl source has no such patch; the kit
# refuses masks with either bit, so no build that still carries the code can be told to apply it.
MUKIT_HOTPATCH_FORBIDDEN=805306368     # 268435456 | 536870912
MUKIT_HOTPATCH_FORBIDDEN_WHY='bits 268435456/536870912 (a CRC-32 patch of the client'"'"'s file-integrity module) are out of scope: this project does not modify that module'
mukit_hotpatch_forbidden() { [[ "$1" =~ ^[0-9]{1,10}$ ]] && [ $(( 10#$1 & MUKIT_HOTPATCH_FORBIDDEN )) != 0 ]; }
mukit_hotpatch_valid()  { [[ "$1" =~ ^[0-9]{1,10}$ ]] && [ "$1" -le "$MUKIT_HOTPATCH_MAX" ] && ! mukit_hotpatch_forbidden "$1"; }

# mukit_mugl_version_sha VERSION -> pinned SHA-256 of mugl/builds/mugl-VERSION.dll (v76 | v75 | v72 | v71 | v70).
mukit_mugl_version_sha() {
    case "$1" in
        v76) printf '%s\n' "$MUKIT_MUGL_V76_SHA256" ;;
        v75) printf '%s\n' "$MUKIT_MUGL_V75_SHA256" ;;
        v72) printf '%s\n' "$MUKIT_MUGL_V72_SHA256" ;;
        v71) printf '%s\n' "$MUKIT_MUGL_V71_SHA256" ;;
        v70) printf '%s\n' "$MUKIT_MUGL_V70_SHA256" ;;
        *) return 1 ;;
    esac
}

# mukit_mugl_identify SHA -> "v7.6" / "v7.5" / "v7.2" / "v7.1" / "v7.0" for the pinned builds (returns 1 otherwise).
mukit_mugl_identify() {
    case "$1" in
        "$MUKIT_MUGL_V76_SHA256") echo v7.6 ;;
        "$MUKIT_MUGL_V75_SHA256") echo v7.5 ;;
        "$MUKIT_MUGL_V72_SHA256") echo v7.2 ;;
        "$MUKIT_MUGL_V71_SHA256") echo v7.1 ;;
        "$MUKIT_MUGL_V70_SHA256") echo v7.0 ;;
        *) return 1 ;;
    esac
}

# ---------------------------------------------------------------- free runtime (MAC-FREE-001)
# The default runtime needs no CrossOver: CodeWeavers' open-source Wine (LGPL-2.1+), which can run a
# 32-bit prefix in wow64 mode (upstream WineHQ builds cannot; see docs/research/mac-free-runtime.md).
# Everything lives under one folder: runtime/, tools/winetricks, prefix/ (the Wine prefix), downloads/.
MUKIT_FREE_HOME=${MUKIT_FREE_HOME:-$HOME/Library/Application Support/MuTheMatrix}
MUKIT_FREE_OWNER_MARKER="mu-free-kit-v1"
# Runtime "cx24": Sikarugir's build of CrossOver 24.0.7's Wine (engine) + the dylibs of Sikarugir's
# wrapper template (freetype, gnutls, ...). Both are public GitHub release assets; URLs and SHA-256 pinned.
MUKIT_RT_CX24_ENGINE_URL=${MUKIT_RT_CX24_ENGINE_URL:-https://github.com/Sikarugir-App/Engines/releases/download/v1.0/WS12WineCX24.0.7_7.tar.xz}
MUKIT_RT_CX24_ENGINE_SHA256=${MUKIT_RT_CX24_ENGINE_SHA256:-203f9e9fd6c2cc77e6525d798a434ced326145db34a356355e05659d3445fd1c}
MUKIT_RT_TEMPLATE_URL=${MUKIT_RT_TEMPLATE_URL:-https://github.com/Sikarugir-App/Template/releases/download/v1.0/Template-1.0.24.tar.xz}
MUKIT_RT_TEMPLATE_SHA256=${MUKIT_RT_TEMPLATE_SHA256:-4b5f89eeb9ef139936bdfad33d9b420b05ea4597cb7d63376674f7a8e171321c}
# Preferred runtime: the CrossOver 26.3 Wine built by packaging/build-wine.sh (same speed as CrossOver; the cx24
# engine is about 20% slower in crowded scenes). It has no public download yet: when the server owner hosts the
# archive, put its https URL and SHA-256 here (or pass --runtime-archive/--runtime-sha256) and it becomes the
# default. Empty = use cx24.
MUKIT_RT_ARCHIVE_URL=${MUKIT_RT_ARCHIVE_URL:-}
MUKIT_RT_ARCHIVE_SHA256=${MUKIT_RT_ARCHIVE_SHA256:-}
# winetricks 20260125 (the version the kit was validated with), fetched from its release tag.
MUKIT_WINETRICKS_URL=${MUKIT_WINETRICKS_URL:-https://raw.githubusercontent.com/Winetricks/winetricks/20260125/src/winetricks}
MUKIT_WINETRICKS_SHA256=${MUKIT_WINETRICKS_SHA256:-431f82fc74000e6c864409f1d8fb495d696c03928808e3e8acffc45179312a7b}
# The official game installer, as linked from the server's download page (webx.muthematrix.com/downloads).
MUKIT_GAME_INSTALLER_URL=${MUKIT_GAME_INSTALLER_URL:-https://dl.muthematrix.com/MuTheMatrix-21.1.2.12.exe}

mukit_runtime_valid() { case "$1" in free|crossover) return 0 ;; *) return 1 ;; esac; }

# A runtime directory holds wine/bin/wine and wine/bin/wineserver (+ the dylibs they load).
mukit_rt_wine()       { printf '%s\n' "$1/wine/bin/wine"; }
mukit_rt_wineserver() { printf '%s\n' "$1/wine/bin/wineserver"; }
mukit_rt_ok() { [ -x "$1/wine/bin/wine" ] && [ -x "$1/wine/bin/wineserver" ] && [ -f "$1/wine/lib/wine/x86_64-unix/ntdll.so" ] && [ -f "$1/.mu-runtime" ]; }

# mukit_prefix_arch PREFIX -> win32 / win64 from the registry header Wine writes ("#arch=win32").
mukit_prefix_arch() {
    [ -f "$1/system.reg" ] || return 1
    local a; a=$(sed -n 's/^#arch=//p' "$1/system.reg" | head -1 | tr -d '\r')
    [ -n "$a" ] || return 1
    printf '%s\n' "$a"
}

# Rosetta 2 runs the x86_64 Wine; arch(1) fails when it is not installed.
mukit_rosetta_ok() { [ "$(uname -m)" != arm64 ] || /usr/bin/arch -x86_64 /usr/bin/true 2>/dev/null; }

# mukit_free_kb PATH -> free kilobytes on PATH's volume.
mukit_free_kb() { df -Pk "$1" 2>/dev/null | awk 'NR == 2 {print $4}'; }

# mukit_file_size FILE -> size in bytes (GNU stat first; BSD stat has no -c).
mukit_file_size() { stat -c %s "$1" 2>/dev/null || stat -f %z "$1" 2>/dev/null; }

# mukit_download URL OUT [CURL_ARGS...]: curl to OUT. Progress: curl's bar by default; with MUKIT_PROGRESS=lines
# (Mu The Matrix.app sets it) curl is quiet and one "MU-PROGRESS BYTES TOTAL NAME" line is printed every second,
# BYTES = size of OUT so far (a resumed download counts what it already had), TOTAL = Content-Length or 0 if unknown.
mukit_download() {
    local url=$1 out=$2 total pid rc
    shift 2
    if [ "${MUKIT_PROGRESS:-bar}" != lines ]; then
        curl -fL --retry 3 --retry-delay 5 "$@" --progress-bar -o "$out" "$url"
        return
    fi
    total=$(curl -fsSIL --max-time 20 "$url" 2>/dev/null | tr -d '\r' |
        awk 'tolower($1) == "content-length:" && $2 ~ /^[0-9]+$/ { n = $2 } END { print n + 0 }')
    curl -fL --retry 3 --retry-delay 5 "$@" -sS -o "$out" "$url" &
    pid=$!
    # Polled in the shell (not "wait" alone) so a cancel's SIGTERM is handled within a second.
    while kill -0 "$pid" 2>/dev/null; do
        printf 'MU-PROGRESS %s %s %s\n' "$(mukit_file_size "$out" || echo 0)" "${total:-0}" "$(basename "${out%.part}")"
        { sleep 1; } 2>/dev/null   # braces: bash's own "Terminated" notice on a cancel goes nowhere
    done
    wait "$pid"; rc=$?
    printf 'MU-PROGRESS %s %s %s\n' "$(mukit_file_size "$out" || echo 0)" "${total:-0}" "$(basename "${out%.part}")"
    return "$rc"
}

# mukit_fetch URL SHA256 DEST: download to DEST (resumable, verified, atomic). An existing DEST with the
# right hash is reused. SHA256 "-" skips the check (only for the game installer, which the server updates).
# A cancelled download leaves DEST.part behind; the next run continues it (curl -C -).
mukit_fetch() {
    local url=$1 sha=$2 dest=$3 got
    if [ -f "$dest" ] && { [ "$sha" = - ] || [ "$(mukit_sha256 "$dest")" = "$sha" ]; }; then return 0; fi
    if [ "${DRY_RUN:-0}" = 1 ]; then printf '[dry-run] download %s -> %s\n' "$url" "$dest"; return 0; fi
    mkdir -p "$(dirname "$dest")" || return 1
    mukit_download "$url" "$dest.part" -C - || {
        # A stale partial file from another version can make the resume fail; restart once.
        rm -f "$dest.part"; mukit_download "$url" "$dest.part" || return 1; }
    if [ "$sha" != - ]; then
        got=$(mukit_sha256 "$dest.part")
        [ "$got" = "$sha" ] || { rm -f "$dest.part"; mukit_warn "download of $url has SHA-256 $got, expected $sha"; return 1; }
    fi
    mv -f "$dest.part" "$dest"
}

# ---------------------------------------------------------------- setup lock (one setup per prefix)
# The lock is a directory with an "owner" file: pid=, pgid=, prefix=, wineserver= (KEY=VALUE lines). A lock whose
# setup is gone (killed, Mac restarted) is stale and may be taken over; mukit_lock_get LOCK KEY reads a value.
mukit_lock_get() { sed -n "s/^$2=//p" "$1/owner" 2>/dev/null | head -1; }

# mukit_lock_alive LOCK -> 0 while the setup that holds LOCK still runs. A lock without an owner file (an older kit,
# or one being created right now) counts as alive: it is never removed automatically.
mukit_lock_alive() {
    local pid
    [ -f "$1/owner" ] || return 0
    pid=$(mukit_lock_get "$1" pid)
    [[ "$pid" =~ ^[0-9]+$ ]] || return 1
    kill -0 "$pid" 2>/dev/null || return 1
    # The pid may have been reused by an unrelated process after a restart.
    ps -o command= -p "$pid" 2>/dev/null | grep -q 'setup-mu-mac' || return 1
    return 0
}

# mukit_kill_group_leftovers PGID PATH...: SIGKILL what is left of a stopped setup's process group (curl, tar,
# winetricks), but only processes whose command line names one of PATH (the runtime folder or the prefix). Never
# touches the caller's own group. Prints the number of processes signalled.
mukit_kill_group_leftovers() {
    local pgid=$1 own n=0 p
    shift
    [[ "$pgid" =~ ^[0-9]+$ ]] && [ "$pgid" -gt 1 ] || { echo 0; return 0; }
    own=$(ps -o pgid= -p $$ 2>/dev/null | tr -d ' ')
    [ "$pgid" != "$own" ] || { echo 0; return 0; }
    for p in $(ps -A -o pid=,pgid=,command= 2>/dev/null |
               MUKIT_PG="$pgid" MUKIT_SELF="$$" MUKIT_PATHS="$(printf '%s\n' "$@")" awk '
        BEGIN { n = split(ENVIRON["MUKIT_PATHS"], paths, "\n") }
        $2 == ENVIRON["MUKIT_PG"] && $1 != ENVIRON["MUKIT_SELF"] && $0 !~ /--stop/ {
            for (i = 1; i <= n; i++) if (paths[i] != "" && index($0, paths[i])) { print $1; break }
        }'); do
        kill -KILL "$p" 2>/dev/null && n=$((n + 1))
    done
    echo "$n"
}

# ---------------------------------------------------------------- desktop launchers
# mukit_launcher_bottle COMMANDFILE -> bottle the launcher starts, or returns 1.
# Explicit MU_BOTTLE=NAME wins; otherwise the default inside the referenced play-mu.sh.
mukit_launcher_bottle() {
    local f=$1 b play
    [ -f "$f" ] || return 1
    b=$(sed -nE "s/.*MU_BOTTLE=['\"]?([A-Za-z0-9_-]+).*/\\1/p" "$f" | head -1)
    if [ -n "$b" ]; then printf '%s\n' "$b"; return 0; fi
    play=$(grep -oE '[^"'"'"' ]*play-mu(-fast)?\.sh' "$f" | head -1)
    [ -n "$play" ] || return 1
    play=${play/\$HOME/$HOME}
    [ -f "$play" ] || return 1
    b=$(sed -nE 's/^BOTTLE=\$\{MU_BOTTLE:-([A-Za-z0-9_-]+)\}.*/\1/p' "$play" | head -1)
    [ -n "$b" ] || return 1
    printf '%s\n' "$b"
}
