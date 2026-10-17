"""Portable checks of the reconstructed camera, picking, input and frame
timing (no client bytes). The instruction comparison against the client is
scripts/validate_camera.py; its private run is gated by MU_RECOVERY_INTEGRATION."""
import ctypes
import importlib.util
import math
import os
from pathlib import Path
import struct
import subprocess
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[2]
spec = importlib.util.spec_from_file_location('validate_camera', ROOT / 'scripts/validate_camera.py')
V = importlib.util.module_from_spec(spec)
spec.loader.exec_module(V)


def f32(x):
    return struct.unpack('<f', struct.pack('<f', x))[0]


class CameraTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.lib = V.load_library()

    def view(self, width=1024, height=768):
        view = V.View()
        view.window_width, view.window_height = width, height
        view.fov, view.view_near, view.view_far = 35.0, 20.0, 2000.0
        view.angle[0], view.angle[1], view.angle[2] = -48.5, 0.0, -45.0
        view.position[0], view.position[1], view.position[2] = 12000.0, 13000.0, 850.0
        return view

    def test_viewport_and_perspective_globals(self):
        view = self.view()
        self.lib.mu_view_viewport2(ctypes.byref(view), 10, 20, 1000, 700)
        self.assertEqual(list(view.gl_viewport), [10, 768 - 720, 1000, 700])
        self.lib.mu_view_perspective2(ctypes.byref(view), 35.0, f32(1000 / 700), 20.0, 2800.0)
        self.assertEqual((view.center_x, view.center_y), (510, 370))
        # observed quirk: the flip uses the window WIDTH (0x01cf1624)
        self.assertEqual(view.center_y_flip, 1024 - 370)
        pi = struct.unpack('<f', struct.pack('<I', 0x40490fd8))[0]
        radians = f32(f32(f32(35.0 * 0.5) * pi) / 180.0)
        t = f32(math.tan(radians))
        self.assertEqual(view.perspective_x, f32(f32(t / 500.0) * f32(1000 / 700)))
        self.assertEqual(view.perspective_y, f32(f32(t / 350.0) * f32(768.0 / 700.0)))

    def test_begin_opengl_matrices_and_ray(self):
        view = self.view()
        self.lib.mu_view_begin_opengl(ctypes.byref(view), 0, 0, 640, 480)
        m = list(view.camera_matrix)
        mv = list(view.modelview)
        for r in range(3):
            for c in range(4):
                self.assertEqual(m[r * 4 + c], mv[r + 4 * c])
        # the eye maps to the origin
        eye = [sum(mv[r + 4 * c] * view.position[c] for c in range(3)) + mv[r + 12] for r in range(3)]
        self.assertLess(max(abs(e) for e in eye), 0.05)
        # the centre pixel's ray runs along the view axis (-row 2)
        target = (ctypes.c_float * 3)()
        self.lib.mu_view_create_screen_vector(ctypes.byref(view), 320.0, 240.0, target, 1)
        d = [target[i] - view.mouse_position[i] for i in range(3)]
        length = math.sqrt(sum(x * x for x in d))
        forward = [-m[8], -m[9], -m[10]]
        self.assertAlmostEqual(sum(d[i] / length * forward[i] for i in range(3)), 1.0, places=4)
        self.assertLess(max(abs(view.mouse_position[i] - view.position[i]) for i in range(3)), 0.05)
        # pitch -48.5 looks down: the ray descends
        self.assertLess(d[2], 0)

    def test_projection_inverts_screen_vector(self):
        view = self.view(1728, 1080)
        self.lib.mu_view_begin_opengl(ctypes.byref(view), 0, 0, 640, 480)
        for sx, sy in ((100.0, 50.0), (320.0, 240.0), (600.0, 400.0)):
            target = (ctypes.c_float * 3)()
            self.lib.mu_view_create_screen_vector(ctypes.byref(view), sx, sy, target, 1)
            point = (ctypes.c_float * 3)(*[(view.mouse_position[i] + target[i]) / 2 for i in range(3)])
            fx, fy = ctypes.c_float(), ctypes.c_float()
            self.lib.mu_view_projection_float(ctypes.byref(view), point, ctypes.byref(fx), ctypes.byref(fy))
            self.assertAlmostEqual(fx.value, sx * 1728 / 640, delta=0.05)
            self.assertAlmostEqual(fy.value, sy * 1080 / 480, delta=0.05)
            ix, iy = ctypes.c_int32(), ctypes.c_int32()
            self.lib.mu_view_projection(ctypes.byref(view), point, ctypes.byref(ix), ctypes.byref(iy))
            self.assertLessEqual(abs(ix.value - sx), 1)
            self.assertLessEqual(abs(iy.value - sy), 1)

    def test_collision_and_inside(self):
        quad = [V.fbuf(0, 0, 0), V.fbuf(100, 0, 0), V.fbuf(100, 100, 0), V.fbuf(0, 100, 0)]
        normal = V.fbuf(0, 0, 0)
        self.lib.mu_face_normalize(quad[0], quad[1], quad[2], normal)
        self.assertEqual(list(normal), [0.0, 0.0, 1.0])
        pick = V.Pick(9999999.0, (ctypes.c_float * 3)())
        hit = self.lib.mu_collision_line_face(ctypes.byref(pick), V.fbuf(50, 25, 100), V.fbuf(50, 25, -100), 3,
                                              *quad, normal, 1)
        self.assertEqual(hit, 1)
        self.assertEqual((pick.nearest, list(pick.collision)), (0.5, [50.0, 25.0, 0.0]))
        # equal t is accepted (t <= nearest), a nearer earlier hit wins otherwise
        self.assertEqual(self.lib.mu_collision_line_face(ctypes.byref(pick), V.fbuf(50, 25, 100), V.fbuf(50, 25, -100), 3,
                                                         *quad, normal, 1), 1)
        pick.nearest = 0.25
        self.assertEqual(self.lib.mu_collision_line_face(ctypes.byref(pick), V.fbuf(50, 25, 100), V.fbuf(50, 25, -100), 3,
                                                         *quad, normal, 1), 0)
        # outside the first triangle (v0, v1, v2) but inside the quad
        pick.nearest = 9999999.0
        self.assertEqual(self.lib.mu_collision_line_face(ctypes.byref(pick), V.fbuf(20, 80, 100), V.fbuf(20, 80, -100), 3,
                                                         *quad, normal, 1), 0)
        self.assertEqual(self.lib.mu_collision_line_face(ctypes.byref(pick), V.fbuf(20, 80, 100), V.fbuf(20, 80, -100), 4,
                                                         *quad, normal, 1), 1)
        # InsideTest: a counter-clockwise quad seen from +z passes on axis 4 only
        # with a positive normal component (axis becomes 32, the sign test flips)
        self.assertEqual(self.lib.mu_inside_test(50, 50, 0, 4, *quad, 4, 1.0), 1)
        self.assertEqual(self.lib.mu_inside_test(50, 50, 0, 4, *quad, 4, -1.0), 0)
        self.assertEqual(self.lib.mu_inside_test(150, 50, 0, 4, *quad, 4, 1.0), 0)
        self.assertEqual(self.lib.mu_inside_test(150, 50, 0, 4, *quad, 3, 1.0), 1)  # unknown axis

    def test_terrain_pick_flat(self):
        heights = (ctypes.c_float * 65536)()
        walls = (ctypes.c_uint16 * 65536)()
        terrain = V.Terrain(heights, walls, 1201.0)
        view = self.view()
        view.mouse_position[0], view.mouse_position[1], view.mouse_position[2] = 12000.0, 23000.0, 900.0
        view.mouse_target[0], view.mouse_target[1], view.mouse_target[2] = 12690.0, 23912.0, -900.0
        pick = V.Pick()
        tx, ty = ctypes.c_int32(), ctypes.c_int32()
        lib = self.lib
        self.assertEqual(lib.mu_terrain_pick(ctypes.byref(pick), ctypes.byref(view), ctypes.byref(terrain), 110, 220,
                                             140, 250, ctypes.byref(tx), ctypes.byref(ty)), 1)
        self.assertEqual((tx.value, ty.value), (123, 234))
        self.assertAlmostEqual(pick.collision[0], 12345.0, delta=0.01)
        self.assertAlmostEqual(pick.collision[1], 23456.0, delta=0.01)
        # a water tile uses the water height
        for x, y in ((123, 234), (124, 234), (124, 235), (123, 235)):
            walls[y * 256 + x] = 0x40
        flag, sx, sy = ctypes.c_uint8(), ctypes.c_float(), ctypes.c_float()
        view.mouse_position[2], view.mouse_target[2] = 3000.0, -600.0
        pick.nearest = 9999999.0
        self.assertEqual(lib.mu_terrain_tile_pick(ctypes.byref(pick), ctypes.byref(view), ctypes.byref(terrain), 123.0,
                                                  234.0, 123, 234, 1.0, 1, ctypes.byref(flag), ctypes.byref(sx),
                                                  ctypes.byref(sy)), 1)
        self.assertEqual((flag.value, sx.value, sy.value, pick.collision[2]), (1, 123.0, 234.0, 1201.0))

    def test_key_scan_states(self):
        keys, sample = V.KeyInput(), V.KeySample()
        sample.active = sample.game_foreground = sample.focus_is_foreground = 1
        history = []
        for down in (1, 1, 1, 0, 0):
            sample.down[0x41] = down
            self.lib.mu_key_scan(ctypes.byref(keys), ctypes.byref(sample))
            history.append(keys.state[0x41])
        self.assertEqual(history, [2, 3, 3, 1, 0])
        # Esc/Tab are ignored while no WM_KEYDOWN is pending and focus is the foreground
        sample.down[0x1b] = 1
        self.lib.mu_key_scan(ctypes.byref(keys), ctypes.byref(sample))
        self.assertEqual(keys.state[0x1b], 0)
        sample.key_message_down = 1
        self.lib.mu_key_scan(ctypes.byref(keys), ctypes.byref(sample))
        self.assertEqual(keys.state[0x1b], 2)
        # inactive: no scan and every query false
        sample.active = 0
        self.lib.mu_key_scan(ctypes.byref(keys), ctypes.byref(sample))
        self.assertEqual(keys.state[0x1b], 2)
        self.assertEqual(self.lib.mu_key_is(ctypes.byref(keys), 0, 0x1b, 2), 0)
        self.assertEqual(self.lib.mu_key_is(ctypes.byref(keys), 1, 0x1b, 2), 1)

    def test_mouse_messages(self):
        mouse = V.Mouse()
        mouse.scale_x, mouse.scale_y = 2.7, 2.25
        self.lib.mu_mouse_message(ctypes.byref(mouse), 0x200, 0, (540 << 16) | 864)
        self.assertEqual((mouse.x, mouse.y), (320, 240))
        self.lib.mu_mouse_message(ctypes.byref(mouse), 0x200, 0, (0xffff << 16) | 5000)
        self.assertEqual((mouse.x, mouse.y), (640, 0))
        self.assertEqual(self.lib.mu_mouse_message(ctypes.byref(mouse), 0x20a, 240 << 16, 0), 6.0)
        self.assertEqual(mouse.wheel, 2)
        self.lib.mu_mouse_message(ctypes.byref(mouse), 0x20a, (0x10000 - 120) << 16, 0)
        self.assertEqual(mouse.wheel, -1)
        self.lib.mu_mouse_message(ctypes.byref(mouse), 0x205, 0, 0)  # up without down: no pop
        self.assertEqual(mouse.right_pop, 0)
        self.lib.mu_mouse_message(ctypes.byref(mouse), 0x202, 0, 0)  # left up always pops
        self.assertEqual((mouse.left_pop, mouse.last_click_x), (1, 640))

    def test_frame_clock_runs_logic_at_25_hz(self):
        for work in (10, 33, 55, 120):
            clock = V.Clock()
            now, steps, frames = 100000, 0, 0
            clock.frame_tick = now
            while now < 100000 + 4000:
                self.lib.mu_frame_begin(ctypes.byref(clock))
                while self.lib.mu_frame_logic_step(ctypes.byref(clock)):
                    steps += 1
                self.lib.mu_frame_render_start(ctypes.byref(clock), now)
                now += work
                sleep = self.lib.mu_frame_finish(ctypes.byref(clock))
                now += max(sleep, 0)
                frames += 1
            # 4 s at 25 Hz, minus the time of the last frames still in the accumulator
            self.assertTrue(100 - (2 * work) // 40 - 1 <= steps <= 101, (work, steps))
            if work < 40:
                self.assertIn(frames, range(99, 102))  # capped at 25 FPS

    def world(self):
        c, view = V.WorldCamera(), self.view()
        c.scene, c.world, c.world_fov = 6, 0, 35.0
        c.far_scale[0] = c.far_scale[1] = c.far_scale[2] = 1.0
        c.hero_position[0], c.hero_position[1], c.hero_position[2] = 12850.0, 13050.0, 0.0
        c.hero_tile_x, c.hero_tile_y = 128, 130
        c.distance = c.distance_target = 1000.0
        self.lib.mu_world_camera_enter(ctypes.byref(c), ctypes.byref(view))
        view.fov = 35.0
        return c, view

    def test_world_camera_default_path(self):
        c, view = self.world()
        self.lib.mu_move_main_camera(ctypes.byref(c), ctypes.byref(view), 5000)
        self.assertEqual(list(view.angle), [-48.5, 0.0, -45.0])
        self.assertEqual((view.view_far, view.fov), (2000.0, 35.0))
        # IRotate((0, -1000, 0)) by Rz(-45): the eye sits at +x/-y of the hero
        offset = 1000.0 * math.sin(math.radians(45))
        self.assertAlmostEqual(view.position[0], 12850.0 + offset, delta=0.01)
        self.assertAlmostEqual(view.position[1], 13050.0 - offset, delta=0.01)
        self.assertEqual(view.position[2], 850.0)
        self.assertEqual((c.distance, c.zoom_level), (1000.0, 0))

    def test_wheel_zoom_limits_and_transition(self):
        c, view = self.world()
        self.lib.mu_move_main_camera(ctypes.byref(c), ctypes.byref(view), 5000)
        self.assertEqual(self.lib.mu_world_camera_wheel(ctypes.byref(c), ctypes.byref(view), -1.0, 0), 1)
        self.assertEqual((c.zoom_index, c.fov_to), (2, 35.0))  # clamped at the world FOV
        self.assertEqual(self.lib.mu_world_camera_wheel(ctypes.byref(c), ctypes.byref(view), 1.0, 0), 0)  # mid-transition
        for now in range(5000, 6000, 40):
            self.lib.mu_move_main_camera(ctypes.byref(c), ctypes.byref(view), now)
        self.assertEqual(self.lib.mu_world_camera_wheel(ctypes.byref(c), ctypes.byref(view), 1.0, 0), 1)
        self.assertEqual((c.zoom_index, c.fov_to, c.zoom_timer.duration, c.zoom_timer.done), (1, 30.0, 500, 0))
        for now in range(6000, 7000, 40):
            self.lib.mu_move_main_camera(ctypes.byref(c), ctypes.byref(view), now)
        self.assertEqual(view.fov, 30.0)
        drop = self.lib.mu_camera_lerp_steps(0.0, 30.8, 5, 26)
        self.assertEqual(view.angle[0], f32(-48.5 - drop))
        for now in (7000, 8000):
            self.lib.mu_world_camera_wheel(ctypes.byref(c), ctypes.byref(view), 1.0, 1)
            for t in range(now, now + 1000, 40):
                self.lib.mu_move_main_camera(ctypes.byref(c), ctypes.byref(view), t)
        self.assertEqual((c.zoom_index, view.fov), (1, 30.0))  # min index 1 for the listed hero states


class PrivateCameraValidation(unittest.TestCase):
    @unittest.skipUnless(os.environ.get('MU_RECOVERY_INTEGRATION') == '1', 'private pinned client captures')
    def test_instruction_comparison(self):
        text = os.environ.get('MU_CLIENT_TEXT', str(ROOT / 'evidence/x86-text-capture-09/client-text.bin'))
        data = os.environ.get('MU_IMAGE_DATA',
                              str(ROOT / 'evidence/image-data-run10/data-capture-10/client-image-data.bin'))
        with tempfile.TemporaryDirectory() as folder:
            report = Path(folder) / 'camera.json'
            result = subprocess.run([sys.executable, str(ROOT / 'scripts/validate_camera.py'), '--text', text, '--data',
                                     data, '--cases', '60', '--mutations', '--output', str(report)],
                                    capture_output=True, text=True)
            self.assertEqual(result.returncode, 0, result.stdout[-2000:] + result.stderr[-2000:])
            import json
            parsed = json.loads(report.read_text())
        self.assertTrue(all(r['mismatches'] == 0 for r in parsed['results'].values()))
        self.assertTrue(all(m['mismatches'] > 0 for m in parsed['mutations']))
        self.assertGreaterEqual(len(parsed['results']), 23)


if __name__ == '__main__':
    unittest.main()
