/* Synthetic social integration over the existing recording GFx ABI. No client data. */
#include "../core/mu_world_players.h"
#include "../gfx/mu_gfx_layer.h"
#include "../world/world_gfx_social.h"
#include <assert.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>

static void tick(world_gfx_social *g, mu_social_session *s, int n)
{
    for (int i = 0; i < n; i++) {
        mu_social_step(s, 0, 120, 120);
        world_gfx_social_frame(g);
    }
}
static void act(world_gfx_social *g, const char *v, const char *a)
{
    assert(world_gfx_social_action(g, v, a));
}
int main(int argc, char **argv)
{
    assert(argc == 3);
    char error[512];
    mu_gfx_layer_config c = {
        .movie_dir = argv[1], .lib_path = argv[2], .width = 1280, .height = 800, .shared = 1};
    mu_gfx_layer *l = mu_gfx_layer_open(&c, error, sizeof error);
    assert(l);
    mu_world_players *p = calloc(1, sizeof *p);
    assert(p);
    p->count = 1;
    p->list[0].in_view = 1;
    snprintf(p->list[0].spec.name, sizeof p->list[0].spec.name, "Shopkeep");
    /* Scripted shop/vault paths must obey escrow for both cancellation and commit. */
    for (int commit = 0; commit < 2; commit++) {
        int probe = mu_gfx_layer_add_item(l, 7002, 5, 2, 2, "Escrow probe");
        assert(probe >= 0);
        int cell = mu_gfx_layer_item_cell(l, probe);
        mu_gfx_slot_item probe_item;
        int reserved = mu_gfx_layer_inventory_reserve(l, cell, &probe_item);
        assert(reserved);
        assert(mu_gfx_layer_npc_shop(l, "Shop", 0, 1, NULL, 0));
        assert(mu_gfx_layer_npc_action(l, "sell", cell));
        assert(strstr(mu_gfx_layer_npc_last(l), "reserved"));
        mu_gfx_layer_npc_close(l);
        assert(mu_gfx_layer_storage(l, "Vault", NULL, 0));
        assert(mu_gfx_layer_npc_action(l, "put", cell + 1));
        assert(strstr(mu_gfx_layer_npc_last(l), "reserved"));
        assert(mu_gfx_layer_slot_items(l, MU_GFX_STORAGE) == 0);
        mu_gfx_layer_npc_close(l);
        if (commit) {
            int tokens[32] = {reserved};
            assert(mu_gfx_layer_inventory_exchange(l, tokens, NULL, 0));
            assert(mu_gfx_layer_count_item(l, 7002, 5) == 0);
        } else {
            mu_gfx_layer_inventory_finish(l, reserved, 0);
            assert(mu_gfx_layer_count_item(l, 7002, 5) == 1);
            reserved = mu_gfx_layer_inventory_reserve(l, cell, &probe_item);
            assert(reserved);
            mu_gfx_layer_inventory_finish(l, reserved, 1);
        }
    }
    mu_social_session s;
    mu_social_init(&s, "Hero", p);
    world_gfx_social *g = world_gfx_social_open(l, &s);
    assert(g);
    mu_gfx_layer_invoke(l, MU_GFX_MAIN, NULL, "testCall", "[\"hudMap\",\"onLoad\",\"_level0.map\"]");
    act(g, "party", "Shopkeep");
    act(g, "accept", "");
    tick(g, &s, 1);
    /* Tab clears its own unit layer; a stationary party still must be fed afterwards. */
    mu_gfx_layer_invoke(l, MU_GFX_MAIN, "_level0.map", "delAllUnit", "[]");
    world_gfx_social_frame(g);
    int kris = mu_gfx_layer_add_item(l, 0, 9, 1, 3, "Kris");
    int helm = mu_gfx_layer_add_item(l, 3584, 7, 2, 2, "Helm");
    int gem = mu_gfx_layer_add_item(l, 7171, 0, 1, 1, "Gem");
    assert(kris >= 0 && helm >= 0 && gem >= 0);
    act(g, "trade", "Shopkeep");
    act(g, "accept", "");
    tick(g, &s, 1);
    char b[24];
    snprintf(b, sizeof b, "%d", mu_gfx_layer_item_cell(l, helm));
    act(g, "offer", b);
    assert(!mu_gfx_layer_count_item(l, 3584, 7));
    /* A click on a covered cell removes the complete multi-cell offer. */
    act(g, "remove", "9");
    assert(mu_gfx_layer_count_item(l, 3584, 7) == 1);
    snprintf(b, sizeof b, "%d", mu_gfx_layer_item_cell(l, kris));
    act(g, "offer", b);
    snprintf(b, sizeof b, "%d", mu_gfx_layer_item_cell(l, helm));
    act(g, "offer", b);
    snprintf(b, sizeof b, "%d", mu_gfx_layer_item_cell(l, gem));
    act(g, "offer", b);
    assert(s.trade.items[0][3].present); /* beyond the old two demo flags */
    act(g, "cancel", "");
    assert(mu_gfx_layer_count_item(l, 0, 9) == 1 && mu_gfx_layer_count_item(l, 3584, 7) == 1);
    act(g, "trade", "Shopkeep");
    act(g, "accept", "");
    tick(g, &s, 1);
    snprintf(b, sizeof b, "%d", mu_gfx_layer_item_cell(l, gem));
    act(g, "offer", b);
    act(g, "partner-item", "");
    act(g, "zen", "1000");
    act(g, "partner-zen", "500");
    tick(g, &s, 26);
    act(g, "ok", "");
    act(g, "partner-ok", "");
    tick(g, &s, 4);
    assert(s.completed == 1 && s.zen == 9999500);
    assert(!mu_gfx_layer_count_item(l, 7171, 0));
    assert(mu_gfx_layer_count_item(l, 7169, 3) == 1);
    /* Reopen/cancel cannot duplicate the incoming item or erase it. */
    act(g, "trade", "Shopkeep");
    act(g, "accept", "");
    tick(g, &s, 1);
    act(g, "cancel", "");
    tick(g, &s, 1);
    assert(mu_gfx_layer_count_item(l, 7169, 3) == 1);
    /* A full destination refuses the result and preserves its balance and items. */
    int last = -1, added;
    while ((added = mu_gfx_layer_add_item(l, 7000, 0, 1, 1, "Filler")) >= 0)
        last = added;
    assert(last >= 0);
    mu_gfx_slot_item removed;
    int token = mu_gfx_layer_inventory_reserve(l, mu_gfx_layer_item_cell(l, last), &removed);
    assert(token);
    mu_gfx_layer_inventory_finish(l, token, 1);
    int before = mu_gfx_layer_items_placed(l);
    act(g, "trade", "Shopkeep");
    act(g, "accept", "");
    tick(g, &s, 1);
    act(g, "partner-item", "");
    act(g, "zen", "1000");
    tick(g, &s, 26);
    act(g, "ok", "");
    act(g, "partner-ok", "");
    /* Capacity changes after locking but before the delayed result. */
    assert(mu_gfx_layer_add_item(l, 7001, 0, 1, 1, "Late purchase") >= 0);
    tick(g, &s, 4);
    assert(!s.trade.open && s.trade.result == 2 && s.completed == 1 && s.zen == 9999500);
    assert(mu_gfx_layer_items_placed(l) == before + 1 && mu_gfx_layer_count_item(l, 7169, 3) == 1);
    act(g, "friends", "");
    mu_gfx_layer_invoke(l, MU_GFX_FRIENDS, NULL, "testCall", "[\"onClickTalkWithFriend\",\"Shopkeep\"]");
    assert(mu_gfx_layer_is_open(l, MU_GFX_MESSENGER));
    mu_gfx_layer_invoke(l, MU_GFX_MESSENGER, NULL, "testCall", "[\"LoadComplete\",1]");
    mu_gfx_layer_invoke(l, MU_GFX_MESSENGER, NULL, "testCall", "[\"AddChatText\",1,\"Hello friend\"]");
    mu_gfx_layer_invoke(l, MU_GFX_MESSENGER, NULL, "testCall",
                        "[\"AddChatText\",\"He said \\\"hello\\\" \\\\ end\\n\\u00e9\\ud83d\\ude00\",1]");
    act(g, "whisper", "Shopkeep Secret message");
    /* Detach/rebind models world travel while keeping the session alive. */
    world_gfx_social_close(g);
    s.players = NULL;
    free(p);
    p = calloc(1, sizeof *p);
    assert(p);
    s.players = p;
    g = world_gfx_social_open(l, &s);
    assert(g);
    tick(g, &s, 1);
    assert(s.party.count == 2 && s.completed == 1);
    assert(!s.party.members[1].in_view);
    world_gfx_social_close(g);
    mu_gfx_layer_close(l);
    free(p);
    puts("{\"social_gfx\":true,\"passed\":true}");
}
