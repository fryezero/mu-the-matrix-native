#include "actors.h"

#include <stdio.h>
#include <string.h>

#include "monster_open_table.h"
#include "monster_class_table.h"
#include "npc_table.h"

/* OpenMonsterModel 0x0180b0f4 (action part) and helpers. Client memory is
 * read where the original reads it and written in the original order. */

static uint8_t *at(const mu_client_memory *memory, uint32_t address, uint32_t length)
{
    for (uint32_t index = 0; index < memory->count; ++index) {
        const mu_client_image *region = &memory->regions[index];
        if (address < region->base)
            continue;
        uint32_t start = address - region->base;
        if (start <= region->size && length <= region->size - start)
            return region->bytes + start;
    }
    return NULL;
}

static int read32(const mu_client_memory *memory, uint32_t address, uint32_t *value)
{
    uint8_t *p = at(memory, address, 4);
    if (!p)
        return 0;
    *value = (uint32_t)p[0] | ((uint32_t)p[1] << 8) | ((uint32_t)p[2] << 16) | ((uint32_t)p[3] << 24);
    return 1;
}

static int read16(const mu_client_memory *memory, uint32_t address, int16_t *value)
{
    uint8_t *p = at(memory, address, 2);
    if (!p)
        return 0;
    *value = (int16_t)(uint16_t)((uint32_t)p[0] | ((uint32_t)p[1] << 8));
    return 1;
}

static int write32(const mu_client_memory *memory, uint32_t address, uint32_t value)
{
    uint8_t *p = at(memory, address, 4);
    if (!p)
        return 0;
    for (unsigned byte = 0; byte < 4; ++byte)
        p[byte] = (uint8_t)(value >> (byte * 8));
    return 1;
}

static int write8(const mu_client_memory *memory, uint32_t address, uint8_t value)
{
    uint8_t *p = at(memory, address, 1);
    if (!p)
        return 0;
    *p = value;
    return 1;
}

static uint32_t float_bits(float value)
{
    uint32_t bits;
    memcpy(&bits, &value, sizeof bits);
    return bits;
}

static float bits_float(uint32_t bits)
{
    float value;
    memcpy(&value, &bits, sizeof value);
    return value;
}

#define CHECK(expression) do { if (!(expression)) return MU_ACTOR_OUTSIDE_MEMORY; } while (0)

/* SetActionSpeed 0x012bd437 / SetActionLoop 0x012bd471: thiscall on the model,
 * refuse action < 0 or >= (int16)model[+0x26]. */
static int set_action(const mu_client_memory *memory, uint32_t model, int32_t action, uint32_t field,
                      uint32_t value, int byte)
{
    int16_t actions;
    uint32_t array;
    CHECK(read16(memory, model + 0x26, &actions));
    if (action < 0 || action >= actions)
        return MU_ACTOR_OK;
    CHECK(read32(memory, model + 0x30, &array));
    uint32_t address = array + (uint32_t)action * 16u + field;
    CHECK(byte ? write8(memory, address, (uint8_t)value) : write32(memory, address, value));
    return MU_ACTOR_OK;
}

/* GetAction 0x012bcf9d: the action record address or 0. */
static int get_action(const mu_client_memory *memory, uint32_t model, int32_t action, uint32_t *record)
{
    int16_t actions;
    uint32_t array;
    *record = 0;
    CHECK(read16(memory, model + 0x26, &actions));
    if (action < 0 || action >= actions)
        return MU_ACTOR_OK;
    CHECK(read32(memory, model + 0x30, &array));
    *record = array + (uint32_t)action * 16u;
    return MU_ACTOR_OK;
}

/* World predicate 0x009dacb8. */
static int npc_texture_world(int32_t world)
{
    return (world >= 0x12 && world <= 0x17) || world == 0x35 || world == 0x61;
}

