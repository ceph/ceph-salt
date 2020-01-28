from ceph_bootstrap.salt_utils import GrainsManager, PillarManager
from ceph_bootstrap.config_shell import CephBootstrapConfigShell, generate_config_shell_tree

from . import SaltMockTestCase


# pylint: disable=invalid-name
class ConfigShellTest(SaltMockTestCase):
    shell = None

    def setUp(self):
        super(ConfigShellTest, self).setUp()
        self.shell = CephBootstrapConfigShell()
        generate_config_shell_tree(self.shell)

        self.salt_env.minions = ['node1.ceph.com', 'node2.ceph.com', 'node3.ceph.com']
        GrainsManager.set_grain('node1.ceph.com', 'fqdn_ip4', ['10.20.39.201'])
        GrainsManager.set_grain('node2.ceph.com', 'fqdn_ip4', ['10.20.39.202'])
        GrainsManager.set_grain('node3.ceph.com', 'fqdn_ip4', ['10.20.39.203'])

    def test_cluster_minions(self):
        self.shell.run_cmdline('/Cluster/Minions add node1.ceph.com')
        self.assertInSysOut('1 minion added.')
        self.assertGrains('node1.ceph.com', 'ceph-salt', {'member': True, 'roles': []})
        self.assertEqual(PillarManager.get('ceph-salt:minions:all'), ['node1'])
        self.assertEqual(PillarManager.get('ceph-salt:minions:mgr'), [])
        self.assertEqual(PillarManager.get('ceph-salt:minions:mon'), {})
        self.assertEqual(PillarManager.get('ceph-salt:bootstrap_minion'), None)

        self.shell.run_cmdline('/Cluster/Minions rm node1.ceph.com')
        self.assertInSysOut('1 minion removed.')
        self.assertNotInGrains('node1.ceph.com', 'ceph-salt')
        self.assertEqual(PillarManager.get('ceph-salt:minions:all'), [])
        self.assertEqual(PillarManager.get('ceph-salt:minions:mgr'), [])
        self.assertEqual(PillarManager.get('ceph-salt:minions:mon'), {})
        self.assertEqual(PillarManager.get('ceph-salt:bootstrap_minion'), None)

    def test_cluster_minions_add_invalid_ip(self):
        fqdn_ip4 = GrainsManager.get_grain('node1.ceph.com', 'fqdn_ip4')
        GrainsManager.set_grain('node1.ceph.com', 'fqdn_ip4', ['127.0.0.1'])

        self.shell.run_cmdline('/Cluster/Minions add node1.ceph.com')
        self.assertInSysOut("Host 'node1.ceph.com' FQDN resolves to the loopback interface IP "
                            "address")
        self.assertEqual(PillarManager.get('ceph-salt:minions:all'), [])

        GrainsManager.set_grain('node1.ceph.com', 'fqdn_ip4', fqdn_ip4)

    def test_cluster_minions_rm_with_role(self):
        self.shell.run_cmdline('/Cluster/Minions add node1.ceph.com')
        self.shell.run_cmdline('/Cluster/Roles/Mgr add node1.ceph.com')
        self.clearSysOut()

        self.shell.run_cmdline('/Cluster/Minions rm node1.ceph.com')
        self.assertInSysOut("Cannot remove host 'node1.ceph.com' because it has roles defined: "
                            "{'mgr'}")
        self.assertEqual(PillarManager.get('ceph-salt:minions:all'), ['node1'])

        self.shell.run_cmdline('/Cluster/Roles/Mgr rm node1.ceph.com')
        self.shell.run_cmdline('/Cluster/Minions rm node1.ceph.com')

    def test_cluster_roles_mgr(self):
        self.shell.run_cmdline('/Cluster/Minions add node1.ceph.com')
        self.clearSysOut()

        self.shell.run_cmdline('/Cluster/Roles/Mgr add node1.ceph.com')
        self.assertInSysOut('1 minion added.')
        self.assertGrains('node1.ceph.com', 'ceph-salt', {'member': True, 'roles': ['mgr']})
        self.assertEqual(PillarManager.get('ceph-salt:minions:all'), ['node1'])
        self.assertEqual(PillarManager.get('ceph-salt:minions:mgr'), ['node1'])
        self.assertEqual(PillarManager.get('ceph-salt:minions:mon'), {})
        self.assertEqual(PillarManager.get('ceph-salt:bootstrap_minion'), None)

        self.shell.run_cmdline('/Cluster/Roles/Mgr rm node1.ceph.com')
        self.assertInSysOut('1 minion removed.')
        self.assertGrains('node1.ceph.com', 'ceph-salt', {'member': True, 'roles': []})
        self.assertEqual(PillarManager.get('ceph-salt:minions:all'), ['node1'])
        self.assertEqual(PillarManager.get('ceph-salt:minions:mgr'), [])
        self.assertEqual(PillarManager.get('ceph-salt:minions:mon'), {})
        self.assertEqual(PillarManager.get('ceph-salt:bootstrap_minion'), None)

        self.shell.run_cmdline('/Cluster/Minions rm node1.ceph.com')

    def test_cluster_roles_mon(self):
        self.shell.run_cmdline('/Cluster/Minions add node1.ceph.com')
        self.shell.run_cmdline('/Cluster/Minions add node2.ceph.com')
        self.shell.run_cmdline('/Cluster/Roles/Mgr add node1.ceph.com')
        self.shell.run_cmdline('/Cluster/Roles/Mgr add node2.ceph.com')
        self.clearSysOut()

        self.shell.run_cmdline('/Cluster/Roles/Mon add node2.ceph.com')
        self.assertInSysOut('1 minion added.')
        self.assertGrains('node2.ceph.com', 'ceph-salt', {'member': True, 'roles': ['mgr', 'mon']})
        self.assertEqual(PillarManager.get('ceph-salt:minions:all'), ['node1', 'node2'])
        self.assertEqual(PillarManager.get('ceph-salt:minions:mgr'), ['node1', 'node2'])
        self.assertEqual(PillarManager.get('ceph-salt:minions:mon'), {'node2': '10.20.39.202'})
        self.assertEqual(PillarManager.get('ceph-salt:bootstrap_minion'), 'node2.ceph.com')

        self.shell.run_cmdline('/Cluster/Roles/Mon rm node2.ceph.com')
        self.assertInSysOut('1 minion removed.')
        self.assertGrains('node2.ceph.com', 'ceph-salt', {'member': True, 'roles': ['mgr']})
        self.assertEqual(PillarManager.get('ceph-salt:minions:all'), ['node1', 'node2'])
        self.assertEqual(PillarManager.get('ceph-salt:minions:mgr'), ['node1', 'node2'])
        self.assertEqual(PillarManager.get('ceph-salt:minions:mon'), {})
        self.assertEqual(PillarManager.get('ceph-salt:bootstrap_minion'), None)

        self.shell.run_cmdline('/Cluster/Roles/Mgr rm node2.ceph.com')
        self.shell.run_cmdline('/Cluster/Roles/Mgr rm node1.ceph.com')
        self.shell.run_cmdline('/Cluster/Minions rm node2.ceph.com')
        self.shell.run_cmdline('/Cluster/Minions rm node1.ceph.com')

    def test_containers_images_ceph(self):
        self.assertValueOption('/Containers/Images/ceph',
                               'ceph-salt:container:images:ceph',
                               'myvalue')

    def test_deployment_bootstrap(self):
        self.assertFlagOption('/Deployment/Bootstrap',
                              'ceph-salt:deploy:bootstrap')

    def test_deployment_dashboard_password(self):
        self.assertValueOption('/Deployment/Dashboard/password',
                               'ceph-salt:dashboard:password',
                               'mypassword')

    def test_deployment_dashboard_username(self):
        self.assertValueOption('/Deployment/Dashboard/username',
                               'ceph-salt:dashboard:username',
                               'myusername')

    def test_deployment_mgr(self):
        self.assertFlagOption('/Deployment/Mgr',
                              'ceph-salt:deploy:mgr')

    def test_deployment_mon(self):
        self.assertFlagOption('/Deployment/Mon',
                              'ceph-salt:deploy:mon')

    def test_deployment_osd(self):
        self.assertFlagOption('/Deployment/OSD',
                              'ceph-salt:deploy:osd')

    def test_ssh(self):
        self.shell.run_cmdline('/SSH generate')
        self.assertInSysOut('Key pair generated.')
        self.assertNotEqual(PillarManager.get('ceph-salt:ssh:private_key'), None)
        self.assertNotEqual(PillarManager.get('ceph-salt:ssh:public_key'), None)

    def test_ssh_private_key(self):
        self.assertValueOption('/SSH/Private_Key',
                               'ceph-salt:ssh:private_key',
                               'myprivatekey')

    def test_ssh_public_key(self):
        self.assertValueOption('/SSH/Public_Key',
                               'ceph-salt:ssh:public_key',
                               'mypublickey')

    def test_storage_drive_groups(self):
        self.assertListOption('/Storage/Drive_Groups',
                              'ceph-salt:storage:drive_groups',
                              ['value1', 'value2'])

    def test_time_server(self):
        self.assertFlagOption('/Time_Server',
                              'ceph-salt:time_server:enabled',
                              False)

    def test_time_server_external_servers(self):
        self.assertListOption('/Time_Server/External_Servers',
                              'ceph-salt:time_server:external_time_servers',
                              ['server1', 'server2'])

    def test_time_server_server_hostname(self):
        self.assertValueOption('/Time_Server/Server_Hostname',
                               'ceph-salt:time_server:server_host',
                               'server1')

    def assertFlagOption(self, path, pillar_key, reset_supported=True):
        self.shell.run_cmdline('{} enable'.format(path))
        self.assertInSysOut('Enabled.')
        self.assertEqual(PillarManager.get(pillar_key), True)

        self.shell.run_cmdline('{} disable'.format(path))
        self.assertInSysOut('Disabled.')
        self.assertEqual(PillarManager.get(pillar_key), False)

        if reset_supported:
            self.shell.run_cmdline('{} reset'.format(path))
            self.assertInSysOut('Value reset.')
            self.assertEqual(PillarManager.get(pillar_key), None)

    def assertValueOption(self, path, pillar_key, value):
        self.shell.run_cmdline('{} set {}'.format(path, value))
        self.assertInSysOut('Value set.')
        self.assertEqual(PillarManager.get(pillar_key), value)

        self.shell.run_cmdline('{} reset'.format(path))
        self.assertInSysOut('Value reset.')
        self.assertEqual(PillarManager.get(pillar_key), None)

    def assertListOption(self, path, pillar_key, values):
        for value in values:
            self.shell.run_cmdline('{} add {}'.format(path, value))
            self.assertInSysOut('Value added.')
        self.assertEqual(PillarManager.get(pillar_key), values)

        for value in values:
            self.shell.run_cmdline('{} remove {}'.format(path, value))
            self.assertInSysOut('Value removed.')
        self.assertEqual(PillarManager.get(pillar_key), [])
