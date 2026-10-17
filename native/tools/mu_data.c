/* mu-data: decode and dump the client's data tables locally (NATIVE-DATA-001).
 *
 *   mu-data list [GAME_ROOT]             catalog, and per-file decode status when GAME_ROOT is given
 *   mu-data dump FILE [--out PATH]       decoded records as JSON, with named fields where a layout exists
 *   mu-data item ITEM_BMD CODE           one item's named attributes and derived values
 *   mu-data layouts                      the record layout catalog with per-field evidence
 *   mu-data item-models FILE [--json]    item code -> model index, folder, file, name
 *   mu-data model ITEM_BMD INDEX         what the client's model getter 0x00eaa8cf does for INDEX
 *   mu-data decode FILE --out PATH       decoded file image (raw bytes)
 *   mu-data mpr FILE                     Lang.mpr package directory (entries stay encrypted)
 *
 * Named fields: NATIVE-DATA-002 (reconstructed/data/table_layouts.c).
 * Output is written locally only; decoded game text and tables are never part
 * of the repository.
 */
#define _POSIX_C_SOURCE 200809L
#include "../core/mu_data.h"

#include <dirent.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <strings.h>

static void usage(void) {
    fputs("usage:\n"
          "  mu-data list [GAME_ROOT]\n"
          "  mu-data dump FILE [--out PATH]\n"
          "  mu-data item ITEM_BMD CODE\n"
          "  mu-data layouts\n"
          "  mu-data item-models FILE [--json] [--out PATH]\n"
          "  mu-data model ITEM_BMD INDEX\n"
          "  mu-data decode FILE --out PATH\n"
          "  mu-data mpr FILE [--out PATH]\n", stderr);
}

/* JSON string: bytes >= 0x80 are written as \u00XX (Latin-1 code points; the
 * client's code page is not converted). */
static void json_string(FILE *out, const uint8_t *s, size_t n) {
    fputc('"', out);
    for (size_t i = 0; i < n && s[i]; ++i) {
        uint8_t c = s[i];
        if (c == '"' || c == '\\') fprintf(out, "\\%c", c);
        else if (c < 0x20 || c >= 0x7f) fprintf(out, "\\u%04x", c);
        else fputc(c, out);
    }
    fputc('"', out);
}

static void json_hex(FILE *out, const uint8_t *p, size_t n) {
    fputc('"', out);
    for (size_t i = 0; i < n; ++i) fprintf(out, "%02x", p[i]);
    fputc('"', out);
}

static uint32_t le(const uint8_t *p, unsigned width) {
    uint32_t v = 0;
    for (unsigned i = 0; i < width; ++i) v |= (uint32_t)p[i] << (8 * i);
    return v;
}

/* printable runs of at least four bytes, as a quick text view of a record */
static void json_strings(FILE *out, const uint8_t *p, size_t n) {
    fputc('[', out);
    int first = 1;
    for (size_t i = 0; i < n;) {
        size_t j = i;
        while (j < n && p[j] >= 0x20 && p[j] != 0x7f) ++j;
        if (j - i >= 4 && (j == n || p[j] == 0)) {
            if (!first) fputc(',', out);
            json_string(out, p + i, j - i);
            first = 0;
        }
        i = j + 1;
    }
    fputc(']', out);
}

static void json_header(FILE *out, const mu_data_table *t) {
    const mu_data_spec *s = t->spec;
    const mu_data_result *r = &t->result;
    fprintf(out, "{\"file\":\"%s\",\"loader\":\"0x%08x\",\"kind\":\"%s\",\"status\":\"%s\",\"bytes\":%zu,", t->name,
            s->loader, mu_data_kind_name(s->kind), mu_data_status_name(r->status), t->size);
    if (s->flags & MU_DATA_HAS_CHECKSUM)
        fprintf(out, "\"checksum\":{\"key\":\"0x%04x\",\"offset\":%u,\"length\":%u,\"stored\":\"0x%08x\","
                     "\"computed\":\"0x%08x\"},",
                s->checksum_key & 0xffff, r->checksum_offset, r->checksum_length, r->checksum_stored,
                r->checksum_computed);
    fprintf(out, "\"units\":%u,\"records\":%u,\"record_size\":%u,", r->units, r->records, s->record_size);
}

