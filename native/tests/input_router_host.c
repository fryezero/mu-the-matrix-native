/* Synthetic adapters isolate the router. This is not session or renderer evidence. */
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include "../world/world_rt_internal.h"
static int casts, picks, labels, messages, last_skill, walk_held[256], key_message_down;
void mu_walk_message(mu_walk *w, uint32_t m, uint32_t wp, uint32_t lp)
{ (void)w; (void)wp; (void)lp; ++messages; if (m == 0x100u || m == 0x101u) key_message_down = m == 0x100u; }
void mu_walk_key(mu_walk *w, int vk, int down) { (void)w; if (vk >= 0 && vk < 256) walk_held[vk] = down; }
void mu_world_items_alt(mu_world_items *it) { (void)it; ++labels; }
int mu_world_items_space(mu_world_items *it) { (void)it; ++picks; return 1; }
void mu_combat_cast(mu_combat *c, int32_t skill, int32_t actor)
{ (void)c; (void)actor; ++casts; last_skill = skill; }
int main(int argc, char **argv)
{
    if (argc == 3 && !strcmp(argv[1], "parse")) {
        mu_input_action items[MU_INPUT_SCRIPT_MAX];
        printf("%d\n", mu_input_script_parse(argv[2], items)); return 0;
    }
    mu_world_rt *rt = calloc(1, sizeof *rt);
    if (!rt) return 2;
    rt->combat = (mu_combat *)rt; rt->ground = (mu_world_items *)rt; rt->quiet = 1;
    for (int i = 1; i < argc; ++i) {
        int r;
        if (!strcmp(argv[i], "focus-lost")) {
            mu_input_msg m = {.kind=MU_INPUT_FOCUS}; r = mu_world_rt_input(rt,&m);
        } else r = mu_world_rt_action(rt,argv[i]);
        printf("{\"result\":%d,\"casts\":%d,\"picks\":%d,\"labels\":%d,\"messages\":%d,"
               "\"skill\":%d,\"digit_held\":%d,\"alt_held\":%d,\"key_message_down\":%d}\n",
               r,casts,picks,labels,messages,last_skill,rt->input_down['1'],walk_held[18],key_message_down);
    }
    free(rt); return 0;
}
