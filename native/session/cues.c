/* SESSION-CORE-001: the cue ring. One writer (the apply functions, through mu_session_cue), any
 * number of readers, each with its own cursor; a reader that falls more than MU_CUE_RING cues
 * behind loses the oldest and is told how many. */
#include "session_internal.h"
#include "mu_audio_cue.h"

#include <string.h>

void mu_session_cue(mu_session *s, const mu_cue *cue)
{
    mu_cue *slot = &s->cues.ring[s->cues.next_seq % MU_CUE_RING];
    *slot = *cue;
    slot->seq = s->cues.next_seq++;
}

size_t mu_session_cues(const mu_session *s, mu_cue_cursor *cursor, mu_cue *out, size_t cap, uint32_t *lost)
{
    if (lost)
        *lost = 0;
    if (!s || !cursor)
        return 0;
    uint64_t next = s->cues.next_seq;
    uint64_t oldest = next > MU_CUE_RING ? next - MU_CUE_RING : 0;
    if (cursor->next < oldest) {
        if (lost)
            *lost = (uint32_t)(oldest - cursor->next);
        cursor->next = oldest;
    }
    if (cursor->next > next)
        cursor->next = next;   /* a cursor from a later session: nothing to read */
    size_t n = 0;
    while (cursor->next < next && n < cap) {
        out[n++] = s->cues.ring[cursor->next % MU_CUE_RING];
        cursor->next++;
    }
    return n;
}

mu_cue_cursor mu_session_cue_cursor(const mu_session *s)
{
    mu_cue_cursor c = {s ? s->cues.next_seq : 0};
    return c;
}

void mu_session_sound_emit(mu_session *s, uint32_t routine, uint32_t site,
                           int32_t id, int16_t at_key, int loop)
{
    if (!s) return;
    mu_cue cue = {0};
    cue.kind = MU_CUE_SOUND;
    cue.handler = routine;
    cue.u.sound.id = id;
    cue.u.sound.at_key = at_key;
    cue.u.sound.loop = loop;
    cue.u.sound.site = site;
    mu_session_cue(s, &cue);
}

void mu_session_sound_missing(mu_session *s, uint32_t routine, uint32_t site, uint32_t input)
{
    if (!s) return;
    mu_cue cue = {0};
    cue.kind = MU_CUE_AUDIO_INPUT;
    cue.handler = routine;
    cue.u.sound.id = (int32_t)input;
    cue.u.sound.at_key = -2;
    cue.u.sound.site = site;
    mu_session_cue(s, &cue);
}
