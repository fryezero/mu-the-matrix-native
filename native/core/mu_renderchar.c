/* World-path item rendering. See mu_renderchar.h. */
#include "mu_renderchar.h"

#include <ctype.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <strings.h>

#include "../../reconstructed/renderchar/link_bones.h"
#include "../../reconstructed/model-codec/character.h"
#include "mu_lang.h"
#include "mu_particles.h"
#include "../../reconstructed/record-math/record_math.h"

int32_t mu_renderchar_type_from_path(const char *path)
{
    static const struct { const char *prefix; int group; } names[] = {
        {"sword", 0}, {"axe", 1}, {"mace", 2}, {"spear", 3}, {"bow", 4}, {"staff", 5}, {"shield", 6},
        {"helmmale", 7}, {"armormale", 8}, {"pantmale", 9}, {"glovemale", 10}, {"bootmale", 11}, {"wing", 12},
    };
    const char *base = strrchr(path, '/');
    base = base ? base + 1 : path;
    for (size_t i = 0; i < sizeof names / sizeof names[0]; ++i) {
        size_t n = strlen(names[i].prefix);
        if (strncasecmp(base, names[i].prefix, n) || !isdigit((unsigned char)base[n]))
            continue;
        long number = strtol(base + n, NULL, 10);
        if (number < 1 || number > 512)
            return -1;
        return 0xae6 + names[i].group * 512 + (int32_t)number - 1;
    }
    static const char *class_parts[] = {"helmclass", "armorclass", "pantclass", "gloveclass", "bootclass"};
    for (size_t i = 0; i < sizeof class_parts / sizeof class_parts[0]; ++i) {
        size_t n = strlen(class_parts[i]);
        if (strncasecmp(base, class_parts[i], n) || !isdigit((unsigned char)base[n]))
            continue;
        long number = strtol(base + n, NULL, 10);
        if (number < 1 || number > MU_CHARACTER_PART_STRIDE)
            return -1;
        return (int32_t)(MU_CHARACTER_PART_BASE + i * MU_CHARACTER_PART_STRIDE) + (int32_t)number - 1;
    }
    return -1;
}

static int32_t link_random(void *context)
{
    return mu_world_particles_rand(context);
}

long mu_renderchar_skin_effects(const mu_model *model, const float *bones, int32_t type, mu_world_particles *p)
{
    if (!p || !p->sprites || !model || !model->bmd || !bones)
        return 0;
    mu_rc_link_effect skin;
    if (mu_rc_skin_effect(type, p->world_time, &skin)) {
        if (model->bmd->bone_count < 1)
            return 0;
        float position[3];
        /* These RenderObjDraw callers transform without model scale, then add OBJECT position. */
        mu_pt_transform_position(bones, skin.offset, position, 0, 1.0f, model->params.origin);
        for (int k = 0; k < 3; ++k)
            position[k] += model->params.origin[k];
        uint64_t before = p->sprites->created;
        mu_world_particles_sprite(p, skin.sprite.bitmap, position, skin.sprite.scale, skin.sprite.light,
                                   MU_PT_NO_OWNER, 0.0f, 0, 4);
        return p->sprites->created != before;
    }
    return 0;
}

long mu_renderchar_link_effects(const mu_model *model, const float *bones, int32_t type, mu_world_particles *p)
{
    if (!p || !p->sprites || !model || !model->bmd || !bones)
        return 0;
    if (type == 0x389c || type == 0x389d)
        return mu_renderchar_skin_effects(model, bones, type, p);
    if (type == 0x0af9 || type == 0x12f9 || type == 0x14f0 || type == 0x12fb || type == 0x0ef4 || type == 0x0afc || type == 0x0afd || type == 0x0afe) {
        mu_rc_link_effect effects[20];
        int32_t n = 0;
        if (mu_rc_link_effects_time(type, p->world_time, link_random, p, effects, 20, &n) != MU_RC_OK)
            return 0;
        long created = 0;
        for (int32_t i = 0; i < n; ++i) {
            const mu_rc_link_effect *e = &effects[i];
            const mu_rc_link_sprite *s = &e->sprite;
            if (s->bone < 0 || s->bone >= model->bmd->bone_count || s->bone >= MU_MODEL_MAX_BONES)
                continue;
            float position[3];
            mu_pt_transform_position(bones + 12 * s->bone, e->offset, position, 1,
                                      model->params.body_scale, model->params.origin);
            if (e->particle) {
                created += mu_world_particles_create(p, s->bitmap, position, model->params.angles,
                                                       s->light, e->particle, s->scale);
            } else {
                uint64_t before = p->sprites->created;
                mu_world_particles_sprite(p, s->bitmap, position, s->scale, s->light,
                                           MU_PT_NO_OWNER, s->rotation, s->blend, s->axes);
                created += p->sprites->created != before;
            }
        }
        return created;
    }
    mu_rc_link_sprite sprites[10];
    int32_t count = 0;
    if (mu_rc_link_sprites(type, 0, sprites, 10, &count) != MU_RC_OK)
        return 0;
    mu_rc_link_sprites(type, mu_world_particles_rand(p), sprites, 10, &count);
    long created = 0;
    static const float zero[3] = {0};
    for (int32_t i = 0; i < count; ++i) {
        const mu_rc_link_sprite *s = &sprites[i];
        if (s->bone < 0 || s->bone >= model->bmd->bone_count || s->bone >= MU_MODEL_MAX_BONES)
            continue;
        float position[3];
        /* 0x0150e746 -> TransformPosition(…, translate=1). Native keep-root
         * poses keep scale/origin outside the saved bone matrices. */
        mu_pt_transform_position(bones + 12 * s->bone, zero, position, 1,
                                  model->params.body_scale, model->params.origin);
        uint64_t before = p->sprites->created;
        mu_world_particles_sprite(p, s->bitmap, position, s->scale, s->light,
                                   MU_PT_NO_OWNER, s->rotation, s->blend, s->axes);
        if (p->sprites->created != before)
            created++;
    }
    return created;
}

