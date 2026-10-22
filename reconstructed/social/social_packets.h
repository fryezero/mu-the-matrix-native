#ifndef MU_SOCIAL_PACKETS_H
#define MU_SOCIAL_PACKETS_H
#include <stddef.h>
#include <stdint.h>
/* Logical packet construction at the original append/send boundary. Length
 * finalization is native framing; transport transforms and sockets are absent. */
#define MU_SOCIAL_PACKET_MAX 1100
typedef struct mu_social_packet {
    int32_t size, channel, send0, send1;
    uint8_t data[MU_SOCIAL_PACKET_MAX];
} mu_social_packet;
int mu_social_party_invite(mu_social_packet *, uint16_t key, int actor_exists, int enabled);
void mu_social_party_answer(mu_social_packet *, uint16_t key, uint8_t reply);
int mu_social_party_popup(int popup, int result, int *reply);
int mu_social_party_permission(int target, int blocked, int world_blocked, int has_party, int leader,
                               int target_pk, int hero_pk, int *notice);
int mu_social_party_autoaccept(int active, int friends, int guild, int is_friend, int exists, int hero_guild,
                               int other_guild);
/* 0 silent, 1 confirmation, 2 map rejection. Notice IDs are GlobalText keys. */
int mu_social_party_leave_prompt(int world, int found, int self, int *notice);
int mu_social_party_remove_confirm(int popup, int result);
int mu_social_party_remove(mu_social_packet *, uint8_t slot, const char *name, int found, int empty);
int mu_social_party_notice(uint8_t result);

int mu_social_room_request(mu_social_packet *, const char *name);
void mu_social_room_connect(mu_social_packet *, uint16_t room, uint32_t ticket);
void mu_social_room_control(mu_social_packet *, uint8_t opcode);
int mu_social_room_invite(mu_social_packet *, const char *name, uint16_t room, uint32_t ui);
/* The three-byte text transform is a separate messenger helper, not the
 * excluded network C3/C4 encryption. Offline sessions supply an authored key. */
void mu_social_room_transform(uint8_t *bytes, size_t size, const uint8_t key[3]);
int mu_social_room_send(mu_social_packet *, const uint8_t *text, size_t size, const uint8_t key[3]);
typedef struct mu_social_room_user {
    char name[11];
    uint8_t serial, server;
} mu_social_room_user;
typedef struct mu_social_room_event {
    int32_t event;
    mu_social_room_user user;
} mu_social_room_event;
typedef struct mu_social_room_message {
    uint8_t serial;
    char text[101];
} mu_social_room_message;
typedef struct mu_social_room_answer {
    char address[16], peer[11];
    uint16_t room;
    uint32_t ticket;
    uint8_t mode, result;
} mu_social_room_answer;
int mu_social_room_event_read(const uint8_t *, size_t, mu_social_room_event *);
int mu_social_room_roster(const uint8_t *, size_t, mu_social_room_user *, size_t capacity);
int mu_social_room_text(const uint8_t *, size_t, const uint8_t key[3], mu_social_room_message *);
int mu_social_room_open_answer(const uint8_t *, size_t, mu_social_room_answer *);

typedef struct mu_social_letter {
    uint32_t id;
    char sender[11], title[33], date[11], time[9];
    int32_t read, arrived;
} mu_social_letter;
typedef struct mu_social_letter_body {
    uint32_t id;
    char text[1001];
} mu_social_letter_body;
int mu_social_mail_header(const uint8_t *, size_t, mu_social_letter *);
int mu_social_mail_body(const uint8_t *, size_t, mu_social_letter_body *);
void mu_social_mail_read_request(mu_social_packet *, uint16_t id);
void mu_social_mail_delete_request(mu_social_packet *, uint16_t id);
int mu_social_mail_write(mu_social_packet *, uint32_t ui, const char *name, const char *title,
                         const uint8_t *body, size_t size);
int mu_social_mail_send_notice(uint8_t result);
#endif
