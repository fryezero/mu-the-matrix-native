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
#endif
