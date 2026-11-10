/* AUDIO-002G: immediate legacy UI sound delivery. The owning reconstructed
 * controller decides the gates and order. No queue, action-success filter or
 * replay on attachment. Zero-initialise before first use. */
#ifndef MU_UI_AUDIO_H
#define MU_UI_AUDIO_H
#include "../../reconstructed/ui/ui_sound.h"
#include "../session/mu_cue.h"
#include <string.h>

typedef void (*mu_ui_audio_fn)(void *context, const mu_cue *cue, uint32_t tick);
typedef struct mu_ui_audio {
    mu_ui_audio_fn sound;
    void *context;
    uint64_t sequence;
} mu_ui_audio;

static inline void mu_ui_audio_set_sound(mu_ui_audio *audio, mu_ui_audio_fn sound, void *context)
{
    audio->sound = sound;
    audio->context = sound ? context : NULL;
}

static inline int mu_ui_audio_event(mu_ui_audio *audio, int op, const uint32_t *words, int count,
                                    const void *data, size_t bytes, uint32_t tick)
{
    if (!audio || op != MU_UI_SOUND || !words || count != 1 || words[0] != 25 || !data ||
        bytes != sizeof(mu_ui_sound_source))
        return 0;
    mu_ui_sound_source source;
    memcpy(&source, data, sizeof source);
    if (source.object || source.loop ||
        !((source.routine == 0x009867e3u && source.site == 0x0098689eu) ||
          (source.routine == 0x009d9eb2u && source.site == 0x009d9eedu)))
        return 0;
    mu_cue cue;
    memset(&cue, 0, sizeof cue);
    cue.seq = ++audio->sequence;
    cue.kind = MU_CUE_SOUND;
    cue.handler = source.routine;
    cue.u.sound.id = (int32_t)words[0];
    cue.u.sound.at_key = -2;
    cue.u.sound.site = source.site;
    if (audio->sound)
        audio->sound(audio->context, &cue, tick);
    return 1;
}
#endif
