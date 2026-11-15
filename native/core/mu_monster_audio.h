/* AUDIO-005: sound-only adapters for complete scalar monster owners. */
#ifndef MU_NATIVE_MONSTER_AUDIO_H
#define MU_NATIVE_MONSTER_AUDIO_H
#include "../../reconstructed/audio/monster_audio.h"
#include "mu_combat.h"
#include "../session/mu_audio_cue.h"

static inline mu_monster_sound_plan mu_monster_audio_plan(int32_t world, int32_t model,
    uint16_t action, float frame, const float position[3], const float hero[3])
{
    mu_monster_sound_plan empty = {0};
    /* 0x013a04d6 runs before the class slot. Its six special models are
     * outside this scalar-owner admission, even in a supported world. */
    if (model == 0x840 || model == 0xa5e || model == 0xa63 || model == 0xa65 ||
        model == 0xa66 || model == 0xa67) return empty;
    mu_monster_sound_plan p = mu_monster_sound_select(world, model, action, frame);
    if (!p.known) return p;
    const float dx = position[0] - hero[0], dy = position[1] - hero[1];
    const float distance = (float)sqrt((double)(dx * dx + dy * dy));
    /* Shared dispatch consumes >500 before the slot, including silent returns.
     * COMISS with unordered inputs does not take this strict-greater branch. */
    if (distance > 500.0f) { p.handled = 1; p.count = 0; }
    return p;
}
static inline void mu_monster_audio_emit(mu_session *session, const mu_monster_sound_plan *p, int16_t key)
{
    for (int n = 0; n < p->count; ++n) {
        const mu_monster_sound *s = &p->sound[n];
        mu_session_sound_emit(session, s->routine, s->site, s->id, s->object ? key : -2, s->loop);
    }
}
/* Native fixture motion starts the existing action 2. The original SetPlayerWalk
 * calls the dispatcher after SetAction. This adapter uses those resulting sound
 * inputs without changing the record or doing a second animation step. */
static inline void mu_monster_audio_motion(mu_session *session, const mu_walk *walk,
    const mu_world_actor *actor, const mu_rp_character *record)
{
    if (!session || !walk || !walk->map || !actor->actor.loaded || actor->player ||
        !record->live || !record->movement) return;
    mu_monster_sound_plan p = mu_monster_audio_plan(walk->map->world, actor->actor.spec.model_index,
        2, mu_actor_action(&actor->actor) == 2 ? mu_actor_frame(&actor->actor) : 0.0f,
        record->position, walk->hero.position);
    mu_monster_audio_emit(session, &p, actor->session_key);
}
/* MoveCharacter's 0x013a77da invokes the dispatcher only for actions 0/1.
 * These scalar owners may be silent; no shared hit/attack/death call is added. */
static inline void mu_monster_audio_tick(mu_session *session, const mu_walk *walk, const mu_world_actor *actor)
{
    if (!session || !walk || !walk->map || !actor->actor.loaded || actor->player) return;
    const uint16_t action = mu_actor_action(&actor->actor);
    if (action > 1) return;
    mu_monster_sound_plan p = mu_monster_audio_plan(walk->map->world, actor->actor.spec.model_index,
        action, mu_actor_frame(&actor->actor), actor->position, walk->hero.position);
    mu_monster_audio_emit(session, &p, actor->session_key);
}
/* These three caller seams are already gated by their owning combat services.
 * The dispatch precedes the shared model-slot fallback, even if it has no sound.
 * The original voice marker is read only. It is never replicated or rewritten. */
static inline int32_t mu_monster_audio_combat(mu_combat *c, int32_t index, float played, int32_t fallback)
{
    if (!c->actors || !c->walk || !c->map || index < 0 || index >= c->actors->count || !(played == 0.0f))
        return fallback;
    const mu_world_actor *actor = &c->actors->list[index];
    if (!actor->actor.loaded || actor->player) return fallback;
    mu_monster_sound_plan p = mu_monster_audio_plan(c->map->world, actor->actor.spec.model_index,
        mu_actor_action(&actor->actor), mu_actor_frame(&actor->actor), actor->position, c->walk->hero.position);
    mu_monster_audio_emit(c->session, &p, actor->session_key);
    if (!c->session && c->play_sound)
        for (int n = 0; n < p.count; ++n) c->play_sound(c->sound_context, p.sound[n].id);
    return p.known && p.handled ? -1 : fallback;
}
static inline float mu_monster_audio_attack(mu_combat *c, int32_t index, float played)
{
    /* A local voice-input value suppresses only this fallback, not future
     * triggers or the session record. Negative sentinel means handled. */
    return mu_monster_audio_combat(c, index, played, 0) < 0 ? 0.001f : played;
}
#endif
