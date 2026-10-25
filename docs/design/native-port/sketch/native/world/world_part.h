/* WORLD-RT-001 (sketch): world parts - the subsystems as views of the session.
 *
 * Replaces the ~14 places a subsystem is wired today (app fields, load, unload, on_step,
 * combat_pre_step, advance, draw_gl, draw_soft, the travel keep list, main() args,
 * mu_world_embed_config, mu_shell_config/open_world, client/main.c parsing, LaunchPlan) with
 * one row in parts.def plus the part's own file.
 *
 * Every hook is optional. Hooks get the runtime (assets, map, walk, the session pointer) and
 * their own state. A part never holds a pointer into another part: what combat needs from the
 * characters it reads from the session's viewport; what names need from combat it reads from
 * cues; shared engine services (effects scene, particles, terrain lights) are runtime fields.
 */
#ifndef MU_WORLD_PART_H
#define MU_WORLD_PART_H

#include "mu_world_rt.h"

struct mu_world_rt;   /* runtime internals: world_rt_internal.h (map, walk, effects, particles, gl, session) */

typedef struct mu_world_part_ops {
    const char *name;
    size_t state_size;
    /* tick_order / draw_order: the client's MoveCharacters/MoveHero order (on_step, main.c:758-826)
     * and RenderScene order (draw_gl, main.c:2296-2520). Both are client facts; both live in this one
     * row. world_rt.c sorts by each and _Static_asserts the orders are unique. */
    int16_t tick_order, draw_order;
    int (*open)(struct mu_world_rt *rt, void *self, char *error, size_t error_size);   /* also after travel */
    void (*close)(struct mu_world_rt *rt, void *self);
    void (*pre_tick)(struct mu_world_rt *rt, void *self, mu_sim *sim);   /* before MoveHero's walk (attack case) */
    void (*tick)(struct mu_world_rt *rt, void *self, mu_sim *sim);       /* one 40 ms step */
    void (*frame)(struct mu_world_rt *rt, void *self, float dt);         /* per rendered frame: cues, changed domains */
    void (*draw_gl)(struct mu_world_rt *rt, void *self);
    void (*draw_soft)(struct mu_world_rt *rt, void *self, mu_raster *raster);
    int (*input)(struct mu_world_rt *rt, void *self, const mu_input_msg *msg);   /* router step 3 owners */
    void (*report)(const struct mu_world_rt *rt, const void *self, char *json, size_t cap);
} mu_world_part_ops;

#endif
