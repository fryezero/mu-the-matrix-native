#ifndef MU_SOCIAL_MESSAGES_H
#define MU_SOCIAL_MESSAGES_H
#include "../../reconstructed/social/social_packets.h"
#define MU_LOCAL_ROOMS 8
#define MU_LOCAL_HISTORY 64
#define MU_LOCAL_MAIL 50
#define MU_LOCAL_WINDOWS 32
enum { MU_SOCIAL_NOTICE_WINDOW_CAPACITY = -1, MU_SOCIAL_NOTICE_CACHE_CAPACITY = -2 };
typedef struct mu_local_message {
    uint32_t sequence;
    mu_social_room_message message;
    char sender[11];
} mu_local_message;
typedef struct mu_local_room {
    uint32_t ui, ticket, connection;
    char address[16];
    uint16_t number;
    char peer[11], invited[11];
    int shown, locked, loaded, count, history_count;
    uint32_t sequence;
    mu_social_room_user users[255];
    mu_local_message *history;
    size_t history_capacity;
    uint32_t delivered;
} mu_local_room;
typedef struct mu_local_letter {
    mu_social_letter header;
    char server_body[1001]; /* OFFLINE server fixture, separate from received cache */
    int pending;
    uint32_t read_ui;
} mu_local_letter;
typedef struct mu_local_cache {
    uint32_t id;
    int used;
    char text[1001];
} mu_local_cache;
typedef struct mu_local_window {
    uint32_t ui, letter;
    int kind, shown, reply; /* 1 compose, 2 read */
    char recipient[11], title[33], body[1001];
} mu_local_window;
typedef struct mu_local_pending {
    uint32_t id, ui;
    int used;
} mu_local_pending;
typedef struct mu_social_messages {
    char hero[11], last[192];
    uint32_t next_ui, active_ui;
    int revision, mailbox_revision, requests, received, notice, letter_count, capacity;
    int delete_count;
    uint32_t delete_ids[MU_LOCAL_MAIL];
    mu_social_packet request;
    int parent_visible, fee_exempt, notice_fee;
    char room_notice[100], pending_peers[MU_LOCAL_ROOMS][11];
    mu_local_pending pending_reads[MU_LOCAL_MAIL];
    mu_local_room rooms[MU_LOCAL_ROOMS];
    mu_local_letter letters[MU_LOCAL_MAIL];
    mu_local_cache cache[MU_LOCAL_MAIL];
    mu_local_window windows[MU_LOCAL_WINDOWS];
} mu_social_messages;
void mu_social_messages_init(mu_social_messages *, const char *hero);
void mu_social_messages_destroy(mu_social_messages *);
void mu_social_messages_delivered(mu_local_room *, uint32_t sequence);
mu_local_room *mu_social_messages_room(mu_social_messages *, uint32_t ui);
mu_local_window *mu_social_messages_window(mu_social_messages *, uint32_t ui);
/* Real client normalized receive keys, not assumed wire opcodes. */
int mu_social_messages_receive(mu_social_messages *, int key, const uint8_t *, size_t);
int mu_social_messages_receive_room(mu_social_messages *, uint32_t ui, int opcode, const uint8_t *, size_t);
/* The following requests use the original builders. Answers and fixture mail
 * are explicitly OFFLINE server policy, never real item/server transactions. */
uint32_t mu_social_messages_open(mu_social_messages *, const char *peer);
int mu_social_messages_send(mu_social_messages *, uint32_t ui, const char *text);
int mu_social_messages_invite(mu_social_messages *, uint32_t ui, const char *name);
int mu_social_messages_minimize(mu_social_messages *, uint32_t ui);
int mu_social_messages_close(mu_social_messages *, uint32_t ui);
uint32_t mu_social_messages_compose(mu_social_messages *, const char *recipient);
int mu_social_messages_write(mu_social_messages *, uint32_t ui, const char *name, const char *title,
                             const char *text);
/* Original asynchronous control. Return 1 when a request was sent, 0 for
 * pending/select/cache replay, -1 for a native capacity/input failure. */
int mu_social_messages_read_request(mu_social_messages *, uint32_t letter);
int mu_social_messages_pending_track(mu_social_messages *, uint32_t letter);
void mu_social_messages_pending_close(mu_social_messages *, uint32_t letter);
void mu_social_messages_pending_bind(mu_social_messages *, uint32_t letter, uint32_t ui);
uint32_t mu_social_messages_pending_get(mu_social_messages *, uint32_t letter);
int mu_social_messages_read(mu_social_messages *, uint32_t letter);
uint32_t mu_social_messages_reply(mu_social_messages *, uint32_t read_ui);
int mu_social_messages_neighbor(mu_social_messages *, uint32_t read_ui, int direction);
int mu_social_messages_delete_prompt(mu_social_messages *, const uint32_t *letters, int count);
int mu_social_messages_delete_confirm(mu_social_messages *, int yes);
int mu_social_messages_seed(mu_social_messages *, const char *sender, const char *title, const char *text);
#endif
