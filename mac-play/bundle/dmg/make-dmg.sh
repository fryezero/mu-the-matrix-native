#!/bin/bash
# make-dmg.sh (MAC-DMG-001): package Mu The Matrix.app as the disk image players download.
# Only tools that come with macOS and the Command Line Tools (hdiutil, ditto, swiftc, tiffutil, codesign, xcrun).
#
# Usage: make-dmg.sh --app "PATH/Mu The Matrix.app" --out "PATH/Mu The Matrix.dmg" [options]
#   --sign ID             sign with this identity before packaging ("Developer ID Application: NAME (TEAMID)"):
#                         hardened runtime, dmg/app.entitlements for the app, dmg/helpers.entitlements for the fast
#                         x87 helpers, secure timestamp; the disk image is signed too. "-" = ad-hoc with the
#                         hardened runtime (tests the entitlements locally; Gatekeeper still asks).
#                         Default: keep the app's ad-hoc signature (players confirm the app once in System Settings).
#   --notary-profile P    with --sign: notarize with "xcrun notarytool submit --keychain-profile P --wait" (create
#                         the profile once with "xcrun notarytool store-credentials P"), first the app (stapled
#                         before packaging), then the disk image (stapled). Notarization removes Gatekeeper's
#                         "Open Anyway" step for players.
#   --format F            hdiutil format: ULFO (default, LZFSE, macOS 10.11+) or UDZO (zlib) or ULMO (LZMA)
#   --volume-name NAME    default "Mu The Matrix"
#   --no-layout           no Finder window layout (.DS_Store); tests
#   --dry-run             print the plan, change nothing
#   --keep-work           keep the work folder (for inspection)
#
# The disk image holds the app, a link to /Applications and a window ("Drag Mu The Matrix to Applications") whose
# background is drawn at build time by dmg-tool.swift (no artwork is committed); the app icon is the volume icon.
set -euo pipefail
HERE=$(cd -- "$(dirname -- "$0")" && pwd -P)
APP= OUT= SIGN= NOTARY= FORMAT=ULFO VOLNAME="Mu The Matrix" LAYOUT=1 DRY=0 KEEP=0
die() { echo "make-dmg: $*" >&2; exit 1; }
need() { [ "$2" -ge 2 ] || die "$1 needs a value"; }
while [ "$#" -gt 0 ]; do
    case "$1" in
        --app) need "$1" "$#"; APP=$2; shift 2 ;;
        --out) need "$1" "$#"; OUT=$2; shift 2 ;;
        --sign) need "$1" "$#"; SIGN=$2; shift 2 ;;
        --notary-profile) need "$1" "$#"; NOTARY=$2; shift 2 ;;
        --format) need "$1" "$#"; FORMAT=$2; shift 2 ;;
        --volume-name) need "$1" "$#"; VOLNAME=$2; shift 2 ;;
        --no-layout) LAYOUT=0; shift ;;
        --dry-run) DRY=1; shift ;;
        --keep-work) KEEP=1; shift ;;
        -h|--help) sed -n '2,/^set -euo/p' "$0" | sed '$d; s/^# \{0,1\}//'; exit 0 ;;
        *) die "unknown option $1 (see --help)" ;;
    esac
