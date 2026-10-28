/* AUDIO-002D: CreateItem sound gates. Availability is the existing static
 * Item.bmd getter's answer: -1 unknown, 0 absent, 1 present. */
#ifndef MU_ITEMS_AUDIO_H
#define MU_ITEMS_AUDIO_H
#include "../mu_audio_cue.h"
#include "../../../reconstructed/items/ground_items.h"
static inline void mu_session_items_drop_audio(mu_session *s, int32_t code, int drop, int available, int16_t slot)
{
    int32_t id = mu_gi_drop_sound(code, drop);
    if (id < 0 || available == 0) return;
    uint32_t site;
    switch (id) {
    case 0x1f: site = 0x016daafdu; break;
    case 0x45: site = 0x016daddeu; break;
    case 0x2d3: site = 0x016dae04u; break;
    case 0x5a: site = code >= 0x1d09 ? 0x016dae5fu : 0x016dae36u; break;
    case 0x1e: site = 0x016dae76u; break;
    default: return;
    }
    if (available < 0) mu_session_sound_missing(s, 0x016daa27u, site, 0x00ccc591u);
    else mu_session_sound_emit(s, 0x016daa27u, site, id, id == 0x1f ? -2 : slot, 0);
}
#endif