static void json_field(FILE *out, const mu_record_field *f, const uint8_t *record) {
    if (f->type == MU_FIELD_TEXT) {
        json_string(out, record + f->offset, f->count);
        return;
    }
    if (f->type == MU_FIELD_BYTES) {
        json_hex(out, record + f->offset, f->count);
        return;
    }
    if (f->count > 1) fputc('[', out);
    for (unsigned i = 0; i < (f->count ? f->count : 1u); ++i) {
        if (i) fputc(',', out);
        if (f->type == MU_FIELD_F32) fprintf(out, "%.9g", (double)mu_field_float(f, record, i));
        else fprintf(out, "%lld", (long long)mu_field_integer(f, record, i));
    }
    if (f->count > 1) fputc(']', out);
}

/* "fields": named values from offset `from`; "unnamed": spans not covered by
 * any field that hold a nonzero byte, as hex keyed by offset. */
static void json_record(FILE *out, const mu_record_layout *layout, const uint8_t *record, unsigned from,
                        const char *fields_key) {
    fprintf(out, "\"%s\":{", fields_key);
    int first = 1;
    for (uint32_t i = 0; i < layout->field_count; ++i) {
        const mu_record_field *f = &layout->fields[i];
        if (f->offset < from) continue;
        fprintf(out, "%s\"%s\":", first ? "" : ",", f->name);
        json_field(out, f, record);
        first = 0;
    }
    fputs("},\"unnamed\":{", out);
    first = 1;
    unsigned at = from;
    for (uint32_t i = 0; i <= layout->field_count; ++i) {
        unsigned next = i < layout->field_count ? layout->fields[i].offset : layout->record_size;
        if (i < layout->field_count && next < from) continue;
        if (next > at) {
            int nonzero = 0;
            for (unsigned k = at; k < next; ++k) nonzero |= record[k];
            if (nonzero) {
                fprintf(out, "%s\"0x%03x\":", first ? "" : ",", at);
                json_hex(out, record + at, next - at);
                first = 0;
            }
        }
        if (i < layout->field_count) {
            unsigned end = next + mu_field_span(&layout->fields[i]);
            if (end > at) at = end;
        }
    }
    fputc('}', out);
}

static void dump_item(FILE *out, const mu_item *item) {
    fprintf(out, "{\"code\":%u,\"section\":%u,\"index\":%u,\"model_index\":%u,\"folder\":", item->code, item->section,
            item->index, item->code + MU_ITEM_MODEL_BASE);
    json_string(out, (const uint8_t *)item->folder, 260);
    fputs(",\"file\":", out);
    json_string(out, (const uint8_t *)item->file, 260);
    fputs(",\"name\":", out);
    json_string(out, (const uint8_t *)item->name, 64);
    fputc(',', out);
    json_record(out, mu_record_layout_find("item.bmd"), item->record, 0x250, "attributes");
    fputc('}', out);
}

