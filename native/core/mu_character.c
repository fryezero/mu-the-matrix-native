/* Character assembly. See mu_character.h. */
#include "mu_character.h"

#include "../../reconstructed/actors/actors.h"

#include <stdio.h>
#include <stdlib.h>
#include <string.h>

#include "../../reconstructed/model-codec/character.h"
#include "../../reconstructed/record-math/record_math.h"

/* Light arguments of every transform call in 0x0139be7a: binary32 at
 * 0x01a7df0c (0.4), 0x01a7df18 (0.8) and 0x01a7df08 (0.2). */
#define LIGHT_AMBIENT 0.4f
#define LIGHT_SCALE 0.8f
#define LIGHT_MINIMUM 0.2f

void mu_character_default_params(mu_character_params *p)
{
    memset(p, 0, sizeof *p);
    p->scale = 0.9f;
    p->wing_scale = 0.9f;
    p->light[0] = p->light[1] = p->light[2] = 1.0f;
    p->lighting = 1;
}

static int fail(char *error, size_t size, const char *message, const char *path)
{
    if (error && size)
        snprintf(error, size, "%s: %s", path ? path : "", message);
    return 1;
}

static int load_model(const char *path, mu_bmd *bmd, mu_model *model, const mu_model_params *params, char *error,
                      size_t size)
{
    char reason[512];
    if (mu_bmd_load_file(path, bmd, reason, sizeof reason) != MU_BMD_OK)
        return fail(error, size, reason, path);
    if (mu_model_init(model, bmd, params, reason, sizeof reason) != MU_MODEL_OK) {
        mu_bmd_free(bmd);
        return fail(error, size, reason, path);
    }
    return 0;
}

int mu_character_init(mu_character *c, const char *player_path, const mu_model_params *model_params, char *error,
                      size_t error_size)
{
    memset(c, 0, sizeof *c);
    mu_character_default_params(&c->params);
    c->shared_bones = calloc(MU_MODEL_SHARED_BONE_BYTES, 1);
    c->shared_root = calloc(0x30, 1);
    c->shared_quaternions = calloc(MU_MODEL_SHARED_QUATERNION_BYTES, 1);
    c->player_bones = calloc(MU_MODEL_SHARED_BONE_BYTES, 1);
    if (!c->shared_bones || !c->shared_root || !c->shared_quaternions || !c->player_bones) {
        mu_character_free(c);
        return fail(error, error_size, "out of memory", player_path);
    }
    mu_model_params params;
    if (model_params)
        params = *model_params;
    else
        mu_model_default_params(&params);
    params.pose_translate = 0;   /* Player pose: keep root 0, translate 0 */
    if (load_model(player_path, &c->player_bmd, &c->player, &params, error, error_size)) {
        mu_character_free(c);
        return 1;
    }
    mu_model_relocate(&c->player, &c->player_bmd);
    mu_model_share(&c->player, c->shared_bones, c->shared_root, c->shared_quaternions);
    c->player_loaded = 1;
    c->player_bone_count = c->player_bmd.bone_count;
    for (int i = 0; i < MU_CHARACTER_ITEMS; ++i)
        c->items[i].link_bone = -1;
    c->items[MU_CHARACTER_WEAPON_ITEM(0)].link_bone = MU_CHARACTER_RIGHT_HAND_BONE;
    c->items[MU_CHARACTER_WEAPON_ITEM(1)].link_bone = MU_CHARACTER_LEFT_HAND_BONE;
    c->items[MU_CHARACTER_WING_ITEM].link_bone = MU_CHARACTER_BACK_BONE;
    return 0;
}

static void unload(mu_character_item *item)
{
    if (!item->loaded)
        return;
    mu_model_free(&item->model);
    mu_bmd_free(&item->bmd);
    mu_textures_free(&item->textures);
    free(item->bones);
    item->bones = NULL;
    item->loaded = 0;
}

void mu_character_free(mu_character *c)
{
    for (int i = 0; i < MU_CHARACTER_ITEMS; ++i)
        unload(&c->items[i]);
    if (c->player_loaded) {
        mu_model_free(&c->player);
        mu_bmd_free(&c->player_bmd);
    }
    free(c->shared_bones);
    free(c->shared_root);
    free(c->shared_quaternions);
    free(c->player_bones);
    memset(c, 0, sizeof *c);
}

