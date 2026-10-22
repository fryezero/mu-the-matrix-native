/* Helpers: pets and mounts (NATIVE-HELPERS-001). See helpers.h and docs/research/client-helpers.md.
 * Comparisons follow the client's comiss/jcc pairs, so NaN inputs take the same branches. */
#include "helpers.h"

#include <string.h>

#include "../movement/client_movement.h"

#ifndef MU_HP_MUTATION
#define MU_HP_MUTATION 0   /* negative controls (scripts/validate_helpers.py --mutations): 1..6 plant one mistake */
#endif
#include "../record-math/record_math.h"

/* ---------------------------------------------------------------- common */

void mu_hp_object_init(mu_hp_object *o)
{
    memset(o, 0, sizeof *o);   /* ObjectInit 0x0129eb81 on the modelled fields */
    o->owner = -1;
    o->alpha_speed = 0.1f;
    o->shadow_alpha = 1.0f;
}

void mu_hp_init(mu_helpers *h, uint32_t rand_seed, mu_hp_owner *owners, int32_t owner_count, const mu_hp_host *host)
{
    memset(h, 0, sizeof *h);
    h->rand_state = rand_seed;
    h->owners = owners;
    h->owner_count = owner_count;
    if (host)
        h->host = *host;
    for (int32_t i = 0; i < MU_HP_BUGS; ++i)   /* the array's OBJECT constructors at startup */
        mu_hp_object_init(&h->bugs[i]);
}

int32_t mu_hp_rand(mu_helpers *h)
{
    h->rand_state = h->rand_state * 214013u + 2531011u;
    ++h->rand_calls;
    return (int32_t)((h->rand_state >> 16) & 0x7fffu);
}

/* x % m for the client's power-of-two remainders (and 0x80000000|(m-1); jns; dec; or; inc): the C remainder. */
static int32_t rmod(int32_t v, int32_t m)
{
    return v % m;
}

static mu_hp_owner *owner_of(mu_helpers *h, int32_t index)
{
    return (index >= 0 && index < h->owner_count) ? &h->owners[index] : NULL;
}

static void set_live(mu_helpers *h, mu_hp_object *o, uint8_t live)
{
    o->live = live;   /* SetLive 0x0129f4a5 */
    if (!live && h->host.kill)
        h->host.kill(h->host.context, o);
}

static int has_model(mu_helpers *h, int32_t model)
{
    return h->host.has_model ? h->host.has_model(h->host.context, model) : 1;
}

void mu_hp_fade_alpha(mu_hp_object *o)
{
    if (o->alpha_enable) {
        if (o->alpha_target > o->alpha) {
            o->alpha = o->alpha + 0.05f;
            if (o->alpha > 1.0f)
                o->alpha = 1.0f;
        } else if (o->alpha > o->alpha_target) {
            o->alpha = o->alpha - 0.05f;
            if (0.0f > o->alpha)
                o->alpha = 0.0f;
        }
    } else {
        o->alpha = (o->alpha_target - o->alpha) * o->alpha_speed + o->alpha;
    }
    if (o->blend_light > o->alpha)
        o->blend_light = o->alpha;
}

/* 0x009dacb8: the run-speed worlds where no bug is created. */
static int no_bug_world(int32_t world)
{
    return (world >= 0x12 && world <= 0x17) || world == 0x35 || world == 0x61;
}

/* 0x009b0418 */
static int world_9b0418(int32_t world)
{
    return (world >= 0x18 && world <= 0x1d) || world == 0x24;
}

int mu_hp_world_16a88ae(int32_t world)
{
    return world == 7 || (world >= 0x80 && world <= 0x82);   /* 0x016a88ae with 0x016a8325 */
}

/* 0x009a645f on the event object (world 0x27, states other than 3..5). */
static int event_block(const mu_hp_inputs *in)
{
    if (in->world != 0x27)
        return 0;
    return !(in->event_state == 3 || in->event_state == 4 || in->event_state == 5);
}

/* ---------------------------------------------------------------- bugs */

int mu_hp_bug_type(int32_t type)
{
    return type == MU_HP_MODEL_ANGEL || type == MU_HP_MODEL_IMP || type == MU_HP_MODEL_DARK_SPIRIT;
}

/* CreateBugSub 0x00c9d42a. Returns its AL: 1 when the slot is live (try the next one), 0 when it created or
 * refused (world). */
static int create_bug_sub(mu_helpers *h, const mu_hp_inputs *in, int32_t type, const float position[3], int32_t owner,
                          mu_hp_object *o, int32_t subtype)
{
    if (no_bug_world(in->world))
        return 0;
    if (o->live)
        return 1;
    const mu_hp_owner *w = owner_of(h, owner);
    o->type = type;
    set_live(h, o, 1);
    o->visible = 0;
    o->lighting = 1;
    o->flag_0e = 0;
    o->alpha_enable = 0;
    o->flag_0d = 0;
    o->owner = owner;
    o->subtype = subtype;
    o->field_68 = -1;
    o->blend_mesh = -1;
    o->blend_light = 1.0f;
    o->scale = 0.7f;
    o->lifetime = 30;
    o->alpha = 0.0f;
    o->alpha_target = 1.0f;
    o->position[0] = position[0];
    o->position[1] = position[1];
    o->position[2] = position[2];
    o->angle[0] = w->angle[0];
    o->angle[1] = w->angle[1];
    o->angle[2] = w->angle[2];
    o->light[0] = o->light[1] = o->light[2] = 3.0f;
    o->prior_frame = 0.0f;
    o->frame = 0.0f;
    o->velocity = 0.5f;
    if (o->type == MU_HP_MODEL_GHOST_HORSE) {
        o->scale = 1.0f;
    } else if (o->type == MU_HP_MODEL_ANGEL) {
        o->blend_mesh = 1;
        float base = w->position[0];
        o->position[0] = (float)(rmod(mu_hp_rand(h), 512) - 0x100) + base;
        base = w->position[1];
        o->position[1] = (float)(rmod(mu_hp_rand(h), 512) - 0x100) + base;
        base = w->position[2];
        o->position[2] = (float)(rmod(mu_hp_rand(h), 128) + (MU_HP_MUTATION == 2 ? 0x81 : 0x80)) + base;
    } else if (o->type == MU_HP_MODEL_IMP) {
        float base = w->position[0];
        o->position[0] = (float)(rmod(mu_hp_rand(h), 128) - 0x40) + base;
        base = w->position[1];
        o->position[1] = (float)(rmod(mu_hp_rand(h), 128) - 0x40) + base;
        o->position[2] = w->position[2];
        float ground = h->host.terrain_height ? h->host.terrain_height(h->host.context, o->position[0], o->position[1])
                                              : 0.0f;
        o->position[2] = ground + (float)(mu_hp_rand(h) % 100);
    }
    return 0;
}

