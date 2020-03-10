from ceph_salt.salt_utils import PillarManager
from ceph_salt.validate.config import validate_config

from . import SaltMockTestCase


class ValidateConfigTest(SaltMockTestCase):

    def setUp(self):
        super(ValidateConfigTest, self).setUp()
        ValidateConfigTest.create_valid_config()

    def tearDown(self):
        super(ValidateConfigTest, self).tearDown()
        PillarManager.reload()

    def test_no_boostrap_minion(self):
        PillarManager.reset('ceph-salt:bootstrap_minion')
        self.assertEqual(validate_config(), "At least one minion must be both 'Mgr' and 'Mon'")

    def test_boostrap_minion_is_not_admin(self):
        PillarManager.set('ceph-salt:minions:admin', [])
        self.assertEqual(validate_config(), "Bootstrap minion must be 'Admin'")

    def test_no_ceph_container_image_path(self):
        PillarManager.reset('ceph-salt:container:images:ceph')
        self.assertEqual(validate_config(), "No Ceph container image path specified in config")

    def test_valid(self):
        self.assertEqual(validate_config(), None)

    @classmethod
    def create_valid_config(cls):
        PillarManager.set('ceph-salt:bootstrap_minion', 'node1.ceph.com')
        PillarManager.set('ceph-salt:minions:admin', 'node1')
        PillarManager.set('ceph-salt:container:images:ceph', 'docker.io/ceph/daemon-base:latest')
