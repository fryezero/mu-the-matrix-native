/* AUDIO-002E: sound events selected by the scene-5 tick, in original order.
 * The following service distinguishes the three otherwise identical calls.
 * Branch gates belong to mu_charsel_tick_step, not to this adapter. */
#ifndef MU_CHARSEL_AUDIO_H
#define MU_CHARSEL_AUDIO_H
#include "../../reconstructed/charsel/charsel.h"
#include "../session/mu_cue.h"
#include <string.h>

static inline int mu_charsel_audio_cue(const mu_charsel_log *log, int32_t index, mu_cue *cue)
{
    if (!log || !cue || index < 0 || index + 1 >= log->count)
        return 0;
    const mu_charsel_event *e = &log->events[index];
    if (e->call != 0x00a6ac96 || e->count != 3 || e->args[0] != 25 || e->args[1] || e->args[2])
        return 0;
    uint32_t site;
    switch (log->events[index + 1].call) {
    case 0x009a5029: site = 0x01857064u; break; /* Enter, before refusal check */
    case 0x009a5792: site = 0x01857163u; break; /* Esc opens menu */
    case 0x00ac3bf7: site = 0x018571e6u; break; /* Esc closes create panel */
    default: return 0;
    }
    memset(cue, 0, sizeof *cue);
    cue->kind = MU_CUE_SOUND;
    cue->handler = 0x01856e6cu;
    cue->u.sound.id = 25;
    cue->u.sound.at_key = -2;
    cue->u.sound.site = site;
    return 1;
}
#endif
