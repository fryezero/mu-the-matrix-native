#!/bin/bash
# build-wine.sh - build the free Wine runtime archive for the Mu The Matrix installer (MAC-FREE-001).
#
# Builds CodeWeavers' open-source Wine from the published CrossOver 26.3.0 sources (LGPL-2.1+) as an x86_64
# wow64 runtime on an Apple Silicon Mac, adds the x86_64 libraries it loads (freetype, gnutls, ... from
# Sikarugir's wrapper template) and the wine-gecko 2.47.4 x86 package, and writes
#   OUT/winecx-26.3.0-mu1.tar.xz  (+ .sha256)
# with the layout setup-mu-mac.sh --runtime-archive expects: wine/{bin,lib,share} + dylibs, .mu-runtime.
# This is the same Wine version as CrossOver 26.3 and runs the game at CrossOver speed (see
# docs/research/mac-free-runtime.md). CrossOver's proprietary parts (GUI, cxbottle, D3DMetal) are not in the
# source tarball and not needed.
#
# Usage: build-wine.sh [WORK_DIR] [OUT_DIR]     (defaults: ./build/wine-work and ./build)
# Needs: Xcode Command Line Tools, Rosetta 2, Homebrew bison and mingw-w64 (brew install bison mingw-w64),
#        ~6 GB of disk, about 25 minutes on an M5 (most of it the i386 + x86_64 PE builds).
# The work directory must not contain spaces (Wine's build system does not support them).
set -euo pipefail
HERE=$(cd -- "$(dirname -- "$0")" && pwd -P)
WORK=${1:-$HERE/build/wine-work}
OUT=${2:-$HERE/build}
case "$WORK$OUT" in *' '*) echo "build-wine.sh: paths must not contain spaces: $WORK $OUT" >&2; exit 1 ;; esac
ID=cx26.3.0-mu1
CX_SRC_URL=https://media.codeweavers.com/pub/crossover/source/crossover-sources-26.3.0.tar.gz
CX_SRC_SHA256=ac99c8ca4b3848f3e81784135f023df266b61c2345726ea55a50b3e030dd6872
GECKO_URL=https://dl.winehq.org/wine/wine-gecko/2.47.4/wine-gecko-2.47.4-x86.tar.xz
GECKO_SHA256=2cfc8d5c948602e21eff8a78613e1826f2d033df9672cace87fed56e8310afb6
LIBS_URL=https://github.com/Sikarugir-App/Template/releases/download/v1.0/Template-1.0.24.tar.xz
LIBS_SHA256=4b5f89eeb9ef139936bdfad33d9b420b05ea4597cb7d63376674f7a8e171321c
HB=$(brew --prefix 2>/dev/null || echo /opt/homebrew)
export PATH="$HB/opt/bison/bin:$HB/bin:/usr/bin:/bin:/usr/sbin:/sbin"

[ "$(uname -m)" = arm64 ] || echo "build-wine.sh: only tested on Apple Silicon" >&2
/usr/bin/arch -x86_64 /usr/bin/true || { echo "Rosetta 2 is required (softwareupdate --install-rosetta)" >&2; exit 1; }
bison --version | head -1 | grep -q ' 3\.' || { echo "Homebrew bison 3.x is required (brew install bison)" >&2; exit 1; }
command -v i686-w64-mingw32-gcc >/dev/null && command -v x86_64-w64-mingw32-gcc >/dev/null ||
    { echo "MinGW-w64 is required (brew install mingw-w64)" >&2; exit 1; }
[ -f "$HB/include/freetype2/ft2build.h" ] && [ -f "$HB/include/gnutls/gnutls.h" ] ||
    { echo "freetype and gnutls headers are required (brew install freetype gnutls)" >&2; exit 1; }

fetch() {   # fetch URL SHA256 FILE
    [ -f "$3" ] && [ "$(shasum -a 256 "$3" | awk '{print $1}')" = "$2" ] && return 0
    curl -fL --retry 3 -o "$3.part" "$1"
    [ "$(shasum -a 256 "$3.part" | awk '{print $1}')" = "$2" ] || { echo "SHA-256 mismatch for $1" >&2; exit 1; }
    mv "$3.part" "$3"
}
mkdir -p "$WORK/dl" "$OUT"
fetch "$CX_SRC_URL" "$CX_SRC_SHA256" "$WORK/dl/crossover-sources-26.3.0.tar.gz"
fetch "$GECKO_URL" "$GECKO_SHA256" "$WORK/dl/wine-gecko-2.47.4-x86.tar.xz"
fetch "$LIBS_URL" "$LIBS_SHA256" "$WORK/dl/Template-1.0.24.tar.xz"

