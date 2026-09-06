import copy
import importlib.util
from pathlib import Path
import stat
from types import SimpleNamespace
import unittest
from unittest.mock import patch

path = Path(__file__).resolve().parents[1] / 'profile-overlay/airootfs/usr/lib/clawos/clawos_install_targets.py'
spec = importlib.util.spec_from_file_location('install_targets', path)
targets = importlib.util.module_from_spec(spec)
spec.loader.exec_module(targets)


class InstallerTargets(unittest.TestCase):
    def setUp(self):
        self.disk = {'path':'/dev/nvme0n1','type':'disk','size':64*1024**3,'ro':False,
                     'model':'Test disk','serial':'test-serial','wwn':'test-wwn','maj:min':'259:0',
                     'mountpoints':[None],'holders':[],'fstype':None,'diskseq':'11'}
        self.boot = {'/dev/sdz','/dev/sdz1'}

    def test_blank_physical_and_virtual_disk_names_are_eligible(self):
        for path in ['/dev/sda','/dev/sdaa','/dev/nvme0n1','/dev/vda','/dev/mmcblk0']:
            disk = {**self.disk,'path':path}
            self.assertIsNone(targets.eligibility(disk,self.boot), path)

    def test_partition_names_are_correct(self):
        self.assertEqual(targets.partitions('/dev/sda'),('/dev/sda1','/dev/sda2'))
        self.assertEqual(targets.partitions('/dev/nvme0n1'),('/dev/nvme0n1p1','/dev/nvme0n1p2'))
        self.assertEqual(targets.partitions('/dev/mmcblk0'),('/dev/mmcblk0p1','/dev/mmcblk0p2'))

    def test_partition_loop_mapper_and_path_traversal_are_rejected(self):
        for path in ['/dev/sda1','/dev/nvme0n1p1','/dev/loop0','/dev/mapper/root','/dev/../sda']:
            self.assertIsNotNone(targets.eligibility({**self.disk,'path':path},self.boot))
            with self.assertRaises(ValueError): targets.partitions(path)

    def test_boot_media_and_unknown_boot_source_are_protected(self):
        self.assertIsNotNone(targets.eligibility(self.disk,set()))
        self.assertIsNotNone(targets.eligibility(self.disk,{self.disk['path']}))
        disk = {**self.disk,'children':[{'path':'/dev/sdz1'}]}
        self.assertEqual(targets.eligibility(disk,self.boot),'Installation boot media')

    def test_mounted_swap_readonly_and_holders_are_protected(self):
        for changes in [{'mountpoints':['/mnt']},{'mountpoints':['[SWAP]']},
                        {'ro':True},{'holders':['dm-0']}]:
            self.assertIsNotNone(targets.eligibility({**self.disk,**changes},self.boot))

    def test_existing_partitions_filesystems_and_small_disks_are_protected(self):
        for changes in [{'children':[{'path':'/dev/nvme0n1p1','mountpoints':[None]}]},
                        {'fstype':'ext4'},{'size':8*1024**3}]:
            self.assertIsNotNone(targets.eligibility({**self.disk,**changes},self.boot))

    def test_identity_changes_when_device_is_replaced(self):
        other = {**self.disk,'serial':'different-device'}
        self.assertNotEqual(targets.identity(self.disk),targets.identity(other))

    def test_same_model_hotplug_replacement_changes_kernel_generation(self):
        other = {**self.disk,'diskseq':'12'}
        self.assertNotEqual(targets.identity(self.disk),targets.identity(other))
        with patch.object(targets,'inventory',return_value=([other],self.boot)):
            with self.assertRaisesRegex(ValueError,'identity changed'):
                targets.check_identity(self.disk['path'],targets.identity(self.disk))

    def validate(self, disk_id=None, confirmation=None, signatures='{"signatures":[]}'):
        with patch.object(targets,'inventory',return_value=([copy.deepcopy(self.disk)],self.boot)), \
             patch.object(targets.os,'stat',return_value=SimpleNamespace(st_mode=stat.S_IFBLK)), \
             patch.object(targets,'run',return_value=signatures):
            return targets.validate(self.disk['path'],disk_id or targets.identity(self.disk),
                                    confirmation or 'ERASE-'+self.disk['path'])

    def test_readonly_plan_for_nvme_has_exact_identity(self):
        plan = self.validate()
        self.assertEqual(plan['esp'],'/dev/nvme0n1p1')
        self.assertEqual(plan['diskId'],targets.identity(self.disk))

    def test_stale_identity_and_wrong_confirmation_are_rejected(self):
        with self.assertRaisesRegex(ValueError,'identity changed'): self.validate(disk_id='stale')
        with self.assertRaisesRegex(ValueError,'confirmation'): self.validate(confirmation='ERASE-/dev/sda')

    def test_raw_filesystem_signature_is_rejected_even_without_partitions(self):
        with self.assertRaisesRegex(ValueError,'signatures'):
            self.validate(signatures='{"signatures":[{"type":"ext4"}]}')


if __name__ == '__main__': unittest.main()
