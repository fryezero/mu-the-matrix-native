/* Table accessor tests use authored rows, never captured game data. */
#include "../core/mu_social_item_tables.h"
#include <assert.h>
#include <stdio.h>
#include <string.h>
int main(int argc, char **argv) {
    assert(argc == 3);
    mu_social_item_tables *t = mu_social_item_tables_load(argv[1], argv[2], NULL);
    assert(t);
    assert(mu_social_item_table_rows(t) == 7);
    mu_social_guardian_option g;
    assert(mu_social_guardian_get(t, 3, 7, &g) && g.id == 7 && g.value == 19 && g.auxiliary == 34);
    assert(!strcmp(g.text, "Option %d\\literal\n"));
    assert(!mu_social_guardian_get(t, 4, 7, &g));
    mu_social_guardian_option bonus[2];
    assert(mu_social_guardian_bonus_get(t, 3, 9, bonus));
    assert(bonus[0].id == 2 && bonus[0].value == 24 && !strcmp(bonus[0].text, "Bonus %d"));
    assert(bonus[1].id == 99 && bonus[1].value == 17 && !bonus[1].text);
    mu_social_artifact_row a;
    assert(mu_social_artifact_get(t, 8, &a));
    assert(a.text_id == 12 && a.pairs[0][0] == 1 && a.pairs[9][1] == 20 && a.tail[4] == 25);
    int format = 0;
    assert(!strcmp(mu_social_artifact_text(t, 12, &format), "Artifact") && format == 2);
    mu_social_advanced_row h;
    assert(mu_social_advanced_get(t, 3, 5, &h));
    assert(h.values[3] == 40 && h.format == 2 && !strcmp(h.name, "Advanced %"));
    assert(!mu_social_advanced_get(t, 3, 6, &h));
    mu_social_socket_row socket;
    assert(mu_social_socket_get(t, 1, 4, &socket));
    assert(socket.index == 54 && socket.values[0] == 540 && socket.values[19] == 559);
    assert(!mu_social_socket_get(t, 0, 50, &socket));
    mu_social_harmony_row harmony;
    assert(mu_social_harmony_get(t, 2, 5, &harmony));
    assert(harmony.id == 5 && harmony.values[13] == 50413 && harmony.zen[13] == 504113);
    assert(!mu_social_harmony_get(t, 0, 0, &harmony));
    mu_social_item_tables_free(t);
    puts("social item tables passed");
}
