from ceph_salt.salt_utils import PillarManager
from ceph_salt.validate.config import validate_config

from . import SaltMockTestCase


class ValidateConfigTest(SaltMockTestCase):

    def tearDown(self):
        super(ValidateConfigTest, self).tearDown()
        PillarManager.reload()

    def test_no_boostrap_minion(self):
        self.assertEqual(validate_config(), "At least one minion must be both 'Mgr' and 'Mon'")

    def test_valid(self):
        ValidateConfigTest.create_valid_config()
        self.assertEqual(validate_config(), None)

    @classmethod
    def create_valid_config(cls):
        PillarManager.set('ceph-salt:bootstrap_minion', 'node1')
