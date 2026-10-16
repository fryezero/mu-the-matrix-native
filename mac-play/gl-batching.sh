#!/bin/bash
# SPDX-License-Identifier: MIT
# Sourced by setup. Every operation is confined to its setup-owned idle bottle.
install_gl_batching() {
    local enabled=${MU_GL_BATCHING:-1} dll="$GAME/opengl32.dll"
    local builtin="$PREFIX/drive_c/windows/system32/opengl32.dll"
    local recorded="$STATE/mugl.sha256" artifact="$SCRIPT_DIR/mugl/build/opengl32.dll"
    local key='HKCU\Software\Wine\AppDefaults\main.exe\DllOverrides' old= actual= digest=
    case "$enabled" in 0|1) ;; *) die 'MU_GL_BATCHING must be 0 or 1' ;; esac
    # Re-query on every rerun. Do not replace a DLL mapped by a running game.
    diagnostic_bottle "$BOTTLE"
    for component in "$GAME" "$dll" "$recorded" "$STATE/mugl.mode" \
        "$PREFIX/drive_c/windows" "$PREFIX/drive_c/windows/system32" "$builtin"; do
        [ ! -L "$component" ] || die "Refusing symlink in mugl deployment: $component"
    done
    [ -f "$builtin" ] || die 'Missing system32 opengl32.dll; recreate this test bottle.'
    # Wine's PE builtin marker is in the DOS stub, immediately after e_lfanew.
    # Never copy the proxy here: absolute LoadLibrary must resolve Wine's builtin.
    [ "$(LC_ALL=C dd if="$builtin" bs=1 skip=64 count=16 2>/dev/null)" = 'Wine builtin DLL' ] ||
        die 'system32 opengl32.dll is not a Wine builtin; refusing deployment. Recreate the bottle.'
    [ ! -f "$recorded" ] || old=$(cat "$recorded")
    [ ! -f "$dll" ] || actual=$(shasum -a 256 "$dll" | awk '{print $1}')
    if [ "$enabled" = 1 ]; then
        [ -f "$artifact" ] || die 'Missing mugl build; run make mugl.'
        digest=$(shasum -a 256 "$artifact" | awk '{print $1}')
        [ -z "$actual" ] || [ "$actual" = "$old" ] || [ "$actual" = "$digest" ] ||
            die 'Unmanaged game opengl32.dll exists; preserve/inspect it before installing mugl.'
        cp "$artifact" "$dll"
        "$WINE" reg add "$key" /v opengl32 /t REG_SZ /d native,builtin /f
        printf '%s\n' "$digest" > "$recorded"
        printf 'on\n' > "$STATE/mugl.mode"
        note "mugl SHA-256: $digest"
    else
        [ -z "$actual" ] || [ "$actual" = "$old" ] || die 'Refusing to remove an unmanaged game opengl32.dll.'
        [ -z "$actual" ] || rm "$dll"
        if "$WINE" reg query "$key" /v opengl32 >/dev/null 2>&1; then
            "$WINE" reg delete "$key" /v opengl32 /f
        fi
        printf 'off\n' > "$STATE/mugl.mode"
        note 'mugl disabled for this bottle.'
    fi
    shasum -a 256 "$builtin" > "$STATE/mugl-builtin.sha256"
}
