#ifndef MU_GI_ITEM_SETS_H
#define MU_GI_ITEM_SETS_H

/* The set-item prefix of item labels (NATIVE-FIDELITY-001, docs/research/client-fidelity.md).
 *
 * The name builder 0x017ea422 starts a plain item's label with
 * 0x009953ef()->0x009e051c(item): the set manager [0x01d1dcc0] answers 0x009e0551(code, item +0x3b). The set
 * manager is filled at start-up by 0x009e02a8:
 *
 *   ItemSetType.bmd (0x009ddde0: 0x2c00 records of 10 bytes at +4, per-record XOR, checksum 0xe5f1),
 *   ItemSetOption.bmd (0x009ddf86: 1000 records of 0x1d4 bytes at +0x1b804, checksum 0xa2f1),
 *   ItemSetOptionText.bmd (0x009df9ca), then
 *   0x009de132: for i = 1..999 with a non-empty name (record +0): a set {index i, name record +0, second name
 *     record +0x40}, inserted into the std::map<std::string, set *> at +0x8dc24 by its name (a set whose name is
 *     already there is dropped); then for every code 0..0x2bff and k = 0..3 with word k of its ItemSetType
 *     record non-zero: an entry {code, set bits (1, 2, 0x10, 0x20)[k]} (dropped with a message box when the
 *     code has no Item.bmd record), appended to the first set in map order whose index equals the word: to its
 *     pair list when LegendaryItemSetType 0x011289d6(word, code) holds (0x0107717c: on the first call the set
 *     gets, for each of the legendary record's two code pairs that is not (-1, -1), a pair of entries with those
 *     codes and set bits 0; the entry then replaces every pair slot with its code), otherwise to its entry list;
 *   0x009debe4: CashItemSetOption's sets get indices base + 1 + i (base: the last non-empty ItemSetOption
 *     index from the map size up, plus 1) and are inserted the same way; each of its items (code group * 512 +
 *     index, set bits 1) goes to the entry list of the set whose index is base + its set field.
 *
 *   0x009e0551(code, bits): for each set in map order (std::string less): an entry list item with that code
 *     whose set bits equal bits & 0x33, or any entry with that code when the code's Item.bmd kind B (+0x251) is
 *     0x79, gives the set's second name; then a pair slot with that code and set bits == bits & 0x33 does;
 *     otherwise "".
 *
 * The builder then copies the prefix and appends the record name with no separator (strcat). */

#include <stddef.h>
#include <stdint.h>

#define MU_GI_SET_CODES 0x2c00
#define MU_GI_SET_TYPE_BYTES 10
#define MU_GI_SET_OPTIONS 1000
#define MU_GI_SET_OPTION_BYTES 0x1d4

typedef struct mu_gi_set_inputs {
    const uint8_t *set_type;        /* decoded ItemSetType records (MU_GI_SET_CODES x 10 bytes) */
    const uint8_t *set_option;      /* decoded ItemSetOption records (1000 x 0x1d4 bytes) */
    void *context;
    int (*has_record)(void *context, int32_t code);              /* 0x00cd5d29 != NULL */
    /* LegendaryItemSetType 0x011288c7: the record's four codes (default record when absent); NULL: no table */
    int (*legendary)(void *context, int32_t type, int32_t codes[4]);
    size_t cash_set_count;          /* CashItemSetOption sets (name, second name) and items */
    const char *const *cash_names, *const *cash_names2;
    size_t cash_item_count;
    const int32_t *cash_items;      /* group, index, set triples */
} mu_gi_set_inputs;

typedef struct mu_gi_sets mu_gi_sets;

mu_gi_sets *mu_gi_sets_build(const mu_gi_set_inputs *in);
void mu_gi_sets_free(mu_gi_sets *sets);
size_t mu_gi_sets_count(const mu_gi_sets *sets);
/* 0x009e0551: the prefix ("" when none); kind_b is the code's Item.bmd kind B (+0x251). */
const char *mu_gi_set_prefix(const mu_gi_sets *sets, int32_t code, uint8_t set_bits, uint8_t kind_b);

#endif
