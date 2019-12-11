import os
from ceph_bootstrap.salt_utils import PillarManager
from . import SaltMockTestCase, SaltClientMock as SaltClient


class PillarManagerTest(SaltMockTestCase):

    def test_pillar_set(self):
        PillarManager.set('ceph-salt:test:enabled', True)
        file_path = os.path.join(SaltClient.pillar_fs_path(), PillarManager.PILLAR_FILE)
        self.assertYamlEqual(file_path, {'ceph-salt': {'test': {'enabled': True}}})
