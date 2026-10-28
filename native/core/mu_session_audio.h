/* AUDIO-002: one independent ring reader per session/audio view. Other views
 * keep their own cursors. Drain even without a host so enabling audio cannot
 * replay old sounds; the caller preserves this reader until the session closes. */
#ifndef MU_SESSION_AUDIO_H
#define MU_SESSION_AUDIO_H
#include "mu_audio_host.h"
#include "../session/mu_session.h"
#include "../session/mu_audio_cue.h"
static inline void mu_session_audio_drain(const mu_session *session, mu_cue_cursor *cursor,
                                          mu_audio_host *host)
{
    if (!session) return;
    mu_session_status status;
    mu_session_status_get(session, &status);
    mu_cue cues[32];
    uint32_t lost;
    size_t count;
    do {
        count = mu_session_cues(session, cursor, cues, 32, &lost);
        mu_audio_host_cue_loss(host, lost, status.tick);
        for (size_t i = 0; i < count; ++i)
            mu_audio_host_cue(host, &cues[i], status.tick);
    } while (count);
}
/* ReceiveTalk's common tail. The caller invokes this only for the ordered
 * SND_Play events returned by mu_npc_talk_result, after its encrypted gate. */
static inline void mu_session_npc_talk_sound(mu_session *session, int32_t id)
{
    uint32_t site = id == 25 ? 0x012811cau : id == 28 ? 0x012811d8u : 0;
    if (site) mu_session_sound_emit(session, 0x01280659u, site, id, -2, 0);
}
/* Already-reconstructed environment sound sites. The caller keeps its verified
 * distance/random/action gates; unknown ids do not acquire an invented site. */
static inline int mu_session_ambient_sound(mu_session *session, int32_t id)
{
    uint32_t site;
    switch (id) {
    case 12: site = 0x00c9fcd5u; break;
    case 13: site = 0x00c9fcfbu; break;
    case 14: site = 0x00c9fd2fu; break;
    case 138: site = 0x00c9fd74u; break;
    case 15: site = 0x00ca1c80u; break;
    default: return 0;
    }
    mu_session_sound_emit(session, id == 15 ? 0x00ca05b3u : 0x00c9eb04u, site, id, -3, 0);
    return 1;
}
/* MoveCharacter model cases. buff_1b < 0 means the owning domain has no buff state.
 * rand_value is supplied only for a0b/a06; the caller owns the audio-only RNG. */
static inline void mu_session_npc_voice(mu_session *session, int32_t model, int32_t rand_value,
                                         uint16_t action, float frame, int buff_1b)
{
    uint32_t site = model == 0xa0b ? 0x013b5402u : model == 0xa06 ? 0x013b542fu :
                    model == 0xa01 ? 0x013b5494u : 0;
    if (!site) return;
    if (model == 0xa01 && buff_1b < 0) {
        mu_session_sound_missing(session, 0x013b23f8u, site, 0x01295adeu);
        return;
    }
    int32_t id = mu_audio_npc_voice(model, rand_value, action, frame, buff_1b);
    if (id >= 0) mu_session_sound_emit(session, 0x013b23f8u, site, id, -2, 0);
}
#endif
