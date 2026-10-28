#include "../charsel_rt_internal.h"

static char *read_text(const char *path)
{
    FILE *f = fopen(path, "rb");
    if (!f)
        return NULL;
    fseek(f, 0, SEEK_END);
    long n = ftell(f);
    fseek(f, 0, SEEK_SET);
    char *text = n >= 0 ? malloc((size_t)n + 1) : NULL;
    if (text && fread(text, 1, (size_t)n, f) != (size_t)n) {
        free(text);
        text = NULL;
    }
    if (text)
        text[n] = 0;
    fclose(f);
    return text;
}

static int load(mu_charsel_rt *a)
{
    char error[512];
    if (a->options.list) {   /* NATIVE-CHARCREATE-001: the caller's list (mu-client's offline session) */
        a->list = *a->options.list;
    } else if (a->options.list_path) {
        char *text = read_text(a->options.list_path);
        if (!text) {
            fprintf(stderr, "%s: cannot read\n", a->options.list_path);
            return 1;
        }
        int status = mu_charsel_list_parse(text, a->options.root, &a->list, error, sizeof error);
        free(text);
        if (status) {
            fprintf(stderr, "%s: %s\n", a->options.list_path, error);
            return 1;
        }
    } else {
        mu_charsel_list_default(&a->list);
    }
    a->s = calloc(1, sizeof *a->s);
    if (!a->s)
        return 1;
    float markers[MU_CHARSEL_MARKERS][3];
    for (int k = 0; k < MU_CHARSEL_MARKERS; ++k)
        memcpy(markers[k], a->options.marker_given ? a->options.marker : mu_charsel_default_marker1, sizeof markers[k]);
    if (a->options.objects_dir) {
        mu_objects_init(&a->objects, MU_CHARSEL_WORLD);
        if (mu_objects_load_dir(&a->objects, a->options.objects_dir, error, sizeof error) != MU_OBJECTS_FILE_OK) {
            fprintf(stderr, "objects: %s\n", error);
            return 1;
        }
        a->has_objects = 1;
        /* marker k is the object of type 13 + k (CreateObject 0x00daa2b2); the last one of a type wins */
        for (int32_t i = 0; i < a->objects.count && !a->options.marker_given; ++i) {
            int32_t k = a->objects.records[i].type - 13;
            if (k >= 0 && k < MU_CHARSEL_MARKERS)
                memcpy(markers[k], a->objects.records[i].position, sizeof markers[k]);
        }
    }
    if (mu_charsel_init(a->s, a->options.root, &a->list, (const float(*)[3])markers, (uint32_t)a->options.width,
                        (uint32_t)a->options.height, 20.0f)) {
        fprintf(stderr, "%s\n", a->s->error);
        return 1;
    }
    if (a->has_objects) {
        mu_objects_load_models(&a->objects, a->options.root, 0);
        /* NATIVE-CHARSEL-002: the client's object lifecycle with CGMCharacterScene_Ex */
        if (mu_charsel_attach_objects(a->s, a->options.root, &a->objects))
            fprintf(stderr, "objects: the lifecycle did not start (static objects are not drawn)\n");
    }
    if (a->options.slot >= 0) {
        if (mu_charsel_entry_of(a->s, a->options.slot) < 0) {
            fprintf(stderr, "slot %d is not in the list\n", a->options.slot);
            return 1;
        }
        mu_charsel_select(a->s, a->options.slot);
    }
    return 0;
}

static void unload(mu_charsel_rt *a)
{
    if (a->s) {
        mu_charsel_free(a->s);
        free(a->s);
        a->s = NULL;
    }
    if (a->has_objects) {
        mu_objects_free(&a->objects);
        a->has_objects = 0;
    }
}

const mu_charsel_part_ops mu_charsel_scene_part = {
    .open = load,
    .close = unload,
};