int mu_character_set_item(mu_character *c, int index, const char *path, int no_textures, char *error,
                          size_t error_size)
{
    if (index < 0 || index >= MU_CHARACTER_ITEMS)
        return fail(error, error_size, "bad item slot", path);
    mu_character_item *item = &c->items[index];
    unload(item);
    if (!path)
        return 0;
    mu_model_params params;
    mu_model_default_params(&params);
    if (load_model(path, &item->bmd, &item->model, &params, error, error_size))
        return 1;
    mu_model_relocate(&item->model, &item->bmd);
    mu_model_share(&item->model, c->shared_bones, c->shared_root, c->shared_quaternions);
    snprintf(item->path, sizeof item->path, "%s", path);
    memset(&item->textures, 0, sizeof item->textures);
    if (!no_textures) {
        char directory[4096];
        mu_path_directory(path, directory, sizeof directory);
        mu_textures_load(&item->textures, &item->bmd, directory);
    }
    if (index >= MU_CHARACTER_PART_SLOTS) {
        item->bones = calloc((size_t)(item->bmd.bone_count ? item->bmd.bone_count : 1), 0x30);
        if (!item->bones) {
            unload(item);
            return fail(error, error_size, "out of memory", path);
        }
    }
    item->loaded = 1;
    return 0;
}

void mu_character_set_state(mu_character *c, uint16_t action, float frame, float prior_frame, uint16_t prior_action)
{
    mu_model_set_state(&c->player, action, frame, prior_frame, prior_action);
}

int mu_character_tick(mu_character *c, float speed, uint8_t *loop)
{
    return mu_model_tick(&c->player, speed, loop);
}

int mu_character_apply_player_speeds(mu_character *c)
{
    int unset = 0;
    for (int32_t a = 0; a < c->player_bmd.action_count; ++a) {
        float speed = mu_player_action_speed(a);
        if (speed == 0.0f) {
            speed = 0.25f;
            unset++;
        }
        uint8_t *record = mu_model_host(&c->player, c->player.actions + 16u * (uint32_t)a, 8);
        if (!record)
            continue;
        memcpy(record + 4, &speed, 4);
        if (mu_player_action_loop(a))
            record[0] = 1;
    }
    return unset;
}

float mu_character_action_speed(const mu_character *c, uint16_t action)
{
    float speed = 0.0f;
    if (action < c->player_bmd.action_count) {
        const uint8_t *record = mu_model_host(&c->player, c->player.actions + 16u * action + 4, 4);
        if (record)
            memcpy(&speed, record, 4);
    }
    return speed;
}

/* Model fields every slot copies from the object before its transform. */
static mu_model_params slot_params(const mu_character *c, const mu_model *model, float scale, const float origin[3])
{
    mu_model_params p = model->params;
    p.body_scale = scale;
    for (int k = 0; k < 3; ++k) {
        p.origin[k] = origin[k];
        p.color[k] = c->params.light[k];
        p.angles[k] = 0.0f;
    }
    p.head_angles[0] = p.head_angles[1] = 0.0f;
    p.lighting = c->params.lighting;
    p.light_override = c->player.params.light_override;   /* one global 0x01cf1048 for every model */
    p.transform_translate = 1;
    p.vertex_scale = 0.0f;
    p.light_ambient = LIGHT_AMBIENT;
    p.light_scale = LIGHT_SCALE;
    p.light_minimum = LIGHT_MINIMUM;
    p.height = 0.0f;
    return p;
}

static int attach(mu_character *c, mu_character_item *item, const float vector[3], float frame, float scale)
{
    float out[3];
    if (mu_model_rotation_position(&c->player, item->link_bone, vector, out) != MU_MODEL_OK)
        return MU_MODEL_ERROR;
    float origin[3];
    for (int k = 0; k < 3; ++k) {
        volatile float sum = c->params.position[k] + out[k];
        origin[k] = sum;
    }
    mu_model_params p = slot_params(c, &item->model, scale, origin);
    p.pose_translate = 1;
    if (c->params.world_items)
        p.lighting = 0;   /* 0x012bdb19 */
    mu_model_apply_params(&item->model, &p);
    mu_model_set_state(&item->model, item->action, frame, frame, 0);
    if (mu_model_pose_keep_root(&item->model) != MU_MODEL_OK)
        return MU_MODEL_ERROR;
    memcpy(item->bones, mu_model_bone_matrices(&item->model), 0x30u * (size_t)item->bmd.bone_count);
    return mu_model_transform_all(&item->model);
}

int mu_character_set_carry(mu_character *c, int index, int32_t mode, const uint32_t local[12], int32_t bone, float frame)
{
    if (index < MU_CHARACTER_PART_SLOTS || index >= MU_CHARACTER_ITEMS || mode < 0 || mode > 2)
        return MU_MODEL_ERROR;
    mu_character_item *item = &c->items[index];
    item->carry = mode;
    if (mode) {
        memcpy(item->carry_local, local, sizeof item->carry_local);
        item->carry_bone = bone;
        item->carry_frame = frame;
    }
    return MU_MODEL_OK;
}

/* Link-mode attachment (RenderLinkItem 0x012bd910, generic back path
 * 0x012c29e4): root = concat(owner bone, local), origin = object position. */
