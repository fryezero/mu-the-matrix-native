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
DLLS="$TMPD/dlls"; mkdir -p "$DLLS" "$TMPD/nopgrep"
printf '#!/bin/sh\nexit 1\n' > "$TMPD/nopgrep/pgrep"; chmod 755 "$TMPD/nopgrep/pgrep"
mkdll "$DLLS/mugl-v76.dll" v76; mkdll "$DLLS/mugl-v75.dll" v75; mkdll "$DLLS/mugl-v72.dll" v72; mkdll "$DLLS/mugl-v71.dll" v71; mkdll "$DLLS/mugl-v70.dll" v70; mkdll "$DLLS/mscoree.dll" mscoree
mkdll "$DLLS/ndp48.exe" dotnet
FAKECX="$TMPD/CrossOver"; mkdir -p "$FAKECX/bin" "$FAKECX/lib/wine/i386-windows"
for b in cxbottle wine wineserver; do printf '#!/bin/sh\necho "stub %s: should not run in tests" >&2\nexit 99\n' "$b" > "$FAKECX/bin/$b"; chmod 755 "$FAKECX/bin/$b"; done
mkbuiltin "$FAKECX/lib/wine/i386-windows/opengl32.dll" stand-in
CX_ROOT=$FAKECX; MUKIT_SKIP_PLATFORM_CHECK=1
MUKIT_MUGL_V76_SHA256=$(mukit_sha256 "$DLLS/mugl-v76.dll"); MUKIT_MUGL_V75_SHA256=$(mukit_sha256 "$DLLS/mugl-v75.dll"); MUKIT_MUGL_V72_SHA256=$(mukit_sha256 "$DLLS/mugl-v72.dll"); MUKIT_MUGL_V71_SHA256=$(mukit_sha256 "$DLLS/mugl-v71.dll")
MUKIT_MUGL_V70_SHA256=$(mukit_sha256 "$DLLS/mugl-v70.dll"); MUKIT_MSCOREE_PROXY_SHA256=$(mukit_sha256 "$DLLS/mscoree.dll")
MUKIT_DOTNET48_INSTALLER_SHA256=$(mukit_sha256 "$DLLS/ndp48.exe")
export CX_ROOT MUKIT_SKIP_PLATFORM_CHECK MUKIT_MUGL_V76_SHA256 MUKIT_MUGL_V75_SHA256 MUKIT_MUGL_V72_SHA256 MUKIT_MUGL_V71_SHA256 MUKIT_MUGL_V70_SHA256 MUKIT_MSCOREE_PROXY_SHA256 MUKIT_DOTNET48_INSTALLER_SHA256
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
yes 'hotpatch 875951 (v7.4 default)' mukit_hotpatch_valid 875951
yes 'hotpatch 2097151' mukit_hotpatch_valid 2097151
yes 'hotpatch 44916143 (v7.5 default)' mukit_hotpatch_valid 44916143
yes 'hotpatch 380460463 (kit default, v7.6 JPEG and CRC bits)' mukit_hotpatch_valid 380460463
yes 'hotpatch 112025007 (previous kit default) valid' mukit_hotpatch_valid 112025007
yes 'hotpatch 30-bit value accepted' mukit_hotpatch_valid 380050863
yes 'hotpatch 67108863' mukit_hotpatch_valid 67108863
no 'hotpatch x'   mukit_hotpatch_valid x
yes 'hotpatch 67108864 (v7.6 JPEG bit)' mukit_hotpatch_valid 67108864
yes 'hotpatch 2147483647 (max)' mukit_hotpatch_valid 2147483647
no 'hotpatch 2147483648' mukit_hotpatch_valid 2147483648
eq 'v7.5 default keeps v7.0 bits' "$((MUKIT_HOTPATCH_DEFAULT & 31))" "$MUKIT_HOTPATCH_V70_BITS"
eq 'v7.1/v7.2 read their default' "$((MUKIT_HOTPATCH_DEFAULT & 16383))" 7599
eq 'v7.3 reads its default' "$((MUKIT_HOTPATCH_DEFAULT & 65535))" 23983
eq 'v7.5 reads its default (26 bits)' "$((MUKIT_HOTPATCH_DEFAULT & 67108863))" 44916143
eq 'kit default has the CRC bit' "$((MUKIT_HOTPATCH_DEFAULT & 268435456))" 268435456
eq 'v7.4 reads its default' "$((MUKIT_HOTPATCH_DEFAULT & 2097151))" 875951
yes 'mugl mode with v7.4 diagnostics' mukit_mugl_mode_valid full+vbo+time+finish

echo '# pinned hashes (real pins are tested in a subshell without the test overrides)'
PINS=$(env -u MUKIT_MUGL_V76_SHA256 -u MUKIT_MUGL_V75_SHA256 -u MUKIT_MUGL_V72_SHA256 -u MUKIT_MUGL_V71_SHA256 -u MUKIT_MUGL_V70_SHA256 -u MUKIT_MSCOREE_PROXY_SHA256 -u MUKIT_DOTNET48_INSTALLER_SHA256 \
    bash -c 'source "$1"; printf "%s %s %s %s %s %s %s %s %s" "$MUKIT_MUGL_V76_SHA256" "$MUKIT_MUGL_V75_SHA256" "$MUKIT_MUGL_V72_SHA256" "$MUKIT_MUGL_V71_SHA256" "$MUKIT_MUGL_V70_SHA256" "$MUKIT_MSCOREE_PROXY_SHA256" "$MUKIT_DOTNET48_INSTALLER_SHA256" "$MUKIT_MAIN_EXE_SHA256" "$MUKIT_LAUNCHER_EXE_SHA256"' _ "$KIT_DIR/lib/mukit.sh")
