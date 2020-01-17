from ceph_bootstrap.salt_utils import GrainsManager, PillarManager
from ceph_bootstrap.config_shell import run_config_cmdline

from . import SaltMockTestCase


# pylint: disable=invalid-name
class ConfigShellTest(SaltMockTestCase):
    shell = None

    def setUp(self):
        super(ConfigShellTest, self).setUp()

        self.salt_env.minions = ['node1.ceph.com', 'node2.ceph.com', 'node3.ceph.com']
        GrainsManager.set_grain('node1.ceph.com', 'fqdn_ip4', ['10.20.39.201'])
        GrainsManager.set_grain('node2.ceph.com', 'fqdn_ip4', ['10.20.39.202'])
        GrainsManager.set_grain('node3.ceph.com', 'fqdn_ip4', ['10.20.39.203'])

    def test_cluster_minions(self):
        run_config_cmdline(False, '/Cluster/Minions add node1.ceph.com')
        self.assertInSysOut('1 minion added.')
        self.assertGrains('node1.ceph.com', 'ceph-salt', {'member': True, 'roles': []})
        self.assertEqual(PillarManager.get('ceph-salt:minions:all'), ['node1'])
        self.assertEqual(PillarManager.get('ceph-salt:minions:mgr'), [])
        self.assertEqual(PillarManager.get('ceph-salt:minions:mon'), {})
        self.assertEqual(PillarManager.get('ceph-salt:bootstrap_mon'), None)

        run_config_cmdline(False, '/Cluster/Minions rm node1.ceph.com')
        self.assertInSysOut('1 minion removed.')
        self.assertNotInGrains('node1.ceph.com', 'ceph-salt')
        self.assertEqual(PillarManager.get('ceph-salt:minions:all'), [])
        self.assertEqual(PillarManager.get('ceph-salt:minions:mgr'), [])
        self.assertEqual(PillarManager.get('ceph-salt:minions:mon'), {})
        self.assertEqual(PillarManager.get('ceph-salt:bootstrap_mon'), None)

    def test_cluster_bootstrap_mon(self):
        run_config_cmdline(False, '/Cluster/Bootstrap_Mon set node1.ceph.com')
        self.assertInSysOut("Minion 'node1.ceph.com' does not exist in current configuration")

        run_config_cmdline(False, '/Cluster/Minions add node1.ceph.com')
        run_config_cmdline(False, '/Cluster/Bootstrap_Mon set node1.ceph.com')
        self.assertGrains('node1.ceph.com', 'ceph-salt', {'member': True, 'roles': ['mgr', 'mon']})
        self.assertEqual(PillarManager.get('ceph-salt:minions:all'), ['node1'])
        self.assertEqual(PillarManager.get('ceph-salt:minions:mgr'), ['node1'])
        self.assertEqual(PillarManager.get('ceph-salt:minions:mon'), {'node1': '10.20.39.201'})
        self.assertEqual(PillarManager.get('ceph-salt:bootstrap_mon'), 'node1.ceph.com')

        run_config_cmdline(False, '/Cluster/Bootstrap_Mon reset')
        self.assertGrains('node1.ceph.com', 'ceph-salt', {'member': True, 'roles': []})
        self.assertEqual(PillarManager.get('ceph-salt:minions:all'), ['node1'])
        self.assertEqual(PillarManager.get('ceph-salt:minions:mgr'), [])
        self.assertEqual(PillarManager.get('ceph-salt:minions:mon'), {})
        self.assertEqual(PillarManager.get('ceph-salt:bootstrap_mon'), None)

        run_config_cmdline(False, '/Cluster/Minions rm node1.ceph.com')

    def test_cluster_minions_add_invalid_ip(self):
        fqdn_ip4 = GrainsManager.get_grain('node1.ceph.com', 'fqdn_ip4')
        GrainsManager.set_grain('node1.ceph.com', 'fqdn_ip4', ['127.0.0.1'])

        run_config_cmdline(False, '/Cluster/Minions add node1.ceph.com')
        self.assertInSysOut("Host 'node1.ceph.com' FQDN resolves to the loopback interface IP "
                            "address")
        self.assertEqual(PillarManager.get('ceph-salt:minions:all'), [])

        GrainsManager.set_grain('node1.ceph.com', 'fqdn_ip4', fqdn_ip4)

    def test_cluster_minions_rm_with_role(self):
        run_config_cmdline(True, '/Cluster/Minions add node1.ceph.com')
        run_config_cmdline(True, '/Cluster/Roles/Mgr add node1.ceph.com')
        self.clearSysOut()

        run_config_cmdline(True, '/Cluster/Minions rm node1.ceph.com')
        self.assertInSysOut("Cannot remove host 'node1.ceph.com' because it has roles defined: "
                            "{'mgr'}")
        self.assertEqual(PillarManager.get('ceph-salt:minions:all'), ['node1'])

        run_config_cmdline(True, '/Cluster/Roles/Mgr rm node1.ceph.com')
        run_config_cmdline(True, '/Cluster/Minions rm node1.ceph.com')

    def test_cluster_roles_mgr(self):
        run_config_cmdline(True, '/Cluster/Minions add node1.ceph.com')
        self.clearSysOut()

        run_config_cmdline(True, '/Cluster/Roles/Mgr add node1.ceph.com')
        self.assertInSysOut('1 minion added.')
        self.assertGrains('node1.ceph.com', 'ceph-salt', {'member': True, 'roles': ['mgr']})
        self.assertEqual(PillarManager.get('ceph-salt:minions:all'), ['node1'])
        self.assertEqual(PillarManager.get('ceph-salt:minions:mgr'), ['node1'])
        self.assertEqual(PillarManager.get('ceph-salt:minions:mon'), {})
        self.assertEqual(PillarManager.get('ceph-salt:bootstrap_mon'), None)

        run_config_cmdline(True, '/Cluster/Roles/Mgr rm node1.ceph.com')
        self.assertInSysOut('1 minion removed.')
        self.assertGrains('node1.ceph.com', 'ceph-salt', {'member': True, 'roles': []})
        self.assertEqual(PillarManager.get('ceph-salt:minions:all'), ['node1'])
        self.assertEqual(PillarManager.get('ceph-salt:minions:mgr'), [])
        self.assertEqual(PillarManager.get('ceph-salt:minions:mon'), {})
        self.assertEqual(PillarManager.get('ceph-salt:bootstrap_mon'), None)

        run_config_cmdline(False, '/Cluster/Minions rm node1.ceph.com')

    def test_cluster_roles_mon(self):
        run_config_cmdline(True, '/Cluster/Minions add node1.ceph.com')
        run_config_cmdline(True, '/Cluster/Minions add node2.ceph.com')
        run_config_cmdline(True, '/Cluster/Roles/Mgr add node1.ceph.com')
        run_config_cmdline(True, '/Cluster/Roles/Mgr add node2.ceph.com')
        self.clearSysOut()

        run_config_cmdline(True, '/Cluster/Roles/Mon add node2.ceph.com')
        self.assertInSysOut('1 minion added.')
        self.assertGrains('node2.ceph.com', 'ceph-salt', {'member': True, 'roles': ['mgr', 'mon']})
        self.assertEqual(PillarManager.get('ceph-salt:minions:all'), ['node1', 'node2'])
        self.assertEqual(PillarManager.get('ceph-salt:minions:mgr'), ['node1', 'node2'])
        self.assertEqual(PillarManager.get('ceph-salt:minions:mon'), {'node2': '10.20.39.202'})
        self.assertEqual(PillarManager.get('ceph-salt:bootstrap_mon'), 'node2.ceph.com')

        run_config_cmdline(True, '/Cluster/Roles/Mon rm node2.ceph.com')
        self.assertInSysOut('1 minion removed.')
        self.assertGrains('node2.ceph.com', 'ceph-salt', {'member': True, 'roles': ['mgr']})
        self.assertEqual(PillarManager.get('ceph-salt:minions:all'), ['node1', 'node2'])
        self.assertEqual(PillarManager.get('ceph-salt:minions:mgr'), ['node1', 'node2'])
        self.assertEqual(PillarManager.get('ceph-salt:minions:mon'), {})
        self.assertEqual(PillarManager.get('ceph-salt:bootstrap_mon'), None)

        run_config_cmdline(True, '/Cluster/Roles/Mgr rm node2.ceph.com')
        run_config_cmdline(True, '/Cluster/Roles/Mgr rm node1.ceph.com')
        run_config_cmdline(True, '/Cluster/Minions rm node2.ceph.com')
        run_config_cmdline(True, '/Cluster/Minions rm node1.ceph.com')

    def test_containers_images_ceph(self):
        self.assertValueOption(False,
                               '/Containers/Images/ceph',
                               'ceph-salt:container:images:ceph',
                               'myvalue')

    def test_deployment_bootstrap(self):
        self.assertFlagOption(True,
                              '/Deployment/Bootstrap',
                              'ceph-salt:deploy:bootstrap')

    def test_deployment_dashboard_password(self):
        self.assertValueOption(True,
                               '/Deployment/Dashboard/password',
                               'ceph-salt:dashboard:password',
                               'mypassword')

    def test_deployment_dashboard_username(self):
        self.assertValueOption(True,
                               '/Deployment/Dashboard/username',
                               'ceph-salt:dashboard:username',
                               'myusername')

    def test_deployment_mgr(self):
        self.assertFlagOption(True,
                              '/Deployment/Mgr',
                              'ceph-salt:deploy:mgr')

    def test_deployment_mon(self):
        self.assertFlagOption(True,
                              '/Deployment/Mon',
                              'ceph-salt:deploy:mon')

    def test_deployment_osd(self):
        self.assertFlagOption(True,
                              '/Deployment/OSD',
                              'ceph-salt:deploy:osd')

    def test_ssh(self):
        run_config_cmdline(False, '/SSH generate')
        self.assertInSysOut('Key pair generated.')
        self.assertNotEqual(PillarManager.get('ceph-salt:ssh:private_key'), None)
        self.assertNotEqual(PillarManager.get('ceph-salt:ssh:public_key'), None)

    def test_ssh_private_key(self):
        self.assertValueOption(False,
                               '/SSH/Private_Key',
                               'ceph-salt:ssh:private_key',
                               'myprivatekey')

    def test_ssh_public_key(self):
        self.assertValueOption(False,
                               '/SSH/Public_Key',
                               'ceph-salt:ssh:public_key',
                               'mypublickey')

    def test_storage_drive_groups(self):
        self.assertListOption(True,
                              '/Storage/Drive_Groups',
                              'ceph-salt:storage:drive_groups',
                              ['value1', 'value2'])

    def test_time_server(self):
        self.assertFlagOption(False,
                              '/Time_Server',
                              'ceph-salt:time_server:enabled',
                              False)

    def test_time_server_external_servers(self):
        self.assertListOption(False,
                              '/Time_Server/External_Servers',
                              'ceph-salt:time_server:external_time_servers',
                              ['server1', 'server2'])

    def test_time_server_server_hostname(self):
        self.assertValueOption(False,
                               '/Time_Server/Server_Hostname',
                               'ceph-salt:time_server:server_host',
                               'server1')

    def assertFlagOption(self, advanced, path, pillar_key, reset_supported=True):
        run_config_cmdline(advanced, '{} enable'.format(path))
        self.assertInSysOut('Enabled.')
        self.assertEqual(PillarManager.get(pillar_key), True)

        run_config_cmdline(advanced, '{} disable'.format(path))
        self.assertInSysOut('Disabled.')
        self.assertEqual(PillarManager.get(pillar_key), False)

        if reset_supported:
            run_config_cmdline(advanced, '{} reset'.format(path))
            self.assertInSysOut('Value reset.')
            self.assertEqual(PillarManager.get(pillar_key), None)

    def assertValueOption(self, advanced, path, pillar_key, value):
        run_config_cmdline(advanced, '{} set {}'.format(path, value))
        self.assertInSysOut('Value set.')
        self.assertEqual(PillarManager.get(pillar_key), value)

        run_config_cmdline(advanced, '{} reset'.format(path))
        self.assertInSysOut('Value reset.')
        self.assertEqual(PillarManager.get(pillar_key), None)

    def assertListOption(self, advanced, path, pillar_key, values):
        for value in values:
            run_config_cmdline(advanced, '{} add {}'.format(path, value))
            self.assertInSysOut('Value added.')
        self.assertEqual(PillarManager.get(pillar_key), values)

        for value in values:
            run_config_cmdline(advanced, '{} remove {}'.format(path, value))
            self.assertInSysOut('Value removed.')
        self.assertEqual(PillarManager.get(pillar_key), [])