int32_t mu_hp_create_bug(mu_helpers *h, const mu_hp_inputs *in, int32_t type, const float position[3], int32_t owner,
                         int32_t subtype)
{
    if (no_bug_world(in->world))
        return -1;
    const mu_hp_owner *w = owner_of(h, owner);
    if (!w || (w->type != MU_HP_MODEL_PLAYER && type != MU_HP_MODEL_ANGEL))
        return -1;
    for (int32_t i = 0; i < MU_HP_BUGS; ++i) {
        mu_hp_object *o = &h->bugs[i];
        int was_live = o->live;
        if (!create_bug_sub(h, in, type, position, owner, o, subtype))
            return was_live ? -1 : i;
    }
    return -1;
}

/* MoveBug 0x00c9d95a (bPet 0). Returns its AL. */
static int move_bug(mu_helpers *h, const mu_hp_inputs *in, mu_hp_object *o)
{
    if (!o->live)
        return 1;
    mu_hp_owner *w = owner_of(h, o->owner);
    if (!w) {   /* native guard: the client dereferences the NULL owner (outside the compared domain) */
        set_live(h, o, 0);
        return 1;
    }
    if (in->scene == 6 && (in->world < 0x52 || in->world > 0x5a) && (!w->live || w->kind != 1)) {
        set_live(h, o, 0);
        return 1;
    }
    mu_hp_fade_alpha(o);
    float range = 0.0f;
    if (!has_model(h, o->type))
        return 0;
    float target[3] = {w->position[0], w->position[1], w->position[2]};
    if (o->type == MU_HP_MODEL_BUTTERFLY) {
        range = 100.0f;
        const float light[3] = {0.4f, 0.6f, 1.0f};
        if (rmod(mu_hp_rand(h), 2) == 0 && h->host.particle)
            h->host.particle(h->host.context, MU_HP_BITMAP_SMOKE, o->position, o->angle, light, 1, 1.0f);
    } else if (o->type == MU_HP_MODEL_ANGEL || o->type == MU_HP_MODEL_IMP) {
        if (o->type == MU_HP_MODEL_ANGEL && o->owner >= 0 && !w->buff_12) {
            const float light[3] = {0.4f, 0.4f, 0.4f};
            for (int32_t k = 0; k < 4; ++k) {
                float p[3];
                p[0] = (float)(rmod(mu_hp_rand(h), 16) - 8);
                p[1] = (float)(rmod(mu_hp_rand(h), 16) - 8);
                p[2] = (float)(rmod(mu_hp_rand(h), 16) - 8);
                p[0] = p[0] + o->position[0];
                p[1] = p[1] + o->position[1];
                p[2] = p[2] + o->position[2];
                if (h->host.particle)
                    h->host.particle(h->host.context, MU_HP_BITMAP_SPARK2, p, o->angle, light, 1, 1.0f);
            }
        }
        range = 150.0f;
    }
    if (h->host.animate)
        h->host.animate(h->host.context, o, o->type, o->velocity);
    if (o->type != MU_HP_MODEL_ANGEL && o->type != MU_HP_MODEL_IMP)
        return 1;
    float d[3];
    d[0] = target[0] - o->position[0];
    d[1] = target[1] - o->position[1];
    d[2] = target[2] - o->position[2];
    (void)d[2];
    float dist2 = d[0] * d[0] + d[1] * d[1];
    float range2 = range * range;
    if (!(dist2 < range2) && dist2 == dist2 && range2 == range2) {   /* comiss; jb: below or unordered skips */
        float heading = mu_create_angle(o->position[0], o->position[1], target[0], target[1]);
        o->angle[2] = mu_turn_angle2(o->angle[2], heading, 20.0f);
    }
    mu_angle_matrix(o->angle, o->matrix);
    float step[3];
    mu_vector_rotate(o->direction, o->matrix, step);
    o->position[0] = o->position[0] + step[0];
    o->position[1] = o->position[1] + step[1];
    o->position[2] = o->position[2] + step[2];
    o->position[2] = (float)(rmod(mu_hp_rand(h), 16) - 8) + o->position[2];
    if (rmod(mu_hp_rand(h), 32) == 0) {
        float speed;
        if (dist2 < range2 || dist2 != dist2 || range2 != range2) {   /* jb 0x00c9e0b4 */
            speed = -(float)(rmod(mu_hp_rand(h), 64) + 0x10) * 0.1f;
            o->angle[2] = (float)(mu_hp_rand(h) % 0x168);
        } else {
            speed = -(float)(rmod(mu_hp_rand(h), 64) + 0x80) * 0.1f;
        }
        o->direction[0] = 0.0f;
        o->direction[1] = speed;
        o->direction[2] = (float)(rmod(mu_hp_rand(h), 64) - 0x20) * 0.1f;
    }
    float top = w->position[2] + 100.0f;
    if (top > o->position[2])   /* comiss top, z; jbe */
        o->direction[2] = o->direction[2] + 1.5f;
    top = w->position[2] + 200.0f;
    if (o->position[2] > top)
        o->direction[2] = o->direction[2] - 1.5f;
    return 1;
}

