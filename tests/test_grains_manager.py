from sesboot.salt_utils import GrainsManager
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
        GrainsManager.set_grain('node1', 'ses', {'member': True, 'roles': ['mon']})
        GrainsManager.set_grain('node2', 'ses', {'member': True, 'roles': ['mgr']})
        GrainsManager.set_grain('node3', 'ses', {'member': True, 'roles': ['storage']})
        result = GrainsManager.filter_by('ses:member')
        self.assertEqual(set(result), {'node1', 'node2', 'node3'})
