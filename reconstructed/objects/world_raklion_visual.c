#include "world_visual_internal.h"
/* Slots 0x38/0x3c (custom 0x00e949f8, after 0x00e96536) are Test Area 121's code: world_test_area_visual.c
 * (RENDER-WORLDS-RAKLION), through the class chain of world_slots2_visual.c. */

/* Complete slot 0x34, 0x00e946a8..0x00e949f8. No world predicate. */
int mu_raklion_visual(const uint8_t *o, int32_t i, int has_model,
                       mu_obj_rand_fn random, void *context, mu_obj_log *log)
{
    if (!has_model) return 0;
    const int32_t t = mu_obj_i32(o, MU_OBJF_TYPE);
    if (t != 0x46 && t != 0x50) return 0;
    const float blue[3] = {0.1f, 0.4f, 1.0f}, warm[3] = {0.7f, 0.2f, 0.1f};
    const float *light = t == 0x46 ? blue : warm;
    const int32_t choice = random(context) % 3;
    const int32_t kinds[3] = {0x8086, 0x8087, 0x8089};
    if (choice >= 0 && choice < 3)
        wv_particle(o, i, kinds[choice], choice == 1 ? 6 : 2, light, 0, log);
    wv_particle(o, i, 0x8086, 2, light, 0, log);
    return 1;
}