n=0; for h in $PINS; do n=$((n + 1)); [[ "$h" =~ ^[0-9a-f]{64}$ ]] && ok "pin $n is a SHA-256" || bad "pin $n is a SHA-256: $h"; done
eq 'pin count' "$n" 9
eq 'real pins are not the synthetic test hashes' "$(printf '%s\n' $PINS | sort -u | wc -l | tr -d ' ')" 9
eq 'identify v7.1'     "$(mukit_mugl_identify "$MUKIT_MUGL_V71_SHA256")" v7.1
eq 'identify v7.2'     "$(mukit_mugl_identify "$MUKIT_MUGL_V72_SHA256")" v7.2
eq 'identify v7.5'     "$(mukit_mugl_identify "$MUKIT_MUGL_V75_SHA256")" v7.5
eq 'identify v7.6'     "$(mukit_mugl_identify "$MUKIT_MUGL_V76_SHA256")" v7.6
eq 'identify v7.6 without CRC' "$(mukit_mugl_identify "$MUKIT_MUGL_V76J_SHA256")" v7.6-jpeg
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
eq  'mugl deployed (v7.6)'       "$(mukit_sha256 "$G/opengl32.dll")" "$MUKIT_MUGL_V76_SHA256"
eq  'mscoree proxy deployed'     "$(mukit_sha256 "$G/mscoree.dll")" "$MUKIT_MSCOREE_PROXY_SHA256"
eq  'mu-modes.txt'               "$(cat "$FB/drive_c/mutools/mu-modes.txt")" '960x600 1024x640 1280x800 1600x1000 1728x1080'
eq  'mugl-mode.txt'              "$(cat "$FB/drive_c/mutools/mugl-mode.txt")" 'full+vbo'
eq  'mugl-hotpatch.txt'          "$(cat "$FB/drive_c/mutools/mugl-hotpatch.txt")" 380460463
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

