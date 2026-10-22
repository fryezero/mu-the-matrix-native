/* NATIVE-SOCIAL-001. Game-side social state from pinned capture09 instructions.
 * Address/coverage boundaries: docs/research/client-social.md. No transport/cipher. */
#ifndef MU_SOCIAL_H
#define MU_SOCIAL_H
#include <stddef.h>
#include <stdint.h>
#define MU_SOCIAL_PARTY 5
#define MU_SOCIAL_FRIENDS 50
#define MU_SOCIAL_SLOTS 32
#define MU_SOCIAL_ITEM_BYTES 15

typedef struct mu_party_member {
    char name[11];
    int32_t slot, number, server, world, x, y;
    int32_t hp, mp, max_hp, max_mp, hp_percent, mp_percent;
    uint8_t control, special, in_view;
} mu_party_member;
typedef struct mu_party {
    int32_t count;
    mu_party_member members[MU_SOCIAL_PARTY];
} mu_party;
typedef struct mu_party_marker {
    int32_t key;
    float x, y;
    char name[11];
} mu_party_marker;
/* 0xc77c4c..0xc77e23, 44-byte list records; 0xc7a7a2 state. */
void mu_social_party_member(const uint8_t record[44], int32_t slot, mu_party_member *out);
int mu_social_party_state(int32_t server, int in_view);
/* 0x1270d06: stores the big-endian key even when the external block predicate suppresses the prompt. */
int mu_social_party_request(const uint8_t *packet, size_t size, int blocked, int32_t *key);
/* C2 42 list, C1 43 clear, C1 44 HP/MP list (13-byte records). Bounds are native guards. */
int mu_social_party_receive(mu_party *p, const uint8_t *packet, size_t size);
/* 0xc6b2cc filters hero, server, world, then type 10/key sortIndex/tile pixels. */
int mu_social_party_markers(const mu_party *p, const char *hero, int32_t server, int32_t world,
                            mu_party_marker out[MU_SOCIAL_PARTY]);
int mu_social_party_hp(const mu_party *p, const char *name, int32_t *hp);

typedef struct mu_trade_item {
    uint8_t present, bytes[MU_SOCIAL_ITEM_BYTES];
} mu_trade_item;
typedef struct mu_trade {
    int32_t open, result, notice, zen[2], proposed_zen, level, guild;
    uint8_t ok[2], warned;
    int32_t wait;
    char name[11];
    mu_trade_item items[2][MU_SOCIAL_SLOTS]; /* 0 mine, 1 partner, 8 x 4 grids */
} mu_trade;
/* 0xc45b3e: 0 off, 1 on, 2 warning-once, both off, 25-frame wait. */
void mu_social_trade_lock(mu_trade *t, uint8_t state);
/* 0xc45c09: notice switch, always closes. 1 is success, no notice. */
void mu_social_trade_result(mu_trade *t, uint8_t result);
/* ReceiveTalk-style game boundary: 54 open, 38 remove, 39 item, 3b partner zen,
 * 73 own zen answer, 3e lock, bd result. Item codec is kept as 15 bytes. */
int mu_social_trade_receive(mu_trade *t, const uint8_t *packet, size_t size);

typedef struct mu_social_friend {
    char name[11];
    int32_t server;
} mu_social_friend;
typedef struct mu_social_friends {
    int32_t count;
    mu_social_friend list[MU_SOCIAL_FRIENDS];
} mu_social_friends;
/* 0x12411ff list: count +6, 11-byte name/server records from +7. */
int mu_social_friends_receive(mu_social_friends *f, const uint8_t *packet, size_t size);
int mu_social_friend_set(mu_social_friends *f, const char *name, int32_t server);
int mu_social_friend_remove(mu_social_friends *f, const char *name);
/* Whisper receive 0xc609b5: name +3[10], message +13[60], block predicate and option bypass. */
int mu_social_whisper(const uint8_t *packet, size_t size, int bypass, int blocked, char name[11],
                      char text[61]);
#endif
