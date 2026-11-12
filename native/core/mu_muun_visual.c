#include "mu_muun_visual.h"
#include "mu_data.h"
#include "mu_objects.h"
#include "../../reconstructed/movement/client_movement.h"
#include <math.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>

static float f32_at(const uint8_t *r, size_t offset)
{
    float value;
    memcpy(&value, r + offset, sizeof value);
    return value;
}

static int32_t i32_at(const uint8_t *r, size_t offset)
{
    int32_t value;
    memcpy(&value, r + offset, sizeof value);
    return value;
}

static void hide_all(mu_muun_visual *v)
{
    for (uint32_t i = 0; i < v->scene.instance_count; ++i)
        v->scene.instances[i].owner.visible = 0;
    v->visible = 0;
}

int mu_muun_visual_bone_available(int32_t bone, int32_t count, int posed)
{
    return bone == -1 || (posed && bone >= 0 && bone < count);
}

void mu_muun_visual_close(mu_muun_visual *v)
{
    if (!v) return;
    hide_all(v);
    mu_effect_scene_free(&v->scene);
    mu_muun_effects_free(v->table);
    free(v->mesh_records);
    free(v->mesh_textures);
    mu_textures_free(&v->textures);
    mu_model_free(&v->model);
    mu_bmd_free(&v->bmd);
    memset(v, 0, sizeof *v);
}

