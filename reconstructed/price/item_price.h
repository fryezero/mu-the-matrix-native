#ifndef MU_ITEM_PRICE_H
#define MU_ITEM_PRICE_H

/* The client's item value and repair-cost routines (NATIVE-LANG-002,
 * docs/research/client-lang-tables.md).
 *
 * Pinned inputs as in reconstructed/data: restored text capture 09
 * (2bd5f2e9...3724, VA 0x00401000), second image section run 10.
 *
 *   ItemValue        0x0169320b..0x01696338  int ItemValue(ITEM *item, int goldType)
 *   ConvertRepairGold 0x016b8d16..0x016b9103 int (int value, int durability, int maxDurability,
 *                                                short code, char *text)
 *
 * goldType (from the 18 callers of 0x0169320b, static):
 *   0  buy price: NpcShop's purchase checks 0x00bf0007/0x00bf0233 (against the hero's zen +0x2d70),
 *      the tooltip's price line 0x00f0bee3/0x00f0bf3a (GlobalText 0x654, the value as unsigned);
 *   1  sell price: the sell paths 0x00ab9432/0x00ad5f83/0x00ad78b4/0x00ad7d98 (GlobalText 0xc4c when the
 *      hero's zen would pass 2,000,000,000), the tooltip's sell line 0x00f0bfe2 (GlobalText 0x3f);
 *   2  repair base: 0x016c3cb5 (one item, GlobalText 0xee) and the repair-all sums 0x016c800b/0x016c813b
 *      pass it to ConvertRepairGold.
 *
 * Labels: "verified" = the client routine ran in Unicorn and equalled this C
 * (scripts/validate_item_price.py); "modelled" = an input of this C that the
 * validator supplies to the client through a stub; "inferred" = see below.
 *
 * Inputs the routine reads besides the record and the item object (all
 * modelled in the validator):
 *   - the current world [0x01cf15fc] (world 0x5c triples a few buy prices);
 *   - byte +4 of the singleton 0x01d1dbd4 (0x0095f75d / 0x0095fb99): when set, the sell price is 1
 *     (the tooltip's sell line then shows 1 too);
 *   - the socket manager 0x06fb4518 (+0x68 + id * 0xa8 + 4, SocketItem.bmd's seed index) for the
 *     seed-sphere prices of socket items (0x010a91a7), which call ItemValue again on a new object;
 *   - MonsterSoulConversion (Lang table 0x06fbbe1c, map +0x44, lookup 0x01135146 through 0x00d371cb):
 *     a listed code costs 10000;
 *   - the pet / special-durability record (codes 0x1a04, 0x1a05, 0x28f7..0x28fa, 0x2900: 0x00cd2326):
 *     0x00c9362d finds it (equipment or pet manager) and 0x00c93eb2 prices it; its status -1 makes the
 *     whole routine return -1;
 *   - the item-script manager's kind A of the code (0x00cd4ea8/0x00cd5de8): kind 0x22 costs 50000.
 *
 * INFERRED: three compares of ItemValue's excellent-option switches are
 * displaced by 5-byte jumps out of the restored image (0x01694b6b ->
 * 0x10b401b0, 0x01694d5e -> 0x10b40050, 0x01694e4b -> 0x10b40100; a module
 * that is out of scope).  The bytes left behind are the tail of
 * "cmp dword [ebp-X], imm8; je +0x1b" followed by the chain's remaining
 * cases 8/12/16 (and 10/15/20); the displaced first values are taken as 4
 * and 5 (the 4/8/12/16 and 5/10/15/20 ladders).  The validator executes the
 * same displaced compares in a stub at the jump targets, so these three
 * values are a reading, not a verified fact; whatever the out-of-scope code
 * does there in the live client is not reproduced. */

#include <stddef.h>
#include <stdint.h>

#define MU_PRICE_BUY 0
#define MU_PRICE_SELL 1
#define MU_PRICE_REPAIR 2

#define MU_PRICE_SPECIALS 8
#define MU_PRICE_SOCKETS 5

