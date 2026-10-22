#include "world_gfx_social.h"
#include "../../reconstructed/hud/item_slots.h"
#include "../gfx/mu_gfx_layer.h"
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
struct world_gfx_social {
    mu_gfx_layer *l;
    mu_social_session *s;
    int revision, party, friends, trade;
    float x[2], y[2], w[2], h[2];
    int prompt;
    char map_path[160];
    int tokens[32];
    mu_gfx_slot_item escrow[32];
    int messenger;
    char room_name[11];
};
/* JSON strings preserve UTF-8; control bytes are escaped. No game data in source. */
static void quote(char *o, size_t cap, const char *s)
{
    size_t n = 0;
    o[n++] = '"';
    for (; s && *s && n + 7 < cap; s++) {
        unsigned char c = (unsigned char)*s;
        if (c == '"' || c == '\\') {
            o[n++] = '\\';
            o[n++] = (char)c;
        } else if (c < 32)
            n += (size_t)snprintf(o + n, cap - n, "\\u%04x", c);
        else
            o[n++] = (char)c;
    }
    o[n++] = '"';
    o[n] = 0;
}
static void call(world_gfx_social *g, int id, const char *fn, const char *args)
{
    mu_gfx_layer_invoke(g->l, id, NULL, fn, args);
}
static void notice(world_gfx_social *g, const char *s) { mu_gfx_layer_chat(g->l, 3, "", s); }
static int item_code(const uint8_t b[15])
{
    return b[0] | ((b[3] & 0x80) << 1) | ((b[5] & 0xf0) << 5) | ((b[5] & 1) << 13);
}
static void whisper(world_gfx_social *g, const char *name, const char *text, int incoming)
{
    if (!name[0] || !text[0])
        return;
    uint8_t b[73] = {0xc1, 73, 2};
    size_t n = strlen(name);
    if (n > 10)
        n = 10;
    memcpy(b + 3, name, n);
    n = strlen(text);
    if (n > 60)
        n = 60;
    memcpy(b + 13, text, n);
    char from[11], msg[61];
    if (mu_social_whisper(b, sizeof b, 0, 0, from, msg))
        mu_gfx_layer_chat(g->l, 2, incoming ? from : g->s->hero, msg);
}
static void restore_offer(world_gfx_social *g)
{
    /* Success commits through the session callback before zen/results change. */
    for (int i = 0; i < 32; i++)
        if (g->tokens[i]) {
            mu_gfx_layer_inventory_finish(g->l, g->tokens[i], 0);
            g->tokens[i] = 0;
        }
}
static int commit_trade(void *user)
{
    world_gfx_social *g = user;
    mu_gfx_slot_item incoming[32];
    int n = 0;
    for (int i = 0; i < 32; i++)
        if (g->s->trade.items[1][i].present) {
            const uint8_t *b = g->s->trade.items[1][i].bytes;
            mu_gfx_slot_item *d = &incoming[n++];
            memset(d, 0, sizeof *d);
            d->code = item_code(b);
            d->level = (b[1] >> 3) & 15;
            d->width = d->height = 1;
            snprintf(d->name, sizeof d->name, "Trade item (demo)");
        }
    if (!mu_gfx_layer_inventory_exchange(g->l, g->tokens, incoming, n))
        return 0;
    memset(g->tokens, 0, sizeof g->tokens);
    return 1;
}
static int offer(world_gfx_social *g, int cell)
{
    if (!g->s->trade.open || g->s->trade.ok[0])
        return 0;
    mu_gfx_slot_item item;
    int token = mu_gfx_layer_inventory_reserve(g->l, cell, &item);
    if (!token)
        return 0;
    int slot = -1;
    for (int y = 0; y + item.height <= 4 && slot < 0; y++)
        for (int x = 0; x + item.width <= 8 && slot < 0; x++) {
            int fits = 1;
            for (int j = 0; j < 32; j++)
                if (g->tokens[j]) {
                    int xx = j % 8, yy = j / 8;
                    if (x < xx + g->escrow[j].width && x + item.width > xx && y < yy + g->escrow[j].height &&
                        y + item.height > yy)
                        fits = 0;
                }
            if (fits)
                slot = y * 8 + x;
        }
    if (slot < 0) {
        mu_gfx_layer_inventory_finish(g->l, token, 0);
        return 0;
    }
    g->tokens[slot] = token;
    g->escrow[slot] = item;
    mu_trade_item *t = &g->s->trade.items[0][slot];
    memset(t, 0, sizeof *t);
    t->present = 1;
    t->bytes[0] = (uint8_t)item.code;
    t->bytes[1] = (uint8_t)(item.level << 3);
    t->bytes[3] = (uint8_t)((item.code >> 1) & 0x80);
    t->bytes[5] = (uint8_t)(((item.code >> 5) & 0xf0) | ((item.code >> 13) & 1));
    mu_social_trade_lock(&g->s->trade, 2);
    g->s->result_due = 0;
    g->s->revision++;
    return 1;
}
static int inventory(void *user, int cell)
{
    world_gfx_social *g = user;
    if (!g->s->trade.open)
        return 0;
    if (!offer(g, cell))
        notice(g, "Item cannot be offered here, or the offer is locked.");
    return 1;
}
static void messenger(world_gfx_social *g, const char *name)
{
    char q[128], b[512];
    quote(q, sizeof q, name);
    snprintf(g->room_name, sizeof g->room_name, "%.10s", name);
    call(
        g, MU_GFX_MESSENGER, "InitText",
        "[[\"Write\",\"Read\",\"Reply\",\"Delete\",\"Messenger\",\"Invite\",\"Delete\",\"Previous\",\"Next\","
        "\"Close\",\"Send\",\"Recipient\",\"Title\",\"Offline demo\",\"Close invite\",\"Send\"]]");
    char hero[64];
    quote(hero, sizeof hero, g->s->hero);
    snprintf(b, sizeof b, "[%s]", hero);
    call(g, MU_GFX_MESSENGER, "SetHeroName", b);
    call(g, MU_GFX_MESSENGER, "ClearWindow", "[]");
    snprintf(b, sizeof b, "[1,560,140,%s,0,\"\",0]", q);
    call(g, MU_GFX_MESSENGER, "AddChatRoom1", b);
    mu_gfx_layer_show(g->l, MU_GFX_MESSENGER, 1);
    g->messenger = 1;
}
int world_gfx_social_action(world_gfx_social *g, const char *verb, const char *arg)
{
    if (!g)
        return 0;
    if (!arg)
        arg = "";
    if (!strcmp(verb, "messenger")) {
        messenger(g, arg[0] ? arg : g->s->target);
        return 1;
    }
    if (!strcmp(verb, "offer"))
        return offer(g, atoi(arg));
    if (!strcmp(verb, "remove")) {
        int i = atoi(arg);
        if (i >= 0 && i < 32 && !g->tokens[i])
            for (int j = 0; j < 32; j++)
                if (g->tokens[j] && i % 8 >= j % 8 && i % 8 < j % 8 + g->escrow[j].width && i / 8 >= j / 8 &&
                    i / 8 < j / 8 + g->escrow[j].height) {
                    i = j;
                    break;
                }
        if (i < 0 || i >= 32 || !g->tokens[i] || g->s->trade.ok[0])
            return 0;
        mu_gfx_layer_inventory_finish(g->l, g->tokens[i], 0);
        g->tokens[i] = 0;
        g->s->trade.items[0][i].present = 0;
        mu_social_trade_lock(&g->s->trade, 2);
        g->s->result_due = 0;
        g->s->revision++;
        return 1;
    }
    if (!strcmp(verb, "friends")) {
        g->friends = !g->friends;
        mu_gfx_layer_show(g->l, MU_GFX_FRIENDS, g->friends);
        g->revision = -1;
        return 1;
    }
    if (!strcmp(verb, "party-window")) {
        g->party = !g->party;
        mu_gfx_layer_show(g->l, MU_GFX_PARTY, g->party);
        call(g, MU_GFX_PARTY, g->party ? "openWindow" : "closeWindow", "[]");
        g->revision = -1;
        return 1;
    }
    if (!strcmp(verb, "whisper") || !strcmp(verb, "receive-whisper")) {
        char name[11] = "";
        const char *text = strchr(arg, ' ');
        if (!text)
            return 0;
        size_t n = (size_t)(text - arg);
        if (n > 10)
            return 0;
        memcpy(name, arg, n);
        whisper(g, name, text + 1, verb[0] == 'r');
        return 1;
    }
    int was_open = g->s->trade.open;
    int ok = mu_social_action(g->s, verb, arg);
    if (g->s->result_due) {
        int count = 0;
        for (int i = 0; i < 32; i++)
            count += g->s->trade.items[1][i].present;
        if (!mu_gfx_layer_inventory_can_receive(g->l, count)) {
            mu_social_trade_result(&g->s->trade, 2);
            g->s->result_due = 0;
            g->s->revision++;
            snprintf(g->s->last, sizeof g->s->last, "Trade refused: inventory is full (offline demo)");
        }
    }
    if (was_open && !g->s->trade.open) {
        restore_offer(g);
        g->trade = 0;
    }
    notice(g, ok ? g->s->last : "Social action refused (offline demo)");
    return ok;
}
static int chat(void *user, const char *recipient, const char *text)
{
    world_gfx_social *g = user;
    if (recipient[0]) {
        whisper(g, recipient, text, 0);
        return 1;
    }
    if (text[0] != '/')
        return 0;
    char verb[40] = "";
    const char *p = strchr(text, ' ');
    size_t n = p ? (size_t)(p - text - 1) : strlen(text + 1);
    if (n >= sizeof verb)
        return 0;
    memcpy(verb, text + 1, n);
    if (!strcmp(verb, "w"))
        snprintf(verb, sizeof verb, "whisper");
    world_gfx_social_action(g, verb, p ? p + 1 : "");
    return 1;
}
static void field(const char *json, const char *name, char *out, size_t cap)
{
    char key[64];
    snprintf(key, sizeof key, "\"%s\"", name);
    const char *p = strstr(json, key);
    if (!p) {
        out[0] = 0;
        return;
    }
    p = strchr(p + strlen(key), ':');
    if (!p) {
        out[0] = 0;
        return;
    }
    p++;
    while (*p == ' ')
        p++;
    if (*p == '"')
        p++;
    size_t n = 0;
    while (*p && *p != '"' && *p != ',' && *p != '}' && n + 1 < cap)
        out[n++] = *p++;
    out[n] = 0;
}
static int hex4(const char *p)
{
    int value = 0;
    for (int i = 0; i < 4; i++) {
        int c = (unsigned char)p[i];
        int d = c >= '0' && c <= '9'   ? c - '0'
                : c >= 'a' && c <= 'f' ? c - 'a' + 10
                : c >= 'A' && c <= 'F' ? c - 'A' + 10
                                       : -1;
        if (d < 0)
            return -1;
        value = value * 16 + d;
    }
    return value;
}
/* First string argument from the GFx JSON array. Preserve escaped quotes, controls and Unicode. */
static int first_string(const char *json, char *out, size_t cap)
{
    const char *p = strchr(json, '"');
    size_t n = 0;
    if (!p || !cap)
        return 0;
    p++;
    while (*p && *p != '"') {
        unsigned c = (unsigned char)*p++;
        if (c == '\\') {
            c = (unsigned char)*p++;
            if (!c)
                return 0;
            if (c == 'u') {
                if (strlen(p) < 4)
                    return 0;
                int h = hex4(p);
                if (h < 0)
                    return 0;
                c = (unsigned)h;
                p += 4;
                if (c >= 0xd800 && c <= 0xdbff && strlen(p) >= 6 && p[0] == '\\' && p[1] == 'u') {
                    int low = hex4(p + 2);
                    if (low >= 0xdc00 && low <= 0xdfff) {
                        c = 0x10000 + ((c - 0xd800) << 10) + (unsigned)low - 0xdc00;
                        p += 6;
                    }
                }
                if (c >= 0xd800 && c <= 0xdfff)
                    c = 0xfffd;
                unsigned bytes = c < 0x80 ? 1 : c < 0x800 ? 2 : c < 0x10000 ? 3 : 4;
                if (n + bytes >= cap)
                    return 0;
                if (bytes == 1)
                    out[n++] = (char)c;
                else {
                    out[n++] = (char)((bytes == 2   ? 0xc0u
                                       : bytes == 3 ? 0xe0u
                                                    : 0xf0u) |
                                      (c >> (6 * (bytes - 1))));
                    for (unsigned i = bytes - 1; i > 0; i--)
                        out[n++] = (char)(0x80 | ((c >> (6 * (i - 1))) & 63));
                }
                continue;
            }
            if (c == 'n')
                c = '\n';
            else if (c == 'r')
                c = '\r';
            else if (c == 't')
                c = '\t';
            else if (c == 'b')
                c = '\b';
            else if (c == 'f')
                c = '\f';
            else if (c != '\\' && c != '"' && c != '/')
                return 0;
        }
        if (n + 1 >= cap)
            return 0;
        out[n++] = (char)c;
    }
    out[n] = 0;
    return *p == '"';
}
static void window(void *user, int id, const char *name, const char *args)
{
    world_gfx_social *g = user;
    char v[64] = "";
    field(args, "name", v, sizeof v);
    if (!strcmp(name, "UIInit") || !strcmp(name, "onLoad")) {
        g->revision = -1;
        return;
    }
    if (id == MU_GFX_PARTY) {
        if (!strcmp(name, "onLeave"))
            world_gfx_social_action(g, !strcmp(v, g->s->hero) ? "leave" : "kick", v);
        else if (!strcmp(name, "onMemberClickR")) {
            char q[128];
            quote(q, sizeof q, v);
            char b[160];
            snprintf(b, sizeof b, "[%s]", q);
            mu_gfx_layer_invoke(g->l, MU_GFX_CHAT, NULL, "SetWhisper", b);
        }
    } else if (id == MU_GFX_TRADE) {
        if (!strcmp(name, "requestSlotInfo")) {
            double x, y, w, h, k;
            if (sscanf(args, "[ %lf , %lf , %lf , %lf , %lf", &x, &y, &w, &h, &k) == 5 && k >= 0 && k < 2) {
                int i = (int)k;
                g->x[i] = (float)x;
                g->y[i] = (float)y;
                g->w[i] = (float)w;
                g->h[i] = (float)h;
            }
        } else if (!strcmp(name, "CloseWindow"))
            world_gfx_social_action(g, "cancel", "");
        else if (!strcmp(name, "requestItemSlotClick") || !strcmp(name, "requestItemSlotClickR")) {
            int i = atoi(args + 1);
            if (i >= 32 && i < 64) {
                char b[16];
                snprintf(b, sizeof b, "%d", i - 32);
                world_gfx_social_action(g, "remove", b);
            }
        } else if (!strcmp(name, "onClickbtnTrade")) {
            world_gfx_social_action(g, "ok", "");
            if (!g->s->trade.ok[1])
                world_gfx_social_action(g, "partner-ok", "");
        } else if (!strcmp(name, "onClickbtnInputZen"))
            notice(g, "Enter /zen AMOUNT in chat to set your trade offer.");
    } else if (id == MU_GFX_FRIENDS) {
        if (!strcmp(name, "CloseWindow")) {
            g->friends = 0;
            mu_gfx_layer_show(g->l, id, 0);
        } else if (!strcmp(name, "onClickAddFriend"))
            notice(g, "Enter /friend NAME in chat.");
        else if (!strcmp(name, "onClickDeleteFriend") || !strcmp(name, "onClickTalkWithFriend")) {
            const char *p = strchr(args, '"');
            if (p) {
                size_t n = strcspn(p + 1, "\"");
                if (n > 10)
                    n = 10;
                memcpy(v, p + 1, n);
                v[n] = 0;
            }
            if (strstr(name, "Delete"))
                world_gfx_social_action(g, "unfriend", v);
            else {
                char q[64], b[96];
                quote(q, sizeof q, v);
                snprintf(b, sizeof b, "[%s]", q);
                mu_gfx_layer_invoke(g->l, MU_GFX_CHAT, NULL, "SetWhisper", b);
                messenger(g, v);
            }
        }
    } else if (id == MU_GFX_MESSENGER) {
        char b[2304], q[2048];
        if (!strcmp(name, "LoadComplete")) {
            quote(q, sizeof q, g->s->hero);
            snprintf(b, sizeof b, "[1,%s,0,\"Offline demo\"]", q);
            call(g, id, "AddFriendAtChatRoom", b);
            quote(q, sizeof q, g->room_name);
            snprintf(b, sizeof b, "[1,%s,1,\"Offline demo\"]", q);
            call(g, id, "AddFriendAtChatRoom", b);
            char title[128];
            snprintf(title, sizeof title, "%s (offline demo)", g->room_name);
            quote(q, sizeof q, title);
            snprintf(b, sizeof b, "[1,%s]", q);
            call(g, id, "SetChatTitle", b);
            call(g, id, "AddChatText", "[1,1,\"Offline demo room. Messages remain on this Mac.\"]");
        } else if (!strcmp(name, "AddChatText")) {
            char msg[256] = "";
            if (!first_string(args, msg, sizeof msg))
                return;
            quote(q, sizeof q, msg);
            snprintf(b, sizeof b, "[1,0,%s]", q);
            call(g, id, "AddChatText", b);
        } else if (!strcmp(name, "CloseWindow") || !strcmp(name, "CloseFriendWindow")) {
            call(g, id, "ClearWindow", "[]");
            mu_gfx_layer_show(g->l, id, 0);
            g->messenger = 0;
        }
    }
}
static int key(void *user, int vk)
{
    world_gfx_social *g = user;
    if (vk == 'F')
        return world_gfx_social_action(g, "friends", "");
    if (vk == 'P')
        return world_gfx_social_action(g, "party-window", "");
    if (g->s->pending && (vk == 'Y' || vk == 'N'))
        return world_gfx_social_action(g, vk == 'Y' ? "accept" : "decline", "");
    if (vk == 27 && g->s->trade.open)
        return world_gfx_social_action(g, "cancel", "");
    return 0;
}
world_gfx_social *world_gfx_social_open(struct mu_gfx_layer *l, mu_social_session *s)
{
    if (!l || !s)
        return NULL;
    world_gfx_social *g = calloc(1, sizeof *g);
    if (!g)
        return NULL;
    g->l = l;
    g->s = s;
    s->trade_commit = commit_trade;
    s->trade_user = g;
    g->revision = -1;
    g->party = 1;
    mu_gfx_social_hooks h = {g, window, key, chat, inventory};
    mu_gfx_layer_set_social_hooks(l, &h);
    const char *path = mu_gfx_layer_path(l, MU_GFX_TRADE);
    for (int i = 0; i < 2; i++) {
        const char *fields[] = {"_x", "_y", "_width", "_height"};
        float *out[] = {&g->x[i], &g->y[i], &g->w[i], &g->h[i]};
        for (int k = 0; k < 4; k++) {
            char p[192];
            snprintf(p, sizeof p, "%s.mcTrade.isSlot%d.%s", path, i * 32, fields[k]);
            const char *v = mu_gfx_layer_get_variable(l, MU_GFX_TRADE, p);
            *out[k] = v ? (float)atof(v) : 0;
        }
    }
    return g;
}
void world_gfx_social_close(world_gfx_social *g)
{
    if (!g)
        return;
    if (g->s->trade.open)
        mu_social_action(g->s, "cancel", "");
    restore_offer(g);
    mu_gfx_layer_trade_items(g->l, NULL, 0);
    mu_gfx_layer_set_social_hooks(g->l, NULL);
    g->s->trade_commit = NULL;
    g->s->trade_user = NULL;
    free(g);
}
void world_gfx_social_frame(world_gfx_social *g)
{
    if (!g)
        return;
    mu_social_session *s = g->s;
    if (g->prompt != s->pending) {
        g->prompt = s->pending;
        if (s->pending) {
            char t[192];
            snprintf(t, sizeof t, "%s %s request: %s. Y accept, N decline (offline demo)",
                     s->incoming ? "Incoming" : "Outgoing", s->pending == 1 ? "party" : "trade",
                     s->pending_name);
            notice(g, t);
        }
    }
    const char *map_path = mu_gfx_layer_channel_path(g->l, "hudMap");
    if (map_path && strcmp(g->map_path, map_path)) {
        snprintf(g->map_path, sizeof g->map_path, "%s", map_path);
        g->revision = -1;
    }
    if (g->trade && !s->trade.open) {
        restore_offer(g);
        notice(g, s->last);
    }
    g->trade = s->trade.open;
    if (g->revision != s->revision) {
        g->revision = s->revision;
        char b[8192], q[128];
        size_t n = 0;
        if (g->party) {
            call(g, MU_GFX_PARTY, "InitText",
                 "[{\"MenuTitle\":\"Party\",\"PartyMemberMove\":\"Move\",\"Mandate\":\"Delegate\","
                 "\"CancelMandate\":\"Cancel\"}]");
            n = (size_t)snprintf(b, sizeof b, "[[");
            for (int i = 0; i < s->party.count; i++) {
                mu_party_member *m = &s->party.members[i];
                quote(q, sizeof q, m->name);
                n += (size_t)snprintf(
                    b + n, sizeof b - n,
                    "%s{\"sortIndex\":%d,\"name\":%s,\"nameColor\":\"ABABAB\",\"channelIndex\":%"
                    "d,\"channelName\":\"%d\",\"hp\":%d,\"mp\":%d,\"MastetrIsHero\":%s,"
                    "\"isMaster\":%s,\"isMe\":%s,\"state\":%d,\"arrBuffs\":[]}",
                    i ? "," : "", i, q, m->server, m->server, m->hp_percent, m->mp_percent,
                    s->party.count && !strcmp(s->party.members[0].name, s->hero) ? "true" : "false",
                    i == 0 ? "true" : "false", !strcmp(m->name, s->hero) ? "true" : "false",
                    mu_social_party_state(m->server, m->in_view));
            }
            snprintf(b + n, sizeof b - n, "]]");
            call(g, MU_GFX_PARTY, "SetMemberInfo", b);
            mu_gfx_layer_show(g->l, MU_GFX_PARTY, s->party.count > 0);
        }
        if (g->friends) {
            call(g, MU_GFX_FRIENDS, "InitText",
                 "[[\"Friends\",\"Add friend\",\"Delete friend\",\"Whisper\",\"Write "
                 "letter\",\"Friends\",\"Windows\",\"Mail\",\"Name\",\"Server\",\"Block\",\"Hide\",\"Write "
                 "letter\",\"Read\",\"Reply\",\"Delete "
                 "letter\",\"Name\",\"Date\",\"Title\",\"Windows\",\"Recipient\",\"Title\",\"Party "
                 "invitation\"]]");
            call(g, MU_GFX_FRIENDS, "OpenFriendList", "[]");
            n = (size_t)snprintf(b, sizeof b, "[[");
            for (int i = 0; i < s->friends.count; i++) {
                quote(q, sizeof q, s->friends.list[i].name);
                n += (size_t)snprintf(b + n, sizeof b - n,
                                      "%s{\"CharacterID\":%s,\"Server\":\"%s\",\"Number\":%d}", i ? "," : "",
                                      q, s->friends.list[i].server == 255 ? "Offline" : "1",
                                      s->friends.list[i].server);
            }
            snprintf(b + n, sizeof b - n, "]]");
            call(g, MU_GFX_FRIENDS, "AddFriends", b);
        }
        mu_trade *t = &s->trade;
        mu_gfx_layer_show(g->l, MU_GFX_TRADE, t->open);
        if (t->open) {
            call(g, MU_GFX_TRADE, "InitTitle", "[\"Trade (offline demo)\"]");
            call(g, MU_GFX_TRADE, "InitTrade",
                 "[\"Partner\",\"Guild\",\"Level\",\"Caution\",\"Check both offers before locking.\",\"Your "
                 "name\",\"Locked\"]");
            call(g, MU_GFX_TRADE, "InitBtnTitle", "[\"OK\",\"Input zen\",\"Lock offer\"]");
            char hero[64];
            quote(q, sizeof q, t->name);
            quote(hero, sizeof hero, s->hero);
            snprintf(b, sizeof b, "[%s,\"\",\"%d\",%s]", q, t->level, hero);
            call(g, MU_GFX_TRADE, "SetTradeValue", b);
            snprintf(b, sizeof b, "[\"%d\"]", t->zen[0]);
            call(g, MU_GFX_TRADE, "SetMyTradeZen", b);
            snprintf(b, sizeof b, "[\"%d\"]", t->zen[1]);
            call(g, MU_GFX_TRADE, "SetOtherTradeZen", b);
            call(g, MU_GFX_TRADE, "ReceiveMyOk", t->ok[0] ? "[true]" : "[false]");
            call(g, MU_GFX_TRADE, "ReceiveOtherOk", t->ok[1] ? "[true]" : "[false]");
            for (int side = 0; side < 2; side++) {
                n = (size_t)snprintf(b, sizeof b, "[%d,\"", side);
                for (int i = 0; i < 32; i++) {
                    int occupied = t->items[1 - side][i].present;
                    if (side == 1)
                        for (int j = 0; j < 32; j++)
                            if (g->tokens[j] && i % 8 >= j % 8 && i % 8 < j % 8 + g->escrow[j].width &&
                                i / 8 >= j / 8 && i / 8 < j / 8 + g->escrow[j].height)
                                occupied = 1;
                    n += (size_t)snprintf(b + n, sizeof b - n, "%s%d", i ? "," : "", occupied ? 1 : 0);
                }
                snprintf(b + n, sizeof b - n, "\"]");
                call(g, MU_GFX_TRADE, "SetSlotStateAll", b);
            }
        }
    }
    char b[2048], q[128];
    const char *map = mu_gfx_layer_channel_path(g->l, "hudMap");
    if (map && map[0]) {
        mu_party_marker marks[5];
        int count = mu_social_party_markers(&s->party, s->hero, s->server, s->world, marks);
        size_t n = (size_t)snprintf(b, sizeof b, "[[");
        for (int i = 0; i < count; i++) {
            quote(q, sizeof q, marks[i].name);
            n += (size_t)snprintf(b + n, sizeof b - n,
                                  "%s{\"type\":10,\"key\":%d,\"text\":%s,\"x\":%g,\"y\":%g}", i ? "," : "",
                                  marks[i].key, q, (double)marks[i].x, (double)marks[i].y);
        }
        snprintf(b + n, sizeof b - n, "]]");
        mu_gfx_layer_invoke(g->l, MU_GFX_MAIN, map, "setPartyUnits", b);
    }
    /* Models over both 8 x 4 grids use the existing RenderItem3D host. Geometry is movie-reported. */
    int32_t stage_w = 1280, stage_h = 800;
    mu_gfx_layer_stage_size(g->l, &stage_w, &stage_h);
    mu_gfx_item_draw items[64];
    int count = 0;
    if (s->trade.open) {
        const char *path = mu_gfx_layer_path(g->l, MU_GFX_TRADE);
        (void)path;
        float ox = 0, oy = 0;
        mu_gfx_layer_window_position(g->l, MU_GFX_TRADE, &ox, &oy);
        float sc = mu_gfx_layer_window_scale(g->l, MU_GFX_TRADE);
        for (int side = 0; side < 2; side++)
            for (int i = 0; i < 32; i++)
                if (s->trade.items[side][i].present) {
                    int k = 1 - side;
                    mu_gfx_item_draw *d = &items[count++];
                    memset(d, 0, sizeof *d);
                    d->item = i;
                    d->code = item_code(s->trade.items[side][i].bytes);
                    d->level = (s->trade.items[side][i].bytes[1] >> 3) & 15;
                    d->rect[0] = ox + (g->x[k] + (float)(i % 8) * (g->w[k] + 1)) * sc;
                    d->rect[1] = oy + (g->y[k] + (float)(i / 8) * (g->h[k] + 1)) * sc;
                    d->rect[2] = g->w[k] * sc * (float)(side == 0 && g->tokens[i] ? g->escrow[i].width : 1);
                    d->rect[3] = g->h[k] * sc * (float)(side == 0 && g->tokens[i] ? g->escrow[i].height : 1);
                    d->slot[0] = d->rect[0] * mu_gfx_rate_x(stage_w);
                    d->slot[1] = d->rect[1] * mu_gfx_rate_y(stage_h);
                    d->slot[2] = d->rect[2] * mu_gfx_rate_x(stage_w);
                    d->slot[3] = d->rect[3] * mu_gfx_rate_y(stage_h);
                    d->page_type = 6;
                    d->frame_scale = sc;
                    d->alpha = 1;
                }
    }
    mu_gfx_layer_trade_items(g->l, items, count);
}
