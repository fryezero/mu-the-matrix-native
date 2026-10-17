#!/bin/bash
# Static tests for mu-mac-kit. Never touches real bottles or a real CrossOver: integration tests run
# against a synthetic bottle under a temp MUKIT_BOTTLES_DIR and a stub CX_ROOT, and never invoke wine
# (all Wine-backed steps are pre-satisfied in the fake registry). All DLLs are synthetic stand-ins whose
# SHA-256 pins are injected through the MUKIT_*_SHA256 test overrides; no game or client-derived file
# is needed. Runs on macOS (bash 3.2) and Linux. Usage: tests/test-mukit.sh
set -u
T_DIR=$(cd -- "$(dirname -- "$0")" && pwd -P)
KIT_DIR=$(cd -- "$T_DIR/.." && pwd -P)
FIX="$T_DIR/fixtures"
# shellcheck source=../lib/mukit.sh
source "$KIT_DIR/lib/mukit.sh"
TMPD=$(mktemp -d "${TMPDIR:-/tmp}/mukit-test.XXXXXX")
[ -n "${MUKIT_TEST_KEEP:-}" ] && echo "keeping $TMPD" || trap 'rm -rf "$TMPD"' EXIT
# Synthetic stand-ins (never real client or Wine files). A "Wine builtin" has the marker at offset 64.
mkbuiltin() { { printf 'MZ'; dd if=/dev/zero bs=1 count=62 2>/dev/null; printf 'Wine builtin DLL'; printf '%s' "$2"; } > "$1"; }
mkdll() { printf 'MZ synthetic %s' "$2" > "$1"; }
sedi() { sed -e "$1" "$2" > "$2.tmp" && mv "$2.tmp" "$2"; }   # portable sed -i
DLLS="$TMPD/dlls"; mkdir -p "$DLLS"
mkdll "$DLLS/mugl-v72.dll" v72; mkdll "$DLLS/mugl-v71.dll" v71; mkdll "$DLLS/mugl-v70.dll" v70; mkdll "$DLLS/mscoree.dll" mscoree
mkdll "$DLLS/ndp48.exe" dotnet
FAKECX="$TMPD/CrossOver"; mkdir -p "$FAKECX/bin" "$FAKECX/lib/wine/i386-windows"
for b in cxbottle wine wineserver; do printf '#!/bin/sh\necho "stub %s: should not run in tests" >&2\nexit 99\n' "$b" > "$FAKECX/bin/$b"; chmod 755 "$FAKECX/bin/$b"; done
mkbuiltin "$FAKECX/lib/wine/i386-windows/opengl32.dll" stand-in
CX_ROOT=$FAKECX; MUKIT_SKIP_PLATFORM_CHECK=1
MUKIT_MUGL_V72_SHA256=$(mukit_sha256 "$DLLS/mugl-v72.dll"); MUKIT_MUGL_V71_SHA256=$(mukit_sha256 "$DLLS/mugl-v71.dll")
MUKIT_MUGL_V70_SHA256=$(mukit_sha256 "$DLLS/mugl-v70.dll"); MUKIT_MSCOREE_PROXY_SHA256=$(mukit_sha256 "$DLLS/mscoree.dll")
MUKIT_DOTNET48_INSTALLER_SHA256=$(mukit_sha256 "$DLLS/ndp48.exe")
export CX_ROOT MUKIT_SKIP_PLATFORM_CHECK MUKIT_MUGL_V72_SHA256 MUKIT_MUGL_V71_SHA256 MUKIT_MUGL_V70_SHA256 MUKIT_MSCOREE_PROXY_SHA256 MUKIT_DOTNET48_INSTALLER_SHA256
NPASS=0 NFAIL=0
ok()   { NPASS=$((NPASS + 1)); printf 'ok    %s\n' "$1"; }
bad()  { NFAIL=$((NFAIL + 1)); printf 'FAIL  %s\n' "$1"; }
eq()   { if [ "$2" = "$3" ]; then ok "$1"; else bad "$1: got [$2] want [$3]"; fi; }
yes()  { if "${@:2}"; then ok "$1"; else bad "$1"; fi; }
no()   { if "${@:2}"; then bad "$1"; else ok "$1"; fi; }

