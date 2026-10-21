"""Descriptor-derived unit actions and explicit snapshot stages, all own data."""
import contextlib
from dataclasses import replace
import io
import json
from pathlib import Path
import struct
import subprocess
import sys
import unittest
from unittest.mock import patch

from lutphoto import settingsplan as q
from research.tests import test_slotbundle as fixtures


class SettingsPlanTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        fixtures.SlotBundleTests.setUpClass(); cls.addClassCleanup(fixtures.SlotBundleTests.doClassCleanups)

    def setUp(self):
        self.f = fixtures.SlotBundleTests(methodName='runTest'); self.f.setUp(); self.addCleanup(self.f.doCleanups)
        self.root, self.directory = self.f.root, self.f.directory
        self.v = self.f.f.b
        self.ram = self.root / 'observed-ram.bin'; self.saved = self.root / 'observed-saved.bin'

    def bound(self):
        stack = self.f.f.bound(); stack.enter_context(patch.object(q.program, '_sources', return_value=({}, {})))
        return stack

    def create(self): return self.f.create(self.directory)

    def review(self):
        with self.bound(): return q.review_bundle('own', self.directory)

    def write(self, path, ap=None, cp=None, reverse=False): self.v.write(path, ap=ap, cp=cp, reverse=reverse)

    def target_ap(self):
        # Independent fixture expectation: ST is base zero + eight existing references.
        ap = dict(self.v.ap); ap[0x02cf0101] = replace(ap[0x02cf0101], data=b'\0')
        for i in range(8):
            key = 0x02cf0201 + i * 8; ap[key] = replace(ap[key], data=ap[0x02cf0300 + i].data)
        return ap

    def check(self, stage='target', **kwargs):
        values = dict(ram_path=self.ram, saved_path=self.saved, ram_roles={'AP': 0, 'CP': 1}, saved_roles={'AP': 0, 'CP': 1})
        values.update(kwargs)
        with self.bound(): return q.check_files('own', self.directory, stage=stage, **values)

    def args(self, output=None):
        return ['review', '--archive', 'own', '--directory', str(self.directory), '--output', str(output or self.root / 'settings.private.json')]

    def cli(self, args):
        out, err = io.StringIO(), io.StringIO()
        with self.bound(), contextlib.redirect_stdout(out), contextlib.redirect_stderr(err): code = q.main(args)
        return code, out.getvalue(), err.getvalue()

    def test_nine_upstream_format_units_exact_st_targets_and_complete_decoded_inverse(self):
        self.create(); result = self.review(); plan = result['settings_contract']; fields = plan['fields']
        self.assertEqual(len(fields), 9)
        keys = [0x02cf0101] + [0x02cf0201 + i * 8 for i in range(8)]
        self.assertEqual([r['key'] for r in fields], keys)
        target = self.target_ap()
        for row in fields:
            self.assertEqual(set(row), {'slot', 'key', 'before_ram', 'before_saved', 'after'})
            self.assertEqual(row['slot'], 1); self.assertEqual(row['before_ram'], self.v.ap[row['key']].data.hex())
            self.assertEqual(row['before_saved'], row['before_ram']); self.assertEqual(row['after'], target[row['key']].data.hex())
        self.assertTrue(plan['decoded_complete_map_inverse_checked_offline'])
        self.assertFalse(plan['full_BK4_target_generated']); self.assertEqual(plan['forward']['write_count'], 9)
        self.assertTrue(plan['forward']['save_required']); self.assertTrue(plan['reverse']['save_required'])
        self.assertEqual(result['contract_sha256'], q.w.sha(q.encoded(plan)))
        for key in q.w.boundary(): self.assertFalse(result[key])
        for key in ('complete_settings_transition_verified', 'settings_save_verified', 'independent_property_readback_verified'):
            self.assertFalse(result[key])

    def test_all_program_routes_couple_name_ap_and_order_before_and_after_program(self):
        own = self.f.f.own
        routes=[('stock',own.ap['stock'],own.cp['stock']),('fl23',own.ap['fl23'],own.cp['fl23']),
                ('stock-lut',own.target('stock',32),own.runtime_cp),('legacy',own.legacy_ap,own.legacy_cp)]
        for kind, ap, cp in routes:
            self.f.kwargs['ap_path'].write_bytes(ap); self.f.kwargs['cp_path'].write_bytes(cp)
            self.directory = self.root / kind; self.create(); chain = self.review()['settings_contract']['chain']
            self.assertEqual(chain['source_programs']['AP'], q.w.sha(ap))
            self.assertLess(chain['apply_order'].index('names_mode_1_at_source_AP'), chain['apply_order'].index('program_mode_1'))
            self.assertLess(chain['apply_order'].index('program_mode_1'), chain['apply_order'].index('settings_forward_at_target_programs'))
            self.assertLess(chain['reverse_order'].index('settings_reverse_at_target_programs'), chain['reverse_order'].index('program_mode_2'))
            self.assertLess(chain['reverse_order'].index('program_mode_2'), chain['reverse_order'].index('names_mode_2_at_source_AP'))
            self.assertFalse(chain['executor_enabled'])

    def test_all_six_single_slot_plans_follow_descriptors_and_st_references(self):
        selection = self.f.f.f; entry = dict(selection.selection['slots']['1'])
        for slot in range(1, 7):
            selection.selection['slots'] = {str(slot): entry}; selection.save_selection()
            self.directory = self.root / f'slot-{slot}'; self.create()
            plan = self.review()['settings_contract']
            self.assertEqual(plan['selected_slot'], slot)
            self.assertEqual([row['key'] for row in plan['fields']],
                             [0x02cf0100 + slot] + [0x02cf0200 + i * 8 + slot for i in range(8)])
            self.assertEqual(plan['fields'][0]['after'], '00')
            for i, row in enumerate(plan['fields'][1:]):
                self.assertEqual(row['after'], self.v.ap[0x02cf0300 + i].data.hex())

    def test_zero_program_and_settings_writes_keep_name_task_and_skip_fake_program_modes(self):
        self.f.kwargs['ap_path'].write_bytes(self.f.f.own.target('stock',1)); self.f.kwargs['cp_path'].write_bytes(self.f.f.zero)
        self.write(self.v.ram_path, self.target_ap()); self.write(self.v.saved_path, self.target_ap()); self.create()
        plan = self.review()['settings_contract']; self.assertEqual(plan['forward']['write_count'], 0)
        self.assertFalse(plan['forward']['save_required']); self.assertEqual(plan['reverse']['write_count'], 0)
        self.assertFalse(plan['chain']['program_change_required']); self.assertIn('names_mode_1_at_source_AP', plan['chain']['apply_order'])
        self.assertNotIn('program_mode_1', plan['chain']['apply_order']); self.assertNotIn('program_mode_2', plan['chain']['reverse_order'])
        self.assertTrue(all(v['read_before_required'] and not v['read_after_write_required'] for v in plan['forward']['units']))

    def test_unit_actions_are_exact_inverse_and_enforce_selected_preconditions(self):
        self.create()
        with self.bound(), q.b._open_bundle('own', self.directory) as (p, inputs, review, binding):
            plan, before, after = q._build(p, inputs, review, binding)
            self.assertEqual(q._transition(after, plan['fields'], reverse=True), before)
            self.assertEqual(q._transition(before, plan['fields']), after)
            bad = {state: {chip: dict(rows) for chip, rows in full.items()} for state, full in before.items()}
            bad['ram']['AP'][0x02cf0101] = replace(bad['ram']['AP'][0x02cf0101], data=b'\x09')
            with self.assertRaises(ValueError): q._transition(bad, plan['fields'])
            bad_fields = [dict(row) for row in plan['fields']]; bad_fields[0]['before_saved'] = '09'
            with self.assertRaises(ValueError): q._actions(bad_fields, reverse=True)

    def test_source_target_and_restored_snapshots_check_only_explicit_exact_stage(self):
        self.create(); self.write(self.ram); self.write(self.saved)
        self.assertEqual(self.check('source')['observed_stage'], 'source')
        self.assertEqual(self.check('restored')['observed_stage'], 'restored')
        with self.assertRaises(ValueError): self.check('target')
        self.write(self.ram,self.target_ap()); self.write(self.saved,self.target_ap())
        result = self.check(); self.assertTrue(result['provided_snapshot_scope_checked_offline'])
        self.assertFalse(result['actual_observation_origin_verified']); self.assertFalse(result['restore_verified'])
        with self.assertRaises(ValueError): self.check('source')

    def test_partial_or_unknown_selected_values_on_ram_or_storage_are_rejected(self):
        self.create()
        for path in (self.ram,self.saved): self.write(path,self.target_ap())
        for path in (self.ram,self.saved):
            changed = self.target_ap(); changed[0x02cf0201] = self.v.ap[0x02cf0201]; self.write(path,changed)
            with self.assertRaises(ValueError): self.check()
            changed[0x02cf0201] = replace(changed[0x02cf0201], data=b'\xff'*4); self.write(path,changed)
            with self.assertRaises(ValueError): self.check()
            self.write(path,self.target_ap())

    def test_unselected_and_st_and_all_four_cp_units_are_strictly_preserved(self):
        self.create(); self.write(self.ram,self.target_ap()); self.write(self.saved,self.target_ap())
        for key in (0x02cf0400,0x02cf0300,0x02cf0102):
            changed = self.target_ap(); changed[key] = replace(changed[key],data=bytes(len(changed[key].data)))
            self.write(self.ram,changed)
            with self.assertRaises(ValueError): self.check()
        self.write(self.ram,self.target_ap())
        for key in self.v.cp:
            cp = dict(self.v.cp); cp[key] = replace(cp[key],data=b'CP-BAD')
            self.write(self.saved,self.target_ap(),cp)
            with self.assertRaises(ValueError): self.check()

    def test_selected_unselected_and_cp_attribute_capacity_reset_changes_reject(self):
        self.create(); self.write(self.ram,self.target_ap())
        for key in (0x02cf0101,0x02cf0201,0x02cf0400):
            for change in ('attr','capacity','reset'):
                ap = self.target_ap(); old = ap[key]
                ap[key] = replace(old,attr=1) if change=='attr' else replace(old,max_size=16) if change=='capacity' else replace(old,attr=4,reset_data=b'R'*len(old.data))
                self.write(self.saved,ap)
                with self.assertRaises(ValueError): self.check()
        self.write(self.saved,self.target_ap()); key=next(iter(self.v.cp)); cp=dict(self.v.cp)
        cp[key] = replace(cp[key],max_size=16); self.write(self.saved,self.target_ap(),cp)
        with self.assertRaises(ValueError): self.check()

    def test_diagnostic_value_may_change_but_its_reset_or_layout_cannot(self):
        self.create(); ap=self.target_ap(); key=0x02cf0b6e; ap[key]=replace(ap[key],data=b'\x99\0\0\0')
        self.write(self.ram,ap); self.write(self.saved,ap)
        self.assertFalse(self.check()['observations']['ram']['diagnostic_value_compared'])
        for value in (replace(ap[key],reset_data=b'RRRR'),replace(ap[key],max_size=16)):
            changed=dict(ap);changed[key]=value;self.write(self.ram,changed)
            with self.assertRaises(ValueError):self.check()

    def test_other_runtime_groups_are_counted_without_claiming_preservation(self):
        self.create(); ap=self.target_ap();ap[0x02770015]=replace(ap[0x02770015],data=b'Y')
        self.write(self.ram,ap);self.write(self.saved,self.target_ap());r=self.check()
        self.assertEqual(r['observations']['ram']['outside_scope_changed_properties'],1)
        self.assertEqual(r['observations']['saved']['outside_scope_changed_properties'],0)
        self.assertFalse(r['other_runtime_groups_preservation_verified'])
        self.assertTrue(r['observations']['ram']['outside_scope_is_diagnostic_only'])

    def test_unselected_unsaved_input_is_rejected_before_issuing_a_plan(self):
        ap=dict(self.v.ap);ap[0x02cf0400]=replace(ap[0x02cf0400],data=b'Z');self.write(self.v.saved_path,ap)
        with self.assertRaises(ValueError):self.create()

    def test_plan_metadata_retains_nontrivial_reset_capacity_and_whole_map_inverse(self):
        for key in (0x02cf0101,0x02cf0201,0x02cf0400):
            self.v.ap[key]=replace(self.v.ap[key],attr=4,max_size=16,reset_data=b'R'*len(self.v.ap[key].data))
        self.write(self.v.ram_path);self.write(self.v.saved_path);self.create()
        r=self.review()['settings_contract'];p=r['property_preconditions'][str(0x02cf0101)]['ram']
        self.assertEqual(p,{'attr':4,'bytes':1,'max_size':16,'reset':'52'})
        self.assertTrue(r['decoded_complete_map_inverse_checked_offline'])

    def test_separate_observation_roles_are_explicit_and_can_reverse_image_order(self):
        self.create();self.write(self.ram,self.target_ap());self.write(self.saved,self.target_ap(),reverse=True)
        with self.assertRaises(ValueError):self.check()
        self.assertTrue(self.check(saved_roles={'AP':1,'CP':0})['provided_snapshot_scope_checked_offline'])
        for roles in ({'AP':True,'CP':0},{'AP':0,'CP':0},{}):
            with self.assertRaises(ValueError):self.check(saved_roles=roles)

    def test_inconsistent_worker_contract_or_bundle_target_never_yields_combined_plan(self):
        self.create();metadata=q.names._metadata
        def changed(*args):
            header,c=metadata(*args);return header,{**c,'AP':'ff'*32}
        with patch.object(q.names,'_metadata',side_effect=changed),self.assertRaises(ValueError):self.review()
        name='evidence/settings-scoped.private.json';raw=(self.directory/name).read_bytes();self.f.rehash(name,raw+b' ')
        with patch.object(q,'_build') as build,self.assertRaises(ValueError):self.review()
        build.assert_not_called()

    def test_reader_lock_changes_and_close_uncertainty_block_result(self):
        self.create();chain=q._chain
        def changed(*args):
            import fcntl
            with (self.directory/'session.lock').open('rb') as stream:
                with self.assertRaises(BlockingIOError):fcntl.flock(stream,fcntl.LOCK_EX|fcntl.LOCK_NB)
            path=self.directory/'source/correction.table';path.write_bytes(path.read_bytes());return chain(*args)
        with patch.object(q,'_chain',side_effect=changed),self.assertRaises(ValueError):self.review()
        close=q.b.i._Reader.close
        def failed(reader):close(reader);raise OSError('own close uncertainty')
        with patch.object(q.b.i._Reader,'close',failed):code,out,_=self.cli(self.args())
        self.assertEqual((code,out),(1,''));self.assertFalse((self.root/'settings.private.json').exists())

    def test_cli_private_plan_and_explicit_snapshot_check_summary(self):
        self.create();code,out,err=self.cli(self.args());self.assertEqual((code,err),(0,''))
        path=self.root/'settings.private.json';self.assertEqual(path.stat().st_mode&0o777,0o600)
        self.assertEqual(json.loads(path.read_bytes()),self.review())
        for secret in (str(self.root),'02cf','before_ram','CP-OWN','sha256'):self.assertNotIn(secret,out)
        self.write(self.ram,self.target_ap());self.write(self.saved,self.target_ap())
        args=['check',*self.args(self.root/'checked.json')[1:],'--stage','target','--ram',str(self.ram),'--saved',str(self.saved),
              '--ram-roles','0','1','--saved-roles','0','1']
        self.assertEqual(self.cli(args)[0],0)

    def test_original_bundle_and_observed_snapshots_remain_unchanged(self):
        self.create();self.write(self.ram,self.target_ap());self.write(self.saved,self.target_ap())
        paths=[p for p in self.directory.rglob('*') if p.is_file()]+[self.ram,self.saved]
        def stamp():return {p:(q.w.sha(p.read_bytes()),p.stat().st_ino,p.stat().st_size,p.stat().st_mode,p.stat().st_mtime_ns,p.stat().st_ctime_ns) for p in paths}
        before=stamp();self.review();self.check();self.assertEqual(before,stamp())

    def test_invalid_or_linked_observations_are_rejected_without_a_success_report(self):
        self.create(); self.write(self.ram, self.target_ap()); self.write(self.saved, self.target_ap())
        raw = self.saved.read_bytes(); self.saved.write_bytes(raw[:-10])
        with self.assertRaises(ValueError): self.check()
        self.saved.unlink(); self.saved.symlink_to(self.ram)
        with self.assertRaises(OSError): self.check()

    def test_private_output_rejections_and_short_stdout_preserve_existing_data(self):
        self.create();existing=self.root/'existing';existing.write_bytes(b'KEEP')
        for output in (existing,self.directory/'evidence/new.json',q.w.ROOT/'NO-SETTINGS-REPORT'):
            self.assertEqual(self.cli(self.args(output))[0],1)
        self.assertEqual(existing.read_bytes(),b'KEEP')
        class Short(io.StringIO):
            def write(self,raw):return 0
        with self.bound(),contextlib.redirect_stdout(Short()),contextlib.redirect_stderr(io.StringIO()):
            self.assertEqual(q.main(self.args()),1)
        self.assertTrue((self.root/'settings.private.json').exists())

    def test_no_site_import_help_no_sdk_and_no_enable_resume_or_plan_override(self):
        script="import sys;from lutphoto import settingsplan as q;assert not any(n=='usb' or n.startswith(('usb.','numpy','elftools','ziglang')) for n in sys.modules);q.main(['--help'])"
        done=subprocess.run([sys.executable,'-S','-B','-c',script],capture_output=True,text=True,timeout=15)
        self.assertEqual(done.returncode,0,done.stderr)
        for extra in (['--enable-device'],['--resume'],['--plan','secret'],['--policy','secret']):
            code,out,err=self.cli(self.args()+extra);self.assertEqual((code,out),(2,''));self.assertNotIn('secret',err)
        for stage in (True,'partial','resume',None):
            with self.assertRaises(ValueError):self.check(stage)


if __name__=='__main__':unittest.main()
