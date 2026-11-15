"""Third UI route pass (parameterised opens) and the trigger-root census: synthetic controls, pinned results."""
import os
from pathlib import Path
import struct
import sys
import unittest

ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT/'scripts'))
from survey_ui_indirect import indirect_routes,indirect_manager_roots,self_open_slots
import survey_ui_triggers as triggers
from survey_ui_routes import DATA_BASE


def call(a,target):return b'\xe8'+struct.pack('<i',target-a-5)


class SelfOpenMethods(unittest.TestCase):
    def scan(self,body,lifecycle=(0xaae420,0xaae470)):
        text=bytearray(0x400)
        text[0x100:0x107]=bytes.fromhex('c7 00')+struct.pack('<I',DATA_BASE+0x10)+b'\xc3'   # constructor stores the vtable
        text[0x200:0x200+len(body)]=body
        text[0x300]=0xc3
        table=[0x401300]*20;table[0x4c//4]=0x401200
        data=bytes(0x10)+struct.pack('<20I',*table)+bytes(8)
        return self_open_slots(bytes(text),data,[{'slot':0xe0,'movie':'Authored.swf','constructor':0x401100,'lifecycle':list(lifecycle)}])

    def test_saved_this_reaches_the_base_open(self):
        body=bytes.fromhex('55 8b ec 51 89 4d fc 8b 4d fc')+call(0x40120a,0xaae420)+bytes.fromhex('c9 c3')
        self.assertEqual(self.scan(body),{0xe0:{0x4c:(0x401200,0x40120a,'open')}})

    def test_virtual_open_and_toggle_through_this(self):
        virtual=bytes.fromhex('55 8b ec 51 89 4d fc 8b 4d fc 8b 01 ff 50 40 c9 c3')
        self.assertEqual(self.scan(virtual)[0xe0][0x4c][2],'open')
        toggle=bytes.fromhex('55 8b ec 51 89 4d fc 8b 4d fc')+call(0x40120a,0xaae767)+bytes.fromhex('c9 c3')
        self.assertEqual(self.scan(toggle)[0xe0][0x4c][2],'toggle')

    def test_this_field_store_keeps_the_frame_save(self):
        body=bytes.fromhex('55 8b ec 51 89 4d fc 8b 45 fc c7 40 24 01 00 00 00 8b 4d fc')+call(0x401214,0xaae420)+bytes.fromhex('c9 c3')
        self.assertEqual(sorted(self.scan(body)[0xe0]),[0x4c])

    def test_other_receivers_and_unknown_stores_refuse(self):
        for body in (
            bytes.fromhex('55 8b ec 31 c9')+call(0x401205,0xaae420)+bytes.fromhex('5d c3'),                       # receiver cleared
            bytes.fromhex('55 8b ec 8b 4d 08')+call(0x401206,0xaae420)+bytes.fromhex('5d c3'),                    # another object
            bytes.fromhex('55 8b ec 51 89 4d fc c6 42 24 01 8b 4d fc')+call(0x40120e,0xaae420)+bytes.fromhex('c9 c3'),  # unknown alias
            bytes.fromhex('55 8b ec 51 89 4d fc')+call(0x401207,0x401300)+bytes.fromhex('8b 01 ff 50 40 c9 c3'),  # call clobbers ecx
            bytes.fromhex('55 8b ec 8b 01 ff 50 44 5d c3')):                                                      # close, not open
            self.assertEqual(self.scan(body),{})

    def test_extra_vtable_offset_joins_only_when_named(self):
        text=bytearray(2048);start=0x401100;getter=0x401600
        seq=call(start,0xac3bf7)+b'\x8b\xc8'+call(start+7,getter)+bytes.fromhex('8b c8 8b 00 ff 50 4c c3')
        text[0x100:0x100+len(seq)]=seq
        registry=[{'slot':0xe0,'movie':'Authored.swf','lifecycle':[0xaae420,0xaae470]}]
        args=(bytes(text),b'',registry,{0xac3bf7:[start]},{getter:0xe0})
        self.assertEqual(indirect_routes(*args),[])
        self.assertEqual(indirect_routes(*args,extra={0xe1:{0x4c}}),[])
        self.assertEqual([(r['manager_slot'],r['action']) for r in indirect_routes(*args,extra={0xe0:{0x4c}})],[('0xe0','open')])


class TriggerRoots(unittest.TestCase):
    def setUp(self):
        text=bytearray(0x1000)
        def function(at,body=b''):text[at:at+3+len(body)]=b'\x55\x8b\xec'+body
        function(0x100,call(0x401103,0x401200))          # dispatcher -> handler
        function(0x200,call(0x401203,0x401300))          # handler -> opener
        function(0x300);function(0x400);function(0x500)  # opener, table method, uncalled
        for k in range(9):                               # a chain longer than the bound
            function(0x600+0x40*k,call(0x401603+0x40*k,0x401640+0x40*k) if k<8 else b'')
        function(0x900,call(0x401903,0x401600))
        self.index=triggers.index(bytes(text),struct.pack('<II',0x401400,0x401900))

    def roots(self,site):return triggers.roots(site,*self.index,dispatcher=0x401100)

    def test_three_root_kinds(self):
        self.assertEqual(self.roots(0x401310),{'server-response':[0x401310,0x401203,0x401103]})
        self.assertEqual(self.roots(0x401410),{'table':[0x401410,triggers.DATA_BASE]})
        self.assertEqual(self.roots(0x401510),{'uncalled':[0x401510,0x401500]})

    def test_depth_bound_reports_nothing_instead_of_guessing(self):
        self.assertEqual(self.roots(0x401810),{})
        self.assertIn('table',self.roots(0x401610))


@unittest.skipUnless(os.environ.get('MU_RECOVERY_INTEGRATION')=='1','private pinned text')
class PinnedResults(unittest.TestCase):
    def test_parameterised_opens_and_control(self):
        import pins
        from survey_ui_routes import census,MANAGER
        text=pins.TEXT.read();data=pins.DATA.read();registry,_,direct,getters=census(text,data)
        direct[MANAGER]=sorted(set(direct[MANAGER]+indirect_manager_roots(text,data)))
        found=self_open_slots(text,data,registry)
        self.assertEqual({slot:{o:m[0] for o,m in methods.items()} for slot,methods in found.items()},
                         {0x124:{0x4c:0xb6b656},0x17c:{0x4c:0xbca125}})
        base={(r['site'],r['manager_slot']) for r in indirect_routes(text,data,registry,direct,getters)}
        self.assertEqual(len(base),482)
        # 0x10c is the already-bound control: its +0x4c opener 0x00bedfb4 must rediscover the quest-progress owner.
        extra={slot:set(methods) for slot,methods in found.items()};extra[0x10c]={0x4c}
        third=sorted((r['site'],r['manager_slot'],r['action']) for r in indirect_routes(text,data,registry,direct,getters,extra)
                     if (r['site'],r['manager_slot']) not in base)
        self.assertEqual(third,[
            ('0x00b04ba3','0x124','open'),('0x00be5405','0x124','open'),('0x00be5453','0x124','open'),
            ('0x00be9159','0x10c','open'),('0x00f2b01f','0x10c','open'),('0x01222a4c','0x10c','open'),
            ('0x0126f12c','0x17c','open'),('0x0126f203','0x17c','open')])

    def test_trigger_roots_of_reviewed_rows(self):
        import pins
        index=triggers.index(pins.TEXT.read(),pins.DATA.read())
        for site in (0x124e15e,0x127c567,0x1281ea7,0x126f12c,0xb7c086,0x12805f4):   # MapName x3, Rummy, GoldArcher, SwitchMode
            self.assertEqual(sorted(triggers.roots(site,*index)),['server-response'])
        for site in (0xc0a996,0xbe5405,0xb92e9c,0xc5a4cd,0xbcc99e):                  # input, dialogue, inventory, alarm, mini game
            self.assertEqual(sorted(triggers.roots(site,*index)),['table'])
        committed=(ROOT/'docs/research/ui-window-triggers.csv').read_text().splitlines()
        self.assertEqual(len(committed),137)
        self.assertIn('MapName.swf,route proved + provider complete,0x01281ea7,0x0128136d,server-response,',
                      '\n'.join(committed))
