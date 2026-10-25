/* SESSION-CORE-001 (sketch): one-shot presentation events produced while state is applied.
 *
 * The reconstructed receive handlers do two things: they write client records (that becomes
 * domain state + a revision bump) and they call into the engine (SND_Play, CreateJoint,
 * CreateEffect, the damage-number CreatePoint, chat lines, GFx window calls). The session's
 * env adapters turn the second kind into cues, typed here, in the order the handler made the
 * calls. Views replay them; nothing in state depends on a cue having been seen.
 *
 * Cues carry client identifiers (sound ids, effect model ids, GlobalText indices, movie
 * names) because those ARE the domain vocabulary of the renderer and the audio engine.
 * They never carry wire bytes.
 */
#ifndef MU_CUE_H
#define MU_CUE_H

#include <stdint.h>

#ifdef __cplusplus
extern "C" {
#endif

typedef struct mu_cue_cursor {
    uint64_t next;               /* sequence number of the next cue this reader wants */
} mu_cue_cursor;

typedef enum mu_cue_kind {
    MU_CUE_SOUND = 1,            /* SND_Play(id, object, loop) */
    MU_CUE_EFFECT,               /* CreateEffect / CreateJoint / CreateParticle with the client's type and subtype */
    MU_CUE_DAMAGE,               /* the damage number over a character (CreatePoint) */
    MU_CUE_CHAT,                 /* a chat-window line */
    MU_CUE_NOTICE,               /* a system notice (GlobalText or server text) */
    MU_CUE_WINDOW,               /* a GFx window call the handler made (open / show / close all / invoke) */
    MU_CUE_LEVEL_UP,             /* level or master level changed (HUD flash; the joints arrive as EFFECT cues) */
    MU_CUE_ANSWER,               /* the server answered an intent kind: accepted or refused with a code */
    MU_CUE_UNHANDLED             /* development: a frame whose opcode has no dispatcher row (counted, journaled) */
} mu_cue_kind;

typedef enum mu_window_verb { MU_WINDOW_OPEN = 1, MU_WINDOW_SHOW, MU_WINDOW_CLOSE, MU_WINDOW_CLOSE_ALL,
                              MU_WINDOW_INVOKE } mu_window_verb;

typedef struct mu_cue {
    uint64_t seq;
    mu_cue_kind kind;
    uint32_t handler;            /* the client handler that produced it (provenance for tests and the journal) */
    union {
        struct { int32_t id; int16_t at_key; int loop; } sound;              /* at_key -1: the hero, -2: none */
        struct { int32_t type, subtype; int16_t owner_key; float position[3]; } effect;
        struct { int16_t target_key; int32_t amount; int32_t color; } damage;
        struct { int32_t channel; char name[11]; char text[256]; } chat;
        struct { int32_t global_text; char text[256]; } notice;
        struct { mu_window_verb verb; char movie[48]; char method[48]; int32_t args[6]; } window;
        struct { int32_t level, master_level; } level_up;
        struct { int32_t intent_kind; int32_t accepted; int32_t code; } answer;
        struct { uint8_t head, opcode, sub; uint16_t length; } unhandled;
    } u;
} mu_cue;

#ifdef __cplusplus
}
#endif

#endif /* MU_CUE_H */
