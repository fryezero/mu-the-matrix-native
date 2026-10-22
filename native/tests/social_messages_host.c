/* Synthetic original-parser/offline-server lifecycle checks. No game data. */
#include "../core/mu_social_messages.h"
#include <assert.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
static void put16(uint8_t *p, unsigned v) {
    p[0] = (uint8_t)v;
    p[1] = (uint8_t)(v >> 8);
}
int main(void) {
    mu_social_messages *m = calloc(1, sizeof *m);
    assert(m);
    mu_social_messages_init(m, "Hero");
    uint32_t first = mu_social_messages_open(m, "Aeris");
    assert(first);
    mu_local_room *r = mu_social_messages_room(m, first);
    assert(r && r->number != first && r->count == 2 && m->requests == 2);
    uint32_t second = mu_social_messages_open(m, "Shopkeep");
    assert(second && second != first);
    int requests = m->requests;
    assert(mu_social_messages_open(m, "Aeris") == first && m->requests == requests);
    assert(mu_social_messages_send(m, first, "Hello \"friend\" \\ UTF-8 é😀"));
    assert(r->history_count == 1 && !strcmp(r->history[0].message.text, "Hello \"friend\" \\ UTF-8 é😀"));
    char too_long[102];
    memset(too_long, 'A', 101);
    too_long[101] = 0;
    requests = m->requests;
    assert(!mu_social_messages_send(m, first, too_long) && m->requests == requests);
    assert(mu_social_messages_minimize(m, first) && !r->shown);
    uint8_t msg[11] = {0xc1, 11, 4, 77, 6, 'Q', 'u', 'e', 'u', 'e', 'd'};
    assert(mu_social_messages_receive_room(m, first, 4, msg, sizeof msg));
    assert(r->history_count == 2 && r->history[1].message.serial == 77 && !r->shown);
    assert(mu_social_messages_open(m, "Aeris") == first && r->shown);
    /* A hidden queue must retain every arrival beyond the display history cap. */
    assert(mu_social_messages_minimize(m, first));
    for (int i = 0; i < 130; i++)
        assert(mu_social_messages_receive_room(m, first, 4, msg, sizeof msg));
    assert(r->history_count == 132 && r->history[0].sequence == 1);
    assert(mu_social_messages_open(m, "Aeris") == first);
    mu_social_messages_delivered(r, r->sequence);
    assert(r->history_count == MU_LOCAL_HISTORY);
    /* A server roster may assign the hero any serial. */
    r->users[0].serial = 19;
    assert(mu_social_messages_send(m, first, "Identity"));
    assert(r->history[r->history_count - 1].message.serial == 19 &&
           !strcmp(r->history[r->history_count - 1].sender, "Hero") && m->request.data[3] == 0);
    /* Reconnection keeps the loaded movie and sequence, then changes transport identity. */
    r->loaded = 1;
    uint32_t sequence = r->sequence, connection = r->connection;
    uint8_t reconnect[36] = {0};
    reconnect[18] = 201;
    reconnect[24] = 1;
    memcpy(reconnect + 3, "offline", 7);
    memcpy(reconnect + 25, "Aeris", 5);
    reconnect[35] = 1;
    assert(mu_social_messages_receive(m, 0x83, reconnect, sizeof reconnect));
    assert(r->ui == first && r->loaded && r->sequence == sequence && r->connection == connection + 1 &&
           r->number == 201);
    assert(mu_social_messages_receive_room(m, first, 4, msg, sizeof msg));
    assert(r->sequence == sequence + 1);
    /* Rebuild the roster after reconnect. */
    uint8_t small_roster[41] = {0};
    small_roster[6] = 3;
    small_roster[8] = 0;
    memcpy(small_roster + 9, "Hero", 4);
    small_roster[19] = 1;
    memcpy(small_roster + 20, "Aeris", 5);
    small_roster[30] = 2;
    memcpy(small_roster + 31, "Other", 5);
    assert(mu_social_messages_receive_room(m, first, 2, small_roster, sizeof small_roster));
    uint8_t leave[15] = {0};
    leave[3] = 1;
    leave[4] = 1;
    memcpy(leave + 5, "Aeris", 5);
    assert(mu_social_messages_receive_room(m, first, 1, leave, sizeof leave));
    assert(mu_social_messages_invite(m, first, "New"));
    assert(r->users[2].serial == 1 && r->users[1].serial == 2);
    small_roster[6] = 2;
    assert(mu_social_messages_receive_room(m, first, 2, small_roster, 30));
    uint8_t join[15] = {0};
    join[4] = 77;
    memcpy(join + 5, "Aeris", 5);
    assert(mu_social_messages_receive_room(m, first, 1, join, sizeof join));
    assert(r->count == 2 && r->users[1].serial == 77);
    assert(mu_social_messages_invite(m, first, "Other"));
    assert(r->count == 3);
    assert(!mu_social_messages_invite(m, first, "Other"));
    join[3] = 1;
    memcpy(join + 5, "Other", 5);
    assert(mu_social_messages_receive_room(m, first, 1, join, sizeof join) && r->count == 2);
    uint8_t roster[8 + 31 * 11] = {0};
    roster[6] = 31;
    for (int i = 0; i < 31; i++) {
        roster[8 + i * 11] = (uint8_t)i;
        snprintf((char *)roster + 9 + i * 11, 10, "User%d", i);
    }
    assert(mu_social_messages_receive_room(m, first, 2, roster, sizeof roster) && r->count == 31);
    assert(!mu_social_messages_invite(m, first, "Limit") && m->notice == 0x432);
    requests = m->requests;
    assert(mu_social_messages_close(m, first));
    assert(m->requests == requests + 1);
    assert(mu_social_messages_close(m, first) && m->requests == requests + 1);
    assert(!mu_social_messages_receive_room(m, first, 4, msg, sizeof msg));
    assert(mu_social_messages_seed(m, "Aeris", "First", "Body one"));
    assert(mu_social_messages_seed(m, "Shopkeep", "Second", "Body two"));
    assert(m->letter_count == 2 && !m->letters[0].header.read);
    assert(mu_social_messages_read(m, 1));
    uint32_t read = m->letters[0].read_ui;
    assert(read && read != second && m->letters[0].header.read);
    requests = m->requests;
    assert(mu_social_messages_read(m, 1) && m->requests == requests);
    assert(!mu_social_messages_neighbor(m, read, -1));
    uint32_t reply = mu_social_messages_reply(m, read);
    assert(reply && reply != read);
    mu_local_window *w = mu_social_messages_window(m, reply);
    assert(w && w->reply && !strcmp(w->recipient, "Aeris"));
    assert(mu_social_messages_write(m, reply, "Aeris", "RE: First", "Reply"));
    assert(!mu_social_messages_window(m, reply) && m->letter_count == 2); /* no manufactured inbox echo */
    assert(mu_social_messages_neighbor(m, read, 1));
    read = m->letters[1].read_ui;
    assert(read && !mu_social_messages_neighbor(m, read, 1));
    uint32_t self = mu_social_messages_compose(m, "Hero");
    assert(self);
    assert(mu_social_messages_write(m, self, "Hero", "Loopback", "Local server delivery"));
    assert(m->letter_count == 3); /* explicit offline server delivery goes through list receive */
    uint32_t ids[3] = {1, 1, 2};
    requests = m->requests;
    assert(mu_social_messages_delete_prompt(m, ids, 3) && m->delete_count == 2);
    assert(mu_social_messages_delete_confirm(m, 0) && m->letter_count == 3 && m->requests == requests);
    assert(mu_social_messages_delete_prompt(m, ids, 3));
    assert(mu_social_messages_delete_confirm(m, 1) && m->letter_count == 1 && m->requests == requests + 2);
    assert(!mu_social_messages_window(m, read));
    /* Body cache can precede a header. Its arrival alone does not invent a header/window. */
    uint8_t body[34] = {0};
    put16(body + 4, 77);
    put16(body + 6, 4);
    memcpy(body + 30, "late", 4);
    assert(mu_social_messages_receive(m, 0xec, body, sizeof body) && m->letter_count == 1);
    uint8_t header[79] = {0};
    put16(header + 4, 77);
    memcpy(header + 6, "Aeris", 5);
    memcpy(header + 46, "Late header", 11);
    assert(mu_social_messages_receive(m, 0xc4, header, sizeof header) && m->letter_count == 2);
    requests = m->requests;
    assert(mu_social_messages_read(m, 77) && m->requests == requests);
    assert(!strcmp(mu_social_messages_window(m, m->letters[1].read_ui)->body, "late"));
    int received = m->received;
    put16(body + 6, 1001);
    assert(!mu_social_messages_receive(m, 0xec, body, sizeof body) && m->received == received);
    assert(!mu_social_messages_receive(m, 0xc4, header, 78));
    header[78] = 3;
    assert(!mu_social_messages_receive(m, 0xc4, header, sizeof header));
    /* The offline server rejects delivery to a full inbox without closing the draft. */
    m->capacity = m->letter_count;
    uint32_t draft = mu_social_messages_compose(m, "Hero");
    assert(draft);
    assert(mu_social_messages_write(m, draft, "Hero", "Keep draft", "Not delivered"));
    assert(mu_social_messages_window(m, draft) && m->notice == 0x425);
    mu_social_messages_destroy(m);
    free(m);
    puts("social messages passed");
}