static int run_op(const mu_client_memory *memory, const mu_monster_services *services, uint32_t own,
                  uint32_t own_index, const mu_monster_op *op)
{
    uint32_t model = own;
    if (op->model != 0) {
        model = services->model_at(services->context, (uint32_t)((int32_t)own_index + op->model));
        if (!model)
            return MU_ACTOR_CLIENT_FAULT;
    }
    uint32_t array, record;
    int status;
    switch (op->kind) {
    case MU_MONSTER_OP_SPEED:
        return set_action(memory, model, op->action, 4, op->value, 0);
    case MU_MONSTER_OP_LOOP:
        return set_action(memory, model, op->action, 0, op->value, 1);
    case MU_MONSTER_OP_ACTION_SPEED:
        status = get_action(memory, model, op->action, &record);
        if (status != MU_ACTOR_OK)
            return status;
        if (!record)
            return MU_ACTOR_CLIENT_FAULT;
        CHECK(write32(memory, record + 4, op->value));
        return MU_ACTOR_OK;
    case MU_MONSTER_OP_RAW32:
    case MU_MONSTER_OP_RAW8:
        CHECK(read32(memory, model + 0x30, &array));
        if (op->kind == MU_MONSTER_OP_RAW32)
            CHECK(write32(memory, array + op->action * 16u + op->offset, op->value));
        else
            CHECK(write8(memory, array + op->action * 16u + op->offset, (uint8_t)op->value));
        return MU_ACTOR_OK;
    case MU_MONSTER_OP_FIELD32:
        CHECK(write32(memory, model + op->offset, op->value));
        return MU_ACTOR_OK;
    case MU_MONSTER_OP_FIELD8:
        CHECK(write8(memory, model + op->offset, (uint8_t)op->value));
        return MU_ACTOR_OK;
    default:
        return MU_ACTOR_OUTSIDE_MEMORY;
    }
}

const mu_monster_op *mu_monster_type_ops(int32_t type, uint32_t *count)
{
    *count = 0;
    if (type < 0 || type >= MU_MONSTER_TABLE_TYPES)
        return NULL;
    uint16_t block = mu_monster_type_block[type];
    *count = (uint32_t)(mu_monster_block_start[block + 1] - mu_monster_block_start[block]);
    return &mu_monster_ops[mu_monster_block_start[block]];
}

int mu_monster_open(const mu_client_memory *memory, int32_t type, int32_t world, const mu_monster_services *services)
{
    uint32_t index = (uint32_t)type + MU_MONSTER_MODEL_BASE;
    uint32_t model = services->model_at(services->context, index);
    if (!model)
        return MU_ACTOR_OK;
    int16_t meshes, actions;
    CHECK(read16(memory, model + 0x26, &actions));
    if (actions > 0)
        return MU_ACTOR_OK;
    CHECK(read16(memory, model + 0x24, &meshes));
    if (meshes > 0)
        return MU_ACTOR_OK;
    services->access_model(services->context, index, "Data\\Monster\\", "Monster", type + 1);
    CHECK(read16(memory, model + 0x24, &meshes));
    if (meshes == 0)
        return MU_ACTOR_OK;

    const char *directory = "Monster\\";
    if (npc_texture_world(world) && type >= 0x46 && type <= 0x48)
        directory = "Npc\\";
    else if (world == 30 && type == 0x4a)
        directory = "Object31\\";
    if (services->open_texture)
        services->open_texture(services->context, index, directory, 0x2901, 0x2600);
    /* Not reconstructed here: the type-specific sound (0x00a6ab76), extra
     * texture (0x0185baac) and action-sound (0x018329fa) loads of the
     * switch at 0x0180b20f and of the two switches below. */

    static const float defaults[7] = {0.25f, 0.2f, 0.34f, 0.33f, 0.33f, 0.5f, 0.55f};
    int status;
    for (int32_t action = 0; action < 7; ++action)
        if ((status = set_action(memory, model, action, 4, float_bits(defaults[action]), 0)) != MU_ACTOR_OK)
            return status;
    if ((status = set_action(memory, model, 6, 0, 1, 1)) != MU_ACTOR_OK)
        return status;

    for (uint32_t action = 0; action < 6; ++action) {
        static const struct { int32_t a, b, c; float scale; } rules[3] = {
            {3, 3, 3, 1.2f}, {5, 25, 25, 0.7f}, {37, 42, 0x1ab, 0.4f}};
        for (int rule = 0; rule < 3; ++rule) {
            if (type != rules[rule].a && type != rules[rule].b && type != rules[rule].c)
                continue;
            uint32_t array, bits;
            CHECK(read32(memory, model + 0x30, &array));
            CHECK(read32(memory, array + action * 16u + 4, &bits));
            float value = bits_float(bits) * rules[rule].scale;
            CHECK(read32(memory, model + 0x30, &array));
            CHECK(write32(memory, array + action * 16u + 4, float_bits(value)));
        }
    }

    uint32_t count;
    const mu_monster_op *ops = mu_monster_type_ops(type, &count);
    for (uint32_t i = 0; i < count; ++i)
        if ((status = run_op(memory, services, model, index, &ops[i])) != MU_ACTOR_OK)
            return status;
    return MU_ACTOR_OK;
}

