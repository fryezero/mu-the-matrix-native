/* AUDIO-002: one independent ring reader per session/audio view. Other views
 * keep their own cursors. Drain even without a host so enabling audio cannot
 * replay old sounds; the caller preserves this reader until the session closes. */
#ifndef MU_SESSION_AUDIO_H
#define MU_SESSION_AUDIO_H
#include "mu_audio_host.h"
#include "../session/mu_session.h"
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
#endif