void mu_hp_move_bugs(mu_helpers *h, const mu_hp_inputs *in)
{
    for (int32_t i = 0; i < MU_HP_BUGS; ++i)
        if (!move_bug(h, in, &h->bugs[i]))
            break;
}

void mu_hp_delete_bug(mu_helpers *h, int32_t owner)
{
    for (int32_t i = 0; i < MU_HP_BUGS; ++i) {
        mu_hp_object *o = &h->bugs[i];
        if (o->live && o->owner == owner && mu_hp_bug_type(o->type))
            set_live(h, o, 0);
    }
}

/* RenderBug 0x00c9e28a(o, 0). */
static void render_bug(mu_helpers *h, const mu_hp_inputs *in, mu_hp_object *o, const mu_hp_render_host *r)
{
    if (!o->live)
        return;
    o->visible = (uint8_t)(r->frustum ? r->frustum(r->context, o->position[0] * 0.01f, o->position[1] * 0.01f, -20.0f)
                                      : 1);
    if (!o->visible)
        return;
    const mu_hp_owner *w = owner_of(h, o->owner);
    if (!w)
        return;   /* native guard (see move_bug) */
    if (w->type != MU_HP_MODEL_PLAYER && o->type != MU_HP_MODEL_ANGEL)
        return;
    if (in->scene == 5)
        o->scale = 1.2f;
    else if (o->type != 0x4a8 && o->type != 0x4aa && o->type != 0x4a9 && o->type != 0x4ab &&
             o->type != MU_HP_MODEL_GHOST_HORSE)
        o->scale = 1.0f;
    int32_t blend = w->buff_12 ? 10 : 0;
    if (r->draw_object)
        r->draw_object(r->context, o, 0, 0, blend, -1, -1);
    float k = (float)(mu_hp_rand(h) % 0x1e + 0x46) * 0.01f;
    if (o->type == MU_HP_MODEL_ANGEL) {
        float light[3] = {k * 0.5f, k * 0.8f, k * 0.6f};
        if (r->sprite)
            r->sprite(r->context, MU_HP_BITMAP_FLARE, o->position, 1.0f, light, o);
    }
}

void mu_hp_render_bugs(mu_helpers *h, const mu_hp_inputs *in, const mu_hp_render_host *r)
{
    for (int32_t i = 0; i < MU_HP_BUGS; ++i)
        render_bug(h, in, &h->bugs[i], r);
}

/* ---------------------------------------------------------------- mounts: classes */

#define S8(v) {v, v, v, v, v, v, v, v, 0.4f, 0.4f, 0.4f, 0.4f, 0.4f, 0.4f, 0.4f, 0.4f}

static const mu_hp_mount_info classes[MU_HP_MOUNT_CLASSES] = {
    {MU_HP_MOUNT_NONE, 0, -1, -1, NULL, NULL, 0.0f, 0, 0, 0, 1.0f, 0, S8(0.4f)},
    /* vtable +8 0x01064b33: actions 0..7 0.34; +0x10 0x01064ba6 */
    {MU_HP_MOUNT_UNIRIA, 0x01ab6bd8, 0x1a02, 0x417, "Rider01", "Bip01 Spine", 20.0f, 1, 0, 1, 1.0f, 0, S8(0.34f)},
    /* 0x01040061: 0..11 0.34; 0x0104011f */
    {MU_HP_MOUNT_DINORANT, 0x01ab6c1c, 0x1a03, 0x473, "Rider02", "Bip01 Spine1", 50.0f, 1, 0, 1, 1.0f, 0,
     {0.34f, 0.34f, 0.34f, 0.34f, 0.34f, 0.34f, 0.34f, 0.34f, 0.34f, 0.34f, 0.34f, 0.34f, 0.4f, 0.4f, 0.4f, 0.4f}},
    /* 0x0103f17e: 0..7 0.34, then 0, 1, 4, 7 0.3 and 8, 9, 10 1.0; 0x0103f324 */
    {MU_HP_MOUNT_DARK_HORSE, 0x01ab6c60, 0x1a04, 0x410, "DarkHorse", "Bip01 Spine1", 30.0f, 1, 0, 1, 1.0f, 0,
     {0.3f, 0.3f, 0.34f, 0.34f, 0.3f, 0.34f, 0.34f, 0.3f, 1.0f, 1.0f, 1.0f, 0.4f, 0.4f, 0.4f, 0.4f, 0.4f}},
    /* 0x01043869: the base 0..7 0.4 (0x0103d420), 2 1.0, 3 0.6; 0x010438fa */
    {MU_HP_MOUNT_FENRIR, 0x01ab6ca4, 0x1a25, 0x4a9, "fenrir_red", "sit_pos_0", 0.0f, 0, 0, 1, 1.0f, 0,
     {0.4f, 0.4f, 1.0f, 0.6f, 0.4f, 0.4f, 0.4f, 0.4f, 0.4f, 0.4f, 0.4f, 0.4f, 0.4f, 0.4f, 0.4f, 0.4f}},
#include "mount_classes.h"
};

const mu_hp_mount_info *mu_hp_mount_class_info(int32_t cls)
{
    if (cls <= MU_HP_MOUNT_NONE || cls >= MU_HP_MOUNT_CLASSES)
        return NULL;
    return &classes[cls];
}

int32_t mu_hp_mount_kind(int32_t item, int32_t state, int item_kind_4f)
{
    int32_t kind = -1;
    if (item == -1 || item == 0xffff) {
        if (0 < state)
            kind = 2;
    } else {
        kind = item_kind_4f ? 1 : 0;
    }
    return kind;
}

