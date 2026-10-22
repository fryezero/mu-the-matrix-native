#include "world_gfx_social.h"
#include "../../reconstructed/hud/item_slots.h"
#include "../../reconstructed/social/item_options.h"
#include "../gfx/mu_gfx_layer.h"
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
struct world_gfx_social {
    mu_gfx_layer *l;
    mu_social_session *s;
    int revision, party, friends, trade, friends_initialized;
    float x[2], y[2], w[2], h[2];
    int prompt;
    char map_path[160];
    int tokens[32];
    mu_gfx_slot_item escrow[32];
    int messenger;
    char room_name[11];
    int message_revision, mailbox_revision;
    uint32_t room_ui[MU_LOCAL_ROOMS], delivered[MU_LOCAL_ROOMS], roster_hash[MU_LOCAL_ROOMS];
    uint32_t mail_ui[MU_LOCAL_WINDOWS], connection[MU_LOCAL_ROOMS];
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
/* Record dimensions belong to the item metadata host, not the social server. */
static int trade_item(world_gfx_social *g, int side, int slot, mu_gfx_slot_item *out) {
    if (slot < 0 || slot >= 32 || !g->s->trade.items[side][slot].present)
        return 0;
    if (side == 0 && g->tokens[slot]) {
        *out = g->escrow[slot];
        return 1;
    }
    return mu_gfx_layer_social_item(g->l, g->s->trade.items[side][slot].bytes, out);
}
static int partner_grid(world_gfx_social *g) {
    uint8_t cells[32] = {0};
    for (int i = 0; i < 32; i++)
        if (g->s->trade.items[1][i].present) {
            mu_gfx_slot_item it;
            if (!trade_item(g, 1, i, &it) || i % 8 + it.width > 8 || i / 8 + it.height > 4)
                return 0;
            for (int y = 0; y < it.height; y++)
                for (int x = 0; x < it.width; x++) {
                    int c = i + y * 8 + x;
                    if (cells[c])
                        return 0;
                    cells[c] = 1;
                }
        }
    return 1;
}
static int covered_item(world_gfx_social *g, int side, int cell, mu_gfx_slot_item *out) {
    if (cell < 0 || cell >= 32)
        return -1;
    for (int i = 0; i < 32; i++)
        if (trade_item(g, side, i, out) && cell % 8 >= i % 8 && cell % 8 < i % 8 + out->width &&
            cell / 8 >= i / 8 && cell / 8 < i / 8 + out->height)
            return i;
    return -1;
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
    if (!partner_grid(g))
        return 0;
    for (int i = 0; i < 32; i++)
        if (g->s->trade.items[1][i].present) {
            if (!trade_item(g, 1, i, &incoming[n]))
                return 0;
            n++;
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
    if (!item.has_data) {
        mu_social_item_wire wire;
        memset(&wire, 0, sizeof wire);
        wire.code = item.code;
        wire.level_word = (uint8_t)(item.level << 3);
        wire.durability = 100; /* original demo inventory has no server instance */
        memset(wire.sockets, 0xff, sizeof wire.sockets);
        memset(wire.extra, 0xff, sizeof wire.extra);
        mu_social_item_pack(&wire, item.data);
        item.has_data = 1;
    }
    mu_gfx_slot_item meta;
    if (!mu_gfx_layer_social_item(g->l, item.data, &meta) || meta.trade_ban) {
        mu_gfx_layer_inventory_finish(g->l, token, 0);
        return 0;
    }
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
    memcpy(t->bytes, item.data, sizeof t->bytes);
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
static void messages_frame(world_gfx_social *g);
static void messenger(world_gfx_social *g, const char *name)
{
    if (mu_social_messages_open(&g->s->messages, name))
        messages_frame(g);
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
    mu_social_messages *messages = &g->s->messages;
    if (!strcmp(verb, "mail")) {
        mu_social_messages_compose(messages, arg);
        messages_frame(g);
        return 1;
    }
    if (!strcmp(verb, "read-mail")) {
        int ok = mu_social_messages_read(messages, (uint32_t)strtoul(arg, NULL, 10));
        messages_frame(g);
        return ok;
    }
    if (!strcmp(verb, "room-send")) {
        int ok = mu_social_messages_send(messages, messages->active_ui, arg);
        messages_frame(g);
        return ok;
    }
    if (!strcmp(verb, "room-invite")) {
        int ok = mu_social_messages_invite(messages, messages->active_ui, arg);
        messages_frame(g);
        return ok;
    }
    if (!strcmp(verb, "room-minimize") || !strcmp(verb, "room-close")) {
        uint32_t ui = arg[0] ? (uint32_t)strtoul(arg, NULL, 10) : messages->active_ui;
        int ok = !strcmp(verb, "room-close") ? mu_social_messages_close(messages, ui)
                                             : mu_social_messages_minimize(messages, ui);
        messages_frame(g);
        return ok;
    }
    if (!strcmp(verb, "delete-confirm")) {
        int ok = mu_social_messages_delete_confirm(messages, strcmp(arg, "no") != 0);
        messages_frame(g);
        return ok;
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
    mu_trade saved = g->s->trade;
    int saved_due = g->s->result_due;
    int ok = mu_social_action(g->s, verb, arg);
    if (ok && !strcmp(verb, "partner-item") && !partner_grid(g)) {
        g->s->trade = saved;
        g->s->result_due = saved_due;
        ok = 0;
    }
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
static const char *argument(const char *json, int index) {
    const char *p = strchr(json, '[');
    if (!p)
        return NULL;
    p++;
    for (int i = 0;; i++) {
        while (*p == ' ' || *p == '\n' || *p == '\t')
            p++;
        if (!*p || *p == ']')
            return NULL;
        if (i == index)
            return p;
        int depth = 0, string = 0;
        for (; *p; p++) {
            if (string) {
                if (*p == '\\' && p[1])
                    p++;
                else if (*p == '"')
                    string = 0;
            } else if (*p == '"')
                string = 1;
            else if (*p == '[' || *p == '{')
                depth++;
            else if (*p == ']' || *p == '}') {
                if (!depth)
                    return NULL;
                depth--;
            } else if (*p == ',' && !depth) {
                p++;
                break;
            }
        }
    }
}
static int string_arg(const char *json, int index, char *out, size_t cap) {
    const char *p = argument(json, index);
    return p && *p == '"' && first_string(p, out, cap);
}
static uint32_t id_arg(const char *json, int index) {
    const char *p = argument(json, index);
    if (!p)
        return 0;
    if (*p == '"')
        p++;
    char *end;
    unsigned long v = strtoul(p, &end, 10);
    return end != p && v <= UINT32_MAX ? (uint32_t)v : 0;
}
static void message_ui_init(world_gfx_social *g) {
    call(g, MU_GFX_MESSENGER, "InitText",
         "[[\"Write\",\"Read\",\"Reply\",\"Delete\",\"Messenger\",\"Invite\",\"Delete\",\"Previous\","
         "\"Next\",\"Close\",\"Send\",\"Recipient\",\"Title\",\"Offline demo\",\"Close invite\",\"Send\"]]");
    char q[64], b[96];
    quote(q, sizeof q, g->s->hero);
    snprintf(b, sizeof b, "[%s]", q);
    call(g, MU_GFX_MESSENGER, "SetHeroName", b);
}
static void messages_frame(world_gfx_social *g) {
    mu_social_messages *m = &g->s->messages;
    if (g->message_revision == m->revision)
        return;
    g->message_revision = m->revision;
    if (m->notice) {
        const char *fallback = "Messenger request could not be completed.";
        switch (m->notice) {
        case 0x3ee:
            fallback = "Enter a recipient.";
            break;
        case 0x3ef:
            fallback = "Enter a letter title.";
            break;
        case 0x3f0:
            fallback = "Enter a message.";
            break;
        case 0x416:
            fallback = "Letter sent (offline demo).";
            break;
        case 0x425:
            fallback = "The recipient's mailbox is full. Your draft is still open.";
            break;
        case 0x432:
            fallback = "This chat room cannot accept more participants.";
            break;
        default:
            break;
        }
        mu_gfx_layer_social_notice(g->l, m->notice, fallback);
        m->notice = 0;
    }
    message_ui_init(g);
    char b[32768], q[8192], name[128], title[256];
    int shown = 0;
    for (int i = 0; i < MU_LOCAL_ROOMS; i++) {
        mu_local_room *r = m->rooms + i;
        if (g->room_ui[i] && g->room_ui[i] != r->ui) {
            snprintf(b, sizeof b, "[%u]", g->room_ui[i]);
            g->room_ui[i] = 0;
            call(g, MU_GFX_MESSENGER, "CloseWindow", b);
        }
        if (!r->ui)
            continue;
        shown |= r->shown;
        if (g->room_ui[i] != r->ui && r->shown) {
            g->room_ui[i] = r->ui;
            g->delivered[i] = 0;
            g->roster_hash[i] = 0;
            r->loaded = 0;
            quote(name, sizeof name, r->peer);
            snprintf(b, sizeof b, "[%u,560,140,%s,%u,\"offline\",%u]", r->ui, name, r->number, r->ticket);
            call(g, MU_GFX_MESSENGER, "AddChatRoom1", b);
        }
        if (!g->room_ui[i])
            continue;
        char visible_path[256];
        snprintf(visible_path, sizeof visible_path, "%s.%u._visible",
                 mu_gfx_layer_path(g->l, MU_GFX_MESSENGER), r->ui);
        mu_gfx_layer_set_variable(g->l, MU_GFX_MESSENGER, visible_path, r->shown ? "true" : "false");
        if (g->connection[i] != r->connection) {
            quote(name, sizeof name, r->address);
            snprintf(b, sizeof b, "[%u,%u,%s,%u]", r->ui, r->number, name, r->ticket);
            call(g, MU_GFX_MESSENGER, "ChangeChatRoomInfo", b);
            g->connection[i] = r->connection;
            g->roster_hash[i] = 0;
        }
        if (!r->loaded || !r->shown)
            continue;
        uint32_t hash = 2166136261u;
        for (int j = 0; j < r->count; j++)
            for (size_t k = 0; k < sizeof r->users[j]; k++)
                hash = (hash ^ ((const uint8_t *)(r->users + j))[k]) * 16777619u;
        if (g->roster_hash[i] != hash) {
            /* Compatibility repair: the movie's RemoveTalker uses slice, which
             * retains removed rows. Rebuild its provider with mutating splice. */
            char path[256];
            snprintf(path, sizeof path, "%s.%u.slTalkers.dataProvider",
                     mu_gfx_layer_path(g->l, MU_GFX_MESSENGER), r->ui);
            mu_gfx_layer_invoke(g->l, MU_GFX_MESSENGER, path, "splice", "[0,255]");
            for (int j = 0; j < r->count; j++) {
                quote(name, sizeof name, r->users[j].name);
                snprintf(b, sizeof b, "[%u,%s,%u,%u]", r->ui, name, r->users[j].serial, r->users[j].server);
                call(g, MU_GFX_MESSENGER, "AddFriendAtChatRoom", b);
            }
            g->roster_hash[i] = hash;
        }
        snprintf(title, sizeof title, "%s (offline demo)", r->peer);
        quote(q, sizeof q, title);
        snprintf(b, sizeof b, "[%u,%s]", r->ui, q);
        call(g, MU_GFX_MESSENGER, "SetChatRoomTitle", b);
        for (int j = 0; j < r->history_count; j++)
            if (r->history[j].sequence > g->delivered[i]) {
                quote(q, sizeof q, r->history[j].message.text);
                snprintf(b, sizeof b, "[%u,%u,%s]", r->ui, r->history[j].message.serial, q);
                const mu_local_message *entry = r->history + j;
                int matches = 0;
                for (int u = 0; u < r->count; u++)
                    if (r->users[u].serial == entry->message.serial &&
                        !strcmp(r->users[u].name, entry->sender))
                        matches = 1;
                if (matches)
                    call(g, MU_GFX_MESSENGER, "AddChatText", b);
                else {
                    /* A replayed serial may now belong to someone else. The movie
                     * resolves AddText against today's roster, so project the
                     * arrival-time identity directly into its text provider. */
                    char label[160], path[256];
                    snprintf(label, sizeof label, "%s%s%s", entry->sender, entry->sender[0] ? ": " : "",
                             entry->message.text);
                    quote(q, sizeof q, label);
                    snprintf(b, sizeof b, "[{\"label\":%s}]", q);
                    snprintf(path, sizeof path, "%s.%u.slTexts.dataProvider",
                             mu_gfx_layer_path(g->l, MU_GFX_MESSENGER), r->ui);
                    mu_gfx_layer_invoke(g->l, MU_GFX_MESSENGER, path, "push", b);
                    snprintf(path, sizeof path, "%s.%u.slTexts", mu_gfx_layer_path(g->l, MU_GFX_MESSENGER),
                             r->ui);
                    mu_gfx_layer_invoke(g->l, MU_GFX_MESSENGER, path, "invalidateData", "[]");
                }
                g->delivered[i] = entry->sequence;
            }
        mu_social_messages_delivered(r, g->delivered[i]);
    }
    for (int i = 0; i < MU_LOCAL_WINDOWS; i++) {
        mu_local_window *w = m->windows + i;
        if (g->mail_ui[i] && g->mail_ui[i] != w->ui) {
            snprintf(b, sizeof b, "[%u]", g->mail_ui[i]);
            g->mail_ui[i] = 0;
            call(g, MU_GFX_MESSENGER, "CloseWindow", b);
        }
        if (!w->ui)
            continue;
        shown |= w->shown;
        if (g->mail_ui[i] != w->ui) {
            g->mail_ui[i] = w->ui;
            quote(name, sizeof name, w->recipient);
            quote(title, sizeof title, w->title);
            if (w->kind == 1) {
                snprintf(b, sizeof b, "[%u,560,140,\"Write letter (offline)\",%s,%s]", w->ui, name, title);
                call(g, MU_GFX_MESSENGER, w->reply ? "AddReplyLetter" : "AddWriteLetter", b);
                quote(q, sizeof q, w->body);
                snprintf(b, sizeof b, "[%u,%s]", w->ui, q);
                call(g, MU_GFX_MESSENGER, "SetLetterText", b);
            } else {
                quote(q, sizeof q, w->body);
                snprintf(b, sizeof b, "[%u,560,140,%u,%s,%s,%s,0,0]", w->ui, w->letter, title, name, q);
                call(g, MU_GFX_MESSENGER, "AddLetterText", b);
            }
        }
        char visible_path[256];
        snprintf(visible_path, sizeof visible_path, "%s.%u._visible",
                 mu_gfx_layer_path(g->l, MU_GFX_MESSENGER), w->ui);
        mu_gfx_layer_set_variable(g->l, MU_GFX_MESSENGER, visible_path, w->shown ? "true" : "false");
    }
    if (g->mailbox_revision != m->mailbox_revision) {
        g->mailbox_revision = m->mailbox_revision;
        call(g, MU_GFX_FRIENDS, "ClearMailBox", "[]");
        size_t n = (size_t)snprintf(b, sizeof b, "[[");
        for (int i = 0; i < m->letter_count; i++) {
            const mu_social_letter *h = &m->letters[i].header;
            quote(name, sizeof name, h->sender);
            quote(title, sizeof title, h->title);
            quote(q, sizeof q, h->date);
            n += (size_t)snprintf(
                b + n, sizeof b - n,
                "%s{\"CharacterID\":%s,\"Date\":%s,\"Text\":%s,\"IsRead\":%d,\"LetterID\":%u}", i ? "," : "",
                name, q, title, h->read, h->id);
        }
        snprintf(b + n, sizeof b - n, "]]");
        call(g, MU_GFX_FRIENDS, "AddLetterList", b);
    }
    for (int i = 0; i < m->letter_count; i++) {
        snprintf(b, sizeof b, "[%u,%d]", m->letters[i].header.id, m->letters[i].header.read);
        call(g, MU_GFX_FRIENDS, "SetMailReaded", b);
    }
    call(g, MU_GFX_FRIENDS, "ClearWindowList", "[]");
    for (int i = 0; i < MU_LOCAL_ROOMS; i++)
        if (m->rooms[i].ui) {
            quote(name, sizeof name, m->rooms[i].peer);
            snprintf(b, sizeof b, "[%u,%s]", m->rooms[i].ui, name);
            call(g, MU_GFX_FRIENDS, "AddWindowList", b);
        }
    for (int i = 0; i < MU_LOCAL_WINDOWS; i++)
        if (m->windows[i].ui) {
            quote(title, sizeof title, m->windows[i].title[0] ? m->windows[i].title : "Write letter");
            snprintf(b, sizeof b, "[%u,%s]", m->windows[i].ui, title);
            call(g, MU_GFX_FRIENDS, "AddWindowList", b);
        }
    mu_local_room *active_room = mu_social_messages_room(m, m->active_ui);
    mu_local_window *active_window = mu_social_messages_window(m, m->active_ui);
    if ((active_room && active_room->shown) || (active_window && active_window->shown)) {
        snprintf(b, sizeof b, "[%u]", m->active_ui);
        call(g, MU_GFX_MESSENGER, "SelectWindow", b);
    }
    g->messenger = shown;
    mu_gfx_layer_show(g->l, MU_GFX_MESSENGER, shown);
}
static int messages_callback(world_gfx_social *g, const char *name, const char *args) {
    mu_social_messages *m = &g->s->messages;
    uint32_t ui = id_arg(args, 0);
    mu_local_room *r = mu_social_messages_room(m, ui);
    char a[1001] = "", b[1001] = "", c[1001] = "";
    if (!strcmp(name, "LoadComplete") || !strcmp(name, "LoadCompleteChat") ||
        !strcmp(name, "RequestChatUser")) {
        if (r) {
            r->loaded = 1;
            g->roster_hash[r - m->rooms] = 0;
            m->revision++;
        }
    } else if (!strcmp(name, "AddChatText")) {
        if (!string_arg(args, 0, a, sizeof a))
            return 1;
        mu_social_messages_send(m, id_arg(args, 1), a);
    } else if (!strcmp(name, "InviteUserList")) {
        snprintf(b, sizeof b, "[%u]", ui);
        call(g, MU_GFX_MESSENGER, "ClearInviteFriend", b);
        for (int i = 0; r && i < g->s->friends.count; i++) {
            quote(a, sizeof a, g->s->friends.list[i].name);
            snprintf(b, sizeof b, "[%u,%s,%d,%d]", ui, a, i, g->s->friends.list[i].server);
            call(g, MU_GFX_MESSENGER, "AddInviteFriend", b);
        }
    } else if (!strcmp(name, "RequestInviteUser")) {
        if (string_arg(args, 1, a, sizeof a))
            mu_social_messages_invite(m, ui, a);
    } else if (!strcmp(name, "MinimizeWindow"))
        mu_social_messages_minimize(m, ui);
    else if (!strcmp(name, "CloseFriendWindow") || !strcmp(name, "DeleteWindow") ||
             !strcmp(name, "CloseWindow"))
        mu_social_messages_close(m, ui);
    else if (!strcmp(name, "WindowToggle")) {
        mu_local_window *w = mu_social_messages_window(m, ui);
        if (r)
            r->shown = 1;
        if (w)
            w->shown = 1;
        m->active_ui = ui;
        m->revision++;
    } else if (!strcmp(name, "AllHideWindow")) {
        for (int i = 0; i < MU_LOCAL_ROOMS; i++)
            m->rooms[i].shown = 0;
        for (int i = 0; i < MU_LOCAL_WINDOWS; i++)
            m->windows[i].shown = 0;
        m->revision++;
    } else if (!strcmp(name, "SendWriteLetter")) {
        string_arg(args, 0, a, sizeof a);
        mu_social_messages_compose(m, a);
    } else if (!strcmp(name, "ReadLetter"))
        mu_social_messages_read(m, ui);
    else if (!strcmp(name, "WriteLetter")) {
        if (string_arg(args, 1, a, sizeof a) && string_arg(args, 2, b, sizeof b) &&
            string_arg(args, 3, c, sizeof c))
            mu_social_messages_write(m, ui, a, b, c);
    } else if (!strcmp(name, "SendReplyLetterByID"))
        mu_social_messages_reply(m, ui);
    else if (!strcmp(name, "SendReplyLetterByInfo")) {
        if (string_arg(args, 0, a, sizeof a) && string_arg(args, 1, b, sizeof b)) {
            uint32_t id = mu_social_messages_compose(m, a);
            mu_local_window *w = mu_social_messages_window(m, id);
            if (w) {
                snprintf(w->title, sizeof w->title, "RE: %.28s", b);
                w->reply = 1;
            }
        }
    } else if (!strcmp(name, "NextLetter") || !strcmp(name, "PrevLetter"))
        mu_social_messages_neighbor(m, ui, name[0] == 'N' ? 1 : -1);
    else if (!strcmp(name, "CloseReadLetter")) {
        for (int i = 0; i < m->letter_count; i++)
            if (m->letters[i].header.id == ui)
                m->letters[i].pending = 0;
    } else if (!strcmp(name, "DeleteLetterByUIID") || !strcmp(name, "DeleteLetterByLetterID")) {
        mu_local_window *w = mu_social_messages_window(m, ui);
        uint32_t id = !strcmp(name, "DeleteLetterByUIID") ? (w ? w->letter : 0) : ui;
        if (mu_social_messages_delete_prompt(m, &id, 1))
            notice(g, "Delete selected letter? Y confirm, N cancel (offline demo)");
    } else if (!strcmp(name, "CheckedMailList")) {
        const char *list = argument(args, 1);
        uint32_t ids[MU_LOCAL_MAIL];
        int count = 0;
        for (int i = 0; list && i < MU_LOCAL_MAIL && argument(list, i); i++)
            ids[count++] = id_arg(list, i);
        if (mu_social_messages_delete_prompt(m, ids, count))
            notice(g, "Delete selected letters? Y confirm, N cancel (offline demo)");
    } else if (!strcmp(name, "UpdateLetterText") || !strcmp(name, "UpdateLetterID") ||
               !strcmp(name, "UpdateLetterTitle")) {
        mu_local_window *w = mu_social_messages_window(m, ui);
        if (w && w->kind == 1 && string_arg(args, 1, a, sizeof a)) {
            int limit = !strcmp(name, "UpdateLetterText") ? 255 : !strcmp(name, "UpdateLetterID") ? 10 : 32;
            if (strlen(a) > (size_t)limit) {
                a[limit] = 0;
                quote(b, sizeof b, a);
                snprintf(c, sizeof c, "[%u,%s]", ui, b);
                call(g, MU_GFX_MESSENGER,
                     limit == 255  ? "SetLetterText"
                     : limit == 10 ? "ChangeIDBySize"
                                   : "ChangeTitleBySize",
                     c);
            }
            if (limit == 255)
                snprintf(w->body, sizeof w->body, "%s", a);
            else if (limit == 10)
                snprintf(w->recipient, sizeof w->recipient, "%.10s", a);
            else
                snprintf(w->title, sizeof w->title, "%.32s", a);
        }
    } else
        return 0;
    messages_frame(g);
    return 1;
}
static void window(void *user, int id, const char *name, const char *args)
{
    world_gfx_social *g = user;
    char v[64] = "";
    if ((id == MU_GFX_MESSENGER || (id == MU_GFX_FRIENDS && strcmp(name, "CloseWindow"))) &&
        messages_callback(g, name, args))
        return;
    field(args, "name", v, sizeof v);
    if (!strcmp(name, "UIInit") || !strcmp(name, "onLoad")) {
        g->revision = -1;
        if (id == MU_GFX_FRIENDS) {
            g->friends_initialized = 0;
            g->mailbox_revision = -1;
            g->s->messages.revision++;
        }
        return;
    }
    if (id == MU_GFX_PARTY) {
        if (!strcmp(name, "onLeave"))
            world_gfx_social_action(g, "confirm-leave", v);
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
        } else if (!strcmp(name, "requestItemSlotOver")) {
            int cell = atoi(args + 1), side = cell >= 32 ? 0 : 1;
            mu_gfx_slot_item it;
            int slot = covered_item(g, side, cell % 32, &it);
            if (cell >= 0 && cell < 64 && slot >= 0) {
                float ox, oy;
                mu_gfx_layer_window_position(g->l, MU_GFX_TRADE, &ox, &oy);
                float sc = mu_gfx_layer_window_scale(g->l, MU_GFX_TRADE);
                int k = 1 - side;
                float rect[4] = {ox + (g->x[k] + (float)(slot % 8) * (g->w[k] + 1)) * sc,
                                 oy + (g->y[k] + (float)(slot / 8) * (g->h[k] + 1)) * sc,
                                 (float)it.width * g->w[k] * sc, (float)it.height * g->h[k] * sc};
                mu_gfx_layer_social_tooltip(g->l, &it, rect);
            }
        } else if (!strcmp(name, "requestItemSlotOut")) {
            mu_gfx_layer_invoke(g->l, MU_GFX_TOOLTIP, NULL, "SetInfoPopupClose", "[]");
        } else if (!strcmp(name, "onClickbtnTrade")) {
            world_gfx_social_action(g, "ok", "");
            if (!g->s->trade.ok[1])
                world_gfx_social_action(g, "partner-ok", "");
        } else if (!strcmp(name, "onClickbtnInputZen"))
            notice(g, "Enter /zen AMOUNT in chat to set your trade offer.");
    } else if (id == MU_GFX_FRIENDS) {
        if (!strcmp(name, "PartyInvitation")) {
            const char *flag = argument(args, 0);
            if (flag && !strncmp(flag, "true", 4) && string_arg(args, 1, v, sizeof v))
                world_gfx_social_action(g, "party", v);
        } else if (!strcmp(name, "CloseWindow")) {
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
    }
}
static int key(void *user, int vk)
{
    world_gfx_social *g = user;
    if (vk == 'F')
        return world_gfx_social_action(g, "friends", "");
    if (vk == 'P')
        return world_gfx_social_action(g, "party-window", "");
    if (g->s->messages.delete_count && (vk == 'Y' || vk == 'N')) {
        int ok = mu_social_messages_delete_confirm(&g->s->messages, vk == 'Y');
        messages_frame(g);
        return ok;
    }
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
    g->message_revision = g->mailbox_revision = -1;
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
    if (s->party_notice) {
        mu_gfx_layer_social_notice(g->l, s->party_notice, "Party request result (offline demo).");
        s->party_notice = 0;
    }
    messages_frame(g);
    if (g->prompt != s->pending) {
        g->prompt = s->pending;
        if (s->pending) {
            char t[192];
            if (s->pending == 3)
                snprintf(t, sizeof t, "Remove %s from party? Y confirm, N cancel (offline demo)",
                         s->pending_name);
            else
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
            if (!g->friends_initialized) {
                g->friends_initialized = 1;
                call(g, MU_GFX_FRIENDS, "InitText",
                     "[[\"Friends\",\"Add friend\",\"Delete friend\",\"Whisper\",\"Write "
                     "letter\",\"Friends\",\"Windows\",\"Mail\",\"Name\",\"Server\",\"Block\",\"Hide\","
                     "\"Write "
                     "letter\",\"Read\",\"Reply\",\"Delete "
                     "letter\",\"Name\",\"Date\",\"Title\",\"Windows\",\"Recipient\",\"Title\",\"Party "
                     "invitation\"]]");
            }
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
                    mu_gfx_slot_item info;
                    int occupied = covered_item(g, 1 - side, i, &info) >= 0;
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
                    mu_gfx_slot_item it;
                    if (!trade_item(g, side, i, &it)) {
                        count--;
                        continue;
                    }
                    mu_social_item_wire wire;
                    mu_social_item_unpack(s->trade.items[side][i].bytes, &wire);
                    d->code = it.code;
                    d->level = it.level;
                    d->has_options = 1;
                    d->level_word = wire.level_word;
                    d->excellent = wire.excellent & 0x3f;
                    d->set_bits = wire.ancient;
                    d->rect[0] = ox + (g->x[k] + (float)(i % 8) * (g->w[k] + 1)) * sc;
                    d->rect[1] = oy + (g->y[k] + (float)(i / 8) * (g->h[k] + 1)) * sc;
                    d->rect[2] = g->w[k] * sc * (float)it.width;
                    d->rect[3] = g->h[k] * sc * (float)it.height;
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
