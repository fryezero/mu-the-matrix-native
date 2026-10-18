/* Character-select scene (NATIVE-CHARSEL-001). See charsel.h. */
#include "charsel.h"

#include <math.h>
#include <stdarg.h>
#include <string.h>

/* ---- record access (little endian, unaligned) ---- */

static uint16_t get16(const uint8_t *p, uint32_t offset)
{
    return (uint16_t)(p[offset] | (p[offset + 1] << 8));
}

static void put16(uint8_t *p, uint32_t offset, uint16_t value)
{
    p[offset] = (uint8_t)value;
    p[offset + 1] = (uint8_t)(value >> 8);
}

static float getf(const uint8_t *p, uint32_t offset)
{
    float value;
    memcpy(&value, p + offset, sizeof value);
    return value;
}

static void putf(uint8_t *p, uint32_t offset, float value)
{
    memcpy(p + offset, &value, sizeof value);
}

static int32_t get32(const uint8_t *p, uint32_t offset)
{
    int32_t value;
    memcpy(&value, p + offset, sizeof value);
    return value;
}

static uint32_t bits(float value)
{
    uint32_t word;
    memcpy(&word, &value, sizeof word);
    return word;
}

static uint8_t *lookup(mu_charsel_character_fn character, void *context, int32_t index)
{
    /* 0x009a13f4: NULL outside 0..399 */
    if (index < 0 || index >= MU_CHARSEL_CHARACTERS)
        return NULL;
    return character(context, index);
}

/* ---- log ---- */

static void event(mu_charsel_log *log, uint32_t call, int32_t count, ...)
{
    if (!log)
        return;
    if (log->count >= MU_CHARSEL_LOG_MAX) {
        log->overflow = 1;
        return;
    }
    mu_charsel_event *e = &log->events[log->count++];
    memset(e, 0, sizeof *e);
    e->call = call;
    e->count = count;
    va_list list;
    va_start(list, count);
    for (int32_t i = 0; i < count && i < MU_CHARSEL_EVENT_ARGS; ++i)
        e->args[i] = va_arg(list, uint32_t);
    va_end(list);
}

/* ---- CGMCharacterScene_Ex ---- */

/* 0x00daa47c.. constants 0x01aa73cc, 0x01a7fb1c, 0x01aa73c8, 0x01a7e93c, 0x01a7fca4 */
const float mu_charsel_marker_yaw[MU_CHARSEL_MARKERS] = {115.0f, 90.0f, 75.0f, 60.0f, 35.0f};

void mu_charsel_scene_init(mu_charsel_scene *scene)
{
    memset(scene, 0, sizeof *scene);
}

int mu_charsel_set_character_position(const mu_charsel_scene *scene, int32_t slot, mu_charsel_character_fn character,
                                      void *context)
{
    uint8_t *c = lookup(character, context, slot);
    if (!c)
        return 0;
    uint8_t *o = c + MU_CHARSEL_OBJECT;
    /* the source index is the constant 1 (0x00daa031: push 0xc; pop eax; shl eax, 0) */
    for (int i = 0; i < 3; ++i)
        putf(o, MU_OBJ_POSITION + 4u * (uint32_t)i, scene->position[1][i]);
    for (int i = 0; i < 3; ++i)
        putf(o, MU_OBJ_ANGLE + 4u * (uint32_t)i, scene->angle[1][i]);
    return 1;
}

int mu_charsel_create_object(mu_charsel_scene *scene, int32_t world, mu_charsel_map_object *object,
                             mu_charsel_character_fn character, void *context)
{
    /* 0x00daa1f5: active only in world 0x5d */
    if (world != MU_CHARSEL_WORLD)
        return 0;
    object->field_64 = 0;
    int32_t type = object->type;
    switch (type) {
    case 0x0d: case 0x0e: case 0x0f: case 0x10: case 0x11: {
        int32_t k = type - 0x0d;
        for (int i = 0; i < 3; ++i)
            scene->position[k][i] = object->position[i];
        scene->angle[k][0] = 0.0f;
        scene->angle[k][1] = 0.0f;
        scene->angle[k][2] = mu_charsel_marker_yaw[k];
        mu_charsel_set_character_position(scene, k, character, context);
        object->field_68 = -2;
        break;
    }
    case 0x26: case 0x27: case 0x28: case 0x36: case 0x37: case 0x38: case 0x39: case 0x45: case 0x50:
        object->field_68 = -2;
        break;
    case 0x3c: case 0x3d:
        object->field_c0 = -428.571442f;   /* 0x01aa5ad4 = 0xc3d64925 */
        break;
    default:
        break;
    }
    return 1;
}

