import json

import pytest

from ceph_salt.exceptions import MinionDoesNotExistInConfiguration
from ceph_salt.salt_utils import GrainsManager, PillarManager
from ceph_salt.config_shell import CephSaltConfigShell, generate_config_shell_tree,\
    run_export, run_import

from . import SaltMockTestCase


# pylint: disable=invalid-name
class ConfigShellTest(SaltMockTestCase):
    shell = None

    def setUp(self):
        super(ConfigShellTest, self).setUp()
        self.shell = CephSaltConfigShell()
        generate_config_shell_tree(self.shell)

        self.salt_env.minions = ['node1.ceph.com', 'node2.ceph.com', 'node3.ceph.com']
        GrainsManager.set_grain('node1.ceph.com', 'fqdn_ip4', ['10.20.39.201'])
        GrainsManager.set_grain('node2.ceph.com', 'fqdn_ip4', ['10.20.39.202'])
        GrainsManager.set_grain('node3.ceph.com', 'fqdn_ip4', ['10.20.39.203'])

    def tearDown(self):
        super(ConfigShellTest, self).tearDown()
        PillarManager.reload()

    def test_ceph_cluster_minions(self):
        self.shell.run_cmdline('/ceph_cluster/minions add node1.ceph.com')
        self.assertInSysOut('1 minion added.')
        self.assertGrains('node1.ceph.com', 'ceph-salt', {'member': True,
                                                          'roles': [],
                                                          'execution': {}})
        self.assertEqual(PillarManager.get('ceph-salt:minions:all'), ['node1'])
        self.assertEqual(PillarManager.get('ceph-salt:minions:admin'), [])
        self.assertEqual(PillarManager.get('ceph-salt:bootstrap_minion'), None)

        self.shell.run_cmdline('/ceph_cluster/minions rm node1.ceph.com')
        self.assertInSysOut('1 minion removed.')
        self.assertNotInGrains('node1.ceph.com', 'ceph-salt')
        self.assertEqual(PillarManager.get('ceph-salt:minions:all'), [])
        self.assertEqual(PillarManager.get('ceph-salt:minions:admin'), [])
        self.assertEqual(PillarManager.get('ceph-salt:bootstrap_minion'), None)

    def test_ceph_cluster_minions_rm_with_roles(self):
        self.shell.run_cmdline('/ceph_cluster/minions add node1.ceph.com')
        self.shell.run_cmdline('/ceph_cluster/roles/admin add node1.ceph.com')
        self.shell.run_cmdline('/ceph_cluster/roles/bootstrap set node1.ceph.com')
        self.clearSysOut()

        self.shell.run_cmdline('/ceph_cluster/minions rm node1.ceph.com')
        self.assertInSysOut("Cannot remove host 'node1.ceph.com' because it has roles defined: "
                            "['admin', 'bootstrap']")
        self.assertEqual(PillarManager.get('ceph-salt:minions:all'), ['node1'])

        self.shell.run_cmdline('/ceph_cluster/roles/admin rm node1.ceph.com')
        self.shell.run_cmdline('/ceph_cluster/roles/bootstrap reset')
        self.shell.run_cmdline('/ceph_cluster/minions rm node1.ceph.com')

    def test_ceph_cluster_roles_admin(self):
        self.shell.run_cmdline('/ceph_cluster/minions add node1.ceph.com')
        self.clearSysOut()

        self.shell.run_cmdline('/ceph_cluster/roles/admin add node1.ceph.com')
        self.assertInSysOut('1 minion added.')
        self.assertGrains('node1.ceph.com', 'ceph-salt', {'member': True,
                                                          'roles': ['admin'],
                                                          'execution': {}})
        self.assertEqual(PillarManager.get('ceph-salt:minions:all'), ['node1'])
        self.assertEqual(PillarManager.get('ceph-salt:minions:admin'), ['node1'])
        self.assertEqual(PillarManager.get('ceph-salt:bootstrap_minion'), None)

        self.shell.run_cmdline('/ceph_cluster/roles/admin rm node1.ceph.com')
        self.assertInSysOut('1 minion removed.')
        self.assertGrains('node1.ceph.com', 'ceph-salt', {'member': True,
                                                          'roles': [],
                                                          'execution': {}})
        self.assertEqual(PillarManager.get('ceph-salt:minions:all'), ['node1'])
        self.assertEqual(PillarManager.get('ceph-salt:minions:admin'), [])
        self.assertEqual(PillarManager.get('ceph-salt:bootstrap_minion'), None)

        self.shell.run_cmdline('/ceph_cluster/minions rm node1.ceph.com')

    def test_ceph_cluster_roles_bootstrap(self):
        with pytest.raises(MinionDoesNotExistInConfiguration):
            self.shell.run_cmdline('/ceph_cluster/roles/bootstrap set node1.ceph.com')
        self.shell.run_cmdline('/ceph_cluster/minions add node1.ceph.com')
        self.clearSysOut()

        self.shell.run_cmdline('/ceph_cluster/roles/bootstrap set node1.ceph.com')
        self.assertInSysOut('Value set.')
        self.assertGrains('node1.ceph.com', 'ceph-salt', {'member': True,
                                                          'roles': [],
                                                          'execution': {}})
        self.assertEqual(PillarManager.get('ceph-salt:minions:all'), ['node1'])
        self.assertEqual(PillarManager.get('ceph-salt:minions:admin'), [])
        self.assertEqual(PillarManager.get('ceph-salt:bootstrap_minion'), 'node1.ceph.com')

        self.shell.run_cmdline('/ceph_cluster/roles/bootstrap reset')
        self.assertInSysOut('Value reset.')
        self.assertGrains('node1.ceph.com', 'ceph-salt', {'member': True,
                                                          'roles': [],
                                                          'execution': {}})
        self.assertEqual(PillarManager.get('ceph-salt:minions:all'), ['node1'])
        self.assertEqual(PillarManager.get('ceph-salt:minions:admin'), [])
        self.assertEqual(PillarManager.get('ceph-salt:bootstrap_minion'), None)

        self.shell.run_cmdline('/ceph_cluster/minions rm node1.ceph.com')

    def test_containers_images_ceph(self):
        self.assertValueOption('/containers/images/ceph',
                               'ceph-salt:container:images:ceph',
                               'myvalue')

    def test_cephadm_bootstrap(self):
        self.assertFlagOption('/cephadm_bootstrap',
                              'ceph-salt:bootstrap_enabled')

    def test_cephadm_bootstrap_ceph_conf(self):
        self.assertConfigOption('/cephadm_bootstrap/ceph_conf',
                                'ceph-salt:bootstrap_ceph_conf')

    def test_cephadm_bootstrap_dashboard_password(self):
        self.assertValueOption('/cephadm_bootstrap/dashboard/password',
                               'ceph-salt:dashboard:password',
                               'mypassword')

    def test_cephadm_bootstrap_dashboard_username(self):
        self.assertValueOption('/cephadm_bootstrap/dashboard/username',
                               'ceph-salt:dashboard:username',
                               'myusername')

    def test_ssh(self):
        self.shell.run_cmdline('/ssh generate')
        self.assertInSysOut('Key pair generated.')
        self.assertNotEqual(PillarManager.get('ceph-salt:ssh:private_key'), None)
        self.assertNotEqual(PillarManager.get('ceph-salt:ssh:public_key'), None)

    def test_ssh_private_key(self):
        self.assertValueOption('/ssh/private_key',
                               'ceph-salt:ssh:private_key',
                               'myprivatekey')

    def test_ssh_public_key(self):
        self.assertValueOption('/ssh/public_key',
                               'ceph-salt:ssh:public_key',
                               'mypublickey')

    def test_time_server(self):
        self.assertFlagOption('/time_server',
                              'ceph-salt:time_server:enabled',
                              False)

    def test_time_server_external_servers(self):
        self.assertListOption('/time_server/external_servers',
                              'ceph-salt:time_server:external_time_servers',
                              ['server1', 'server2'])

    def test_time_server_server_hostname(self):
        self.assertValueOption('/time_server/server_hostname',
                               'ceph-salt:time_server:server_host',
                               'server1')

    def test_system_update_packages(self):
        self.assertFlagOption('/system_update/packages',
                              'ceph-salt:updates:enabled')

    def test_system_update_reboot(self):
        self.assertFlagOption('/system_update/reboot',
                              'ceph-salt:updates:reboot')

    def test_export(self):
        self.shell.run_cmdline('/ceph_cluster/minions add node1.ceph.com')
        self.shell.run_cmdline('/ceph_cluster/minions add node2.ceph.com')
        self.shell.run_cmdline('/ceph_cluster/roles/admin add node1.ceph.com')
        self.shell.run_cmdline('/time_server/server_hostname set server1')
        self.clearSysOut()

        self.assertTrue(run_export(False))
        self.assertJsonInSysOut({
            'minions': {
                'all': ['node1', 'node2'],
                'admin': ['node1']
            },
            'time_server': {
                'server_host': 'server1'
            }})

        self.shell.run_cmdline('/time_server/server_hostname reset')
        self.shell.run_cmdline('/ceph_cluster/roles/admin rm node1.ceph.com')
        self.shell.run_cmdline('/ceph_cluster/minions rm node2.ceph.com')
        self.shell.run_cmdline('/ceph_cluster/minions rm node1.ceph.com')

    def test_import(self):
        self.fs.create_file('/config.json', contents=json.dumps({
            'minions': {
                'all': ['node1', 'node2'],
                'admin': ['node1']
            },
            'time_server': {
                'server_host': 'server1'
            }}))
        self.assertTrue(run_import("/config.json"))
        self.assertInSysOut('Configuration imported.')
        self.assertGrains('node1.ceph.com',
                          'ceph-salt', {'member': True,
                                        'roles': ['admin'],
                                        'execution': {}})
        self.assertGrains('node2.ceph.com',
                          'ceph-salt', {'member': True,
                                        'roles': [],
                                        'execution': {}})
        self.assertEqual(PillarManager.get('ceph-salt:minions:all'), ['node1', 'node2'])
        self.assertEqual(PillarManager.get('ceph-salt:minions:admin'), ['node1'])
        self.assertIsNone(PillarManager.get('ceph-salt:bootstrap_minion'))
        self.assertEqual(PillarManager.get('ceph-salt:time_server:server_host'), 'server1')

        self.shell.run_cmdline('/time_server/server_hostname reset')
        self.shell.run_cmdline('/ceph_cluster/roles/admin rm node1.ceph.com')
        self.shell.run_cmdline('/ceph_cluster/minions rm node2.ceph.com')
        self.shell.run_cmdline('/ceph_cluster/minions rm node1.ceph.com')
        self.fs.remove('/config.json')

    def test_import_invalid_host(self):
        self.fs.create_file('/config.json', contents=json.dumps({
            'minions': {
                'all': ['node1', 'node2', 'node9'],
                'admin': ['node1']
            }}))

        self.assertFalse(run_import("/config.json"))
        self.assertInSysOut("Cannot find host 'node9'")

        self.fs.remove('/config.json')

    def assertConfigOption(self, path, pillar_key):
        self.shell.run_cmdline('{} add section1'.format(path))
        self.assertInSysOut('Section added.')

        sec_path = '{}/{}'.format(path, 'section1')
        sec_pillar_key = '{}:{}'.format(pillar_key, 'section1')

        self.shell.run_cmdline('{} set "my option1" 2'.format(sec_path))
        self.assertInSysOut('Parameter set.')
        self.assertEqual(PillarManager.get(sec_pillar_key), {'my option1': '2'})

        self.shell.run_cmdline('{} set "my option2" 3'.format(sec_path))
        self.assertInSysOut('Parameter set.')
        self.assertEqual(PillarManager.get(sec_pillar_key), {'my option1': '2', 'my option2': '3'})

        self.shell.run_cmdline('{} remove "my option1"'.format(sec_path))
        self.assertInSysOut('Parameter removed.')
        self.assertEqual(PillarManager.get(sec_pillar_key), {'my option2': '3'})

        self.shell.run_cmdline('{} reset'.format(sec_path))
        self.assertInSysOut('Section reset.')
        self.assertEqual(PillarManager.get(sec_pillar_key), {})

        self.shell.run_cmdline('{} reset'.format(path))
        self.assertInSysOut('Config reset.')
        self.assertEqual(PillarManager.get(pillar_key), {})

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
