/* AUDIO-002G: provenance accompanying the existing one-word MU_UI_SOUND.
 * Borrowed for the duration of sink.call; contains no client pointers. */
#ifndef MU_UI_SOUND_H
#define MU_UI_SOUND_H
#include "ui2d.h"

typedef struct mu_ui_sound_source {
    uint32_t routine, site, object, loop;
} mu_ui_sound_source;

static inline void mu_ui_sound_emit(mu_ui_state *state, uint32_t id, uint32_t routine, uint32_t site)
{
    const mu_ui_sound_source source = {routine, site, 0, 0};
    if (state->sink.call)
        state->sink.call(state->sink.user, MU_UI_SOUND, &id, 1, &source, sizeof source);
}
#endif