done
[ -n "$APP" ] && [ -n "$OUT" ] || die "--app and --out are required (see --help)"
[ -d "$APP/Contents/MacOS" ] || die "not an app bundle: $APP"
case "$FORMAT" in ULFO|UDZO|ULMO|UDBZ) ;; *) die "--format must be ULFO, UDZO or ULMO" ;; esac
[ -z "$NOTARY" ] || [ -n "$SIGN" ] || die "--notary-profile needs --sign (a Developer ID Application identity)"
[ -z "$NOTARY" ] || [ "$SIGN" != - ] || die "notarization needs a Developer ID identity, not ad-hoc (-)"
[ "$(uname -s)" = Darwin ] || die "macOS only"
APPNAME=$(basename "$APP")
case "$OUT" in /*) ;; *) OUT="$PWD/$OUT" ;; esac

plan() { echo "plan: $*"; }
if [ "$DRY" = 1 ]; then
    plan "stage $APPNAME + Applications link$([ "$LAYOUT" = 1 ] && echo ' + .background/background.tiff (dmg-tool background 1x/2x) + .VolumeIcon.icns')"
    if [ -n "$SIGN" ]; then
        plan "codesign --options runtime --timestamp --entitlements helpers.entitlements: Resources/fast-x87 executables and libraries"
        plan "codesign --options runtime --timestamp --entitlements app.entitlements --sign '$SIGN' $APPNAME"
        [ -z "$NOTARY" ] || plan "notarytool submit (zip of the app) --keychain-profile '$NOTARY' --wait; stapler staple $APPNAME"
    else plan "keep the app's signature ($(codesign -dv "$APP" 2>&1 | sed -n 's/^Signature=//p' || echo unsigned))"; fi
    plan "hdiutil create UDRW (HFS+, volume '$VOLNAME'), attach, $([ "$LAYOUT" = 1 ] && echo 'write .DS_Store (dmg-tool dsstore), volume icon, ')detach"
    plan "hdiutil convert -format $FORMAT -> $OUT"
    if [ -n "$SIGN" ]; then plan "codesign --timestamp --sign '$SIGN' the disk image"; [ -z "$NOTARY" ] || plan "notarytool submit the disk image --wait; stapler staple; spctl --assess"; fi
    echo "dry run: nothing was changed"
    exit 0
fi

WORK=$(mktemp -d "${TMPDIR:-/tmp}/mu-dmg.XXXXXX")
MNT=
cleanup() {
    [ -z "$MNT" ] || hdiutil detach -quiet "$MNT" 2>/dev/null || hdiutil detach -quiet -force "$MNT" 2>/dev/null || true
    [ "$KEEP" = 1 ] && echo "work folder kept: $WORK" || rm -rf "$WORK"
}
trap cleanup EXIT
STAGE="$WORK/stage"; mkdir -p "$STAGE"
echo "== stage"
ditto "$APP" "$STAGE/$APPNAME"
ln -s /Applications "$STAGE/Applications"
if [ "$LAYOUT" = 1 ]; then
    xcrun swiftc -O -o "$WORK/dmg-tool" "$HERE/dmg-tool.swift"
    mkdir -p "$STAGE/.background"
    "$WORK/dmg-tool" background "$WORK/bg.png" 1
    "$WORK/dmg-tool" background "$WORK/bg@2x.png" 2
    tiffutil -cathidpicheck "$WORK/bg.png" "$WORK/bg@2x.png" -out "$STAGE/.background/background.tiff" >/dev/null 2>&1
    [ ! -f "$APP/Contents/Resources/AppIcon.icns" ] || cp "$APP/Contents/Resources/AppIcon.icns" "$STAGE/.VolumeIcon.icns"
fi

if [ -n "$SIGN" ]; then
    echo "== sign ($SIGN)"
    S="$STAGE/$APPNAME"
    TS=--timestamp; [ "$SIGN" = - ] && TS=--timestamp=none
    # Inside out: the Mach-O helpers in Resources first, then the app (its seal covers them).
    find "$S/Contents/Resources" -type f | while IFS= read -r f; do
        file -b "$f" | grep -q '^Mach-O' || continue
        codesign --force $TS --options runtime --entitlements "$HERE/helpers.entitlements" --sign "$SIGN" "$f"
        echo "signed ${f#$S/}"
    done
    codesign --force $TS --options runtime --entitlements "$HERE/app.entitlements" --sign "$SIGN" "$S"
    codesign --verify --strict --deep --verbose=1 "$S"
    if [ -n "$NOTARY" ]; then
        echo "== notarize the app"
        ditto -c -k --keepParent "$S" "$WORK/app.zip"
        xcrun notarytool submit "$WORK/app.zip" --keychain-profile "$NOTARY" --wait
        xcrun stapler staple "$S"
        spctl --assess --type execute --verbose=2 "$S"
    fi
fi

echo "== disk image"
SIZE_MB=$(( $(du -sk "$STAGE" | awk '{print $1}') / 1024 + 40 ))
hdiutil create -quiet -srcfolder "$STAGE" -volname "$VOLNAME" -fs HFS+ -format UDRW -size "${SIZE_MB}m" "$WORK/rw.dmg"
if [ "$LAYOUT" = 1 ]; then
    mkdir -p "$WORK/mnt"
    hdiutil attach -quiet -readwrite -noverify -noautoopen -nobrowse -mountpoint "$WORK/mnt" "$WORK/rw.dmg"
    MNT="$WORK/mnt"
    "$WORK/dmg-tool" dsstore "$MNT" .background/background.tiff "$APPNAME"
    # The volume uses .VolumeIcon.icns: FinderInfo "has custom icon" (0x0400) on the volume's root folder.
    [ ! -f "$MNT/.VolumeIcon.icns" ] || xattr -wx com.apple.FinderInfo \
        0000000000000000040000000000000000000000000000000000000000000000 "$MNT"
    rm -rf "$MNT/.fseventsd" "$MNT/.Trashes" 2>/dev/null || true
    sync
    hdiutil detach -quiet "$MNT" || hdiutil detach -quiet -force "$MNT"
    MNT=
fi
mkdir -p "$(dirname "$OUT")"
rm -f "$OUT"
hdiutil convert -quiet "$WORK/rw.dmg" -format "$FORMAT" -o "$OUT"

if [ -n "$SIGN" ]; then
    echo "== sign the disk image"
    TS=--timestamp; [ "$SIGN" = - ] && TS=--timestamp=none
    codesign --force $TS --sign "$SIGN" "$OUT"
    if [ -n "$NOTARY" ]; then
        echo "== notarize the disk image"
        xcrun notarytool submit "$OUT" --keychain-profile "$NOTARY" --wait
        xcrun stapler staple "$OUT"
        spctl --assess --type open --context context:primary-signature --verbose=2 "$OUT"
    fi
fi
hdiutil verify -quiet "$OUT"
echo "disk image: $OUT"
echo "size: $(du -h "$OUT" | awk '{print $1}')  sha256: $(shasum -a 256 "$OUT" | awk '{print $1}')"