SRC="$WORK/src/sources/wine"
[ -f "$SRC/configure" ] || { mkdir -p "$WORK/src"; tar xzf "$WORK/dl/crossover-sources-26.3.0.tar.gz" -C "$WORK/src" sources/wine; }
LIBS="$WORK/x86libs"
if [ ! -f "$LIBS/libfreetype.6.dylib" ]; then
    rm -rf "$WORK/tpl"; mkdir -p "$WORK/tpl" "$LIBS"
    tar xf "$WORK/dl/Template-1.0.24.tar.xz" -C "$WORK/tpl"
    cp -a "$WORK"/tpl/*/Contents/Frameworks/*.dylib "$LIBS/"
    rm -rf "$WORK/tpl"
fi

BUILD="$WORK/build"; INST="$WORK/install"
mkdir -p "$BUILD" "$INST"
cd "$BUILD"
if [ ! -f Makefile ]; then
    # enable_*: CrossOver runs 32-bit prefixes in wow64 mode, which needs the i386 builds of these programs
    # (upstream configure builds them for the host architecture only).
    /usr/bin/arch -x86_64 /bin/bash -c "
      export PATH='$PATH'
      CC='clang -arch x86_64' CXX='clang++ -arch x86_64' CFLAGS='-O2 -g0' CROSSCFLAGS='-O2 -g0' \
      LDFLAGS='-Wl,-rpath,@loader_path/../../ -Wl,-rpath,@loader_path/../../../ -Wl,-headerpad_max_install_names' \
      FREETYPE_CFLAGS='-I$HB/include/freetype2' FREETYPE_LIBS='-L$LIBS -lfreetype' \
      GNUTLS_CFLAGS='-I$HB/include -I$HB/opt/nettle/include -I$HB/opt/p11-kit/include/p11-kit-1' GNUTLS_LIBS='-L$LIBS -lgnutls' \
      PKG_CONFIG_LIBDIR=/nonexistent \
      enable_conhost=yes enable_plugplay=yes enable_rpcss=yes enable_services=yes enable_spoolsv=yes \
      enable_termsv=yes enable_wineboot=yes enable_winemenubuilder=yes enable_wuauserv=yes \
      '$SRC/configure' --prefix='$INST' \
        --enable-archs=i386,x86_64 --enable-win64 --disable-tests --disable-winebth_sys \
        --without-alsa --without-capi --with-coreaudio --without-cups --without-dbus --without-ffmpeg \
        --without-fontconfig --with-freetype --without-gettext --without-gettextpo --without-gphoto \
        --with-gnutls --without-gssapi --without-gstreamer --without-krb5 \
        --with-mingw --without-netapi --without-opencl --without-oss --without-pcap \
        --without-pcsclite --with-pthread --without-pulse --without-sane --without-sdl --without-udev \
        --without-usb --without-v4l2 --without-vulkan --without-wayland --without-x --without-inotify"
fi
# configure reads library sonames from otool output, which newer otool formats differently: pin them.
sed -i '' -e 's|^#define SONAME_LIBFREETYPE .*|#define SONAME_LIBFREETYPE "libfreetype.6.dylib"|' \
          -e 's|^#define SONAME_LIBGNUTLS .*|#define SONAME_LIBGNUTLS "libgnutls.30.dylib"|' include/config.h
grep -q '^#define SONAME_LIBVULKAN' include/config.h || echo '#define SONAME_LIBVULKAN "libvulkan.1.dylib"' >> include/config.h
# Build tools (sfnt2fon) link freetype by its leaf name and find it, and its dependencies, through
# @loader_path/../../ = this directory.
for l in "$LIBS"/*.dylib; do ln -sf "$l" .; done
/usr/bin/arch -x86_64 /bin/bash -c "export PATH='$PATH'; make -j$(sysctl -n hw.ncpu) && make install"

# ---------------------------------------------------------------- package
R="$WORK/pkg/$ID"; rm -rf "$WORK/pkg"; mkdir -p "$R/wine/bin"
cp -a "$INST/bin/wine" "$INST/bin/wineserver" "$R/wine/bin/"
cp -a "$INST/lib" "$INST/share" "$R/wine/"
find "$R/wine/lib/wine" -name '*.a' -delete
rm -rf "$R/wine/share/man" "$R/wine/share/applications" "$R/wine/lib/pkgconfig"
cp -a "$LIBS"/*.dylib "$R/"
(cd "$R/wine/lib" && for f in ../../*.dylib; do ln -sf "$f" .; done)
for f in "$R/wine/bin/wineserver" "$R/wine/lib/wine/x86_64-unix/winebus.so"; do
    if otool -L "$f" | grep -q '^[[:space:]]*libinotify.dylib'; then
        install_name_tool -change libinotify.dylib @rpath/libinotify.0.dylib "$f" 2>/dev/null
        codesign -f -s - "$f" 2>/dev/null
    fi
done
mkdir -p "$R/wine/share/wine/gecko"
tar xf "$WORK/dl/wine-gecko-2.47.4-x86.tar.xz" -C "$R/wine/share/wine/gecko"
cat > "$R/.mu-runtime" <<EOF
id=$ID
source=$CX_SRC_URL (sha256 $CX_SRC_SHA256), built by mac-play/installer/runtime/build-wine.sh
EOF
cat > "$R/SOURCES.txt" <<EOF
This runtime is free software. Corresponding sources:
- Wine (LGPL-2.1-or-later): CodeWeavers CrossOver 26.3.0 sources, $CX_SRC_URL
  sha256 $CX_SRC_SHA256; built unmodified with mac-play/installer/runtime/build-wine.sh (configure options there).
- wine-gecko 2.47.4 (MPL-2.0): $GECKO_URL
- x86_64 libraries (freetype FTL/GPL-2.0, gnutls LGPL-2.1+, nettle/gmp LGPL-3.0+, libpng, zlib, ... each under its
  own license) from Sikarugir's wrapper template $LIBS_URL; sources: https://github.com/Sikarugir-App/Sikarugir-foss-sources
EOF
cp "$SRC/COPYING.LIB" "$R/COPYING.LIB"
tar -cJf "$OUT/winecx-26.3.0-mu1.tar.xz" -C "$R" .
(cd "$OUT" && shasum -a 256 winecx-26.3.0-mu1.tar.xz | tee winecx-26.3.0-mu1.tar.xz.sha256)
echo "Runtime archive: $OUT/winecx-26.3.0-mu1.tar.xz"
echo "Install with: setup-mu-mac.sh --runtime-archive $OUT/winecx-26.3.0-mu1.tar.xz"
