#ifndef MU_MIX_RULES_H
#define MU_MIX_RULES_H
#include <stddef.h>
#include <stdint.h>

/* Client layouts. No client data is embedded. Sources are the 100-byte
 * mix-item summaries, recipes are decoded Mix.bmd rows (928 bytes), and
 * conditions are their 72-byte records at +0x15c. Native hosts build these
 * summaries from their own items. See docs/research/client-mix.md. */
#define MU_MIX_SOURCE_SIZE 100
#define MU_MIX_RECIPE_SIZE 928
#define MU_MIX_MAX_SOURCES 32
#define MU_MIX_MAX_CONDITIONS 8
int mu_mix_matches(const uint8_t *source, const uint8_t *condition);
/* Scalar part of 0x00d07528. Supports ordinary items without harmony
 * vectors. Returns 0 for that unsupported state or invalid record codes.
 * item is the client's 300-byte ITEM scalar layout; record is 708 bytes.
 * value is supplied by
 * the already reconstructed ItemValue path. Writes a 100-byte summary. */
int mu_mix_source_make(uint8_t *out, const uint8_t *item, const uint8_t *record, uint32_t value);
/* Mix valuation 0x00d07e3f; buy_value is ItemValue(item, 0), used only
 * outside the helper's special item-code cases. */
uint32_t mu_mix_value(int32_t code, uint32_t buy_value);
int32_t mu_mix_repeats(const uint8_t *sources, int32_t count, const uint8_t *recipe);
int mu_mix_extra(int32_t kind, const uint8_t *recipe);
/* Readiness consumes +0x24 in each summary as the client does. */
int mu_mix_ready(uint8_t *sources, int32_t count, const uint8_t *recipe);

/* Rate expression's inputs from the mix state. Values are unsigned except
 * max_rate and first_level, following the original conversion instructions. */
typedef struct mu_mix_values {
    int32_t max_rate, first_level;
    uint32_t total, excellent, equipment, ancient, other, first_value, bonus, wing;
} mu_mix_values;
/* Returns 0 for malformed/unsupported expressions instead of the client's
 * unbounded recursion. Non-finite intermediates and zero divisors are
 * rejected. Writes the binary32 result and token cursor. */
int mu_mix_formula(const uint8_t *recipe, const mu_mix_values *values, float *out, int32_t *cursor);
uint32_t mu_mix_rate(uint32_t formula, uint32_t cap, uint32_t bless, uint32_t life,
                     uint32_t charm, int add_bless, int add_life, int subtract_charm);
/* A/B/C only. Other modes return 0 as an unsupported sentinel, NOT a valid
 * free quote. A host must check the mode before using the returned cost. */
uint32_t mu_mix_cost(uint8_t type, uint32_t base, uint32_t repeats, uint32_t rate);
/* Manager 0x00d0b2c6. Rows are in their original group order and their
 * +0 IDs must equal that order, as in the client's loader. Returns -1
 * without a candidate. A candidate may be incomplete: test readiness
 * separately. force skips the client's single-row shortcut. */
int32_t mu_mix_select(uint8_t *sources, int32_t count, const uint8_t *rows, int32_t row_count, int force);
int32_t mu_mix_score(uint8_t *sources, int32_t count, const uint8_t *recipe);
int mu_mix_same(const uint8_t *a, const uint8_t *b); /* 0x00d0a318 */
/* Scalar no-harmony branch of 0x00d08e38, class filter -1. */
int mu_mix_group_add(uint8_t *sources, int count, const uint8_t *source, uint32_t item_value, uint8_t durability);
/* Scalar aggregation 0x00d096f0 / 0x00d09811. Starts from zero. */
void mu_mix_values_make(mu_mix_values *out, const uint8_t *sources, int32_t count);
/* 0x00d0960d overwrites these for EVERY match of condition 0. Historical
 * formula field names: first_value is summary +0x10, first_level +0x38. */
void mu_mix_first_values(mu_mix_values *out, const uint8_t *sources, int32_t count, const uint8_t *recipe);
typedef struct mu_mix_additions { uint32_t bless, life, charm; } mu_mix_additions;
/* 0x00d09366: level_254 supplies each source's optional Item.bmd +0x254. */
void mu_mix_additions_make(mu_mix_additions *out, const uint8_t *sources, int32_t count, const uint16_t *level_254);
#endif
