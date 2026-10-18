# Reconstructed client audio logic

Authored C for the client's audio decisions (NATIVE-AUDIO-001). Names are
investigator choices, not original symbols. The finding is
[client-audio](../../docs/research/client-audio.md).

The client plays everything through FMOD Ex, imported as 35 C++ methods
(stdcall with `this` on the stack). That is the platform boundary. This module
never mixes audio: it makes the same FMOD calls as the client, in the same
order with the same arguments, through the `mu_fmod_api` table in
`client_audio.h`. The native engine (`native/core/mu_audio.c`) implements the
table with a software mixer; the validator implements it with a recorder.

| Source | Client routines |
|---|---|
| `audio_system.c` | FMOD wrapper init `0x010aad03`, create with path cache `0x010aaa97`, play `0x010aaffb`, settings `0x010ab480`/`0x010ab506`, group control; sound table `0x00a6ab76`..`0x00a6ae37`; PlayMp3 `0x0120f602`, StopMp3 `0x0120f5a0`; options-UI level conversions |
| `audio_world.c` | per-frame ambient loops and music selection `0x0185280c`..`0x01854498`; OpenWorld music-group volume `0x018290be`..`0x018293a6` |
| `audio_options.c` | `Data/Sound/Option.ini` read (`0x010ab7e0`) and write (`0x010ab573`, double format `0x00943757`) |
| `hero_sound.c` | NATIVE-WORLD-002: PlayWalkSound `0x013b1f61`, the footstep trigger `0x013b8090` in `0x013b23f8`, the foot reset `0x013a773c`, HeroTile `0x016ad7a5`; compared by `scripts/validate_hero_sound.py` ([finding](../../docs/research/native-world-alive.md)) |

## Comparison scope

`scripts/validate_audio.py` runs the client instructions in Unicorn over the
pinned restored text and second image section and compares every FMOD call
with the C. Modelled, not client code: uncaptured globals, the allocator, CRT
memset/memcpy/memmove/strstr/free/rand, `std::string` construction inside the
frame block, the security cookie and `__locale_changed = 0`, and the
event-world managers the frame block delegates to (recorded, not run). The
frame block segment `0x01854279`..`0x018542c2` jumps into protector-virtualised
code and is not reconstructed. The options file parser and writer are a static
reading checked against the installed file only; the jsoncpp reader itself was
not run.

```sh
./tools/python/bin/python scripts/validate_audio.py \
  --text /path/to/client-text.bin --data /path/to/client-image-data.bin --random 2000
```

`make test` runs the portable checks against a recording FMOD stand-in. The
private checks run with `MU_RECOVERY_INTEGRATION=1`, `MU_GAME_ROOT`,
`MU_CLIENT_TEXT` and `MU_IMAGE_DATA`.
