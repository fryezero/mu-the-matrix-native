"""Synthetic publication/regeneration checks, with no game bytes or Wine execution."""
import hashlib
import io
import importlib.util
import json
from pathlib import Path
import re
import struct
import sys
import tempfile
import unittest
from unittest import mock

ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / 'mac-play/hotpatch'
sys.path.insert(0, str(SOURCE))
import generate as hp
import inliner
import peep
sys.path.pop(0)


class GeneratorTests(unittest.TestCase):
    def test_bounds_overlap_and_replacement_size(self):
        hp.validate_records([(16,b'abc',b'xyz'),(19,b'a',b'b')])
        for records in [[(16,b'',b'')],[(16,b'ab',b'x')],[(16,b'ab',b'cd'),(17,b'x',b'y')]]:
            with self.subTest(records=records), self.assertRaises(ValueError):
                hp.validate_records(records)
        with self.assertRaises(ValueError):
            hp.checked(b'changed',{'length':7,'sha256':hashlib.sha256(b'correct').hexdigest()},'fixture')

    def test_private_headers_are_only_locally_generated(self):
        with tempfile.TemporaryDirectory() as td:
            output = Path(td)
            hp.tables(output,[],[],[],bytes(16),False)
            self.assertEqual((output/'private-build.h').read_text(),'#define MUGL_PRIVATE_TABLES 0\n')
            self.assertNotIn('0x12b5bde',(output/'hotpatches.h').read_text())
            hp.tables(output,[('fixture',16,b'abc',b'xyz')],[(32,b'abcde',b'vwxyz')],[],bytes(16),True)
            self.assertEqual((output/'private-build.h').read_text(),'#define MUGL_PRIVATE_TABLES 1\n')
        for name in ('hotpatches.h','inlinesites.h','peepsites.h','orig.h','xform-prologue.h','meshdraw-orig.h'):
            self.assertFalse((SOURCE/name).exists(),name)

    def test_offline_listing_derivation_keeps_direct_calls_only(self):
        config = {'image_base':0x400000,'text_start':0x400002,'text_end':0x400006}
        fake = mock.Mock()
        fake.stdout = io.StringIO('header\n  400002:\tcall   0x400040\n  400007:\tcall   *%eax\n')
        fake.wait.return_value = 0
        with tempfile.TemporaryDirectory() as td, mock.patch.object(hp.subprocess,'Popen',return_value=fake) as popen:
            output = Path(td)
            calls, dis = hp.derive_listings(b'abcdefgh',config,output,'fixture-objdump')
            self.assertEqual((output/'text.bin').read_bytes(),b'cdef')
            self.assertEqual(calls.read_text(),'400002 0x400040\n')
            self.assertEqual(len(dis.read_text().splitlines()),2)
            self.assertIn('--adjust-vma=0x400002',popen.call_args.args[0])

    def test_inline_scanner_uses_hashes_and_checks_call_displacement(self):
        # Authored fixture: an identity helper and one relative call.
        base = 0x4000
        helper = b'\x89\xc8\xc3'
        mem = bytearray(64); mem[32:35] = helper
        mem[0:5] = b'\xe8' + struct.pack('<i',27)
        cfg = {'image_base':base,'helpers':[], 'ret4_address':base+48,
               'inline_templates':{'self':{'length':3,'sha256':hp.digest(helper),'replacement':'89c8909090'}},
               'wrapper_prefix':{'length':11,'sha256':'0'*64},'wrapper_suffix':{'length':2,'sha256':'0'*64}}
        records = inliner.scan(bytes(mem),[(base,base+32)],cfg)
        self.assertEqual(records,[(base,bytes(mem[:5]),b'\x89\xc8\x90\x90\x90')])
        mem[1] ^= 1
        with self.assertRaisesRegex(ValueError,'disagrees'):
            inliner.scan(bytes(mem),[(base,base+32)],cfg)

    def test_peephole_nonzero_base_slice_and_live_flags_rejection(self):
        base = 0x400000
        mem = b'\x6a\x04\x58\x6b\xc0\x00\xc3'
        ins = [(base,'push','$0x4'),(base+2,'pop','%eax'),(base+3,'imul','$0x0,%eax,%eax'),(base+6,'ret','')]
        a, old, new = peep.find_at(ins,0,mem,base)
        self.assertEqual((a,old,new),(base,mem[:6],b'\xb8\0\0\0\0\x90'))
        ins[-1] = (base+6,'je','0x500000')
        self.assertIsNone(peep.find_at(ins,0,mem,base))

    def test_no_credentials_or_process_restart_in_autologin(self):
        text = (ROOT/'mac-play/automation/mu-autologin.sh').read_text()
        self.assertIn('${SUBSERVER_FX:-0.498} ${SUBSERVER_FY:-0.468}',text)   # default MTM-1, env override kept
        self.assertIn('security find-generic-password',text)
        self.assertIn('"$MU_ACCOUNT"',text)
        self.assertNotIn('pkill',text)
        self.assertNotIn('mu-to-server.sh',text)
        self.assertNotIn('set -x',text)


