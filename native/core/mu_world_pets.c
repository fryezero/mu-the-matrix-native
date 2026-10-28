/* The data-driven pets in the walk-around world (NATIVE-HELPERS-002). See mu_world_pets.h. */
#include "mu_world_pets.h"

#include <stdlib.h>
#include <string.h>

#include "mu_objects.h"
#include "mu_particles.h"
#include "mu_world_helpers.h"
#include "../../reconstructed/terrain/terrain.h"

/* The pets' Item.bmd model files (records 13,64.. of the installed Item.bmd, mu-data item; model index = item code
 * + 0xae6 = 0x24e6 + item index). */
static const struct { int32_t item; const char *file; const char *name; } pet_table[] = {
    {MU_PET_DEMON, "demon.bmd", "demon"},
    {MU_PET_SPIRIT, "maria.bmd", "spirit"},
    {MU_PET_RUDOLPH, "xmas_deer.bmd", "rudolph"},
    {MU_PET_PANDA, "pandapet.bmd", "panda"},
    {MU_PET_UNICORN, "pet_unicorn.bmd", "unicorn"},
    {MU_PET_SKELETON, "skeletonpet.bmd", "skeleton"},
    {MU_PET_PC_PANDA, "pandapet.bmd", "pc-panda"},
    {MU_PET_PC_SKELETON, "skeletonpet.bmd", "pc-skeleton"},
};

int mu_world_pets_is_pet(int32_t item)
{
    for (size_t i = 0; i < sizeof pet_table / sizeof pet_table[0]; ++i)
        if (pet_table[i].item == item)
            return 1;
    return 0;
}

int32_t mu_world_pets_parse(const char *text)
{
    if (!strcmp(text, "spirit-of-guardian") || !strcmp(text, "maria"))
        return MU_PET_SPIRIT;
    for (size_t i = 0; i < sizeof pet_table / sizeof pet_table[0]; ++i)
        if (!strcmp(text, pet_table[i].name))
            return pet_table[i].item;
    return -2;
}

int mu_world_pets_model_file(int32_t model, char *out, size_t size)
{
    for (size_t i = 0; i < sizeof pet_table / sizeof pet_table[0]; ++i)
        if (MU_PET_MODEL_BASE + pet_table[i].item - 0x1a00 == model)
            return snprintf(out, size, "Data/Item/%s", pet_table[i].file) > 0;
    return 0;
}

/* ---------------------------------------------------------------- host */

static uint32_t h_clock(void *c)
{
    return ((mu_world_pets *)c)->clock;
}

static int h_has_model(void *c, int32_t model)
{
    (void)c;
    mu_world_helpers *w = ((mu_world_pets *)c)->helpers;
    if (!w || w->no_assets)
        return 1;
    mu_wh_model *m = mu_world_helpers_model(w, model);
    return m && m->loaded;
}

static void h_animate(void *c, mu_hp_object *o, int32_t index, float speed)
{
    (void)c;
    mu_world_helpers *w = ((mu_world_pets *)c)->helpers;
    mu_wh_model *m = w ? mu_world_helpers_model(w, index) : NULL;
    if (!m || !m->loaded || m->bmd.action_count <= 0)
        return;
    uint8_t loop = 0;
    mu_model_set_state(&m->model, o->action, o->frame, o->prior_frame, o->prior_action);
    mu_model_tick(&m->model, speed, &loop);
    o->frame = mu_model_frame(&m->model);
    o->prior_frame = mu_model_prior_frame(&m->model);
    o->prior_action = mu_model_prior_action(&m->model);
}

static void h_pickup(void *c, int32_t item)
{
    mu_world_pets *pp = c;
    (void)item;
    pp->stats.pickups++;
    pp->p.pending_pickup = -1;   /* DEMO: no server answers the request; the next one may go */
}

static void h_sound(void *c, int32_t sound)
{
    mu_world_pets *pp = c;
    (void)sound;
    pp->stats.sounds++;
}