/* ---- SetCharacterScale 0x01394f6f ---- */

static uint8_t class_nibble(uint8_t class_byte)
{
    return (uint8_t)(class_byte & 0xf);   /* 0x0095f5cc */
}

static uint8_t skin_index(uint8_t class_byte)
{
    /* 0x0139d6a2 (= mu_character_skin_index, verified): base + 16*(tier-1),
     * tier 1 for a zero high nibble, else 2 + index of its highest set bit */
    uint8_t high = (uint8_t)(class_byte >> 4), tier = 1;
    if (high) {
        int top = 0;
        for (int bit = 0; bit < 4; ++bit)
            if (high & (1 << bit))
                top = bit;
        tier = (uint8_t)(2 + top);
    }
    return (uint8_t)(class_nibble(class_byte) + 16 * (tier - 1));
}

static int helm_shows_face(int16_t helm)
{
    /* 0x01394fa3..0x01395077 */
    static const int16_t list[] = {0x18e6, 0x18e8, 0x18f0, 0x18f1, 0x18f2, 0x18f3, 0x1925, 0x1927, 0x192a,
                                   0x192c, 0x193d, 0x193e, 0x193f, 0x19a0, 0x19a1, 0x1a35, 0x1a5f};
    for (size_t i = 0; i < sizeof list / sizeof list[0]; ++i)
        if (list[i] == helm)
            return 1;
    return 0;
}

void mu_charsel_character_scale(uint8_t *c, uint32_t ref, const mu_charsel_scale_inputs *in, mu_charsel_log *log)
{
    if (c[MU_CHAR_FLAG_E])
        return;
    int16_t helm = (int16_t)get16(c, MU_CHAR_PARTS + MU_CHAR_PART_SIZE * 1);
    if (helm_shows_face(helm))
        put16(c, MU_CHAR_PARTS, (uint16_t)(skin_index(c[MU_CHAR_CLASS]) + 0x3700));
    else
        put16(c, MU_CHAR_PARTS, 0xffff);
    event(log, 0x009dacb8, 1, (uint32_t)in->world);
    uint8_t nibble = class_nibble(c[MU_CHAR_CLASS]);
    if (in->event_world) {
        for (uint32_t k = 0; k < 6; ++k)
            putf(c, MU_CHAR_PARTS + MU_CHAR_PART_SIZE * k + 0xc4, 0.0f);
        /* jump table 0x013953f3 */
        putf(c, MU_CHARSEL_OBJECT + MU_OBJ_SCALE, nibble == 2 ? 0.88f : 0.9f);
        return;
    }
    for (uint32_t k = 0; k < 6; ++k) {
        float value = 0.0f;
        if (nibble == 11 && k == 1)
            value = 0.95f;
        putf(c, MU_CHAR_PARTS + MU_CHAR_PART_SIZE * k + 0xc4, value);
    }
    if (in->scene == MU_CHARSEL_SCENE) {
        putf(c, MU_CHARSEL_OBJECT + MU_OBJ_SCALE, 1.7f);   /* 0x01a9a5a4 */
        return;
    }
    /* jump table 0x01395433 */
    static const float scale[16] = {0.9f, 0.9f, 0.88f, 0.95f, 0.92f, 0.9f, 1.03f, 0.9f,
                                    0.9f, 0.9f, 0.9f, 0.99f, 0.9f, 0.9f, 0.8f, 1.1f};
    putf(c, MU_CHARSEL_OBJECT + MU_OBJ_SCALE, scale[nibble]);
    event(log, 0x01295ade, 2, ref + 0x35ac, 0x1a8u);
    int buff = in->buff_1a8;
    if (!buff) {
        event(log, 0x01295ade, 2, ref + 0x35ac, 0x1a9u);
        buff = in->buff_1a9;
    }
    if (buff)
        putf(c, MU_CHARSEL_OBJECT + MU_OBJ_SCALE, 1.1f);   /* 0x01a889d0 */
}

/* ---- CreateHero 0x0137f824 ---- */