int mu_monster_model_file(int32_t type, char *out, uint32_t size)
{
    if (type < 0 || (uint32_t)type >= MU_MONSTER_TYPE_COUNT || !out || size == 0)
        return 0;
    int number = type + 1;
    int written = snprintf(out, size, number < 10 ? "Data\\Monster\\Monster0%d.bmd" : "Data\\Monster\\Monster%d.bmd",
                           number);
    return written > 0 && (uint32_t)written < size;
}

/* ------------------------------------------------------------------ */
/* Character animation step 0x013960d2. */

static int read_u16(const mu_client_memory *memory, uint32_t address, uint16_t *value)
{
    int16_t raw;
    if (!read16(memory, address, &raw))
        return 0;
    *value = (uint16_t)raw;
    return 1;
}

static int read_f(const mu_client_memory *memory, uint32_t address, float *value)
{
    uint32_t bits;
    if (!read32(memory, address, &bits))
        return 0;
    *value = bits_float(bits);
    return 1;
}

static int read8(const mu_client_memory *memory, uint32_t address, uint8_t *value)
{
    uint8_t *p = at(memory, address, 1);
    if (!p)
        return 0;
    *value = *p;
    return 1;
}

/* cvttss2si: out-of-range and NaN give 0x80000000. */
static int32_t truncate_float(float value)
{
    if (!(value >= -2147483648.0f && value < 2147483648.0f))
        return INT32_MIN;
    return (int32_t)value;
}

