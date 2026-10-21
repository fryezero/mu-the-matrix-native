/* Test host for native/gfx/mu_gfx_layer.c (NATIVE-GFX-002/003).
 *
 *   gfx-layer-host MOVIE_DIR LIBMUGFX [OP ...]
 *
 * Opens the layer (no GL: compiled with -DMU_GFX_NO_GL, read-back path) on
 * the given library (the real libmugfx or tests/gfx_stub_mugfx.c), adds
 * three demo items and runs the ops in order:
 *   key VK | text STR | click CELL | rclick CELL | hover CELL | at X Y (click)
 *   | closebtn | advance MS | composite | open MOVIE | print
 *   | compose STR | invoke MOVIE PATH METHOD JSON ("-" path: the movie's) | items | channels
 *   | npcdialog | npcshop | storage | npcact VERB ARG | slot MOVIE CELL | slotdraws MOVIE | npcprint
 *   (NATIVE-NPC-001: the NPC windows with demo contents)
 *   | buffs | charrows   (NATIVE-LANG-002: three buffs, then the bufflist's tooltip through
 *   `npcact bufftip N`; three CharacterInfoSetup-like rows for the character window;
 *   MU_GFX_HOST_CHOICE=1 installs a dialogue-choice callback that takes the choice)
 * `print` writes one JSON line with the layer state; each input op prints
 * whether the interface took it.  MU_GFX_SIZE=WxH sets the window size in
 * points (default 1280x800).  MU_GFX_HOST_TEXT=1 installs a GlobalText
 * provider that returns "T<n>" (NATIVE-LANG-001). */
#include <stdio.h>
#include <stdlib.h>
#include <string.h>

#include "../gfx/mu_gfx_layer.h"

static void print_state(mu_gfx_layer *L)
{
    printf("{\"inventory_open\": %d, \"character_open\": %d, \"held\": %d, \"cells\": [",
           mu_gfx_layer_is_open(L, MU_GFX_INVENTORY), mu_gfx_layer_is_open(L, MU_GFX_CHARACTER), mu_gfx_layer_held(L));
    for (int i = 0; i < mu_gfx_layer_item_count(L); i++)
        printf("%s%d", i ? ", " : "", mu_gfx_layer_item_cell(L, i));
    int32_t v[4];
    mu_gfx_layer_view(L, MU_GFX_INVENTORY, v);
    printf("], \"text_active\": %d, \"chat_sent\": \"%s\", \"main_path\": \"%s\", \"inventory_path\": \"%s\", "
           "\"inventory_view\": [%d, %d, %d, %d], \"points\": %d, \"base_mode\": %d, \"chat_path\": \"%s\"}\n",
           mu_gfx_layer_text_active(L), mu_gfx_layer_last_sent(L), mu_gfx_layer_path(L, MU_GFX_MAIN),
           mu_gfx_layer_path(L, MU_GFX_INVENTORY), v[0], v[1], v[2], v[3], mu_gfx_layer_hero(L)->points,
           mu_gfx_layer_base_mode(L), mu_gfx_layer_path(L, MU_GFX_CHAT));
    fflush(stdout);
}

static const char *host_text(void *user, int32_t index)
{
    static char buf[16][24];
    static int next;
    (void)user;
    char *b = buf[next++ & 15];
    snprintf(b, sizeof buf[0], "T%d", index);
    return b;
}

static int host_choice(void *user, int index)
{
    (void)user;
    printf("host choice %d\n", index);
    return 1;
}

static int host_buff_tooltip(void *user, int32_t buff, char *html, size_t cap)
{
    (void)user;
    snprintf(html, cap, "<b>buff %d</b>", (int)buff);
    return 0;
}

static int click(mu_gfx_layer *L, double x, double y, int button)
{
    mu_gfx_layer_mouse(L, 0, 0, x, y);
    int took = mu_gfx_layer_mouse(L, 1, button, x, y);
    mu_gfx_layer_mouse(L, 2, button, x, y);
    return took;
}