uint8_t *mu_charsel_create_hero(int32_t slot, uint8_t class_byte, uint8_t skin, float x, float y, float angle,
                                const mu_charsel_scale_inputs *scale, mu_charsel_character_fn character, void *context,
                                mu_charsel_log *log)
{
    uint8_t *c = lookup(character, context, slot);
    if (!c)
        return NULL;
    uint32_t ref = MU_CHARSEL_REF(slot, 0);
    uint8_t *o = c + MU_CHARSEL_OBJECT;
    event(log, 0x0137d8a1, 5, ref, (uint32_t)MU_CHARSEL_PLAYER_MODEL, 0u, 0u, bits(angle));
    for (uint32_t i = 0; i < 3; ++i)
        putf(o, MU_OBJ_LIGHT + 4 * i, 0.3f);
    put16(c, MU_CHAR_KEY, (uint16_t)slot);
    putf(o, MU_OBJ_POSITION, x);
    putf(o, MU_OBJ_POSITION + 4, y);
    c[MU_CHAR_CLASS] = class_byte;
    c[MU_CHAR_SKIN] = skin;
    event(log, 0x01295f18, 1, ref + MU_CHARSEL_OBJECT + MU_OBJ_BUFFS);
    if (scale->scene == 3) {
        /* login scene: preset equipment (0x0137f937..0x0137fa66) */
        static const uint16_t parts[5] = {0x1902, 0x1b02, 0x1d02, 0x1f02, 0x2102};
        for (uint32_t k = 1; k <= 5; ++k) {
            put16(c, MU_CHAR_PARTS + MU_CHAR_PART_SIZE * k, parts[k - 1]);
            c[MU_CHAR_PARTS + MU_CHAR_PART_SIZE * k + 2] = 7;
        }
        put16(c, MU_CHAR_WEAPONS, 0x0ef4);
        put16(c, MU_CHAR_WEAPONS + MU_CHAR_PART_SIZE, 0x24eb);
        c[MU_CHAR_WEAPONS + 2] = 0x0d;
        put16(c, MU_CHAR_WING, 0x2504);
        put16(c, MU_CHAR_HELPER, 0x24ea);
    } else {
        static const uint16_t base[5] = {0x3700, 0x3750, 0x37a0, 0x37f0, 0x3840};
        for (uint32_t k = 1; k <= 5; ++k)
            put16(c, MU_CHAR_PARTS + MU_CHAR_PART_SIZE * k, (uint16_t)(skin_index(class_byte) + base[k - 1]));
        put16(c, MU_CHAR_WEAPONS, 0xffff);
        put16(c, MU_CHAR_WEAPONS + MU_CHAR_PART_SIZE, 0xffff);
        put16(c, MU_CHAR_WING, 0xffff);
        put16(c, MU_CHAR_HELPER, 0xffff);
        event(log, 0x0129dc78, 2, ref, 0xffffu);
        c[MU_CHAR_BYTE_322C] = 0xff;
    }
    event(log, 0x0128ed7d, 2, 0x1cu, ref + MU_CHARSEL_OBJECT);
    c[MU_CHAR_FLAG_14] = 0;
    mu_charsel_character_scale(c, ref, scale, log);
    event(log, 0x0138fe69, 1, ref);
    return c;
}

/* ---- render 0x018576b3 ---- */

float mu_charsel_character_z(uint16_t mount)
{
    return mount == 0x1a03 ? 194.5f : 169.5f;   /* 0x01af7064 / 0x01af7060 */
}

float mu_charsel_highlight_luminosity(float world_time)
{
    float x = world_time * 0.0015f;                 /* 0x01a800a0 */
    float s = (float)sin((double)x);                /* CRT sin 0x01985700, fstp dword */
    float value = s * 0.3f;                         /* 0x01a7e6e0 */
    return value + 0.5f;                            /* 0x01a7df14 */
}

static void log_vector(uint32_t *out, const uint8_t *p, uint32_t offset)
{
    for (uint32_t i = 0; i < 3; ++i)
        out[i] = bits(getf(p, offset + 4 * i));
}

