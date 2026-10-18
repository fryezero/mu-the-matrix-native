#ifndef MU_TABLE_LAYOUTS_H
#define MU_TABLE_LAYOUTS_H

#include <stddef.h>
#include <stdint.h>

/* Record layouts of the decoded client data tables (NATIVE-DATA-002).
 *
 * Each layout names the fields of one table's fixed-size record. Names are
 * authored from the evidence class recorded per field (see
 * docs/research/client-item-attributes.md); they are not original symbol
 * names. Bytes not covered by a field are reported as unnamed spans.
 */

typedef enum {
    MU_FIELD_U8 = 1,
    MU_FIELD_I8,
    MU_FIELD_U16,
    MU_FIELD_I16,
    MU_FIELD_U32,
    MU_FIELD_I32,
    MU_FIELD_F32,
    MU_FIELD_TEXT,   /* NUL-terminated client code page text; count = byte length */
    MU_FIELD_BYTES   /* opaque bytes; count = byte length */
} mu_field_type;

typedef enum {
    MU_EVIDENCE_CONSUMER = 1, /* client code that reads the field was traced (static or verified) */
    MU_EVIDENCE_LAYOUT,       /* offset/width from a record constructor, comparator or loader; meaning open */
    MU_EVIDENCE_DATA          /* inferred from the decoded installed contents only */
} mu_field_evidence;

/* Field flags (Item.bmd). */
#define MU_FIELD_CTOR     0x01u /* zeroed by the record constructor */
#define MU_FIELD_COMPARED 0x02u /* compared by the record comparator */

typedef struct {
    uint16_t offset;
    uint8_t type;      /* mu_field_type */
    uint8_t evidence;  /* mu_field_evidence */
    uint16_t count;    /* array elements (1 = scalar); byte length for TEXT/BYTES */
    uint16_t stride;   /* bytes between array elements; 0 = element width */
    uint8_t flags;
    const char *name;
} mu_record_field;

typedef struct {
    const char *file;          /* table file name, lower case */
    uint32_t record_size;
    const mu_record_field *fields;
    uint32_t field_count;
} mu_record_layout;

/* Element width in bytes (TEXT/BYTES: 1). */
unsigned mu_field_width(const mu_record_field *field);
/* Bytes the field spans in the record. */
unsigned mu_field_span(const mu_record_field *field);
/* Integer value of element i of a numeric field (sign-extended for I types;
 * F32 returns the raw bits). */
int64_t mu_field_integer(const mu_record_field *field, const uint8_t *record, unsigned i);
/* F32 element i. */
float mu_field_float(const mu_record_field *field, const uint8_t *record, unsigned i);

const mu_record_layout *mu_record_layouts(size_t *count);
/* Case-insensitive lookup by table file name; NULL if no layout. */
const mu_record_layout *mu_record_layout_find(const char *file);
const char *mu_field_evidence_name(mu_field_evidence evidence);

#endif
