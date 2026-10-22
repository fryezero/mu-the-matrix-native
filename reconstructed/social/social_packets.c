#include "social_packets.h"
#include <stdio.h>
#include <string.h>
static void u16(uint8_t *p, uint16_t v) {
    p[0] = (uint8_t)v;
    p[1] = (uint8_t)(v >> 8);
}
static void u32(uint8_t *p, uint32_t v) {
    for (int i = 0; i < 4; i++)
        p[i] = (uint8_t)(v >> (8 * i));
}
static uint16_t get16(const uint8_t *p) {
    return (uint16_t)(p[0] | p[1] << 8);
}
static uint32_t get32(const uint8_t *p) {
    return (uint32_t)p[0] | (uint32_t)p[1] << 8 | (uint32_t)p[2] << 16 | (uint32_t)p[3] << 24;
}
static void fixed(uint8_t *p, const char *s, size_t n) {
    size_t k = s ? strlen(s) : 0;
    if (k > n)
        k = n;
    memset(p, 0, n);
    if (k)
        memcpy(p, s, k);
}
static void packet(mu_social_packet *p, int n, int wide, uint8_t opcode) {
    memset(p, 0, sizeof *p);
    p->size = n;
    p->data[0] = (uint8_t)(wide ? 0xc2 : 0xc1);
    if (wide) {
        p->data[1] = (uint8_t)(n >> 8);
        p->data[2] = (uint8_t)n;
        p->data[3] = opcode;
    } else {
        p->data[1] = (uint8_t)n;
        p->data[2] = opcode;
    }
}
int mu_social_party_invite(mu_social_packet *p, uint16_t key, int exists, int enabled) {
    memset(p, 0, sizeof *p);
    if (!exists || !enabled)
        return 0;
    packet(p, 5, 0, 0x3a);
    p->send0 = 1;
    p->data[3] = (uint8_t)(key >> 8);
    p->data[4] = (uint8_t)key;
#ifdef MU_SOCIAL2_MUTATION_PARTY
    p->data[3] = (uint8_t)key;
#endif
    return 1;
}
void mu_social_party_answer(mu_social_packet *p, uint16_t key, uint8_t reply) {
    packet(p, 6, 0, 0x86);
    p->send0 = 1;
    p->data[3] = reply;
    p->data[4] = (uint8_t)(key >> 8);
    p->data[5] = (uint8_t)key;
#ifdef MU_SOCIAL2_MUTATION_ANSWER
    p->data[3] ^= 1;
#endif
}
int mu_social_party_popup(int popup, int result, int *reply) {
    if (popup != 13 || (result != 0 && result != 1))
        return 0;
    *reply = 1 - result;
    return 1;
}
int mu_social_party_permission(int target, int blocked, int world_blocked, int has_party, int leader,
                               int target_pk, int hero_pk, int *notice) {
    *notice = 0;
    if (!target)
        return 0;
    if (blocked == 1)
        *notice = 0xe9e;
    else if (world_blocked)
        *notice = 0x1217;
    else if (has_party == 1 && !leader)
        *notice = 0x101;
    else if (target_pk > 3 || hero_pk > 3)
        *notice = 0x1263;
    return *notice == 0;
}
int mu_social_party_autoaccept(int active, int friends, int guild, int is_friend, int exists, int hero_guild,
                               int other_guild) {
    return active &&
           ((friends && is_friend) || (guild && exists && hero_guild != -1 && hero_guild == other_guild));
}
int mu_social_party_leave_prompt(int world, int found, int self, int *notice) {
    *notice = 0;
    if ((world >= 0x2d && world <= 0x32) || (world >= 0x62 && world <= 0x63))
        return 0;
    if (world >= 0x67 && world <= 0x6a) {
        *notice = 0x1217;
        return 2;
    }
    if (!found)
        return 0;
    *notice = self ? 0xf14 : 0xf1f;
    return 1;
}
int mu_social_party_remove_confirm(int popup, int result) {
    return popup == 0x37 && result == 0;
}
int mu_social_party_remove(mu_social_packet *p, uint8_t slot, const char *name, int found, int empty) {
    memset(p, 0, sizeof *p);
    if (!found || empty)
        return 0;
    packet(p, 15, 0, 0xc3);
    p->data[3] = slot;
    fixed(p->data + 4, name, 10);
#ifdef MU_SOCIAL2_MUTATION_REMOVE
    p->data[14] = 1;
#endif
    return 1;
}
int mu_social_party_notice(uint8_t r) {
    static const int notices[17] = {0x1f1, 0x1f2, 0x1f3, 0x1f4,  0x1f5,  0x1f6, 0xbae,  0xbb5, 0xbb6,
                                    0xf0d, 0,     0,     0x1674, 0x1263, 0,     0x187c, 0x186b};
#ifdef MU_SOCIAL2_MUTATION_RESULT
    return r < 17 ? notices[r] + 1 : 0;
#else
    return r < 17 ? notices[r] : 0;
#endif
}
int mu_social_room_request(mu_social_packet *p, const char *name) {
    if (!name || !*name)
        return 0;
    packet(p, 13, 0, 0x3d);
    fixed(p->data + 3, name, 10);
    return 1;
}
void mu_social_room_connect(mu_social_packet *p, uint16_t room, uint32_t ticket) {
    packet(p, 16, 0, 0);
    p->channel = 1;
    u16(p->data + 4, room);
    char text[11];
    snprintf(text, sizeof text, "%u", ticket);
    fixed(p->data + 6, text, 10);
#ifdef MU_SOCIAL2_MUTATION_CONNECT
    p->data[15] = 0;
#endif
}
void mu_social_room_control(mu_social_packet *p, uint8_t opcode) {
    packet(p, 3, 0, opcode);
    p->channel = 1;
}
int mu_social_room_invite(mu_social_packet *p, const char *name, uint16_t room, uint32_t ui) {
    if (!name || !*name)
        return 0;
    packet(p, 20, 0, 0x19);
    fixed(p->data + 3, name, 10);
    u16(p->data + 14, room);
    u32(p->data + 16, ui);
    return 1;
}
void mu_social_room_transform(uint8_t *b, size_t n, const uint8_t key[3]) {
    for (size_t i = 0; i < n; i++)
        b[i] ^= key[i % 3];
}
int mu_social_room_send(mu_social_packet *p, const uint8_t *text, size_t n, const uint8_t key[3]) {
    if (n > 1000 || (n && !text))
        return 0; /* native capacity guard, not an original clamp */
    packet(p, (int)n + 5, 0, 4);
    p->channel = 1;
    p->data[4] = (uint8_t)n;
#ifdef MU_SOCIAL2_MUTATION_SEND_LENGTH
    p->data[4] = (uint8_t)(n > 100 ? 100 : n);
#endif
    if (n)
        memcpy(p->data + 5, text, n);
    mu_social_room_transform(p->data + 5, n, key);
    return 1;
}
int mu_social_room_event_read(const uint8_t *b, size_t n, mu_social_room_event *out) {
    if (!b || !out || n < 15 || b[3] > 1)
        return 0;
    memset(out, 0, sizeof *out);
    out->event = b[3];
    out->user.serial = b[4];
    memcpy(out->user.name, b + 5, 10);
    return 1;
}
int mu_social_room_roster(const uint8_t *b, size_t n, mu_social_room_user *out, size_t capacity) {
    if (!b || (!out && n >= 8 && b[6]) || n < 8 || b[6] > capacity || n < 8 + (size_t)b[6] * 11)
        return -1;
    for (int i = 0; i < b[6]; i++) {
        memset(out + i, 0, sizeof *out);
        out[i].serial = b[8 + i * 11];
        memcpy(out[i].name, b + 9 + i * 11, 10);
    }
    return b[6]
#ifdef MU_SOCIAL2_MUTATION_ROSTER
                   > 30
               ? 30
               : b[6]
#endif
        ;
}
int mu_social_room_text(const uint8_t *b, size_t n, const uint8_t key[3], mu_social_room_message *out) {
    if (!b || !out || n < 5 || b[4] > 100 || n < 5 + (size_t)b[4])
        return 0;
    memset(out, 0, sizeof *out);
    out->serial = b[3];
    memcpy(out->text, b + 5, b[4]);
    mu_social_room_transform((uint8_t *)out->text, b[4], key);
#ifdef MU_SOCIAL2_MUTATION_ROOM
    out->serial ^= 1;
#endif
    return 1;
}
int mu_social_room_open_answer(const uint8_t *b, size_t n, mu_social_room_answer *out) {
    if (!b || !out || n < 36)
        return 0;
    memset(out, 0, sizeof *out);
    memcpy(out->address, b + 3, 15);
    out->room = get16(b + 18);
    out->ticket = get32(b + 20);
    out->mode = b[24];
    memcpy(out->peer, b + 25, 10);
    out->result = b[35];
    return 1;
}
int mu_social_mail_header(const uint8_t *b, size_t n, mu_social_letter *out) {
    if (!b || !out || n < 79 || b[78] > 2)
        return 0;
    memset(out, 0, sizeof *out);
    out->id = get16(b + 4);
    memcpy(out->sender, b + 6, 10);
    memcpy(out->date, b + 16, 10);
    memcpy(out->time, b + 27, 8);
    memcpy(out->title, b + 46, 32);
    out->read = b[78] == 1;
    out->arrived = b[78] == 2;
#ifdef MU_SOCIAL2_MUTATION_HEADER
    out->read = b[78];
#endif
    return 1;
}
int mu_social_mail_body(const uint8_t *b, size_t n, mu_social_letter_body *out) {
    if (!b || !out || n < 30)
        return 0;
    uint16_t len = get16(b + 6);
    if (len > 1000 || n < 30 + (size_t)len)
        return 0;
    memset(out, 0, sizeof *out);
    out->id = get16(b + 4);
    memcpy(out->text, b + 30, len);
#ifdef MU_SOCIAL2_MUTATION_MAIL
    out->id = get16(b + 5);
#endif
    return 1;
}
void mu_social_mail_read_request(mu_social_packet *p, uint16_t id) {
    packet(p, 6, 0, 0x30);
    u16(p->data + 4, id);
#ifdef MU_SOCIAL2_MUTATION_READ
    p->data[4] = (uint8_t)(id >> 8);
    p->data[5] = (uint8_t)id;
#endif
}
void mu_social_mail_delete_request(mu_social_packet *p, uint16_t id) {
    packet(p, 6, 0, 0x40);
    u16(p->data + 4, id);
#ifdef MU_SOCIAL2_MUTATION_DELETE
    p->data[2] = 0x41;
#endif
}
int mu_social_mail_write(mu_social_packet *p, uint32_t ui, const char *name, const char *title,
                         const uint8_t *body, size_t n) {
    if (!name || !*name || !title || !*title || !body || !n || n > 1000)
        return 0;
    packet(p, (int)n + 54, 1, 0xa7);
    p->send0 = p->send1 = 1;
#ifdef MU_SOCIAL2_MUTATION_MAIL_WRITE
    ui ^= 0x100;
#endif
    u32(p->data + 4, ui);
    fixed(p->data + 8, name, 10);
    fixed(p->data + 18, title, 32);
    u16(p->data + 52, (uint16_t)n);
    memcpy(p->data + 54, body, n);
    return 1;
}
int mu_social_mail_send_notice(uint8_t result) {
    static const int notices[8] = {0x41d, 0x416, 0x425, 0x428, 0x429, 0, 0x42c, 0x1a7};
    return result < 8 ? notices[result] : 0;
}