static void dump_records(FILE *out, const mu_data_table *t) {
    const mu_data_spec *s = t->spec;
    const uint8_t *p = t->bytes;
    size_t n = t->size;
    fputs("\"data\":[", out);
    int first = 1;
#define SEP() do { if (!first) fputc(',', out); first = 0; } while (0)
    switch (s->kind) {
    case MU_DATA_MAP_LISTS:
        for (size_t at = 0; at + 8 <= n;) {
            uint32_t key = le(p + at, 4);
            int32_t count = (int32_t)le(p + at + 4, 4);
            at += 8;
            SEP();
            fprintf(out, "{\"key\":%u,\"values\":[", key);
            for (int32_t i = 0; i < count && at + 4 <= n; ++i, at += 4) fprintf(out, "%s%u", i ? "," : "", le(p + at, 4));
            fputs("]}", out);
        }
        break;
    case MU_DATA_WORDS:
        for (size_t at = 0; at + 6 <= n;) {
            uint32_t id = le(p + at, 4), length = le(p + at + 4, 2);
            at += 6;
            if (at + length > n) break;
            SEP();
            fprintf(out, "{\"id\":%u,\"text\":", id);
            json_string(out, p + at, length);
            fputc('}', out);
            at += length;
        }
        break;
    case MU_DATA_SERVER_LIST:
        for (size_t at = 0; at + 39 <= n;) {
            int16_t length = (int16_t)le(p + at + 37, 2);
            if (length < 0 || at + 39 + (size_t)length > n) break;
            SEP();
            fputs("{\"header\":", out);
            json_hex(out, p + at, 39);
            fputs(",\"header_strings\":", out);
            json_strings(out, p + at, 39);
            fputs(",\"entry\":", out);
            json_hex(out, p + at + 39, (size_t)length);
            fputs(",\"strings\":", out);
            json_strings(out, p + at + 39, (size_t)length);
            fputc('}', out);
            at += 39 + (size_t)length;
        }
        break;
    case MU_DATA_FORMULA: {
        size_t at = 8;
        uint32_t groups = n >= 8 ? le(p + 4, 4) : 0;
        for (uint32_t g = 0; g < groups && at + 8 <= n; ++g) {
            uint32_t id = le(p + at, 4), count = le(p + at + 4, 4);
            at += 8;
            SEP();
            fprintf(out, "{\"group\":%u,\"records\":[", id);
            for (uint32_t i = 0; i < count && at + s->record_size <= n; ++i, at += s->record_size) {
                if (i) fputc(',', out);
                json_strings(out, p + at, s->record_size);
            }
            fputs("]}", out);
        }
        break;
    }
    case MU_DATA_PACKAGE:
        break;
    default: {
        size_t size = s->record_size;
        if (s->kind == MU_DATA_PET && n >= 12) size = le(p + 4, 4) * 8 + 16;
        if (s->kind == MU_DATA_COUNT_BYTES) size = t->result.records;
        size_t at = t->result.records_offset;
        const mu_record_layout *layout = mu_record_layout_find(t->name);
        if (layout && size && layout->record_size && size % layout->record_size == 0) {
            /* named records; fixed units holding several records are split */
            uint32_t index = 0;
            for (uint32_t i = 0; i < t->result.records && at + size <= n; ++i, at += size)
                for (size_t sub = 0; sub < size; sub += layout->record_size) {
                    SEP();
                    fprintf(out, "{\"i\":%u,", index++);
                    json_record(out, layout, p + at + sub, 0, "fields");
                    fputc('}', out);
                }
            break;
        }
        for (uint32_t i = 0; i < t->result.records && size && at + size <= n; ++i, at += size) {
            SEP();
            fprintf(out, "{\"i\":%u,\"hex\":", i);
            json_hex(out, p + at, size);
            fputs(",\"strings\":", out);
            json_strings(out, p + at, size);
            fputc('}', out);
        }
    }
    }
#undef SEP
    fputc(']', out);
}

static FILE *open_out(const char *path) {
    if (!path) return stdout;
    FILE *f = fopen(path, "wb");
    if (!f) perror(path);
    return f;
}

static int load(const char *path, mu_data_table *t) {
    if (mu_data_load(path, NULL, t) != 0) {
        fprintf(stderr, "%s: unreadable or not a known table\n", path);
        return -1;
    }
    return 0;
}

static int cmd_list(const char *root) {
    size_t count;
    const mu_data_spec *specs = mu_data_specs(&count);
    int failures = 0;
    printf("%-28s %-10s %-12s %8s %6s %-6s %s\n", "file", "loader", "kind", "record", "fixed", "key",
           root ? "installed status" : "path");
    for (size_t i = 0; i < count; ++i) {
        const mu_data_spec *s = &specs[i];
        printf("%-28s 0x%08x %-12s %8u %6u 0x%04x ", s->file, s->loader, mu_data_kind_name(s->kind), s->record_size,
               s->record_count, s->checksum_key & 0xffff);
        if (!root) {
            printf("%s\n", s->path);
            continue;
        }
        char folder[4096], path[4200];
        snprintf(folder, sizeof folder, "%s/Data%s", root, strcasecmp(s->file, "lang.mpr") ? "/Local" : "");
        DIR *dir = opendir(folder);
        int found = 0;
        if (dir) {
            struct dirent *e;
            while ((e = readdir(dir))) {
                if (strcasecmp(e->d_name, s->file)) continue;
                snprintf(path, sizeof path, "%s/%s", folder, e->d_name);
                mu_data_table t;
                if (mu_data_load(path, s, &t) == 0) {
                    printf("%s bytes=%zu units=%u records=%u\n", mu_data_status_name(t.result.status), t.size,
                           t.result.units, t.result.records);
                    failures += t.result.status != MU_DATA_OK;
                    mu_data_free(&t);
                    found = 1;
                }
                break;
            }
            closedir(dir);
        }
        if (!found) printf("absent\n");
    }
    return failures ? 1 : 0;
}

