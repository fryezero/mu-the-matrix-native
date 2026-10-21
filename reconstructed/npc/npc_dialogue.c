/* NPC dialogue manager lookups and the npcdialogue window's choice (NATIVE-LANG-002); see npc_dialogue.h. */
#include "npc_dialogue.h"

#include <stdlib.h>
#include <string.h>

static int32_t rd32(const uint8_t *p)
{
    return (int32_t)((uint32_t)p[0] | (uint32_t)p[1] << 8 | (uint32_t)p[2] << 16 | (uint32_t)p[3] << 24);
}

static int cmp_record(const void *a, const void *b)
{
    int32_t x = ((const mu_dlg_record *)a)->key, y = ((const mu_dlg_record *)b)->key;
    return (x > y) - (x < y);
}

static int cmp_word(const void *a, const void *b)
{
    int32_t x = ((const mu_dlg_word *)a)->id, y = ((const mu_dlg_word *)b)->id;
    return (x > y) - (x < y);
}

long mu_dlg_parse_records(mu_dlg_tables *t, const uint8_t *decoded, size_t size)
{
    size_t n = size / MU_DLG_RECORD_SIZE;
    mu_dlg_record *r = calloc(n ? n : 1, sizeof *r);
    if (!r)
        return -1;
    size_t kept = 0;
    for (size_t k = 0; k < n; k++) {
        const uint8_t *p = decoded + k * MU_DLG_RECORD_SIZE;
        mu_dlg_record rec;
        rec.key = rd32(p);
        rec.text = rd32(p + 4);
        for (int i = 0; i < MU_DLG_OPTIONS; i++) {
            rec.option_text[i] = rd32(p + 8 + 8 * i);
            rec.option_next[i] = rd32(p + 12 + 8 * i);
        }
        int dup = 0;                  /* std::map insert: a key already present keeps its record */
        for (size_t j = 0; j < kept && !dup; j++)
            dup = r[j].key == rec.key;
        if (!dup)
            r[kept++] = rec;
    }
    qsort(r, kept, sizeof *r, cmp_record);
    free(t->records);
    t->records = r;
    t->nrecords = kept;
    return (long)kept;
}

long mu_dlg_parse_words(mu_dlg_tables *t, const uint8_t *decoded, size_t size)
{
    /* The loader reads each text into one 0x500-byte stack buffer (ebp-0x564) without a terminator and builds
     * the std::string from its first NUL: a text without a NUL continues with the bytes a longer earlier text
     * left there (the buffer's first contents are taken as zero). */
    static const size_t BUFFER = 0x500;
    uint8_t buffer[0x500 + 1];
    memset(buffer, 0, sizeof buffer);
    size_t cap = 256, n = 0, off = 0;
    mu_dlg_word *w = malloc(cap * sizeof *w);
    if (!w)
        return -1;
    while (off + 6 <= size) {
        int32_t id = rd32(decoded + off);
        int16_t len = (int16_t)((uint16_t)decoded[off + 4] | (uint16_t)decoded[off + 5] << 8);   /* movsx */
        off += 6;
        if (len < 0 || (size_t)len > BUFFER || off + (size_t)len > size)
            break;
        memcpy(buffer, decoded + off, (size_t)len);
        off += (size_t)len;
        int dup = 0;
        for (size_t j = 0; j < n && !dup; j++)
            dup = w[j].id == id;
        if (dup)
            continue;
        if (n == cap) {
            mu_dlg_word *nw = realloc(w, cap * 2 * sizeof *w);
            if (!nw)
                break;
            w = nw;
            cap *= 2;
        }
        const uint8_t *nul = memchr(buffer, 0, BUFFER);
        size_t l = nul ? (size_t)(nul - buffer) : BUFFER;
        char *s = malloc(l + 1);
        if (!s)
            break;
        memcpy(s, buffer, l);
        s[l] = 0;
        w[n].id = id;
        w[n].text = s;
        n++;
    }
    qsort(w, n, sizeof *w, cmp_word);
    for (size_t i = 0; i < t->nwords; i++)
        free(t->words[i].text);
    free(t->words);
    t->words = w;
    t->nwords = n;
    return (long)n;
}

void mu_dlg_free(mu_dlg_tables *t)
{
    if (!t)
        return;
    for (size_t i = 0; i < t->nwords; i++)
        free(t->words[i].text);
    free(t->words);
    free(t->records);
    memset(t, 0, sizeof *t);
}

void mu_dlg_set_npc(mu_dlg_tables *t, int32_t npc)
{
    t->npc = npc;
}

const mu_dlg_record *mu_dlg_find(const mu_dlg_tables *t, int32_t npc, int32_t state)
{
    mu_dlg_record key;
    key.key = (int32_t)(((uint32_t)npc << 16) + (uint32_t)state);   /* shl eax, 0x10; add eax, state */
    return t->records ? bsearch(&key, t->records, t->nrecords, sizeof key, cmp_record) : NULL;
}

const char *mu_dlg_text(const mu_dlg_tables *t, int32_t id)
{
    mu_dlg_word key;
    key.id = id;
    const mu_dlg_word *w = t->words ? bsearch(&key, t->words, t->nwords, sizeof key, cmp_word) : NULL;
    return w ? w->text : NULL;
}

const char *mu_dlg_state_text(const mu_dlg_tables *t, int32_t state)
{
    if (!t->npc)
        return NULL;
    const mu_dlg_record *r = mu_dlg_find(t, t->npc, state);
    return r ? mu_dlg_text(t, r->text) : NULL;
}

const char *mu_dlg_option_text(const mu_dlg_tables *t, int32_t state, int32_t i)
{
    if (!t->npc || i < 0 || i >= MU_DLG_OPTIONS)
        return NULL;
    const mu_dlg_record *r = mu_dlg_find(t, t->npc, state);
    if (!r || !r->option_text[i])
        return NULL;
    return mu_dlg_text(t, r->option_text[i]);
}

int32_t mu_dlg_option_next(const mu_dlg_tables *t, int32_t state, int32_t i)
{
    if (!t->npc)
        return 0;
    if (i < 0 || i >= MU_DLG_OPTIONS)
        return -1;
    const mu_dlg_record *r = mu_dlg_find(t, t->npc, state);
    if (!r || !r->option_text[i])
        return -1;
    return r->option_next[i];
}

mu_dlg_choice mu_dlg_select(const mu_dlg_tables *t, int32_t state, int32_t choice)
{
    mu_dlg_choice c;
    int32_t next = mu_dlg_option_next(t, state, choice);
    if (next <= MU_DLG_SHOW_LIMIT && next != -1) {
        c.kind = MU_DLG_SHOW;
        c.value = next;
    } else if (next >= MU_DLG_ACTION_FIRST && next <= MU_DLG_ACTION_LAST) {
        c.kind = MU_DLG_ACTION;
        c.value = next;
    } else {
        c.kind = MU_DLG_SHOW;
        c.value = MU_DLG_FALLBACK_STATE;
    }
    return c;
}

int mu_dlg_option_count(const mu_dlg_tables *t, int32_t state)
{
    int n = 0;
    while (n < MU_DLG_OPTIONS && mu_dlg_option_text(t, state, n))
        n++;
    return n;
}

int mu_dlg_action_closes(int32_t action)
{
    /* the cases of the jump table at 0x00be9915 that call 0x00be8565 */
    return action == 902 || action == 910 || (action >= 915 && action <= 920);
}