echo '# Wine .reg parsing'
R="$FIX/user.reg"
eq 'dword normalized'         "$(mukit_reg_value "$R" 'Software\Microsoft\Avalon.Graphics' DisableHWAcceleration)" 1
eq 'case-insensitive key'     "$(mukit_reg_value "$R" 'SOFTWARE\microsoft\AVALON.GRAPHICS' disablehwacceleration)" 1
eq 'string unescaped'         "$(mukit_reg_value "$R" Environment MUGL_STATS)" 'C:\mutools\mugl-stats.txt'
eq 'str(2) expand string'     "$(mukit_reg_value "$R" Environment TEMP)" 'C:\users\crossover\Temp'
eq 'appdefaults load order'   "$(mukit_reg_value "$R" 'Software\Wine\AppDefaults\main.exe\DllOverrides' opengl32)" 'native,builtin'
eq 'star override'            "$(mukit_dll_override "$R" windowscodecs)" builtin
eq 'plain override fallback'  "$(mukit_dll_override "$R" d3dx9_43)" native
eq 'empty string value'       "$(mukit_reg_get "$R" 'Software\Test' Empty)" '""'
eq 'escaped quote in name'    "$(mukit_reg_value "$R" 'Software\Test' 'we"ird')" 1
eq 'default value @'          "$(mukit_reg_value "$R" 'Software\Test' @)" 'dflt'
eq 'dword hex > 9'            "$(mukit_reg_value "$R" 'Software\Test' Hex)" 11001
no 'value in sibling key not leaked' mukit_reg_get "$R" 'Software\Wine\AppDefaults\main.exe' opengl32
no 'missing value'            mukit_reg_get "$R" 'Software\Microsoft\Avalon.Graphics' Nope
no 'missing key'              mukit_reg_get "$R" 'Software\Nope' X
no 'prefix key does not match' mukit_reg_get "$R" 'Software\Wine\AppDefaults\main' opengl32
yes 'load order spacing'      mukit_loadorder_eq 'native, builtin' 'Native,Builtin'
no 'load order differs'       mukit_loadorder_eq 'builtin,native' 'native,builtin'

echo '# cxbottle.conf'
eq 'WineArch'  "$(mukit_conf_get "$FIX/cxbottle.conf" WineArch)" win32
eq 'Template'  "$(mukit_conf_get "$FIX/cxbottle.conf" Template)" win10
no 'commented key ignored' mukit_conf_get "$FIX/cxbottle.conf" WindowsVersion

echo '# LauncherOption.if (shipped BOM/CR-only format and launcher-rewritten format)'
eq 'orig DevModeIndex'  "$(mukit_lopt_get "$FIX/LauncherOption.orig.if" DevModeIndex)" 3
eq 'orig RDP index'     "$(mukit_lopt_get "$FIX/LauncherOption.orig.if" DevModeRDPIndex)" 0
eq 'orig WindowMode'    "$(mukit_lopt_get "$FIX/LauncherOption.orig.if" WindowMode)" 1
eq 'orig empty ID'      "$(mukit_lopt_get "$FIX/LauncherOption.orig.if" ID)" ''
eq 'live DevModeIndex'  "$(mukit_lopt_get "$FIX/LauncherOption.live.if" DevModeIndex)" 4
eq 'live ID'            "$(mukit_lopt_get "$FIX/LauncherOption.live.if" ID)" Player
eq 'render == launcher bytes' "$(mukit_lopt_render 4 1 Player | od -An -tx1 | tr -d ' \n')" "$(od -An -tx1 < "$FIX/LauncherOption.live.if" | tr -d ' \n')"

echo '# display modes'
eq 'reference Mac 1800x1169'  "$(mukit_pick_modes 1800 1169)" '960x600 1024x640 1280x800 1600x1000 1728x1080|4'
eq 'MacBook Air 1470x956'     "$(mukit_pick_modes 1470 956)" '960x600 1024x640 1280x800|2'
eq '1440x900 (800+89 fits)'   "$(mukit_pick_modes 1440 900)" '960x600 1024x640 1280x800|2'
eq '1512x982 MBP14'           "$(mukit_pick_modes 1512 982)" '960x600 1024x640 1280x800|2'
eq '1728x1117 MBP16'          "$(mukit_pick_modes 1728 1117)" '960x600 1024x640 1280x800 1600x1000|3'
eq '2560x1440 external'       "$(mukit_pick_modes 2560 1440)" '960x600 1024x640 1280x800 1600x1000 1728x1080 1920x1200|5'
eq 'tiny screen keeps base'   "$(mukit_pick_modes 1000 650)" '960x600 1024x640 1280x800|0'
eq 'mode_at 4'                "$(mukit_mode_at '960x600 1024x640 1280x800 1600x1000 1728x1080' 4)" 1728x1080
no 'mode_at out of range'     mukit_mode_at '960x600 1024x640' 2
yes 'modes valid'             mukit_modes_valid '960x600 1024x640 1280x800 1600x1000 1728x1080'
no 'modes junk'               mukit_modes_valid '960x600 big'
no 'modes empty'              mukit_modes_valid ''
eq 'modes count'              "$(mukit_modes_count '960x600 1024x640 1280x800')" 3

