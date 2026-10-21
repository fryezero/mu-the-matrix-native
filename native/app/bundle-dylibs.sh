#!/bin/sh
# NATIVE-APP-001: make the preview app self-contained. Copies every non-system dylib that the bundle's
# Mach-O files load (Homebrew's Crypto++, libjpeg, SDL2) into Contents/Frameworks, points the load
# commands at @rpath, adds the rpaths and, for sdl2-compat (which dlopens SDL3 from @loader_path at run
# time), copies SDL3 next to it. Usage: bundle-dylibs.sh APP [SDL3_DYLIB]
set -eu
APP=$1
SDL3=${2:-}
FW="$APP/Contents/Frameworks"
mkdir -p "$FW"

is_system() {
    case "$1" in /System/*|/usr/lib/*|@*) return 0 ;; *) return 1 ;; esac
}

deps() {   # non-system load commands of a Mach-O file
    otool -L "$1" | tail -n +2 | awk '{print $1}' | while read -r d; do is_system "$d" || echo "$d"; done
}

# Mach-O files to process, with the rpath that reaches Contents/Frameworks from each.
todo=$(mktemp)
trap 'rm -f "$todo"' EXIT
for f in "$APP"/Contents/MacOS/*; do
    file "$f" | grep -q Mach-O && echo "$f|@executable_path/../Frameworks" >> "$todo"
done
for f in "$APP"/Contents/Resources/converter/model-recovery/*.dylib; do
    [ -f "$f" ] && echo "$f|@loader_path/../../../Frameworks" >> "$todo"
done
for f in "$FW"/*.dylib; do
    [ -f "$f" ] && echo "$f|@loader_path" >> "$todo"
done

processed=""
while [ -s "$todo" ]; do
    line=$(head -1 "$todo"); sed -i '' 1d "$todo"
    f=${line%%|*}; rp=${line#*|}
    case " $processed " in *" $f "*) continue ;; esac
    processed="$processed $f"
    chmod u+w "$f"
    for d in $(deps "$f"); do
        name=$(basename "$d")
        if [ "$d" = "$(otool -D "$f" | tail -n +2 | head -1)" ]; then
            install_name_tool -id "@rpath/$name" "$f" 2>/dev/null
            continue
        fi
        if [ ! -f "$FW/$name" ]; then
            src=$d
            [ -f "$src" ] || { echo "bundle-dylibs: $f needs $d, which does not exist" >&2; exit 1; }
            cp -L "$src" "$FW/$name"
            chmod u+w "$FW/$name"
            echo "$FW/$name|@loader_path" >> "$todo"
            echo "bundled $name (from $d)"
        fi
        install_name_tool -change "$d" "@rpath/$name" "$f" 2>/dev/null
    done
    case "$f" in *.dylib) install_name_tool -id "@rpath/$(basename "$f")" "$f" 2>/dev/null ;; esac
    otool -l "$f" | grep -A2 LC_RPATH | grep -q " $rp " || install_name_tool -add_rpath "$rp" "$f" 2>/dev/null
done

# sdl2-compat loads SDL3 at run time from @loader_path/libSDL3.dylib (among others).
if [ -f "$FW/libSDL2-2.0.0.dylib" ] && strings "$FW/libSDL2-2.0.0.dylib" | grep -q '@loader_path/libSDL3.dylib'; then
    [ -n "$SDL3" ] && [ -f "$SDL3" ] || { echo "bundle-dylibs: libSDL2 is sdl2-compat; pass SDL3_LIB" >&2; exit 1; }
    cp -L "$SDL3" "$FW/libSDL3.dylib"
    chmod u+w "$FW/libSDL3.dylib"
    install_name_tool -id "@rpath/libSDL3.dylib" "$FW/libSDL3.dylib" 2>/dev/null
    for d in $(deps "$FW/libSDL3.dylib"); do
        echo "bundle-dylibs: SDL3 needs $d (not handled)" >&2; exit 1
    done
    echo "bundled libSDL3.dylib (sdl2-compat's run-time SDL3, from $SDL3)"
fi

# No Mach-O in the bundle may still name a library outside the system and the bundle.
bad=0
for f in "$APP"/Contents/MacOS/* "$FW"/*.dylib "$APP"/Contents/Resources/converter/model-recovery/*.dylib; do
    [ -f "$f" ] || continue
    file "$f" | grep -q Mach-O || continue
    for d in $(deps "$f"); do echo "bundle-dylibs: $f still loads $d" >&2; bad=1; done
done
exit $bad
