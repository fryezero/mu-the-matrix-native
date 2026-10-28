#ifndef MU_WORLD_PETS_H
#define MU_WORLD_PETS_H

/* The data-driven pets in the walk-around world (NATIVE-HELPERS-002, docs/research/client-pets.md).
 *
 * The client's pet process (reconstructed/pets, compared with the client in Unicorn): petdata.bmd gives each pet
 * item its move type, range, scale, BlendMesh and play speeds; CreatePet makes a PetObject per (character, item);
 * UpdatePets flies the Demon and the Spirit of Guardian after their owner (move type 0) and walks Rudolph, the
 * Panda, the Unicorn and the Skeleton around it (move type 1, the zen collector); RenderPets draws them with their
 * sprites, particles and effects (the visuals 0x00eaeaf8).
 *
 * This module is a part of mu_world_helpers: it reads the helpers' owners (index 0 the hero, 1 + i the players),
 * loads its models through the helpers' model table (so the helpers' draw targets draw them) and runs inside
 * mu_world_helpers_step / _draw. The hero's pet comes from the demo option (--helper demon|spirit|rudolph|panda|
 * unicorn|skeleton, DEMO: the client creates it from the inventory); a player's from ChangeCharacterExt's recorded
 * calls (CreatePet 0x00eb0e78 / DeletePet 0x00eb1015). */

#include <stdint.h>
#include <stdio.h>

#include "../../reconstructed/pets/pets.h"

struct mu_world_helpers;
struct mu_world_helpers_target;
struct mu_terrain_frustum;

typedef struct mu_wp_stats {
    uint32_t steps, created, deleted, sprites, particles, particles_kept, effects, remembered, pickups, sounds;
    uint32_t live, drawn;
} mu_wp_stats;

typedef struct mu_world_pets {
    mu_pets p;
    struct mu_world_helpers *helpers; /* host binding for this pet process */
    mu_pet_owner owners[16];
    mu_pet_inputs inputs;
    int loaded;               /* petdata.bmd: 0 ok, 1 missing, 2 corrupted, -1 not read */
    int32_t hero_item;        /* DEMO: the hero's pet item code (-1 none) */
    int hero_applied;
    uint32_t clock;           /* GetTickCount / timeGetTime: 40 ms per logic step */
    mu_wp_stats stats;
} mu_world_pets;

/* Item code -> 1 when the pet process owns it (a petdata.bmd record or a known pet). */
int mu_world_pets_is_pet(int32_t item);
/* The pet names of --helper (demon, spirit, spirit-of-guardian, rudolph, panda, unicorn, skeleton, pc-panda,
 * pc-skeleton): the item code, or -2. */
int32_t mu_world_pets_parse(const char *text);
/* The Item.bmd model file of a pet model index (0x24e6 + item index): "Data/Item/<file>". */
int mu_world_pets_model_file(int32_t model, char *out, size_t size);

mu_world_pets *mu_world_pets_new(const char *game_root, int32_t hero_item, uint32_t seed, int no_assets);
void mu_world_pets_free(mu_world_pets *pp);

/* ChangeCharacterExt's recorded pet calls for owner `owner` (CreatePet(item, model, owner position) /
 * DeletePet(owner, item or slot type)). */
void mu_world_pets_create(mu_world_pets *pp, struct mu_world_helpers *w, int32_t owner, int32_t item, int32_t model);
void mu_world_pets_delete(mu_world_pets *pp, int32_t owner, int32_t item);
/* An owner left the view / was deleted: its pets go (DeleteCharacter, static). */
void mu_world_pets_owner_gone(mu_world_pets *pp, int32_t owner);

/* One logic step: the owners from the helpers, the hero's demo pet, UpdatePets. */
void mu_world_pets_step(mu_world_pets *pp, struct mu_world_helpers *w);
/* RenderPets: the pets' models through the helpers' draw target, their sprites / particles / effects through
 * NATIVE-PARTICLE-001's module. Returns the models drawn. */
long mu_world_pets_draw(mu_world_pets *pp, struct mu_world_helpers *w, const struct mu_terrain_frustum *frustum,
                        const struct mu_world_helpers_target *target);

void mu_world_pets_report_frame(const mu_world_pets *pp, FILE *out, int32_t frame);
void mu_world_pets_report_summary(const mu_world_pets *pp, FILE *out);

#endif