int main(int argc, char **argv)
{
    if (argc < 3) {
        fprintf(stderr, "usage: %s MOVIE_DIR LIBMUGFX [OP ...]\n", argv[0]);
        return 2;
    }
    char error[512];
    double scale = getenv("MU_GFX_SCALE") ? atof(getenv("MU_GFX_SCALE")) : 1.0;
    int pw = 1280, ph = 800;
    if (getenv("MU_GFX_SIZE"))
        sscanf(getenv("MU_GFX_SIZE"), "%dx%d", &pw, &ph);
    mu_gfx_layer_config cfg = {.movie_dir = argv[1], .lib_path = argv[2], .width = (int32_t)(pw * scale),
                               .height = (int32_t)(ph * scale), .shared = 1, .log = getenv("MU_GFX_LOG") ? stderr : NULL,
                               .scale = scale};
    if (getenv("MU_GFX_HOST_TEXT"))
        cfg.text = host_text;
    if (getenv("MU_GFX_HOST_CHOICE"))
        cfg.dialog_choice = host_choice;
    cfg.buff_tooltip = host_buff_tooltip;
    mu_gfx_layer *L = mu_gfx_layer_open(&cfg, error, sizeof error);
    if (!L) {
        printf("{\"error\": \"%s\"}\n", error);
        return 1;
    }
    mu_gfx_layer_add_item(L, 0, 9, 1, 3, "Kris");
    mu_gfx_layer_add_item(L, 3584, 7, 2, 2, "Bronze Helm");
    mu_gfx_layer_add_item(L, 7171, 0, 1, 1, "Healing Potion");
    for (int i = 3; i < argc; i++) {
        const char *op = argv[i], *a = i + 1 < argc ? argv[i + 1] : "0";
        double x, y;
        if (!strcmp(op, "print")) {
            print_state(L);
        } else if (!strcmp(op, "key")) {
            int vk = atoi(a);
            int d = mu_gfx_layer_key(L, 1, vk, 0, 0), u = mu_gfx_layer_key(L, 0, vk, 0, 0);
            printf("key %d took %d %d\n", vk, d, u);
            i++;
        } else if (!strcmp(op, "text")) {
            printf("text took %d\n", mu_gfx_layer_text(L, a));
            i++;
        } else if (!strcmp(op, "click") || !strcmp(op, "rclick") || !strcmp(op, "hover")) {
            if (!mu_gfx_layer_cell_center(L, atoi(a), &x, &y)) {
                printf("%s %s: no geometry\n", op, a);
            } else if (!strcmp(op, "hover")) {
                printf("hover %s took %d\n", a, mu_gfx_layer_mouse(L, 0, 0, x, y));
            } else {
                printf("%s %s took %d\n", op, a, click(L, x, y, op[0] == 'r' ? 1 : 0));
            }
            i++;
        } else if (!strcmp(op, "at") && i + 2 < argc) {
            printf("at %s %s took %d\n", argv[i + 1], argv[i + 2],
                   click(L, atof(argv[i + 1]) * scale, atof(argv[i + 2]) * scale, 0));
            i += 2;
        } else if (!strcmp(op, "closebtn")) {
            int32_t v[4];
            mu_gfx_layer_view(L, MU_GFX_INVENTORY, v);
            printf("closebtn took %d\n", click(L, (1280 - 332 + 315) * scale, (20 + 10) * scale, 0));
        } else if (!strcmp(op, "advance")) {
            mu_gfx_layer_advance(L, atof(a));
            i++;
        } else if (!strcmp(op, "composite")) {
            int32_t W = (int32_t)(1280 * scale), H = (int32_t)(800 * scale);
            uint8_t *px = calloc((size_t)W * (size_t)H, 4);
            mu_gfx_layer_composite(L, px, W, H);
            long drawn = 0;
            for (size_t p = 0; p < (size_t)W * (size_t)H; p++)
                drawn += px[p * 4 + 3] != 0;
            printf("composite drawn %ld\n", drawn);
            free(px);
        } else if (!strcmp(op, "open")) {
            mu_gfx_layer_toggle(L, atoi(a));
            i++;
        } else if (!strcmp(op, "compose")) {
            printf("compose took %d\n", mu_gfx_layer_compose(L, a, (int)strlen(a)));
            i++;
        } else if (!strcmp(op, "invoke") && i + 4 < argc) {
            const char *path = strcmp(argv[i + 2], "-") ? argv[i + 2] : NULL;
            const char *r = mu_gfx_layer_invoke(L, atoi(argv[i + 1]), path, argv[i + 3], argv[i + 4]);
            printf("invoke %s = %s\n", argv[i + 3], r ? r : "(null)");
            i += 4;
        } else if (!strcmp(op, "items")) {
            mu_gfx_item_draw d[16];
            int n = mu_gfx_layer_item_draws(L, d, 16);
            for (int k = 0; k < n; k++)
                printf("{\"item_draw\": %d, \"code\": %d, \"level\": %d, \"slot\": [%.2f, %.2f, %.2f, %.2f], "
                       "\"rect\": [%.2f, %.2f, %.2f, %.2f], \"frame_scale\": %.2f, \"select\": %d}\n", d[k].item,
                       d[k].code, d[k].level, d[k].slot[0], d[k].slot[1], d[k].slot[2], d[k].slot[3], d[k].rect[0],
                       d[k].rect[1], d[k].rect[2], d[k].rect[3], d[k].frame_scale, d[k].select);
        } else if (!strcmp(op, "npcdialog")) {
            mu_gfx_npc_dialog d = {.title = "Demo NPC", .text = "First line of the talk;Second line", .noptions = 2,
                                   .hide_contribute = 1};
            d.options[0] = "Tell me more";
            d.options[1] = "Goodbye";
            printf("npcdialog %d\n", mu_gfx_layer_npc_dialog(L, &d));
        } else if (!strcmp(op, "npcshop") || !strcmp(op, "storage")) {
            mu_gfx_slot_item it[3] = {{0, 9, 1, 3, 1000, "Kris"}, {3584, 7, 2, 2, 5000, "Bronze Helm"},
                                      {7171, 0, 1, 1, 30, "Healing Potion"}};
            int ok = !strcmp(op, "npcshop") ? mu_gfx_layer_npc_shop(L, "Demo Shop", 1, 2, it, 3)
                                            : mu_gfx_layer_storage(L, "Vault", it, 2);
            printf("%s %d\n", op, ok);
        } else if (!strcmp(op, "npcact") && i + 2 < argc) {
            printf("npcact %s %s = %d\n", argv[i + 1], argv[i + 2], mu_gfx_layer_npc_action(L, argv[i + 1], atoi(argv[i + 2])));
            i += 2;
        } else if (!strcmp(op, "slot") && i + 2 < argc) {
            int m = atoi(argv[i + 1]);
            if (mu_gfx_layer_slot_center(L, m, atoi(argv[i + 2]), &x, &y))
                printf("slot %d %s took %d\n", m, argv[i + 2], click(L, x, y, 0));
            else
                printf("slot %d %s: no geometry\n", m, argv[i + 2]);
            i += 2;
        } else if (!strcmp(op, "slotdraws")) {
            mu_gfx_item_draw d[16];
            int n = mu_gfx_layer_slot_draws(L, atoi(a), d, 16);
            for (int k = 0; k < n; k++)
                printf("{\"slot_draw\": %d, \"code\": %d, \"slot\": [%.2f, %.2f, %.2f, %.2f], \"page_type\": %d, "
                       "\"type8\": %d, \"rect\": [%.2f, %.2f, %.2f, %.2f]}\n", d[k].item, d[k].code, d[k].slot[0],
                       d[k].slot[1], d[k].slot[2], d[k].slot[3], d[k].page_type, d[k].type8_seen, d[k].rect[0],
                       d[k].rect[1], d[k].rect[2], d[k].rect[3]);
            i++;
        } else if (!strcmp(op, "npcprint")) {
            int pages = 0, page = mu_gfx_layer_npc_page(L, &pages);
            printf("{\"npc_window\": %d, \"last\": \"%s\", \"page\": %d, \"pages\": %d, \"shop_items\": %d, "
                   "\"storage_items\": %d, \"inventory_items\": %d, \"inventory_open\": %d, \"zen\": %lld}\n",
                   mu_gfx_layer_npc_window(L), mu_gfx_layer_npc_last(L), page, pages,
                   mu_gfx_layer_slot_items(L, MU_GFX_NPC_SHOP), mu_gfx_layer_slot_items(L, MU_GFX_STORAGE),
                   mu_gfx_layer_items_placed(L), mu_gfx_layer_is_open(L, MU_GFX_INVENTORY),
                   (long long)mu_gfx_layer_hero(L)->zen);
        } else if (!strcmp(op, "buffs")) {
            mu_gfx_buff b[3] = {{1, 0, 0, 1, 0}, {35, 0, 0, 1, 2}, {55, 1, 0, 0, 0}};
            int n = 0;
            for (int k = 0; k < 3; k++)
                n += mu_gfx_layer_add_buff(L, &b[k]);
            n += mu_gfx_layer_add_buff(L, &b[0]);   /* a buff already listed is not sent again */
            printf("buffs %d %d\n", n, mu_gfx_layer_buff_count(L));
        } else if (!strcmp(op, "charrows")) {
            mu_gfx_char_row r[3] = {{1, 1, 0, 0, 20, 3, MU_GFX_ROW_CLASS, "Class"},
                                    {2, 8, 0, 1, 20, 3, MU_GFX_ROW_STRENGTH, "Strength"},
                                    {3, 43, 0, 0, 20, 3, MU_GFX_ROW_NONE, "* Critical <DMG>"}};
            mu_gfx_layer_set_char_rows(L, r, 3);
            printf("charrows 3\n");
        } else if (!strcmp(op, "channels")) {
            static const char *const NAMES[] = {"UIFrame", "ASData", "main", "chat", "alarmframe", "topmenu"};
            printf("{\"channels\": {");
            for (size_t k = 0; k < sizeof NAMES / sizeof NAMES[0]; k++)
                printf("%s\"%s\": \"%s\"", k ? ", " : "", NAMES[k], mu_gfx_layer_channel_path(L, NAMES[k]));
            printf("}}\n");
        } else {
            fprintf(stderr, "unknown op %s\n", op);
            return 2;
        }
    }
    mu_gfx_layer_close(L);
    return 0;
}