int mu_muun_visual_open(mu_muun_visual *v, const char *root, const char *lang, int32_t code,
                        const mu_mv_owner *owner, uint32_t generation, char *error, size_t error_size)
{
    memset(v, 0, sizeof *v);
    char path[2048], relative[1024], directory[2048];
    mu_data_table render = {0}, items = {0}, meshes = {0};
    mu_item item;
    const uint8_t *record = NULL;
    const char *stage = "render table";
    if (!owner || !owner->live || !mu_objects_resolve(root, "Data/Local/MuunRenderInfo.bmd", path, sizeof path) ||
        mu_data_load(path, NULL, &render) || render.result.status != MU_DATA_OK)
        goto fail;
    for (uint32_t k = 0; k < render.result.records; ++k) {
        const uint8_t *r = render.bytes + render.result.records_offset + (size_t)k * 612;
        if (i32_at(r, 0) == code) { record = r; break; }
    }
    stage = "appearance record";
    if (!record) goto fail;
    v->slot_kind = record[8];
    memcpy(v->secondary_name, record + 9, 256);
    v->secondary_name[256] = 0;
    v->base_body = record[0x258] != 0;
    v->shadow_alpha = f32_at(record, 0x254);
    if (!isfinite(v->shadow_alpha)) goto fail;
    v->info.code = code;
    v->info.item = i32_at(record, 4);
    v->info.scale = f32_at(record, 0x110);
    if (v->info.item < 0 || v->info.item > MU_ITEM_MODEL_LIMIT - MU_ITEM_MODEL_BASE ||
        !isfinite(v->info.scale) || v->info.scale <= 0.0f) goto fail;
    for (int k = 0; k < 3; ++k) {
        v->info.offset[k] = f32_at(record, 0x114 + 4 * (size_t)k);
        if (!isfinite(v->info.offset[k])) goto fail;
    }
    for (int k = 0; k < 5; ++k) {
        v->info.speed[k] = f32_at(record, 0x238 + 4 * (size_t)k);
        if (!isfinite(v->info.speed[k]) || v->info.speed[k] < 0.0f) goto fail;
    }
    stage = "item model record";
    if (!mu_objects_resolve(root, "Data/Local/Item.bmd", path, sizeof path) ||
        mu_data_load(path, NULL, &items) || items.result.status != MU_DATA_OK ||
        mu_item_model(&items, v->info.item + MU_ITEM_MODEL_BASE, &item) != 1) goto fail;
    stage = "model file/base actions";
    snprintf(relative, sizeof relative, "%s%s", item.folder, item.file);
    if (!mu_objects_resolve(root, relative, path, sizeof path) ||
        mu_bmd_load_file(path, &v->bmd, error, error_size) != MU_BMD_OK || v->bmd.action_count < 3) goto fail;
    mu_model_params params;
    mu_model_scene_params(&params);
    params.body_scale = v->info.scale;
    params.pose_translate = 0;   /* OBJECT bones are local; attachment adds position and scale once */
    params.transform_translate = 1;
    stage = "native model";
    if (mu_model_init(&v->model, &v->bmd, &params, error, error_size) != MU_MODEL_OK) goto fail;
    mu_path_directory(path, directory, sizeof directory);
    mu_textures_load(&v->textures, &v->bmd, directory);
    if (v->textures.missing) {
        mu_textures retry = {0};
        snprintf(relative, sizeof relative, "%s/texture", directory);
        if (!mu_textures_load(&retry, &v->bmd, relative) && retry.missing < v->textures.missing) {
            mu_textures_free(&v->textures);
            v->textures = retry;
        } else mu_textures_free(&retry);
    }
    /* MuunMeshInfo is keyed by the model item, not by the effect/render-info id. */
    stage = "mesh table";
    if (mu_objects_resolve(root, "Data/Local/MuunMeshInfo.bmd", path, sizeof path) &&
        !mu_data_load(path, NULL, &meshes) && meshes.result.status == MU_DATA_OK) {
        size_t count = meshes.result.records;
        v->mesh_records = calloc(count, 300);
        v->mesh_textures = calloc(count, sizeof *v->mesh_textures);
        if (count && (!v->mesh_records || !v->mesh_textures)) goto fail;
        for (uint32_t k = 0; k < meshes.result.records; ++k) {
            const uint8_t *r = meshes.bytes + meshes.result.records_offset + (size_t)k * 300;
            if (i32_at(r, 0) != v->info.item) continue;
            int32_t mesh = i32_at(r, 4);
            /* These later special models need their own caller branches, never this fallback. */
            if (v->info.item + MU_ITEM_MODEL_BASE == 0x2b7a || v->info.item + MU_ITEM_MODEL_BASE == 0x2b7b ||
                v->info.item + MU_ITEM_MODEL_BASE == 0x2b8d || v->info.item + MU_ITEM_MODEL_BASE == 0x2b8e ||
                v->info.item + MU_ITEM_MODEL_BASE == 0x2b90 || mesh < 0 || mesh >= v->bmd.mesh_count) {
                ++v->refused_meshes; continue;
            }
            int valid = 1;
            for (int off = 0x108; off <= 0x120; off += 4) valid &= isfinite(f32_at(r, (size_t)off));
            if (r[0x128] && r[0x129] && (fabsf(f32_at(r, 0x118)) < 0.001f ||
                fabsf(f32_at(r, 0x118)) > 1000.0f)) valid = 0;
            if (!valid) { ++v->refused_meshes; continue; }
            int32_t texture = -1;
            char name[257]; memcpy(name, r + 8, 256); name[256] = 0;
            if (strcmp(name, "default")) {
                const char *names[] = {name}, *directories[] = {directory};
                if (!mu_objects_resolve(root, "Data/Item/Texture", directory, sizeof directory)) {
                    ++v->refused_meshes; continue;
                }
                texture = 0xa000 + v->textures.extra_count;
                if (mu_textures_add_extras(&v->textures, &texture, directories, names, 1, 0x2601, 0x2900)) goto fail;
                if (!v->textures.slots[v->textures.count - 1]) { ++v->refused_meshes; continue; }
            }
            memcpy(v->mesh_records + (size_t)v->mesh_count * 300, r, 300);
            v->mesh_textures[v->mesh_count++] = texture;
        }
    }
    mu_data_free(&meshes);
    stage = "effect scene";
    if (mu_effect_scene_init(&v->scene, root, 0x4d55554eu) != MU_EFFECT_OK) goto fail;
    v->table = mu_muun_effects_load(lang);
    v->effects.scene = &v->scene;
    mu_mv_setup(&v->state, &v->info, owner);
    const mu_muun_slot slot = {1, owner->key, 0, 1, code, 1, owner->key};
    mu_muun_owner_refresh(&v->effects, v->table, &slot);
    int32_t kept = 0;
    for (int32_t k = 0; k < v->effects.count; ++k) {
        const mu_object_effect_record *r = &v->effects.records[k];
        if (!mu_muun_visual_bone_available(r->bone, v->bmd.bone_count, 1) ||
            (r->bone >= 0 && v->bmd.bones[r->bone].dummy)) {
            ++v->refused_bones;
            v->scene.instances[r->handle].owner.visible = 0;
        } else v->effects.records[kept++] = *r;
    }
    v->effects.count = kept;
    v->generation = generation;
    v->rng = 0x4d55554eu;
    v->loaded = v->live = 1;
    mu_data_free(&items);
    mu_data_free(&render);
    return 0;
fail:
    mu_data_free(&items);
    mu_data_free(&meshes);
    mu_data_free(&render);
    mu_muun_visual_close(v);
    snprintf(error, error_size, "Muun fixture %d: missing/invalid %s", code, stage);
    return 1;
}

static int lease(mu_muun_visual *v, const mu_mv_owner *owner, uint32_t generation)
{
    if (v->live && (!owner || !mu_mv_alive(v->loaded, owner != NULL, v->live, 6, owner->live, 1) ||
                    owner->key != v->state.key || generation != v->generation)) {
        v->live = 0;
        hide_all(v);
    }
    return v->live;
}

