#include "mu_social.h"
#include "mu_world_players.h"
#include "../fixture/party_demo.h"
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
static void str10(char out[11], const char *s) { snprintf(out, 11, "%.10s", s ? s : ""); }
static void put32(uint8_t *p, int32_t v)
{
    for (int i = 0; i < 4; ++i) p[i] = (uint8_t)((uint32_t)v >> (8 * i));
}
static int player(const mu_social_session *s, const char *name)
{
    for (int i = 0; s->players && i < s->players->count; i++)
        if (!strcmp(s->players->list[i].spec.name, name))
            return i;
    return -1;
}
void mu_social_init(mu_social_session *s, const char *hero, struct mu_world_players *players)
{
    memset(s, 0, sizeof *s);
    str10(s->hero, hero && hero[0] ? hero : "Hero");
    s->players = players;
    s->server = 1;
    s->zen = 10000000;
    s->inventory[0] = s->inventory[1] = 1;
    s->trade.result = -1;
    s->guild_id = -1;
    mu_social_messages_init(&s->messages, s->hero);
    mu_social_messages_seed(
        &s->messages, "Shopkeep", "Local mail demo",
        "This mailbox is an offline demo. Read, reply, compose and delete stay on this Mac.");
    uint8_t b[7 + MU_WORLD_PLAYERS_MAX * 11] = {0};
    int n = players ? players->count : 0;
    b[6] = (uint8_t)n;
    for (int i = 0; i < n; i++) {
        memcpy(b + 7 + i * 11, players->list[i].spec.name, 10);
        b[17 + i * 11] = 1;
    }
    mu_social_friends_receive(&s->friends, b, 7 + (size_t)n * 11);
    mu_party_demo_open(s);
    if (n)
        str10(s->target, players->list[0].spec.name);
}
void mu_social_step(mu_social_session *s, int32_t world, int32_t x, int32_t y)
{
    s->steps++;
    s->world = world;
    s->x = x;
    s->y = y;
    mu_party_demo_step(s);
    if (s->trade.wait > 0)
        s->trade.wait--;
    if (s->result_due && s->steps >= s->result_due) {
        uint8_t b[4] = {0xc1, 4, 0xbd, 1};
        if (s->trade.zen[0] < 0 || s->trade.zen[0] > s->zen)
            b[3] = 2;
        if (b[3] == 1 && s->trade_commit && !s->trade_commit(s->trade_user))
            b[3] = 2;
        if (b[3] == 1) {
            s->zen += s->trade.zen[1] - s->trade.zen[0];
            s->completed++;
            for (int i = 0; i < 32; i++)
                s->received_items += s->trade.items[1][i].present;
        } else
            for (int i = 0; i < 2; i++)
                if (s->trade.items[0][i].present)
                    s->inventory[i] = 1;
        mu_social_trade_receive(&s->trade, b, 4);
        s->result_due = 0;
        s->revision++;
        snprintf(s->last, sizeof s->last, "Trade %s (offline demo)", b[3] == 1 ? "completed" : "refused");
    }
}
static void edit(mu_social_session *s)
{
    mu_social_trade_lock(&s->trade, 2);
    s->result_due = 0;
    s->revision++;
}
int mu_social_receive(mu_social_session *s, const uint8_t *b, size_t n)
{
    return s && mu_party_demo_receive(s, b, n);
}
void mu_social_close(mu_social_session *s)
{
    if (!s) return;
    mu_party_demo_close(s);
    mu_social_messages_destroy(&s->messages);
}
int mu_social_action(mu_social_session *s, const char *verb, const char *arg)
{
    if (!arg)
        arg = "";
    if (!strcmp(verb, "party") || !strcmp(verb, "incoming-party") ||
        !strcmp(verb, "confirm-leave") || !strcmp(verb, "leave") || !strcmp(verb, "kick") ||
        !strcmp(verb, "health") || !strcmp(verb, "party-result") ||
        ((!strcmp(verb, "accept") || !strcmp(verb, "decline")) && (s->pending == 1 || s->pending == 3)))
        return mu_party_demo_action(s, verb, arg);
    const char *name = arg[0] ? arg : s->target;
    if (!strcmp(verb, "target")) {
        if (player(s, name) < 0)
            return 0;
        str10(s->target, name);
    } else if (!strcmp(verb, "trade") || !strcmp(verb, "incoming-trade")) {
        if (s->pending || s->trade.open || player(s, name) < 0) return 0;
        s->pending = 2;
        s->incoming = !strcmp(verb, "incoming-trade");
        str10(s->pending_name, name);
    } else if (!strcmp(verb, "accept")) {
        if (s->pending != 2) return 0;
        {
            uint8_t b[20] = {0xc1, 20, 0x54, 1};
            memcpy(b + 4, s->pending_name, 10);
            b[14] = 180;
            mu_social_trade_receive(&s->trade, b, 20);
        }
        s->pending = 0;
    } else if (!strcmp(verb, "decline")) {
        if (!s->pending)
            return 0;
        s->pending = 0;
        s->declined++;
    } else if (!strcmp(verb, "friend")) {
        if (!name[0])
            return 0;
        if (!mu_social_friend_set(&s->friends, name, player(s, name) >= 0 ? 1 : 255))
            return 0;
    } else if (!strcmp(verb, "unfriend")) {
        if (!mu_social_friend_remove(&s->friends, name))
            return 0;
    } else if (!strcmp(verb, "offer") || !strcmp(verb, "remove")) {
        int i = atoi(arg);
        if (!s->trade.open || i < 0 || i >= 2 || s->trade.ok[0])
            return 0;
        mu_trade_item *q = &s->trade.items[0][i];
        if (verb[0] == 'o') {
            if (!s->inventory[i])
                return 0;
            memset(q, 0, sizeof *q);
            q->present = 1;
            q->bytes[0] = (uint8_t)(i ? 1 : 0);
            q->bytes[1] = 0x18;
            q->bytes[5] = 0xe0;
            s->inventory[i] = 0;
        } else {
            if (!q->present)
                return 0;
            q->present = 0;
            s->inventory[i] = 1;
        }
        edit(s);
    } else if (!strcmp(verb, "zen")) {
        char *end = NULL;
        long v = strtol(arg, &end, 10);
        if (!s->trade.open || s->trade.ok[0] || !arg[0] || *end || v < 0 || v > s->zen || v > INT32_MAX)
            return 0;
        s->trade.proposed_zen = (int32_t)v;
        uint8_t b[4] = {0xc1, 4, 0x73, 1};
        mu_social_trade_receive(&s->trade, b, 4);
        edit(s);
    } else if (!strcmp(verb, "partner-item")) {
        if (!s->trade.open)
            return 0;
        uint8_t b[19] = {0xc1, 19, 0x39, 0, 1, 0x18};
        b[9] = 0xe0;
        if (arg[0]) {
            char *end;
            long slot = strtol(arg, &end, 10);
            if (end == arg || *end != ',' || slot < 0 || slot >= 32 || strlen(end + 1) != 30)
                return 0;
            b[3] = (uint8_t)slot;
            for (int i = 0; i < 15; i++) {
                char hex[3] = {end[1 + i * 2], end[2 + i * 2], 0}, *tail;
                long byte = strtol(hex, &tail, 16);
                if (*tail || hex[0] == '-' || hex[0] == '+' || hex[0] == ' ')
                    return 0;
                b[4 + i] = (uint8_t)byte;
            }
        }
        mu_social_trade_receive(&s->trade, b, 19);
        edit(s);
    } else if (!strcmp(verb, "partner-zen")) {
        char *end = NULL;
        long amount = strtol(arg, &end, 10);
        if (!s->trade.open || !arg[0] || *end || amount < 0 || amount > INT32_MAX)
            return 0;
        uint8_t b[8] = {0xc1, 8, 0x3b, 0};
        put32(b + 4, (int32_t)amount);
        mu_social_trade_receive(&s->trade, b, 8);
        edit(s);
    } else if (!strcmp(verb, "ok") || !strcmp(verb, "partner-ok")) {
        if (!s->trade.open || s->trade.wait)
            return 0;
        if (verb[0] == 'o')
            s->trade.ok[0] = !s->trade.ok[0];
        else {
            uint8_t b[4] = {0xc1, 4, 0x3e, (uint8_t)!s->trade.ok[1]};
            mu_social_trade_receive(&s->trade, b, 4);
        }
        if (s->trade.ok[0] && s->trade.ok[1])
            s->result_due = s->steps + 3;
        else
            s->result_due = 0;
    } else if (!strcmp(verb, "cancel")) {
        if (!s->trade.open)
            return 0;
        for (int i = 0; i < 2; i++)
            if (s->trade.items[0][i].present)
                s->inventory[i] = 1;
        uint8_t b[4] = {0xc1, 4, 0xbd, 0};
        mu_social_trade_receive(&s->trade, b, 4);
        s->result_due = 0;
    } else
        return 0;
    s->revision++;
    snprintf(s->last, sizeof s->last, "%s %.80s (offline demo)", verb, arg);
    return 1;
}