int mu_charsel_render(const mu_charsel_frame *f, mu_charsel_character_fn character, void *context, uint8_t *fog,
                      mu_charsel_log *log)
{
    if (!f->initialised)
        return 0;
    if (f->protocol < 0x33)
        return 0;
    *fog = 0;
    event(log, 0x016b47bf, 1, 1u);
    if (f->pick >= 0) {
        event(log, 0x00cc3564, 0);
        if (f->input_byte_1f) {
            event(log, 0x011e228b, 0);
            event(log, 0x009a5029, 2, MU_CHARSEL_ID(MU_CHARSEL_ID_UIMNG) + 0x4bb0, (uint32_t)f->selected);
            if (!f->enter_refused)
                event(log, 0x0185a75a, 1, 0u);
        }
    }
    event(log, 0x0098647b, 0);
    event(log, 0x0098647b, 0);
    event(log, 0x0098647b, 0);
    event(log, 0x0185498e, 0);
    event(log, MU_CHARSEL_GL_COLOR3F, 3, bits(1.0f), bits(1.0f), bits(1.0f));
    const int32_t height = 480;
    event(log, 0x016bc355, 0);
    int32_t width = f->screen_width;
    /* 0x01857811: the red component pushed is 255.0 (0x01a7df30) */
    event(log, MU_CHARSEL_GL_CLEAR_COLOR, 4, bits(255.0f), 0u, 0u, bits(1.0f));
    event(log, 0x0184adc7, 4, 0u, 0u, (uint32_t)width, (uint32_t)height);
    float aspect = (float)width / 640.0f;
    event(log, 0x016cba24, 5, bits(aspect), bits(f->record_position[0]), bits(f->record_position[1]),
          bits(f->record_position[2]), 0u);
    /* CreateScreenVector(MouseX, MouseY, &MouseTarget, 1) */
    event(log, 0x01849f08, 4, bits((float)f->mouse_x), bits((float)f->mouse_y), 0x0bdc5990u, 1u);
    for (int32_t i = 0; i < MU_CHARSEL_LIST; ++i) {
        uint8_t *c = lookup(character, context, i);
        for (uint32_t k = 0; k < 3; ++k)
            putf(c + MU_CHARSEL_OBJECT, MU_OBJ_LIGHT + 4 * k, 0.0f);
    }
    uint8_t *selected = lookup(character, context, f->selected);
    if (selected && selected[MU_CHARSEL_OBJECT + MU_OBJ_LIVE]) {
        uint8_t *o = selected + MU_CHARSEL_OBJECT;
        event(log, 0x0184aa2b, 0);
        for (uint32_t k = 0; k < 3; ++k)
            putf(o, MU_OBJ_LIGHT + 4 * k, 1.0f);
        event(log, 0x016cacfc, 7, bits(getf(o, MU_OBJ_POSITION)), bits(getf(o, MU_OBJ_POSITION + 4)), bits(1.0f),
              bits(1.0f), bits(1.0f), 1u, 0x0b9f5430u);
        event(log, 0x0184a7f3, 0);
    }
    for (int32_t i = 0; i < MU_CHARSEL_LIST; ++i) {
        uint8_t *c = lookup(character, context, i);
        putf(c + MU_CHARSEL_OBJECT, MU_OBJ_POSITION + 8, mu_charsel_character_z(get16(c, MU_CHAR_MOUNT)));
    }
    event(log, 0x016cd468, 1, 0u);
    event(log, 0x016d5020, 0);
    uint8_t *shown = lookup(character, context, f->shown);
    if (shown && shown[MU_CHARSEL_OBJECT + MU_OBJ_LIVE] && shown[MU_CHARSEL_OBJECT + MU_OBJ_VISIBLE]) {
        event(log, 0x01363260, 3, MU_CHARSEL_REF(f->shown, 0), MU_CHARSEL_REF(f->shown, MU_CHARSEL_OBJECT), 0u);
        if (get32(shown + MU_CHARSEL_OBJECT, MU_OBJ_TYPE) == MU_CHARSEL_PLAYER_MODEL)
            event(log, 0x00d8bd8f, 2, MU_CHARSEL_REF(f->shown, 0), MU_CHARSEL_REF(f->shown, MU_CHARSEL_OBJECT));
    }
    event(log, 0x00c9e4e3, 0);
    event(log, 0x01534b4c, 0);
    event(log, 0x01589b56, 1, 0u);
    event(log, 0x015181fa, 2, 0x0a4ca430u, 0u);
    event(log, 0x00b990b0, 0);
    event(log, 0x00eb1309, 2, MU_CHARSEL_ID(MU_CHARSEL_ID_QUEST_MGR), shown ? MU_CHARSEL_REF(f->shown, 0) : 0u);
    if (f->quest_object)
        event(log, 0x00eac4e0, 1, MU_CHARSEL_ID(MU_CHARSEL_ID_QUEST));
    event(log, 0x00c9fd8d, 1, 0u);
    event(log, 0x016d6949, 0);
    event(log, 0x01692887, 1, 0x0a3da070u);
    if (selected) {
        uint8_t *o = selected + MU_CHARSEL_OBJECT;
        if (o[MU_OBJ_LIVE]) {
            float light[3] = {1.0f, 1.0f, 1.0f};
            float luminosity = mu_charsel_highlight_luminosity(f->world_time);
            for (int k = 0; k < 3; ++k)
                light[k] = luminosity * light[k];
            event(log, 0x0184aa2b, 0);
            const float sizes[2] = {1.8f, 1.2f};          /* 0x01a7ebc0, 0x01a7e6e4 */
            for (int pass = 0; pass < 2; ++pass) {
                float t = pass == 0 ? f->world_time : -f->world_time;
                float rotation = t * 0.01f;                 /* 0x01a7df00 */
                event(log, 0x016cdd5f, 13, 0x8036u, bits(getf(o, MU_OBJ_POSITION)), bits(getf(o, MU_OBJ_POSITION + 4)),
                      bits(sizes[pass]), bits(sizes[pass]), bits(light[0]), bits(light[1]), bits(light[2]),
                      bits(rotation), bits(1.0f), bits(5.0f), 1u, 0u);
            }
            event(log, 0x0184a7f3, 0);
            for (uint32_t k = 0; k < 3; ++k)
                putf(o, MU_OBJ_LIGHT + 4 * k, 0.15f);       /* 0x01a7e6d8 */
            if (log && log->count < MU_CHARSEL_LOG_MAX) {
                event(log, 0x0168fafd, 14, 0x8022u, 0u, 0u, 0u, 0u, 0u, 0u, 0u, 0u, 0u, 5u, bits(1.0f), 0u, 0u);
                mu_charsel_event *e = &log->events[log->count - 1];
                log_vector(&e->args[1], o, MU_OBJ_POSITION);
                log_vector(&e->args[4], o, MU_OBJ_ANGLE);
                log_vector(&e->args[7], o, MU_OBJ_LIGHT);
            } else {
                event(log, 0x0168fafd, 0);
            }
        }
        uint8_t *again = lookup(character, context, f->selected);
        if (again) {
            event(log, 0x0121d4c9, 0);
            event(log, 0x009eaebe, 2, MU_CHARSEL_ID(MU_CHARSEL_ID_NAME_MGR), MU_CHARSEL_REF(f->selected, 0x3658));
        }
    }
    event(log, 0x0184a699, 0);
    event(log, 0x009c104e, 0);
    event(log, 0x0106bcc5, 2, MU_CHARSEL_ID(MU_CHARSEL_ID_UI_HELPER), 1u);
    event(log, 0x0169270e, 2, 0x0a3da070u, 0u);
    event(log, 0x0159123f, 2, 0x0a3a9adcu, 0u);
    event(log, 0x0169159e, 2, 0x0a3ae150u, 0u);
    event(log, 0x009c104e, 0);
    event(log, 0x0106bcc5, 2, MU_CHARSEL_ID(MU_CHARSEL_ID_UI_HELPER), 0u);
    event(log, 0x0184a6ab, 0);
    event(log, 0x0184f793, 0);
    event(log, 0x01858c72, 0);
    event(log, 0x0184f8d7, 0);
    event(log, 0x0184b6dd, 0);
    return 1;
}

