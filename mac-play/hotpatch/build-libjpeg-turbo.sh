#!/bin/sh
# build-libjpeg-turbo.sh <work-dir>: fetch libjpeg-turbo 3.1.2 (SHA-256 pinned), apply the two mugl changes and
# cross-build a static i686 MinGW libjpeg.a for mugl's native JPEG decode (v7.6, MAC-PERF-010). Prints the LJT_DIR
# to pass to make. Needs curl, cmake, nasm and i686-w64-mingw32-gcc. Nothing is installed.
#   1. src/jdsample.c: no h1v2 fancy upsampling (IJG 6b, which the client links, upsamples h1v2 by replication).
#   2. simd/i386/jsimd.c: SSE2 is the only SIMD level used (AVX2 measured slower under Rosetta; same output).
#   jconfigint.h: THREAD_LOCAL empty (no emulated TLS in the DLL; the cached SIMD flag is the only user).
set -eu
W=${1:?work dir}
URL=https://github.com/libjpeg-turbo/libjpeg-turbo/releases/download/3.1.2/libjpeg-turbo-3.1.2.tar.gz
SHA=8f0012234b464ce50890c490f18194f913a7b1f4e6a03d6644179fa0f867d0cf
mkdir -p "$W/src" "$W/build"
T="$W/libjpeg-turbo-3.1.2.tar.gz"
[ -f "$T" ] || curl -fsSL -o "$T" "$URL"
echo "$SHA  $T" | shasum -a 256 -c - >/dev/null
rm -rf "$W/src/libjpeg-turbo-3.1.2"; tar xzf "$T" -C "$W/src"
S="$W/src/libjpeg-turbo-3.1.2"
perl -0pi -e 's/(v_in_group \* 2 == v_out_group && do_fancy)\) \{/$1 && 0) { \/* mugl: IJG 6b has no h1v2 fancy upsampling *\//' "$S/src/jdsample.c"
perl -0pi -e 's/simd_support = jpeg_simd_cpu_support\(\);/simd_support = jpeg_simd_cpu_support() & JSIMD_SSE2; \/* mugl: SSE2 only *\//' "$S/simd/i386/jsimd.c"
grep -q 'mugl: IJG 6b' "$S/src/jdsample.c" && grep -q 'mugl: SSE2 only' "$S/simd/i386/jsimd.c"
cat > "$W/build/tc.cmake" <<'EOF'
set(CMAKE_SYSTEM_NAME Windows)
set(CMAKE_SYSTEM_PROCESSOR i686)
set(CMAKE_C_COMPILER i686-w64-mingw32-gcc)
set(CMAKE_RC_COMPILER i686-w64-mingw32-windres)
EOF
cmake -S "$S" -B "$W/build" -DCMAKE_TOOLCHAIN_FILE="$W/build/tc.cmake" -DCMAKE_INSTALL_PREFIX="$W/inst" \
  -DCMAKE_ASM_NASM_COMPILER="$(command -v nasm)" -DENABLE_SHARED=0 -DWITH_TURBOJPEG=0 -DWITH_TOOLS=0 -DWITH_TESTS=0 \
  -DCMAKE_BUILD_TYPE=Release -DCMAKE_C_FLAGS="-msse2 -mfpmath=sse -ffp-contract=off" >/dev/null
perl -pi -e 's/^#define THREAD_LOCAL .*/#define THREAD_LOCAL \/* mugl: none *\//' "$W/build/jconfigint.h"
make -C "$W/build" -j8 jpeg-static >/dev/null
cp "$S/src/jpeglib.h" "$S/src/jmorecfg.h" "$S/src/jerror.h" "$W/build/"
echo "LJT_DIR=$W/build"
