/* RENDER-ITEMS-TEX-001: installed-data survey of item body textures.
 *
 * usage: item-textures-host GAME_ROOT TYPES_TSV [--legacy] [--list] [--ids] [--wearer | --class BYTE]
 *
 * For every type of the survey TSV (docs/research/item-body-types.tsv) the model is found as the inventory renderer
 * finds it (mu_hud_item_model_path; class parts from Data/Player), its textures are loaded by the production item
 * loader (mu_item_textures_load; --legacy: the model folder only, as before this lane), and the item is drawn by
 * mu_renderchar_draw_item through mu_scene over 48 states (levels 0/7/9/11/13/15, excellent 0/1, ancient 0/5, lit
 * 0/1). A pass is white when it draws with GL_TEXTURE_2D on and texture name 0. Output: one line per type with
 * white passes (--list: every type), then a JSON summary. --ids prints only the override bitmap indices the
 * body executor names over all types (comma-separated, the input of validate_item_textures.py --emit-table).
 * RENDER-ITEMS-TEX-002: by default the models keep +0xa4 = 0 (no character has worn them); --class BYTE wears every
 * type with that class byte, --wearer with an authored wearer per type: the first class slot c whose require_class
 * stage s is set, class byte c | (s >= 2 ? 1 << (s - 2) : 0) << 4 (tier s, mu_character_class_tier). */
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <sys/stat.h>

#include "../core/mu_hud.h"
#include "../core/mu_hud_tip.h"
#include "../core/mu_item_textures.h"
#include "../core/mu_renderchar.h"
#include "../../reconstructed/model-codec/character.h"

/* Authored wearer of an item (survey only): the first class its record admits, at that class's minimum stage. */
static int wearer_class(const mu_item *record, uint8_t *class_byte)
{
    for (int c = 0; c < MU_ITEM_CLASS_SLOTS; ++c) {
        const int stage = record->attributes.require_class[c];
        if (stage > 0 && stage <= 5) {
            *class_byte = (uint8_t)(c | (stage >= 2 ? (1 << (stage - 2)) << 4 : 0));
            return 1;
        }
    }
    return 0;
}

typedef struct counter {
    long passes, white;
} counter;

static void prepare(void *context, const mu_meshdraw_state *state, int32_t texture)
{
    counter *c = context;
    c->passes++;
    if (state->texture && texture < 0)
        c->white++;
}
static void texcoord(void *c, float s, float t) { (void)c; (void)s; (void)t; }
static void color3(void *c, const float rgb[3]) { (void)c; (void)rgb; }
static void color4(void *c, float r, float g, float b, float a) { (void)c; (void)r; (void)g; (void)b; (void)a; }
static void vertex(void *c, const float xyz[3]) { (void)c; (void)xyz; }

static int class_part_path(const char *root, int32_t type, char *out, size_t size)
{
    static const char *parts[] = {"Helm", "Armor", "Pant", "Glove", "Boot"};
    if (type < (int32_t)MU_CHARACTER_PART_BASE || type >= (int32_t)(MU_CHARACTER_PART_BASE + 5 * MU_CHARACTER_PART_STRIDE))
        return 0;
    const int32_t k = type - (int32_t)MU_CHARACTER_PART_BASE, stride = (int32_t)MU_CHARACTER_PART_STRIDE;
    snprintf(out, size, "%s/Data/Player/%sClass%02d.bmd", root, parts[k / stride], (int)(k % stride) + 1);
    struct stat st;
    return stat(out, &st) == 0;
}

