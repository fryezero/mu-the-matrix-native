#ifndef MU_WORLD_RAVEN_H
#define MU_WORLD_RAVEN_H

/* The Dark Raven (Dark Spirit) in the walk-around world (NATIVE-HELPERS-002, docs/research/client-dark-spirit.md).
 *
 * The client's own routines, reconstructed in reconstructed/raven (compared with the client in Unicorn): the pet
 * byte 0x00c92bea, the Dark Raven's constructor 0x009ecbdf, MovePet 0x009ecfe9 (it flies around and above its
 * owner, sparkles, and in a safe zone turns into the soul model Dark_Soul that follows the owner's shoulder),
 * RenderPet 0x009ef6d5 and the render functors 0x00a2eea5 / 0x00a55f03.
 *
 * The module hangs off mu_world_helpers (its owners, models and draw target): index 0 is the hero (DEMO: --helper
 * dark-raven[-20|-40] stands for the pet byte the server sends, 1 / 2 / 3), 1 + i the demo players with raven=1|2|3
 * in the players file (DEMO: the same byte). */

#include <stdint.h>
#include <stdio.h>

#include "../../reconstructed/raven/raven.h"

struct mu_world_helpers;
struct mu_world_helpers_target;
struct mu_terrain_frustum;

typedef struct mu_world_raven_stats {
    uint32_t steps, sets, creates, moves, live, drawn, souls, sparkles, sprites, particles, shadows, draws, skipped;
} mu_world_raven_stats;

typedef struct mu_world_raven {
    mu_raven r;
    mu_rv_owner owners[MU_RV_OWNERS];
    int32_t applied[MU_RV_OWNERS];   /* the pet byte applied (-1 none) */
    mu_rv_inputs inputs;
    struct mu_world_helpers *w;
    mu_world_raven_stats stats;
    float world_time;
} mu_world_raven;

/* The pet byte the hero's demo option stands for: -1 when the item is not the Dark Raven. */
int32_t mu_world_raven_hero_value(int32_t item, int32_t state);

void mu_world_raven_init(mu_world_raven *rv, struct mu_world_helpers *w, uint32_t seed);
/* After the helpers' step: the owners, the pet bytes, MovePet per owner. */
void mu_world_raven_step(mu_world_raven *rv);
/* RenderPet per owner through the helpers' draw target (NULL: logic only). */
long mu_world_raven_draw(mu_world_raven *rv, const struct mu_terrain_frustum *frustum,
                         const struct mu_world_helpers_target *target);
void mu_world_raven_report_frame(const mu_world_raven *rv, FILE *out);
void mu_world_raven_report_summary(const mu_world_raven *rv, FILE *out);

#endif