void mu_renderchar_default_env(mu_renderchar_env *env)
{
    memset(env, 0, sizeof *env);
    env->quality = 5;
    env->glow_color[0] = env->glow_color[1] = env->glow_color[2] = 1.0f;
    env->render_type = 2;
    env->lang = NULL; /* caller supplies its runtime tables */
}

static void fill_item(mu_rc_item *it, const mu_renderchar_glow *g, const mu_renderchar_env *env, const float light[3],
                      float alpha)
{
    memset(it, 0, sizeof *it);
    it->type = g->type;
    it->item_level = g->level << 3;
    it->option1 = g->option1;
    it->ext_option = g->ext;
    it->render_type = env->render_type;
    it->a10 = -1;
    it->a11 = -1;
    it->a12 = 3;
    it->alpha = alpha;
    for (int k = 0; k < 3; ++k) {
        it->light[k] = light[k];
        it->enchant[k] = env->glow_color[k];
    }
    /* PartObjectColor's EnchantEffect colour 0x010ffd7a(type - 0xae6): the first entry of the item code,
     * else the table's default (NATIVE-LANG-001) */
    if (!env->glow_override && g->type >= 0xae6)
        mu_lang_enchant_first(env->lang, g->type - 0xae6, it->enchant);
    it->object_alpha = alpha;
    it->blend_mesh = -1;
    it->time = env->time;
    it->quality = env->quality;
    it->has_record = g->has_record;
    it->kind_a = g->kind_a;
    it->kind_b = g->kind_b;
    it->item_kind = g->item_kind;
}

int mu_renderchar_draw_item(const mu_model *model, const mu_renderchar_glow *glow, const mu_renderchar_env *env,
                            const float light[3], float alpha, const mu_draw_options *base,
                            const mu_render_backend *backend, mu_draw_stats *draw_stats, mu_renderchar_stats *stats)
{
    mu_rc_item it;
    fill_item(&it, glow, env, light, alpha);
    mu_rc_model m = {{light[0], light[1], light[2]}, 0, {light[0], light[1], light[2]}, 0, 0};
    mu_rc_draw draws[32];
    int32_t count = 0;
    int status = glow->type < 0 ? MU_RC_SPECIAL : mu_rc_item_draws(&it, &m, draws, 32, &count);
    if (status != MU_RC_OK) {
        /* plain textured body (viewer fallback) */
        count = 1;
        memset(&draws[0], 0, sizeof draws[0]);
        draws[0].entry = MU_RC_ENTRY_BODY;
        draws[0].flags = env->render_type;
        draws[0].alpha = alpha;
        draws[0].blend_mesh = -1;
        draws[0].hidden = -1;
        draws[0].texture = -1;
        for (int k = 0; k < 3; ++k)
            draws[0].body_light[k] = draws[0].shade[k] = light[k];
        if (stats)
            stats->special++;
    }
    for (int32_t i = 0; i < count; ++i) {
        const mu_rc_draw *d = &draws[i];
        mu_draw_options o = *base;
        mu_draw_model_fields f;
        memcpy(f.color, d->body_light, sizeof f.color);
        f.hide_typed = d->level_field;
        memcpy(f.alt_color, d->shade, sizeof f.alt_color);
        f.alt_on_skin = d->flag_ca;
        f.flag_a5 = 0;
        o.fields = &f;
        o.flags = d->flags;
        o.alpha = d->alpha;
        o.select = d->blend_mesh;
        o.color_scale = d->blend_light;
        o.u_offset = d->u;
        o.v_offset = d->v;
        o.texture = d->texture;
        o.time = env->time;
        o.skip_mesh = d->entry == MU_RC_ENTRY_BODY ? d->hidden : -1;
        o.mesh_plus_one = d->entry == MU_RC_ENTRY_MESH ? d->mesh + 1 : 0;
        if (mu_scene_draw_model(model, &o, backend, draw_stats))
            return 1;
        if (stats)
            stats->passes++;
    }
    return 0;
}