eq 'up-to-date DLL recorded as kit-managed' "$(cat "$FB/.mukit/opengl32.dll.sha256")" "$MUKIT_MUGL_V76_SHA256"
ls "$G"/*.mukit-backup-* > /dev/null 2>&1 && bad 'no backups of kit-managed DLLs' || ok 'no backups of kit-managed DLLs'
"$KIT_DIR/verify-mu-mac.sh" --bottle FakeKit > "$TMPD/verify.log" 2>&1; rc=$?
eq 'verify on fake bottle: no FAIL' "$rc" 0
grep -q 'WARN  main.exe' "$TMPD/verify.log" && ok 'verify flags untested main.exe' || bad 'verify flags untested main.exe'
grep -q 'v7.6 (pinned' "$TMPD/verify.log" && ok 'verify accepts kit mugl v7.6' || bad 'verify accepts kit mugl v7.6'
grep -q 'PASS  mugl-hotpatch.txt *380460463' "$TMPD/verify.log" && ok 'verify: 380460463 is the norm' || bad 'verify: 380460463 is the norm'

# Rollback to v7.0 and back; the hotpatch file written by an earlier kit (15) is upgraded.
"${SETUP[@]}" --mugl-version v70 > "$TMPD/run6.log" 2>&1; rc=$?
eq 'v70 rollback exit 0' "$rc" 0
eq 'v70 deployed' "$(mukit_sha256 "$G/opengl32.dll")" "$MUKIT_MUGL_V70_SHA256"
"$KIT_DIR/verify-mu-mac.sh" --bottle FakeKit > "$TMPD/verify70.log" 2>&1; rc=$?
eq 'verify v70: no FAIL' "$rc" 0
grep -q 'v7.0 (pinned rollback' "$TMPD/verify70.log" && ok 'verify names v7.0 rollback' || bad 'verify names v7.0 rollback'
printf '15\n' > "$FB/drive_c/mutools/mugl-hotpatch.txt"
"${SETUP[@]}" > "$TMPD/run7.log" 2>&1
eq 'back to v7.6' "$(mukit_sha256 "$G/opengl32.dll")" "$MUKIT_MUGL_V76_SHA256"
eq 'old kit default 15 upgraded' "$(cat "$FB/drive_c/mutools/mugl-hotpatch.txt")" 380460463
printf '7599\n' > "$FB/drive_c/mutools/mugl-hotpatch.txt"
"${SETUP[@]}" > "$TMPD/run7b.log" 2>&1
eq 'old kit default 7599 upgraded' "$(cat "$FB/drive_c/mutools/mugl-hotpatch.txt")" 380460463
printf '875951\n' > "$FB/drive_c/mutools/mugl-hotpatch.txt"
"${SETUP[@]}" > "$TMPD/run7a.log" 2>&1
eq 'old kit default 875951 upgraded' "$(cat "$FB/drive_c/mutools/mugl-hotpatch.txt")" 380460463
printf '44916143\n' > "$FB/drive_c/mutools/mugl-hotpatch.txt"
"${SETUP[@]}" > "$TMPD/run7d.log" 2>&1
eq 'old kit default 44916143 (v7.5) upgraded' "$(cat "$FB/drive_c/mutools/mugl-hotpatch.txt")" 380460463
printf '112025007\n' > "$FB/drive_c/mutools/mugl-hotpatch.txt"
"${SETUP[@]}" > "$TMPD/run7e.log" 2>&1
eq 'old kit default 112025007 (v7.6 without CRC) upgraded' "$(cat "$FB/drive_c/mutools/mugl-hotpatch.txt")" 380460463
printf '23983\n' > "$FB/drive_c/mutools/mugl-hotpatch.txt"
"${SETUP[@]}" > "$TMPD/run7c.log" 2>&1
eq 'user mask 23983 (v7.3 default) kept' "$(cat "$FB/drive_c/mutools/mugl-hotpatch.txt")" 23983
"$KIT_DIR/verify-mu-mac.sh" --bottle FakeKit > "$TMPD/verify23983.log" 2>&1
grep -q 'PASS  mugl-hotpatch.txt *23983 .*v7.3 default' "$TMPD/verify23983.log" && ok 'verify names the v7.3 default' || bad 'verify names the v7.3 default'
printf '6575\n' > "$FB/drive_c/mutools/mugl-hotpatch.txt"
"${SETUP[@]}" > "$TMPD/run8.log" 2>&1
eq 'user mask 6575 kept' "$(cat "$FB/drive_c/mutools/mugl-hotpatch.txt")" 6575
"$KIT_DIR/verify-mu-mac.sh" --bottle FakeKit > "$TMPD/verify6575.log" 2>&1
grep -q 'PASS  mugl-hotpatch.txt *6575 .*without the frame pacing fix' "$TMPD/verify6575.log" && ok 'verify accepts 6575' || bad 'verify accepts 6575'
printf '380460463\n' > "$FB/drive_c/mutools/mugl-hotpatch.txt"

echo '# Desktop launcher step (temporary HOME)'
FH="$TMPD/home"; mkdir -p "$FH/Desktop"
DSETUP=("$KIT_DIR/setup-mu-mac.sh" --bottle FakeKit --dll-source prebuilt --dll-dir "$DLLS" --modes '960x600 1024x640 1280x800 1600x1000 1728x1080' --skip-verify)
HOME="$FH" "${DSETUP[@]}" > "$TMPD/d1.log" 2>&1; rc=$?
LF="$FH/Desktop/Play Mu The Matrix (FakeKit).command"
eq 'desktop run exit 0' "$rc" 0
yes 'launcher written + executable' [ -x "$LF" ]
eq 'launcher targets bottle' "$(mukit_launcher_bottle "$LF")" FakeKit
yes 'launcher calls play-mu.sh' grep -q "play-mu.sh" "$LF"
yes 'launcher keeps normal priority (zsh NO_BG_NICE)' grep -q '^setopt NO_BG_NICE' "$LF"
yes 'launcher plain Rosetta by default' grep -q 'MU_FAST_X87=0' "$LF"
HOME="$FH" "${DSETUP[@]}" > "$TMPD/d2.log" 2>&1
grep -q '\[do\]' "$TMPD/d2.log" && bad 'desktop rerun no-op' || ok 'desktop rerun no-op'
printf '#!/bin/zsh\necho mine\n' > "$FH/Desktop/Mine.command"
HOME="$FH" "${DSETUP[@]}" --launcher-name Mine.command > /dev/null 2>&1 && bad 'refuse overwriting foreign .command' || ok 'refuse overwriting foreign .command'
eq 'foreign .command untouched' "$(cat "$FH/Desktop/Mine.command")" $'#!/bin/zsh\necho mine'
TW="$TMPD/timewalker"; mkdir -p "$TW/scripts" "$TW/build"
TW=$(cd -- "$TW" && pwd -P)   # setup records the physical path (macOS: /var -> /private/var)
printf '#!/bin/sh\nexit 0\n' > "$TW/scripts/run-crossover.sh"; chmod 755 "$TW/scripts/run-crossover.sh"; : > "$TW/build/libtimewalker.dylib"
HOME="$FH" "${DSETUP[@]}" --fast-x87 --timewalker-dir "$TW" > "$TMPD/x87.log" 2>&1
yes 'fast x87 launcher sets MU_FAST_X87=1' grep -q 'MU_FAST_X87=1' "$LF"
yes 'fast x87 launcher passes MU_TIMEWALKER_DIR' grep -q "MU_TIMEWALKER_DIR='$TW'" "$LF"
HOME="$FH" "$KIT_DIR/verify-mu-mac.sh" --bottle FakeKit > "$TMPD/vx87.log" 2>&1
grep -q '^PASS  fast x87' "$TMPD/vx87.log" && ok 'verify: launcher fast x87 build present' || bad 'verify: launcher fast x87 build present'
rm "$TW/build/libtimewalker.dylib"
HOME="$FH" "$KIT_DIR/verify-mu-mac.sh" --bottle FakeKit > "$TMPD/vx87b.log" 2>&1
grep -q '^WARN  fast x87' "$TMPD/vx87b.log" && ok 'verify WARNs: launcher fast x87 build missing' || bad 'verify WARNs: launcher fast x87 build missing'
HOME="$FH" "${DSETUP[@]}" > /dev/null 2>&1
yes 'rerun without --fast-x87 restores plain launcher' grep -q 'MU_FAST_X87=0' "$LF"

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
    # Rebuilds must be byte-identical (no PE timestamp), so a rerun leaves the installed DLLs alone.
    MUKIT_BUILD_DIR="$TMPD/kitbuild" "$KIT_DIR/setup-mu-mac.sh" --bottle FakeBuild --modes '960x600 1024x640 1280x800 1600x1000 1728x1080' --no-desktop --skip-verify > "$TMPD/build2.log" 2>&1
    grep -q '\[do\]   install' "$TMPD/build2.log" && bad 'build rerun: DLLs unchanged (reproducible build)' || ok 'build rerun: DLLs unchanged (reproducible build)'
    # Prebuilt with a mugl-only --dll-dir (no mscoree.dll): the public mscoree proxy is built instead.
    mkdir -p "$TMPD/muglonly"; cp "$DLLS/mugl-v76.dll" "$TMPD/muglonly/"
    MUKIT_BUILD_DIR="$TMPD/kitbuild" "$KIT_DIR/setup-mu-mac.sh" --bottle FakeBuild --dll-source prebuilt --dll-dir "$TMPD/muglonly" --modes '960x600 1024x640 1280x800 1600x1000 1728x1080' --no-desktop --skip-verify > "$TMPD/muglonly.log" 2>&1; rc=$?
    eq 'prebuilt mugl-only --dll-dir exit 0' "$rc" 0
    grep -q 'building the mscoree proxy' "$TMPD/muglonly.log" && ok 'mugl-only --dll-dir builds the mscoree proxy' || bad 'mugl-only --dll-dir builds the mscoree proxy'
    eq 'prebuilt mugl deployed from mugl-only dir' "$(mukit_sha256 "$BG/opengl32.dll")" "$MUKIT_MUGL_V76_SHA256"
    eq 'built mscoree deployed with mugl-only dir' "$(mukit_sha256 "$BG/mscoree.dll")" "$(mukit_sha256 "$TMPD/kitbuild/mscoree.dll")"
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
"${SETUP[@]}" --dry-run --hotpatch-mask 2147483648 > /dev/null 2>&1 && bad 'refuse bad --hotpatch-mask' || ok 'refuse bad --hotpatch-mask'
"${SETUP[@]}" --dry-run --dll-source prebuilt --dll-dir "$TMPD/nonexistent" > /dev/null 2>&1 && bad 'refuse missing --dll-dir' || ok 'refuse missing --dll-dir'
env -u MU_DLL_DIR "$KIT_DIR/setup-mu-mac.sh" --dry-run --bottle FakeKit --game-dir "$SRC" --dll-source prebuilt --modes '960x600' > /dev/null 2>&1 && bad 'prebuilt without --dll-dir is refused' || ok 'prebuilt without --dll-dir is refused'
mkdir -p "$TMPD/baddlls"; cp "$DLLS"/* "$TMPD/baddlls/"; printf 'tampered' >> "$TMPD/baddlls/mugl-v76.dll"
"${SETUP[@]}" --dll-dir "$TMPD/baddlls" > "$TMPD/tamper.log" 2>&1 && bad 'refuse DLL with the wrong SHA-256' || { grep -q 'does not match the pinned' "$TMPD/tamper.log" && ok 'refuse DLL with the wrong SHA-256' || bad 'tamper message'; }
MUKIT_PRIVATE_BUILD_DIR="$TMPD/no-private-build" "${SETUP[@]}" --dry-run --dll-source build --mugl-build private > "$TMPD/priv.log" 2>&1 && bad 'private build without your own private DLL is refused' || ok 'private build without your own private DLL is refused'
"${SETUP[@]}" --dry-run --mugl-build both > /dev/null 2>&1 && bad 'refuse bad --mugl-build' || ok 'refuse bad --mugl-build'
sedi 's/"WineArch" = "win32"/"WineArch" = "win64"/' "$FB/cxbottle.conf"
"${SETUP[@]}" --dry-run > /dev/null 2>&1 && bad 'refuse win64 bottle' || ok 'refuse win64 bottle'
"$KIT_DIR/verify-mu-mac.sh" --bottle FakeKit > /dev/null 2>&1 && bad 'verify FAILs win64' || ok 'verify FAILs win64'

echo '# free runtime (no CrossOver): synthetic runtime archive, prefix and winetricks; nothing real runs'
FH2="$TMPD/freehome"; RTSRC="$TMPD/rtsrc"; FREC="$TMPD/freerec"; mkdir -p "$RTSRC/wine/bin" "$RTSRC/wine/lib/wine/x86_64-unix" "$RTSRC/wine/lib/wine/i386-windows" "$FREC"
cat > "$RTSRC/wine/bin/wine" <<EOS
#!/bin/sh
[ "\$1" = --version ] && { echo "wine-11.0 (synthetic)"; exit 0; }
printf '%s|%s\\n' "\${WINEPREFIX:-unset}" "\$*" >> "$FREC/wine.calls"
# "wine SETUP.exe /S" stands in for the official game installer: it "installs" two synthetic files.
case "\$1" in *.exe) if [ "\${2:-}" = /S ]; then
    d="\$WINEPREFIX/drive_c/Program Files/Glitch Games Network/Mu The Matrix"; mkdir -p "\$d"
    printf 'fake main' > "\$d/main.exe"; printf 'fake launcher' > "\$d/MuTheMatrix.exe"; fi ;; esac
exit 0
EOS
printf '#!/bin/sh\nprintf "%%s|%%s\\n" "${WINEPREFIX:-unset}" "$*" >> "%s/wineserver.calls"\nexit 0\n' "$FREC" > "$RTSRC/wine/bin/wineserver"
chmod 755 "$RTSRC/wine/bin/wine" "$RTSRC/wine/bin/wineserver"; : > "$RTSRC/wine/lib/wine/x86_64-unix/ntdll.so"
mkbuiltin "$RTSRC/wine/lib/wine/i386-windows/opengl32.dll" stand-in
(cd "$RTSRC" && tar -cJf "$TMPD/runtime.tar.xz" .)
RTSHA=$(mukit_sha256 "$TMPD/runtime.tar.xz")
FP="$FH2/prefix"
mkdir -p "$FP/.mukit" "$FP/drive_c/windows/system32" "$FP/drive_c/windows/Microsoft.NET/Framework/v4.0.30319/WPF" "$FH2/tools"
printf '%s\n' "$MUKIT_FREE_OWNER_MARKER" > "$FP/.mukit/owner"
cp "$FIX/fake-bottle-user.reg" "$FP/user.reg"; cp "$FIX/fake-bottle-system.reg" "$FP/system.reg"
mkbuiltin "$FP/drive_c/windows/system32/opengl32.dll" stand-in
printf 'MZ native mscoree stand-in' > "$FP/drive_c/windows/system32/mscoree.dll"; : > "$FP/drive_c/windows/Microsoft.NET/Framework/v4.0.30319/clr.dll"
printf '#!/bin/sh\necho synthetic winetricks; exit 0\n' > "$FH2/tools/winetricks"; chmod 755 "$FH2/tools/winetricks"
export MUKIT_WINETRICKS_SHA256=$(mukit_sha256 "$FH2/tools/winetricks")
FSETUP=(env MUKIT_FREE_HOME="$FH2" "$KIT_DIR/setup-mu-mac.sh" --runtime-archive "$TMPD/runtime.tar.xz" --game-dir "$SRC" --mugl-dll "$DLLS/mugl-v75.dll" --mscoree-dll "$DLLS/mscoree.dll" --modes '960x600 1024x640 1280x800 1600x1000 1728x1080' --no-desktop --skip-verify)
"${FSETUP[@]}" --dry-run > "$TMPD/free-dry.log" 2>&1; rc=$?
eq 'free dry-run exit 0' "$rc" 0
grep -q 'runtime=free' "$TMPD/free-dry.log" && ok 'free runtime is the default' || bad 'free runtime is the default'
no 'free dry-run installed nothing' test -e "$FH2/runtime"
"${FSETUP[@]}" > "$TMPD/free1.log" 2>&1; rc=$?
eq 'free first run exit 0' "$rc" 0
RTID="archive-${RTSHA:0:12}"
eq 'runtime/current names the archive runtime' "$(cat "$FH2/runtime/current" 2>/dev/null)" "$RTID"
yes 'runtime unpacked with marker' test -f "$FH2/runtime/$RTID/.mu-runtime"
yes 'runtime wine executable' test -x "$FH2/runtime/$RTID/wine/bin/wine"
yes 'free: game copied' test -f "$FP/drive_c/MuTheMatrix/main.exe"
eq 'free: mugl --mugl-dll deployed' "$(mukit_sha256 "$FP/drive_c/MuTheMatrix/opengl32.dll")" "$MUKIT_MUGL_V75_SHA256"
eq 'free: mscoree --mscoree-dll deployed' "$(mukit_sha256 "$FP/drive_c/MuTheMatrix/mscoree.dll")" "$MUKIT_MSCOREE_PROXY_SHA256"
eq 'free: pinned v7.5 keeps the full mode list' "$(mukit_lopt_get "$FP/drive_c/MuTheMatrix/LauncherOption.if" DevModeIndex)" 4
grep -q 'stub cxbottle\|stub wine' "$TMPD/free1.log" && bad 'free run never calls CrossOver' || ok 'free run never calls CrossOver'
"${FSETUP[@]}" > "$TMPD/free2.log" 2>&1; rc=$?
eq 'free rerun exit 0' "$rc" 0
grep -q '\[do\]' "$TMPD/free2.log" && bad 'free rerun is a no-op' || ok 'free rerun is a no-op'
# a repair without --runtime-archive keeps the installed archive runtime (no switch back to cx24)
env MUKIT_FREE_HOME="$FH2" "$KIT_DIR/setup-mu-mac.sh" --dry-run --game-dir "$SRC" --mugl-dll "$DLLS/mugl-v75.dll" --mscoree-dll "$DLLS/mscoree.dll" --modes '960x600 1024x640 1280x800 1600x1000 1728x1080' --no-desktop --skip-verify > "$TMPD/free-keep.log" 2>&1
grep -q "runtime=free ($RTID)" "$TMPD/free-keep.log" && ok 'repair keeps the archive runtime' || bad 'repair keeps the archive runtime'
grep -q 'WS12WineCX24\|select runtime' "$TMPD/free-keep.log" && bad 'repair does not switch to cx24' || ok 'repair does not switch to cx24'
MUKIT_FREE_HOME="$FH2" "$KIT_DIR/verify-mu-mac.sh" > "$TMPD/free-verify.log" 2>&1; rc=$?
eq 'verify (free default prefix): no FAIL' "$rc" 0
grep -q 'PASS  Wine runtime' "$TMPD/free-verify.log" && ok 'verify names the free runtime' || bad 'verify names the free runtime'
grep -q 'PASS  opengl32 = runtime i386 builtin' "$TMPD/free-verify.log" && ok 'verify compares opengl32 with the runtime' || bad 'verify compares opengl32 with the runtime'
# an unpinned --mugl-dll (e.g. a public build bundled in the app) is treated like the public build
printf 'MZ synthetic public build' > "$TMPD/public-opengl32.dll"
"${FSETUP[@]}" --mugl-dll "$TMPD/public-opengl32.dll" --reset-config > "$TMPD/free3.log" 2>&1; rc=$?
eq 'free unpinned mugl exit 0' "$rc" 0
grep -q 'not a pinned mugl build' "$TMPD/free3.log" && ok 'unpinned mugl warns' || bad 'unpinned mugl warns'
eq 'unpinned mugl caps DevModeIndex' "$(mukit_lopt_get "$FP/drive_c/MuTheMatrix/LauncherOption.if" DevModeIndex)" 2
# play-mu.sh with the free runtime: explicit prefix, relative launcher in C:\MuTheMatrix, no CrossOver
if command -v zsh >/dev/null 2>&1; then
    : > "$FREC/wine.calls"; : > "$FREC/wineserver.calls"
    env PATH="$TMPD/nopgrep:$PATH" MUKIT_FREE_HOME="$FH2" HOME="$TMPD/home" zsh "$KIT_DIR/play-mu.sh" > /dev/null 2>&1
    eq 'play-mu free: launcher started in the prefix' "$(tail -1 "$FREC/wine.calls")" "$FP|MuTheMatrix.exe"
    eq 'play-mu free: prefix wineserver reset' "$(tail -1 "$FREC/wineserver.calls")" "$FP|-k"
fi
# refusals
FP2="$TMPD/freehome2/prefix"; mkdir -p "$FP2"; printf 'x' > "$FP2/system.reg"
env MUKIT_FREE_HOME="$TMPD/freehome2" "$KIT_DIR/setup-mu-mac.sh" --dry-run --runtime-archive "$TMPD/runtime.tar.xz" --game-dir "$SRC" > /dev/null 2>&1 && bad 'free: refuse an unowned prefix' || ok 'free: refuse an unowned prefix'
env MUKIT_FREE_HOME="$FH2" "$KIT_DIR/setup-mu-mac.sh" --dry-run --prefix "$MUKIT_BOTTLES_DIR/Inside" --game-dir "$SRC" > /dev/null 2>&1 && bad "free: refuse a prefix in CrossOver's bottles" || ok "free: refuse a prefix in CrossOver's bottles"
sedi 's/^#arch=win32/#arch=win64/' "$FP/system.reg"
"${FSETUP[@]}" --dry-run > /dev/null 2>&1 && bad 'free: refuse a 64-bit prefix' || ok 'free: refuse a 64-bit prefix'
sedi 's/^#arch=win64/#arch=win32/' "$FP/system.reg"
"${FSETUP[@]}" --dry-run --runtime-archive https://example.invalid/rt.tar.xz > /dev/null 2>&1 && bad 'free: URL archive needs --runtime-sha256' || ok 'free: URL archive needs --runtime-sha256'
"${FSETUP[@]}" --dry-run --runtime bogus > /dev/null 2>&1 && bad 'refuse bad --runtime' || ok 'refuse bad --runtime'
"${FSETUP[@]}" --dry-run --game-installer "$TMPD/nope.exe" > /dev/null 2>&1 && bad 'refuse missing --game-installer' || ok 'refuse missing --game-installer'
env MUKIT_FREE_HOME="$TMPD/freehome3" "$KIT_DIR/setup-mu-mac.sh" --dry-run --game-installer official > "$TMPD/free-official.log" 2>&1
grep -q 'download https://dl.muthematrix.com/MuTheMatrix-21.1.2.12.exe' "$TMPD/free-official.log" && ok 'official installer URL planned' || bad 'official installer URL planned'
grep -q 'wineserver -p 5' "$TMPD/free-official.log" && ok 'free: 32-bit prefix created through the wineserver' || bad 'free: 32-bit prefix created through the wineserver'
grep -q 'WS12WineCX24.0.7_7.tar.xz' "$TMPD/free-official.log" && ok 'free: default runtime download planned' || bad 'free: default runtime download planned'
# fast x87 dry run from the app's layout (Resources/installer, no x87-main-only-wrapper.c beside it): a source
# folder that brings its own wrapper is copied, not built, so the dry run must not warn that it is missing.
APPRES="$TMPD/appres"; mkdir -p "$APPRES/installer/lib" "$APPRES/installer/registry" "$TMPD/fx-src" "$TMPD/fx-src-nowrap"
cp "$KIT_DIR/setup-mu-mac.sh" "$KIT_DIR/verify-mu-mac.sh" "$KIT_DIR/play-mu.sh" "$APPRES/installer/"
cp "$KIT_DIR/lib/mukit.sh" "$APPRES/installer/lib/"; cp "$KIT_DIR/registry/mu-mac.reg" "$APPRES/installer/registry/"
for f in libtimewalker.dylib runtime_loader libRuntimeRosettax87; do
    printf 'stub' > "$TMPD/fx-src/$f"; printf 'stub' > "$TMPD/fx-src-nowrap/$f"
done
printf 'stub' > "$TMPD/fx-src/x87-main-only-wrapper"
AFSETUP=(env MUKIT_FREE_HOME="$TMPD/freehome4" "$APPRES/installer/setup-mu-mac.sh" --dry-run --runtime-archive "$TMPD/runtime.tar.xz" --game-dir "$SRC" --no-desktop --skip-verify)
"${AFSETUP[@]}" --fast-x87-dir "$TMPD/fx-src" > "$TMPD/fx-app-dry.log" 2>&1; rc=$?
eq 'app-layout fast x87 dry run exit 0' "$rc" 0
grep -q 'no x87-main-only-wrapper' "$TMPD/fx-app-dry.log" && bad 'app-layout dry run: bundled wrapper not reported missing' || ok 'app-layout dry run: bundled wrapper not reported missing'
grep -q 'install fast x87 file x87-main-only-wrapper' "$TMPD/fx-app-dry.log" && ok 'app-layout dry run plans the wrapper copy' || bad 'app-layout dry run plans the wrapper copy'
"${AFSETUP[@]}" --fast-x87-dir "$TMPD/fx-src-nowrap" > "$TMPD/fx-app-dry2.log" 2>&1
grep -q 'no x87-main-only-wrapper and no compiler' "$TMPD/fx-app-dry2.log" && ok 'app-layout dry run without any wrapper still warns' || bad 'app-layout dry run without any wrapper still warns'
no 'app-layout dry runs installed nothing' test -e "$TMPD/freehome4/fast-x87"
echo '# download progress lines (MUKIT_PROGRESS=lines) with a synthetic curl'
# The synthetic curl: "-I" (HEAD) prints a Content-Length of 1000; a download appends 100-byte chunks to its -o file,
# one every MUKIT_TEST_CURL_DELAY seconds, continuing from the current size with -C -. It records its pid and arguments.
CURLBIN="$TMPD/curlbin"; mkdir -p "$CURLBIN"
cat > "$CURLBIN/curl" <<'EOS'
#!/bin/bash
out=; head=0; resume=0; prev=
for a in "$@"; do
    [ "$prev" = -o ] && out=$a
    [ "$prev" = -C ] && resume=1
    case "$a" in --*) ;; -*I*) head=1 ;; esac
    prev=$a
done
if [ "$head" = 1 ]; then printf 'HTTP/1.1 200 OK\r\nContent-Length: 1000\r\n\r\n'; exit 0; fi
echo $$ > "$MUKIT_TEST_REC/curl.pid"; printf '%s\n' "$*" >> "$MUKIT_TEST_REC/curl.calls"
[ "$resume" = 1 ] && [ -f "$out" ] || : > "$out"
n=$(wc -c < "$out" | tr -d ' ')
while [ "$n" -lt 1000 ]; do
    sleep "${MUKIT_TEST_CURL_DELAY:-0}"
    head -c 100 /dev/zero >> "$out"; n=$((n + 100))
done
exit 0
EOS
chmod 755 "$CURLBIN/curl"
CREC="$TMPD/curlrec"; mkdir -p "$CREC"; export MUKIT_TEST_REC="$CREC"
P=$(PATH="$CURLBIN:$PATH" MUKIT_PROGRESS=lines MUKIT_TEST_CURL_DELAY=0.3 mukit_download https://example.invalid/big.exe "$TMPD/big.exe.part" -C -); rc=$?
eq 'progress download exit 0' "$rc" 0
eq 'progress download size' "$(mukit_file_size "$TMPD/big.exe.part")" 1000
case "$P" in *'MU-PROGRESS '*' 1000 big.exe'*) ok 'MU-PROGRESS lines with the Content-Length total' ;; *) bad "MU-PROGRESS lines: $P" ;; esac
eq 'last progress line is complete' "$(printf '%s\n' "$P" | tail -1)" 'MU-PROGRESS 1000 1000 big.exe'
P=$(PATH="$CURLBIN:$PATH" mukit_download https://example.invalid/big.exe "$TMPD/big2.part" 2>&1)
case "$P" in *MU-PROGRESS*) bad 'default progress keeps curl bar (no MU-PROGRESS lines)' ;; *) ok 'default progress keeps curl bar (no MU-PROGRESS lines)' ;; esac

echo '# cancel: SIGTERM during the game download, stale locks, --stop'
# A copy of the free home above with the game removed, so the official-installer path runs (download, then the
# synthetic wine "installer"). The prefix's wineserver stub records the -k calls.
FH6="$TMPD/freehome6"; cp -R "$FH2" "$FH6"; FP6="$FH6/prefix"; rm -rf "$FP6/drive_c/MuTheMatrix"
RT6="$FH6/runtime/$RTID"; : > "$FREC/wineserver.calls"
CSETUP=(env MUKIT_FREE_HOME="$FH6" PATH="$CURLBIN:$PATH" MUKIT_PROGRESS=lines "$KIT_DIR/setup-mu-mac.sh" --runtime-archive "$TMPD/runtime.tar.xz"
        --game-installer https://example.invalid/MuTheMatrix-test.exe --mugl-dll "$DLLS/mugl-v75.dll" --mscoree-dll "$DLLS/mscoree.dll"
        --modes '960x600 1024x640 1280x800 1600x1000 1728x1080' --no-desktop --skip-verify)
LOCK6="$FH6/.prefix.mukit-lock"; PART6="$FH6/downloads/MuTheMatrix-test.exe.part"
MUKIT_TEST_CURL_DELAY=0.5 "${CSETUP[@]}" > "$TMPD/cancel1.log" 2>&1 & SP=$!
t=0; while [ "$(mukit_file_size "$PART6" 2>/dev/null || echo 0)" -lt 200 ] && [ "$t" -lt 100 ]; do sleep 0.1; t=$((t + 1)); done
yes 'setup holds the lock while it runs' test -f "$LOCK6/owner"
eq 'lock records the setup pid' "$(mukit_lock_get "$LOCK6" pid)" "$SP"
eq 'lock records the prefix wineserver' "$(mukit_lock_get "$LOCK6" wineserver)" "$RT6/wine/bin/wineserver"
yes 'lock owner is alive' mukit_lock_alive "$LOCK6"
CPID=$(cat "$CREC/curl.pid" 2>/dev/null)
kill -TERM "$SP"; wait "$SP"; rc=$?
eq 'SIGTERM: setup exits 143' "$rc" 143
grep -q 'Stopped: the installation was cancelled' "$TMPD/cancel1.log" && ok 'SIGTERM: setup says it was cancelled' || bad 'SIGTERM: setup says it was cancelled'
no 'SIGTERM: lock removed' test -e "$LOCK6"
sleep 0.3
no 'SIGTERM: the download (curl) was stopped' kill -0 "$CPID" 2>/dev/null
yes 'SIGTERM: the partial download is kept' test -s "$PART6"
grep -q "^$FP6|-k\$" "$FREC/wineserver.calls" && ok "SIGTERM: this prefix's wineserver stopped (-k)" || bad "SIGTERM: this prefix's wineserver stopped (-k): $(cat "$FREC/wineserver.calls")"
eq 'SIGTERM: no other prefix touched' "$(grep -cv "^$FP6|" "$FREC/wineserver.calls")" 0
grep -q 'MU-PROGRESS [0-9]* 1000 MuTheMatrix-test.exe' "$TMPD/cancel1.log" && ok 'game download reports MU-PROGRESS' || bad 'game download reports MU-PROGRESS'
# a stale lock (its setup was killed) is taken over; a live one is refused
mkdir -p "$LOCK6"; printf 'pid=999999\npgid=999999\nprefix=%s\n' "$FP6" > "$LOCK6/owner"
no 'stale lock owner is not alive' mukit_lock_alive "$LOCK6"
bash -c 'exec -a setup-mu-mac.sh sleep 30' & LIVE=$!
sleep 0.2
printf 'pid=%s\n' "$LIVE" > "$TMPD/live-owner"; mkdir -p "$TMPD/livelock"; cp "$TMPD/live-owner" "$TMPD/livelock/owner"
yes 'a running setup holds a live lock' mukit_lock_alive "$TMPD/livelock"
mv "$LOCK6/owner" "$TMPD/stale-owner"; cp "$TMPD/live-owner" "$LOCK6/owner"
"${CSETUP[@]}" > "$TMPD/cancel-live.log" 2>&1; rc=$?
[ "$rc" != 0 ] && grep -q 'Another installation is still running (process' "$TMPD/cancel-live.log" && ok 'live lock refused' || bad "live lock refused: $(tail -2 "$TMPD/cancel-live.log")"
kill "$LIVE" 2>/dev/null; wait "$LIVE" 2>/dev/null
mv "$TMPD/stale-owner" "$LOCK6/owner"
: > "$CREC/curl.calls"
MUKIT_TEST_CURL_DELAY=0 "${CSETUP[@]}" > "$TMPD/cancel2.log" 2>&1; rc=$?
eq 'Try Again after a cancel: exit 0' "$rc" 0
grep -q 'taking over the setup lock of an installation that was stopped' "$TMPD/cancel2.log" && ok 'stale lock taken over' || bad 'stale lock taken over'
grep -q -- '-C -' "$CREC/curl.calls" && ok 'the download resumes (curl -C -)' || bad 'the download resumes (curl -C -)'
yes 'game installed after the resumed download' test -f "$FP6/drive_c/MuTheMatrix/main.exe"
no 'lock released after a normal run' test -e "$LOCK6"
no 'downloaded installer removed' test -e "$FH6/downloads/MuTheMatrix-test.exe"
# --stop: kills what is left of a stopped setup's process group (only processes naming this install), stops this
# prefix's wineserver and removes the lock; a lock without an owner file (older kit) is never taken over.
: > "$FREC/wineserver.calls"
if command -v perl >/dev/null 2>&1; then
    # A stand-in for the stopped setup's group: a leader whose command line names this install, and a member that does not.
    LEFT=$(perl -e 'setpgrp(0, 0); if (fork) { sleep 3000 } else { exec "sleep", "3001" }' "$FH6/downloads/leftover.part" > /dev/null 2>&1 & echo $!)
    sleep 0.5
    OTHER=$(ps -A -o pid=,pgid=,command= | awk -v g="$LEFT" '$2 == g && / 3001$/ { print $1 }')
    yes 'leftover group has a member without the install path' test -n "$OTHER"
    mkdir -p "$LOCK6"; printf 'pid=999999\npgid=%s\nprefix=%s\nwineserver=%s\n' "$LEFT" "$FP6" "$RT6/wine/bin/wineserver" > "$LOCK6/owner"
    env MUKIT_FREE_HOME="$FH6" "$KIT_DIR/setup-mu-mac.sh" --runtime free --stop > "$TMPD/stop.log" 2>&1; rc=$?
    eq '--stop exit 0' "$rc" 0
    sleep 0.2
    no '--stop killed the leftover download of that setup' kill -0 "$LEFT" 2>/dev/null
    yes '--stop left a process that does not name this install alone' kill -0 "$OTHER"
    grep -q 'stopped 1 leftover process' "$TMPD/stop.log" && ok '--stop reports the leftover it stopped' || bad "--stop reports the leftover it stopped: $(cat "$TMPD/stop.log")"
    kill "$OTHER" 2>/dev/null
    no '--stop removed the lock' test -e "$LOCK6"
    eq "--stop: only this prefix's wineserver -k" "$(cat "$FREC/wineserver.calls")" "$FP6|-k"
    grep -q 'Stopped. Run the setup again' "$TMPD/stop.log" && ok '--stop says what to do next' || bad '--stop says what to do next'
else
    echo 'skip  --stop leftover processes (no perl for setpgrp)'
fi
env MUKIT_FREE_HOME="$FH6" "$KIT_DIR/setup-mu-mac.sh" --runtime free --stop > /dev/null 2>&1; rc=$?
eq '--stop without a lock exit 0' "$rc" 0
mkdir -p "$LOCK6"
"${CSETUP[@]}" > "$TMPD/oldlock.log" 2>&1 && bad 'a lock without owner file is refused' || { grep -q 'left by an older version' "$TMPD/oldlock.log" && ok 'a lock without owner file is refused' || bad 'old lock message'; }
rmdir "$LOCK6"
# leftovers of a stopped run are cleaned up: an incomplete game copy, a half-unpacked runtime, an unfinished prefix
mkdir -p "$FP6/drive_c/MuTheMatrix.mukit-partial" "$FH6/runtime/$RTID.partial.engine"; : > "$FP6/.mukit/prefix.incomplete"
rm -rf "$FP6/drive_c/MuTheMatrix"
"${FSETUP[@]/$FH2/$FH6}" > "$TMPD/leftovers.log" 2>&1; rc=$?
eq 'run after leftovers: exit 0' "$rc" 0
grep -q 'removing the incomplete copy of a stopped installation' "$TMPD/leftovers.log" && ok 'incomplete game copy replaced' || bad 'incomplete game copy replaced'
yes 'game copied after removing the partial copy' test -f "$FP6/drive_c/MuTheMatrix/main.exe"
grep -q 'the prefix was being created when an installation stopped' "$TMPD/leftovers.log" && ok 'unfinished prefix step is redone' || bad 'unfinished prefix step is redone'
no 'prefix marker removed once the step finished' test -e "$FP6/.mukit/prefix.incomplete"
unset MUKIT_TEST_REC
unset MUKIT_WINETRICKS_SHA256

printf '\n%d passed, %d failed\n' "$NPASS" "$NFAIL"
[ "$NFAIL" = 0 ]
