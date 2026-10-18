#ifndef MU_ITEM_ATTRIBUTES_H
#define MU_ITEM_ATTRIBUTES_H

#include <stddef.h>
#include <stdint.h>

#include "table_layouts.h"

/* Item.bmd record attributes (NATIVE-DATA-002).
 *
 * The client copies each decoded 708-byte Item.bmd record over an object
 * built by constructor 0x01184277, so record and object layouts coincide.
 * Field names below are authored from the game code that reads each field
 * (docs/research/client-item-attributes.md); they are not original symbol
 * names. A few routines that derive values from the record are
 * reconstructed here; each names its client address.
 */

#define MU_ITEM_RECORD_BYTES 708
#define MU_ITEM_CLASS_SLOTS 16       /* require_class[16] at +0x291 (comparator 0x011844d9 loops 16) */
#define MU_ITEM_RESISTANCES 7        /* resistance[7] at +0x2a1 (comparator loops 7) */
#define MU_ITEM_CODE_LIMIT 0x2c00    /* item predicates accept 0 <= code <= 0x2c00 */

/* The named fields of the whole record, in offset order: the "item.bmd"
 * entry of the table layout catalog (table_layouts.h). Flags carry
 * MU_FIELD_CTOR / MU_FIELD_COMPARED. */
const mu_record_field *mu_item_layout(size_t *count);

typedef struct {
    uint32_t code;                  /* +0x000 lookup key, section * 512 + index */
    uint16_t section, index;        /* +0x004, +0x006 */
    uint8_t kind_a;                 /* +0x250 category (getter 0x00cd5de8, predicate 0x0095fc2e) */
    uint8_t kind_b;                 /* +0x251 sub-category (getter 0x00cd5dba, predicate 0x00987982) */
    uint8_t type;                   /* +0x252 grade (predicate 0x0095fbeb); not zeroed by the constructor */
    uint8_t two_handed;             /* +0x253 */
    uint16_t level;                 /* +0x254 item level, base of requirement and bonus formulas */
    uint8_t slot;                   /* +0x256 equipment slot, 0xff none */
    uint16_t skill;                 /* +0x258 skill index granted by the skill option */
    uint8_t width, height;          /* +0x25a, +0x25b inventory cells */
    uint16_t damage_min, damage_max;/* +0x25c, +0x25e */
    uint8_t defense_rate;           /* +0x260 successful blocking */
    uint16_t defense;               /* +0x262 */
    uint16_t magic_defense;         /* +0x264 */
    uint8_t attack_speed;           /* +0x266 */
    uint8_t walk_speed;             /* +0x267 */
    uint8_t durability;             /* +0x268 */
    uint16_t set_defense_tier;      /* +0x26a argument of formula 1/72 for set-item defense */
    uint8_t magic_durability;       /* +0x26c durability base for staff-like kinds */
    uint32_t magic_power;           /* +0x270 wizardry / curse / spirit power rise, percent */
    uint32_t combat_power;          /* +0x274 tooltip "Combat Power %d%%", formula group 12 */
    uint32_t attack_success_rate;   /* +0x278 tooltip "Attack Success Rate: %d" */
    uint16_t require_strength;      /* +0x27c */
    uint16_t require_dexterity;     /* +0x27e */
    uint16_t require_energy;        /* +0x280 */
    uint16_t require_vitality;      /* +0x282 */
    uint16_t require_command;       /* +0x284 */
    uint16_t require_level;         /* +0x286 */
    uint8_t value;                  /* +0x288 price base, value*value*10/12 */
    uint32_t zen;                   /* +0x28c fixed price */
    uint8_t set_attribute;          /* +0x290 1..6, selects the set stat line (text 0x3b6..0x3bb) */
    uint8_t require_class[MU_ITEM_CLASS_SLOTS]; /* +0x291 minimum class stage per class slot, 0 = no */
    uint8_t resistance[MU_ITEM_RESISTANCES];    /* +0x2a1 */
    uint8_t can_drop;               /* +0x2a8 not zeroed or compared */
    uint8_t can_trade;              /* +0x2a9 */
    uint8_t can_personal_store;     /* +0x2aa constructor writes +0x2a9 twice instead */
    uint8_t can_warehouse;          /* +0x2ab */
    uint8_t can_sell;               /* +0x2ac sell to NPC */
    uint8_t high_value;             /* +0x2ad selling asks for confirmation */
    uint8_t can_repair;             /* +0x2ae */
    uint8_t max_stack;              /* +0x2af 0 = not stackable */
    uint8_t pc_room;                /* +0x2b0 not zeroed or compared */
    uint8_t evolved_pet;            /* +0x2b1 not zeroed or compared */
    uint16_t stat_option_melee;     /* +0x2b2 melee attack/defense increase option */
    uint16_t stat_option_ranged;    /* +0x2b4 */
    uint16_t stat_option_magic;     /* +0x2b6 */
    uint8_t pentagram_grade;        /* +0x2b8 */
    uint8_t field_2b9, field_2ba;   /* +0x2b9, +0x2ba no reader in the restored code */
    uint16_t elemental_attack;      /* +0x2bc pentagram elemental attack increase */
    uint16_t elemental_defense_bonus; /* +0x2be pentagram elemental defense increase */
    uint16_t elemental_defense;     /* +0x2c0 */
} mu_item_attributes;

/* Read the attributes of one decoded 708-byte record (little endian). */
void mu_item_attributes_read(const uint8_t *record, mu_item_attributes *out);

/* Instance state of an item object that the reconstructed routines read.
 * Offsets are those of the client item object (record pointer at +0x00).
 */
typedef struct {
    int32_t code;       /* +0x10 */
    int32_t level;      /* 0..15, object +0x14 bits 3..6 */
    uint8_t ancient;    /* +0x3b option bits; 0x00cd0995(0) tests bits & 0x33 */
    uint8_t period;     /* +0x92 */
    uint8_t expired;    /* +0x93 */
    uint8_t excellent;  /* +0x98, 0x00cd0995(1) tests == 1 */
} mu_item_state;

/* Client 0x00ccc5b0: maximum durability of an item object (stored at
 * object +0x39). The harmony/socket sub-object at +0xe0 is taken as empty
 * (its option adds nothing), an authored restriction.
 */
uint8_t mu_item_max_durability(const mu_item_attributes *a, const mu_item_state *s);

/* Client 0x016bec14: 1 when the item may not be put in the warehouse. */
int mu_item_store_ban(const mu_item_attributes *a, const mu_item_state *s);

/* Client 0x016be1d9: 1 when the item may not be repaired. */
int mu_item_repair_ban(const mu_item_attributes *a, const mu_item_state *s);

#endif