echo '# mutools values'
for m in full full+vbo nomerge off nofilter full+vbo+time; do yes "mugl mode $m" mukit_mugl_mode_valid "$m"; done
for m in fast vbo full+time+vbo ''; do no "mugl mode '$m' rejected" mukit_mugl_mode_valid "$m"; done
yes 'hotpatch 15' mukit_hotpatch_valid 15
yes 'hotpatch 47' mukit_hotpatch_valid 47
yes 'hotpatch 7599 (v7.1 default)' mukit_hotpatch_valid 7599
yes 'hotpatch 16383' mukit_hotpatch_valid 16383
no 'hotpatch x'   mukit_hotpatch_valid x
no 'hotpatch 16384' mukit_hotpatch_valid 16384
eq 'v7.1 default keeps v7.0 bits' "$((MUKIT_HOTPATCH_DEFAULT & 31))" "$MUKIT_HOTPATCH_V70_BITS"

echo '# pinned hashes (real pins are tested in a subshell without the test overrides)'
PINS=$(env -u MUKIT_MUGL_V72_SHA256 -u MUKIT_MUGL_V71_SHA256 -u MUKIT_MUGL_V70_SHA256 -u MUKIT_MSCOREE_PROXY_SHA256 -u MUKIT_DOTNET48_INSTALLER_SHA256 \
    bash -c 'source "$1"; printf "%s %s %s %s %s %s %s" "$MUKIT_MUGL_V72_SHA256" "$MUKIT_MUGL_V71_SHA256" "$MUKIT_MUGL_V70_SHA256" "$MUKIT_MSCOREE_PROXY_SHA256" "$MUKIT_DOTNET48_INSTALLER_SHA256" "$MUKIT_MAIN_EXE_SHA256" "$MUKIT_LAUNCHER_EXE_SHA256"' _ "$KIT_DIR/lib/mukit.sh")
n=0; for h in $PINS; do n=$((n + 1)); [[ "$h" =~ ^[0-9a-f]{64}$ ]] && ok "pin $n is a SHA-256" || bad "pin $n is a SHA-256: $h"; done
eq 'pin count' "$n" 7
eq 'real pins are not the synthetic test hashes' "$(printf '%s\n' $PINS | sort -u | wc -l | tr -d ' ')" 7
eq 'identify v7.1'     "$(mukit_mugl_identify "$MUKIT_MUGL_V71_SHA256")" v7.1
eq 'identify v7.2'     "$(mukit_mugl_identify "$MUKIT_MUGL_V72_SHA256")" v7.2
no 'identify unknown'  mukit_mugl_identify 0000
eq 'version sha v70'   "$(mukit_mugl_version_sha v70)" "$MUKIT_MUGL_V70_SHA256"
no 'version sha v69 unknown' mukit_mugl_version_sha v69

echo '# bottle names'
for b in MuMatrix32 mumatrix32 Windows10MU STEAM MuMatrixRecovery; do yes "protected $b" mukit_is_protected_bottle "$b"; done
no 'MuMatrixKit not protected' mukit_is_protected_bottle MuMatrixKit
no 'bad name with space' mukit_valid_bottle_name 'Mu Kit'
no 'bad name with slash' mukit_valid_bottle_name '../x'

echo '# PE builtin marker'
yes 'builtin marker at offset 64' mukit_pe_is_wine_builtin "$CX_ROOT/lib/wine/i386-windows/opengl32.dll"
no 'proxy DLL is not builtin'    mukit_pe_is_wine_builtin "$DLLS/mugl-v71.dll"
no 'missing file is not builtin' mukit_pe_is_wine_builtin "$DLLS/nope.dll"

