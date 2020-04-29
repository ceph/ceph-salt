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

    def test_no_bootstrap_minion(self):
        PillarManager.reset('ceph-salt:bootstrap_minion')
        self.assertEqual(validate_config([]), "No bootstrap minion specified in config")
        self.assertEqual(validate_config([{'hostname': 'node1'}]), None)

    def test_bootstrap_minion_is_not_admin(self):
        PillarManager.set('ceph-salt:minions:admin', [])
        self.assertEqual(validate_config([]), "Bootstrap minion must be 'Admin'")
        self.assertEqual(validate_config([{'hostname': 'node1'}]), None)

    def test_no_bootstrap_mon_ip(self):
        PillarManager.reset('ceph-salt:bootstrap_mon_ip')
        self.assertEqual(validate_config([]), "No bootstrap Mon IP specified in config")

    def test_loopback_bootstrap_mon_ip(self):
        PillarManager.set('ceph-salt:bootstrap_mon_ip', '127.0.0.1')
        self.assertEqual(validate_config([]), "Mon IP cannot be the loopback interface IP")

    def test_no_time_server_host(self):
        PillarManager.reset('ceph-salt:time_server:server_host')
        self.assertEqual(validate_config([]), "No time server host specified in config")

    def test_no_time_server_subnet(self):
        PillarManager.reset('ceph-salt:time_server:subnet')
        self.assertEqual(validate_config([]), "No time server subnet specified in config")

    def test_no_external_time_servers(self):
        PillarManager.reset('ceph-salt:time_server:external_time_servers')
        self.assertEqual(validate_config([]), "No external time servers specified in config")

    def test_time_server_not_a_minion(self):
        not_minion_err = ('Time server is not a minion: {} '
                          'setting will not have any effect')
        PillarManager.set('ceph-salt:time_server:server_host', 'foo.example.com')
        PillarManager.reset('ceph-salt:time_server:external_time_servers')
        self.assertEqual(
            validate_config([]),
            not_minion_err.format('time server subnet'))
        PillarManager.reset('ceph-salt:time_server:subnet')
        PillarManager.set('ceph-salt:time_server:external_time_servers', ['pool.ntp.org'])
        self.assertEqual(
            validate_config([]),
            not_minion_err.format('external time servers'))

    def test_admin_not_cluster_minion(self):
        PillarManager.set('ceph-salt:bootstrap_minion', 'node3.ceph.com')
        PillarManager.set('ceph-salt:minions:admin', ['node3.ceph.com'])
        self.assertEqual(validate_config([]), "One or more Admin nodes are not cluster minions")

    def test_no_ceph_container_image_path(self):
        PillarManager.reset('ceph-salt:container:images:ceph')
        self.assertEqual(validate_config([]), "No Ceph container image path specified in config")

    def test_valid(self):
        self.assertEqual(validate_config([]), None)

    @classmethod
    def create_valid_config(cls):
        PillarManager.set('ceph-salt:bootstrap_minion', 'node1.ceph.com')
        PillarManager.set('ceph-salt:bootstrap_mon_ip', '10.20.188.201')
        PillarManager.set('ceph-salt:time_server:enabled', True)
        PillarManager.set('ceph-salt:time_server:server_host', 'node1.ceph.com')
        PillarManager.set('ceph-salt:time_server:external_time_servers', ['pool.ntp.org'])
        PillarManager.set('ceph-salt:time_server:subnet', '10.20.188.0/24')
        PillarManager.set('ceph-salt:minions:all', ['node1.ceph.com', 'node2.ceph.com'])
        PillarManager.set('ceph-salt:minions:admin', ['node1.ceph.com'])
        PillarManager.set('ceph-salt:container:images:ceph', 'docker.io/ceph/daemon-base:latest')