/* The item object fields ItemValue reads (client object offsets). */
typedef struct mu_price_item {
    int32_t code;                       /* +0x10 (group * 512 + index; -1 = none: price 0) */
    int32_t level;                      /* +0x14 bits 3..6 (0..15) */
    uint8_t durability;                 /* +0x38 durability, or the stack count */
    uint8_t max_durability;             /* +0x39 */
    uint8_t set_bits;                   /* +0x3b (0x00cd0995(0): bits & 0x33 = set item) */
    uint8_t special_count;              /* +0x3d (at most MU_PRICE_SPECIALS here) */
    uint16_t special[MU_PRICE_SPECIALS];        /* +0x3e option ids */
    uint16_t special_value[MU_PRICE_SPECIALS];  /* +0x4e option values */
    uint16_t skill;                     /* +0x60 */
    uint8_t flag_72;                    /* +0x72 (1: +16 %) */
    uint8_t slot_73[5];                 /* +0x73..+0x77 (0xff empty; value >> 4 = rank; +0x76 also wing-core bits) */
    uint8_t socket_count;               /* +0x78 (socket items; also the level byte of kinds 0x19/0x1a) */
    uint8_t socket[MU_PRICE_SOCKETS];   /* +0x79.. seed ids (0xff empty) */
    uint8_t socket_level[MU_PRICE_SOCKETS];     /* +0x7e.. */
    uint8_t period, expired;            /* +0x92, +0x93 */
    uint8_t excellent;                  /* +0x98 (0x00cd0995(1): == 1) */
    uint8_t excellent_options[9];       /* +0x99..+0xa1 (0xff empty) */
    int32_t harmony;                    /* +0xe8 (0x00cb6efe on +0xe0): 50000 zen each */
} mu_price_item;

typedef struct mu_price_state {
    int32_t world;                      /* [0x01cf15fc] */
    uint8_t sell_flag;                  /* byte +4 of [0x01d1dbd4] */
    const int32_t *socket_seed;         /* 256 entries (socket manager +0x68 + id*0xa8 + 4); NULL: all 0 */
    /* Item.bmd record of a code (the item-script manager); NULL: only `record` for its own code. */
    const uint8_t *(*record_of)(void *user, int32_t code);
    /* MonsterSoulConversion has the code (0x00d371cb); NULL: never. */
    int (*soul_conversion)(void *user, int32_t code);
    void *user;
    int32_t pet_status;                 /* first int of 0x00c9362d's record (-1: the routine returns -1) */
    uint32_t pet_value;                 /* 0x00c93eb2's value for that record */
} mu_price_state;

/* A freshly constructed item object (0x00ccbaa2): everything 0, code -1,
 * the excellent options 0xff. */
void mu_price_item_init(mu_price_item *item);

/* ItemValue 0x0169320b: record = the item's 708-byte Item.bmd record (the
 * routine dereferences it unconditionally; NULL returns 0, which the client
 * would not); state may be NULL (world 0, no flags, no tables).  The client
 * returns the low 32 bits of its 64-bit gold; prices above 2^31 come out
 * negative here as there (the tooltip's buy line prints them unsigned). */
int32_t mu_item_price(const uint8_t *record, const mu_price_item *item, int gold_type, const mu_price_state *state);

/* ConvertRepairGold 0x016b8d16.  Window state (GFx manager 0x00ac3bf7):
 * NpcShop (+0xf4) visible and its repair flag (+0xb0, set by the talk case
 * for the repair NPCs), the inventory (+0xa0) visible.  discount_percent is
 * the sum the routine collects from three equipped helper items (Muun-like
 * slots through +0x1a8 / 0x00c062b5, info +0xc == 15, table +0x110 by level);
 * modelled as an input.  Assumes the x87 precision control the Windows
 * process starts with (53-bit, 0x27f) for the two square roots. */
typedef struct mu_repair_state {
    int shop_visible, shop_repair_flag, inventory_visible;
    int32_t discount_percent;
} mu_repair_state;
int32_t mu_item_repair_cost(int32_t value, int32_t durability, int32_t max_durability, int16_t code,
                            const mu_repair_state *state);

/* The repair price of one item as 0x016c3cb5 builds it: ItemValue(item, 2),
 * nothing when it is -1 or the item is at full durability (returns 0, *shown
 * = 0), else ConvertRepairGold(value, durability, max, code). */
int32_t mu_item_repair_price(const uint8_t *record, const mu_price_item *item, const mu_price_state *state,
                             const mu_repair_state *repair, int *shown);

/* The client's zen formatting 0x016b8b26 for integral values: "%d" of the
 * leading group, then ",%03d" groups (static reading).  Returns out. */
char *mu_price_format(uint32_t value, char *out, size_t cap);

#endif
