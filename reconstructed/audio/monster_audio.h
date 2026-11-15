/* AUDIO-005: complete scalar class sound owners; no replicated/event input. */
#ifndef MU_MONSTER_AUDIO_H
#define MU_MONSTER_AUDIO_H
#include <stdint.h>
#include <math.h>
typedef struct mu_monster_sound { uint32_t routine, site; int32_t id, object, loop; } mu_monster_sound;
typedef struct mu_monster_sound_plan { int known, handled, count; mu_monster_sound sound[4]; } mu_monster_sound_plan;
/* The class registry is selected by world, not the server monster class.
 * Keep the class handled result for dispatcher comparison. Combat callers
 * discard it and still request their shared voice. */
static inline mu_monster_sound_plan mu_monster_sound_select(int32_t world, int32_t model,
                                                            uint16_t action, float frame)
{
    mu_monster_sound_plan p = {0};
    uint32_t owner = 0;
#define MU_AUDIO_MONSTER_WORLD(w, r) if (world == (w)) owner = (r);
#define MU_AUDIO_MONSTER_OWNER(r, ret)
#define MU_AUDIO_MONSTER_RETURN(r, m, a, ret)
#define MU_AUDIO_MONSTER_SOUND(r,m,a,lo,hi,lc,hc,nan,n,site,id,obj,loop)
#include "monster_audio_table.inc"
#undef MU_AUDIO_MONSTER_WORLD
#undef MU_AUDIO_MONSTER_OWNER
#undef MU_AUDIO_MONSTER_RETURN
#undef MU_AUDIO_MONSTER_SOUND
    if (!owner) return p;
    p.known = 1;
#define MU_AUDIO_MONSTER_WORLD(w, r)
#define MU_AUDIO_MONSTER_OWNER(r, ret) if (owner == (r)) p.handled = (ret);
#define MU_AUDIO_MONSTER_RETURN(r, m, a, ret) if (owner == (r) && model == (m) && ((a) < 0 || action == (a))) p.handled = (ret);
#define MU_AUDIO_MONSTER_SOUND(r,m,a,lo,hi,lc,hc,nan,n,s,id,obj,loop) \
    if (owner == (r) && model == (m) && action == (a) && \
        ((nan) ? isnan(frame) : !isnan(frame) && ((lc) ? frame >= (lo) : frame > (lo)) && \
        ((hc) ? frame <= (hi) : frame < (hi)))) { \
        if (p.count < 4) p.sound[p.count++] = (mu_monster_sound){r,s,id,obj,loop}; \
    }
#include "monster_audio_table.inc"
#undef MU_AUDIO_MONSTER_WORLD
#undef MU_AUDIO_MONSTER_OWNER
#undef MU_AUDIO_MONSTER_RETURN
#undef MU_AUDIO_MONSTER_SOUND
    return p;
}
#endif
