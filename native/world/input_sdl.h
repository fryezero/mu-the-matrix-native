/* INPUT-001: shared SDL translation. The router owns GFx refusal and gameplay. */
#ifndef MU_WORLD_INPUT_SDL_H
#define MU_WORLD_INPUT_SDL_H
#include <SDL.h>
#include "mu_world_rt.h"
#include "../gfx/mu_gfx_sdl.h"
static inline int mu_world_rt_sdl_event(mu_world_rt *a, const SDL_Event *e, double scale)
{
    mu_input_msg m = {0};
    switch (e->type) {
    case SDL_KEYDOWN: case SDL_KEYUP:
        m.kind = MU_INPUT_KEY; m.vk = mu_gfx_sdl_vk((int)e->key.keysym.scancode);
        m.down = e->type == SDL_KEYDOWN; m.repeat = e->key.repeat;
        m.mods = ((e->key.keysym.mod & KMOD_SHIFT) ? 1 : 0) |
                 ((e->key.keysym.mod & (KMOD_CTRL | KMOD_GUI)) ? 2 : 0) |
                 ((e->key.keysym.mod & KMOD_ALT) ? 4 : 0);
        /* Esc without an interface retains the shell's scene navigation. */
        if (mu_world_rt_input(a, &m) == 0 && m.vk == 27) return 0;
        return 1;
    case SDL_TEXTINPUT: m.kind = MU_INPUT_TEXT; m.text = e->text.text; break;
    case SDL_TEXTEDITING:
        m.kind = MU_INPUT_COMPOSE; m.text = e->edit.text; m.cursor = e->edit.start; break;
    case SDL_WINDOWEVENT:
        if (e->window.event != SDL_WINDOWEVENT_FOCUS_LOST && e->window.event != SDL_WINDOWEVENT_FOCUS_GAINED)
            return 0;
        m.kind = MU_INPUT_FOCUS; m.down = e->window.event == SDL_WINDOWEVENT_FOCUS_GAINED; break;
    case SDL_MOUSEWHEEL:
        m.kind = MU_INPUT_MESSAGE; m.message = MU_WM_MOUSEWHEEL;
        m.wparam = (uint32_t)(uint16_t)(e->wheel.y * 120) << 16; break;
    case SDL_MOUSEMOTION: case SDL_MOUSEBUTTONDOWN: case SDL_MOUSEBUTTONUP: {
        int x, y;
        m.kind = MU_INPUT_MESSAGE;
        if (e->type == SDL_MOUSEMOTION) { x = e->motion.x; y = e->motion.y; m.message = 0x200u; }
        else {
            x = e->button.x; y = e->button.y;
            int down = e->type == SDL_MOUSEBUTTONDOWN;
            m.message = e->button.button == SDL_BUTTON_LEFT ? (down ? 0x201u : 0x202u) :
                        e->button.button == SDL_BUTTON_RIGHT ? (down ? 0x204u : 0x205u) : (down ? 0x207u : 0x208u);
            m.wparam = down && e->button.button == SDL_BUTTON_LEFT ? 1u : 0u;
        }
        m.lparam = ((uint32_t)(uint16_t)(int)(y * scale) << 16) | (uint16_t)(int)(x * scale);
        break;
    }
    default: return 0;
    }
    (void)mu_world_rt_input(a, &m);
    return 1;
}
#endif
