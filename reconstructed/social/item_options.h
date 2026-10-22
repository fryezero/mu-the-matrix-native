#ifndef MU_SOCIAL_ITEM_OPTIONS_H
#define MU_SOCIAL_ITEM_OPTIONS_H
#include <stdint.h>
/* Packet-to-converter arguments, 0x00f08dca. The caller's record-kind
 * conversion remains separate. No item payload or table is compiled in. */
typedef struct mu_social_item_wire {
    int32_t code;
    uint8_t level_word, durability, excellent, ancient, flags, harmony;
    uint8_t sockets[5], extra[3];
} mu_social_item_wire;
static inline int32_t mu_social_item_code(const uint8_t b[15]) {
    return b[0] | ((b[3] & 0x80) << 1) | ((b[5] & 0xf0) << 5) | ((b[5] & 1) << 13);
}
void mu_social_item_unpack(const uint8_t bytes[15], mu_social_item_wire *out);
/* Native inverse for offline inventory escrow; preserves all 15 wire bytes. */
void mu_social_item_pack(const mu_social_item_wire *item, uint8_t bytes[15]);

/* Item.bmd and finalized-state inputs at the converter's external boundaries.
 * excellent_resolved is ITEM+0x98, not the raw packet excellent mask. */
typedef struct mu_social_item_context {
    int32_t kind_a, kind_b, grade, skill, base_level, normalized_slot;
    int32_t slot_flags[4], excellent_resolved;
    int32_t can_trade, capability, character_option, character_status;
} mu_social_item_context;
typedef struct mu_social_item_option {
    int32_t id, value;
} mu_social_item_option;
typedef struct mu_social_item_decoded {
    int32_t code, level_word, level, skill_bit, luck_bit, add_rank, skill;
    int32_t durability, excellent, ancient, period, expired, flag_72;
    int32_t harmony_kind, harmony_level, socket_subtype, socket_count;
    int32_t socket_raw[5], seed_index[5], seed_level[5], socket_bonus;
    int32_t element, element_aux, rank[4][4];
    int32_t extra_excellent[3], special_raw[5], extra_word, extra_124[5];
    int32_t advanced_group, advanced_level, saved_group, advanced_slot, advanced_option;
    int32_t artifact_count, artifact[3][3], guardian_base, guardian_keys[5];
    int32_t prefix_count;
    mu_social_item_option prefix[8];
} mu_social_item_decoded;
/* Category conversion 0xf08fb2 through its named external option/stat boundaries. */
void mu_social_item_convert(const mu_social_item_wire *, const mu_social_item_context *,
                            mu_social_item_decoded *);
int mu_social_item_advanced_eligible(const mu_social_item_wire *, const mu_social_item_context *,
                                     int check_level);
int mu_social_item_advanced_group(const mu_social_item_wire *, const mu_social_item_context *);
/* 0x16bed45: true means banned, separately from incoming-item conversion. */
int mu_social_item_trade_banned(const mu_social_item_wire *, const mu_social_item_context *);

/* ccc993 finalizer. Callers initialize retained skill/cache/slot state and
 * supply the opaque eligibility result and external table/formula boundaries. */
typedef struct mu_social_item_final_env {
    void *context;
    int (*formula)(void *, int family, int index, int arg1, int arg2, double *value);
    int (*excellent_row)(void *, int family, int category, int id, int slot);
    int32_t level_word, ancient, enabled, class_byte, character_stat, state_level;
    int32_t special_tag, special_row, special_enabled, special_bonus[3], special_lows[3];
    int32_t state_known; /* external item-state inputs are present, including a real zero */
} mu_social_item_final_env;
typedef struct mu_social_item_finalized {
    int32_t count;
    mu_social_item_option options[8];
    int32_t rank, skill, excellent, slots[9], family, category;
    int32_t special_count, special[5][3], bonus_count, bonus[3][3], unresolved;
} mu_social_item_finalized;
void mu_social_item_finalize(const mu_social_item_wire *, const mu_social_item_context *,
                             const mu_social_item_final_env *, mu_social_item_finalized *);
int mu_social_item_excellent_value(int category, int id, int value_type, int base, int level_word,
                                   int record_level, int hero_level, const mu_social_item_final_env *,
                                   double *value);
#endif