mu_world_pets *mu_world_pets_new(const char *game_root, int32_t hero_item, uint32_t seed, int no_assets)
{
    mu_world_pets *pp = calloc(1, sizeof *pp);
    if (!pp)
        return NULL;
    mu_pet_host host;
    memset(&host, 0, sizeof host);
    host.context = pp;
    host.tick = h_clock;
    host.time = h_clock;
    host.has_model = h_has_model;
    host.animate = h_animate;
    host.pickup = h_pickup;
    host.sound = h_sound;
    mu_pets_init(&pp->p, seed, pp->owners, MU_WH_OWNERS, &host);
    pp->hero_item = hero_item;
    pp->loaded = -1;
    pp->inputs.hero = 0;
    pp->inputs.scene = 6;
    pp->clock = 0x10000;
    for (int32_t i = 0; i < 16; ++i)
        pp->owners[i].alt_pet = -1;
    if (!no_assets && game_root && *game_root) {
        char path[1024];
        uint8_t raw[MU_PET_FILE_BYTES + 16];
        size_t n = 0;
        FILE *f = mu_objects_resolve(game_root, "Data/Local/petdata.bmd", path, sizeof path) ? fopen(path, "rb")
                                                                                              : NULL;
        if (f) {
            n = fread(raw, 1, sizeof raw, f);
            fclose(f);
        }
        pp->loaded = mu_pet_data_load(f ? raw : NULL, n, pp->p.table);
    }
    if (pp->loaded != 0) {
        /* no installed file (portable builds, synthetic tests): DEMO records, not the installed file's values:
         * the two flying pets of the visuals routine fly (move type 0), the others collect (1) */
        static const int32_t items[] = {0x40, 0x41, 0x43, 0x50, 0x6a, 0x7b};
        memset(pp->p.table, 0, sizeof pp->p.table);
        for (int32_t i = 0; i < (int32_t)(sizeof items / sizeof items[0]); ++i) {
            mu_pet_info *r = &pp->p.table[i];
            r->seq = i;
            r->item = items[i];
            r->slot = 8;
            r->move = (uint8_t)(items[i] == 0x40 || items[i] == 0x41 ? 0 : 1);
            r->range = r->move ? 10.0f : 50.0f;
            r->follow = (uint8_t)(r->move == 0);
            r->scale = 0.5f;
            r->blend_mesh = -1;
            for (int k = 0; k < 5; ++k)
                r->speed[k] = 0.5f;
        }
    }
    return pp;
}

void mu_world_pets_free(mu_world_pets *pp)
{
    free(pp);
}

/* ---------------------------------------------------------------- owners */

static void sync_owners(mu_world_pets *pp, mu_world_helpers *w)
{
    for (int32_t i = 0; i < MU_WH_OWNERS; ++i) {
        const mu_hp_owner *o = &w->owners[i];
        mu_pet_owner *q = &pp->owners[i];
        q->live = o->live;
        q->kind = o->kind;
        q->action = o->action;
        q->key = (int16_t)w->who[i].key;
        memcpy(q->position, o->position, sizeof q->position);
        memcpy(q->angle, o->angle, sizeof q->angle);
        q->scale = 1.0f;   /* the character object's scale +0xa0 (1 for players) */
        q->buff_12 = o->buff_12;
        q->alt_pet = -1;
    }
}

void mu_world_pets_create(mu_world_pets *pp, mu_world_helpers *w, int32_t owner, int32_t item, int32_t model)
{
    if (owner < 0 || owner >= MU_WH_OWNERS)
        return;
    sync_owners(pp, w);
    pp->helpers = w;
    if (mu_pets_create(&pp->p, item, model, pp->owners[owner].position, owner, 0))
        pp->stats.created++;
}

void mu_world_pets_delete(mu_world_pets *pp, int32_t owner, int32_t item)
{
    int32_t before = pp->p.count;
    mu_pets_delete(&pp->p, owner, item);
    pp->stats.deleted += (uint32_t)(before - pp->p.count);
}

void mu_world_pets_owner_gone(mu_world_pets *pp, int32_t owner)
{
    for (int32_t i = pp->p.count - 1; i >= 0; --i)
        if (pp->p.list[i].object.owner == owner)
            mu_world_pets_delete(pp, owner, -1);
}

void mu_world_pets_step(mu_world_pets *pp, mu_world_helpers *w)
{
    pp->helpers = w;
    pp->clock += 40;
    sync_owners(pp, w);
    if (!pp->hero_applied && w->walk) {
        pp->hero_applied = 1;
        if (pp->hero_item >= 0)   /* DEMO: the inventory's CreatePet(item, 0x24e6 + index, position, hero, 0, 0) */
            mu_world_pets_create(pp, w, 0, pp->hero_item, MU_PET_MODEL_BASE + pp->hero_item - 0x1a00);
    }
    pp->inputs.hero = 0;
    pp->inputs.scene = 6;
    pp->inputs.helper_type = pp->hero_item;   /* the hero's helper slot entry +0x10 (the pet item) */
    pp->inputs.helper_92 = pp->inputs.helper_93 = 0;
    pp->inputs.world_time = (float)(pp->clock % 0x1000000u);
    pp->inputs.items = NULL;   /* DEMO: the ground items are not offered to the collectors */
    mu_pets_update(&pp->p, &pp->inputs);
    pp->stats.live = (uint32_t)pp->p.count;
    pp->stats.steps++;
}

/* ---------------------------------------------------------------- draw */

typedef struct draw_context {
    mu_world_pets *pp;
    mu_world_helpers *w;
    const mu_world_helpers_target *target;
    const mu_terrain_frustum *frustum;
    long drawn;
} draw_context;

static int r_frustum(void *c, float x, float y, float range)
{
    draw_context *d = c;
    if (!d->frustum)
        return 1;
    return mu_terrain_test_frustum_2d(d->frustum->x2d, d->frustum->y2d, 6, x, y, range);
}

static void r_draw(void *c, const mu_hp_object *o, int32_t a1, int32_t a2, int32_t a3, int32_t a4, int32_t a5)
{
    draw_context *d = c;
    (void)a2, (void)a3, (void)a4, (void)a5;
    if (mu_world_helpers_draw_object(d->w, d->target, o, a1)) {
        d->drawn++;
        d->pp->stats.drawn++;
    }
}

