/* RENDER-EFFECTS-018: the Muun effect table through the production loader (mu_muun_effects), the slot refresh
 * (0x009af6f6 then 0x009af699 / 0x0114203d) and the OBJECT's per-frame update 0x0129f671, with a synthetic Muun
 * OBJECT (own bone transforms +0x318, not in a sector list). argv[1]: a game root whose Data/Effect holds the
 * templates; argv[2]: a lang directory with muuneffects.tsv. Prints one JSON line per code of the table (or of the
 * codes given after argv[2]) and a summary line. */
#include "../core/mu_muun_effects.h"
#include "../core/mu_effect_scene.h"
#include <assert.h>
#include <math.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>

enum { BONES = 60, STEPS = 30 };

static float bones[12 * BONES], shared[12 * 64];

static void pose(float t)
{
    for (int b = 0; b < BONES; ++b) {   /* rows of a turned, offset bone frame (a fixture pose) */
        float *m = bones + 12 * b;
        const float a = 0.05f * (float)b + t;
        m[0] = cosf(a); m[1] = -sinf(a); m[2] = 0; m[3] = 3.0f * (float)b;
        m[4] = sinf(a); m[5] = cosf(a);  m[6] = 0; m[7] = -2.0f * (float)b;
        m[8] = 0;       m[9] = 0;        m[10] = 1; m[11] = 40.0f + (float)b;
    }
}

static int same16(const float *a, const float *b)
{
    return memcmp(a, b, 16 * sizeof(float)) == 0;
}

int main(int argc, char **argv)
{
    assert(argc >= 3);
    mu_muun_effects *table = mu_muun_effects_load(argv[2]);
    if (!table) {
        printf("{\"table\": false}\n");
        return 0;
    }
    int32_t codes[64], ncodes = 0;
    for (int k = 3; k < argc && ncodes < 64; ++k)
        codes[ncodes++] = (int32_t)strtol(argv[k], NULL, 10);
    for (int32_t k = 0; k < table->count && argc == 3 && ncodes < 64; ++k)
        if (!ncodes || codes[ncodes - 1] != table->entries[k].code)
            codes[ncodes++] = table->entries[k].code;
    printf("{\"table\": true, \"entries\": %d, \"codes\": %d}\n", table->count, ncodes);

    mu_effect_scene *scene = calloc(1, sizeof *scene);
    assert(mu_effect_scene_init(scene, argv[1], 0x018u) == MU_EFFECT_OK);
    for (int k = 0; k < 12 * 64; ++k)
        shared[k] = (float)(k % 7) - 3.0f;
    mu_effect_object obj;
    memset(&obj, 0, sizeof obj);
    obj.position[0] = 12800.0f; obj.position[1] = 13000.0f; obj.position[2] = 180.0f;
    obj.angle[2] = 45.0f;
    obj.scale = 1.2f;
    obj.in_sector = 0;   /* a Muun OBJECT is not a map object */
    obj.bones = bones;
    obj.model_bones = BONES;
    obj.shared = shared;
    long total_requested = 0, total_invalid = 0, total_attached = 0, total_updates = 0, placed = 0;
    for (int32_t c = 0; c < ncodes; ++c) {
        mu_muun_owner owner;
        memset(&owner, 0, sizeof owner);
        owner.scene = scene;
        const mu_muun_slot slot = {1, 77, 0, 1, codes[c], 1, 77};
        const int attached = mu_muun_owner_refresh(&owner, table, &slot);
        int matrices = 1;
        for (int s = 0; s < STEPS; ++s) {
            pose(0.1f * (float)s);
            mu_muun_owner_update(&owner, &obj, 0.1f);
            for (int32_t r = 0; r < owner.count; ++r) {   /* the update's external matrix for every record */
                float expect[16];
                if (mu_object_effect_matrix(expect, &owner.records[r], &obj))
                    matrices &= same16(expect, scene->instances[owner.records[r].handle].external) &&
                                scene->instances[owner.records[r].handle].has_external;
            }
        }
        float x = 0, y = 0, z = 0;
        if (owner.count) {   /* where the first record's effect sits after the steps */
            const float *m = scene->instances[owner.records[0].handle].external;
            x = m[12]; y = m[13]; z = m[14];
        }
        placed += matrices;
        printf("{\"code\": %d, \"attached\": %d, \"requested\": %ld, \"invalid\": %ld, \"records\": %d, "
               "\"updates\": %ld, \"matrices\": %s, \"bones\": [", codes[c], attached, owner.requested,
               owner.invalid, owner.count, owner.updates, matrices ? "true" : "false");
        for (int32_t r = 0; r < owner.count; ++r)
            printf("%s[%d, %d, %.1f]", r ? ", " : "", owner.records[r].bone, owner.records[r].follow,
                   (double)owner.records[r].template_scale);
        printf("], \"at\": [%.1f, %.1f, %.1f]}\n", (double)x, (double)y, (double)z);
        total_requested += owner.requested;
        total_invalid += owner.invalid;
        total_attached += owner.attached;
        total_updates += owner.updates;
    }

    /* the gate and the clear on one fixture code: a foreign owner key, an inactive slot and no record refuse;
     * a refresh clears the list first; timed records expire */
    mu_muun_owner owner;
    memset(&owner, 0, sizeof owner);
    owner.scene = NULL;   /* requests only */
    const int32_t code = codes[0];
    mu_muun_slot slot = {1, 5, 0, 1, code, 1, 6};
    const int foreign = mu_muun_owner_refresh(&owner, table, &slot);
    slot.key = 5; slot.active = 0;
    const int inactive = mu_muun_owner_refresh(&owner, table, &slot);
    slot.active = 1; slot.has_info = 0;
    const int no_info = mu_muun_owner_refresh(&owner, table, &slot);
    slot.has_info = 1;
    const int ok1 = mu_muun_owner_refresh(&owner, table, &slot);
    const int32_t first = owner.count;
    const int ok2 = mu_muun_owner_refresh(&owner, table, &slot);
    const int32_t second = owner.count;
    for (int32_t r = 0; r < owner.count; ++r) {
        owner.records[r].timed = 1;
        owner.records[r].lifetime = 0.25f;
    }
    obj.bones = NULL;
    for (int s = 0; s < 3; ++s)
        mu_muun_owner_update(&owner, &obj, 0.1f);
    printf("{\"requested\": %ld, \"invalid\": %ld, \"attached\": %ld, \"updates\": %ld, \"placed\": %ld, "
           "\"gate\": [%d, %d, %d, %d, %d], \"refresh\": [%d, %d], \"cleared\": %ld, \"expired\": %ld, "
           "\"left\": %d, \"scaled\": %ld}\n", total_requested, total_invalid, total_attached, total_updates, placed,
           foreign, inactive, no_info, ok1, ok2, first, second, owner.cleared, owner.expired, owner.count,
           owner.scaled);
    mu_effect_scene_free(scene);
    free(scene);
    mu_muun_effects_free(table);
    return 0;
}