int mu_renderchar_back_local(int32_t type, int32_t kind_b, int32_t right_hand, uint32_t local[12])
{
    return mu_rc_back_local(type, kind_b, right_hand, local);
}

int mu_renderchar_link_bones(int32_t model_index, int32_t *right, int32_t *left)
{
    for (size_t i = 0; i < sizeof mu_rc_link_bones / sizeof mu_rc_link_bones[0]; ++i)
        if (mu_rc_link_bones[i].type == model_index) {
            *right = mu_rc_link_bones[i].right;
            *left = mu_rc_link_bones[i].left;
            return 1;
        }
    return 0;
}

int mu_renderchar_host_init(mu_renderchar_host *host, mu_model *model)
{
    host->bones = calloc(MU_MODEL_SHARED_BONE_BYTES, 1);
    host->root = calloc(0x30, 1);
    host->quaternions = calloc(MU_MODEL_SHARED_QUATERNION_BYTES, 1);
    if (!host->bones || !host->root || !host->quaternions) {
        mu_renderchar_host_free(host);
        return 1;
    }
    mu_model_share(model, host->bones, host->root, host->quaternions);
    return 0;
}

void mu_renderchar_host_free(mu_renderchar_host *host)
{
    free(host->bones);
    free(host->root);
    free(host->quaternions);
    memset(host, 0, sizeof *host);
}

int mu_renderchar_attach_load(mu_renderchar_attachment *a, mu_renderchar_host *host, const char *path, int32_t bone,
                              int no_textures, char *error, size_t error_size)
{
    memset(a, 0, sizeof *a);
    char reason[512];
    if (mu_bmd_load_file(path, &a->bmd, reason, sizeof reason) != MU_BMD_OK) {
        snprintf(error, error_size, "%s: %s", path, reason);
        return 1;
    }
    mu_model_params params;
    mu_model_default_params(&params);
    if (mu_model_init(&a->model, &a->bmd, &params, reason, sizeof reason) != MU_MODEL_OK) {
        mu_bmd_free(&a->bmd);
        snprintf(error, error_size, "%s: %s", path, reason);
        return 1;
    }
    mu_model_relocate(&a->model, &a->bmd);
    mu_model_share(&a->model, host->bones, host->root, host->quaternions);
    if (!no_textures) {
        char directory[4096];
        mu_path_directory(path, directory, sizeof directory);
        mu_textures_load(&a->textures, &a->bmd, directory);
    }
    a->bone = bone;
    a->root = host->root;
    a->glow.type = -1;
    a->loaded = 1;
    return 0;
}

void mu_renderchar_attach_free(mu_renderchar_attachment *a)
{
    if (!a->loaded)
        return;
    mu_model_free(&a->model);
    mu_bmd_free(&a->bmd);
    mu_textures_free(&a->textures);
    memset(a, 0, sizeof *a);
}

int mu_renderchar_attach_update(mu_renderchar_attachment *a, mu_model *host_model, const float *host_bones,
                                const float position[3], float scale, const float light[3])
{
    static const float zero[3] = {0.0f, 0.0f, 0.0f};
    float out[3] = {0.0f, 0.0f, 0.0f};
    if (host_bones) {
        uint32_t local[12];
        int mode = mu_rc_back_local(a->glow.type, 0, 1, local);
        if (!mode)
            return MU_MODEL_ERROR;
        if (mode == 1)
            mu_pose_concat(host_bones + 12 * a->bone, local, a->root);   /* 0x012c29e4 */
        else
            memcpy(a->root, local, 48);
    } else if (mu_model_rotation_position(host_model, a->bone, zero, out) != MU_MODEL_OK) {
        return MU_MODEL_ERROR;
    }
    mu_model_params p = a->model.params;
    p.body_scale = scale;
    for (int k = 0; k < 3; ++k) {
        volatile float sum = position[k] + out[k];   /* 0x012c5c0c: object position + result */
        p.origin[k] = sum;
        p.color[k] = light[k];
        p.angles[k] = 0.0f;
    }
    p.head_angles[0] = p.head_angles[1] = 0.0f;
    p.pose_translate = 1;
    p.transform_translate = 1;
    p.vertex_scale = 0.0f;
    p.light_ambient = 0.4f;
    p.light_scale = 0.8f;
    p.light_minimum = 0.2f;
    p.height = 0.0f;
    p.lighting = 0;   /* 0x012bdb19: the item model's lighting flag is cleared */
    mu_model_apply_params(&a->model, &p);
    mu_model_set_state(&a->model, 0, 0.0f, 0.0f, 0);
    if (mu_model_pose_keep_root(&a->model) != MU_MODEL_OK)
        return MU_MODEL_ERROR;
    return mu_model_transform_all(&a->model);
}