void mu_muun_visual_step(mu_muun_visual *v, const mu_mv_owner *owner, uint32_t generation)
{
    if (!lease(v, owner, generation)) return;
    int32_t action = v->state.state;
    if (action < 0 || action >= v->bmd.action_count || action >= 5) { v->live = 0; hide_all(v); return; }
    /* Authored deterministic fixture RNG; the real client's process-rand phase is unavailable. */
    v->rng = v->rng * 214013u + 2531011u;
    int32_t request = mu_mv_select(&v->state, &v->info, owner, v->bmd.actions[action].keys,
                                   (int32_t)((v->rng >> 16) & 0x7fffu));
    if (request >= 0)
        mu_move_set_action(&v->state.action, &v->state.prior_action, &v->state.frame, &v->state.prior_frame,
                           v->bmd.action_count, request);
    mu_model_set_state(&v->model, v->state.action, v->state.frame, v->state.prior_frame, v->state.prior_action);
    uint8_t loop = 0;
    mu_model_tick(&v->model, v->info.speed[v->state.state], &loop);
    v->state.frame = mu_model_frame(&v->model);
    v->state.prior_frame = mu_model_prior_frame(&v->model);
    v->state.prior_action = mu_model_prior_action(&v->model);
    mu_mv_follow(&v->state, &v->info, owner);
    ++v->steps;
}

void mu_muun_visual_frame(mu_muun_visual *v, const mu_mv_owner *owner, uint32_t generation, int frustum, float dt)
{
    if (!lease(v, owner, generation)) return;
    if (!mu_mv_visible(v->loaded, v->live, frustum, v->state.key, owner->key)) { hide_all(v); return; }
    mu_model_params p = v->model.params;
    p.body_scale = v->state.scale;
    memcpy(p.origin, v->state.position, sizeof p.origin);
    memcpy(p.angles, v->state.angle, sizeof p.angles);
    mu_model_apply_params(&v->model, &p);
    v->posed = mu_model_pose(&v->model) == MU_MODEL_OK && v->model.posed && mu_model_transform_all(&v->model) == MU_MODEL_OK;
    if (!v->posed) { ++v->refused_pose; hide_all(v); return; }
    v->visible = 1;
    for (int32_t k = 0; k < v->effects.count; ++k) {
        mu_effect_instance *i = &v->scene.instances[v->effects.records[k].handle];
        i->owner.flag5 = i->owner.flag6 = 1;
        i->owner.visible = 1;
        i->owner.action = v->state.action;
        i->owner.frame = v->state.frame;
        for (int c = 0; c < 3; ++c) i->owner.tint[c] = 1.0f;
    }
    mu_effect_object object = {0};
    memcpy(object.position, v->state.position, sizeof object.position);
    memcpy(object.angle, v->state.angle, sizeof object.angle);
    object.scale = v->state.scale;
    object.bones = mu_model_bone_matrices(&v->model);
    object.model_bones = v->bmd.bone_count;
    mu_muun_owner_update(&v->effects, &object, dt);
}

int mu_muun_visual_command(mu_muun_visual *v, int32_t category, const float target[3])
{
    int32_t action = mu_mv_command_action(category);
    if (!v->live || action < 0 || action >= v->bmd.action_count || !target ||
        !isfinite(target[0]) || !isfinite(target[1])) { ++v->refused_commands; return 0; }
    v->state.angle[2] = mu_create_angle(v->state.position[0], v->state.position[1], target[0], target[1]);
    v->state.state = action;
    mu_move_set_action(&v->state.action, &v->state.prior_action, &v->state.frame, &v->state.prior_frame,
                       v->bmd.action_count, action);
    ++v->command_draws;
    return 1;
}

void mu_muun_visual_draw(mu_muun_visual *v, float time, const mu_render_backend *backend, mu_draw_stats *stats)
{
    if (!v->visible || !v->posed) return;
    mu_draw_options o;
    mu_draw_default_options(&o);
    o.textures = &v->textures;
    o.time = time;
    if (v->base_body) mu_scene_draw_model(&v->model, &o, backend, stats);
    for (int32_t k = 0; k < v->mesh_count; ++k) {
        mu_mv_pass pass;
        mu_mv_mesh_pass(v->mesh_records + (size_t)k * 300, v->model.params.color, 1.0f, -1,
                       1.0f, v->mesh_textures[k], time, &pass);
        mu_draw_model_fields fields = {0};
        memcpy(fields.color, pass.color, sizeof fields.color);
        o.fields = &fields;
        o.mesh_plus_one = pass.mesh + 1;
        o.flags = (uint32_t)pass.flags;
        o.alpha = pass.alpha;
        o.select = pass.blend;
        o.color_scale = pass.light;
        o.texture = pass.texture;
        mu_scene_draw_model(&v->model, &o, backend, stats);
        ++v->mesh_draws;
    }
}
