/* parts/players.c (sketch): other players as a view of the session's CharactersClient table.
 * Replaces core/mu_world_players.c's file feed (which moves to fixture/behaviors/players.c and
 * speaks 0x12/0x3d/0x14/0x17/0x3f as real frames). */
#include "../world_part.h"
#include "../world_rt_internal.h"

typedef struct players_part {
    /* per (index, generation): body-part GL sets, fade, plates; never game state */
    uint32_t cached_generation[MU_VIEWPORT_MAX];
    mu_rp_calls calls;
} players_part;

/* No tick: MoveCharacters runs once over the whole table in parts/characters.c:
 *
 *   for (i = 0; i < sim->character_count; ++i)
 *       if (sim->used[i] && i != sim->hero_index)
 *           mu_rp_move_step(&sim->characters[i], &rt->rp_env, &calls);   // verified, unchanged
 *
 * This part only renders player entries (class_word == -1). */

static void players_frame(struct mu_world_rt *rt, void *self, float dt)
{
    /* TODO: v = mu_session_viewport(rt->session); for each used player entry whose generation differs from
     * cached_generation: (re)build its parts from the record's slots (mu_rp_slot type/level/option/ext);
     * pose/skin every visible player (the existing mu_world_players render path, fed by records) */
    (void)rt; (void)self; (void)dt;
    MU_NOT_IMPLEMENTED();
}

const mu_world_part_ops mu_part_players = {
    .name = "players", .state_size = sizeof(players_part),
    .frame = players_frame,
    /* .draw_gl / .draw_soft: the existing player passes over the records */
};