static int cmd_dump(const char *path, const char *out_path) {
    mu_data_table t;
    if (load(path, &t)) return 2;
    FILE *out = open_out(out_path);
    if (!out) return 2;
    json_header(out, &t);
    if (t.result.status == MU_DATA_OK && mu_item_count(&t)) {
        fputs("\"items\":[", out);
        for (size_t i = 0; i < mu_item_count(&t); ++i) {
            mu_item item;
            mu_item_get(&t, i, &item);
            if (i) fputs(",\n", out);
            dump_item(out, &item);
        }
        fputc(']', out);
    } else if (t.result.status == MU_DATA_OK && t.spec->kind == MU_DATA_PACKAGE) {
        mu_package_entry entries[4096];
        int total = 0;
        int n = mu_package_list(&t, entries, 4096, &total);
        fputs("\"entries\":[", out);
        for (int i = 0; i < n; ++i) {
            fprintf(out, "%s{\"name\":", i ? ",\n" : "");
            json_string(out, (const uint8_t *)entries[i].name, sizeof entries[i].name);
            fprintf(out, ",\"size\":%u,\"compressed\":%u,\"crc32\":\"0x%08x\",\"method\":%u,\"encrypted\":%s}",
                    entries[i].size, entries[i].compressed_size, entries[i].crc32, entries[i].method,
                    entries[i].flags & 1 ? "true" : "false");
        }
        fprintf(out, "],\"entry_count\":%d", total);
    } else if (t.result.status == MU_DATA_OK) {
        dump_records(out, &t);
    } else {
        fputs("\"data\":null", out);
    }
    fputs("}\n", out);
    if (out != stdout) fclose(out);
    int status = t.result.status == MU_DATA_OK ? 0 : 1;
    mu_data_free(&t);
    return status;
}

static int cmd_item_models(const char *path, int json, const char *out_path) {
    mu_data_table t;
    if (load(path, &t)) return 2;
    if (!mu_item_count(&t)) {
        fprintf(stderr, "%s: not a decodable Item.bmd (%s)\n", path, mu_data_status_name(t.result.status));
        mu_data_free(&t);
        return 1;
    }
    FILE *out = open_out(out_path);
    if (!out) return 2;
    if (json) fprintf(out, "{\"model_base\":%u,\"model_limit\":%u,\"items\":[", MU_ITEM_MODEL_BASE, MU_ITEM_MODEL_LIMIT);
    for (size_t i = 0; i < mu_item_count(&t); ++i) {
        mu_item item;
        mu_item_get(&t, i, &item);
        uint32_t model = item.code + MU_ITEM_MODEL_BASE;
        if (json) {
            fprintf(out, "%s{\"code\":%u,\"section\":%u,\"index\":%u,\"model_index\":%u,\"in_range\":%s,\"folder\":",
                    i ? ",\n" : "", item.code, item.section, item.index, model,
                    model <= MU_ITEM_MODEL_LIMIT ? "true" : "false");
            json_string(out, (const uint8_t *)item.folder, 260);
            fputs(",\"file\":", out);
            json_string(out, (const uint8_t *)item.file, 260);
            fputs(",\"texture_folder\":", out);
            char texture[300];
            snprintf(texture, sizeof texture, "%sTexture\\", item.folder);
            json_string(out, (const uint8_t *)texture, sizeof texture);
            fputs(",\"name\":", out);
            json_string(out, (const uint8_t *)item.name, 64);
            fputc('}', out);
        } else {
            fprintf(out, "%5u (%2u,%3u) model %5u  %s%s  %s\n", item.code, item.section, item.index, model, item.folder,
                    item.file, item.name);
        }
    }
    if (json) fputs("]}\n", out);
    if (out != stdout) fclose(out);
    mu_data_free(&t);
    return 0;
}

static int cmd_item(const char *path, const char *code_text) {
    mu_data_table t;
    if (load(path, &t)) return 2;
    char *end = NULL;
    unsigned long code = strtoul(code_text, &end, 0);
    mu_item item;
    if (!end || *end || code > 0xffffffffUL || mu_item_find(&t, (uint32_t)code, &item) != 0) {
        fprintf(stderr, "%s: no item with code %s\n", path, code_text);
        mu_data_free(&t);
        return 1;
    }
    dump_item(stdout, &item);
    /* derived values (0x00ccc5b0, 0x016bec14, 0x016be1d9) for a plain instance */
    printf("\n{\"max_durability\":{");
    static const char *const states[] = {"plain", "excellent", "ancient", "excellent_ancient"};
    for (int s = 0; s < 4; ++s) {
        printf("%s\"%s\":[", s ? "," : "", states[s]);
        for (int level = 0; level < 16; ++level)
            printf("%s%u", level ? "," : "", mu_item_max_durability_at(&item, level, s & 1, s >> 1));
        putchar(']');
    }
    mu_item_state plain = {(int32_t)item.code, 0, 0, 0, 0, 0};
    printf("},\"store_ban\":%d,\"repair_ban\":%d}\n", mu_item_store_ban(&item.attributes, &plain),
           mu_item_repair_ban(&item.attributes, &plain));
    mu_data_free(&t);
    return 0;
}

