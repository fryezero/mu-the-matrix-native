/* WORLD-RT-001: the world's input as world/main.c's window handled it, now reachable from every front end.
 *
 * The window procedure's messages and key states go to the walk session (click-to-move, the client terrain pick,
 * the wheel zoom); the world's own keys (Alt, Space, 1..0) and the right-button skill cast act on a press.  This
 * keeps today's handling; the input router (GFx first refusal, the key scan 0x00ec5475, the panel bindings,
 * intents) is INPUT-001's (docs/design/native-port/sketch/native/world/input.c). */
#include <stdio.h>

#ifndef MU_WORLD_NO_GL
#include "../core/mu_skill.h"
#endif
#include "world_rt_internal.h"

void mu_world_rt_message(mu_world_rt *a, uint32_t message, uint32_t wparam, uint32_t lparam)
{
    mu_walk_message(&a->walk, message, wparam, lparam);
}

void mu_world_rt_key(mu_world_rt *a, int vk, int down)
{
    mu_walk_key(&a->walk, vk, down);
}

/* A key press (not a repeat), after the key state and its window message. */
int mu_world_rt_hotkey(mu_world_rt *a, int vk)
{
    int used = 0;
    if (a->ground && vk == 0x12) {   /* Alt: setItemView(!view) (0x00efc7d3) */
        mu_world_items_alt(a->ground);
        used = 1;
    }
    if (a->ground && vk == 0x20) {   /* space: the nearest item (0x00efd9ab) */
        mu_world_items_space(a->ground);
        used = 1;
    }
    if (a->combat && vk >= 0x30 && vk <= 0x39) {
        /* 1..6 (NATIVE-COMBAT-001), 7 Evil Spirit, 8 Hellfire, 9 Inferno, 0 Cyclone */
        static const int32_t keys[10] = {22, 4, 17, 22, 41, 24, 26, 9, 10, 14};
        mu_combat_cast(a->combat, keys[vk - 0x30], -1);
        used = 1;
    }
    return used;
}

#ifndef MU_WORLD_NO_GL
/* NATIVE-SKILL-001: the selected skill's cast at a monster through the client's checks (core/mu_skill: stats,
 * the class special cases, IsSkillReady, the mana/AG check, StartSkillDelay -> onUseSkillDelay), then the combat
 * path draws it (mu_combat_cast, NATIVE-COMBAT-001/002).  Returns MU_SKILL_CAST_*. */
int world_rt_skill_cast_at(mu_world_rt *a, int32_t actor, int32_t *skill)
{
    *skill = 0;
    if (!a->gfx)
        return MU_SKILL_CAST_NONE;
    int r = world_gfx_skill_cast(a->gfx, skill);
    if (r == MU_SKILL_CAST_OK) {
        a->skill_casts++;
        if (a->combat && actor >= 0)
            mu_combat_cast(a->combat, *skill, actor);
    } else {
        a->skill_refused++;
    }
    return r;
}
#endif

/* NATIVE-SKILL-001: the right button casts the bar's selected skill at the monster under the mouse (the classic
 * binding; the use controller 0x0107e99a runs the checks). */
int mu_world_rt_right_button(mu_world_rt *a)
{
#ifndef MU_WORLD_NO_GL
    if (a->gfx && a->combat && mu_combat_pick(a->combat) >= 0) {
        int32_t actor = mu_combat_pick(a->combat), skill = 0;
        int r = world_rt_skill_cast_at(a, actor, &skill);
        if (!a->quiet)
            fprintf(stderr, "skill %d at actor %d: %s\n", (int)skill, (int)actor, mu_skill_cast_name(r));
        return 1;
    }
#else
    (void)a;
#endif
    return 0;
}