static int carry(mu_character *c, mu_character_item *item, float scale)
{
    if (item->carry == 1) {
        if (item->carry_bone < 0 || item->carry_bone >= c->player_bone_count)
            return MU_MODEL_ERROR;
        mu_pose_concat(c->player_bones + 12 * item->carry_bone, item->carry_local, c->shared_root);
    } else {
        memcpy(c->shared_root, item->carry_local, 48);
    }
    mu_model_params p = slot_params(c, &item->model, scale, c->params.position);
    p.pose_translate = 1;
    if (c->params.world_items)
        p.lighting = 0;   /* 0x012bdb19 */
    mu_model_apply_params(&item->model, &p);
    mu_model_set_state(&item->model, item->action, item->carry_frame, item->carry_frame, 0);
    if (mu_model_pose_keep_root(&item->model) != MU_MODEL_OK)
        return MU_MODEL_ERROR;
    memcpy(item->bones, mu_model_bone_matrices(&item->model), 0x30u * (size_t)item->bmd.bone_count);
    return mu_model_transform_all(&item->model);
}

int mu_character_update(mu_character *c)
{
    mu_model_params pp = c->player.params;
    for (int k = 0; k < 3; ++k)
        pp.angles[k] = c->params.angles[k];
    pp.head_angles[0] = c->params.head[0];
    pp.head_angles[1] = c->params.head[1];
    pp.pose_translate = 0;
    /* 0x017edd1d-style object copy: the Player model takes the object's
     * scale (+0xa0 -> +0x74) and position (+0x158 -> +0x78) before its pose. */
    pp.body_scale = c->params.scale;
    for (int k = 0; k < 3; ++k)
        pp.origin[k] = c->params.position[k];
    mu_model_apply_params(&c->player, &pp);
    if (mu_model_pose(&c->player) != MU_MODEL_OK)
        return MU_MODEL_ERROR;
    memcpy(c->player_bones, mu_model_bone_matrices(&c->player), 0x30u * (size_t)c->player_bone_count);
    for (int slot = MU_CHARACTER_PART_SLOTS - 1; slot >= 0; --slot) {
        mu_character_item *item = &c->items[slot];
        if (!item->loaded)
            continue;
        mu_model_params p = slot_params(c, &item->model, c->params.scale, c->params.position);
        mu_model_apply_params(&item->model, &p);
        if (mu_model_transform_all(&item->model) != MU_MODEL_OK)
            return MU_MODEL_ERROR;
    }
    static const float zero[3] = {0.0f, 0.0f, 0.0f}, wing[3] = {0.0f, 0.0f, 15.0f};
    for (int slot = 0; slot < MU_CHARACTER_WEAPON_SLOTS; ++slot) {
        mu_character_item *item = &c->items[MU_CHARACTER_WEAPON_ITEM(slot)];
        if (item->loaded && item->carry) {
            if (carry(c, item, c->params.scale) != MU_MODEL_OK)
                return MU_MODEL_ERROR;
            continue;
        }
        if (item->loaded && attach(c, item, zero, 0.0f, c->params.scale) != MU_MODEL_OK)
            return MU_MODEL_ERROR;
    }
    mu_character_item *item = &c->items[MU_CHARACTER_WING_ITEM];
    if (item->loaded && attach(c, item, wing, 2.0f, c->params.wing_scale) != MU_MODEL_OK)
        return MU_MODEL_ERROR;
    return MU_MODEL_OK;
}

int mu_character_bounds(const mu_character *c, float lo[3], float hi[3])
{
    int any = 0;
    for (int k = 0; k < 3; ++k) {
        lo[k] = 1e30f;
        hi[k] = -1e30f;
    }
    for (int i = 0; i < MU_CHARACTER_ITEMS; ++i) {
        const mu_character_item *item = &c->items[i];
        if (!item->loaded)
            continue;
        for (int32_t m = 0; m < item->bmd.mesh_count; ++m) {
            const float *v = mu_model_vertices(&item->model, m);
            for (int32_t j = 0; j < item->bmd.meshes[m].vertex_count; ++j)
                for (int k = 0; k < 3; ++k) {
                    float x = v[3 * j + k];
                    if (x < lo[k]) lo[k] = x;
                    if (x > hi[k]) hi[k] = x;
                    any = 1;
                }
        }
    }
    return any;
}

int mu_character_part_path(const char *game_root, int slot, uint8_t class_byte, char *out, size_t size)
{
    if (slot < MU_PART_HELM || slot > MU_PART_BOOTS)
        return 0;
    char name[64];
    if (!mu_character_part_file(mu_character_part_type(slot, class_byte), name, sizeof name))
        return 0;
    int written = snprintf(out, size, "%s/Data/Player/%s", game_root, name);
    return written > 0 && (size_t)written < size;
}
