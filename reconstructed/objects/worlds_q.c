/* RENDER-WORLDS-Q dispatch by world. */
#include "worlds_q.h"
#include "worlds_s.h"

int mu_worlds_q_owns(int32_t world)
{
    /* World 92 has its own class (0x01aa6154) although Acheron's predicate also accepts it. */
    return world == 91 || world == 112 || world == 122 || (world >= 123 && world <= 127) ||
           world == 95;   /* RENDER-WORLDS-S: Debenter on the same inputs */
}

int mu_worlds_q_create(uint8_t *o, int32_t index, const mu_q_inputs *in, mu_obj_log *log)
{
    if (in->world == 91 || in->world == 92) return mu_acheron_create(o, in);
    if (in->world == 95) return mu_debenter_create(o, index, in, log);
    if (in->world == 112) return mu_ferea_create(o, in);
    if (in->world == 122) return mu_swamp_darkness_create(o, in);
    return mu_kubera_create(o, index, in, log);
}

int mu_worlds_q_move(uint8_t *o, int32_t index, const mu_q_inputs *in, mu_obj_log *log)
{
    if (in->world == 91 || in->world == 92) return mu_acheron_move(o, index, in, log);
    if (in->world == 95) return mu_debenter_move(o, index, in, log);
    if (in->world == 112) return mu_ferea_move(o, index, in, log);
    if (in->world == 122) return mu_swamp_darkness_move(o, in);
    return mu_kubera_move(o, index, in, log);
}

int mu_worlds_q_visual(const uint8_t *o, int32_t index, int model_present, const mu_q_inputs *in, mu_obj_log *log)
{
    if (in->world == 91 || in->world == 92) return mu_acheron_visual(o, index, in, log);
    if (in->world == 95)   /* type 9 stores its bone points in the object; the host passes a writable image */
        return model_present ? mu_debenter_visual((uint8_t *)(uintptr_t)o, index, in, log) : 0;
    if (in->world == 122) return mu_swamp_darkness_visual(o, index, model_present, in, log);
    if (in->world >= 123 && in->world <= 127) return mu_kubera_visual(o, index, model_present, in, log);
    if (in->world == 112) return mu_ferea_visual(o, index, model_present, in, log);
    return -1;
}
