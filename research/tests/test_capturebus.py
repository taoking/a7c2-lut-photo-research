"""Darwin's zero-based uint8 bus numbers on self-made SDK/OS only."""
import json
import unittest
from unittest.mock import patch

from lutphoto import capturemac as m, captureevidence as e, capturediagnostics as d
from lutphoto import capturesession as s
from lutphoto.capturestore import encoded
from research.tests import test_captureexecution as fixtures
from research.tests.native_sdk_fixture import Core, Device


class BusTests(unittest.TestCase):
    def setUp(self):
        self.case=fixtures.ExecutionTests(methodName='runTest');self.case.setUp()
        self.addCleanup(self.case.doCleanups)

    def locations(self,first=0,service=0,returned=0,ports=(1,2)):
        return (m._Key(m.NORMAL,first,(1,2),4),m._Key(m.SERVICE,service,ports,5),m._Key(m.NORMAL,returned,(1,2),6))

    def make(self,name='zero',*,locations=None,resources=False,**kwargs):
        if resources:
            kwargs['files']=self.case.files|{'resources/'+n:s.c.synthetic_resource(False) for n in s.c.RESOURCE_FILES}
        return self.case.make(name,resources=resources,system_options={'locations':self.locations() if locations is None else locations},**kwargs)

    def test_bus_domain_is_exact_uint8_without_relabeling_and_ports_stay_explicit(self):
        observation={'model':'ILCE-7CM2','serial_source':'sony-get-camera-info','serial_sha256':'11'*32,
                     'pid':m.NORMAL,'bus':0,'ports':[1,2]}
        for bus in (0,1,255):
            self.assertEqual(m._Key(m.NORMAL,bus,(1,2),4).bus,bus)
            self.assertEqual(s._location({'bus':bus,'ports':[1,2]}),(bus,(1,2)))
            self.assertTrue(e._observation(observation|{'bus':bus}))
            self.assertEqual(d.rejected_key_fields(m.NORMAL,bus,(1,2),4),[])
        for bus in (None,True,False,-1,256,1.0,'0'):
            with self.assertRaises(ValueError):m._Key(m.NORMAL,bus,(1,2),4)
            with self.assertRaises(ValueError):s._location({'bus':bus,'ports':[1,2]})
            self.assertFalse(e._observation(observation|{'bus':bus}))
            self.assertEqual(d.rejected_key_fields(m.NORMAL,bus,(1,2),4),['BUS'])
        for ports in ((),(0,),(True,)):
            with self.assertRaises(ValueError):m._Key(m.NORMAL,0,ports,4)
            self.assertFalse(e._observation(observation|{'ports':list(ports)}))
        self.assertFalse(e._observation(observation|{'model':'ILCE-7CR'}))

    def test_zero_bus_full_74_material_cycle_preserves_raw_bus_and_unproven_flags(self):
        result,world,path,receipt=self.make(resources=True)
        self.assertEqual(result['phase'],'EXERCISE_COMPLETE');self.assertEqual(e.exit_code(result),0)
        checkpoint=json.loads((path/e.CHECKPOINT).read_bytes())
        self.assertEqual(len(checkpoint['files']),74)
        for role in ('initial','returned'):
            self.assertEqual(checkpoint['observations'][role]['bus'],0)
            self.assertEqual(checkpoint['observations'][role]['ports'],[1,2])
        self.assertTrue(all(device.bus==0 for device in world.devices))
        self.assertEqual(len(world.host.owners),3);self.assertTrue(all(owner.close_ok for owner in world.host.owners))
        checked=e.inspect_directory(path,receipt=receipt)
        self.assertEqual(checked['classification'],'CONSISTENT_EXERCISE_RECORDS')
        self.assertTrue(all(v is False for v in checked['unproven'].values()))
        self.assertEqual(checked['host_diagnostics'],[])

    def test_zero_and_positive_bus_keep_identical_sdk_action_sequences_and_counters(self):
        zero,w0,p0,_=self.make('zero')
        positive,w1,p1,_=self.make('positive',locations=self.locations(1,1,1))
        self.assertEqual(zero['phase'],positive['phase'])
        self.assertEqual([name for name,_ in w0.trace],[name for name,_ in w1.trace])
        self.assertEqual(w0.counts,w1.counts);self.assertEqual(w0.system.counts,w1.system.counts)
        f0=json.loads((p0/e.CHECKPOINT).read_bytes())['flow'];f1=json.loads((p1/e.CHECKPOINT).read_bytes())['flow']
        self.assertEqual(f0,f1)

    def test_zero_to_positive_service_bus_is_changed_location_and_stops_authentication(self):
        result,world,path,receipt=self.make(locations=self.locations(0,1,0))
        self.assertEqual(result['phase'],'NEEDS_REVIEW');self.assertEqual(world.counts['control'],1)
        self.assertEqual(world.system.service_device.counts.get('control',0),0)
        self.assertEqual(len(world.host.owners),1)
        self.assertEqual(e.inspect_directory(path,receipt=receipt)['classification'],'NEEDS_REVIEW_UNKNOWN')

    def test_changed_return_bus_is_rejected_instead_of_treating_zero_as_wildcard(self):
        result,world,path,receipt=self.make(locations=self.locations(0,0,1))
        self.assertEqual(result['phase'],'NEEDS_REVIEW');self.assertEqual(world.counts['control'],3)
        self.assertEqual(world.system.service_device.counts['control'],2)
        self.assertEqual(len(world.host.owners),2)
        flow=json.loads((path/e.CHECKPOINT).read_bytes())['flow']
        self.assertFalse(flow['normal_identity_matched']);self.assertEqual(flow['identity_queries'],1)
        self.assertEqual(e.inspect_directory(path,receipt=receipt)['classification'],'NEEDS_REVIEW_UNKNOWN')

    def test_changed_ports_and_duplicate_zero_bus_devices_remain_rejected(self):
        result,world,_,_=self.make('ports',locations=self.locations(ports=(1,3)))
        self.assertEqual(result['phase'],'NEEDS_REVIEW');self.assertEqual(world.counts['control'],1)
        original=Core.find
        def duplicate(core,**kwargs):
            for device in original(core,**kwargs):yield device;yield device
        with patch.object(Core,'find',duplicate):result,world,_,_=self.make('duplicate')
        self.assertEqual(result['phase'],'NEEDS_REVIEW');self.assertFalse(world.host.owners)
        self.assertEqual(world.counts.get('control',0),0)
        self.assertEqual(len(world.devices),1);self.assertEqual(world.devices[0].dispose_attempts,1)

    def test_unknown_bus_still_stops_before_media_identity_or_auth(self):
        original=Device.__init__
        def unknown(device,*args):original(device,*args);device.bus=None
        with patch.object(Device,'__init__',unknown):result,world,path,receipt=self.make()
        failure=result['host_diagnostics'][0]['failure']
        self.assertEqual((failure['boundary'],failure['invalid_key_fields']),('KEY_VALIDATE',['BUS']))
        self.assertFalse(world.host.owners);self.assertEqual(world.counts.get('command',0),0)
        self.assertEqual(world.counts.get('control',0),0)
        self.assertEqual(e.inspect_directory(path,receipt=receipt)['classification'],'NEEDS_REVIEW_UNKNOWN')

    def test_historical_bus_rejection_metadata_is_not_upgraded_or_rewritten(self):
        result,_,path,receipt=self.make(native_faults={('find',1):ValueError('own historical failure')})
        result['host_diagnostics'][0]['failure']=d.make_inventory_failure('KEY_VALIDATE',ValueError('own'),['BUS'])
        receipt.write_bytes(encoded(result));before=receipt.read_bytes()
        checked=e.inspect_directory(path,receipt=receipt)
        self.assertEqual(checked['classification'],'NEEDS_REVIEW_UNKNOWN')
        self.assertEqual(checked['host_diagnostics'][0]['failure']['invalid_key_fields'],['BUS'])
        self.assertEqual(receipt.read_bytes(),before);self.assertEqual(checked['materials_hashed'],0)


if __name__=='__main__':unittest.main()