class MeshDrawPublicationTests(unittest.TestCase):
    def setUp(self):
        self.mugl = (SOURCE/'mugl.c').read_text()
        self.meshdraw = (SOURCE/'meshdraw.c').read_text()
        self.targets = json.loads((SOURCE/'targets.json').read_text())

    def test_patch_site_originals_are_hash_pinned_and_header_is_not_source(self):
        sites = {site['name']: site for site in self.targets['meshdraw_sites']}
        self.assertEqual(set(sites),{'md_orig','md_lorig','md_prologue'})
        addresses = {name: int(re.search(rf'#define {macro} (0x[0-9a-fA-F]+)',self.meshdraw).group(1),16)
                     for name,macro in [('md_orig','MD_PATCH'),('md_lorig','MD_LPATCH'),('md_prologue','MD_ENTRY')]}
        for name,site in sites.items():
            with self.subTest(name=name):
                self.assertEqual(site['address'],addresses[name])
                self.assertRegex(site['sha256'],r'^[0-9a-f]{64}$')
                # The C source compares/copies exactly this many bytes of the generated array.
                self.assertRegex(self.meshdraw,rf'{name}, (?:j, )?{site["length"]}\b')
        self.assertIn('#include "meshdraw-orig.h"',self.meshdraw)
        for name in sites:
            self.assertIsNone(re.search(rf'{name}\[[0-9]*\]\s*=',self.meshdraw),'original bytes must stay in the generated header')
        self.assertIsNone(re.search(r'unsigned char[^;=]*\[[^\]]*\]\s*=\s*\{\s*0x',self.meshdraw))

    def test_synthetic_meshdraw_header_has_zero_tables_and_private_one_is_exact_size(self):
        with tempfile.TemporaryDirectory() as td:
            output = Path(td)
            hp.tables(output,[],[],[],bytes(16),False)
            text = (output/'meshdraw-orig.h').read_text()
            for name,length in [('md_orig',7),('md_lorig',6),('md_prologue',10)]:
                self.assertIn(f'static const unsigned char {name}[{length}] = {{'+','.join(['0']*length)+'};',text)
            hp.tables(output,[],[],[],bytes(16),True,[('md_orig',b'\x01\x02')])
            self.assertIn('md_orig[2] = {1,2};',(output/'meshdraw-orig.h').read_text())
        for site in self.targets['meshdraw_sites']:
            with self.assertRaises(ValueError):
                hp.checked(bytes(site['length']),site,site['name'])

    def test_mask_bits_are_documented_and_default_is_their_sum(self):
        default = int(re.search(r'int want = (\d+);',self.mugl).group(1))
        mask = int(re.search(r'want = v & (\d+);',self.mugl).group(1))
        readme = (SOURCE/'README.md').read_text()
        rows = {int(m.group(1)) for m in re.finditer(r'^\| (\d+) \|',readme,re.M)}
        self.assertEqual(rows,{1<<k for k in range(21)})
        self.assertEqual(mask,(1<<21)-1)
        # v7.4: v7.3's 23983 plus quad batching 65536, deferred client-array enables 262144, off-screen culling 524288
        self.assertEqual(default,875951)
        self.assertEqual(default,sum(1<<k for k in (0,1,2,3,5,7,8,10,11,12,14,16,18,19)))
        self.assertEqual(default & 16383,7599,'v7.1/v7.2 builds read 14 bits and see their own default')
        self.assertEqual(default & 65535,23983,'v7.3 reads 16 bits and sees its own default')
        self.assertEqual(default & (8192|64|16|512|32768|131072|1048576),0,'diagnostic and unverified bits stay off by default')
        self.assertIn('md_untested = (mask & 8192) != 0',self.mugl)

    def test_synthetic_build_cannot_apply_game_patches(self):
        self.assertRegex(self.mugl,r'total_frames > 100 && MUGL_PRIVATE_TABLES')
        self.assertIn('0x8000',self.meshdraw)
        self.assertRegex(self.meshdraw,r'if \(mode == 0x8000\) \{ md_fallback\+\+')
        self.assertRegex(self.meshdraw,r'\(flags & 0x420\) == 0x400')

    def test_provenance_records_v72_mugl_and_v71_sources(self):
        provenance = json.loads((SOURCE/'source-provenance.json').read_text())
        self.assertEqual(provenance['mugl/mugl_v72.c']['base_of'],'mac-play/hotpatch/mugl.c')   # v7.3 edits it in place
        self.assertRegex(provenance['mugl/mugl_v72.c']['sha256'],r'^[0-9a-f]{64}$')
        for source,published in [('mugl/meshdraw_v71.c','mac-play/hotpatch/meshdraw.c'),
                                 ('glstride/glstride.c','mac-play/diagnostics/glstride.c')]:
            with self.subTest(source=source):
                self.assertRegex(provenance[source]['sha256'],r'^[0-9a-f]{64}$')
                self.assertEqual(provenance[source]['published_as'],published)
                self.assertTrue((ROOT/published).is_file())
        self.assertRegex(provenance['mugl/mugl_v71.c']['sha256'],r'^[0-9a-f]{64}$')
        self.assertEqual(provenance['mugl/mugl_v71.c']['superseded_by'],'mugl/mugl_v72.c')
        self.assertNotIn('published_as',provenance['mugl/mugl_v71.c'])
        self.assertEqual(provenance['mugl/xform_v70.c']['published_as'],'mac-play/hotpatch/xform.c')  # xform.c is unchanged between v7.0 and v7.2