int32_t mu_hp_mount_class(int32_t kind, int32_t item, int32_t state)
{
    /* 0x0106cc74: kind -1 -> (-1, -1, -1); 2 -> (2, state, -1); else (kind, item, state). The factory reads
     * +0 (kind) and +4. */
    int32_t key = kind == 2 ? state : (kind == -1 ? -1 : item);
    if (kind == 2) {
        switch (key) {
        case 1: return MU_HP_MOUNT_GIANT_1;
        case 2: return MU_HP_MOUNT_GIANT_2;
        case 3: return MU_HP_MOUNT_GIANT_3;
        default: return MU_HP_MOUNT_NONE;
        }
    }
    for (int32_t c = MU_HP_MOUNT_UNIRIA; c <= MU_HP_MOUNT_DIVINE_HORSE; ++c)
        if (classes[c].item == key)
            return c;
    return MU_HP_MOUNT_NONE;
}

int32_t mu_hp_mount_model(int32_t cls, int32_t state)
{
    if (cls == MU_HP_MOUNT_FENRIR) {   /* 0x0104394e on the descriptor's +8 */
        switch (state) {
        case 0: return 0x4a9;
        case 1: return MU_HP_MUTATION == 1 ? 0x4aa : 0x4a8;
        case 2: return 0x4aa;
        case 4: return 0x4ab;
        default: return 0x4a9;
        }
    }
    const mu_hp_mount_info *i = mu_hp_mount_class_info(cls);
    return i ? i->model : -1;
}

float mu_hp_mount_speed(int32_t cls, int32_t action)
{
    const mu_hp_mount_info *i = mu_hp_mount_class_info(cls);
    if (!i || action < 0 || action >= MU_HP_SPEEDS)
        return 0.4f;
    return i->speed[action];
}

/* ---------------------------------------------------------------- mounts: manager */

mu_hp_mount *mu_hp_mount_find(mu_hp_mounts *m, int32_t key)
{
    for (int32_t i = 0; i < m->count; ++i)
        if (m->list[i].key == key)
            return &m->list[i];
    return NULL;
}

static void mount_remove(mu_hp_mounts *m, int32_t index)
{
    for (int32_t i = index; i + 1 < m->count; ++i)
        m->list[i] = m->list[i + 1];
    --m->count;
    memset(&m->list[m->count], 0, sizeof m->list[m->count]);
}

int mu_hp_mount_init(mu_helpers *h, mu_hp_mount *mount, const mu_hp_inputs *in, int32_t owner, int shadow_world)
{
    (void)in;
    mu_hp_owner *w = owner_of(h, owner);
    if (!w)
        return 0;
    mount->owner = owner;
    mu_hp_object *o = &mount->object;
    mu_hp_object_init(o);   /* operator new + the OBJECT constructor 0x0129e792 (ObjectInit) */
    o->live = 1;
    o->lighting = 1;
    o->flag_0d = 1;
    o->owner = owner;
    o->subtype = 0;
    o->field_68 = -1;
    o->blend_mesh = -1;
    o->blend_light = 1.0f;
    o->lifetime = 0x1e;
    o->alpha_target = 1.0f;
    o->action = 0;
    o->prior_frame = 0.0f;
    o->frame = 0.0f;
    o->velocity = 0.5f;
    mount->shadow = 1;
    o->position[0] = w->position[0];
    o->position[1] = w->position[1];
    o->position[2] = w->position[2];
    /* vtable +0x38: the model */
    o->scale = mu_hp_mount_class_info(mount->cls)->scale;
    mount->model = mu_hp_mount_model(mount->cls, mount->state);
    mount->has_model = (uint8_t)has_model(h, mount->model);
    if (!mount->has_model)
        return 0;
    o->type = mount->model;
    if (mount->cls == MU_HP_MOUNT_DINORANT)
        mount->fly = 0;
    /* the pose builder on the object's bones (host: the first render poses the model) */
    mount->action = 0;   /* +0x30 is 0 from the reset (vtable +4) */
    mu_hp_mount_offset(h, mount);
    if (h->host.rider_reset)
        h->host.rider_reset(h->host.context, owner);
    if (shadow_world)
        mount->shadow_arg = 5;
    return 1;
}

mu_hp_mount *mu_hp_mount_set(mu_helpers *h, mu_hp_mounts *m, const mu_hp_inputs *in, int32_t key, int32_t owner,
                             int32_t item, int32_t state, int item_kind_4f, int shadow_world)
{
    mu_hp_mount *existing = mu_hp_mount_find(m, key);
    if (existing)
        return existing;
    int32_t kind = mu_hp_mount_kind(item, state, item_kind_4f);
    int32_t cls = mu_hp_mount_class(kind, item, state);
    if (cls == MU_HP_MOUNT_NONE || m->count >= MU_HP_MOUNTS)
        return NULL;
    int32_t at = 0;
    while (at < m->count && m->list[at].key < key)
        ++at;
    mu_hp_mount fresh;
    memset(&fresh, 0, sizeof fresh);
    fresh.live = 1;
    fresh.key = key;
    fresh.cls = cls;
    fresh.kind = kind;
    fresh.item = kind == 2 ? state : (kind == -1 ? -1 : item);
    fresh.state = kind == 2 ? -1 : (kind == -1 ? -1 : state);
    fresh.model = -1;
    fresh.owner = -1;
    fresh.object.owner = -1;
    if (!mu_hp_mount_init(h, &fresh, in, owner, shadow_world))
        return NULL;   /* vtable +0x20 destroys it, the factory's object is released */
    for (int32_t i = m->count; i > at; --i)
        m->list[i] = m->list[i - 1];
    m->list[at] = fresh;
    ++m->count;
    return &m->list[at];
}

void mu_hp_mount_reset(mu_helpers *h, mu_hp_mounts *m, int32_t key, int32_t owner)
{
    for (int32_t i = 0; i < m->count; ++i)
        if (m->list[i].key == key) {
            mount_remove(m, i);
            if (h->host.rider_reset)
                h->host.rider_reset(h->host.context, owner);
            return;
        }
}