int main(int argc, char **argv)
{
    if (argc < 3) {
        fprintf(stderr, "usage: %s GAME_ROOT TYPES_TSV [--legacy] [--list]\n", argv[0]);
        return 2;
    }
    const char *root = argv[1];
    int legacy = 0, list = 0, ids = 0, wearer = 0, fixed_class = -1;
    for (int i = 3; i < argc; ++i) {
        wearer |= !strcmp(argv[i], "--wearer");
        if (!strcmp(argv[i], "--class") && i + 1 < argc)
            fixed_class = (int)strtol(argv[++i], NULL, 0);
        ids |= !strcmp(argv[i], "--ids");
        legacy |= !strcmp(argv[i], "--legacy");
        list |= !strcmp(argv[i], "--list");
    }
    FILE *tsv = fopen(argv[2], "r");
    if (!tsv)
        return 2;
    mu_hud_tip_tables t;
    mu_hud_tip_tables_load(root, &t);
    char line[1024];
    if (ids) {
        int32_t all[1024], n_all = 0;
        while (fgets(line, sizeof line, tsv)) {
            unsigned type;
            int32_t want[64];
            if (sscanf(line, "0x%x", &type) != 1)
                continue;
            const int32_t n = mu_item_textures_overrides((int32_t)type, t.have_items ? &t.items : NULL, want, 64);
            for (int32_t i = 0; i < n && i < 64; ++i) {
                int32_t k = 0;
                while (k < n_all && all[k] != want[i])
                    ++k;
                if (k == n_all && n_all < 1024)
                    all[n_all++] = want[i];
            }
        }
        for (int32_t k = 0; k < n_all; ++k)
            printf("%s0x%04x", k ? "," : "", (unsigned)all[k]);
        printf("\n");
        fclose(tsv);
        mu_hud_tip_tables_free(&t);
        return 0;
    }
    long types = 0, implemented = 0, no_model = 0, white_types = 0, white_implemented = 0, missing_meshes = 0;
    long missing_bitmaps = 0, passes = 0, white = 0, specials = 0, special_meshes = 0, typed_meshes = 0, name_map = 0;
    long wearers = 0;
    while (fgets(line, sizeof line, tsv)) {
        char vis[64], shape[64];
        unsigned type;
        int body;
        if (sscanf(line, "0x%x\t%63[^\t]\t%63s\t%d", &type, vis, shape, &body) != 4)
            continue;
        types++;
        implemented += body == 1;
        char path[2048];
        if (!mu_hud_item_model_path(t.have_items ? &t.items : NULL, root, (int32_t)type, path, sizeof path) &&
            !class_part_path(root, (int32_t)type, path, sizeof path)) {
            no_model++;
            if (list) {
                mu_item r;
                const int has = t.have_items && mu_item_model(&t.items, (int32_t)type, &r) == 1;
                printf("0x%04x\t%s\t%d\tno-model\t%s%s\n", type, vis, body, has ? r.folder : "(no record)",
                       has ? r.file : "");
            }
            continue;
        }
        mu_bmd bmd;
        char error[256];
        if (mu_bmd_load_file(path, &bmd, error, sizeof error) != MU_BMD_OK) {
            no_model++;
            continue;
        }
        mu_model_params params;
        mu_model_default_params(&params);
        mu_model model;
        if (mu_model_init(&model, &bmd, &params, error, sizeof error) != MU_MODEL_OK) {
            mu_bmd_free(&bmd);
            no_model++;
            continue;
        }
        mu_model_set_state(&model, 0, 0.0f, 0.0f, 0);
        mu_model_update(&model);
        mu_textures textures;
        mu_item_textures_stats ts = {0};
        if (legacy) {
            char directory[2048];
            mu_path_directory(path, directory, sizeof directory);
            mu_textures_load(&textures, &bmd, directory);
            ts.missing_meshes = textures.missing;
        } else {
            mu_item_textures_load(&textures, &bmd, t.have_items ? &t.items : NULL, root, (int32_t)type, path, &ts);
        }
        if (getenv("MU_ITEM_TEXTURES_MESHES"))   /* local survey aid: each mesh slot's pixels and upload */
            for (int k = 0; k < bmd.mesh_count && k < textures.model_count; ++k) {
                uint32_t h = 2166136261u;
                const mu_image *im = textures.slots[k];
                if (im)
                    for (size_t b = 0; b < (size_t)im->width * (size_t)im->height * 4; ++b)
                        h = (h ^ im->rgba[b]) * 16777619u;
                fprintf(stderr, "M\t0x%04x\t%d\t%s\t%08x\t%x\t%x\n", type, k, bmd.meshes[k].texture, im ? h : 0,
                        textures.filter[k], textures.wrap[k]);
            }
        if (getenv("MU_ITEM_TEXTURES_NAMES"))   /* local survey aid: every mesh name */
            for (int k = 0; k < bmd.mesh_count; ++k)
                fprintf(stderr, "0x%04x\t%s\n", type, bmd.meshes[k].texture);
        mu_renderchar_glow glow = {0};
        glow.type = (int32_t)type;
        mu_item record;
        uint8_t class_byte = 0;
        int worn = 0;
        if (t.have_items && (int32_t)type >= 0xae6 && mu_item_find(&t.items, type - 0xae6, &record) == 0) {
            glow.has_record = 1;
            glow.kind_a = record.attributes.kind_a;
            glow.kind_b = record.attributes.kind_b;
            glow.item_kind = record.attributes.type;
            worn = wearer && wearer_class(&record, &class_byte);
        }
        if (fixed_class >= 0) {
            class_byte = (uint8_t)fixed_class;
            worn = 1;
        }
        if (worn && !legacy) {
            mu_item_textures_wear(&textures, root, class_byte);
            wearers++;
        }
        counter c = {0, 0};
        mu_render_backend backend = {&c, prepare, NULL, NULL, {&c, texcoord, color3, color4, vertex}, NULL};
        mu_draw_options draw;
        mu_draw_default_options(&draw);
        draw.textures = &textures;
        mu_renderchar_env env;
        mu_renderchar_default_env(&env);
        static const int levels[] = {0, 7, 9, 11, 13, 15};
        const float light[3] = {1.0f, 1.0f, 1.0f};
        mu_renderchar_stats rs = {0, 0};
        for (int lit = 0; lit < 2; ++lit) {
            model.params.lighting = (uint8_t)lit;
            for (int l = 0; l < 6; ++l)
                for (int x = 0; x < 2; ++x)
                    for (int a = 0; a < 2; ++a) {
                        glow.level = levels[l];
                        glow.option1 = x;
                        glow.ext = a ? 5 : 0;
                        env.time = 1000.0f * (float)(l + 1);
                        mu_draw_stats ds = {0, 0, 0, 0};
                        mu_renderchar_draw_item(&model, &glow, &env, light, 1.0f, &draw, &backend, &ds, &rs);
                    }
        }
        passes += c.passes;
        white += c.white;
        specials += rs.special;
        missing_meshes += ts.missing_meshes;
        missing_bitmaps += ts.missing_bitmaps;
        special_meshes += ts.special_meshes;
        typed_meshes += ts.typed_meshes;
        name_map += ts.name_map;
        if (c.white) {
            white_types++;
            white_implemented += body == 1;
        }
        if (c.white || list) {
            printf("0x%04x\t%s\t%d\twhite %ld/%ld\tmeshes %d\tmissing_meshes %d", type, vis, body, c.white, c.passes,
                   bmd.mesh_count, ts.missing_meshes);
            for (int k = 0; k < bmd.mesh_count && k < textures.model_count; ++k)
                if (!textures.slots[k])
                    printf(" [%s%s]", bmd.meshes[k].texture,
                           textures.client_index && textures.client_index[k] ? " special" : "");
            if (worn)
                printf("\twearer 0x%02x", class_byte);
            printf("\tbitmaps %d missing %d", ts.bitmaps, ts.missing_bitmaps);
            for (int k = 0; k < ts.missing_bitmaps && k < MU_ITEM_TEXTURES_REPORT; ++k)
                printf(" 0x%04x", (unsigned)ts.missing_index[k]);
            printf("\n");
        }
        mu_textures_free(&textures);
        mu_model_free(&model);
        mu_bmd_free(&bmd);
    }
    fclose(tsv);
    printf("{\"legacy\": %d, \"types\": %ld, \"implemented\": %ld, \"no_model\": %ld, \"passes\": %ld, "
           "\"white_passes\": %ld, \"white_types\": %ld, \"white_implemented\": %ld, \"missing_meshes\": %ld, "
           "\"missing_bitmaps\": %ld, \"special_draws\": %ld, \"special_meshes\": %ld, \"typed_meshes\": %ld, "
           "\"name_map_meshes\": %ld, \"worn\": %ld}\n",
           legacy, types, implemented, no_model, passes, white, white_types, white_implemented, missing_meshes,
           missing_bitmaps, specials, special_meshes, typed_meshes, name_map, wearers);
    mu_hud_tip_tables_free(&t);
    return 0;
}
