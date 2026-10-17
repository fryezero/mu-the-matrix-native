#include "data_tables.h"

#include "data_codec.h"

#include <ctype.h>
#include <string.h>

/* Catalog of loaders recovered from the pinned client (NATIVE-DATA-001).
 * Every row is backed by an actual-instruction trace of the loader in
 * scripts/validate_data_tables.py; see docs/research/client-data-tables.md.
 */
#define CHK MU_DATA_HAS_CHECKSUM
#define NZ MU_DATA_COUNT_NONZERO
static const mu_data_spec SPECS[] = {
    /* file, client path, loader, kind, R, N, checksum key, codec, codec key, flags */
    {"item.bmd", "Data\\Local\\Item.bmd", 0x00cd4f2a, MU_DATA_COUNTED, 708, 0, 0xe2f1, 0, 0, CHK|NZ},
    {"itemaddoption.bmd", "Data\\Local\\ItemAddOption.bmd", 0x00cd4bff, MU_DATA_FIXED_PLAIN, 0x2c000, 1, 0, 0, 0, 0},
    {"excellentcommonoption.bmd", "Data\\Local\\ExcellentCommonOption.bmd", 0x00cd51fe, MU_DATA_COUNTED, 120, 0, 0xe2f1, 0, 0, CHK|NZ},
    {"excellentwingoption.bmd", "Data\\Local\\ExcellentWingOption.bmd", 0x00cd51fe, MU_DATA_COUNTED, 120, 0, 0xe2f1, 0, 0, CHK|NZ},
    {"formuladata.bmd", "Data\\Local\\FormulaData.bmd", 0x0117b199, MU_DATA_FORMULA, 260, 0, 0xe2f1, 0, 0, CHK|NZ},
    {"pentagrammixneedsource.bmd", "Data\\Local\\PentagramMixNeedSource.bmd", 0x00fc6a61, MU_DATA_COUNTED, 188, 0, 0xe2f1, 0, 0, CHK|NZ},
    {"muunoption.bmd", "Data\\Local\\MuunOption.bmd", 0x009b3a26, MU_DATA_COUNTED, 836, 0, 0xe2f1, 0, 0, CHK|NZ},
    {"muunaddoption.bmd", "Data\\Local\\MuunAddOption.bmd", 0x009b3cb1, MU_DATA_COUNTED, 40, 0, 0xe2f1, 0, 0, CHK|NZ},
    {"muuninfo.bmd", "Data\\Local\\MuunInfo.bmd", 0x009b3f7e, MU_DATA_COUNTED, 60, 0, 0xe2f1, 0, 0, CHK|NZ},
    {"muuntooltipinfo.bmd", "Data\\Local\\MuunTooltipInfo.bmd", 0x009b41e7, MU_DATA_COUNTED, 32, 0, 0xe2f1, 0, 0, CHK|NZ},
    {"muunexchange.bmd", "Data\\Local\\MuunExchange.bmd", 0x009b0fd5, MU_DATA_TWO_COUNTS, 16, 0, 0xe2f1, 0, 0, CHK|NZ},
    {"muunrenderinfo.bmd", "Data\\Local\\MuunRenderInfo.bmd", 0x009b90d5, MU_DATA_COUNTED, 612, 0, 0xe2f1, 0, 0, CHK|NZ},
    {"muunmeshinfo.bmd", "Data\\Local\\MuunMeshInfo.bmd", 0x009b9510, MU_DATA_COUNTED, 300, 0, 0xe2f1, 0, 0, CHK|NZ},
    {"statoption.bmd", "Data\\Local\\StatOption.bmd", 0x00995776, MU_DATA_COUNTED, 52, 0, 0xe2f1, 0, 0, CHK|NZ},
    {"statoptiontext.bmd", "Data\\Local\\StatOptionText.bmd", 0x00995a29, MU_DATA_COUNTED, 260, 0, 0xe2f1, 0, 0, CHK|NZ},
    {"quest.bmd", "Data\\Local\\Quest.bmd", 0x009f4866, MU_DATA_FIXED_PLAIN, 1000, 200, 0, 0, 0, 0},
    {"playguide.bmd", "Data\\Local\\PlayGuide.bmd", 0x009d7096, MU_DATA_COUNTED, 260, 0, 0xe2f1, 0, 0, CHK|NZ},
    {"evolutionmonsterbox.bmd", "Data\\Local\\EvolutionMonsterBox.bmd", 0x00a9d8d2, MU_DATA_COUNT_BYTES, 1, 0, 0xc4a2, 0, 0, CHK|NZ},
    {"murummyoption.bmd", "Data\\Local\\MuRummyOption.bmd", 0x00bcc159, MU_DATA_COUNTED, 8, 0, 0xe2f1, 0, 0, CHK},
    {"murummycard.bmd", "Data\\Local\\MuRummyCard.bmd", 0x00bcc2a5, MU_DATA_COUNTED, 60, 0, 0xe2f1, 0, 0, CHK},
    {"murummyslot.bmd", "Data\\Local\\MuRummySlot.bmd", 0x00bcc44d, MU_DATA_COUNTED, 11, 0, 0xe2f1, 0, 0, CHK},
    {"monsterskill.bmd", "Data\\Local\\MonsterSkill.bmd", 0x01692f3c, MU_DATA_COUNTED, 48, 0, 0, 0, 0, 0},
    {"masterskilltreedata.bmd", "Data\\Local\\MasterSkillTreeData.bmd", 0x00baf58c, MU_DATA_FIXED, 24, 2048, 0x2bc1, 0, 0, CHK},
    {"masterskilltooltip.bmd", "Data\\Local\\MasterSkillTooltip.bmd", 0x00baf73e, MU_DATA_FIXED, 808, 2048, 0x2bc1, 0, 0, CHK},
    {"npcdialogue.bmd", "Data\\Local\\NPCDialogue.bmd", 0x00fdcbb4, MU_DATA_UNTIL_EOF, 88, 0, 0, 0, 0, 0},
    {"questprogress.bmd", "Data\\Local\\QuestProgress.bmd", 0x00fdccc1, MU_DATA_UNTIL_EOF, 41, 0, 0, 0, 0, 0},
    {"questwords.bmd", "Data\\Local\\QuestWords.bmd", 0x00fdcdc8, MU_DATA_WORDS, 0, 0, 0, 0, 0, 0},
    {"skilltooltiptext.bmd", "Data\\Local\\SkillTooltipText.bmd", 0x0117d758, MU_DATA_COUNTED, 808, 0, 0xe2f1, 0, 0, CHK|NZ},
    {"itemsettype.bmd", "Data\\Local\\ItemSetType.bmd", 0x009ddde0, MU_DATA_FIXED, 10, 11264, 0xe5f1, 0, 0, CHK},
    {"itemsetoption.bmd", "Data\\Local\\ItemSetOption.bmd", 0x009ddf86, MU_DATA_FIXED, 468, 1000, 0xa2f1, 0, 0, CHK},
    {"itemsetoptiontext.bmd", "Data\\Local\\ItemSetOptionText.bmd", 0x009df9ca, MU_DATA_COUNTED, 102, 0, 0xe2f1, 0, 0, CHK|NZ},
    {"infotooltip.bmd", "Data\\Local\\InfoTooltip.bmd", 0x00ab3411, MU_DATA_COUNTED, 42, 0, 0xa4c6, 0, 0, CHK|NZ},
    {"infotooltiptext.bmd", "Data\\Local\\InfoTooltipText.bmd", 0x00ab35fc, MU_DATA_COUNTED, 258, 0, 0xa4c6, 0, 0, CHK|NZ},
    {"helpdata.bmd", "Data\\Local\\helpdata.bmd", 0x00b8968b, MU_DATA_FIXED, 136, 512, 0xc4f7, 0, 0, CHK},
    {"ruudshopviewinfo.bmd", "Data\\Local\\RuudShopViewInfo.bmd", 0x00c0f48a, MU_DATA_COUNTED, 240, 0, 0xe2f1, 0, 0, CHK|NZ},
    {"mapcharacters.bmd", "Data\\Local\\MapCharacters.bmd", 0x00cdd16b, MU_DATA_MAP_LISTS, 4, 0, 0, 0, 0, 0},
    {"mix.bmd", "Data\\Local\\Mix.bmd", 0x00d0aea2, MU_DATA_MIX, 928, 3000, 0, 0, 0, 0},
    {"petdata.bmd", "Data\\Local\\petdata.bmd", 0x00eb0a7d, MU_DATA_FIXED, 48, 32, 0x3bb2, 0, 0, CHK},
    {"pet.bmd", "Data\\Local\\pet.bmd", 0x012a9c1b, MU_DATA_PET, 0, 0, 0x7f1d, 0, 0, CHK},
    {"itemtooltip.bmd", "Data\\Local\\itemtooltip.bmd", 0x00f0ada4, MU_DATA_FIXED, 136, 11264, 0xe2f1, 0, 0, CHK|MU_DATA_STOP_BYTE4},
    {"itemtooltiptext.bmd", "Data\\Local\\itemtooltiptext.bmd", 0x00f0afe2, MU_DATA_COUNTED, 260, 0, 0xe2f1, MU_DATA_CODEC_XOR3_KEY, 0xe2f1, CHK},
    {"jewelofharmonyoption.bmd", "Data\\Local\\JewelOfHarmonyOption.bmd", 0x011dfd13, MU_DATA_FIXED_PLAIN, 135000, 1, 0, 0, 0, 0},
    {"serverlist.bmd", "Data\\Local\\ServerList.bmd", 0x01072501, MU_DATA_SERVER_LIST, 0, 0, 0, MU_DATA_CODEC_XOR3_LOCAL, 0, 0},
    {"lang.mpr", "./Data/Lang.mpr", 0x00ffaeb8, MU_DATA_PACKAGE, 0, 0, 0x12dc, MU_DATA_CODEC_XOR3_KEY, 0x12dc, CHK},
};
#undef CHK
#undef NZ

