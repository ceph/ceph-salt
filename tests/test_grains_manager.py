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
        self.assertEqual(value, 'value')

    def test_grains_del(self):
        GrainsManager.del_grain('test', 'key')
        self.assertNotInGrains('test', 'key')