echo '# registry/mu-mac.reg <-> expectations'
# Parse REGEDIT4 into "root|key|name|normalized" and check every expectation is set by the file.
REGROWS=$(awk '
    /^\[/ { k = substr($0, 2, length($0) - 2); root = (k ~ /^HKEY_LOCAL_MACHINE\\/) ? "system" : "user"; sub(/^HKEY_[A-Z_]+\\/, "", k); next }
    /^"/ { i = index($0, "\"="); name = substr($0, 2, i - 2); val = substr($0, i + 2)
           if (val ~ /^dword:/) { h = tolower(substr(val, 7)); v = 0; for (j = 1; j <= length(h); j++) v = v * 16 + index("0123456789abcdef", substr(h, j, 1)) - 1; val = sprintf("%d", v) }
           else { gsub(/^"|"$/, "", val); gsub(/\\\\/, "\\", val) }
           print root "|" k "|" name "|" val }' "$KIT_DIR/registry/mu-mac.reg")
while IFS='|' read -r f k n v c; do
    row=$(printf '%s\n' "$REGROWS" | awk -F'|' -v f="$f" -v n="$n" -v K="$(printf '%s' "$k" | tr '\\' '/')" '{ kk = $2; gsub(/\\/, "/", kk) } $1 == f && kk == K && $3 == n { print $4 }')
    if [ "$c" = order ]; then yes "reg file sets $n" mukit_loadorder_eq "$row" "$v"
    else eq "reg file sets ${k##*\\}:$n" "$row" "$v"; fi
done < <(mukit_registry_expectations 1)

echo '# desktop launcher parsing'
printf '#!/bin/zsh\nexport MU_BOTTLE='"'"'KitX'"'"' MU_FAST_X87=0\nnohup /x/play-mu.sh &\n' > "$TMPD/a.command"
printf 'BOTTLE=${MU_BOTTLE:-DefaultB}\n' > "$TMPD/play-mu.sh"
printf '#!/bin/zsh\nnohup "%s/play-mu.sh" >/dev/null 2>&1 &\n' "$TMPD" > "$TMPD/b.command"
eq 'explicit MU_BOTTLE'      "$(mukit_launcher_bottle "$TMPD/a.command")" KitX
eq 'play-mu.sh default'      "$(mukit_launcher_bottle "$TMPD/b.command")" DefaultB

echo '# shell syntax'
for f in "$KIT_DIR/setup-mu-mac.sh" "$KIT_DIR/verify-mu-mac.sh" "$KIT_DIR/lib/mukit.sh" "$0"; do
    yes "bash -n $(basename "$f")" bash -n "$f"
    if command -v zsh >/dev/null 2>&1; then yes "zsh -n $(basename "$f")" zsh -n "$f"; else echo "skip  zsh -n $(basename "$f") (no zsh)"; fi
done
command -v zsh >/dev/null 2>&1 && yes 'zsh -n play-mu.sh' zsh -n "$KIT_DIR/play-mu.sh" || echo 'skip  zsh -n play-mu.sh (no zsh)'

echo '# integration: synthetic bottle (no wine)'
export MUKIT_BOTTLES_DIR="$TMPD/Bottles"
FB="$MUKIT_BOTTLES_DIR/FakeKit"
mkdir -p "$FB/.mukit" "$FB/drive_c/windows/system32" "$FB/drive_c/windows/Microsoft.NET/Framework/v4.0.30319/WPF"
printf '%s\n' "$MUKIT_OWNER_MARKER" > "$FB/.mukit/owner"
cp "$FIX/cxbottle.conf" "$FB/cxbottle.conf"
cp "$FIX/fake-bottle-user.reg" "$FB/user.reg"
cp "$FIX/fake-bottle-system.reg" "$FB/system.reg"
cp "$CX_ROOT/lib/wine/i386-windows/opengl32.dll" "$FB/drive_c/windows/system32/opengl32.dll"
printf 'MZ native mscoree stand-in' > "$FB/drive_c/windows/system32/mscoree.dll"
: > "$FB/drive_c/windows/Microsoft.NET/Framework/v4.0.30319/clr.dll"
SRC="$TMPD/client"; mkdir -p "$SRC/Data/Launcher/Design"
printf 'fake main' > "$SRC/main.exe"; printf 'fake launcher' > "$SRC/MuTheMatrix.exe"
printf 'skin' > "$SRC/Data/Launcher/Design/Template.design"
cp "$FIX/LauncherOption.orig.if" "$SRC/LauncherOption.if"
printf 'transfer' > "$SRC/.mu-recovery-transfer.tar"
SETUP=("$KIT_DIR/setup-mu-mac.sh" --bottle FakeKit --game-dir "$SRC" --dll-source prebuilt --dll-dir "$DLLS" --modes '960x600 1024x640 1280x800 1600x1000 1728x1080' --no-desktop --skip-verify)