/* ---------------------------------------------------------------- mounts: move */

void mu_hp_mount_offset(mu_helpers *h, mu_hp_mount *mount)
{
    const mu_hp_mount_info *i = mu_hp_mount_class_info(mount->cls);
    if (!i || !i->bone)
        return;
    static const float zero[3] = {0.0f, 0.0f, 0.0f};
    if (h->host.bone_position)
        h->host.bone_position(h->host.context, &mount->object, mount->model, i->bone, zero, mount->offset);
    if (i->scale_offset) {   /* e.g. 0x01049b79, 0x01057e86: times the object scale, then the lift */
        mount->offset[0] = mount->object.scale * mount->offset[0];
        mount->offset[1] = mount->object.scale * mount->offset[1];
        mount->offset[2] = mount->object.scale * mount->offset[2];
    }
    if (i->has_lift)
        mount->offset[2] = mount->offset[2] + i->lift;
}

int mu_hp_mount_move_base(mu_helpers *h, mu_hp_mount *mount, const mu_hp_inputs *in)
{
    (void)in;
    mu_hp_owner *w = owner_of(h, mount->owner);
    mu_hp_object *o = &mount->object;
    o->position[0] = w->position[0];
    o->position[1] = w->position[1];
    o->position[2] = w->position[2];
    o->angle[0] = w->angle[0];
    o->angle[1] = w->angle[1];
    o->angle[2] = w->angle[2];
    if (w->fade == 1 || w->fade == 2) {
        o->alpha = o->alpha - (MU_HP_MUTATION == 5 ? 0.11f : 0.1f);
        if (0.0f > o->alpha)
            o->alpha = 0.0f;
    } else {
        o->alpha = 1.0f;
    }
    float speed = mu_hp_mount_speed(mount->cls, o->action);
    if (h->host.animate)
        h->host.animate(h->host.context, o, mount->model, speed);
    mu_hp_mount_offset(h, mount);
    mount->riding = (uint8_t)(w->live & (w->hidden == 0));
    if (!mount->riding) {
        o->alpha = 0.0f;
        return 0;
    }
    return 1;
}

static void dust(mu_helpers *h, mu_hp_mount *mount, const mu_hp_inputs *in, const float light[3], int sparse)
{
    /* the shared shape of 0x01064cc2 (Uniria) and 0x01040302 (Dinorant); sparse: Fenrir's 1/3 variant */
    mu_hp_object *o = &mount->object;
    mu_hp_owner *w = owner_of(h, mount->owner);
    if (w->buff_12)
        return;
    float p[3];
    p[0] = (float)(rmod(mu_hp_rand(h), 64) - 0x20) + o->position[0];
    p[1] = (float)(rmod(mu_hp_rand(h), 64) - 0x20) + o->position[1];
    p[2] = (float)(rmod(mu_hp_rand(h), 32) - 0x10) + o->position[2];
    (void)sparse;
    if (in->world == 2) {
        if (h->host.particle)
            h->host.particle(h->host.context, MU_HP_BITMAP_SMOKE, p, o->angle, light, 0, 1.0f);
    } else if (!sparse || (in->world != 10 && in->world != 0x84 && !event_block(in))) {
        if (h->host.particle)
            h->host.particle(h->host.context, MU_HP_BITMAP_SMOKE_B, p, o->angle, light, 0, 1.0f);
    }
}

/* 0x01064cc2 / 0x01040302 */
static void walk_dust(mu_helpers *h, mu_hp_mount *mount, const mu_hp_inputs *in)
{
    if (rmod(mu_hp_rand(h), 2) != 0 || in->world == 10 || in->world == 0x84 || event_block(in))
        return;
    static const float light[3] = {1.0f, 1.0f, 1.0f};
    dust(h, mount, in, light, 0);
}

/* The flying step of Fenrir 0x01043a1c and the Dark Horse 0x0103f5e0 in worlds 10 / 0x84: an effect 0x8012 at a
 * bone, then rand % 5 + 5 smoke puffs around it (the bound is drawn again before every puff). */
static void flying_step(mu_helpers *h, mu_hp_mount *mount, const float base[3])
{
    mu_hp_object *o = &mount->object;
    static const float light[3] = {1.0f, 1.0f, 1.0f};
    float p[3] = {base[0], base[1], base[2]};
    if (h->host.effect)
        h->host.effect(h->host.context, MU_HP_EFFECT_STEP, p, o->angle, light, 1, -1);
    for (int32_t i = 0; i < mu_hp_rand(h) % 5 + 5; ++i) {
        p[0] = (float)(mu_hp_rand(h) % 0x32 - 0x19) + base[0];
        p[1] = (float)(mu_hp_rand(h) % 0x32 - 0x19) + base[1];
        p[2] = ((float)(rmod(mu_hp_rand(h), 16) - 8) + base[2]) - 10.0f;
        if (h->host.particle)
            h->host.particle(h->host.context, MU_HP_BITMAP_SMOKE, p, o->angle, light, 0, 1.0f);
    }
}

static int bone(mu_helpers *h, mu_hp_mount *mount, const char *name, const float v[3], float out[3])
{
    if (!h->host.bone_position)
        return 0;
    return h->host.bone_position(h->host.context, &mount->object, mount->model, name, v, out);
}

