"""Offline mix/jewel transaction boundaries over the real GFx layer, synthetic movies."""
import json
import os
from pathlib import Path
import subprocess
import tempfile
import unittest
from test_native_gfx2 import build_layer_host


class NativeMix(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.tmp=tempfile.TemporaryDirectory();cls.dir=Path(cls.tmp.name)
        cls.host,cls.lib=build_layer_host(cls.dir)
        cls.movies=cls.dir/'movies';cls.movies.mkdir()
        for name in ('MixInventoryFrame','MixGoblinSel','NpcShop','StorageInven'):(cls.movies/f'{name}.swf').touch()

    @classmethod
    def tearDownClass(cls):cls.tmp.cleanup()

    def run_host(self,*args,order=False):
        result=subprocess.run([str(self.host),str(self.movies),str(self.lib),*map(str,args)],
                              capture_output=True,text=True,timeout=30,
                              env={**os.environ,**({'MU_GFX_HOST_MIX_ORDER':'1'} if order else {})})
        self.assertEqual(result.returncode,0,result.stdout+result.stderr)
        return [json.loads(l) for l in result.stdout.splitlines() if l.startswith('{')]

    def test_mix_waits_for_answer_locks_close_and_charges_once(self):
        s=self.run_host('mixact','mixopen',0,0,'mixact','mixput',0,0,'mixstate',
                        'mixact','mix',0,0,'mixact','mix',0,0,'open',24,'mixstate',
                        'advance',160,'mixstate','advance',160,'mixstate',
                        'mixact','mixtake',0,0,'mixstate')
        self.assertEqual(s[0]['placed'],2)
        self.assertEqual((s[1]['pending'],s[1]['mix_open'],s[1]['zen']),(1,1,s[0]['zen']))
        self.assertEqual((s[2]['pending'],s[2]['mix_items'],s[2]['zen']),(0,1,s[0]['zen']-100))
        self.assertEqual(s[2],s[3])
        self.assertEqual((s[4]['placed'],s[4]['levels'][0][0]),(3,10))

    def test_rejection_preserves_ingredients_and_zen(self):
        s=self.run_host('mixact','mixopen',0,0,'mixact','mixput',0,0,'mixact','mixresult',0,0,'mixstate',
                        'mixact','mix',0,0,'advance',160,'mixstate','open',24,'mixstate')
        self.assertEqual(s[0],s[1])
        self.assertEqual((s[2]['placed'],s[2]['mix_items'],s[2]['mix_open']),(3,0,0))

    def test_failure_consumes_only_mix_ingredients(self):
        s=self.run_host('mixact','mixopen',0,0,'mixact','mixput',0,0,'mixact','mixresult',2,0,'mixstate',
                        'mixact','mix',0,0,'advance',160,'mixstate')
        self.assertEqual((s[1]['placed'],s[1]['mix_items'],s[1]['zen']),(2,0,s[0]['zen']-100))

    def test_jewel_reply_changes_level_and_consumes_source(self):
        s=self.run_host('additem',0x1c0e,0,1,1,'mixact','jewel',4,1,'mixstate','advance',160,'mixstate')
        self.assertEqual(s[0]['pending'],2)
        self.assertEqual(s[0]['levels'][1][0],7)
        self.assertEqual((s[1]['pending'],s[1]['levels'][1][0],s[1]['placed']),(0,8,3))

    def test_life_reply_updates_option_and_rejection_restores_source(self):
        s=self.run_host('additem',0x1c10,0,1,1,'mixact','jewel',4,1,'advance',160,'mixstate',
                        'additem',0x1c10,0,1,1,'mixact','mixresult',0,0,'mixact','jewel',4,1,
                        'advance',160,'mixstate')
        self.assertEqual(s[0]['levels'][1][1],1)
        self.assertEqual((s[1]['levels'][1][1],s[1]['placed']),(1,4))

    def test_pending_jewel_cannot_return_to_world_or_duplicate_on_rejection(self):
        for outcome,placed,level in ((1,3,8),(0,4,7)):
            s=self.run_host('additem',0x1c0e,0,1,1,'mixact','mixresult',outcome,0,
                            'mixact','jewel',4,1,'at',640,300,'advance',160,'mixstate')
            self.assertEqual((s[0]['placed'],s[0]['levels'][1][0]),(placed,level))

    def test_ingredient_slots_can_be_reused_and_escape_closes_pair(self):
        cycles=['mixact','mixput',0,0,'mixact','mixtake',0,0]*40
        s=self.run_host('mixact','mixopen',0,0,*cycles,'mixact','mixput',0,0,'mixstate',
                        'key',27,'mixstate','print')
        self.assertEqual(s[0]['mix_items'],1)
        self.assertEqual((s[1]['mix_open'],s[1]['placed']),(0,3))
        self.assertEqual(s[2]['inventory_open'],0)

    def test_reinserted_ingredients_follow_grid_insertion_order(self):
        s=self.run_host('additem',1,2,1,1,'additem',1,7,1,1,'mixact','mixopen',0,0,
                        'mixact','mixput',0,0,'mixact','mixput',4,0,'mixact','mixtake',0,0,
                        'mixact','mixput',5,0,'mixstate','mixact','mix',0,0,'advance',160,'mixstate',order=True)
        self.assertEqual(s[0]['zen']-s[1]['zen'],70)

    def test_close_with_held_jewel_preserves_every_item_on_rejection(self):
        s=self.run_host('additem',0x1c0e,0,1,1,'mixact','mixopen',0,0,'mixact','mixput',3,0,
                        'click',4,'open',24,'mixstate','print','click',4,
                        'mixact','mixtake',0,0,'open',24,'open',1,'mixact','mixresult',0,0,
                        'mixact','jewel',4,1,'advance',160,'mixstate','print')
        self.assertEqual(s[0]['mix_open'],1)
        self.assertEqual(s[-2]['placed'],4)
        self.assertEqual(len([v for v in s[-1]['cells'] if v>=0]),4)

    def test_scripted_sell_and_vault_put_cannot_mutate_pending_target(self):
        for window,verb in (('npcshop','sell'),('storage','put')):
            s=self.run_host('additem',0x1c0e,0,1,1,window,'mixact','jewel',4,1,
                            'npcact',verb,1,'mixstate','advance',160,'mixstate')
            self.assertEqual((s[0]['placed'],s[1]['placed'],s[1]['levels'][1][0]),(3,3,8))

    def test_vault_round_trip_preserves_life_option(self):
        s=self.run_host('additem',0x1c10,0,1,1,'mixact','jewel',4,1,'advance',160,
                        'storage','npcact','put',1,'npcact','take',3,'mixstate')
        self.assertEqual((s[0]['placed'],s[0]['levels'][1][1]),(3,1))

    def test_consumed_inventory_entries_are_reused_after_many_results(self):
        cycle=['additem',7171,0,1,1,'mixact','mixput',4,0,'mixact','mix',0,0,'advance',160]
        s=self.run_host('mixact','mixopen',0,0,'mixact','mixresult',2,0,*cycle*60,
                        'additem',7171,0,1,1,'mixstate','print')
        self.assertEqual(s[0]['placed'],4)
        self.assertLessEqual(len(s[1]['cells']),4)


if __name__=='__main__':unittest.main()
