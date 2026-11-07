/* APP-POLISH-008 test host: the character list's item values (FILE[@GROUP:INDEX[:LEVEL[:OPTION[:EXT]]]]), the
 * offline session's characters with their equipment records, and the character store's round trip. */
#include <stdio.h>
#include <string.h>

#include "../client/offline-session.h"

static void print_record(const char *path, const mu_charsel_item_record *r)
{
    printf("{\"path\": \"%s\", \"set\": %d, \"code\": %d, \"level\": %d, \"option\": %d, \"ext\": %d}", path,
           (int)r->set, (int)r->code, (int)r->level, (int)r->option, (int)r->ext);
}

static void print_characters(const mu_offline_session *s)
{
    printf("{\"characters\": [");
    for (int32_t i = 0; i < s->characters.count; ++i) {
        const mu_charsel_entry *e = &s->characters.entries[i];
        printf("%s{\"slot\": %d, \"name\": \"%s\", \"items\": {", i ? ", " : "", (int)e->slot, e->name);
        int first = 1;
        for (int k = 1; k < MU_CHARACTER_ITEMS; ++k)
            if (e->items[k][0]) {
                printf("%s\"%d\": ", first ? "" : ", ", k);
                print_record(e->items[k], &e->records[k]);
                first = 0;
            }
        printf("}}");
    }
    printf("]}\n");
}

int main(int argc, char **argv)
{
    if (argc == 4 && !strcmp(argv[1], "item")) {
        char path[MU_CHARSEL_PATH];
        mu_charsel_item_record r;
        if (mu_charsel_parse_item(argv[2], argv[3], path, sizeof path, &r)) {
            printf("{\"error\": 1}\n");
            return 0;
        }
        print_record(path, &r);
        printf("\n");
        return 0;
    }
    if ((argc == 4 || argc == 5) && !strcmp(argv[1], "session")) {
        static mu_offline_session s, back;
        char error[512] = "";
        if (mu_offline_session_load(&s, argv[2], argv[3], error, sizeof error)) {
            printf("{\"error\": \"%s\"}\n", error);
            return 0;
        }
        if (argc == 4) {
            print_characters(&s);
            return 0;
        }
        /* the store: written from the session's characters, then read back by a second session */
        if (mu_offline_session_use_store(&s, argv[4], "2026-11-07", error, sizeof error) ||
            mu_offline_session_save(&s) ||
            mu_offline_session_load(&back, argv[2], argv[3], error, sizeof error) ||
            mu_offline_session_use_store(&back, argv[4], "2026-11-07", error, sizeof error)) {
            printf("{\"error\": \"store: %s\"}\n", error);
            return 0;
        }
        print_characters(&back);
        return 0;
    }
    fprintf(stderr, "usage: item VALUE ROOT | session PATH ROOT [STORE]\n");
    return 2;
}