int mu_character_animation_step(const mu_client_memory *memory, uint32_t character, uint32_t object,
                                const mu_character_services *services, const mu_tick_globals *globals,
                                uint8_t *result, float *speed_out)
{
    uint32_t type, actions, bits;
    uint16_t action, current;
    int16_t count;
    float speed = 0.0f, frame;
    uint8_t flag;
    *result = 0;
    *speed_out = 0.0f;
    CHECK(read32(memory, object + 0x5c, &type));
    uint32_t model = services->model_at(services->context, type);
    if (!model)
        return MU_ACTOR_OK;
    CHECK(read16(memory, model + 0x26, &count));
    if (count > 0) {
        CHECK(read_u16(memory, model + 0xa8, &current));
        CHECK(read32(memory, model + 0x30, &actions));
        CHECK(read32(memory, actions + (uint32_t)current * 16u + 4, &bits));
        speed = bits_float(bits);
        if (0.0f > speed)
            speed = 0.0f;
        CHECK(read8(memory, character + 0xe, &flag));
        if (flag) {
            CHECK(read_u16(memory, object + 0x2a, &action));
            if (action >= 3 && action <= 4)
                speed = speed * 1.5f;
        }
        CHECK(read_u16(memory, object + 0x2a, &action));
        int done = 0;
        if (action == 0x9c || action == 0x11d) {
            CHECK(read_f(memory, object + 0xd0, &frame));
            if (frame > 6.0f) {
                speed = speed / 2.0f;
                done = 1;
            }
        }
        if (!done) {
            CHECK(read_u16(memory, object + 0x2a, &action));
            if (action == 0x92) {
                CHECK(read_f(memory, object + 0xd0, &frame));
                if (frame > 5.5f) {
                    speed = speed / 10.0f;
                    done = 1;
                }
            }
        }
        if (!done) {
            uint8_t class_byte;
            CHECK(read8(memory, character + 0x12, &class_byte));
            if ((class_byte & 0xf) == 4) {
                CHECK(read_u16(memory, object + 0x2a, &action));
                if (action == 0xa7) {
                    CHECK(read_f(memory, object + 0xd0, &frame));
                    if (frame > 1.0f) {
                        CHECK(read_f(memory, object + 0xd0, &frame));
                        if (3.0f > frame) {
                            uint8_t check = services->weapon_check(services->context, character);
                            speed = check == 1 ? speed / 8.0f : speed / 2.0f;
                        }
                    }
                }
            }
        }
        CHECK(read_u16(memory, object + 0x2a, &action));
        if (action == 0x9f)
            speed = speed / 2.0f;
        CHECK(read32(memory, object + 0x5c, &type));
        if (type != 0xa91) {
            CHECK(read32(memory, object + 0x5c, &type));
            int32_t t = (int32_t)type;
            int timed = 0;
            if (t == 0x7e5 || t == 0x940) {
                timed = 1;
            } else if (t == 0xa52) {
                speed = speed * 0.5f;
            } else if (t <= 0x7e5 && (uint32_t)(t - 0x135) <= 0xf) {
                switch (t - 0x135) {
                case 0xa: speed = speed * 1.5f; break;
                case 0xd: speed = speed * 1.5f; break;
                case 0xe:
                    CHECK(read_u16(memory, object + 0x2a, &action));
                    speed = speed * 2.0f;   /* both branches multiply by 2.0 */
                    break;
                case 0xf:
                    CHECK(read_u16(memory, object + 0x2a, &action));
                    speed = action == 0 ? speed * 1.0f : speed * 1.5f;
                    break;
                default: speed = speed * 2.0f; break;
                }
            }
            if (timed) {
                CHECK(read_u16(memory, object + 0x2a, &action));
                if (action == 6) {
                    CHECK(read_f(memory, object + 0xd0, &frame));
                    if (frame > 6.0f)
                        speed = speed * 4.0f;
                }
            }
        }
        CHECK(read32(memory, object + 0x5c, &type));
        if (type == 0x7fc) {
            CHECK(read_u16(memory, object + 0x2a, &action));
            if (action == 6)
                speed = speed / 2.0f;
        }
    }
    static const uint32_t stopping_buffs[4] = {0x3d, 0x48, 0xb2, 0x118};
    for (int i = 0; i < 4; ++i)
        if (services->has_buff(services->context, object + 0x358, stopping_buffs[i]))
            return MU_ACTOR_OK;

    mu_tick_arguments tick = {object + 0xd0, object + 0xd4, object + 0x2c, float_bits(speed), object + 0x158,
                              object + 0x164};
    uint8_t loop = 1;
    int status = mu_animation_tick(memory, model, &tick, globals, &loop);
    if (status != MU_SKIN_OK)
        return MU_ACTOR_OUTSIDE_MEMORY;
    *speed_out = speed;
    CHECK(read_u16(memory, object + 0x2a, &action));
    if (action == 0x184 && !loop)
        services->stop(services->context, character);
    CHECK(read_u16(memory, object + 0x2a, &action));
    CHECK(read_u16(memory, object + 0x2a, &action));
    if (action != 0xd9)
        CHECK(read_u16(memory, object + 0x2a, &action));
    if ((action == 0xd9 || action == 0x125) && !loop)
        services->stop(services->context, character);
    CHECK(read_u16(memory, object + 0x2a, &action));
    if (action == 0x170) {
        uint32_t tile_x, tile_y, bones, tracks, positions;
        int16_t key;
        float px, py;
        CHECK(read32(memory, character + 0x180, &tile_x));
        CHECK(read32(memory, character + 0x184, &tile_y));
        CHECK(read32(memory, model + 0x2c, &bones));
        CHECK(read_u16(memory, object + 0x2a, &action));
        CHECK(read32(memory, bones + 0x24, &tracks));
        uint32_t track = tracks + (uint32_t)action * 0xcu;
        CHECK(read16(memory, model + 0xb4, &key));
        CHECK(read32(memory, track, &positions));
        CHECK(read_f(memory, positions + (uint32_t)((int32_t)key * 0xc), &px));
        int32_t dx = truncate_float(px);
        CHECK(read16(memory, model + 0xb4, &key));
        CHECK(read32(memory, track, &positions));
        CHECK(read_f(memory, positions + (uint32_t)((int32_t)key * 0xc) + 4, &py));
        int32_t dy = truncate_float(py);
        dx = truncate_float((float)dx / 100.0f);
        dy = truncate_float((float)dy / 100.0f);
        uint32_t cell = (((tile_y + (uint32_t)dy) << 8) + tile_x + (uint32_t)dx) * 2u;
        uint16_t attribute;
        CHECK(read_u16(memory, MU_TERRAIN_ATTRIBUTES + cell, &attribute));
        if (attribute & 4)
            services->stop(services->context, character);
    }
    *result = loop;
    return MU_ACTOR_OK;
}

