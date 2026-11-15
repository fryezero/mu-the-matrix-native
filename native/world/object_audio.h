/* AUDIO-004: world-owner binding for immediate, provenance-bearing commands.
 * Include after world_rt_internal.h. The existing independent reader is drained
 * even when the audio host is disabled; no request survives detach/rebind. */
#ifndef MU_WORLD_OBJECT_AUDIO_H
#define MU_WORLD_OBJECT_AUDIO_H
#include "../core/mu_object_audio.h"
static int world_object_audio_command(void *context, const mu_obj_event *event)
{
    mu_world_rt *a = context;
    mu_session *session = world_rt_characters_session(a);
    int accepted = mu_object_audio_command_deliver(session, a->has_sound ? a->sound.host : NULL, a->world, event);
    if (accepted) world_rt_characters_audio_drain(a);
    return accepted;
}
#endif
