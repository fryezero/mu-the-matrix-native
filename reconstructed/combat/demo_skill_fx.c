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
    memset(p, 0, sizeof *p); p->limit = 15; p->target_key = -1;
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
        if (s->base == 51) p->target_key = s->target_key;
        if (s->base == 24) arrow(p, s, 1); /* intentional fallthrough at 0x013af9fe */
        arrow(p, s, 0);
    }
    return 1;
}
