/* AUDIO-004: provenance attached to an already-selected object sound.
 * args[count..15] are outside the original callee argument stream. Sound
 * records use only three words; reserve 13..15 for routine/site/tag. This
 * preserves the event ABI and every normalized original call argument.
 * A tag is local to the event, never global or queued separately. */
#ifndef MU_AUDIO_OBJECT_REQUEST_H
#define MU_AUDIO_OBJECT_REQUEST_H
#include "object_render.h"
#define MU_AUDIO_OBJECT_TAG 0x41554434u
static inline void mu_audio_object_tag(mu_obj_log *log, uint32_t routine, uint32_t site)
{
    if (!log || !log->count || log->overflow || !site) return;
    mu_obj_event *e = &log->events[log->count - 1];
    if (e->call != MU_OBJ_CALL_SOUND || e->count != 3 || e->args[15]) return;
    e->args[13] = routine;
    e->args[14] = site;
    e->args[15] = MU_AUDIO_OBJECT_TAG;
}
static inline void mu_audio_ignis_request(mu_obj_log *log, uint16_t action)
{
    mu_audio_object_tag(log, 0x00e05d76u, action == 1 ? 0x00e05eddu : 0x00e05f09u);
}
static inline void mu_audio_premove_request(mu_obj_log *log, int32_t cls, const uint8_t *o)
{
    if (!log || !log->count) return;
    const mu_obj_event *e = &log->events[log->count - 1];
    const uint32_t id = e->args[0];
    uint32_t routine = 0, site = 0;
    if (cls >= 69 && cls <= 72) {
        routine = 0x00dd2faeu;
        switch (id) {
        case 0x38f: site = 0x00dd3008u; break;
        case 0x38c: site = 0x00dd303au; break;
        case 0x38d: site = 0x00dd304du; break;
        case 0x38e: site = 0x00dd3060u; break;
        }
    } else if (cls == 80 || cls == 81) {
        routine = 0x00e189afu;
        if (id == 0x3db) site = 0x00e189d8u;
    } else if (cls == 122 && o) {
        routine = 0x00e5e1a4u;
        switch (mu_obj_i32(o, MU_OBJF_TYPE)) {
        case 0x1a: site = 0x00e5e214u; break;
        case 0x83: case 0x84: site = 0x00e5e236u; break;
        case 0x85: site = 0x00e5e25du; break;
        case 0xa1: site = 0x00e5e270u; break;
        case 0xa8: site = 0x00e5e2c2u; break;
        }
    }
    mu_audio_object_tag(log, routine, site);
}
static inline void mu_audio_keth_request(mu_obj_log *log, int32_t world, int32_t type, uint16_t action)
{
    if (!log || !log->count || (world != 135 && world != 136)) return;
    const mu_obj_event *e = &log->events[log->count - 1];
    uint32_t site = 0;
    const int old = world == 135;
    switch (e->args[0]) {
    case 0x557: site = old ? 0x00e3a861u : 0; break;
    case 0x558: site = old ? 0 : 0x00d93caeu; break;
    case 0x54c: site = old ? 0x00e3a92eu : 0x00d93d7bu; break;
    case 0x549: site = old ? 0x00e3a9f8u : 0x00d93e45u; break;
    case 0x548: site = old ? 0x00e3aa3cu : 0x00d93e89u; break;
    case 0x55c: site = old ? (action == 1 ? 0x00e3ac4au : 0x00e3ac75u)
                            : (action == 1 ? 0x00d940a3u : 0x00d940ceu); break;
    case 0x55b: site = old ? (action == 0 ? 0x00e3aceau : 0x00e3ad8eu)
                            : (action == 0 ? 0x00d94143u : 0x00d941e7u); break;
    case 0x54b: site = old ? 0x00e3ae4bu : (type == 0xa5 ? 0x00d94361u : 0x00d942aau); break;
    case 0x559: site = old ? 0 : 0x00d94b75u; break;
    case 0x55a: site = old ? 0 : 0x00d94cbcu; break;
    }
    mu_audio_object_tag(log, old ? 0x00e3a719u : 0x00d93b31u, site);
}
/* Kubera's stop and play are distinct operations in the existing event stream.
 * Never annotate an overflowed/foreign event or replace previous provenance. */
static inline void mu_audio_kubera_request(mu_obj_log *log)
{
    if (!log || !log->count || log->overflow) return;
    mu_obj_event *e = &log->events[log->count - 1];
    if (e->args[15]) return;
    uint32_t site = 0;
    if (e->call == 0x00a6ad76u && e->count == 2 && e->args[1] == 1) {
        if (e->args[0] == 0x4f2) site = 0x00e1a2bau;
        else if (e->args[0] == 0x4f1) site = 0x00e1a37du;
    } else if (e->call == MU_OBJ_CALL_SOUND && e->count == 3 && !e->args[1] && !e->args[2]) {
        switch (e->args[0]) {
        case 0x4f4: site = 0x00e1a071u; break;
        case 0x4f3: site = 0x00e1a0a4u; break;
        case 0x4f1: site = 0x00e1a2cau; break;
        case 0x4f2: site = 0x00e1a38du; break;
        }
    }
    if (!site) return;
    e->args[13] = 0x00e19ed0u;
    e->args[14] = site;
    e->args[15] = MU_AUDIO_OBJECT_TAG;
}
#endif
