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
        self.assertEqual(PillarManager.get('ceph-salt:minions:all'), ['node1.ceph.com'])
        self.assertEqual(PillarManager.get('ceph-salt:minions:admin'), [])
        self.assertEqual(PillarManager.get('ceph-salt:bootstrap_minion'), None)

        self.shell.run_cmdline('/ceph_cluster/minions remove node1.ceph.com')
        self.assertInSysOut('1 minion removed.')
        self.assertNotInGrains('node1.ceph.com', 'ceph-salt')
        self.assertEqual(PillarManager.get('ceph-salt:minions:all'), [])
        self.assertEqual(PillarManager.get('ceph-salt:minions:admin'), [])
        self.assertEqual(PillarManager.get('ceph-salt:bootstrap_minion'), None)

    def test_ceph_cluster_minions_remove_with_roles(self):
        self.shell.run_cmdline('/ceph_cluster/minions add node1.ceph.com')
        self.shell.run_cmdline('/ceph_cluster/roles/admin add node1.ceph.com')
        self.shell.run_cmdline('/ceph_cluster/roles/bootstrap set node1.ceph.com')
        self.clearSysOut()

        self.shell.run_cmdline('/ceph_cluster/minions remove node1.ceph.com')
        self.assertInSysOut("Cannot remove host 'node1.ceph.com' because it has roles defined: "
                            "['admin', 'bootstrap']")
        self.assertEqual(PillarManager.get('ceph-salt:minions:all'), ['node1.ceph.com'])

        self.shell.run_cmdline('/ceph_cluster/roles/admin remove node1.ceph.com')
        self.shell.run_cmdline('/ceph_cluster/roles/bootstrap reset')
        self.shell.run_cmdline('/ceph_cluster/minions remove node1.ceph.com')

    def test_ceph_cluster_roles_admin(self):
        self.shell.run_cmdline('/ceph_cluster/minions add node1.ceph.com')
        self.clearSysOut()

        self.shell.run_cmdline('/ceph_cluster/roles/admin add node1.ceph.com')
        self.assertInSysOut('1 minion added.')
        self.assertGrains('node1.ceph.com', 'ceph-salt', {'member': True,
                                                          'roles': ['admin'],
                                                          'execution': {}})
        self.assertEqual(PillarManager.get('ceph-salt:minions:all'), ['node1.ceph.com'])
        self.assertEqual(PillarManager.get('ceph-salt:minions:admin'), ['node1.ceph.com'])
        self.assertEqual(PillarManager.get('ceph-salt:bootstrap_minion'), None)

        self.shell.run_cmdline('/ceph_cluster/roles/admin remove node1.ceph.com')
        self.assertInSysOut('1 minion removed.')
        self.assertGrains('node1.ceph.com', 'ceph-salt', {'member': True,
                                                          'roles': [],
                                                          'execution': {}})
        self.assertEqual(PillarManager.get('ceph-salt:minions:all'), ['node1.ceph.com'])
        self.assertEqual(PillarManager.get('ceph-salt:minions:admin'), [])
        self.assertEqual(PillarManager.get('ceph-salt:bootstrap_minion'), None)

        self.shell.run_cmdline('/ceph_cluster/minions remove node1.ceph.com')

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
        self.assertEqual(PillarManager.get('ceph-salt:minions:all'), ['node1.ceph.com'])
        self.assertEqual(PillarManager.get('ceph-salt:minions:admin'), [])
        self.assertEqual(PillarManager.get('ceph-salt:bootstrap_minion'), 'node1.ceph.com')

        self.shell.run_cmdline('/ceph_cluster/roles/bootstrap reset')
        self.assertInSysOut('Value reset.')
        self.assertGrains('node1.ceph.com', 'ceph-salt', {'member': True,
                                                          'roles': [],
                                                          'execution': {}})
        self.assertEqual(PillarManager.get('ceph-salt:minions:all'), ['node1.ceph.com'])
        self.assertEqual(PillarManager.get('ceph-salt:minions:admin'), [])
        self.assertEqual(PillarManager.get('ceph-salt:bootstrap_minion'), None)

        self.shell.run_cmdline('/ceph_cluster/minions remove node1.ceph.com')

    def test_containers_images_ceph(self):
        self.assertValueOption('/containers/images/ceph',
                               'ceph-salt:container:images:ceph',
                               'myvalue')

    def test_containers_registries_conf(self):
        self.assertFlagOption('/containers/registries_conf',
                              'ceph-salt:container:registries_enabled',
                              reset_supported=False)

    def test_containers_registry_auth_username(self):
        self.assertValueOption('/containers/registry_auth/username',
                               'ceph-salt:container:auth:username',
                               'testuser')

    def test_containers_registry_auth_password(self):
        self.assertValueOption('/containers/registry_auth/password',
                               'ceph-salt:container:auth:password',
                               'testpassword')

    def test_containers_registry_auth_registry(self):
        self.assertValueOption('/containers/registry_auth/registry',
                               'ceph-salt:container:auth:registry',
                               '172.17.0.1:5000')

    def test_containers_registries_conf_registries(self):
        self.assertListDictOption('/containers/registries_conf/registries',
                                  'ceph-salt:container:registries',
                                  ['location=172.17.0.1:5000 insecure=false',
                                   ('location=192.168.0.1:8080/docker.io prefix=docker.io'
                                    ' insecure=1')],
                                  [
                                      {
                                          'location': '172.17.0.1:5000',
                                          'insecure': False
                                      },
                                      {
                                          'location': '192.168.0.1:8080/docker.io',
                                          'prefix': 'docker.io',
                                          'insecure': True
                                      }
                                  ])

    def test_cephadm_advanced_fsid(self):
        self.assertDictOption('/cephadm_bootstrap/advanced',
                              'ceph-salt:bootstrap_arguments',
                              'fsid',
                              '8726cb9c-75d8-11ea-924c-001a4aab830c')

    def test_cephadm_advanced_mon_id(self):
        self.assertDictOption('/cephadm_bootstrap/advanced',
                              'ceph-salt:bootstrap_arguments',
                              'mon-id',
                              'a')

    def test_cephadm_advanced_mgr_id(self):
        self.assertDictOption('/cephadm_bootstrap/advanced',
                              'ceph-salt:bootstrap_arguments',
                              'mgr-id',
                              'y')

    def test_cephadm_bootstrap_ceph_conf(self):
        self.assertConfigOption('/cephadm_bootstrap/ceph_conf',
                                'ceph-salt:bootstrap_ceph_conf')

    def test_cephadm_bootstrap_dashboard_force_password_update(self):
        self.assertFlagOption('/cephadm_bootstrap/dashboard/force_password_update',
                              'ceph-salt:dashboard:password_update_required',
                              True)

    def test_cephadm_bootstrap_dashboard_password(self):
        default = PillarManager.get('ceph-salt:dashboard:password')
        self.assertValueOption('/cephadm_bootstrap/dashboard/password',
                               'ceph-salt:dashboard:password',
                               'mypassword',
                               default)

    def test_cephadm_bootstrap_dashboard_username(self):
        self.assertValueOption('/cephadm_bootstrap/dashboard/username',
                               'ceph-salt:dashboard:username',
                               'myusername',
                               'admin')

    def test_cephadm_bootstrap_dashboard_ssl_certificate(self):
        self.assertImportOption('/cephadm_bootstrap/dashboard/ssl_certificate',
                                'ceph-salt:dashboard:ssl_certificate',
                                'mycert')

    def test_cephadm_bootstrap_dashboard_ssl_certificate_key(self):
        self.assertImportOption('/cephadm_bootstrap/dashboard/ssl_certificate_key',
                                'ceph-salt:dashboard:ssl_certificate_key',
                                'mycertkey')

    def test_ssh(self):
        self.shell.run_cmdline('/ssh generate')
        self.assertInSysOut('Key pair generated.')
        self.assertNotEqual(PillarManager.get('ceph-salt:ssh:private_key'), None)
        self.assertNotEqual(PillarManager.get('ceph-salt:ssh:public_key'), None)

    def test_ssh_private_key(self):
        self.assertImportOption('/ssh/private_key',
                                'ceph-salt:ssh:private_key',
                                'myprivatekey')

    def test_ssh_public_key(self):
        self.assertImportOption('/ssh/public_key',
                                'ceph-salt:ssh:public_key',
                                'mypublickey')

    def test_time_server(self):
        self.assertFlagOption('/time_server',
                              'ceph-salt:time_server:enabled',
                              reset_supported=False)

    def test_time_server_external_servers(self):
        self.assertListOption('/time_server/external_servers',
                              'ceph-salt:time_server:external_time_servers',
                              ['server1', 'server2'])

    def test_time_server_server_hostname(self):
        self.shell.run_cmdline('/ceph_cluster/minions add node1.ceph.com')
        self.clearSysOut()

        self.assertValueOption('/time_server/server_hostname',
                               'ceph-salt:time_server:server_host',
                               'node1.ceph.com')

        self.shell.run_cmdline('/ceph_cluster/minions remove node1.ceph.com')

    def test_time_server_subnet(self):
        self.assertValueOption('/time_server/subnet',
                               'ceph-salt:time_server:subnet',
                               '10.20.188.0/24')

    def test_system_update_packages(self):
        self.assertFlagOption('/system_update/packages',
                              'ceph-salt:updates:enabled',
                              True)

    def test_system_update_reboot(self):
        self.assertFlagOption('/system_update/reboot',
                              'ceph-salt:updates:reboot',
                              True)

    def test_export(self):
        self.shell.run_cmdline('/ceph_cluster/minions add node1.ceph.com')
        self.shell.run_cmdline('/ceph_cluster/minions add node2.ceph.com')
        self.shell.run_cmdline('/ceph_cluster/roles/cephadm add node1.ceph.com')
        self.shell.run_cmdline('/ceph_cluster/roles/cephadm add node2.ceph.com')
        self.shell.run_cmdline('/ceph_cluster/roles/admin add node1.ceph.com')
        self.shell.run_cmdline('/time_server/server_hostname set node1.ceph.com')
        self.shell.run_cmdline('/time_server/subnet set 10.20.188.0/24')
        self.clearSysOut()

        self.assertTrue(run_export(False))
        self.assertJsonInSysOut({
            'container': {
                'registries_enabled': True
            },
            'dashboard': {
                'username': 'admin',
                'password': PillarManager.get('ceph-salt:dashboard:password'),
                'password_update_required': True
            },
            'minions': {
                'all': ['node1.ceph.com', 'node2.ceph.com'],
                'admin': ['node1.ceph.com'],
                'cephadm': ['node1.ceph.com', 'node2.ceph.com']
            },
            'time_server': {
                'enabled': True,
                'server_host': 'node1.ceph.com',
                'subnet': '10.20.188.0/24'
            },
            'updates': {
                'enabled': True,
                'reboot': True
            }})

        self.shell.run_cmdline('/time_server/subnet reset')
        self.shell.run_cmdline('/time_server/server_hostname reset')
        self.shell.run_cmdline('/ceph_cluster/roles/admin remove node1.ceph.com')
        self.shell.run_cmdline('/ceph_cluster/roles/cephadm remove node2.ceph.com')
        self.shell.run_cmdline('/ceph_cluster/roles/cephadm remove node1.ceph.com')
        self.shell.run_cmdline('/ceph_cluster/minions remove node2.ceph.com')
        self.shell.run_cmdline('/ceph_cluster/minions remove node1.ceph.com')

    def test_import(self):
        self.fs.create_file('/config.json', contents=json.dumps({
            'minions': {
                'all': ['node1.ceph.com', 'node2.ceph.com'],
                'admin': ['node1.ceph.com']
            },
            'time_server': {
                'server_host': 'node1.ceph.com',
                'subnet': '10.20.188.0/24'
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
        self.assertEqual(PillarManager.get('ceph-salt:minions:all'), ['node1.ceph.com',
                                                                      'node2.ceph.com'])
        self.assertEqual(PillarManager.get('ceph-salt:minions:admin'), ['node1.ceph.com'])
        self.assertIsNone(PillarManager.get('ceph-salt:bootstrap_minion'))
        self.assertEqual(PillarManager.get('ceph-salt:time_server:server_host'), 'node1.ceph.com')
        self.assertEqual(PillarManager.get('ceph-salt:time_server:subnet'), '10.20.188.0/24')

        self.shell.run_cmdline('/time_server/subnet reset')
        self.shell.run_cmdline('/time_server/server_hostname reset')
        self.shell.run_cmdline('/ceph_cluster/roles/admin remove node1.ceph.com')
        self.shell.run_cmdline('/ceph_cluster/minions remove node2.ceph.com')
        self.shell.run_cmdline('/ceph_cluster/minions remove node1.ceph.com')

        self.fs.remove('/config.json')

    def test_import_invalid_host(self):
        self.fs.create_file('/config.json', contents=json.dumps({
            'minions': {
                'all': ['node1.ceph.com', 'node2.ceph.com', 'node9.ceph.com'],
                'admin': ['node1.ceph.com']
            }}))

        self.assertFalse(run_import("/config.json"))
        self.assertInSysOut("Cannot find minion 'node9.ceph.com'")

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
        self.assertInSysOut('Parameters reset.')
        self.assertEqual(PillarManager.get(sec_pillar_key), None)

        self.shell.run_cmdline('{} reset'.format(path))
        self.assertInSysOut('Config reset.')
        self.assertEqual(PillarManager.get(pillar_key), None)

    def assertFlagOption(self, path, pillar_key, default=None, reset_supported=True):
        self.shell.run_cmdline('{} enable'.format(path))
        self.assertInSysOut('Enabled.')
        self.assertEqual(PillarManager.get(pillar_key), True)

        self.shell.run_cmdline('{} disable'.format(path))
        self.assertInSysOut('Disabled.')
        self.assertEqual(PillarManager.get(pillar_key), False)

        if reset_supported:
            self.shell.run_cmdline('{} reset'.format(path))
            self.assertInSysOut('Value reset.')
            self.assertEqual(PillarManager.get(pillar_key), default)

    def assertImportOption(self, path, pillar_key, file_content):
        file_path = '/import.file'
        self.fs.create_file(file_path, contents=file_content)
        self.shell.run_cmdline('{} import {}'.format(path, file_path))
        self.assertInSysOut('Value imported.')
        self.assertEqual(PillarManager.get(pillar_key), file_content)

        self.shell.run_cmdline('{} export'.format(path))
        self.assertInSysOut(file_content)

        self.shell.run_cmdline('{} reset'.format(path))
        self.assertInSysOut('Value reset.')
        self.assertEqual(PillarManager.get(pillar_key), None)
        self.fs.remove(file_path)

    def assertValueOption(self, path, pillar_key, value, default=None):
        self.shell.run_cmdline('{} set {}'.format(path, value))
        self.assertInSysOut('Value set.')
        self.assertEqual(PillarManager.get(pillar_key), value)

        self.shell.run_cmdline('{} reset'.format(path))
        self.assertInSysOut('Value reset.')
        self.assertEqual(PillarManager.get(pillar_key), default)

    def assertDictOption(self, path, pillar_key, parameter, value):
        self.shell.run_cmdline('{} set "{}" "{}"'.format(path, parameter, value))
        self.assertInSysOut('Parameter set.')
        self.assertEqual(PillarManager.get('{}:{}'.format(pillar_key, parameter)), value)

        self.shell.run_cmdline('{} remove {}'.format(path, parameter))
        self.assertInSysOut('Parameter removed.')
        self.assertEqual(PillarManager.get('{}:{}'.format(pillar_key, parameter)), None)

    def assertListOption(self, path, pillar_key, values):
        for value in values:
            self.shell.run_cmdline('{} add {}'.format(path, value))
            self.assertInSysOut('Value added.')
        self.assertEqual(PillarManager.get(pillar_key), values)

        for value in values:
            self.shell.run_cmdline('{} remove {}'.format(path, value))
            self.assertInSysOut('Value removed.')
        self.assertEqual(PillarManager.get(pillar_key), [])

    def assertListDictOption(self, path, pillar_key, values, check_values):
        for value in values:
            self.shell.run_cmdline('{} add {}'.format(path, value))
            self.assertInSysOut('Item added.')
        self.assertEqual(PillarManager.get(pillar_key), check_values)

        for value in values:
            self.shell.run_cmdline('{} remove {}'.format(path, value))
            self.assertInSysOut('item(s) removed.')
        self.assertEqual(PillarManager.get(pillar_key), [])