static const char *field_type_name(unsigned type) {
    static const char *const names[] = {"?", "u8", "i8", "u16", "i16", "u32", "i32", "f32", "text", "bytes"};
    return type < sizeof names / sizeof names[0] ? names[type] : "?";
}

static int cmd_layouts(void) {
    size_t count;
    const mu_record_layout *layouts = mu_record_layouts(&count);
    printf("{\"layouts\":[");
    for (size_t i = 0; i < count; ++i) {
        const mu_record_layout *l = &layouts[i];
        printf("%s\n{\"file\":\"%s\",\"record_size\":%u,\"fields\":[", i ? "," : "", l->file, l->record_size);
        for (uint32_t k = 0; k < l->field_count; ++k) {
            const mu_record_field *f = &l->fields[k];
            printf("%s{\"name\":\"%s\",\"offset\":%u,\"type\":\"%s\",\"count\":%u,\"stride\":%u,"
                   "\"evidence\":\"%s\"}",
                   k ? "," : "", f->name, f->offset, field_type_name(f->type), f->count, f->stride,
                   mu_field_evidence_name((mu_field_evidence)f->evidence));
        }
        printf("]}");
    }
    printf("]}\n");
    return 0;
}

static int cmd_model(const char *path, const char *index_text) {
    mu_data_table t;
    if (load(path, &t)) return 2;
    char *end = NULL;
    long index = strtol(index_text, &end, 0);
    if (!end || *end || index < -2147483647L - 1 || index > 2147483647L) {
        usage();
        mu_data_free(&t);
        return 2;
    }
    mu_item item;
    int r = mu_item_model(&t, (int32_t)index, &item);
    if (r == 1)
        printf("load %ld %s%s texture-folder %sTexture\\ code %u name %s\n", index, item.folder, item.file, item.folder,
               item.code, item.name);
    else if (r == 0)
        printf("empty %ld\n", index);  /* client inserts an empty model object */
    else
        printf("null %ld\n", index);   /* out of range: client returns NULL */
    mu_data_free(&t);
    return 0;
}

static int cmd_decode(const char *path, const char *out_path) {
    if (!out_path) {
        usage();
        return 2;
    }
    mu_data_table t;
    if (load(path, &t)) return 2;
    FILE *out = open_out(out_path);
    if (!out) return 2;
    fwrite(t.bytes, 1, t.size, out);
    fclose(out);
    fprintf(stderr, "%s: %s, %u units, %u records\n", path, mu_data_status_name(t.result.status), t.result.units,
            t.result.records);
    int status = t.result.status == MU_DATA_OK ? 0 : 1;
    mu_data_free(&t);
    return status;
}

int main(int argc, char **argv) {
    if (argc < 2) {
        usage();
        return 2;
    }
    const char *out = NULL;
    int json = 0;
    const char *positional[4] = {0};
    int npos = 0;
    for (int i = 2; i < argc; ++i) {
        if (!strcmp(argv[i], "--out") && i + 1 < argc) out = argv[++i];
        else if (!strcmp(argv[i], "--json")) json = 1;
        else if (npos < 4) positional[npos++] = argv[i];
    }
    const char *cmd = argv[1];
    if (!strcmp(cmd, "list")) return cmd_list(positional[0]);
    if (!strcmp(cmd, "layouts")) return cmd_layouts();
    if (!positional[0]) {
        usage();
        return 2;
    }
    if (!strcmp(cmd, "dump") || !strcmp(cmd, "mpr")) return cmd_dump(positional[0], out);
    if (!strcmp(cmd, "item-models")) return cmd_item_models(positional[0], json, out);
    if (!strcmp(cmd, "decode")) return cmd_decode(positional[0], out);
    if (!strcmp(cmd, "model") && positional[1]) return cmd_model(positional[0], positional[1]);
    if (!strcmp(cmd, "item") && positional[1]) return cmd_item(positional[0], positional[1]);
    usage();
    return 2;
}