const mu_data_spec *mu_data_specs(size_t *count) {
    if (count) *count = sizeof SPECS / sizeof SPECS[0];
    return SPECS;
}

static int same_name(const char *a, const char *b) {
    for (; *a && *b; ++a, ++b)
        if (tolower((unsigned char)*a) != tolower((unsigned char)*b)) return 0;
    return *a == *b;
}

const mu_data_spec *mu_data_find(const char *file) {
    if (!file) return NULL;
    for (size_t i = 0; i < sizeof SPECS / sizeof SPECS[0]; ++i)
        if (same_name(SPECS[i].file, file)) return &SPECS[i];
    return NULL;
}

const char *mu_data_status_name(mu_data_status status) {
    switch (status) {
    case MU_DATA_OK: return "ok";
    case MU_DATA_TRUNCATED: return "truncated";
    case MU_DATA_BAD_CHECKSUM: return "bad-checksum";
    case MU_DATA_ZERO_COUNT: return "zero-count";
    case MU_DATA_BAD_HEADER: return "bad-header";
    case MU_DATA_BAD_ARGUMENT: return "bad-argument";
    }
    return "unknown";
}

const char *mu_data_kind_name(mu_data_kind kind) {
    switch (kind) {
    case MU_DATA_COUNTED: return "counted";
    case MU_DATA_FIXED: return "fixed";
    case MU_DATA_UNTIL_EOF: return "until-eof";
    case MU_DATA_FIXED_PLAIN: return "fixed-plain";
    case MU_DATA_COUNT_BYTES: return "count-bytes";
    case MU_DATA_FORMULA: return "formula";
    case MU_DATA_MAP_LISTS: return "map-lists";
    case MU_DATA_WORDS: return "words";
    case MU_DATA_SERVER_LIST: return "server-list";
    case MU_DATA_PET: return "pet";
    case MU_DATA_MIX: return "mix";
    case MU_DATA_TWO_COUNTS: return "two-counts";
    case MU_DATA_PACKAGE: return "package";
    }
    return "unknown";
}

