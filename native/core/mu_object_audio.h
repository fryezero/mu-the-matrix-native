/* AUDIO-003: delivery for world-object sounds already gated by reconstructed
 * callers. This decoder is deliberately world-specific: id 0x5a5 also occurs
 * in Karutan. No eligibility, animation or RNG decision is repeated here. */
#ifndef MU_OBJECT_AUDIO_H
#define MU_OBJECT_AUDIO_H
#include "mu_audio_host.h"
#include "../session/mu_audio_cue.h"
#include <string.h>

static inline int mu_object_audio_cue(int32_t world, int32_t id, mu_cue *cue)
{
    uint32_t routine = 0, site = 0;
    int loop = 0, owner = -2;
    if (world == 2) {
        routine = 0x017ff238u; /* enclosing MoveObject, branch begins 0x017fffda */
        if (id == 0x12) site = 0x0180041bu;
        else if (id == 0x11) site = 0x018005beu;
    } else if (world == 51) {
        routine = 0x00e34169u;
        loop = 1;
        owner = -3; /* unkeyed world OBJECT, never a native pointer */
        switch (id) {
        case 0x317: site = 0x00e3425fu; break;
        case 0x318: site = 0x00e3427cu; break;
        case 0x319: site = 0x00e34290u; break;
        case 0x314: site = 0x00e342aau; break;
        case 0x316: site = 0x00e342beu; break;
        case 0x315: site = 0x00e342d8u; break;
        case 0x313: site = 0x00e342ecu; break;
        }
    } else if (world == 100 || world == 101) {
        routine = 0x00e6f3d5u;
        if (id == 0x442) site = 0x00e6f4a6u;
    } else if (world == 143) {
        routine = 0x00e0ed1cu;
        switch (id) {
        case 0x5a6: site = 0x00e0f41bu; break;
        case 0x5a9: site = 0x00e0f43du; break;
        case 0x5a7: site = 0x00e0f465u; break;
        case 0x5a8: site = 0x00e0f478u; break;
        case 0x5a4: site = 0x00e0f48bu; break;
        case 0x5a5: site = 0x00e0f49eu; break;
        }
    }
    if (!site) return 0;
    memset(cue, 0, sizeof *cue);
    cue->kind = MU_CUE_SOUND;
    cue->handler = routine;
    cue->u.sound.site = site;
    cue->u.sound.id = id;
    cue->u.sound.loop = loop;
    cue->u.sound.at_key = (int16_t)owner;
    return 1;
}

/* AUDIO-004: exact command boundary. Only the already-gated play requests in
 * the reviewed allowlist are admitted. Stops have no command here and remain
 * refused by the runtime; they cannot be mistaken for a play of the same id. */
#include "../../reconstructed/objects/audio_request.h"
static inline int mu_object_audio_command_cue(int32_t world, const mu_obj_event *event, mu_cue *cue)
{
    if (event && world >= 123 && world <= 127 && event->args[15] == MU_AUDIO_OBJECT_TAG &&
        event->args[13] == 0x00e19ed0u) {
        const uint32_t site = event->args[14], id = event->args[0];
        const int stop = event->call == 0x00a6ad76u && event->count == 2 && event->args[1] == 1 &&
            ((site == 0x00e1a2bau && id == 0x4f2) || (site == 0x00e1a37du && id == 0x4f1));
        const int play = event->call == MU_OBJ_CALL_SOUND && event->count == 3 && !event->args[1] && !event->args[2] &&
            ((site == 0x00e1a071u && id == 0x4f4) || (site == 0x00e1a0a4u && id == 0x4f3) ||
             (site == 0x00e1a2cau && id == 0x4f1) || (site == 0x00e1a38du && id == 0x4f2));
        if (!stop && !play) return 0;
        memset(cue, 0, sizeof *cue);
        cue->kind = stop ? MU_CUE_SOUND_STOP : MU_CUE_SOUND;
        cue->handler = 0x00e19ed0u;
        cue->u.sound.site = site;
        cue->u.sound.id = (int32_t)id;
        cue->u.sound.at_key = -2;
        return 1;
    }
    if (!event || event->call != MU_OBJ_CALL_SOUND || event->count != 3 ||
        event->args[15] != MU_AUDIO_OBJECT_TAG) return 0;
    const uint32_t routine = event->args[13], site = event->args[14];
    int accepted = 0;
#define MU_OBJECT_AUDIO_SITE(w, r, s, id, owner, loop) \
    if ((world == (w) || ((w) == 69 && world >= 70 && world <= 72) || ((w) == 80 && world == 81)) && \
        routine == (r) && site == (s) && event->args[0] == (id) && \
        event->args[1] == (owner) && event->args[2] == (loop)) accepted = 1;
#include "../../reconstructed/audio/object_audio_sites.inc"
#undef MU_OBJECT_AUDIO_SITE
    if (!accepted) return 0;
    memset(cue, 0, sizeof *cue);
    cue->kind = MU_CUE_SOUND;
    cue->handler = routine;
    cue->u.sound.site = site;
    cue->u.sound.id = (int32_t)event->args[0];
    cue->u.sound.at_key = event->args[1] ? -3 : -2;
    cue->u.sound.loop = (int32_t)event->args[2];
    return 1;
}
static inline int mu_object_audio_command_deliver(mu_session *session, mu_audio_host *host,
                                                  int32_t world, const mu_obj_event *event)
{
    mu_cue cue;
    if (!mu_object_audio_command_cue(world, event, &cue)) return 0;
    if (session && cue.kind == MU_CUE_SOUND_STOP)
        mu_session_sound_stop_emit(session, cue.handler, cue.u.sound.site, cue.u.sound.id);
    else if (session)
        mu_session_sound_emit(session, cue.handler, cue.u.sound.site, cue.u.sound.id, cue.u.sound.at_key, cue.u.sound.loop);
    else if (host)
        mu_audio_host_cue(host, &cue, 0);
    return 1;
}

/* A session keeps its independent cursor even while audio is disabled. A
 * standalone host has no backlog. The caller drains after an accepted cue. */
static inline int mu_object_audio_deliver(mu_session *session, mu_audio_host *host, int32_t world, int32_t id)
{
    mu_cue cue;
    if (!mu_object_audio_cue(world, id, &cue)) return 0;
    if (session && cue.kind == MU_CUE_SOUND_STOP)
        mu_session_sound_stop_emit(session, cue.handler, cue.u.sound.site, cue.u.sound.id);
    else if (session)
        mu_session_sound_emit(session, cue.handler, cue.u.sound.site, cue.u.sound.id, cue.u.sound.at_key, cue.u.sound.loop);
    else if (host)
        mu_audio_host_cue(host, &cue, 0);
    return 1;
}
#endif