/* Fenrir 0x01043a1c */
static void fenrir_step(mu_helpers *h, mu_hp_mount *mount, const mu_hp_inputs *in)
{
    mu_hp_object *o = &mount->object;
    static const float light[3] = {1.0f, 1.0f, 1.0f};
    if (in->world == 10 || in->world == 0x84) {
        float v[3] = {120.0f, 0.0f, 32.0f}, out[3] = {0.0f, 0.0f, 0.0f};
        int hit = 0;
        if (o->frame > 1.0f && 1.2f > o->frame) {
            bone(h, mount, "Bip01 R Hand", v, out);
            out[0] = out[0] + 40.0f;
            hit = 1;
        } else if (o->frame > 4.8f && !(5.0f < o->frame) && o->frame == o->frame) {
            bone(h, mount, "Bip01 R HorseLink", v, out);
            out[0] = out[0] + 40.0f;
            out[2] = out[2] + 700.0f;
            hit = 1;
        }
        if (hit)
            flying_step(h, mount, out);
        return;
    }
    if (mu_hp_rand(h) % 3 != 0)
        return;
    if (world_9b0418(in->world))
        return;
    dust(h, mount, in, light, 1);
}

/* Dark Horse 0x0103f457: the slow dust from "Bone03". */
static void dark_horse_dust(mu_helpers *h, mu_hp_mount *mount, const mu_hp_inputs *in)
{
    mu_hp_owner *w = owner_of(h, mount->owner);
    if (w->buff_12)
        return;
    if (mu_hp_rand(h) % 3 != 0)
        return;
    mu_hp_object *o = &mount->object;
    float v[3] = {50.0f, -4.0f, 0.0f}, p[3] = {0.0f, 0.0f, 0.0f};
    int flag = h->host.dark_horse_flag ? h->host.dark_horse_flag(h->host.context) : 0;
    if (!flag && h->host.bone_vector)
        h->host.bone_vector(h->host.context, o, mount->model, "Bone03", v, p);
    if (h->host.particle)
        h->host.particle(h->host.context, mu_hp_world_16a88ae(in->world) ? MU_HP_BITMAP_SMOKE_C : MU_HP_BITMAP_SMOKE,
                         p, o->angle, o->light, 0, 1.0f);
}

/* Dark Horse 0x0103f5e0: the running dust, or the flying step in worlds 10 / 0x84. */
static void dark_horse_run(mu_helpers *h, mu_hp_mount *mount, const mu_hp_inputs *in)
{
    mu_hp_object *o = &mount->object;
    static const float light[3] = {1.0f, 1.0f, 1.0f};
    if (in->world != 10 && in->world != 0x84 && !event_block(in)) {
        if (rmod(mu_hp_rand(h), 2) != 0 || world_9b0418(in->world))
            return;
        dust(h, mount, in, light, 1);
        return;
    }
    float v[3] = {120.0f, 0.0f, 0.0f}, out[3] = {0.0f, 0.0f, 0.0f};
    v[2] = (float)rmod(mu_hp_rand(h), 64) - 32.0f;
    const char *name = NULL;
    float f = o->frame;
    if (f > 1.0f && 1.2f > f)
        name = "Bip01 Spine1";
    else if (f > 1.1f && 1.4f > f)
        name = "Bone01";
    else if (f > 1.3f && 1.6f > f)
        name = "Bip01 L Forearm";
    else if (f > 1.5f && !(1.8f < f) && f == f)
        name = "Bip01 R Forearm";
    if (!name)
        return;
    bone(h, mount, name, v, out);
    float base[3];
    base[0] = (float)(rmod(mu_hp_rand(h), 16) - 8) + out[0];
    base[1] = (float)(rmod(mu_hp_rand(h), 16) - 8) + out[1];
    base[2] = out[2];
    if (h->host.effect)
        h->host.effect(h->host.context, MU_HP_EFFECT_STEP, base, o->angle, light, 1, -1);
    for (int32_t i = 0; i < mu_hp_rand(h) % 5 + 5; ++i) {
        float p[3];
        p[0] = (float)(mu_hp_rand(h) % 0x32 - 0x19) + out[0];
        p[1] = (float)(mu_hp_rand(h) % 0x32 - 0x19) + out[1];
        p[2] = ((float)(rmod(mu_hp_rand(h), 16) - 8) + out[2]) - 10.0f;
        if (h->host.particle)
            h->host.particle(h->host.context, MU_HP_BITMAP_SMOKE, p, o->angle, light, 0, 1.0f);
    }
}

/* Dark Horse 0x0103fc2e: the ring of joints while c + 0x328d is 1. */
static void dark_horse_ring(mu_helpers *h, mu_hp_mount *mount)
{
    mu_hp_owner *w = owner_of(h, mount->owner);
    if (w->ring != 1)
        return;
    mu_hp_object *o = &mount->object;
    float angle[3] = {0.0f, 0.0f, 0.0f};
    const float v[3] = {0.0f, 50.0f, 0.0f};
    for (int32_t i = 0; i < 4; ++i) {
        angle[2] = angle[2] + 90.0f;
        float m[3][4], p[3];
        mu_angle_matrix(angle, m);
        mu_vector_rotate(v, m, p);
        p[0] = p[0] + o->position[0];
        p[1] = p[1] + o->position[1];
        p[2] = p[2] + o->position[2];
        for (int32_t j = 0; j < 3; ++j)
            if (h->host.joint)
                h->host.joint(h->host.context, MU_HP_JOINT_DARK_HORSE, p, angle, o, 40.0f);
    }
}

int mu_hp_mount_move(mu_helpers *h, mu_hp_mount *mount, const mu_hp_inputs *in)
{
    if (!mu_hp_mount_move_base(h, mount, in))
        return 0;
    switch (mount->cls) {
    case MU_HP_MOUNT_UNIRIA:
        if (mount->action == 2 || mount->action == 3)
            walk_dust(h, mount, in);
        break;
    case MU_HP_MOUNT_DINORANT:
        mount->fly = (uint8_t)(in->world == 8 || in->world == 10 || in->world == 0x84 || event_block(in));
        if (mount->action == 2 || mount->action == 3)
            walk_dust(h, mount, in);
        break;
    case MU_HP_MOUNT_DARK_HORSE:
        if (mount->action == 0 || mount->action == 1) {
            mount->object.flag_41 = 0;
            dark_horse_dust(h, mount, in);
        } else if (mount->action == 2 || mount->action == 3) {
            dark_horse_run(h, mount, in);
        } else {
            dark_horse_dust(h, mount, in);
        }
        dark_horse_ring(h, mount);
        owner_of(h, mount->owner)->ring = 0;
        break;
    case MU_HP_MOUNT_FENRIR:
        if (mount->action == 2 || mount->action == 3)
            fenrir_step(h, mount, in);
        break;
    default:
        break;
    }
    return 1;
}