typedef struct {
    const mu_data_spec *spec;
    uint8_t *image;
    size_t size;
    mu_data_unit_fn callback;
    void *user;
    mu_data_result *result;
} decoder;

static uint32_t le32(const uint8_t *p) {
    return (uint32_t)p[0] | (uint32_t)p[1] << 8 | (uint32_t)p[2] << 16 | (uint32_t)p[3] << 24;
}

static int fits(const decoder *d, size_t offset, uint64_t length) {
    return offset <= d->size && length <= (uint64_t)(d->size - offset);
}

/* One decoder call. Returns 0 when the unit does not fit the image. */
static int unit(decoder *d, size_t offset, uint32_t length) {
    if (!fits(d, offset, length)) return 0;
    uint8_t *p = d->image + offset;
    switch (d->spec->codec) {
    case MU_DATA_CODEC_XOR3_LOCAL:
        mu_data_xor3_local(p, (int32_t)length);
        break;
    case MU_DATA_CODEC_XOR3_KEY:
        mu_data_xor3_key(p, length, mu_data_key3, d->spec->codec_key);
        break;
    default:
        mu_data_xor3(p, (int32_t)length, mu_data_key3);
        break;
    }
    d->result->units++;
    if (offset + length > d->result->consumed) d->result->consumed = offset + length;
    if (d->callback) d->callback(d->user, offset, length, d->spec->codec);
    return 1;
}

