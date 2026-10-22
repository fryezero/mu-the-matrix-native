"""Offline item services exercise movie callbacks and inventory ownership."""
import unittest
import test_native_mix as mix_test


def act(verb,a=0,b=0):return ['service',verb,a,b]

class ItemServices(unittest.TestCase):
    run_host=mix_test.NativeMix.run_host
    @classmethod
    def setUpClass(cls):
        mix_test.NativeMix.setUpClass.__func__(cls)
        for name in ('PersonalShopProductList','PersonalShopRegister','PersonalShopPurchase'):
            (cls.movies/f'{name}.swf').touch()

    @classmethod
    def tearDownClass(cls):cls.tmp.cleanup()

    def listing(self):
        return [*act('store'),*act('storereg'),*act('storeput',0),*act('storeprice',0,1000),*act('storeconfirm')]

    def test_mix_movie_buttons_reach_game_handler_after_social_integration(self):
        s=self.run_host('mixact','goblin',0,0,'invoke',23,'-','testCall','["onClickGoblinMenu",1,0]',
                        'mixact','mixput',0,0,'invoke',24,'-','testCall','["onClickbtnMix",0]',
                        'mixstate','advance',160,'mixstate')
        self.assertEqual((s[0]['mix_open'],s[0]['pending'],s[1]['pending']),(1,1,0))

    def test_listing_reserves_inventory_through_all_mutation_paths(self):
        s=self.run_host(*self.listing(),'click',0,'npcshop','npcact','sell',0,'storage','npcact','put',0,
                        'mixact','mixopen',0,0,'service','damage',0,1,'servicestate','print')
        self.assertEqual((s[0]['placed'],s[0]['products']),(3,1))
        self.assertEqual(s[1]['held'],-1)

    def test_store_open_close_wait_for_demo_answer(self):
        s=self.run_host(*self.listing(),*act('storeopen'),'servicestate',*act('storeunlist'),
                        'advance',160,'servicestate',*act('storeclose'),'advance',160,*act('storeunlist'),
                        'servicestate')
        self.assertEqual((s[0]['pending'],s[0]['opened'],s[1]['opened'],s[2]['products']),(2,0,1,0))
        self.assertEqual(s[0]['zen'],s[2]['zen'])

    def test_bundle_registration_cancel_releases_only_draft(self):
        s=self.run_host(*act('store'),*act('storereg'),*act('storebundle',1),*act('storeput',0),*act('storeput',1),
                        'servicestate',*act('storecancel'),'servicestate','click',0,'print')
        self.assertEqual((s[0]['draft'],s[1]['draft']),(2,0));self.assertEqual(s[2]['held'],0)

    def test_register_movie_prices_and_cancelled_edit_preserve_listing(self):
        s=self.run_host(*act('store'),*act('storereg'),*act('storeput',0),
                        'invoke',26,'-','testCall','["OnClickOk",100,2,3]','servicestate',
                        *act('storereg'),*act('storecancel'),'servicestate')
        self.assertEqual((s[0]['products'],s[1]['products']),(1,1))

    def test_repair_reply_charges_once_and_rejection_preserves_damage(self):
        s=self.run_host(*act('damage',0,5),*act('selfrepair'),*act('repair',0),'servicestate',
                        *act('damage',0,1),'npcshop','npcact','sell',0,'advance',160,'servicestate',
                        'advance',160,'servicestate',*act('damage',0,4),*act('serviceresult',0),
                        *act('repair',0),'advance',160,'servicestate')
        self.assertEqual(s[0]['durability'][0],5)
        self.assertEqual((s[1]['durability'][0],s[0]['zen']-s[1]['zen']),(100,200))
        self.assertEqual(s[1],s[2]);self.assertEqual((s[3]['durability'][0],s[3]['zen']),(4,s[1]['zen']))

    def test_repair_all_skips_reserved_products(self):
        s=self.run_host(*self.listing(),*act('repairall'),'advance',160,'servicestate')
        self.assertNotEqual(s[0]['durability'][0],100)
        self.assertEqual(s[0]['durability'][1:], [100,100])

    def test_store_purchase_movie_waits_and_rejects_without_charging(self):
        s=self.run_host(*act('storebrowse'),*act('storepurchase'),*act('serviceresult',0),
                        'invoke',27,'-','testCall','["OnClickOk",0]','servicestate',
                        'advance',160,'servicestate',*act('serviceresult',1),*act('storebuy'),
                        'advance',160,'servicestate')
        self.assertEqual((s[0]['pending'],s[1]['placed'],s[2]['placed']),(4,3,4))
        self.assertEqual(s[0]['zen'],s[1]['zen']);self.assertEqual(s[1]['zen']-s[2]['zen'],1000)

    def test_sales_consume_only_listing_and_reuse_slots(self):
        s=self.run_host(*self.listing(),*act('storeopen'),'advance',160,*act('storesale'),
                        'servicestate','advance',160,'servicestate','additem',1,0,1,1,'servicestate')
        self.assertEqual((s[0]['placed'],s[1]['placed'],s[1]['products'],s[2]['placed']),(3,2,0,3))
        self.assertEqual(s[1]['zen']-s[0]['zen'],1000)

    def test_store_typing_routes_to_focused_movie_before_hotkeys(self):
        s=self.run_host(*act('store'),*act('storereg'),*act('storeput',0),
                        'invoke',26,'-','testFocus','[]','text','1000','key',ord('I'),
                        'invoke',26,'-','testStoreSubmit','[]','servicestate','print')
        self.assertEqual(s[0]['products'],1);self.assertEqual(s[1]['inventory_open'],1)

    def test_failed_jewel_script_does_not_change_store_draft(self):
        s=self.run_host('additem',0x1c0e,0,1,1,*act('store'),*act('storereg'),'servicestate',
                        'mixact','jewel',4,1,'servicestate')
        self.assertEqual(s[0],s[1])

    def test_store_sale_releases_trade_capacity_when_backing_array_was_full(self):
        fill=['additem',1,0,1,1]*45
        s=self.run_host(*fill,*self.listing(),*act('storeopen'),'advance',160,
                        'canreceive',1,*act('storesale'),'advance',160,'canreceive',1)
        self.assertEqual([x['can_receive'] for x in s],[0,1])

    def test_full_inventory_purchase_does_not_charge(self):
        s=self.run_host(*(['additem',1,0,1,1]*48),*act('storebrowse'),*act('storepurchase'),
                        'servicestate',*act('storebuy'),'advance',160,'servicestate')
        self.assertEqual((s[0]['placed'],s[0]['zen']),(s[1]['placed'],s[1]['zen']))

    def test_npc_repair_buttons_use_npc_price_and_all_callback(self):
        s=self.run_host('npcshop','invoke',6,'-','testCall','["onClickbtnRepair",0]',
                        'click',0,'servicestate','advance',160,'servicestate',
                        'invoke',6,'-','testCall','["onClickbtnRepairAll",0]','advance',160,'servicestate')
        self.assertEqual(s[0]['pending'],1)
        self.assertEqual((s[1]['durability'][0],s[0]['zen']-s[1]['zen']),(100,100))
        self.assertEqual(s[2]['durability'],[100,100,100])