class V73Tests(unittest.TestCase):
    """v7.3 (MAC-PERF-007): terrain face sorting, render-thread priority, long-frame diagnostics. No game bytes."""

    def setUp(self):
        self.mugl = (SOURCE/'mugl.c').read_text()
        self.terrain = (SOURCE/'terrain.c').read_text()
        self.stall = (SOURCE/'stall.c').read_text()

    def body(self, text, signature):
        start = text.index(signature)
        return text[start:text.index('\n}\n', start)]

    def test_new_sources_are_built_and_carry_no_byte_tables(self):
        make = (SOURCE/'Makefile').read_text()
        self.assertIn('meshdraw.c stall.c terrain.c gpudiag.c ../mumodes/modehook.c',make)
        self.assertIn('#include "stall.c"\n#include "terrain.c"',self.mugl)
        for text in (self.terrain,self.stall):
            self.assertIsNone(re.search(r'unsigned char[^;=]*\[[^\]]*\]\s*=\s*\{\s*0x',text))

    def test_terrain_sort_is_bits_16384_and_32768_and_keyed_by_the_two_face_callers(self):
        self.assertIn('ts_on_flag = (mask & 16384) != 0; ts_verify = (mask & 32768) != 0;',self.mugl)
        self.assertIn('#define TS_OPAQUE_CALLER ((void *)0x016cfab3)',self.terrain)
        self.assertIn('#define TS_ALPHA_CALLER  ((void *)0x016cfb53)',self.terrain)
        begin = self.body(self.terrain,'static int ts_glbegin(GLenum mode, void *ret)')
        self.assertIn('mode == GL_TRIANGLE_FAN && (ret == TS_OPAQUE_CALLER || ret == TS_ALPHA_CALLER)',begin)
        self.assertIn('if (!kind || (ts_active && kind != ts_kind)) { if (ts_active) ts_end(); if (!kind) return 0; }',begin)   # any other block ends the run first
        # every flush (stubs, extensions, swaps) ends an open run before anything else is emitted
        self.assertIn('if (ts_active_flag) ts_end_hook();',self.body(self.mugl,'static void flush_pending(void)'))
        self.assertIn('if (ts_active_flag) ts_end_hook();',self.body(self.mugl,'static void WINAPI mugl_ActiveTexture(GLenum unit)'))

    def test_only_listed_state_calls_become_virtual(self):
        cap = self.body(self.terrain,'static int ts_cap(GLenum cap, int on)')
        self.assertIn('if (cap == GL_BLEND) ts_v.blend = v; else if (cap == GL_CULL_FACE) ts_v.cull = v; else if (cap == GL_ALPHA_TEST) ts_v.atest = v;',cap)
        self.assertIn('else return 0;',cap)
        self.assertIn('target != GL_TEXTURE_2D || active_unit != 0) return 0;',self.terrain)
        for fn in ('mugl_glEnable','mugl_glDisable','mugl_glBindTexture','mugl_glBlendFunc','mugl_glDepthMask','mugl_glAlphaFunc'):
            self.assertRegex(self.mugl,r'void WINAPI '+fn+r'\([^)]*\)\n\{\n    (TR\([^\n]*\n    )?if \(ts_active_flag && ts_')
        self.assertNotIn('ts_depthfunc',self.mugl)   # a depth-function change ends the run

    def test_sorting_preconditions_and_in_place_pairs(self):
        end = self.body(self.terrain,'static void ts_end(void)\n{')
        self.assertIn('ts_f[i].st.dm != 2 || ts_f[i].st.blend != (ts_f[i].alpha ? 2 : 1)',end)   # depth writes on, O blend off, A blend on
        self.assertIn('ts_same_class(&ts_f[*c].st, &ts_f[i].st)',end)
        self.assertIn('paired = !memcmp(ts_store[o->start + k].v, ts_store[f->start + k].v, sizeof(float) * 3)',end)   # A directly after its O
        self.assertIn('ts_f[i].unsafe = 1;',end)
        self.assertIn('} else ts_emit_original();',end)
        self.assertIn('ts_apply(&fin);',end)   # the real state ends as the original stream leaves it
        plan = self.body(self.terrain,'static void ts_emit_plan(void)')
        self.assertIn('ts_emit_sorted(s0, pair);',plan)
        self.assertIn('for (int k = pair; k <= i; k++)',plan)
        facing = self.body(self.terrain,'static long *ts_facing(const Vtx *v, int n)')
        self.assertIn('m[k][2] = c[3];',facing)   # clip-space (x, y, w) determinant, no perspective divide
        self.assertIn('return &ts_st_ambig;',facing)

    def test_verification_compares_both_orders_offscreen(self):
        self.assertIn('ts_verify_px(start, ts_emit_plan, 0, NULL)',self.body(self.terrain,'static void ts_verify_run(const TState *start)'))
        verify = self.body(self.terrain,'static long ts_verify_px(')
        self.assertIn('if (k == 0) ts_emit_original(); else plan();',verify)
        self.assertIn('GL_DEPTH_COMPONENT, GL_UNSIGNED_INT',self.terrain)
        self.assertIn('a[i] != b[i] || a[np + i] != b[np + i]',verify)
        self.assertIn('GL_DEPTH_BITS',self.terrain)   # offscreen depth size follows the window

    def test_render_thread_priority_defaults_to_highest_and_refuses_time_critical(self):
        prio = self.body(self.stall,'static void prio_check(void)')
        self.assertIn('int p = 2;',prio)
        self.assertIn('if (p < -2 || p > 2) p = 0;',prio)
        self.assertIn('SetThreadPriority(GetCurrentThread(), p)',prio)
        self.assertRegex(self.mugl,r'total_frames > 100 && MUGL_PRIVATE_TABLES && mugl_client\) \{[^\n]*prio_check\(\);')

    def test_io_counters_are_opt_in_and_call_the_originals(self):
        install = self.body(self.stall,'static void io_install(HMODULE self)')
        self.assertIn('GetFileAttributesA("C:\\\\mutools\\\\mugl-stall.txt")',install)
        for wrapper,orig in (('io_CreateFileA','sv_cfa('),('io_ReadFile','sv_rf('),('io_TexImage2D','sv_ti(')):
            self.assertIn(orig,self.body(self.stall,'static '+('HANDLE' if 'Create' in wrapper else 'BOOL' if 'Read' in wrapper else 'void')+' WINAPI '+wrapper))
        self.assertIn('io_frame_end(); tr_frame_end();',self.mugl)

    def test_tools_for_stalls_and_zoomed_scene(self):
        stallprof = (ROOT/'mac-play/machprof/stallprof.c').read_text()
        self.assertIn('usage: stallprof <pid> <frame-counter-hex> <seconds>',stallprof)
        self.assertIn('if (tn - t_frame < arm) continue;',stallprof)   # normal frames are not sampled
        self.assertIn('stallprof.c -o build/stallprof',(ROOT/'mac-play/machprof/Makefile').read_text())
        muinput = (ROOT/'mac-play/automation/muinput.c').read_text()
        self.assertIn('MOUSEEVENTF_WHEEL',muinput)
        self.assertIn('!strcmp(c, "kdown")',muinput)