snap() { (cd "$TMPD" && find Bottles client -type f | LC_ALL=C sort | while IFS= read -r f; do printf '%s  %s\n' "$(mukit_sha256 "$f")" "$f"; done); }
before=$(snap)
"${SETUP[@]}" --dry-run > "$TMPD/dry.log" 2>&1; rc=$?
eq 'dry-run exit 0' "$rc" 0
yes 'snapshot is not empty (guards a vacuous comparison)' test -n "$before"
eq 'dry-run changed nothing' "$(snap)" "$before"
grep -q '\[dry-run\] cp .*-R' "$TMPD/dry.log" && ok 'dry-run plans clone copy' || bad 'dry-run plans clone copy'
grep -q 'Template.design.disabled' "$TMPD/dry.log" && ok 'dry-run plans skin rename' || bad 'dry-run plans skin rename'
grep -q 'winetricks' "$TMPD/dry.log" && bad 'dry-run: wine steps should be satisfied by fake registry' || ok 'dry-run: wine steps already satisfied'

"${SETUP[@]}" > "$TMPD/run1.log" 2>&1; rc=$?
eq 'first run exit 0' "$rc" 0
G="$FB/drive_c/MuTheMatrix"
yes 'game copied'                [ -f "$G/main.exe" ]
no  'transfer tar excluded'      [ -e "$G/.mu-recovery-transfer.tar" ]
yes 'skin renamed'               [ -f "$G/Data/Launcher/Design/Template.design.disabled" ]
yes 'source skin untouched'      [ -f "$SRC/Data/Launcher/Design/Template.design" ]
eq  'mugl deployed (v7.2)'       "$(mukit_sha256 "$G/opengl32.dll")" "$MUKIT_MUGL_V72_SHA256"
eq  'mscoree proxy deployed'     "$(mukit_sha256 "$G/mscoree.dll")" "$MUKIT_MSCOREE_PROXY_SHA256"
eq  'mu-modes.txt'               "$(cat "$FB/drive_c/mutools/mu-modes.txt")" '960x600 1024x640 1280x800 1600x1000 1728x1080'
eq  'mugl-mode.txt'              "$(cat "$FB/drive_c/mutools/mugl-mode.txt")" 'full+vbo'
eq  'mugl-hotpatch.txt'          "$(cat "$FB/drive_c/mutools/mugl-hotpatch.txt")" 7599
eq  'LauncherOption rewritten'   "$(od -An -tx1 < "$G/LauncherOption.if" | tr -d ' \n')" "$(mukit_lopt_render 4 1 '' | od -An -tx1 | tr -d ' \n')"
yes 'LauncherOption original kept' cmp -s "$G/LauncherOption.if.mukit-orig" "$FIX/LauncherOption.orig.if"
yes 'launcher config written (missing in source)' grep -q 'v4.8' "$G/MuTheMatrix.exe.config"

"${SETUP[@]}" > "$TMPD/run2.log" 2>&1; rc=$?
eq 'second run exit 0' "$rc" 0
if grep -q '\[do\]' "$TMPD/run2.log"; then bad "second run is a no-op: $(grep '\[do\]' "$TMPD/run2.log" | head -3 | tr '\n' ';')"; else ok 'second run is a no-op (idempotent)'; fi

# A game update restoring the skin is re-disabled with a numbered suffix.
printf 'skin2' > "$G/Data/Launcher/Design/Template.design"
"${SETUP[@]}" > "$TMPD/run3.log" 2>&1
yes 'restored skin -> .disabled.1' [ -f "$G/Data/Launcher/Design/Template.design.disabled.1" ]

