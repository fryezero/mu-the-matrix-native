/* SDL2 front end of the GFx layer (NATIVE-GFX-002): turns SDL events into
 * mu_gfx_layer input.  Header-only so that the layer itself stays free of
 * SDL; hosts that already use SDL (mu-world, mu-gfx-window) include it. */
#ifndef MU_GFX_SDL_H
#define MU_GFX_SDL_H

#include <SDL.h>

#include "mu_gfx_layer.h"

/* Windows virtual key of an SDL scancode (USB HID usage numbering), 0 if none. */
static inline int mu_gfx_sdl_vk(int sc)
{
    if (sc >= 4 && sc <= 29) return 0x41 + (sc - 4);       /* A..Z */
    if (sc >= 30 && sc <= 38) return 0x31 + (sc - 30);     /* 1..9 */
    if (sc == 39) return 0x30;
    if (sc >= 58 && sc <= 69) return 0x70 + (sc - 58);     /* F1..F12 */
    switch (sc) {
    case 40: case 88: return 0x0d;                          /* Return, keypad Enter */
    case 41: return 0x1b;
    case 42: return 0x08;
    case 43: return 0x09;
    case 44: return 0x20;
    case 73: return 0x2d;
    case 74: return 0x24;
    case 75: return 0x21;
    case 76: return 0x2e;
    case 77: return 0x23;
    case 78: return 0x22;
    case 79: return 0x27;
    case 80: return 0x25;
    case 81: return 0x28;
    case 82: return 0x26;
    case 224: case 228: return 0x11;
    case 225: case 229: return 0x10;
    case 226: case 230: return 0x12;
    default: return 0;
    }
}

static inline int mu_gfx_sdl_mods(void)
{
    SDL_Keymod m = SDL_GetModState();
    return ((m & KMOD_SHIFT) ? 1 : 0) | ((m & (KMOD_CTRL | KMOD_GUI)) ? 2 : 0) | ((m & KMOD_ALT) ? 4 : 0);
}

/* Feeds one event to the layer; `scale` converts window points to drawable
 * pixels.  Returns 1 when the interface took the event. */
static inline int mu_gfx_sdl_event(mu_gfx_layer *layer, const SDL_Event *e, double scale)
{
    switch (e->type) {
    case SDL_MOUSEMOTION:
        return mu_gfx_layer_mouse(layer, 0, 0, e->motion.x * scale, e->motion.y * scale);
    case SDL_MOUSEBUTTONDOWN:
    case SDL_MOUSEBUTTONUP: {
        int button = e->button.button == SDL_BUTTON_RIGHT ? 1 : e->button.button == SDL_BUTTON_MIDDLE ? 2 : 0;
        return mu_gfx_layer_mouse(layer, e->type == SDL_MOUSEBUTTONDOWN ? 1 : 2, button, e->button.x * scale,
                                  e->button.y * scale);
    }
    case SDL_MOUSEWHEEL: {
        int x, y;
        SDL_GetMouseState(&x, &y);
        return mu_gfx_layer_mouse(layer, 3, e->wheel.y, x * scale, y * scale);
    }
    case SDL_KEYDOWN:
    case SDL_KEYUP: {
        int vk = mu_gfx_sdl_vk((int)e->key.keysym.scancode);
        uint32_t ch = e->key.keysym.sym >= 0x20 && e->key.keysym.sym < 0x7f ? (uint32_t)e->key.keysym.sym : 0;
        return vk ? mu_gfx_layer_key(layer, e->type == SDL_KEYDOWN, vk, ch, mu_gfx_sdl_mods()) : 0;
    }
    case SDL_TEXTINPUT:
        return mu_gfx_layer_text(layer, e->text.text);
    default:
        return 0;
    }
}

#endif