/* Checksum over [offset, offset+length) compared with the u32 that follows. */
static mu_data_status checksum(decoder *d, size_t offset, uint64_t length) {
    if (!fits(d, offset, length + 4) || length > 0xffffffffu) return MU_DATA_TRUNCATED;
    mu_data_result *r = d->result;
    r->checksum_offset = (uint32_t)offset;
    r->checksum_length = (uint32_t)length;
    r->checksum_stored = le32(d->image + offset + length);
    r->checksum_computed = mu_data_checksum(d->image + offset, (uint32_t)length, d->spec->checksum_key);
    if (offset + length + 4 > r->consumed) r->consumed = (size_t)(offset + length + 4);
    return r->checksum_stored == r->checksum_computed ? MU_DATA_OK : MU_DATA_BAD_CHECKSUM;
}

static mu_data_status records(decoder *d, size_t offset, uint32_t count, uint32_t size) {
    d->result->records_offset = offset;
    for (uint32_t i = 0; i < count; ++i) {
        size_t at = offset + (size_t)i * size;
        if (!unit(d, at, size)) return MU_DATA_TRUNCATED;
        d->result->records++;
        if ((d->spec->flags & MU_DATA_STOP_BYTE4) && size > 4 && d->image[at + 4] == 0) break;
    }
    return MU_DATA_OK;
}

static mu_data_status counted(decoder *d) {
    const mu_data_spec *s = d->spec;
    if (d->size < 4) return MU_DATA_TRUNCATED;
    uint32_t count = le32(d->image);
    if (count == 0 && (s->flags & MU_DATA_COUNT_NONZERO)) return MU_DATA_ZERO_COUNT;
    if (!(s->flags & MU_DATA_HAS_CHECKSUM)) {
        /* MonsterSkill: signed count, one fread+decode per record. */
        int32_t n = (int32_t)count;
        d->result->consumed = 4;
        return records(d, 4, n > 0 ? (uint32_t)n : 0, s->record_size);
    }
    uint64_t length = (uint64_t)count * s->record_size;
    mu_data_status st = checksum(d, 4, length);
    if (st != MU_DATA_OK) return st;
    return records(d, 4, count, s->record_size);
}

