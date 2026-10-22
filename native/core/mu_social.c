#include "mu_social.h"
#include "mu_world_players.h"
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
static void str10(char out[11], const char *s) { snprintf(out, 11, "%.10s", s ? s : ""); }
static void put32(uint8_t *p, int32_t v)
{
    uint32_t u = (uint32_t)v;
    for (int i = 0; i < 4; i++)
        p[i] = (uint8_t)(u >> (8 * i));
}
static int player(const mu_social_session *s, const char *name)
{
    for (int i = 0; s->players && i < s->players->count; i++)
        if (!strcmp(s->players->list[i].spec.name, name))
            return i;
    return -1;
}
static void party_packet(mu_social_session *s)
{
    uint8_t b[5 + 5 * 44] = {0xc2, 0, 0, 0x42, 0};
    int n = s->party.count;
    b[4] = (uint8_t)n;
    for (int i = 0; i < n; i++) {
        mu_party_member *m = &s->party.members[i];
        uint8_t *r = b + 5 + 44 * i;
        memcpy(r, m->name, 10);
        r[10] = (uint8_t)m->number;
        r[14] = (uint8_t)m->world;
        r[15] = (uint8_t)((uint32_t)m->world >> 8);
        r[16] = (uint8_t)m->x;
        r[17] = (uint8_t)m->y;
        put32(r + 20, m->hp);
        put32(r + 24, m->max_hp);
        put32(r + 28, m->server);
        put32(r + 32, m->mp);
        put32(r + 36, m->max_mp);
        r[40] = m->control;
        r[41] = m->special;
    }
    size_t len = 5 + (size_t)n * 44;
    b[1] = (uint8_t)(len >> 8);
    b[2] = (uint8_t)len;
    mu_social_receive(s, b, len);
    for (int i = 0; i < n; i++) {
        int k = player(s, s->party.members[i].name);
        s->party.members[i].in_view =
            (uint8_t)(k >= 0 ? s->players->list[k].in_view : !strcmp(s->party.members[i].name, s->hero));
    }
    s->revision++;
}
static void add_member(mu_social_session *s, const char *name)
{
    mu_party_member *m = &s->party.members[s->party.count++];
    memset(m, 0, sizeof *m);
    str10(m->name, name);
    m->number = s->party.count - 1;
    m->server = s->server;
    m->world = s->world;
    m->max_hp = m->hp = 100;
    m->max_mp = m->mp = 100;
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
    for (int i = 0; i < 9; i++)
        s->vitals[i][0] = s->vitals[i][1] = 100;
    uint8_t b[7 + MU_WORLD_PLAYERS_MAX * 11] = {0};
    int n = players ? players->count : 0;
    b[6] = (uint8_t)n;
    for (int i = 0; i < n; i++) {
        memcpy(b + 7 + i * 11, players->list[i].spec.name, 10);
        b[17 + i * 11] = 1;
    }
    mu_social_friends_receive(&s->friends, b, 7 + (size_t)n * 11);
    for (int i = 0; i < n; i++)
        if (players->list[i].spec.party && s->party.count < 5) {
            if (!s->party.count)
                add_member(s, s->hero);
            add_member(s, players->list[i].spec.name);
        }
    party_packet(s);
    if (n)
        str10(s->target, players->list[0].spec.name);
}
void mu_social_step(mu_social_session *s, int32_t world, int32_t x, int32_t y)
{
    s->steps++;
    s->world = world;
    s->x = x;
    s->y = y;
    int changed = 0;
    for (int i = 0; i < s->party.count; i++) {
        mu_party_member *m = &s->party.members[i];
        int k = player(s, m->name);
        int nx = x, ny = y, w = world, hp = s->vitals[k + 1][0], mp = s->vitals[k + 1][1];
        if (k >= 0) {
            const mu_world_player *p = &s->players->list[k];
            nx = p->c.tile[0];
            ny = p->c.tile[1];
            hp = p->c.dead ? 0 : hp;
        }
        if (k < 0 && strcmp(m->name, s->hero)) {
            if (m->in_view)
                changed = 1;
            m->in_view = 0;
            continue;
        }
        if (m->x != nx || m->y != ny || m->world != w || m->hp != hp || m->mp != mp ||
            m->in_view != (uint8_t)(k < 0 || s->players->list[k].in_view))
            changed = 1;
        m->x = nx;
        m->y = ny;
        m->world = w;
        m->hp = hp;
        m->mp = mp;
        m->in_view = (uint8_t)(k < 0 || s->players->list[k].in_view);
    }
    if (changed)
        party_packet(s);
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
int mu_social_receive(mu_social_session *s, const uint8_t *b, size_t n) {
    if (!s || !b || n < 4)
        return 0;
    if (b[0] == 0xc1 && b[2] == 0x40) {
        if (n < 5)
            return 0;
        /* Offline pending UI owns one inviter/key pair atomically. A second
         * request must not replace half of that outstanding invitation. */
        if (s->pending || s->trade.open)
            return 0;
        mu_social_party_request(b, n, 0, &s->request_key);
        int index = s->request_key - 0x200;
        if (s->players && index >= 0 && index < s->players->count)
            return mu_social_action(s, "incoming-party", s->players->list[index].spec.name);
        return 1; /* The original retains an unresolved request key without a popup. */
    }
    if (b[0] == 0xc1 && b[2] == 0x41) {
        s->party_notice = mu_social_party_notice(b[3]);
        s->revision++;
        return 1;
    }
    if (b[0] == 0xc1 && b[2] == 0x43) {
        if (n < 5)
            return 0;
        s->party_notice = b[4] == 0 ? 0x1f6 : 0;
    }
    if (!mu_social_party_receive(&s->party, b, n))
        return 0;
    s->revision++;
    return 1;
}
static void sent(mu_social_session *s) {
    s->requests++;
}
static int remove_party_member(mu_social_session *s, const char *who) {
    int k = -1;
    for (int i = 0; i < s->party.count; i++)
        if (!strcmp(s->party.members[i].name, who))
            k = i;
    int notice;
    if (mu_social_party_leave_prompt(s->world, k >= 0, !strcmp(who, s->hero), &notice) != 1) {
        s->party_notice = notice;
        return 0;
    }
    /* Movie visibility is client-side. The demo server independently enforces
     * leader/self authorization after the original request has been built. */
    if (!mu_social_party_remove(&s->request, (uint8_t)s->party.members[k].number, who, 1, !*who))
        return 0;
    sent(s);
    const char *requested = (const char *)s->request.data + 4;
    if (strcmp(requested, s->hero) && strcmp(s->party.members[0].name, s->hero))
        return 0;
    if (!strcmp(requested, s->hero)) {
        uint8_t b[5] = {0xc1, 5, 0x43, 0, 1};
        mu_social_receive(s, b, sizeof b);
    } else {
        memmove(s->party.members + k, s->party.members + k + 1,
                (size_t)(--s->party.count - k) * sizeof s->party.members[0]);
        party_packet(s);
    }
    return 1;
}
int mu_social_action(mu_social_session *s, const char *verb, const char *arg)
{
    if (!arg)
        arg = "";
    const char *name = arg[0] ? arg : s->target;
    if (!strcmp(verb, "target")) {
        if (player(s, name) < 0)
            return 0;
        str10(s->target, name);
    } else if (!strcmp(verb, "party") || !strcmp(verb, "trade") || !strcmp(verb, "incoming-party") ||
               !strcmp(verb, "incoming-trade")) {
        if (s->pending || s->trade.open || player(s, name) < 0)
            return 0;
        if (!strcmp(verb, "party")) {
            int world_blocked = (s->world >= 18 && s->world <= 23) || s->world == 53 || s->world == 97;
            int other_blocked = s->world >= 103 && s->world <= 106;
            if (!mu_social_party_permission(1, world_blocked, other_blocked, s->party.count != 0,
                                            !s->party.count || !strcmp(s->party.members[0].name, s->hero), 0,
                                            0, &s->party_notice))
                return 0;
            if (!mu_social_party_invite(&s->request, (uint16_t)(0x200 + player(s, name)), 1, 1))
                return 0;
            sent(s);
            int recipient = ((s->request.data[3] << 8) | s->request.data[4]) - 0x200;
            if (!s->players || recipient < 0 || recipient >= s->players->count)
                return 0;
            name = s->players->list[recipient].spec.name; /* offline server consumes serialized key */
        }
        if (strstr(verb, "party"))
            for (int i = 0; i < s->party.count; i++)
                if (!strcmp(s->party.members[i].name, name))
                    return 0;
        s->pending = strstr(verb, "party") ? 1 : 2;
        s->incoming = !strncmp(verb, "incoming", 8);
        if (s->incoming && s->pending == 1) {
            int key = 0x200 + player(s, name);
            uint8_t request[5] = {0xc1, 5, 0x40, (uint8_t)(key >> 8), (uint8_t)key};
            mu_social_party_request(request, sizeof request, 0, &s->request_key);
        }
        str10(s->pending_name, name);
        int is_friend = 0;
        for (int i = 0; i < s->friends.count; i++)
            is_friend |= !strcmp(s->friends.list[i].name, name);
        if (s->incoming && s->pending == 1 &&
            mu_social_party_autoaccept(s->auto_enabled, s->auto_friends, s->auto_guild, is_friend, 1,
                                       s->guild_id, -1))
            return mu_social_action(s, "accept", "");
    } else if (!strcmp(verb, "confirm-leave")) {
        int found = 0, notice;
        for (int i = 0; i < s->party.count; i++)
            found |= !strcmp(s->party.members[i].name, name);
        if (s->pending || mu_social_party_leave_prompt(s->world, found, !strcmp(name, s->hero), &notice) != 1)
            return 0;
        s->party_notice = notice;
        s->pending = 3;
        str10(s->pending_name, name);
    } else if (!strcmp(verb, "accept")) {
        if (!s->pending)
            return 0;
        if (s->pending == 3) {
            if (!mu_social_party_remove_confirm(0x37, 0))
                return 0;
            if (!remove_party_member(s, s->pending_name))
                return 0;
        } else if (s->pending == 1) {
            if (s->incoming) {
                int reply;
                if (!mu_social_party_popup(13, 0, &reply))
                    return 0;
                mu_social_party_answer(&s->request, (uint16_t)s->request_key, (uint8_t)reply);
                sent(s);
            }
            for (int i = 0; i < s->party.count; i++)
                if (!strcmp(s->party.members[i].name, s->pending_name))
                    return 0;
            if (s->party.count >= 5)
                return 0;
            if (!s->party.count) {
                if (s->incoming) {
                    add_member(s, s->pending_name);
                    add_member(s, s->hero);
                } else {
                    add_member(s, s->hero);
                    add_member(s, s->pending_name);
                }
            } else
                add_member(s, s->pending_name);
            party_packet(s);
        } else {
            uint8_t b[20] = {0xc1, 20, 0x54, 1};
            memcpy(b + 4, s->pending_name, 10);
            b[14] = 180;
            mu_social_trade_receive(&s->trade, b, 20);
        }
        s->pending = 0;
    } else if (!strcmp(verb, "decline")) {
        if (!s->pending)
            return 0;
        if (s->pending == 1 && s->incoming) {
            int reply;
            if (!mu_social_party_popup(13, 1, &reply))
                return 0;
            mu_social_party_answer(&s->request, (uint16_t)s->request_key, (uint8_t)reply);
            sent(s);
        }
        s->pending = 0;
        s->declined++;
    } else if (!strcmp(verb, "leave") || !strcmp(verb, "kick")) {
        const char *who = verb[0] == 'l' ? s->hero : name;
        if (!s->party.count || !remove_party_member(s, who))
            return 0;
    } else if (!strcmp(verb, "party-result")) {
        char *end;
        long result = strtol(arg, &end, 10);
        if (end == arg || *end || result < 0 || result > 255)
            return 0;
        uint8_t packet[4] = {0xc1, 4, 0x41, (uint8_t)result};
        return mu_social_receive(s, packet, sizeof packet);
    } else if (!strcmp(verb, "health")) {
        char who[11];
        int hp, mp;
        if (sscanf(arg, "%10[^,],%d,%d", who, &hp, &mp) != 3 || hp < 0 || hp > 100 || mp < 0 || mp > 100)
            return 0;
        int k = !strcmp(who, s->hero) ? 0 : player(s, who) + 1;
        if (k == 0 && strcmp(who, s->hero))
            return 0;
        s->vitals[k][0] = hp;
        s->vitals[k][1] = mp;
        uint8_t b[17] = {0xc1, 17, 0x44, 1, (uint8_t)hp, (uint8_t)mp};
        memcpy(b + 6, who, strlen(who));
        mu_social_receive(s, b, sizeof b);
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
