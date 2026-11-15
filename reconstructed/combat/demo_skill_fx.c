#include "demo_skill_fx.h"
#include <string.h>

int mu_skill30_select(int32_t skill, int32_t base)
{
    /* Master aliases are explicit selector inputs. No blanket brand routing. */
    if (skill == base)
        return base == 24 || base == 48 || base == 51 || base == 52 || base == 344;
    return (skill == 416 && base == 52) || (skill == 424 && base == 51);
}
static mu_sfx_call *request(mu_skill30_plan *p, const mu_skill30_input *s, int routine, int type, int sub)
{
    mu_sfx_call *c = &p->calls[p->count++].visual;
    c->routine = routine; c->type = type; c->subtype = sub; c->owner = s->owner;
    memcpy(c->position, s->position, sizeof c->position);
    memcpy(c->angle, s->angle, sizeof c->angle);
    memcpy(c->light, s->light, sizeof c->light);
    c->range = -1; c->arg7 = -1;
    return c;
}
static void arrow(mu_skill30_plan *p, const mu_skill30_input *s, int flag)
{
    mu_sfx_call *c = request(p, s, MU_SKILL30_ARROW, s->skill, flag);
    c->range = s->learned_index;
    if (flag) c->type = 0;
}
int mu_skill30_plan_cast(mu_skill30_input *s, int end, mu_skill30_plan *p)
{
    memset(p, 0, sizeof *p); p->limit = 15; p->target_index = -1;
    if (!mu_skill30_select(s->skill, s->base)) return 0;
    if (!end) {
        if (s->base == 344) s->attack_time = 15; /* 0x0139b2fd */
        if (s->base == 48 && s->attack_time > 9 && s->model == 0xa91 &&
            (s->action == 0x9c || s->action == 0x11d)) s->attack_time = 15;
        if (s->base == 52) { /* 0x01399ca2..0x01399d80 */
            if (s->model == 0xa91 && s->action >= 0x6f && s->action < 0x133 && s->frame >= 5.0f) {
                s->prior_frame = 4.0f; s->frame = 5.0f;
            }
            if (s->attack_time == 3) {
                request(p, s, MU_SFX_CALL_EFFECT, 0x7fd0, 0);
                request(p, s, MU_SFX_CALL_SOUND, 0x81, 0);
                p->calls[p->count-1].site = 0x01399d6e;
            }
            p->limit = 5;
        }
        return 1;
    }
    if (s->base == 344) { /* 0x013a9f25..0x013aa064, light is a destination point */
        s->light[0] = ((float)s->tile[0] + 0.5f) * 100.0f;
        s->light[1] = ((float)s->tile[1] + 0.5f) * 100.0f;
        s->light[2] = s->position[2];
        request(p, s, MU_SFX_CALL_EFFECT, 0x583, 0);
    } else if (s->base == 48) { /* 0x013aa0e1..0x013aa2af */
        for (int n = 0; n < 36; ++n) {
            mu_sfx_call *c = request(p, s, MU_SFX_CALL_JOINT, 0x7fd3, 2);
            c->position[2] += 100.0f;
            memcpy(c->target, c->position, sizeof c->target);
            c->angle[0] = -10.0f; c->angle[1] = 0.0f; c->angle[2] = (float)n * 10.0f;
            c->scale = 60.0f; c->arg7 = 0;
            if (n % 20 == 0) {
                c = request(p, s, MU_SFX_CALL_EFFECT, 0x7f84, 4);
                c->angle[0] = -10.0f; c->angle[1] = 0.0f; c->angle[2] = (float)n * 10.0f;
            }
        }
        request(p, s, MU_SFX_CALL_SOUND, 0x7f, 0);
        p->calls[p->count-1].site = 0x013aa2a7;
        p->calls[p->count-1].visual.owner = -1;
    } else {
        if (s->base == 51) p->target_index = s->target_index;
        if (s->base == 24) arrow(p, s, 1); /* intentional fallthrough at 0x013af9fe */
        arrow(p, s, 0);
    }
    return 1;
}


int mu_skill32_select(int32_t skill, int32_t base)
{
    return skill == base && (base == 18 || (base >= 30 && base <= 36) || base == 44 || base == 49);
}