static mu_data_status fixed(decoder *d) {
    const mu_data_spec *s = d->spec;
    uint64_t length = (uint64_t)s->record_count * s->record_size;
    if (s->flags & MU_DATA_HAS_CHECKSUM) {
        mu_data_status st = checksum(d, 0, length);
        if (st != MU_DATA_OK) return st;
    }
    return records(d, 0, s->record_count, s->record_size);
}

static mu_data_status until_eof(decoder *d) {
    uint32_t r = d->spec->record_size;
    uint32_t n = (uint32_t)(d->size / r);
    return records(d, 0, n, r);
}

static mu_data_status count_bytes(decoder *d) {
    if (d->size < 4) return MU_DATA_TRUNCATED;
    uint32_t n = le32(d->image);
    if (n == 0) return MU_DATA_ZERO_COUNT;
    mu_data_status st = checksum(d, 4, n);
    if (st != MU_DATA_OK) return st;
    d->result->records_offset = 4;
    if (!unit(d, 4, n)) return MU_DATA_TRUNCATED;
    d->result->records = n;
    return MU_DATA_OK;
}

static mu_data_status formula(decoder *d) {
    if (d->size < 8) return MU_DATA_TRUNCATED;
    uint32_t total = le32(d->image), groups = le32(d->image + 4);
    if (total == 0 || groups == 0) return MU_DATA_ZERO_COUNT;
    uint32_t length = total * d->spec->record_size + groups * 8; /* client 32-bit arithmetic */
    mu_data_status st = checksum(d, 8, length);
    if (st != MU_DATA_OK) return st;
    size_t at = 8;
    d->result->records_offset = 8;
    for (uint32_t g = 0; g < groups; ++g) {
        if (!unit(d, at, 4) || !unit(d, at + 4, 4)) return MU_DATA_TRUNCATED;
        uint32_t n = le32(d->image + at + 4);
        at += 8;
        for (uint32_t i = 0; i < n; ++i, at += d->spec->record_size) {
            if (!unit(d, at, d->spec->record_size)) return MU_DATA_TRUNCATED;
            d->result->records++;
        }
    }
    return MU_DATA_OK;
}

static mu_data_status map_lists(decoder *d) {
    size_t at = 0;
    while (fits(d, at, 8)) {
        unit(d, at, 4);
        unit(d, at + 4, 4);
        int32_t n = (int32_t)le32(d->image + at + 4);
        at += 8;
        d->result->records++;
        for (int32_t i = 0; i < n; ++i, at += 4)
            if (!unit(d, at, 4)) return MU_DATA_TRUNCATED;
    }
    return at == d->size ? MU_DATA_OK : MU_DATA_TRUNCATED;
}

static mu_data_status words(decoder *d) {
    size_t at = 0;
    while (fits(d, at, 6)) {
        unit(d, at, 6);
        uint16_t length = (uint16_t)(d->image[at + 4] | d->image[at + 5] << 8);
        at += 6;
        if (!unit(d, at, length)) return MU_DATA_TRUNCATED;
        at += length;
        d->result->records++;
    }
    return at == d->size ? MU_DATA_OK : MU_DATA_TRUNCATED;
}

static mu_data_status server_list(decoder *d) {
    size_t at = 0;
    while (fits(d, at, 39)) {
        unit(d, at, 39);
        int16_t length = (int16_t)(d->image[at + 37] | d->image[at + 38] << 8);
        at += 39;
        if (length < 0) return MU_DATA_BAD_HEADER; /* client fread size would be negative */
        if (!unit(d, at, (uint32_t)length)) return MU_DATA_TRUNCATED;
        at += (size_t)length;
        d->result->records++;
    }
    return at == d->size ? MU_DATA_OK : MU_DATA_TRUNCATED;
}

