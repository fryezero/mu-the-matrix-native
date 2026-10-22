#include "mu_social_messages.h"
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
static const uint8_t OFFLINE_KEY[3] = {0, 0, 0};
static void name10(char out[11], const char *s) {
    snprintf(out, 11, "%.10s", s ? s : "");
}
static void put16(uint8_t *p, uint32_t v) {
    p[0] = (uint8_t)v;
    p[1] = (uint8_t)(v >> 8);
}
static void put32(uint8_t *p, uint32_t v) {
    for (int i = 0; i < 4; i++)
        p[i] = (uint8_t)(v >> (8 * i));
}
static uint32_t get32(const uint8_t *p) {
    return (uint32_t)p[0] | (uint32_t)p[1] << 8 | (uint32_t)p[2] << 16 | (uint32_t)p[3] << 24;
}
static uint32_t get16(const uint8_t *p) {
    return (uint32_t)p[0] | (uint32_t)p[1] << 8;
}
static void emit(mu_social_messages *m) {
    m->requests++;
    m->revision++;
}
static mu_local_letter *letter(mu_social_messages *m, uint32_t id) {
    for (int i = 0; i < m->letter_count; i++)
        if (m->letters[i].header.id == id)
            return m->letters + i;
    return NULL;
}
static mu_local_cache *cache(mu_social_messages *m, uint32_t id, int create) {
    mu_local_cache *free_slot = NULL;
    for (int i = 0; i < MU_LOCAL_MAIL; i++) {
        if (m->cache[i].used && m->cache[i].id == id)
            return m->cache + i;
        if (!m->cache[i].used && !free_slot)
            free_slot = m->cache + i;
    }
    if (!create || !free_slot)
        return NULL;
    memset(free_slot, 0, sizeof *free_slot);
    free_slot->used = 1;
    free_slot->id = id;
    return free_slot;
}
mu_local_room *mu_social_messages_room(mu_social_messages *m, uint32_t ui) {
    for (int i = 0; i < MU_LOCAL_ROOMS; i++)
        if (m->rooms[i].ui == ui && ui)
            return m->rooms + i;
    return NULL;
}
mu_local_window *mu_social_messages_window(mu_social_messages *m, uint32_t ui) {
    for (int i = 0; i < MU_LOCAL_WINDOWS; i++)
        if (m->windows[i].ui == ui && ui)
            return m->windows + i;
    return NULL;
}
static mu_local_window *window_new(mu_social_messages *m, int kind) {
    for (int i = 0; i < MU_LOCAL_WINDOWS; i++)
        if (!m->windows[i].ui) {
            mu_local_window *w = m->windows + i;
            memset(w, 0, sizeof *w);
            w->ui = m->next_ui++;
            w->kind = kind;
            w->shown = 1;
            m->active_ui = w->ui;
            m->revision++;
            return w;
        }
    return NULL;
}
static void add_user(mu_local_room *r, const mu_social_room_user *u) {
    for (int i = 0; i < r->count; i++)
        if (!strcmp(r->users[i].name, u->name)) {
            r->users[i] = *u;
            return;
        }
    if (r->count < 255)
        r->users[r->count++] = *u;
}
void mu_social_messages_delivered(mu_local_room *r, uint32_t sequence) {
    r->delivered = sequence;
    /* Keep recent delivered history for a recreated movie. Undelivered messages
     * remain queued regardless of how long the room is minimized. */
    int remove = 0;
    while (r->history_count - remove > MU_LOCAL_HISTORY && r->history[remove].sequence <= sequence)
        remove++;
    if (remove) {
        r->history_count -= remove;
        memmove(r->history, r->history + remove, (size_t)r->history_count * sizeof *r->history);
    }
}
static int append_message(mu_local_room *r, const mu_social_room_message *msg) {
    if ((size_t)r->history_count == r->history_capacity) {
        size_t cap = r->history_capacity ? r->history_capacity * 2 : MU_LOCAL_HISTORY;
        if (cap > (size_t)INT32_MAX || cap > SIZE_MAX / sizeof *r->history)
            return 0;
        mu_local_message *h = realloc(r->history, cap * sizeof *h);
        if (!h)
            return 0;
        r->history = h;
        r->history_capacity = cap;
    }
    mu_local_message *v = r->history + r->history_count++;
    v->sequence = ++r->sequence;
    v->message = *msg;
    name10(v->sender, "");
    for (int i = 0; i < r->count; i++)
        if (r->users[i].serial == msg->serial) {
            name10(v->sender, r->users[i].name);
            break;
        }
    return 1;
}
void mu_social_messages_destroy(mu_social_messages *m) {
    if (!m)
        return;
    for (int i = 0; i < MU_LOCAL_ROOMS; i++)
        free(m->rooms[i].history);
    memset(m, 0, sizeof *m);
}
void mu_social_messages_init(mu_social_messages *m, const char *hero) {
    memset(m, 0, sizeof *m);
    name10(m->hero, hero);
    m->next_ui = 1;
    m->capacity = MU_LOCAL_MAIL;
}
int mu_social_messages_receive_room(mu_social_messages *m, uint32_t ui, int op, const uint8_t *b, size_t n) {
    mu_local_room *r = mu_social_messages_room(m, ui);
    if (!r || !b)
        return 0;
    if (op == 1) {
        mu_social_room_event e;
        if (!mu_social_room_event_read(b, n, &e))
            return 0;
        if (e.event == 0)
            add_user(r, &e.user);
        else
            for (int i = 0; i < r->count; i++)
                if (!strcmp(r->users[i].name, e.user.name)) {
                    memmove(r->users + i, r->users + i + 1, (size_t)(--r->count - i) * sizeof r->users[0]);
                    break;
                }
    } else if (op == 2) {
        mu_social_room_user users[255];
        int count = mu_social_room_roster(b, n, users, 255);
        if (count < 0)
            return 0;
        r->count = 0;
        for (int i = 0; i < count; i++)
            add_user(r, users + i);
    } else if (op == 4) {
        mu_social_room_message msg;
        if (!mu_social_room_text(b, n, OFFLINE_KEY, &msg))
            return 0;
        if (!append_message(r, &msg))
            return 0;
    } else if (op == 0) {
        if (n < 4)
            return 0;
        if (b[3] == 0)
            m->notice = 0x422;
    } else if (op == 0x0d) {
        if (n < 5)
            return 0;
        size_t count = n - 5;
        if (count > 99)
            count = 99;
        snprintf(m->last, sizeof m->last, "%.*s", (int)count, (const char *)b + 5);
    } else
        return 0;
    m->received++;
    m->revision++;
    return 1;
}
int mu_social_messages_receive(mu_social_messages *m, int key, const uint8_t *b, size_t n) {
    if (!b)
        return 0;
    if (key == 0x83) {
        mu_social_room_answer a;
        if (!mu_social_room_open_answer(b, n, &a))
            return 0;
        if (a.result != 1) {
            if (a.result == 0)
                m->notice = 0x42d;
            else if (a.result == 2)
                m->notice = 0x42e;
        } else if (a.mode <= 2) {
            mu_local_room *r = NULL;
            if (a.mode == 1)
                for (int i = 0; i < MU_LOCAL_ROOMS; i++)
                    if (m->rooms[i].ui && !strcmp(m->rooms[i].peer, a.peer))
                        r = m->rooms + i;
            if (r) {
                mu_social_room_control(&m->request, 1);
                emit(m);
            } else
                for (int i = 0; i < MU_LOCAL_ROOMS; i++)
                    if (!m->rooms[i].ui) {
                        r = m->rooms + i;
                        break;
                    }
            if (!r)
                return 0;
            if (!r->ui)
                r->ui = m->next_ui++;
            /* A mode-1 answer reconnects the transport behind the existing
             * movie. Keep its loaded state, transcript and monotonic sequence. */
            r->count = 0;
            r->locked = 0;
            r->connection++;
            r->number = a.room;
            r->ticket = a.ticket;
            snprintf(r->address, sizeof r->address, "%s", a.address);
            name10(r->peer, a.peer);
            r->shown = 1;
            m->active_ui = r->ui;
            mu_social_room_connect(&m->request, a.room, a.ticket);
            emit(m);
        }
    } else if (key == 0xc4) {
        mu_social_letter h;
        if (!mu_social_mail_header(b, n, &h))
            return 0;
        if (!letter(m, h.id)) {
            if (m->letter_count >= m->capacity || m->letter_count >= MU_LOCAL_MAIL)
                return 0;
            m->letters[m->letter_count++].header = h;
            m->mailbox_revision++;
        }
    } else if (key == 0xec) {
        mu_social_letter_body body;
        if (!mu_social_mail_body(b, n, &body))
            return 0;
        mu_local_cache *c = cache(m, body.id, 1);
        if (!c)
            return 0;
        snprintf(c->text, sizeof c->text, "%s", body.text);
        mu_local_letter *h = letter(m, body.id);
        if (h) {
            h->header.read = 1;
            h->pending = 0;
            mu_local_window *w = mu_social_messages_window(m, h->read_ui);
            if (!w) {
                w = window_new(m, 2);
                if (!w)
                    return 0;
                h->read_ui = w->ui;
            }
            w->letter = body.id;
            w->shown = 1;
            name10(w->recipient, h->header.sender);
            snprintf(w->title, sizeof w->title, "%s", h->header.title);
            snprintf(w->body, sizeof w->body, "%s", body.text);
            m->active_ui = w->ui;
        }
    } else if (key == 0x41) {
        if (n < 8)
            return 0;
        m->notice = mu_social_mail_send_notice(b[3]);
        if (b[3] == 1) {
            mu_local_window *w = mu_social_messages_window(m, get32(b + 4));
            if (w)
                memset(w, 0, sizeof *w);
        }
    } else if (key == 0xa2) {
        if (n < 6)
            return 0;
        uint32_t id = get16(b + 4);
        if (b[3] == 0)
            m->notice = 0x41f;
        else if (b[3] == 1) {
            for (int i = 0; i < m->letter_count; i++)
                if (m->letters[i].header.id == id) {
                    mu_local_window *w = mu_social_messages_window(m, m->letters[i].read_ui);
                    if (w)
                        memset(w, 0, sizeof *w);
                    memmove(m->letters + i, m->letters + i + 1,
                            (size_t)(--m->letter_count - i) * sizeof m->letters[0]);
                    memset(m->letters + m->letter_count, 0, sizeof m->letters[0]);
                    m->mailbox_revision++;
                    break;
                }
            mu_local_cache *c = cache(m, id, 0);
            if (c)
                memset(c, 0, sizeof *c);
        }
    } else if (key == 0xf7) {
        if (n < 8)
            return 0;
        mu_local_room *r = mu_social_messages_room(m, get32(b + 4));
        if (r)
            m->notice = b[3] == 0 ? 0x420 : b[3] == 1 ? 0x421 : b[3] == 3 ? 0x432 : 0;
    } else
        return 0;
    m->received++;
    m->revision++;
    return 1;
}
/* OFFLINE server: requests below are serialized first, then synthetic answers
 * enter the same receive handlers. No request directly inserts a UI row. */
