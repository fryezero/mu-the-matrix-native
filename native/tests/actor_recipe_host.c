/* RENDER-ACTORS-001: exercise the production actor loader without a session. */
#include "../core/mu_world_actors.c"

int main(int argc, char **argv)
{
    if (argc != 3) return 2;
    mu_world *map = calloc(1, sizeof *map);
    mu_world_actors actors = {0};
    mu_world_actor actor;
    actors.map = map;
    char error[1024];
    int cl = atoi(argv[2]);
    int result = load_actor(&actors, &actor, argv[1], cl, 128, 124, 5, 0,
                            "DemoActor", 0, error, sizeof error);
    if (result) { fprintf(stderr, "%s\n", error); free(map); return 1; }
    printf("{\"class\":%d,\"player\":%d,\"scale\":%.9g,\"slots\":[", cl,
           actor.player != NULL, (double)actor.actor.spec.scale);
    if (actor.player) {
        if (mu_character_update(actor.player) != MU_MODEL_OK) return 3;
        float lo[3], hi[3];
        if (!mu_character_bounds(actor.player, lo, hi) || !(hi[2] > lo[2])) return 4;
        for (int i = 0; i < MU_CHARACTER_ITEMS; ++i) {
            const mu_character_item *part = &actor.player->items[i];
            printf("%s[%d,%d,%d,%d,%d]", i ? "," : "", part->loaded,
                actor.player_glow[i].type, actor.player_glow[i].level,
                part->bmd.mesh_count, part->textures.missing);
        }
        mu_character_free(actor.player); free(actor.player);
    }
    printf("]}\n");
    mu_actor_free(&actor.actor); free(map);
    return 0;
}