int32_t mu_hp_action_category(uint16_t action)
{
    if (action >= 1 && action < 0x32)
        return 0;
    if (action >= 0x32 && action < 0x4f)
        return 1;
    if (action >= 0x4f && action < (MU_HP_MUTATION == 4 ? 0x70 : 0x6f))
        return 2;
    if (action >= 0x6f && action < 0x89)
        return 3;
    if (action >= 0x89 && action < 0x133)
        return 4;
    if (action >= 0x133 && action < 0x142)
        return 6;
    if (action >= 0x142 && action < 0x148)
        return 7;
    if (action >= 0x148 && action < 0x186)
        return 8;
    return 0;
}

static void set_action_base(mu_helpers *h, mu_hp_mount *mount, int32_t action)
{
    if (mount->action == action)   /* 0x0103d9eb */
        return;
    mount->action = action;
    if (h->host.set_action)
        h->host.set_action(h->host.context, &mount->object, action);
}

void mu_hp_mount_set_action(mu_helpers *h, mu_hp_mount *mount, int32_t action)
{
    if (mount->cls == MU_HP_MOUNT_DIVINE_HORSE) {   /* 0x010406cf: the idle variant 1 */
        float f = mount->object.frame;
        if (action != 0) {
            set_action_base(h, mount, action);
        } else if (mount->action != 0 || f <= 7.0f) {
            if (mount->action != 1 || 9.0f <= f)
                set_action_base(h, mount, 0);
            else
                set_action_base(h, mount, 1);
        } else if (rmod(mu_hp_rand(h), 16) == 0) {
            set_action_base(h, mount, 1);
        }
        return;
    }
    if (mount->action == action)
        return;
    if (mount->cls == MU_HP_MOUNT_DINORANT && mount->fly) {   /* 0x010401c6 */
        mount->action = action;
        int32_t a = 8;
        if (action == 0 || action == 1)
            a = 8;
        else if (action == 2 || action == 3)
            a = 9;
        else if (action == 4)
            a = 10;
        else if (action == 5)
            a = 0xb;
        if (h->host.set_action)
            h->host.set_action(h->host.context, &mount->object, a);
        return;
    }
    mount->action = action;   /* 0x0103d9eb */
    if (h->host.set_action)
        h->host.set_action(h->host.context, &mount->object, action);
}

void mu_hp_mount_follow_action(mu_helpers *h, mu_hp_mount *mount)
{
    mu_hp_owner *w = owner_of(h, mount->owner);
    int32_t c = w ? mu_hp_action_category(w->action) : 0;
    int32_t a;
    switch (c) {
    case 0: a = 0; break;
    case 1: a = 2; break;
    case 2: a = 3; break;
    case 3: case 4: a = 5; break;
    case 6: a = 4; break;
    case 7: a = 7; break;
    default: a = 0; break;
    }
    mu_hp_mount_set_action(h, mount, a);
}

void mu_hp_mounts_move(mu_helpers *h, mu_hp_mounts *m, const mu_hp_inputs *in)
{
    for (int32_t i = 0; i < m->count; ++i)
        if (mu_hp_mount_move(h, &m->list[i], in))
            mu_hp_mount_follow_action(h, &m->list[i]);
}

/* ---------------------------------------------------------------- mounts: rider */

int mu_hp_mount_lifts(const mu_helpers *h, const mu_hp_mount *mount)
{
    const mu_hp_owner *w = (mount->owner >= 0 && mount->owner < h->owner_count) ? &h->owners[mount->owner] : NULL;
    if (!w || !mount->riding)
        return 0;
    uint16_t a = w->action;
    return (a >= 0x26 && a < 0x32) || (a >= 0x47 && a < 0x4f) || (a >= 0x67 && a < 0x6f) ||
           (a >= 0x118 && a < 0x133) || (a >= 0x13b && a < 0x142);
}

void mu_hp_mount_place_owner(mu_helpers *h, mu_hp_mount *mount, int lift)
{
    mu_hp_owner *w = owner_of(h, mount->owner);
    const float *p = mount->object.position;
    if (lift && mu_hp_mount_lifts(h, mount)) {
        w->position[0] = p[0] + mount->offset[0];
        w->position[1] = p[1] + mount->offset[1];
        w->position[2] = p[2] + mount->offset[2];
        return;
    }
    w->position[0] = p[0];
    w->position[1] = p[1];
    w->position[2] = p[2];
}

void mu_hp_mounts_place_owners(mu_helpers *h, mu_hp_mounts *m, int lift)
{
    for (int32_t i = 0; i < m->count; ++i)
        mu_hp_mount_place_owner(h, &m->list[i], lift);
}