/* PoseBuilder on the model with the object's frame, angle and head angle (translate 1: the origin is the object
 * position; 0: model space, the skeletons). */
static void r_pose(void *c, const mu_hp_object *o, int32_t model, int translate)
{
    draw_context *d = c;
    mu_wh_model *m = mu_world_helpers_model(d->w, model);
    if (!m || !m->loaded)
        return;
    mu_model_params p = m->model.params;
    for (int k = 0; k < 3; ++k) {
        p.origin[k] = o->position[k];
        p.angles[k] = o->angle[k];
    }
    p.body_scale = o->scale;
    p.pose_translate = (uint8_t)(translate ? 1 : 0);
    mu_model_apply_params(&m->model, &p);
    mu_model_set_state(&m->model, o->action, o->frame, o->prior_frame, o->prior_action);
    mu_model_pose(&m->model);
}

static const float *r_bone_matrix(void *c, int32_t model, int32_t bone)
{
    draw_context *d = c;
    mu_wh_model *m = mu_world_helpers_model(d->w, model);
    if (!m || !m->loaded || bone < 0 || bone >= m->bmd.bone_count || bone >= MU_MODEL_MAX_BONES)
        return NULL;
    const float *bones = mu_model_bone_matrices(&m->model);
    return bones ? bones + 12 * bone : NULL;
}

static void r_sprite(void *c, int32_t bitmap, const float position[3], float scale, const float light[3],
                     const mu_hp_object *o)
{
    draw_context *d = c;
    (void)o;
    d->pp->stats.sprites++;
    if (d->w->particles)   /* CreateSprite(bitmap, position, scale, light, object, 0, 0, 4) */
        mu_world_particles_sprite(d->w->particles, bitmap, position, scale, light, -1, 0.0f, 0, 4);
}

static void r_particle(void *c, int32_t bitmap, const float position[3], const float angle[3], const float light[3],
                       int32_t subtype, float scale, const mu_hp_object *owner, int32_t arg8)
{
    draw_context *d = c;
    (void)owner, (void)arg8;
    d->pp->stats.particles++;
    if (d->w->particles && mu_world_particles_create(d->w->particles, bitmap, position, angle, light, subtype, scale))
        d->pp->stats.particles_kept++;
}

static void r_effect(void *c, int32_t type, const float position[3], const float angle[3], const float light[3],
                     const int32_t args[10])
{
    draw_context *d = c;
    d->pp->stats.effects++;
    if (d->w->particles)
        mu_world_particles_effect(d->w->particles, type, args[0], position, angle, light, -1, 0.0f, NULL);
}

static void r_remember(void *c, int32_t kind)
{
    draw_context *d = c;
    if (kind != -1)
        d->pp->stats.remembered++;
}

long mu_world_pets_draw(mu_world_pets *pp, mu_world_helpers *w, const mu_terrain_frustum *frustum,
                        const mu_world_helpers_target *target)
{
    pp->helpers = w;
    draw_context d = {pp, w, target, frustum, 0};
    mu_pet_render_host r;
    memset(&r, 0, sizeof r);
    r.context = &d;
    r.frustum = r_frustum;
    r.draw_object = r_draw;
    r.pose = r_pose;
    r.bone_matrix = r_bone_matrix;
    r.sprite = r_sprite;
    r.particle = r_particle;
    r.effect = r_effect;
    r.remember = r_remember;
    pp->stats.drawn = 0;
    mu_pets_render(&pp->p, &pp->inputs, &r);
    return d.drawn;
}

/* ---------------------------------------------------------------- reports */

void mu_world_pets_report_frame(const mu_world_pets *pp, FILE *out, int32_t frame)
{
    fprintf(out, "{\"pets_frame\": %d, \"pets\": %d, \"drawn\": %u", frame, pp->p.count, pp->stats.drawn);
    for (int32_t i = 0; i < pp->p.count; ++i) {
        const mu_pet *q = &pp->p.list[i];
        fprintf(out, ", \"pet%d\": [%d, %d, %d, %.2f, %.2f, %.2f, %.1f]", i, q->item, q->object.owner, q->state,
                (double)q->object.position[0], (double)q->object.position[1], (double)q->object.position[2],
                (double)q->object.angle[2]);
    }
    fprintf(out, "}\n");
}

void mu_world_pets_report_summary(const mu_world_pets *pp, FILE *out)
{
    fprintf(out, "{\"pets\": {\"petdata\": %d, \"steps\": %u, \"created\": %u, \"deleted\": %u, \"live\": %u,"
                 " \"sprites\": %u, \"particles\": %u, \"particles_kept\": %u, \"effects\": %u, \"remembered\": %u,"
                 " \"pickups\": %u, \"sounds\": %u, \"rand_calls\": %llu}}\n",
            pp->loaded, pp->stats.steps, pp->stats.created, pp->stats.deleted, pp->stats.live, pp->stats.sprites,
            pp->stats.particles, pp->stats.particles_kept, pp->stats.effects, pp->stats.remembered, pp->stats.pickups,
            pp->stats.sounds, (unsigned long long)pp->p.rand_calls);
}
