/* parts/combat.c (sketch): combat as a view + intent producer.
 * Keeps the verified client-side pieces of core/mu_combat (attack actions and speed, range,
 * hit predicate, damage text layout, dead fade, the older effect system); drops its demo
 * server (damage rolls, counter-attacks, respawn timers -> fixture/behaviors/combat.c). */
#include "../world_part.h"
#include "../world_rt_internal.h"

typedef struct combat_part {
    mu_cue_cursor cues;
    /* damage-number sprites, effect pools, terrain lights: presentation only */
} combat_part;

/* MoveHero's attack case (before the walk): the hero is in range of its target -> the client's
 * attack action and the attack request. */
static void combat_pre_tick(struct mu_world_rt *rt, void *self, mu_sim *sim)
{
    /* TODO
     *   target = rt->walk.target key (set by the input router's left click on a character)
     *   if mu_combat in-range rule (verified) holds and the attack timer allows:
     *       local: SetAction attack on the hero (mu_walk), as the client does before the answer
     *       mu_intent in = {MU_INTENT_ATTACK, .u.attack = {key, action, dir}}; mu_session_submit(rt->session, &in)
     *       (UNRECOVERED until SESSION-COMBAT-001: the hero still swings; the journal shows the gap)
     */
    (void)rt; (void)self; (void)sim;
    MU_NOT_IMPLEMENTED();
}

static void combat_frame(struct mu_world_rt *rt, void *self, float dt)
{
    combat_part *c = self;
    mu_cue cue[64];
    uint32_t lost = 0;
    size_t n = mu_session_cues(rt->session, &c->cues, cue, 64, &lost);
    for (size_t i = 0; i < n; ++i) {
        /* TODO: MU_CUE_DAMAGE -> damage text over the character (verified layout);
         *       MU_CUE_EFFECT of the combat effect types -> the effect pools */
    }
    (void)dt;
}

const mu_world_part_ops mu_part_combat = {
    .name = "combat", .state_size = sizeof(combat_part),
    .pre_tick = combat_pre_tick, .frame = combat_frame,
};
