/* Synthetic social integration over the existing recording GFx ABI. No client data. */
#include "../core/mu_world_players.h"
#include "../gfx/mu_gfx_layer.h"
#include "../world/world_gfx_social.h"
#include <assert.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>

static void tick(world_gfx_social *g, mu_social_session *s, int n) {
    for (int i = 0; i < n; i++) {
        mu_social_step(s, 0, 120, 120);
        world_gfx_social_frame(g);
    }
}
static void act(world_gfx_social *g, const char *v, const char *a) {
    assert(world_gfx_social_action(g, v, a));
}
static int metadata(void *user, int32_t code, mu_gfx_slot_item *out) {
    (void)user;
    out->width = code == 42 ? 2 : 1;
    out->height = code == 42 ? 3 : 1;
    out->trade_ban = code == 43;
    return 1;
}
static int allow_jewel(void *user, int jewel, const mu_mix_item *target, int visible) {
    (void)user;
    (void)visible;
    return jewel == 0x1c10 && target->code == 42;
}
static void mutated_wire(mu_gfx_layer *l) {
    uint8_t bytes[15] = {42, 0x0d, 77, 0x20, 5, 0x08, 0x95, 1, 52, 103, 254, 255, 6, 7, 8};
    mu_gfx_slot_item src;
    assert(mu_gfx_layer_social_item(l, bytes, &src));
    int idx = mu_gfx_layer_add_slot_item(l, &src);
    assert(idx >= 0);
    int cell = mu_gfx_layer_item_cell(l, idx);
    int jewel = mu_gfx_layer_add_item(l, 0x1c10, 0, 1, 1, "Synthetic jewel");
    assert(jewel >= 0);
    assert(mu_gfx_layer_mix_action(l, "mixresult", 1, 0));
    assert(mu_gfx_layer_mix_action(l, "jewel", mu_gfx_layer_item_cell(l, jewel), cell));
    mu_gfx_layer_advance(l, 160);
    bytes[1]++; /* only the option rank changes */
    mu_gfx_slot_item out;
    int token = mu_gfx_layer_inventory_reserve(l, cell, &out);
    assert(token && !memcmp(bytes, out.data, 15));
    mu_gfx_layer_inventory_finish(l, token, 0);
    assert(mu_gfx_layer_storage(l, "Vault", NULL, 0));
    assert(mu_gfx_layer_npc_action(l, "put", cell));
    assert(mu_gfx_layer_npc_action(l, "take", 0));
    mu_gfx_layer_npc_close(l);
    token = mu_gfx_layer_inventory_reserve(l, cell, &out);
    assert(token && !memcmp(bytes, out.data, 15));
    mu_gfx_layer_inventory_finish(l, token, 1);
}
static void full_item_trade(mu_gfx_layer *l, mu_world_players *p) {
    const uint8_t bytes[15] = {42, 0xcf, 77, 0x7f, 5, 0x08, 0x95, 1, 52, 103, 0xfe, 0xff, 6, 7, 8};
    mu_gfx_slot_item info;
    assert(mu_gfx_layer_social_item(l, bytes, &info) && info.width == 2 && info.height == 3);
    int idx = mu_gfx_layer_add_slot_item(l, &info);
    assert(idx >= 0);
    int original_cell = mu_gfx_layer_item_cell(l, idx);
    assert(mu_gfx_layer_storage(l, "Vault", NULL, 0));
    assert(mu_gfx_layer_npc_action(l, "put", original_cell + 1));
    assert(mu_gfx_layer_slot_items(l, MU_GFX_STORAGE) == 1);
    assert(mu_gfx_layer_npc_action(l, "take", 0));
    mu_gfx_layer_npc_close(l);
    mu_gfx_slot_item returned;
    int transfer = mu_gfx_layer_inventory_reserve(l, original_cell, &returned);
    assert(transfer && returned.has_data && !memcmp(returned.data, bytes, 15));
    mu_gfx_layer_inventory_finish(l, transfer, 0);
    assert(idx >= 0);
    mu_social_session s;
    mu_social_init(&s, "Hero", p);
    world_gfx_social *g = world_gfx_social_open(l, &s);
    assert(g);
    for (int commit = 0; commit < 2; commit++) {
        act(g, "trade", "Shopkeep");
        act(g, "accept", "");
        tick(g, &s, 1);
        char cell[24];
        snprintf(cell, sizeof cell, "%d", mu_gfx_layer_item_cell(l, idx));
        act(g, "offer", cell);
        assert(!memcmp(s.trade.items[0][0].bytes, bytes, sizeof bytes));
        act(g, "partner-item", "0,2acf4d7f050895013467feff060708");
        /* A second rectangle cannot overlap the first or cross the 8 x 4 grid. */
        assert(!world_gfx_social_action(g, "partner-item", "1,2acf4d7f050895013467feff060708"));
        assert(!s.trade.items[1][1].present);
        assert(!world_gfx_social_action(g, "partner-item", "7,2acf4d7f050895013467feff060708"));
        if (commit) {
            tick(g, &s, 26);
            act(g, "ok", "");
            act(g, "partner-ok", "");
            tick(g, &s, 4);
            assert(s.completed == 1);
        } else
            act(g, "cancel", "");
        assert(mu_gfx_layer_count_item(l, 42, 9) == 1);
        int token = mu_gfx_layer_inventory_reserve(l, mu_gfx_layer_item_cell(l, idx), &info);
        assert(token && info.has_data && info.width == 2 && info.height == 3);
        assert(!memcmp(info.data, bytes, sizeof bytes));
        mu_gfx_layer_inventory_finish(l, token, commit);
    }
    uint8_t banned[15] = {43};
    assert(mu_gfx_layer_social_item(l, banned, &info));
    idx = mu_gfx_layer_add_slot_item(l, &info);
    assert(idx >= 0);
    act(g, "trade", "Shopkeep");
    act(g, "accept", "");
    char cell[24];
    snprintf(cell, sizeof cell, "%d", mu_gfx_layer_item_cell(l, idx));
    assert(!world_gfx_social_action(g, "offer", cell));
    assert(mu_gfx_layer_count_item(l, 43, 0) == 1);
    act(g, "cancel", "");
    int token = mu_gfx_layer_inventory_reserve(l, mu_gfx_layer_item_cell(l, idx), &info);
    assert(token);
    mu_gfx_layer_inventory_finish(l, token, 1);
    world_gfx_social_close(g);
    mu_social_close(&s);
}
int main(int argc, char **argv) {
    assert(argc == 3);
    char error[512];
    mu_gfx_layer_config c = {.movie_dir = argv[1],
                             .lib_path = argv[2],
                             .width = 1280,
                             .height = 800,
                             .shared = 1,
                             .social_item_info = metadata,
                             .jewel_check = allow_jewel};
    mu_gfx_layer *l = mu_gfx_layer_open(&c, error, sizeof error);
    assert(l);
    mu_world_players *p = calloc(1, sizeof *p);
    assert(p);
    p->count = 1;
    p->list[0].in_view = 1;
    snprintf(p->list[0].spec.name, sizeof p->list[0].spec.name, "Shopkeep");
    mutated_wire(l);
    full_item_trade(l, p);
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
    mu_gfx_layer_invoke(l, MU_GFX_MESSENGER, NULL, "testCall", "[\"AddChatText\",\"Hello friend\",1]");
    mu_gfx_layer_invoke(l, MU_GFX_MESSENGER, NULL, "testCall",
                        "[\"AddChatText\",\"He said \\\"hello\\\" \\\\ end\\n\\u00e9\\ud83d\\ude00\",1]");
    /* Existing UI reconnection must update transport fields and continue delivery. */
    uint8_t reconnect[36] = {0};
    reconnect[18] = 201;
    reconnect[24] = 1;
    reconnect[35] = 1;
    memcpy(reconnect + 3, "offline", 7);
    memcpy(reconnect + 25, "Shopkeep", 8);
    assert(mu_social_messages_receive(&s.messages, 0x83, reconnect, sizeof reconnect));
    uint8_t text[10] = {0, 0, 4, 7, 5, 'A', 'g', 'a', 'i', 'n'};
    assert(mu_social_messages_receive_room(&s.messages, 1, 4, text, sizeof text));
    tick(g, &s, 1);
    mu_gfx_layer_invoke(l, MU_GFX_FRIENDS, NULL, "testCall", "[\"CloseWindow\",\"\"]");
    assert(!mu_gfx_layer_is_open(l, MU_GFX_FRIENDS));
    act(g, "whisper", "Shopkeep Secret message");
    act(g, "messenger", "Aeris");
    uint32_t aeris = s.messages.active_ui;
    assert(aeris != 1);
    act(g, "messenger", "Shopkeep");
    assert(s.messages.active_ui == 1);
    act(g, "mail", "Hero");
    uint32_t draft = s.messages.active_ui;
    mu_local_window *compose = mu_social_messages_window(&s.messages, draft);
    assert(compose);
    snprintf(compose->body, sizeof compose->body, "Draft survives travel");
    /* A serial can be reused by the server, but old messages retain their sender. */
    uint8_t new_user[15] = {0};
    memcpy(new_user + 5, "New", 3);
    assert(mu_social_messages_receive_room(&s.messages, 1, 1, new_user, sizeof new_user));
    assert(mu_social_messages_read(&s.messages, 1));
    tick(g, &s, 1);
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
    char load[96];
    snprintf(load, sizeof load, "[\"LoadComplete\",1]");
    mu_gfx_layer_invoke(l, MU_GFX_MESSENGER, NULL, "testCall", load);
    assert(mu_social_messages_window(&s.messages, draft));
    s.messages.capacity = s.messages.letter_count;
    assert(mu_social_messages_write(&s.messages, draft, "Hero", "Keep draft", "Draft survives travel"));
    tick(g, &s, 1);
    assert(mu_social_messages_window(&s.messages, draft));
    assert(s.party.count == 2 && s.completed == 1);
    assert(!s.party.members[1].in_view);
    world_gfx_social_close(g);
    mu_social_close(&s);
    mu_gfx_layer_close(l);
    free(p);
    puts("{\"social_gfx\":true,\"passed\":true}");
}