static mu_data_status pet(decoder *d) {
    if (d->size < 12) return MU_DATA_TRUNCATED;
    uint32_t n = le32(d->image + 4), count = le32(d->image + 8);
    uint32_t size = n * 8 + 16; /* client 32-bit arithmetic */
    mu_data_status st = checksum(d, 12, (uint32_t)(size * count));
    if (st != MU_DATA_OK) return st;
    return records(d, 12, count, size);
}

static mu_data_status mix(decoder *d) {
    if (!unit(d, 0, 88)) return MU_DATA_TRUNCATED;
    size_t at = 88;
    d->result->records_offset = 88;
    for (int g = 0; g < 22; ++g) {
        int32_t n = (int32_t)le32(d->image + 4 * (size_t)g);
        if (at > d->size || n > (int32_t)d->spec->record_count) return MU_DATA_BAD_HEADER;
        for (int32_t i = 0; i < n; ++i, at += d->spec->record_size) {
            if (!unit(d, at, d->spec->record_size)) return MU_DATA_TRUNCATED;
            d->result->records++;
        }
    }
    return MU_DATA_OK;
}

static mu_data_status two_counts(decoder *d) {
    if (d->size < 8) return MU_DATA_TRUNCATED;
    uint32_t a = le32(d->image), b = le32(d->image + 4);
    if (a == 0 && b == 0) return MU_DATA_ZERO_COUNT;
    uint32_t count = a + b;
    mu_data_status st = checksum(d, 8, (uint64_t)count * d->spec->record_size);
    if (st != MU_DATA_OK) return st;
    return records(d, 8, count, d->spec->record_size);
}

static mu_data_status package(decoder *d) {
    if (d->size < 4) return MU_DATA_TRUNCATED;
    uint32_t length = (uint32_t)(d->size - 4);
    mu_data_status st = checksum(d, 0, length);
    if (st != MU_DATA_OK) return st;
    d->result->records_offset = 0;
    unit(d, 0, length);
    return MU_DATA_OK;
}

mu_data_status mu_data_decode(const mu_data_spec *spec, uint8_t *image, size_t size,
                              mu_data_unit_fn callback, void *user, mu_data_result *result) {
    mu_data_result local;
    if (!result) result = &local;
    memset(result, 0, sizeof *result);
    if (!spec || (!image && size)) return result->status = MU_DATA_BAD_ARGUMENT;
    if (size > 0x7fffffffu) return result->status = MU_DATA_BAD_ARGUMENT;
    if ((spec->kind == MU_DATA_COUNTED || spec->kind == MU_DATA_FIXED || spec->kind == MU_DATA_UNTIL_EOF ||
         spec->kind == MU_DATA_FIXED_PLAIN || spec->kind == MU_DATA_FORMULA || spec->kind == MU_DATA_MIX ||
         spec->kind == MU_DATA_TWO_COUNTS) && spec->record_size == 0)
        return result->status = MU_DATA_BAD_ARGUMENT;
    decoder d = {spec, image, size, callback, user, result};
    mu_data_status st;
    switch (spec->kind) {
    case MU_DATA_COUNTED: st = counted(&d); break;
    case MU_DATA_FIXED: st = fixed(&d); break;
    case MU_DATA_UNTIL_EOF: st = until_eof(&d); break;
    case MU_DATA_FIXED_PLAIN: st = records(&d, 0, spec->record_count, spec->record_size); break;
    case MU_DATA_COUNT_BYTES: st = count_bytes(&d); break;
    case MU_DATA_FORMULA: st = formula(&d); break;
    case MU_DATA_MAP_LISTS: st = map_lists(&d); break;
    case MU_DATA_WORDS: st = words(&d); break;
    case MU_DATA_SERVER_LIST: st = server_list(&d); break;
    case MU_DATA_PET: st = pet(&d); break;
    case MU_DATA_MIX: st = mix(&d); break;
    case MU_DATA_TWO_COUNTS: st = two_counts(&d); break;
    case MU_DATA_PACKAGE: st = package(&d); break;
    default: st = MU_DATA_BAD_ARGUMENT; break;
    }
    return result->status = st;
}
