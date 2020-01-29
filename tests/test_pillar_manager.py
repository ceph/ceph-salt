import os
from ceph_bootstrap.salt_utils import PillarManager
from . import SaltMockTestCase


class PillarManagerTest(SaltMockTestCase):

    def tearDown(self):
        super(PillarManagerTest, self).tearDown()
        PillarManager.reload()

    def test_pillar_set(self):
        PillarManager.set('ceph-salt:test:enabled', True)
        file_path = os.path.join(self.pillar_fs_path(), PillarManager.PILLAR_FILE)
        self.assertYamlEqual(file_path, {'ceph-salt': {'test': {'enabled': True}}})

    def test_pillar_get(self):
        PillarManager.set('ceph-salt:test', 'some text')
        val = PillarManager.get('ceph-salt:test')
        self.assertEqual(val, 'some text')

    def test_pillar_reset(self):
        PillarManager.set('ceph-salt:test', 'some text')
        val = PillarManager.get('ceph-salt:test')
        self.assertEqual(val, 'some text')
        PillarManager.reset('ceph-salt:test')
        val = PillarManager.get('ceph-salt:test')
        self.assertIsNone(val)
