/* AUDIO-002: cosmetic audio decisions from a world caller into its owning session.
 * No replicated records are written. site is the original SND_Play instruction. */
#ifndef MU_AUDIO_CUE_H
#define MU_AUDIO_CUE_H
#include "mu_session.h"
#ifdef __cplusplus
extern "C" {
#endif
void mu_session_sound_emit(mu_session *s, uint32_t routine, uint32_t site,
                           int32_t id, int16_t at_key, int loop);
void mu_session_sound_missing(mu_session *s, uint32_t routine, uint32_t site, uint32_t input);
#ifdef __cplusplus
}
#endif
#endif