uint32_t mu_social_messages_open(mu_social_messages *m, const char *peer) {
    if (!peer || !*peer || strlen(peer) > 10 || !strcmp(peer, m->hero))
        return 0;
    for (int i = 0; i < MU_LOCAL_ROOMS; i++)
        if (m->rooms[i].ui && !strcmp(m->rooms[i].peer, peer)) {
            m->rooms[i].shown = 1;
            m->active_ui = m->rooms[i].ui;
            m->revision++;
            return m->active_ui;
        }
    int free_room = -1;
    for (int i = 0; i < MU_LOCAL_ROOMS; i++)
        if (!m->rooms[i].ui) {
            free_room = i;
            break;
        }
    if (free_room < 0 || !mu_social_room_request(&m->request, peer))
        return 0;
    emit(m);
    uint8_t answer[36] = {0};
    memcpy(answer + 3, "offline", 7);
    put16(answer + 18, (uint32_t)(100 + free_room));
    put32(answer + 20, (uint32_t)(1000 + free_room));
    memcpy(answer + 25, m->request.data + 3, 10);
    answer[35] = 1;
    if (!mu_social_messages_receive(m, 0x83, answer, sizeof answer))
        return 0;
    mu_local_room *r = mu_social_messages_room(m, m->active_ui);
    if (!r)
        return 0;
    uint8_t roster[30] = {0};
    roster[6] = 2;
    roster[8] = 0;
    memcpy(roster + 9, m->hero, 10);
    roster[19] = 1;
    memcpy(roster + 20, r->peer, 10);
    mu_social_messages_receive_room(m, r->ui, 2, roster, sizeof roster);
    return r->ui;
}
int mu_social_messages_send(mu_social_messages *m, uint32_t ui, const char *text) {
    mu_local_room *r = mu_social_messages_room(m, ui);
    size_t n = text ? strlen(text) : 0;
    if (!r || r->locked || !n || n > 100 ||
        !mu_social_room_send(&m->request, (const uint8_t *)text, n, OFFLINE_KEY))
        return 0;
    /* The server stamps the sender serial. The reserved request byte is not
     * a participant identity, and the local hero need not have serial zero. */
    int hero = -1;
    for (int i = 0; i < r->count; i++)
        if (!strcmp(r->users[i].name, m->hero))
            hero = i;
    if (hero < 0)
        return 0;
    emit(m);
    uint8_t answer[105];
    memcpy(answer, m->request.data, (size_t)m->request.size);
    answer[3] = r->users[hero].serial;
    return mu_social_messages_receive_room(m, ui, 4, answer, (size_t)m->request.size);
}
int mu_social_messages_invite(mu_social_messages *m, uint32_t ui, const char *name) {
    mu_local_room *r = mu_social_messages_room(m, ui);
    if (!r || r->locked || r->count < 2 || !name || !*name)
        return 0;
    if (r->count >= 30) {
        m->notice = 0x432;
        m->revision++;
        return 0;
    }
    for (int i = 0; i < r->count; i++)
        if (!strcmp(r->users[i].name, name))
            return 0;
    if (!mu_social_room_invite(&m->request, name, r->number, ui))
        return 0;
    name10(r->invited, name);
    emit(m);
    uint8_t event[15] = {0};
    int serial = 0;
    for (; serial < 256; serial++) {
        int used = 0;
        for (int i = 0; i < r->count; i++)
            used |= r->users[i].serial == serial;
        if (!used)
            break;
    }
    event[4] = (uint8_t)serial;
    memcpy(event + 5, m->request.data + 3, 10);
    return mu_social_messages_receive_room(m, ui, 1, event, sizeof event);
}
int mu_social_messages_minimize(mu_social_messages *m, uint32_t ui) {
    mu_local_room *r = mu_social_messages_room(m, ui);
    mu_local_window *w = mu_social_messages_window(m, ui);
    if (!r && !w)
        return 0;
    if (r)
        r->shown = 0;
    if (w)
        w->shown = 0;
    m->revision++;
    return 1;
}
int mu_social_messages_close(mu_social_messages *m, uint32_t ui) {
    mu_local_room *r = mu_social_messages_room(m, ui);
    if (r) {
        mu_social_room_control(&m->request, 1);
        emit(m);
        free(r->history);
        memset(r, 0, sizeof *r);
    }
    mu_local_window *w = mu_social_messages_window(m, ui);
    if (w) {
        if (w->kind == 2) {
            mu_local_letter *h = letter(m, w->letter);
            if (h) {
                h->read_ui = 0;
                h->pending = 0;
            }
        }
        memset(w, 0, sizeof *w);
    }
    if (m->active_ui == ui)
        m->active_ui = 0;
    m->revision++;
    return 1;
}
uint32_t mu_social_messages_compose(mu_social_messages *m, const char *recipient) {
    mu_local_window *w = window_new(m, 1);
    if (!w)
        return 0;
    name10(w->recipient, recipient);
    return w->ui;
}
int mu_social_messages_seed(mu_social_messages *m, const char *sender, const char *title, const char *text) {
    if (m->letter_count >= m->capacity)
        return 0;
    uint32_t id = 1;
    while (letter(m, id))
        id++;
    uint8_t b[79] = {0xc2, 0, 79, 0};
    put16(b + 4, id);
    snprintf((char *)b + 6, 11, "%.10s", sender);
    memcpy(b + 16, "2026-10-22", 10);
    memcpy(b + 27, "00:00:00", 8);
    snprintf((char *)b + 46, 33, "%.32s", title);
    b[78] = 2;
    if (!mu_social_messages_receive(m, 0xc4, b, sizeof b))
        return 0;
    mu_local_letter *h = letter(m, id);
    snprintf(h->server_body, sizeof h->server_body, "%s", text);
    return 1;
}
int mu_social_messages_write(mu_social_messages *m, uint32_t ui, const char *name, const char *title,
                             const char *text) {
    mu_local_window *w = mu_social_messages_window(m, ui);
    if (!w || w->kind != 1)
        return 0;
    if (!name || !*name) {
        m->notice = 0x3ee;
        m->revision++;
        return 0;
    }
    if (!title || !*title) {
        m->notice = 0x3ef;
        m->revision++;
        return 0;
    }
    if (!text || !*text) {
        m->notice = 0x3f0;
        m->revision++;
        return 0;
    }
    if (!mu_social_mail_write(&m->request, ui, name, title, (const uint8_t *)text, strlen(text)))
        return 0;
    name10(w->recipient, name);
    snprintf(w->title, sizeof w->title, "%.32s", title);
    snprintf(w->body, sizeof w->body, "%s", text);
    emit(m);
    /* An accepted outgoing letter does not create a client mailbox row. The
     * offline server delivers only mail addressed to this local hero. */
    int result = 1;
    if (!strcmp(name, m->hero) && !mu_social_messages_seed(m, m->hero, title, text))
        result = 2;
    uint8_t answer[8] = {0xc1, 8, 0, (uint8_t)result};
    put32(answer + 4, ui);
    return mu_social_messages_receive(m, 0x41, answer, sizeof answer);
}
int mu_social_messages_read(mu_social_messages *m, uint32_t id) {
    mu_local_letter *h = letter(m, id);
    if (!h)
        return 0;
    if (h->read_ui) {
        mu_local_window *w = mu_social_messages_window(m, h->read_ui);
        if (w) {
            w->shown = 1;
            m->active_ui = w->ui;
            m->revision++;
            return 1;
        }
    }
    if (h->pending)
        return 1;
    mu_local_cache *c = cache(m, id, 0);
    if (!c) {
        mu_social_mail_read_request(&m->request, (uint16_t)id);
        emit(m);
        h->pending = 1;
    }
    const char *text = c ? c->text : h->server_body;
    size_t n = strlen(text);
    if (n > 1000)
        return 0;
    uint8_t b[1030] = {0};
    put16(b + 4, id);
    put16(b + 6, (uint32_t)n);
    memcpy(b + 30, text, n);
    return mu_social_messages_receive(m, 0xec, b, 30 + n);
}
uint32_t mu_social_messages_reply(mu_social_messages *m, uint32_t ui) {
    mu_local_window *w = mu_social_messages_window(m, ui);
    if (!w || w->kind != 2)
        return 0;
    mu_local_letter *h = letter(m, w->letter);
    if (!h)
        return 0;
    mu_local_window *out = window_new(m, 1);
    if (!out)
        return 0;
    name10(out->recipient, h->header.sender);
    snprintf(out->title, sizeof out->title, "RE: %.28s", h->header.title);
    out->reply = 1;
    return out->ui;
}
int mu_social_messages_neighbor(mu_social_messages *m, uint32_t ui, int direction) {
    mu_local_window *w = mu_social_messages_window(m, ui);
    if (!w || w->kind != 2 || !direction)
        return 0;
    for (int i = 0; i < m->letter_count; i++)
        if (m->letters[i].header.id == w->letter) {
            int next = i + (direction > 0 ? 1 : -1);
            if (next < 0 || next >= m->letter_count)
                return 0;
            uint32_t id = m->letters[next].header.id;
            mu_social_messages_close(m, ui);
            return mu_social_messages_read(m, id);
        }
    return 0;
}
int mu_social_messages_delete_prompt(mu_social_messages *m, const uint32_t *ids, int count) {
    if (!ids || count < 1 || count > MU_LOCAL_MAIL)
        return 0;
    m->delete_count = 0;
    for (int i = 0; i < count; i++)
        if (letter(m, ids[i])) {
            int duplicate = 0;
            for (int j = 0; j < m->delete_count; j++)
                duplicate |= m->delete_ids[j] == ids[i];
            if (!duplicate)
                m->delete_ids[m->delete_count++] = ids[i];
        }
    m->revision++;
    return m->delete_count > 0;
}
int mu_social_messages_delete_confirm(mu_social_messages *m, int yes) {
    int count = m->delete_count;
    m->delete_count = 0;
    for (int i = 0; yes && i < count; i++) {
        mu_social_mail_delete_request(&m->request, (uint16_t)m->delete_ids[i]);
        emit(m);
        uint8_t answer[6] = {0xc1, 6, 0, 1};
        put16(answer + 4, m->delete_ids[i]);
        mu_social_messages_receive(m, 0xa2, answer, sizeof answer);
    }
    m->revision++;
    return count > 0;
}
