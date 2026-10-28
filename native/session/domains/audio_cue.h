/* AUDIO-002: shared adapter for a reconstructed SND_Play log line.
 * Include after session_internal.h in a domain adapter. No audio engine in the session. */
#ifndef MU_DOMAIN_AUDIO_CUE_H
#define MU_DOMAIN_AUDIO_CUE_H
#include <stdio.h>
#include <string.h>
static inline int mu_domain_sound_cue(mu_session *s, const char *line)
{
    unsigned callee, id, loop;
    char object[32];
    int end = 0;
    if (sscanf(line, "call %x %x %31s %x %n", &callee, &id, object, &loop, &end) != 4 ||
        callee != 0x00a6ac96u || !end || line[end]) return 0;
    mu_cue cue = {0};
    cue.kind = MU_CUE_SOUND;
    cue.handler = s->route.client_handler;
    cue.u.sound.id = (int32_t)id;
    cue.u.sound.loop = (int32_t)loop;
    cue.u.sound.at_key = !strcmp(object, "0") ? -2 : -1;
    mu_session_cue(s, &cue);
    return 1;
}
#endif
