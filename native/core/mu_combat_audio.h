/* AUDIO-002C: original SND_Play provenance for the bounded combat services.
 * The deciding combat routines retain their gates and RNG consumption. */
#ifndef MU_COMBAT_AUDIO_H
#define MU_COMBAT_AUDIO_H
#include "../session/mu_audio_cue.h"
typedef struct mu_combat_audio { uint32_t routine, site; int32_t id; } mu_combat_audio;
enum { MU_COMBAT_AUDIO_SHOCK, MU_COMBAT_AUDIO_DIE, MU_COMBAT_AUDIO_ATTACK };
static inline mu_combat_audio mu_combat_voice_sound(int kind, int monster, int32_t id)
{
    mu_combat_audio d = {0,0,id};
    if (id < 0) return d;
    if (kind == MU_COMBAT_AUDIO_SHOCK) {
        d.routine=0x0138f92fu;
        if (id==0x7b) d.site=0x0138fbdau;
        else if (monster) d.site=0x0138fc68u;
        else if (id==0x1c6) d.site=0x0138fcc5u;
        else if (id>=0x69 && id<=0x6b) d.site=0x0138fcf5u;
        else if (id>=0x6d && id<=0x6e) d.site=0x0138fd2bu;
    } else if (kind == MU_COMBAT_AUDIO_DIE) {
        d.routine=0x01393a61u;
        if (id==0x5e || id==0x5f) d.site=0x01394351u;
        else if (monster) d.site=0x013943e5u;
        else if (id==0x1c7) d.site=0x0139441eu;
        else if (id==0x6c) d.site=0x0139442fu;
        else if (id==0x6e) d.site=0x01394440u;
        else if (id==0x2b9) d.site=0x01394464u;
    } else if (kind == MU_COMBAT_AUDIO_ATTACK) {
        d.routine=0x01392bdeu;
        if (monster) d.site=0x01393917u;
        else if (id==0x55) d.site=0x01393939u;
        else if (id==0x56) d.site=0x0139395bu;
        else if (id==0x76) d.site=0x013939a3u;
        else if (id==0x3e) d.site=0x013939ebu;
        else if (id==0x3c || id==0x3d) d.site=0x01393a3fu;
    }
    return d;
}
static inline mu_combat_audio mu_combat_extra_shock_sound(int32_t model, float played, int32_t primary)
{
    mu_combat_audio d={0x0138f92fu,0,-1};
    if (model==0x7e2 && primary>=0 && played==0.0f) { d.site=0x0138fe5eu;d.id=0x86; }
    return d;
}
/* SetPlayerAttack's model-slot tail, same slot pair as the hurt voice. */
static inline int32_t mu_combat_monster_attack(int world, float played, int has_model, int kind, int16_t slot2, int16_t slot3, int32_t random)
{
    if (world==0x49 || !(played==0.0f) || !has_model || slot2==-1) return -1;
    return 0xd2 + (kind==9 ? 5 : 0) + (random%2 ? slot3 : slot2);
}
/* Native timing is the existing visual attack start/end. These fragments are
 * compared separately from the whole receive/MoveCharacter routines. */
static inline mu_combat_audio mu_combat_skill_sound(int32_t skill, int end, int32_t caster_class, int32_t special_state)
{
    mu_combat_audio d={end ? 0x013a763eu : 0x01253a92u,0,-1};
    if ((!end && (skill==26 || skill==27 || skill==28) && caster_class==0x4d) ||
        (end && skill==41 && special_state==3)) return d;
    if (!end) {
        switch (skill) {
        case 19: d.site=0x01255f1cu;d.id=0x70;break;
        case 20: d.site=0x01255f4bu;d.id=0x71;break;
        case 21: d.site=0x01255f7au;d.id=0x72;break;
        case 22: d.site=0x01255fa9u;d.id=0x73;break;
        case 23: d.site=0x01256011u;d.id=0x73;break;
        case 26: case 27: case 28: d.site=0x01255962u;d.id=0x6f;break;
        }
    } else {
        switch (skill) {
        case 1: d.site=0x013b0099u;d.id=0x22;break;
        case 2: d.site=0x013b0101u;d.id=0x42;break;
        case 4: d.site=0x013b03ebu;d.id=0x42;break;
        case 7: d.site=0x013afe5cu;d.id=0x78;break;
        case 9: d.site=0x013ad00bu;d.id=0x75;break;
        case 10: d.site=0x013abc4bu;d.id=0x77;break;
        case 11: d.site=0x013b063eu;d.id=0x76;break;
        case 12: d.site=0x013ac92eu;d.id=0x7a;break;
        case 17: d.site=0x013b0e08u;d.id=0x76;break;
        case 41: d.site=0x013abb36u;d.id=0x73;break;
        case 42: d.site=0x013a954du;d.id=0x95;break;
        }
    }
    return d;
}
static inline mu_combat_audio mu_combat_effect_sound(int32_t id)
{
    mu_combat_audio d={0x013c0f19u,id==0x582 ? 0x013c42eeu : 0,id};
    return d;
}
static inline void mu_combat_audio_emit(mu_session *s, mu_combat_audio d, int16_t key)
{
    if (d.site && d.id>=0) mu_session_sound_emit(s,d.routine,d.site,d.id,key,0);
}
#endif
