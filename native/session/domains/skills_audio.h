/* AUDIO-002D: event selected by the verified Master click, before its checks. */
#ifndef MU_SKILLS_AUDIO_H
#define MU_SKILLS_AUDIO_H
#include "../mu_audio_cue.h"
#include <string.h>
static inline void mu_session_master_audio_event(void *session, const char *what, int32_t id)
{
    if (!strcmp(what, "sound") && id == 0x19)
        mu_session_sound_emit(session, 0x00bb22e1u, 0x00bb23d1u, 0x19, -2, 0);
}
#endif