class PrecisePacingTests(unittest.TestCase):
    """v7.2 (MAC-PERF-006): bit 1024 waits on a waitable timer; no new patch site, no original bytes."""

    def setUp(self):
        self.mugl = (SOURCE/'mugl.c').read_text()

    def function_body(self, signature):
        start = self.mugl.index(signature)
        return self.mugl[start:self.mugl.index('\n}\n', start)]

    def test_precise_wait_uses_timer_with_sleep_fallback(self):
        body = self.function_body('static void precise_wait(long long ticks)')
        self.assertIn('CreateWaitableTimerW(NULL, TRUE, NULL)',body)
        self.assertIn('SetWaitableTimer(pace_timer, &due',body)
        self.assertIn('WaitForSingleObject(pace_timer',body)
        self.assertIn('pace_timer_failed',body)
        self.assertRegex(body,r'if \(ms\) real_sleep\(ms\)')   # fallback when the timer is unavailable
        self.assertRegex(body,r'due\.QuadPart = -\(ticks \* 10000000')  # relative 100 ns units, no ms rounding

    def test_sleep_hook_routes_only_positive_render_thread_sleeps_when_pacing(self):
        body = self.function_body('static void WINAPI hook_sleep(DWORD ms)')
        self.assertIn('GetCurrentThreadId() != render_tid) { real_sleep(ms); return; }',body)   # other threads untouched
        self.assertRegex(body,r'if \(pace_fix && ms && qpf\.QuadPart\) \{ pc_other\+\+; precise_wait')
        self.assertRegex(body,r'else real_sleep\(ms\)')
        # the driver's own eligible Sleep is still skipped by return address, before any wait
        self.assertRegex(self.mugl,r'pace_fix && pace_swapped && ret == \(void \*\)0x01852680')

    def test_pacing_remains_bit_1024_and_adds_no_game_bytes(self):
        self.assertEqual(sum(1<<k for k in (0,1,2,3,5,7,8,10,11,12)),7599)
        self.assertIn('pace_fix = (mask & 1024) != 0;',self.mugl)
        self.assertIsNone(re.search(r'unsigned char[^;=]*\[[^\]]*\]\s*=\s*\{\s*0x',self.mugl))
        self.assertIn('pace: logic steps=%u waits=%ld late=%ld restarts=%ld overshoot avg=%.2fms',self.mugl)
        self.assertRegex(self.mugl,r'total_frames > 100 && MUGL_PRIVATE_TABLES')
        # the stats line must not dereference the client's logic counter in the compile-only build
        self.assertIn('MUGL_PRIVATE_TABLES && mugl_client ? *(volatile unsigned *)0x0bdc5eb0 : 0',self.function_body('static void pace_stats(FILE *f)\n{'))

    def test_notes_record_v72_cause_and_unverified_limits(self):
        notes = (SOURCE/'meshdraw-notes.md').read_text()
        section = notes[notes.index('## v7.2: precise waits'):]
        for text in ('0x01cf0fc0','0x0120ee34','0x01852680','not the frontmost Mac app','waitable timer','Not established'):
            self.assertIn(text,section)


