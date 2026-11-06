/* RENDER-WORLDS-Q dispatch by world. */
#include "worlds_q.h"
#include "worlds_s.h"
#include "worlds_s2.h"

int mu_worlds_q_owns(int32_t world)
{
    return world == 91 || world == 112 || world == 122 || (world >= 123 && world <= 127) ||
           world == 95 ||   /* RENDER-WORLDS-S: Debenter on the same inputs */
           world == 110 || world == 92 || world == 96 || world == 111;   /* RENDER-WORLDS-S2: Nars, Arca War */
}

/* RENDER-WORLDS-S2: the Arca War class (worlds 92, 96, 111 here; 101 is on Uruk's inputs) forwards to its base
 * world's class, which runs with the Arca world. */
typedef struct q_arca {
    uint8_t *o;
    int32_t index;
    int model_present;
    const mu_q_inputs *in;
    mu_obj_log *log;
} q_arca;
static int q_arca_forward(void *context, int32_t slot, int32_t base)
{
    const q_arca *a = context;
    if (slot == MU_ARCA_CREATE_SLOT)
        return base == 91 ? mu_acheron_create(a->o, a->in) : base == 95 ? mu_debenter_create(a->o, a->index, a->in, a->log)
             : base == 110 ? mu_nars_create(a->o, a->index, a->in, a->log) : 0;
    if (slot == MU_ARCA_MOVE_SLOT)
        return base == 91 ? mu_acheron_move(a->o, a->index, a->in, a->log) : base == 95 ? mu_debenter_move(a->o, a->index, a->in, a->log)
             : base == 110 ? mu_nars_move(a->o, a->index, a->in, a->log) : 0;
    if (base == 91) return mu_acheron_visual(a->o, a->index, a->in, a->log);   /* as the direct dispatch below */
    if (!a->model_present) return 0;
    return base == 95 ? mu_debenter_visual(a->o, a->index, a->in, a->log)
         : base == 110 ? mu_nars_visual(a->o, a->index, a->in, a->log) : 0;
}
static int arca_q(int32_t world) { return world == 92 || world == 96 || world == 111; }

int mu_worlds_q_create(uint8_t *o, int32_t index, const mu_q_inputs *in, mu_obj_log *log)
{
    if (arca_q(in->world)) {
        q_arca a = {o, index, 1, in, log};
        return mu_arca_create(o, in->world, mu_arca_base_world(in->world), q_arca_forward, &a);
    }
    if (in->world == 91) return mu_acheron_create(o, in);
    if (in->world == 95) return mu_debenter_create(o, index, in, log);
    if (in->world == 110) return mu_nars_create(o, index, in, log);
    if (in->world == 112) return mu_ferea_create(o, in);
    if (in->world == 122) return mu_swamp_darkness_create(o, in);
    return mu_kubera_create(o, index, in, log);
}

int mu_worlds_q_move(uint8_t *o, int32_t index, const mu_q_inputs *in, mu_obj_log *log)
{
    if (arca_q(in->world)) {
        q_arca a = {o, index, 1, in, log};
        return mu_arca_move(in->world, mu_arca_base_world(in->world), q_arca_forward, &a);
    }
    if (in->world == 91) return mu_acheron_move(o, index, in, log);
    if (in->world == 95) return mu_debenter_move(o, index, in, log);
    if (in->world == 110) return mu_nars_move(o, index, in, log);
    if (in->world == 112) return mu_ferea_move(o, index, in, log);
    if (in->world == 122) return mu_swamp_darkness_move(o, in);
    return mu_kubera_move(o, index, in, log);
}

int mu_worlds_q_visual(const uint8_t *o, int32_t index, int model_present, const mu_q_inputs *in, mu_obj_log *log)
{
    /* Debenter type 9, Nars type 26 and the Arca forwards write the object; the host passes a writable image. */
    uint8_t *w = (uint8_t *)(uintptr_t)o;
    if (arca_q(in->world)) {
        q_arca a = {w, index, model_present, in, log};   /* 0x59b without a model: no bones, refused */
        return mu_arca_visual(o, index, in->world, mu_arca_base_world(in->world),
                              in->handler ? in->handler->arca_stage : 0, model_present ? in->bone : NULL,
                              in->context, q_arca_forward, &a, log);
    }
    if (in->world == 91) return mu_acheron_visual(o, index, in, log);
    if (in->world == 95) return model_present ? mu_debenter_visual(w, index, in, log) : 0;
    if (in->world == 110) return model_present ? mu_nars_visual(w, index, in, log) : 0;
    if (in->world == 122) return mu_swamp_darkness_visual(o, index, model_present, in, log);
    if (in->world >= 123 && in->world <= 127) return mu_kubera_visual(o, index, model_present, in, log);
    if (in->world == 112) return mu_ferea_visual(o, index, model_present, in, log);
    return -1;
}

int32_t mu_worlds_q_visual_bones(int32_t world, int32_t type)
{
    if (arca_q(world) && mu_arca_visual_bones(type) >= 0) return mu_arca_visual_bones(type);
    const int32_t base = arca_q(world) ? mu_arca_base_world(world) : world;
    return base == 91 ? mu_acheron_visual_bones(type) : base == 95 ? mu_debenter_visual_bones(type) :
           base == 110 ? mu_nars_visual_bones(type) : -1;
}
