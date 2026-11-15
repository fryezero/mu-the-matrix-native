"""Table-driven provider/firewall and original instruction comparisons."""
import os
from pathlib import Path
import random
import sys
import unittest
from native.tests import test_ui_windows4 as harness

ROOT=harness.ROOT

class Windows5(unittest.TestCase):
    HOST='native/tests/ui_windows5_host.c'
    MOVIES=('PersonalShop','ArtifactFrame','DuelWatch')
    EXPECTED='63 inert callbacks'
    run_host=harness.PresentationWindows.run_host
    setUpClass=classmethod(harness.PresentationWindows.setUpClass.__func__)

    def test_production_controllers(self):self.run_host()

    @unittest.skipUnless(harness.PRIVATE,'private original movies')
    def test_original_movies(self):self.run_host(real=True)

    @unittest.skipUnless(harness.PRIVATE,'private original instructions')
    def test_original_routes(self):
        sys.path.insert(0,str(ROOT/'scripts'))
        import pins
        import validate_npc as original
        from native.tests.test_ui_windows3 import OriginalRoutes
        native=self.run_host()
        machine=original.TalkMachine(pins.TEXT.read(),pins.DATA.read())
        for result in (0x30,0x21):
            case=next(c for c in original.talk_cases(random.Random(4),1) if c['packet'][3]==result)
            events=machine.run(case)['events'];trace=''
            for callee,owner,args in events:
                if callee==0xac9c74:trace+='close,'
                elif callee==0xaae767:trace+=f'{owner:x}:toggle,'
                elif callee==0xb54793:trace+=f'{owner:x}:open,'
                elif callee==0xa6ac96:trace+=f'sound{args[0]},'
            self.assertEqual(native[result],trace)
        # Execute the exact artifact callback arm with a manager and getter stub.
        oracle=OriginalRoutes();oracle.text=pins.TEXT.read()
        calls=oracle.machine(0xb97ed1,0xb97ee4,{
            0xac3bf7:lambda u,c:(0x10000700,0),
            0x981423:lambda u,c:(0x10000100,0),
            0xaae767:lambda u,c:(c.append('280:toggle,') or 0,0)})
        self.assertEqual(native[0x280],''.join(calls))

        tail=oracle.machine(0xb548ef,0xb548f7,{
            0xaae420:lambda u,c:(c.append('e0:open,') or 0,0)},
            [(0x1000efe4,0x10000100)])
        self.assertEqual(tail,['e0:open,'])