int32_t mu_hp_rider_action(mu_helpers *h, int32_t owner, int32_t how)
{
    mu_hp_owner *w = owner_of(h, owner);
    if (!w)
        return 0;
    int unarmed = w->weapon[0] == -1 && w->weapon[1] == -1;
    int32_t a = 0;
    if (unarmed || (w->safe_zone && w->weapon_kind[0] != 0x5a)) {   /* 0x0103dd6b */
        switch (how) {
        case 0: a = 0x26; break;
        case 1: a = 0x47; break;
        case 2: a = 0x67; break;
        case 6: a = 0x13b; break;
        default: a = 0; break;
        }
    } else {   /* 0x0103ddde */
        int32_t base;
        switch (how) {
        case 0: base = 0x27; break;
        case 1: base = MU_HP_MUTATION == 3 ? 0x49 : 0x48; break;
        case 2: base = 0x68; break;
        case 6: base = 0x13c; break;
        default: base = 0; break;
        }
        if (base) {
            int32_t nibble = (w->class_byte & 0xf);
            if (how == 0 && nibble == 9)
                a = 0x2a;
            else if (how == 0 && w->weapon_54)
                a = 0x2b;
            else if (w->weapon_kind[1] == 0x59)
                a = base + (how == 0 ? 5 : 3);
            else if (w->weapon_kind[0] == 0x5a)
                a = base + (how == 0 ? 6 : 4);
            else if (w->weapon_kind[1] == 0x72)
                a = base + (how == 0 ? 7 : 5);
            else if (w->weapon[0] != -1 && w->weapon[1] != -1)
                a = base + 2;
            else if (w->weapon[0] != -1)
                a = base;
            else if (w->weapon[1] != -1)
                a = base + 1;
        }
    }
    if (a && h->host.set_owner_action)
        h->host.set_owner_action(h->host.context, owner, a);
    return a;
}

/* ---------------------------------------------------------------- mounts: render */

void mu_hp_mount_render(mu_helpers *h, mu_hp_mount *mount, const mu_hp_inputs *in, const mu_hp_render_host *r)
{
    mu_hp_object *o = &mount->object;
    mu_hp_owner *w = owner_of(h, mount->owner);
    int drawn = 0;
    /* vtable +0x14: 0x0103d6d5 */
    if (!o->live) {
        mount->counter = 0;
    } else {
        o->visible = (uint8_t)(r->frustum ? r->frustum(r->context, o->position[0] * 0.01f, o->position[1] * 0.01f,
                                                       -20.0f)
                                          : 1);
        if (!o->visible || w->hidden) {
            mount->counter = 0;
        } else {
            int32_t blend = w->buff_12 ? 10 : 0;
            if (r->draw_body && r->draw_body(r->context, o, 1, blend, 0)) {
                drawn = 1;
            } else {
                ++mount->counter;
                if (mount->counter > 100)
                    mount->counter = MU_HP_MUTATION == 6 ? 0x18 : 0x19;
                if (mount->counter == 1)
                    mu_hp_rider_action(h, mount->owner, 0);
            }
        }
    }
    if (!drawn)
        return;   /* vtable +0x34: nothing for the reconstructed classes */
    /* 0x0103d281: the shadow */
    if (mount->shadow && in->world != 10 && in->world != 0x84 && !world_9b0418(in->world) && !event_block(in)) {
        if (r->alpha_test)
            r->alpha_test(r->context, 1);
        float a;
        if (o->custom_shadow)
            a = mu_hp_world_16a88ae(in->world) ? o->shadow_alpha / 3.0f : o->shadow_alpha;
        else
            a = mu_hp_world_16a88ae(in->world) ? 0.2f : 0.7f;
        if (r->color4)
            r->color4(r->context, 0.0f, 0.0f, 0.0f, a * o->alpha);
        const mu_hp_mount_info *info = mu_hp_mount_class_info(mount->cls);
        int32_t mode = info ? info->shadow_mode : 0;
        if (r->shadow)
            r->shadow(r->context, o, mount->model, (mode == 0 || mode == 3) ? mount->shadow_arg : 0,
                      mode == 2 ? 1 : (mode == 3 ? 2 : 0));
    }
    /* vtable +0x18: 0x0103d830 */
    int32_t blend = w->buff_12 ? 10 : 0;
    if (r->draw_after)
        r->draw_after(r->context, o, 1, blend, 0, -1, -1);
    ++mount->counter;
    if (mount->counter > 100)
        mount->counter = 0x19;
    if (mount->counter == 1)
        mu_hp_rider_action(h, mount->owner, 0);
}

void mu_hp_mounts_render(mu_helpers *h, mu_hp_mounts *m, const mu_hp_inputs *in, const mu_hp_render_host *r)
{
    for (int32_t i = 0; i < m->count; ++i)
        mu_hp_mount_render(h, &m->list[i], in, r);
}

/* ---------------------------------------------------------------- imp, routes */

int mu_hp_imp_link_plan(int32_t helper_type, int32_t scene, int has_pet_item, uint8_t class_byte, int16_t weapon0,
                        mu_hp_imp_link *out)
{
    if (helper_type != MU_HP_MODEL_IMP)
        return 0;
    if (!(scene == 5 || (scene == 6 && !has_pet_item)))
        return 0;
    out->bone = 0x22;
    out->speed = 0.5f;
    int moved = (class_byte & 0xf) == 6 &&
                (weapon0 == 0x1b21 || weapon0 == 0x1b22 || weapon0 == 0x1b23 || weapon0 == 0x1b2f || weapon0 == 0x1b39);
    out->vector[0] = 20.0f;
    out->vector[1] = moved ? -5.0f : 0.0f;
    out->vector[2] = 20.0f;
    out->sprite_vector[0] = 20.0f;
    out->sprite_vector[1] = moved ? -5.0f : 0.0f;
    out->sprite_vector[2] = moved ? 35.0f : 15.0f;
    return 1;
}

int32_t mu_hp_helper_route(int32_t item, uint8_t kind_b)
{
    if (item == MU_HP_ITEM_ANGEL)
        return MU_HP_HELPER_BUG;
    if (item == MU_HP_ITEM_IMP)
        return MU_HP_HELPER_LINK;
    int32_t cls = mu_hp_mount_class(mu_hp_mount_kind(item, 0, kind_b == 0x4f), item, 0);
    if (cls != MU_HP_MOUNT_NONE)
        return MU_HP_HELPER_MOUNT;
    if (kind_b == 0x2d)
        return MU_HP_HELPER_PET;
    return MU_HP_HELPER_NONE;
}