# A user's later launcher resolution choice is preserved without --reset-config.
mukit_lopt_render 2 1 '' > "$G/LauncherOption.if"
"${SETUP[@]}" > "$TMPD/run4.log" 2>&1
eq 'user DevModeIndex preserved' "$(mukit_lopt_get "$G/LauncherOption.if" DevModeIndex)" 2
"${SETUP[@]}" --reset-config > "$TMPD/run5.log" 2>&1
eq '--reset-config restores index' "$(mukit_lopt_get "$G/LauncherOption.if" DevModeIndex)" 4
# A kit-written index (like the --mugl-repo cap at 2) follows the options on the next run.
"${SETUP[@]}" --mode-index 2 > "$TMPD/run5b.log" 2>&1
eq 'kit writes --mode-index 2' "$(mukit_lopt_get "$G/LauncherOption.if" DevModeIndex)" 2
"${SETUP[@]}" > "$TMPD/run5c.log" 2>&1
eq 'kit-written index is not mistaken for a user choice' "$(mukit_lopt_get "$G/LauncherOption.if" DevModeIndex)" 4

eq 'up-to-date DLL recorded as kit-managed' "$(cat "$FB/.mukit/opengl32.dll.sha256")" "$MUKIT_MUGL_V72_SHA256"
ls "$G"/*.mukit-backup-* > /dev/null 2>&1 && bad 'no backups of kit-managed DLLs' || ok 'no backups of kit-managed DLLs'
"$KIT_DIR/verify-mu-mac.sh" --bottle FakeKit > "$TMPD/verify.log" 2>&1; rc=$?
eq 'verify on fake bottle: no FAIL' "$rc" 0
grep -q 'WARN  main.exe' "$TMPD/verify.log" && ok 'verify flags untested main.exe' || bad 'verify flags untested main.exe'
grep -q 'v7.2 (pinned' "$TMPD/verify.log" && ok 'verify accepts kit mugl v7.2' || bad 'verify accepts kit mugl v7.2'
grep -q 'PASS  mugl-hotpatch.txt *7599' "$TMPD/verify.log" && ok 'verify: 7599 is the norm' || bad 'verify: 7599 is the norm'

# Rollback to v7.0 and back; the hotpatch file written by an earlier kit (15) is upgraded.
"${SETUP[@]}" --mugl-version v70 > "$TMPD/run6.log" 2>&1; rc=$?
eq 'v70 rollback exit 0' "$rc" 0
eq 'v70 deployed' "$(mukit_sha256 "$G/opengl32.dll")" "$MUKIT_MUGL_V70_SHA256"
"$KIT_DIR/verify-mu-mac.sh" --bottle FakeKit > "$TMPD/verify70.log" 2>&1; rc=$?
eq 'verify v70: no FAIL' "$rc" 0
grep -q 'v7.0 (pinned rollback' "$TMPD/verify70.log" && ok 'verify names v7.0 rollback' || bad 'verify names v7.0 rollback'
printf '15\n' > "$FB/drive_c/mutools/mugl-hotpatch.txt"
"${SETUP[@]}" > "$TMPD/run7.log" 2>&1
eq 'back to v7.2' "$(mukit_sha256 "$G/opengl32.dll")" "$MUKIT_MUGL_V72_SHA256"
eq 'old kit default 15 upgraded' "$(cat "$FB/drive_c/mutools/mugl-hotpatch.txt")" 7599
printf '6575\n' > "$FB/drive_c/mutools/mugl-hotpatch.txt"
"${SETUP[@]}" > "$TMPD/run8.log" 2>&1
eq 'user mask 6575 kept' "$(cat "$FB/drive_c/mutools/mugl-hotpatch.txt")" 6575
"$KIT_DIR/verify-mu-mac.sh" --bottle FakeKit > "$TMPD/verify6575.log" 2>&1
grep -q 'PASS  mugl-hotpatch.txt *6575 .*without the frame pacing fix' "$TMPD/verify6575.log" && ok 'verify accepts 6575' || bad 'verify accepts 6575'
printf '7599\n' > "$FB/drive_c/mutools/mugl-hotpatch.txt"

echo '# Desktop launcher step (temporary HOME)'
FH="$TMPD/home"; mkdir -p "$FH/Desktop"
DSETUP=("$KIT_DIR/setup-mu-mac.sh" --bottle FakeKit --dll-source prebuilt --dll-dir "$DLLS" --modes '960x600 1024x640 1280x800 1600x1000 1728x1080' --skip-verify)
HOME="$FH" "${DSETUP[@]}" > "$TMPD/d1.log" 2>&1; rc=$?
LF="$FH/Desktop/Play Mu The Matrix (FakeKit).command"
eq 'desktop run exit 0' "$rc" 0
yes 'launcher written + executable' [ -x "$LF" ]
eq 'launcher targets bottle' "$(mukit_launcher_bottle "$LF")" FakeKit
yes 'launcher calls play-mu.sh' grep -q "play-mu.sh" "$LF"
yes 'launcher plain Rosetta by default' grep -q 'MU_FAST_X87=0' "$LF"
HOME="$FH" "${DSETUP[@]}" > "$TMPD/d2.log" 2>&1
grep -q '\[do\]' "$TMPD/d2.log" && bad 'desktop rerun no-op' || ok 'desktop rerun no-op'
printf '#!/bin/zsh\necho mine\n' > "$FH/Desktop/Mine.command"
HOME="$FH" "${DSETUP[@]}" --launcher-name Mine.command > /dev/null 2>&1 && bad 'refuse overwriting foreign .command' || ok 'refuse overwriting foreign .command'
eq 'foreign .command untouched' "$(cat "$FH/Desktop/Mine.command")" $'#!/bin/zsh\necho mine'

echo '# build path: public mugl + mscoree proxy from the repository sources (needs MinGW and python3)'
if command -v "${MINGW_CC:-i686-w64-mingw32-gcc}" >/dev/null 2>&1 && command -v python3 >/dev/null 2>&1; then
    BB="$MUKIT_BOTTLES_DIR/FakeBuild"; mkdir -p "$BB/.mukit" "$BB/drive_c/windows/system32" "$BB/drive_c/windows/Microsoft.NET/Framework/v4.0.30319/WPF"
    printf '%s\n' "$MUKIT_OWNER_MARKER" > "$BB/.mukit/owner"
    cp "$FIX/cxbottle.conf" "$BB/cxbottle.conf"; cp "$FIX/fake-bottle-user.reg" "$BB/user.reg"; cp "$FIX/fake-bottle-system.reg" "$BB/system.reg"
    cp "$CX_ROOT/lib/wine/i386-windows/opengl32.dll" "$BB/drive_c/windows/system32/opengl32.dll"
    printf 'MZ native mscoree stand-in' > "$BB/drive_c/windows/system32/mscoree.dll"; : > "$BB/drive_c/windows/Microsoft.NET/Framework/v4.0.30319/clr.dll"
    MUKIT_BUILD_DIR="$TMPD/kitbuild" "$KIT_DIR/setup-mu-mac.sh" --bottle FakeBuild --game-dir "$SRC" --modes '960x600 1024x640 1280x800 1600x1000 1728x1080' --no-desktop --skip-verify > "$TMPD/build.log" 2>&1; rc=$?
    eq 'default build path exit 0' "$rc" 0
    BG="$BB/drive_c/MuTheMatrix"
    eq 'built mugl is a PE file'    "$(head -c 2 "$BG/opengl32.dll")" MZ
    eq 'built mscoree is a PE file' "$(head -c 2 "$BG/mscoree.dll")" MZ
    eq 'build recorded as kit-managed' "$(cat "$BB/.mukit/opengl32.dll.sha256")" "$(mukit_sha256 "$BG/opengl32.dll")"
    yes 'public mugl warning: DevModeIndex capped' grep -q 'capping DevModeIndex at 2' "$TMPD/build.log"
    eq 'capped DevModeIndex written' "$(mukit_lopt_get "$BG/LauncherOption.if" DevModeIndex)" 2
    no 'build did not write into the checkout' test -e "$KIT_DIR/../mugl/build"
    "$KIT_DIR/verify-mu-mac.sh" --bottle FakeBuild > "$TMPD/verify-build.log" 2>&1; rc=$?
    eq 'verify on built bottle: no FAIL' "$rc" 0
    grep -q 'kit-installed build' "$TMPD/verify-build.log" && ok 'verify accepts the kit-built mugl' || bad 'verify accepts the kit-built mugl'
else
    echo 'skip  build path (no MinGW cross-compiler or python3)'
fi

echo '# .NET detection (fresh CrossOver bottles pre-register Release 533320 / Version 4.7.03190)'
yes '.NET 4.8 recognised in fake bottle' mukit_dotnet48_state "$FB"
cp "$FB/system.reg" "$TMPD/system.reg.keep"
sedi 's/"Release"=dword:00080eb1/"Release"=dword:00082348/;s/"Version"="4.8.03761"/"Version"="4.7.03190"/' "$FB/system.reg"
no 'Wine placeholder registration is not .NET 4.8' mukit_dotnet48_state "$FB"
"${SETUP[@]}" --dry-run > "$TMPD/dry-net.log" 2>&1
grep -q 'winetricks -q dotnet48' "$TMPD/dry-net.log" && ok 'placeholder -> setup plans dotnet48' || bad 'placeholder -> setup plans dotnet48'
grep -q "W_CACHE=$HOME/.cache/winetricks\|W_CACHE=.*winetricks" "$TMPD/dry-net.log" && ok 'winetricks gets explicit W_CACHE' || bad 'winetricks gets explicit W_CACHE'
"$KIT_DIR/verify-mu-mac.sh" --bottle FakeKit > /dev/null 2>&1 && bad 'verify FAILs placeholder .NET' || ok 'verify FAILs placeholder .NET'
cp "$TMPD/system.reg.keep" "$FB/system.reg"

echo '# refusals'
for b in MuMatrix32 windows10mu; do
    "$KIT_DIR/setup-mu-mac.sh" --dry-run --bottle "$b" --game-dir "$SRC" > /dev/null 2>&1 && bad "refuse $b" || ok "refuse $b"
done
mkdir -p "$MUKIT_BOTTLES_DIR/Foreign"; : > "$MUKIT_BOTTLES_DIR/Foreign/cxbottle.conf"
"$KIT_DIR/setup-mu-mac.sh" --dry-run --bottle Foreign --game-dir "$SRC" > /dev/null 2>&1 && bad 'refuse unowned existing bottle' || ok 'refuse unowned existing bottle'
"${SETUP[@]}" --dry-run --modes 'big' > /dev/null 2>&1 && bad 'refuse bad --modes' || ok 'refuse bad --modes'
"${SETUP[@]}" --dry-run --mode-index 9 > /dev/null 2>&1 && bad 'refuse out-of-range index' || ok 'refuse out-of-range index'
"${SETUP[@]}" --dry-run --ac-variant no-ac > /dev/null 2>&1 && bad 'no-ac TODO hook refuses' || ok 'no-ac TODO hook refuses'
"${SETUP[@]}" --dry-run --mugl-version v69 > /dev/null 2>&1 && bad 'refuse unknown --mugl-version' || ok 'refuse unknown --mugl-version'
"${SETUP[@]}" --dry-run --hotpatch-mask 20000 > /dev/null 2>&1 && bad 'refuse bad --hotpatch-mask' || ok 'refuse bad --hotpatch-mask'
"${SETUP[@]}" --dry-run --dll-source prebuilt --dll-dir "$TMPD/nonexistent" > /dev/null 2>&1 && bad 'refuse missing --dll-dir' || ok 'refuse missing --dll-dir'
env -u MU_DLL_DIR "$KIT_DIR/setup-mu-mac.sh" --dry-run --bottle FakeKit --game-dir "$SRC" --dll-source prebuilt --modes '960x600' > /dev/null 2>&1 && bad 'prebuilt without --dll-dir is refused' || ok 'prebuilt without --dll-dir is refused'
mkdir -p "$TMPD/baddlls"; cp "$DLLS"/* "$TMPD/baddlls/"; printf 'tampered' >> "$TMPD/baddlls/mugl-v72.dll"
"${SETUP[@]}" --dll-dir "$TMPD/baddlls" > "$TMPD/tamper.log" 2>&1 && bad 'refuse DLL with the wrong SHA-256' || { grep -q 'does not match the pinned' "$TMPD/tamper.log" && ok 'refuse DLL with the wrong SHA-256' || bad 'tamper message'; }
"${SETUP[@]}" --dry-run --dll-source build --mugl-build private > "$TMPD/priv.log" 2>&1 && bad 'private build without your own private DLL is refused' || ok 'private build without your own private DLL is refused'
"${SETUP[@]}" --dry-run --mugl-build both > /dev/null 2>&1 && bad 'refuse bad --mugl-build' || ok 'refuse bad --mugl-build'
sedi 's/"WineArch" = "win32"/"WineArch" = "win64"/' "$FB/cxbottle.conf"
"${SETUP[@]}" --dry-run > /dev/null 2>&1 && bad 'refuse win64 bottle' || ok 'refuse win64 bottle'
"$KIT_DIR/verify-mu-mac.sh" --bottle FakeKit > /dev/null 2>&1 && bad 'verify FAILs win64' || ok 'verify FAILs win64'

printf '\n%d passed, %d failed\n' "$NPASS" "$NFAIL"
[ "$NFAIL" = 0 ]