/* ------------------------------------------------------------------ */
/* Extracted tables. */

const mu_monster_class *mu_monster_class_find(uint32_t server_class)
{
    for (uint32_t i = 0; i < MU_MONSTER_CLASS_ROWS; ++i)
        if (mu_monster_classes[i].server_class == server_class)
            return &mu_monster_classes[i];
    return NULL;
}

const mu_monster_class_speed *mu_monster_class_speeds_for(uint32_t server_class, uint32_t *count)
{
    *count = 0;
    for (uint32_t i = 0; i < MU_MONSTER_CLASS_SPEED_ROWS; ++i) {
        if (mu_monster_class_speeds[i].server_class != server_class)
            continue;
        uint32_t n = 0;
        while (i + n < MU_MONSTER_CLASS_SPEED_ROWS && mu_monster_class_speeds[i + n].server_class == server_class)
            ++n;
        *count = n;
        return &mu_monster_class_speeds[i];
    }
    return NULL;
}

const mu_npc_model *mu_npc_find(uint32_t index)
{
    for (uint32_t i = 0; i < MU_NPC_ROWS; ++i)
        if (mu_npc_models[i].index == index)
            return &mu_npc_models[i];
    return NULL;
}

float mu_monster_class_scale(const mu_monster_class *row)
{
    return row->scale_bits ? bits_float(row->scale_bits) : 0.9f;
}

int mu_access_model_file(const char *directory, const char *name, int32_t number, char *out, uint32_t size)
{
    int written;
    if (number == -1)
        written = snprintf(out, size, "%s%s.bmd", directory, name);
    else if (number < 10)
        written = snprintf(out, size, "%s%s0%d.bmd", directory, name, number);
    else
        written = snprintf(out, size, "%s%s%d.bmd", directory, name, number);
    return written > 0 && (uint32_t)written < size;
}

/* ------------------------------------------------------------------ */
/* SetAction 0x012affa4 and the unarmed stop action 0x0139d6da. */

int mu_set_action(const mu_client_memory *memory, uint32_t object, int32_t action,
                  uint32_t (*model_at)(void *context, uint32_t index), void *context)
{
    uint32_t type, frame;
    int16_t count;
    uint16_t current;
    CHECK(read32(memory, object + 0x5c, &type));
    uint32_t model = model_at(context, type);
    if (!model)
        return MU_ACTOR_OK;
    CHECK(read16(memory, model + 0x26, &count));
    if (action >= count)
        return MU_ACTOR_OK;
    CHECK(read_u16(memory, object + 0x2a, &current));
    if ((int32_t)current == action)
        return MU_ACTOR_OK;
    CHECK(read_u16(memory, object + 0x2a, &current));
    uint8_t *prior = at(memory, object + 0x2c, 2);
    CHECK(prior);
    prior[0] = (uint8_t)current;
    prior[1] = (uint8_t)(current >> 8);
    CHECK(read32(memory, object + 0xd0, &frame));
    CHECK(write32(memory, object + 0xd4, frame));
    uint8_t *slot = at(memory, object + 0x2a, 2);
    CHECK(slot);
    slot[0] = (uint8_t)action;
    slot[1] = (uint8_t)((uint32_t)action >> 8);
    CHECK(write32(memory, object + 0xd0, 0));
    return MU_ACTOR_OK;
}

int32_t mu_player_unarmed_stop_action(uint8_t class_byte, int32_t world, int32_t (*rand_function)(void *context),
                                      void *context)
{
    int base = class_byte & 0xf;
    int event_world = npc_texture_world(world);
    switch (base) {
    case 2: return 2;
    case 7: return 5;
    case 8: return 6;
    case 5: return event_world ? 1 : 3;
    case 9: return event_world ? 1 : 6;
    case 10:
        if (event_world)
            return 1;
        return rand_function(context) % 20 == 0 ? 0x1f : 1;
    case 11: return 1;
    case 12: return event_world ? 1 : 2;
    case 14: return 6;
    case 15:
        if (event_world)
            return 8;
        return rand_function(context) % 20 == 0 ? 9 : 8;
    default: return 1;
    }
}