int mu_skill32_action(int32_t skill, int32_t class_byte, const mu_skill32_context *c)
{
    int cls = class_byte & 15;
    if (skill == 18) return cls == 1 && c->shield ? 0xd7 : -1;
    if (skill == 44) return cls == 1 ? 0x98 : -1;
    if (skill == 49) return cls == 1 && c->mount ? 0xf9 : -1;
    if (skill >= 30 && skill <= 36) return cls == 2 ? 0xa5 : -1;
    if (skill == 24 || skill == 51 || skill == 52 || skill == 416 || skill == 424) {
        if (cls != 2 || (c->bow_kind != 1 && c->bow_kind != 2)) return -1;
        int penetration = skill == 52 || skill == 416;
        if (penetration) return (c->bow_kind == 1 ? 0x93 : 0x94) + (c->wing != -1 ? 2 : 0);
        return (c->bow_kind == 1 ? 0x7e : 0x7f) + (c->wing != -1 ? 2 : 0);
    }
    return -1;
}
static mu_sfx_call *request32(mu_skill32_plan *p, const mu_skill32_input *s, int routine, int type, int sub)
{
    mu_sfx_call *c = &p->calls[p->count++].call.visual;
    c->routine = routine; c->type = type; c->subtype = sub; c->owner = s->cast.owner;
    memcpy(c->position, s->cast.position, sizeof c->position);
    memcpy(c->angle, s->cast.angle, sizeof c->angle);
    memcpy(c->light, s->cast.light, sizeof c->light);
    c->range = -1; c->arg7 = -1;
    return c;
}
int mu_skill32_plan_cast(mu_skill32_input *s, int end, mu_skill32_plan *p)
{
    memset(p, 0, sizeof *p); p->limit = 15;
    if (!mu_skill32_select(s->cast.skill, s->cast.base)) return 0;
    int skill = s->cast.base;
    if (end == 2) {
        int sound = skill == 44 ? 0x71 : 0x6f;
        if (skill != 49) {
            mu_sfx_call *c = request32(p, s, MU_SFX_CALL_SOUND, sound, 0); c->owner = -1;
            p->calls[p->count-1].call.site = skill == 18 ? 0x01222fa3 : skill == 44 ? 0x01256d18 : 0x01255962;
        }
    } else if (!end) {
        if (skill == 49 && s->cast.model == 0xa91 && s->cast.action == 0xf9 && s->cast.frame >= 5.0f)
            s->cast.attack_time = 15;
        if (skill == 44) {
            if (s->cast.frame > 5.0f) s->cast.attack_time = 15;
            float pos[3]; memcpy(pos, s->cast.position, sizeof pos);
            pos[0] = ((float)(s->random[0] % 30) - 15.0f) + pos[0];
            pos[1] = ((float)(s->random[1] % 30) - 15.0f) + pos[1]; pos[2] += 20.0f;
            for (int n = 0; n < 4; ++n) {
                float angle[3] = {(float)(s->random[n+2] % 60 + 150), 0.0f, s->cast.angle[2]};
                mu_sfx_call *c = request32(p, s, MU_SFX_CALL_JOINT, 0x7fd5, 0);
                memcpy(c->position, pos, sizeof pos); memcpy(c->target, pos, sizeof pos);
                memcpy(c->angle, angle, sizeof angle); c->owner = -1; c->scale = 10.0f;
                c = request32(p, s, MU_SFX_CALL_PARTICLE, 0x7f3c, 2);
                memcpy(c->position, pos, sizeof pos); memcpy(c->angle, angle, sizeof angle);
                c->owner = -1; c->scale = 1.5f;
            }
            p->random_used = 6;
        }
    } else if (skill >= 30 && skill <= 36) {
        request32(p, s, MU_SFX_CALL_EFFECT, 0x7f84, 3);
    } else if (skill == 49) {
        mu_sfx_call *c = request32(p, s, MU_SFX_CALL_EFFECT, 0x8001, 0);
        c->range = s->object_key; p->calls[p->count-1].skill = s->skill_word;
        c = request32(p, s, MU_SFX_CALL_SOUND, 0x72, 0); c->owner = -1;
        p->calls[p->count-1].call.site = 0x013aba74;
    } else if (skill == 44) {
        request32(p, s, MU_SFX_CALL_EFFECT, 0x49e, 0);
        /* MoveCharacter's white local, not OBJECT Light. */
        mu_sfx_call *c = &p->calls[p->count-1].call.visual;
        c->light[0] = c->light[1] = c->light[2] = 1.0f;
        c = request32(p, s, MU_SFX_CALL_SOUND, 0x2ad, 0); c->owner = -1;
        p->calls[p->count-1].call.site = 0x013ad7ec;
    }
    return 1;
}