class V74Tests(unittest.TestCase):
    """v7.4 (MAC-PERF-008): quad batching, deferred client-array enables, off-screen culling, draw/GPU diagnostics."""

    def setUp(self):
        self.mugl = (SOURCE/'mugl.c').read_text()
        self.terrain = (SOURCE/'terrain.c').read_text()
        self.quads = (SOURCE/'quads.c').read_text()
        self.cull = (SOURCE/'cull.c').read_text()
        self.diag = (SOURCE/'gpudiag.c').read_text()
        self.exports = (SOURCE/'gen_exports.py').read_text()

    def body(self, text, signature):
        start = text.index(signature)
        return text[start:text.index('\n}\n', start)]

    def test_new_sources_are_included_and_carry_no_byte_tables(self):
        self.assertIn('#include "quads.c"',self.terrain)
        self.assertIn('#include "gpudiag.c"\n#include "cull.c"',self.mugl)
        for text in (self.quads,self.cull,self.diag):
            self.assertIsNone(re.search(r'unsigned char[^;=]*\[[^\]]*\]\s*=\s*\{\s*0x',text))
        for name in ('glDrawArrays','glEnableClientState','glDisableClientState','glTranslatef','glMultMatrixf','glLoadMatrixf','glRenderMode'):
            self.assertRegex(self.exports,rf"'{name}':\d+")

    def test_bits(self):
        self.assertIn('qs_on_flag = (mask & 65536) != 0; qs_verify = (mask & 131072) != 0;',self.mugl)
        self.assertIn('cs_lazy = (mask & 262144) != 0',self.mugl)
        self.assertIn('cull_on = (mask & 524288) != 0; cull_verify = (mask & 1048576) != 0;',self.mugl)
        # code patches, pacing and reads of client addresses only in main.exe; test programs get the GL-level bits
        self.assertIn('if (!mugl_client) mask &= ~(1 | 2 | 4 | 8 | 16 | 32 | 64 | 128 | 256 | 512 | 1024 | 8192);',self.mugl)
        self.assertIn('mugl_client = !lstrcmpiA(b, "main.exe");',self.mugl)

    def test_quad_runs_are_keyed_by_the_two_callers_and_smooth_quads(self):
        self.assertIn('#define QS_SPRITE_CALLER ((void *)0x0184c914)',self.terrain)
        self.assertIn('#define QS_GRASS_CALLER  ((void *)0x016d16bf)',self.terrain)
        begin = self.body(self.terrain,'static int ts_glbegin(GLenum mode, void *ret)')
        self.assertIn('mode == GL_QUADS && shade_model == GL_SMOOTH && (ret == QS_SPRITE_CALLER || ret == QS_GRASS_CALLER)',begin)
        self.assertIn('if (!kind || (ts_active && kind != ts_kind)) { if (ts_active) ts_end(); if (!kind) return 0; }',begin)

    def test_a_face_passes_only_faces_it_commutes_with(self):
        plan = self.body(self.quads,'static void qs_plan(void)')
        self.assertIn('if (!memcmp(&b->st, &f->st, sizeof(TState))) { join = k; break; }',plan)
        self.assertIn('if (!(qs_disjoint(f, b) || (f->add && b->all_add))) break;',plan)
        self.assertIn('f->add = qs_add_ok && f->st.blend == 2 && f->st.bs == GL_ONE && f->st.bd == GL_ONE && f->st.dm == 1;',plan)
        start = self.body(self.quads,'static void qs_run_start(void)')
        self.assertIn('eq == 0x8006 && eqa == 0x8006 && !lo',start)   # FUNC_ADD for color and alpha, no logic op
        box = self.body(self.quads,'static void qs_bbox(TFace *f, const double *mvp)')
        self.assertIn('if (qs_depth_clamp) { f->full = 1; continue; }',box)
        self.assertIn('f->x0 = (int)floor(x0) - 2;',box)
        self.assertIn('if (!(q[k][3] > 1e-5)) { f->full = 1; break; }',box)

    def test_quad_verification_compares_both_orders_from_a_window_copy(self):
        end = self.body(self.quads,'static void qs_end_run(const TState *fin)')
        self.assertIn('ts_verify_px(&start, qs_emit_plan, 1, &blit)',end)
        self.assertIn('ts_apply(fin);',end)
        self.assertIn('GL_COLOR_BUFFER_BIT | GL_DEPTH_BUFFER_BIT, GL_NEAREST',self.quads)
        verify = self.body(self.terrain,'static long ts_verify_px(')
        self.assertIn('if (k == 0) ts_emit_original(); else plan();',verify)

    def test_client_array_enables_are_sent_before_anything_that_observes_them(self):
        cs = self.body(self.mugl,'static void cs_set(GLenum a, unsigned char v)')
        self.assertIn('if (cs_lazy && !passthrough && k >= 0 && cs_real[k])',cs)
        self.assertIn('if (cs_dirty && idx >= 0 && idx < (int)sizeof mugl_flags && (mugl_flags[idx] & 2)) cs_apply();',self.mugl)
        self.assertIn('if (cs_dirty && !passthrough) { cs_apply(); update_busy(); }',self.body(self.mugl,'void WINAPI mugl_glBegin(GLenum mode)'))
        self.assertIn('cs_apply();',self.body(self.mugl,'void mugl_sync(void)\n{'))
        self.assertIn('if (pname_client(p)) { flush_pending(); cs_apply(); release_arrays(); }',self.mugl)
        self.assertIn('if (!passthrough) { cs_apply(); cs_forget(); }',self.body(self.mugl,'void WINAPI mugl_glPopClientAttrib(void)'))
        self.assertIn('strstr(exts[i].name, "ClientActiveTexture")) cs_forget();',self.mugl)
        self.assertIn('cs_dirty ||',self.body(self.mugl,'static void update_busy(void)'))

    def test_culling_uses_x_y_and_w_planes_with_margin_and_fresh_matrices(self):
        code = self.body(self.cull,'static unsigned cull_code(const float *p)')
        self.assertIn('double e = 1e-5 * (1.0 + fabs(c[0]) + fabs(c[1]) + fabs(c[3]));',code)
        self.assertNotIn('c[2]',code.split('double e')[1])   # no near/far planes
        batch = self.body(self.cull,'static int cull_batch(const Vtx *v, int n)')
        self.assertIn('if (!cull_code(v[0].v)) return 0;',batch)
        self.assertIn('if (_mm_movemask_ps(bad) & 14) return 0;',batch)
        self.assertIn('if (mx_seen != mx_epoch || mx_always)',batch)
        self.assertIn('if (batch_mode == GL_TRIANGLES && cull_batch(vb, vcount))',self.mugl)
        # the epoch advances after the real matrix call (a flush inside the call re-reads the old matrix)
        self.assertIn('R(glTranslatef, PFNtf)(x, y, z); MX_POST; }',self.cull)
        self.assertIn('R(glPopMatrix, PFN0)();\n    if (!unchanged) mx_epoch++;',self.mugl)
        self.assertIn('mugl_sync_from(-1); R(glLoadIdentity, PFN0)(); matrix_modified(); mx_epoch++;',self.mugl)
        self.assertIn('cull_rendermode_ok = m == GL_RENDER;',self.cull)
        check = self.body(self.cull,'static void cull_check(const Vtx *v, int n)')
        self.assertIn('dq_begin(0x8914',check)
        self.assertIn('R(glPopAttrib, PFN0)();',check)

    def test_diagnostics_are_mode_tokens(self):
        for tok in ('vbo','time','finish','samples','cull'):
            self.assertIn(f'!strcmp(tok, "{tok}")',self.mugl)
        self.assertIn('R(glFinish, PFN0)();',self.diag)
        self.assertIn('0x8914 /* GL_SAMPLES_PASSED */',self.diag)
        diags = (ROOT/'mac-play/diagnostics').glob('gl*.c')
        names = {p.name for p in diags}
        self.assertTrue({'glvbench.c','glcstate.c'} <= names)


if __name__ == '__main__':
    unittest.main()