/* ---- logic tick 0x01856e6c ---- */

int mu_charsel_tick_step(mu_charsel_tick *t, mu_charsel_log *log)
{
    if (t->protocol < 0x33)
        return 0;
    if (!t->initialised) {
        t->initialised = 1;
        event(log, 0x01851540, 0);
    }
    event(log, 0x016ca4fa, 0);
    event(log, 0x016d82c7, 0);
    event(log, 0x00c9e24a, 0);
    event(log, 0x0137a7ce, 0);
    event(log, 0x0137a716, 1, 0x0a39d780u);
    event(log, 0x009c104e, 0);
    event(log, 0x0106bcc5, 2, MU_CHARSEL_ID(MU_CHARSEL_ID_UI_HELPER), 1u);
    event(log, 0x0150ddb1, 1, 0x0a4ca430u);
    event(log, 0x01589b06, 0);
    event(log, 0x0159122d, 1, 0x0a3a9adcu);
    event(log, 0x009c104e, 0);
    event(log, 0x0106bcc5, 2, MU_CHARSEL_ID(MU_CHARSEL_ID_UI_HELPER), 0u);
    event(log, 0x00c9eb04, 0);
    event(log, 0x00b990b0, 0);
    event(log, 0x00eb0d64, 1, MU_CHARSEL_ID(MU_CHARSEL_ID_QUEST_MGR));
    event(log, 0x009c2aea, 0);
    event(log, 0x009b9913, 1, MU_CHARSEL_ID(MU_CHARSEL_ID_UI_9C2AEA));
    event(log, 0x00ac3bf7, 0);
    event(log, 0x00ac9613, 2, MU_CHARSEL_ID(MU_CHARSEL_ID_GFX), (uint32_t)t->scene);
    event(log, 0x01854529, 0);
    event(log, 0x00ac3bf7, 0);
    event(log, 0x00aae6f9, 1, MU_CHARSEL_ID(MU_CHARSEL_ID_GFX_MOVIE));
    if (t->gfx_busy == 1)
        return 0;
    event(log, 0x00cc3564, 0);
    event(log, 0x011e228b, 0);
    int enter = 0;
    if (!t->input_byte_31) {
        event(log, 0x00ec53a7, 1, 0x0du);
        enter = t->key_enter;
    }
    if (enter) {
        event(log, 0x00ac3bf7, 0);
        event(log, 0x00aae6f9, 1, MU_CHARSEL_ID(MU_CHARSEL_ID_GFX_MOVIE));
        if (t->gfx_busy_enter)
            return 1;
        event(log, 0x00ac3bf7, 0);
        if (t->gfx_flag_79 || t->global_1d22d1e || t->global_6fca007)
            return 1;
        event(log, 0x00ac3bf7, 0);
        if (t->gfx_flag_78 || t->ui_byte_464)
            return 1;
        if (t->selected <= -1 || t->selected >= MU_CHARSEL_LIST)
            return 1;
        event(log, 0x00a6ac96, 3, 0x19u, 0u, 0u);
        if (t->shown >= 0)
            t->selected = t->shown;
        event(log, 0x009a5029, 2, MU_CHARSEL_ID(MU_CHARSEL_ID_UIMNG) + 0x4bb0, (uint32_t)t->selected);
        if (t->enter_refused == 1)
            return 1;
        event(log, 0x0185a75a, 1, 0u);
        return 1;
    }
    int escape = 0;
    if (!t->input_byte_31) {
        event(log, 0x00ec53a7, 1, 0x1bu);
        escape = t->key_escape;
    }
    if (!escape)
        return 1;
    event(log, 0x00ac3bf7, 0);
    event(log, 0x00aae6f9, 1, MU_CHARSEL_ID(MU_CHARSEL_ID_GFX_MOVIE));
    if (!t->gfx_busy_escape && !t->global_6fca007) {
        event(log, 0x00ac3bf7, 0);
        if (!t->gfx_flag_78 && !t->global_1d22d1e && !t->gfx_menu_flag) {
            event(log, 0x00a6ac96, 3, 0x19u, 0u, 0u);
            event(log, 0x009a5792, 2, 0x01d22c60u, MU_CHARSEL_STACK_REF);
            event(log, 0x00c8c8b1, 1, MU_CHARSEL_ID(MU_CHARSEL_ID_MENU_HANDLE));
            return 1;
        }
    }
    event(log, 0x00ac3bf7, 0);
    if (t->gfx_flag_78) {
        event(log, 0x00a6ac96, 3, 0x19u, 0u, 0u);
        event(log, 0x00ac3bf7, 0);
        event(log, 0x00b49bf4, 2, MU_CHARSEL_ID(MU_CHARSEL_ID_GFX_22C), 0u);
        event(log, 0x011e228b, 0);
        t->ui_byte_65b9 = 0;
    }
    return 1;
}
