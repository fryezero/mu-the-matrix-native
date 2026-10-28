#include "../core/mu_social_item_view.h"
#include "../core/mu_lang.h"
#include <assert.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
static int contains(const mu_social_item_view *v, const char *s) {
    for (int i = 0; i < v->count; i++)
        if (strstr(v->text[i], s))
            return 1;
    return 0;
}
int main(int argc, char **argv) {
    assert(argc == 3);
    assert(setenv("MU_LANG_DIR", argv[2], 1) == 0);

    mu_hud_tip_tables base;
    mu_hud_tip_tables_load(argv[1], &base);
    assert(base.have_items);
    mu_social_item_tables *t = mu_social_item_tables_load(argv[1], argv[2], &base.items);
    assert(t);
    mu_social_item_view *v = calloc(1, sizeof *v);
    mu_social_item_hero hero = {
        .known = 1, .level = 400, .hp_known = 1, .max_hp = 120000, .mp_known = 1, .max_mp = 220000};
    for (int code = 100; code <= 107; code++) {
        mu_social_item_wire w = {.code = code, .level_word = 8, .durability = 17};
        memset(w.sockets, 255, 5);
        memset(w.extra, 255, 3);
        w.harmony = 255;
        const char *expect = NULL;
        if (code == 100) {
            w.level_word = 0x8f;
            w.excellent = 0x60;
            w.harmony = 0;
            expect = "Excellent damage 16";
        }
        if (code == 101) {
            w.sockets[0] = 0;
            expect = "Socket power 7";
        }
        if (code == 102) {
            w.sockets[0] = 7;
            expect = "Guardian 2";
        }
        if (code == 103) {
            w.sockets[0] = 8;
            w.sockets[1] = 3;
            expect = "Artifact power +4%";
        }
        if (code == 104) {
            w.sockets[0] = 224;
            expect = "Mastery power +10";
        }
        if (code == 105) {
            w.sockets[0] = 0x21;
            expect = "Elemental Power 20";
        }
        if (code == 106) {
            w.ancient = 0x21;
            w.sockets[0] = 1;
            w.harmony = 1;
            expect = "Fire elemental attack +51";
        }
        if (code == 107) {
            w.level_word = 9 << 3;
            w.extra[0] = 0x21;
            w.harmony = 0;
            expect = "Advanced strength +2%";
        }
        uint8_t bytes[15];
        mu_social_item_pack(&w, bytes);
        assert(mu_social_item_view_build(t, &base, bytes, &hero, v));
        if (!contains(v, expect)) {
            fprintf(stderr, "code %d missing %s\n", code, expect);
            for (int i = 0; i < v->count; i++)
                fprintf(stderr, "%s\n", v->text[i]);
            return 1;
        }
        if (code == 100) {
            assert(contains(v, "Extra damage 28"));
            assert(contains(v, "Luck 25"));
            assert(v->finalized.excellent == 1);
        }
        if (code == 106) {
            assert(v->unresolved > 0);
            assert(contains(v, "equipment"));
        }
        uint8_t packed[15];
        mu_social_item_pack(&v->wire, packed);
        assert(!memcmp(packed, bytes, 15));
        char html[32768];
        assert(mu_social_item_view_html(v, html, sizeof html) > 0);
        assert(strstr(html, "<font"));
    }
    mu_social_item_tables *missing_tables = mu_social_item_tables_load(NULL, argv[2], &base.items);
    mu_social_item_wire raw = {.code = 100, .excellent = 0x20};
    memset(raw.sockets, 255, 5);
    memset(raw.extra, 255, 3);
    uint8_t bytes[15];
    mu_social_item_pack(&raw, bytes);
    assert(mu_social_item_view_build(missing_tables, &base, bytes, &hero, v));
    assert(!v->excellent_known && v->requested_excellent[0] == 0 && v->unresolved > 0 &&
           contains(v, "Excellent options"));
    assert(v->context.excellent_resolved == -1 && v->finalized.slots[0] == 255);
    mu_social_item_tables_free(missing_tables);
    missing_tables = mu_social_item_tables_load(NULL, NULL, &base.items);
    assert(!mu_social_item_table_available(missing_tables, "guardian_value"));
    raw.code = 102;
    raw.excellent = 0;
    raw.level_word = 8;
    raw.sockets[0] = 7;
    mu_social_item_pack(&raw, bytes);
    assert(mu_social_item_view_build(missing_tables, &base, bytes, &hero, v));
    assert(v->unresolved > 0 && contains(v, "Guardian options: details unavailable"));
    raw.code = 104;
    raw.sockets[0] = 224;
    mu_social_item_pack(&raw, bytes);
    assert(mu_social_item_view_build(missing_tables, &base, bytes, &hero, v));
    assert(v->unresolved > 0 && contains(v, "Earring options: details unavailable"));
    raw.code = 105;
    raw.sockets[0] = 0x21;
    mu_social_item_pack(&raw, bytes);
    assert(mu_social_item_view_build(missing_tables, &base, bytes, &hero, v));
    assert(v->unresolved > 0 && contains(v, "Errtel options: details unavailable"));
    mu_social_item_tables_free(missing_tables);
    char directory[4096];
    snprintf(directory, sizeof directory, "%s/missing", argv[2]);
    missing_tables = mu_social_item_tables_load(NULL, directory, &base.items);
    raw.code = 102;
    memset(raw.sockets, 255, 5);
    raw.sockets[3] = 7;
    mu_social_item_pack(&raw, bytes);
    assert(mu_social_item_view_build(missing_tables, &base, bytes, &hero, v));
    assert(v->decoded.guardian_keys[3] == 7 && v->unresolved > 0 &&
           contains(v, "Guardian options: details unavailable"));
    mu_social_item_tables_free(missing_tables);
    assert(mu_social_item_view_build(t, &base, bytes, &hero, v) && contains(v, "Guardian 2"));
    snprintf(directory, sizeof directory, "%s/empty", argv[2]);
    missing_tables = mu_social_item_tables_load(NULL, directory, &base.items);
    assert(mu_social_item_table_available(missing_tables, "guardian_value"));
    assert(mu_social_item_view_build(missing_tables, &base, bytes, &hero, v));
    assert(v->unresolved == 0 && !contains(v, "Guardian 2") && !contains(v, "details unavailable"));
    mu_social_item_tables_free(missing_tables);
    free(v);
    mu_social_item_tables_free(t);
    mu_hud_tip_tables_free(&base);
    puts("social item views passed");
}
