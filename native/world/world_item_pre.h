/* RENDER-ITEMS-CALLERS-001: RenderObjDraw 0x0176ce74's visibility flag for the item pre-draw programs
 * (RENDER-ITEMS-002R), as the world callers compute it (world_rt_item_pre).
 *
 * [ebp-0xd] = TestFrustrum2D 0x016ccce7(OBJECT +0x158 x * 0.01, y * 0.01, -20.0), written at 0x0176cef2 (constants
 * 0x01a7df00 = 0.01f and 0x01a7ee00 = -20.0f, single precision). For a worn weapon or wing the OBJECT is the link
 * OBJECT (PART + 0x24) whose position RenderLinkItem 0x012bd910 sets to the item model's BodyOrigin (model +0x78)
 * at 0x012c6302..0x012c637b, before the pose 0x012b5064 (0x012c6478) and the call 0x012c6a83; for a ground item
 * the model origin is the OBJECT position. The in-world scene state is 6 (TestFrustrum2D passes everything only in
 * states 1..4). scripts/validate_item_callers.py compares this with the client. */
#ifndef MU_WORLD_ITEM_PRE_H
#define MU_WORLD_ITEM_PRE_H

#include "../../reconstructed/terrain/terrain.h"

/* 1 when the flag is clear: the item's OBJECT is outside the frame's CreateFrustrum2D polygon by the -20 margin. */
static inline int mu_world_item_out_of_view(const float x2d[4], const float y2d[4], const float origin[3])
{
    const float x = origin[0] * 0.01f, y = origin[1] * 0.01f;
    return !mu_terrain_test_frustum_2d(x2d, y2d, 6, x, y, -20.0f);
}

#endif
