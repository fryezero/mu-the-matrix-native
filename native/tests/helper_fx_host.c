/* Synthetic regression for native helper bone spaces and effect ownership. */
#include <math.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>

#include "../core/mu_world_helpers.h"
#include "../core/mu_particles.h"

int main(int argc, char **argv)
{
    if (argc != 2) return 2;
    mu_world *map = calloc(1, sizeof *map);
    mu_world_helpers *w = calloc(1, sizeof *w);
    mu_world_particles *p = calloc(1, sizeof *p);
    if (!map || !w || !p) return 2;
    char error[512];
    if (mu_world_helpers_open(w, argv[1], map, NULL, NULL, -1, 0, 0, 0, error, sizeof error) ||
        mu_world_particles_open(p, argv[1], map, 0, 0, 1, error, sizeof error)) return 2;
    mu_world_helpers_attach_particles(w, p);
    mu_hp_mount *m = &w->mounts.list[0];
    w->mounts.count = 1;
    m->live = m->has_model = m->object.live = m->object.visible = 1;
    m->cls = MU_HP_MOUNT_FENRIR;
    m->key = 0x7fff;
    m->model = m->object.type = 0x4ab;
    m->object.scale = 1.25f;
    m->object.alpha = 1.0f;
    m->object.position[0] = 12000.0f;
    m->object.position[1] = 14000.0f;
    m->object.position[2] = 200.0f;
    const float zero[3] = {0, 0, 0}, light[3] = {1, 1, 1};
    float expected[3], relative[3], world[3];
    const int32_t owner = mu_world_helpers_effect_id(w, &m->object);
    if (!mu_world_helpers_effect_bone(w, owner, 1, zero, expected) ||
        !w->h.host.bone_position(w, &m->object, m->model, "sit_pos_0", zero, relative, 0) ||
        !w->h.host.bone_position(w, &m->object, m->model, "sit_pos_0", zero, world, 1)) return 2;
    int spaces = 1, offset = 1, flash = 1;
    mu_hp_mount_offset(&w->h, m);
    for (int k = 0; k < 3; ++k) {
        spaces &= fabsf(world[k] - (relative[k] * m->object.scale + m->object.position[k])) < 0.001f;
        spaces &= fabsf(world[k] - expected[k]) < 0.001f;
        offset &= fabsf(m->offset[k] - relative[k]) < 0.001f;
    }
    /* Both owners use one cached model. Each lookup must pose its own object. */
    mu_hp_mount *other = &w->mounts.list[1];
    *other = *m;
    other->key++;
    other->object.position[0] += 700.0f;
    other->object.position[1] -= 900.0f;
    w->mounts.count = 2;
    float second[3], again[3];
    int owners = w->h.host.bone_position(w, &other->object, other->model, "sit_pos_0", zero, second, 1) &&
                 w->h.host.bone_position(w, &m->object, m->model, "sit_pos_0", zero, again, 1);
    for (int k = 0; k < 3; ++k) {
        owners &= fabsf(second[k] - world[k] - (other->object.position[k] - m->object.position[k])) < 0.001f;
        owners &= fabsf(again[k] - world[k]) < 0.001f;
    }
    /* The synthetic skeleton has seven bones; Fenrir can request bone 53. */
    float untouched[3] = {17.0f, 18.0f, 19.0f};
    const int bounds = !mu_world_helpers_effect_bone(w, owner, 53, zero, untouched) &&
                       !mu_world_helpers_effect_bone(w, owner, -1, zero, untouched) &&
                       untouched[0] == 17.0f && untouched[1] == 18.0f && untouched[2] == 19.0f;
    /* The fifth rand() of 0x4ac chooses bone 2 when r % 30 is 4. */
    uint32_t seed = 0;
    for (;; ++seed) {
        uint32_t state = seed;
        for (int k = 0; k < 5; ++k) state = state * 214013u + 2531011u;
        if (((state >> 16) & 0x7fffu) % 30u == 4u) break;
    }
    mu_world_helpers_effect_bone(w, owner, 2, zero, expected);
    p->rand_state = seed;
    if (!mu_world_particles_effect(p, 0x4ac, 0, m->object.position, zero, light, owner, 1.0f, NULL)) return 2;
    flash &= p->effects[0].owner == owner;
    for (int k = 0; k < 3; ++k) flash &= fabsf(p->effects[0].position[k] - expected[k]) < 0.001f;
    w->h.host.joint(w, 0x7f78, m->object.position, zero, &m->object, 40.0f);
    const int ring = p->joints[0].target == owner && p->joints[0].light[0] == 0.0f &&
                     p->joints[0].light[1] == 0.0f && p->joints[0].light[2] == 0.0f;
    /* SetEye's cached world positions feed the persistent coloured joint through the native dispatcher. */
    w->class_state_count = 1;
    w->class_keys[0] = m->key;
    memcpy(w->class_eyes[0][1], world, sizeof world);
    const float eye_light[3] = {0.6f, 0.4f, 0.9f};
    const int32_t eye_index = mu_world_particles_joint(p, 0x7fd6, world, world, zero, 0x43, owner,
                                                       30.0f, 0xffff, 0, 0, 0xffff, 0, eye_light);
    int eye = eye_index >= 0;
    if (eye) {
        const mu_jt_joint *j = &p->joints[eye_index];
        for (int k = 0; k < 3; ++k) eye &= j->position[k] == world[k] && j->light[k] == eye_light[k];
        w->class_eyes[0][1][0] += 100.0f;
        mu_world_particles_step(p, 40.0f);
        eye &= j->live && j->lifetime == 10 && j->position[0] == world[0] + 100.0f;
    }
    printf("{\"spaces\": %d, \"offset\": %d, \"flash\": %d, \"ring\": %d, \"owners\": %d, \"bounds\": %d, \"eye\": %d}\n",
           spaces, offset, flash, ring, owners, bounds, eye);
    mu_world_helpers_close(w);
    mu_world_particles_close(p);
    free(w); free(p); free(map);
    return spaces && offset && flash && ring && owners && bounds && eye ? 0 : 1;
}
