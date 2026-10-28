#include "../core/mu_social.h"
#include "../core/mu_world_players.h"
#include <assert.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
int main(void) {
    mu_world_players *p = calloc(1, sizeof *p);
    assert(p);
    p->count = 2;
    snprintf(p->list[0].spec.name, sizeof p->list[0].spec.name, "Aeris");
    snprintf(p->list[1].spec.name, sizeof p->list[1].spec.name, "Kyra");
    p->list[0].in_view = 1;
    p->list[0].c.tile[0] = 132;
    p->list[0].c.tile[1] = 121;
    mu_social_session s;
    mu_social_init(&s, "Hero", p);
    assert(mu_social_action(&s, "party", "Aeris"));
    assert(s.party.count == 0);
    assert(mu_social_action(&s, "decline", ""));
    assert(s.party.count == 0);
    assert(mu_social_action(&s, "incoming-party", "Aeris"));
    assert(mu_social_action(&s, "accept", ""));
    assert(s.party.count == 2);
    assert(!mu_social_action(&s, "kick", "Aeris"));
    assert(mu_social_action(&s, "leave", ""));
    assert(s.party.count == 0);
    assert(mu_social_action(&s, "party", "Aeris"));
    assert(mu_social_action(&s, "accept", ""));
    assert(mu_social_action(&s, "party", "Kyra"));
    assert(mu_social_action(&s, "accept", ""));
    mu_social_step(&s, 0, 120, 120);
    mu_party_marker m[5];
    assert(mu_social_party_markers(&s.party, "Hero", 1, 0, m) == 2);
    assert(m[0].x == 264 && m[0].y == 270);
    assert(mu_social_action(&s, "health", "Aeris,38,61"));
    assert(!strcmp(s.last, "health Aeris,38,61 (offline demo)"));
    mu_social_step(&s, 0, 120, 120);
    assert(s.party.members[1].hp_percent == 38 && s.party.members[1].mp_percent == 61);
    assert(mu_social_action(&s, "kick", "Kyra"));
    assert(s.party.count == 2);
    assert(mu_social_action(&s, "trade", "Aeris"));
    assert(mu_social_action(&s, "accept", ""));
    assert(mu_social_action(&s, "offer", "0"));
    assert(!s.inventory[0]);
    assert(!mu_social_action(&s, "ok", ""));
    assert(mu_social_action(&s, "cancel", ""));
    assert(s.inventory[0]);
    assert(!s.trade.open);
    assert(mu_social_action(&s, "trade", "Aeris"));
    assert(mu_social_action(&s, "accept", ""));
    assert(mu_social_action(&s, "offer", "0"));
    assert(mu_social_action(&s, "zen", "1000"));
    assert(mu_social_action(&s, "partner-item", ""));
    for (int i = 0; i < 26; i++)
        mu_social_step(&s, 0, 120, 120);
    assert(mu_social_action(&s, "ok", ""));
    assert(mu_social_action(&s, "partner-ok", ""));
    for (int i = 0; i < 4; i++)
        mu_social_step(&s, 0, 120, 120);
    assert(!s.trade.open && s.completed == 1 && s.received_items == 1 && s.zen == 9999000);
    assert(!mu_social_action(&s, "ok", ""));
    assert(mu_social_action(&s, "unfriend", "Kyra"));
    assert(s.friends.count == 1);
    s.auto_enabled = s.auto_friends = 1;
    assert(mu_social_action(&s, "incoming-party", "Kyra"));
    assert(s.pending == 1); /* removed friends must require explicit approval */
    assert(mu_social_action(&s, "decline", ""));
    assert(mu_social_action(&s, "friend", "Kyra"));
    assert(s.friends.count == 2);
    uint8_t answer[4] = {0xc1, 4, 0x41, 13};
    int members = s.party.count;
    int saved_key = s.request_key;
    assert(mu_social_receive(&s, answer, sizeof answer) && s.party_notice == 0x1263 &&
           s.party.count == members);
    uint8_t clear[5] = {0xc1, 5, 0x43, 0, 0};
    assert(mu_social_receive(&s, clear, sizeof clear) && s.party.count == 0 && s.request_key == saved_key &&
           s.party_notice == 0x1f6);
    s.auto_enabled = 0;
    uint8_t invite_a[5] = {0xc1, 5, 0x40, 2, 0}, invite_b[5] = {0xc1, 5, 0x40, 2, 1};
    assert(mu_social_receive(&s, invite_a, 5) && s.request_key == 0x200 && s.pending == 1);
    assert(!mu_social_receive(&s, invite_b, 5) && s.request_key == 0x200);
    assert(mu_social_action(&s, "accept", "") && s.request.data[4] == 2 && s.request.data[5] == 0);
    int aeris = 0, kyra = 0;
    for (int i = 0; i < s.party.count; i++) {
        aeris += !strcmp(s.party.members[i].name, "Aeris");
        kyra += !strcmp(s.party.members[i].name, "Kyra");
    }
    assert(aeris == 1 && kyra == 0);
    mu_social_close(&s);
    free(p);
    puts("{\"social_session\":true,\"passed\":true}");
    return 0;
}
