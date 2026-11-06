/* APP-POLISH-005 test host: the offline session's skills/hero lines and the fixture lines they become. */
#include <stdio.h>
#include <stdlib.h>
#include <string.h>

#include "../client/offline-session.h"
#include "../fixture/skills_demo.h"

int main(int argc, char **argv)
{
    if (argc == 4 && !strcmp(argv[1], "session")) {
        static mu_offline_session s;
        char error[512] = "";
        if (mu_offline_session_load(&s, argv[2], argv[3], error, sizeof error)) {
            printf("{\"error\": \"%s\"}\n", error);
            return 0;
        }
        printf("{\"skills\": \"%s\", \"characters\": %d, \"joins\": %d, \"heroes\": [", s.skills_path,
               (int)s.characters.count, (int)s.join_count);
        for (int32_t i = 0; i < s.hero_count; ++i) {
            const mu_offline_hero *h = mu_offline_session_hero(&s, s.heroes[i].slot);
            const mu_charsel_entry *e = mu_offline_session_character(&s, h->slot);
            mu_offline_join j = mu_offline_session_join(&s, h->slot);
            printf("%s{\"slot\": %d, \"stats\": [%d, %d, %d, %d, %d], \"points\": %d, \"class\": %d, \"level\": %d, "
                   "\"world\": %d, \"tile\": [%d, %d]}", i ? ", " : "", (int)h->slot, (int)h->stats[0],
                   (int)h->stats[1], (int)h->stats[2], (int)h->stats[3], (int)h->stats[4], (int)h->points,
                   e ? (int)e->class_byte : -1, e ? (int)e->level : -1, (int)j.world, (int)j.tile[0], (int)j.tile[1]);
        }
        printf("], \"missing\": %d}\n", mu_offline_session_hero(&s, 7) == NULL);
        return 0;
    }
    if (argc == 12 && !strcmp(argv[1], "lines")) {
        mu_skills_demo_join join = {argv[3][0] ? argv[3] : NULL, atoi(argv[4]) > 0, atoi(argv[4]),
                                    {atoi(argv[5]), atoi(argv[6]), atoi(argv[7]), atoi(argv[8]), atoi(argv[9])},
                                    atoi(argv[10])};
        mu_skills_demo_login(stdout, argv[11], atoi(argv[2]), &join);
        mu_skills_demo_hero(stdout, atoi(argv[2]), 0, 182, 128, 90.0f, &join);
        return 0;
    }
    fprintf(stderr, "usage: session PATH ROOT | lines CLASS FILE LEVEL STR AGI VIT ENE CMD POINTS ROOT\n");
    return 2;
}
