from ceph_bootstrap.salt_utils import GrainsManager
from . import SaltMockTestCase


class GrainsManagerTest(SaltMockTestCase):

    def setUp(self):
        super(GrainsManagerTest, self).setUp()
        GrainsManager.set_grain('test', 'key', 'value')

    def test_grains_set(self):
        self.assertGrains('test', 'key', 'value')

    def test_grains_get(self):
        value = GrainsManager.get_grain('test', 'key')
        self.assertDictEqual(value, {'test': 'value'})

    def test_grains_del(self):
        GrainsManager.del_grain('test', 'key')
        self.assertNotInGrains('test', 'key')

    def test_grains_filter_by(self):
        GrainsManager.set_grain('node1', 'ceph-salt', {'member': True,
                                                       'roles': ['mon'],
                                                       'execution': {}})
        GrainsManager.set_grain('node2', 'ceph-salt', {'member': True,
                                                       'roles': ['mgr'],
                                                       'execution': {}})
        GrainsManager.set_grain('node3', 'ceph-salt', {'member': True,
                                                       'roles': ['storage'],
                                                       'execution': {}})
        result = GrainsManager.filter_by('ceph-salt:member')
        self.assertEqual(set(result), {'node1', 'node2', 'node3'})
