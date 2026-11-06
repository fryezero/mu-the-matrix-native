/* RENDER-WORLDS-SLOTS2: RenderObjectVisual's outer flicker draw for the class worlds, and the custom render
 * (slot 0x38) / after render (slot 0x3c) of the classes RENDER-WORLDS-SLOTS left. Addresses in
 * docs/research/client-worlds-slots2.md. */
#include "world_visual_slots.h"
#include "world_visual_slots2.h"

int mu_obj_visual_flicker(int32_t world, int has_model)
{
    if (!has_model)
        return 0;   /* 0x017f9790: no model, RenderObjectVisual returns before the draw */
    return world == 57 || world == 58 || (world >= 62 && world <= 64) || (world >= 69 && world <= 72) ||
           (world >= 79 && world <= 82) || (world >= 91 && world <= 96) || world == 100 || world == 101 ||
           (world >= 110 && world <= 140) || (world >= 142 && world <= 145);
}
