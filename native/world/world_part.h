/* WORLD-RT-001: world parts, one row of parts.def each.
 *
 * Replaces the ~14 places a subsystem was wired in world/main.c (app fields, load, unload, on_step,
 * combat_pre_step, advance, draw_gl, draw_soft, gl_setup, gl_teardown, the reports, the embed's config and
 * the shell's) with one row in parts.def plus the part's file.  Every hook is optional; a hook does what
 * world/main.c did at that place, including its own guard ("if (a->combat)"), so the runtime calls each hook
 * of a column in the column's order on every pass.
 *
 * The orders are columns of parts.def, not fields here: open (the row order: load()), pre_tick
 * (combat_pre_step, MoveHero's attack/pick-up/NPC case before the walk), tick (on_step: MoveCharacters'
 * order after the walk), frame (advance, once per rendered frame), draw_gl / draw_soft (RenderScene in each
 * backend; the two differ for the helpers and the marker) and report (the frame rows and the summary).
 * close runs in reverse row order; gl_setup / gl_teardown in row order.
 *
 * State: a part's own presentation state (GL handles, per-view caches) is its `self` (state_size bytes,
 * zeroed, alive as long as the runtime).  The unmigrated demo subsystems (mu_combat, mu_world_items, mu_npc,
 * mu_world_players, ...) stay runtime fields (world_rt_internal.h) because they still point into each other
 * (combat -> walk, character, actors; names -> combat; players -> names, combat, social; ...); each domain
 * migration (plan.md, stage 2) moves its subsystem behind the session and out of the shared fields. */
#ifndef MU_WORLD_PART_H
#define MU_WORLD_PART_H

#include <stddef.h>
#include <stdint.h>

#include "../core/mu_raster.h"

struct mu_world_rt;

/* What one draw pass carries from part to part: the frame size, the open perf phase, the terrain's faces. */
typedef struct mu_world_draw {
    int32_t width, height;
    double perf;                   /* NATIVE-PERF-001: the phase started by an earlier part of the pass */
    long faces;                    /* the terrain pass's face count (the draw's return value) */
    mu_raster *raster;             /* draw_soft only */
} mu_world_draw;

typedef struct mu_world_part_ops {
    const char *name;
    size_t state_size;
    int (*open)(struct mu_world_rt *rt, void *self);          /* load(): 1 = the world does not load */
    void (*close)(struct mu_world_rt *rt, void *self);        /* unload() */
    void (*pre_tick)(struct mu_world_rt *rt, void *self);     /* one 40 ms step, before the walk */
    void (*tick)(struct mu_world_rt *rt, void *self);         /* one 40 ms step, after the walk */
    void (*frame)(struct mu_world_rt *rt, void *self, uint32_t now);   /* once per rendered frame */
    void (*draw_gl)(struct mu_world_rt *rt, void *self, mu_world_draw *d);
    void (*draw_soft)(struct mu_world_rt *rt, void *self, mu_world_draw *d);
    void (*gl_setup)(struct mu_world_rt *rt, void *self);
    void (*gl_teardown)(struct mu_world_rt *rt, void *self);
    void (*report_frame)(const struct mu_world_rt *rt, const void *self, int32_t frame);
    void (*report_summary)(const struct mu_world_rt *rt, const void *self);
} mu_world_part_ops;

#define MU_PART(id, ops, pre_tick, tick, frame, draw_gl, draw_soft, report) extern const mu_world_part_ops ops;
#include "parts.def"
#undef MU_PART

#endif
