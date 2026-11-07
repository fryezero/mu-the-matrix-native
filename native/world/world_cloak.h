/* RENDER-ITEMS-CLOAK: the capes of wings 0x2382..0x2385, 0x2394, 0x2395 in the world (reconstructed/cloth).
 *
 * The client draws these capes as a physics cloth that RenderCharacter 0x01363260 owns per character: it steps the
 * OBJECT's cloths every rendered frame (MoveCloth 0x01362f24) and, behind its cloth flag, creates (CreateCloth
 * 0x01357ccc) and renders them (RenderCloth 0x01363098) after the body parts and before the weapons and the wing.
 * The world's wind is the physics manager's walk (0x00fdad7b, five times per logic step in the frame driver).
 * See docs/research/client-render-items.md part 24. The hero and player parts call world_cloak_draw between their
 * body parts and their linked items. */
#ifndef MU_WORLD_CLOAK_H
#define MU_WORLD_CLOAK_H

#include <stdint.h>

#include "../core/mu_character.h"
#include "../core/mu_scene.h"
#include "../../reconstructed/cloth/cloth.h"

struct mu_world_rt;
struct mu_raster;

enum { WORLD_CLOAK_HERO = 0 };   /* key of the hero; player i is key 1 + i */
#define WORLD_CLOAK_PLAYER(i) (1 + (i))

/* One character's cloth call for this rendered frame. raster: the software draw's raster (its texture table is set
 * to the cloth bitmaps for the draw and restored after), NULL for GL (the cloth bitmaps' own GL set, drawn through
 * batch when the caller's batch session is open, else immediately). generation: changes when the character's
 * OBJECT is made again (a viewport create), which drops its cloths. gate: the CHARACTER's inputs of RenderCharacter's
 * cloth block (its world field is the runtime's); action / prior_action: OBJECT +0x2a / +0x2c (RenderCloth's draw
 * test); alpha: OBJECT +0xdc. */
void world_cloak_draw(struct mu_world_rt *a, int32_t key, uint32_t generation, const mu_character *ch,
                      const mu_cloth_gate_in *gate, uint16_t action, uint16_t prior_action, float alpha,
                      struct mu_raster *raster, void *batch);
/* Once per rendered frame after its logic steps (mu_world_rt_frame): the physics manager's wind walk (five steps per
 * logic step) and this frame's wind, time and step counter for the wearers' catch-up. Nothing before a cloth wing. */
void world_cloak_frame(struct mu_world_rt *a);
/* The travel / unload drop: the characters' OBJECTs are freed with their cloths. */
void world_cloak_reset(struct mu_world_rt *a);
void world_cloak_free(struct mu_world_rt *a);
void world_cloak_gl_teardown(struct mu_world_rt *a);
/* Counters for reports and tests. */
typedef struct world_cloak_stats {
    uint32_t created;   /* cloths made (CreateCloth's cases) */
    uint32_t steps;     /* MoveCloth calls on a cloth (Move2(0.005, 5) each) */
    uint32_t drawn;     /* cloth renders */
    uint32_t gated;     /* frames a wearer's cloth flag was clear */
    uint32_t wind_steps;
    float wind;
} world_cloak_stats;
void world_cloak_stats_get(const struct mu_world_rt *a, world_cloak_stats *out);

#endif
