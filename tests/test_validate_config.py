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

    def test_ssh_no_private_key(self):
        PillarManager.reset('ceph-salt:ssh:private_key')
        self.assertEqual(validate_config([]), "No SSH private key specified in config")

    def test_ssh_no_public_key(self):
        PillarManager.reset('ceph-salt:ssh:public_key')
        self.assertEqual(validate_config([]), "No SSH public key specified in config")

    def test_ssh_invalid_key_pair(self):
        public_key = """ssh-rsa AAAAB3NzaC1yc2EAAAADAQABAAABAQCrI0b980egkmfqFQcsYWrqb2TR3QX/dL+\
HA5UDa0RFLiOW0xh0liHqd02NZ3j4AoQsh6MSanrROAC2g/cYNDeLo/DR3NXTOPsIhwOkGCncFaOkraVZ/+ZoLsh\
8FFXPVz761PgbuzUmz5cQ+IAVSMS5YColvPaynLNtsDQqGwdiL9jB411HbiNnC0oiqU4FpPTa7zFq530WxrtLwee\
0P8s0ybiomlBY9m+tYNZJypz4lTPfHa9XHWRn5nxFiqiR5yswRRXeZDAEPBXgN9maIC1Rj2mmDVGpr4v3gKf9TBD\
PBVw2pLCZsH5ol3VJ1/DETsGRMzFubFeTUNOC3MzhhG+V"""
        PillarManager.set('ceph-salt:ssh:public_key', public_key)
        self.assertEqual(validate_config([]), "Invalid SSH key pair")

    def test_no_bootstrap_mon_ip(self):
        PillarManager.reset('ceph-salt:bootstrap_mon_ip')
        self.assertEqual(validate_config([]), "No bootstrap Mon IP specified in config")

    def test_loopback_bootstrap_mon_ip(self):
        PillarManager.set('ceph-salt:bootstrap_mon_ip', '127.0.0.1')
        self.assertEqual(validate_config([]), "Mon IP cannot be the loopback interface IP")

    def test_no_dashboard_username(self):
        PillarManager.reset('ceph-salt:dashboard:username')
        self.assertEqual(validate_config([]), "No dashboard username specified in config")

    def test_no_dashboard_password(self):
        PillarManager.reset('ceph-salt:dashboard:password')
        self.assertEqual(validate_config([]), "No dashboard password specified in config")

    def test_dashboard_password_update_required_not_set(self):
        PillarManager.reset('ceph-salt:dashboard:password_update_required')
        self.assertEqual(validate_config([]),
                         "'ceph-salt:dashboard:password_update_required' must be of type Boolean")

    def test_updates_enabled_not_set(self):
        PillarManager.reset('ceph-salt:updates:enabled')
        self.assertEqual(validate_config([]), "'ceph-salt:updates:enabled' must be of type Boolean")

    def test_updates_reboot_not_set(self):
        PillarManager.reset('ceph-salt:updates:reboot')
        self.assertEqual(validate_config([]), "'ceph-salt:updates:reboot' must be of type Boolean")

    def test_time_server_enabled_not_set(self):
        PillarManager.reset('ceph-salt:time_server:enabled')
        self.assertEqual(validate_config([]),
                         "'ceph-salt:time_server:enabled' must be of type Boolean")

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

    def test_cephadm_not_cluster_minion(self):
        PillarManager.set('ceph-salt:minions:cephadm', ['node4.ceph.com'])
        self.assertEqual(validate_config([]),
                         "Minion 'node4.ceph.com' has 'cephadm' role but is not a cluster minion")

    def test_admin_without_cephadm_role(self):
        PillarManager.set('ceph-salt:bootstrap_minion', 'node3.ceph.com')
        PillarManager.set('ceph-salt:minions:admin', ['node3.ceph.com'])
        self.assertEqual(validate_config([]),
                         "Minion 'node3.ceph.com' has 'admin' role but not 'cephadm' role")

    def test_no_ceph_container_image_path(self):
        PillarManager.reset('ceph-salt:container:images:ceph')
        self.assertEqual(validate_config([]), "No Ceph container image path specified in config")

    def test_valid(self):
        self.assertEqual(validate_config([]), None)

    @classmethod
    def create_valid_config(cls):
        PillarManager.set('ceph-salt:dashboard:username', 'admin1')
        PillarManager.set('ceph-salt:dashboard:password', 'admin2')
        PillarManager.set('ceph-salt:dashboard:password_update_required', True)
        PillarManager.set('ceph-salt:bootstrap_minion', 'node1.ceph.com')
        PillarManager.set('ceph-salt:bootstrap_mon_ip', '10.20.188.201')
        PillarManager.set('ceph-salt:time_server:enabled', True)
        PillarManager.set('ceph-salt:time_server:server_host', 'node1.ceph.com')
        PillarManager.set('ceph-salt:time_server:external_time_servers', ['pool.ntp.org'])
        PillarManager.set('ceph-salt:time_server:subnet', '10.20.188.0/24')
        PillarManager.set('ceph-salt:minions:all', ['node1.ceph.com',
                                                    'node2.ceph.com',
                                                    'node3.ceph.com'])
        PillarManager.set('ceph-salt:minions:cephadm', ['node1.ceph.com',
                                                        'node2.ceph.com'])
        PillarManager.set('ceph-salt:minions:admin', ['node1.ceph.com'])
        PillarManager.set('ceph-salt:updates:enabled', True)
        PillarManager.set('ceph-salt:updates:reboot', True)
        PillarManager.set('ceph-salt:container:images:ceph', 'docker.io/ceph/daemon-base:latest')
        PillarManager.set('ceph-salt:ssh:public_key', """ssh-rsa AAAAB3NzaC1yc2EAAAADAQABAAABAQ\
ClF4wYDBN6wC9Amp4xouZTDbOqZdkXxUezgbFrG1Nd+YtK7rF3sMdcE7ypKWkxwq3a/ZdWxnlAgQaCq2onXVo02/HhXrkaOf\
fH2GKzhEIw6sW0FnZ+y6XpBh6nvlD87mD8mrQbnhsjFjX+odS8gmNJOZOBxHdeWy86PHUesjttAUYwi42fWB6LkJrz74nbkp\
ueqi4w3EjuV3zSsQoAnVkCNO1ShlQYi1LeMB9EmejaGXBugAC+XsK0hn2kabRTa3ido6BbCXJDH+dkFnBKkiGQZY1Gl7+lJZ\
PkBcJB7nz233ba8bgrT0uSSu3fyWnnobKjnuas9lakvRedwKIy8LjZ""")
        PillarManager.set('ceph-salt:ssh:private_key', """-----BEGIN RSA PRIVATE KEY-----
MIIEpAIBAAKCAQEApReMGAwTesAvQJqeMaLmUw2zqmXZF8VHs4GxaxtTXfmLSu6x
d7DHXBO8qSlpMcKt2v2XVsZ5QIEGgqtqJ11aNNvx4V65Gjn3x9his4RCMOrFtBZ2
fsul6QYep75Q/O5g/Jq0G54bIxY1/qHUvIJjSTmTgcR3XlsvOjx1HrI7bQFGMIuN
n1gei5Ca8++J25KbnqouMNxI7ld80rEKAJ1ZAjTtUoZUGItS3jAfRJno2hlwboAA
vl7CtIZ9pGm0U2t4naOgWwlyQx/nZBZwSpIhkGWNRpe/pSWT5AXCQe589t922vG4
K09Lkkrt38lp56Gyo57mrPZWpL0XncCiMvC42QIDAQABAoIBACnvVEebcatBe/82
By7miQjZtyR2YHGYTAE91Vo2g7OgOpCbFvsnLUynOsnhWfYo1E6HEdUZ7xzCaWvx
rLI5FTvODp/Hls8hoF3kChY9Zy7Tw8pd1lWY1xjc1BaZ0iqdRoeDqHJHc+8yqh52
7vm/SQcFmAFjbUrLcLCjQMC+Vzf1rRfOfoTM9snkuBcd0eOjvivGAQSeF4S6FPlV
XjuVPMqkXYxzVv+AUbMzwr4iPcDUJ09qx+w/S2f/h7SBgt9Jsq4dvYtQfKwS2XSP
QSE0cK7tCjVE1t0sh/2+j1ppl8LHiYS3fIeLAkCnnm9jhVPddtgImp9GlL+qx70Y
40DDbn0CgYEAvSKahj8hswDnH433jf8NQEcjcb3CHqfUjmZrG/qLi1uMsaUp7ICU
wMc6MCgGcMFsC11g2PvGIvwaACBIpjWM/7cGxnomYWYeOjluhQdb1PB+KYX5mSPL
RRYq0kSNiJeqUFGj+9xfoVFGfpYIdtCUqUy9eGVyhYTLH0vxJz91l3sCgYEA33Tz
YG0Xj/1zvFPO+GD+cn5Sm4AEpiYxVuk7EGj1jEPVtA9l+nUUpbBV0U92a+pzuX/f
q0n7Zy+THAC0Q6qdzsKHcy6vPeHECF49G29qXxaQ3sHop8316rAqu7BpdL4xn9XT
Qp7g/1ivrzMWRZpt/BtEnBe7XMUZLZNzPJ0LlrsCgYEAoyiu1RCxKZKlz3rRDBXy
gHjeAskIJRnzK8T+sWw55UZc4QLyX6usp4E2mURuCedSJZuwaH8KNjP02hb/lSKt
OAvUNHQ7l9pYSTIyPWBTwCaXL4r7/zf5quesmSe6URNFQXSsWiGJ/cf3YExdkOHu
3P3ulWYunTApah5BMvJzpvECgYEAgIeEdbJKG0htiaWrJrKjqLeATHEWO3s8ZgFB
N+8nTca25Rr2TVmKxsLmmb5bHzd72Pb0cFHdiTyUIUdGaKV6n7LEtjvkEHQLjcSm
4WD0jj0slvRyHhMZoCQ0cEDIZ53+bTFQksFQKY+ZfeykouRw3tHQZPhBjNrR4KUv
Y23xfIECgYBDFQLNOS7Tz0+TGZaAOce7oRV5HWyW+AFrpyxavw+YbE3s37IDvcdU
EwiXg1NW1KlU9Q2bjWRXJ0tPQO+EyRQ0pn7yXA53xhBxVYW4T4KAqK6AFsiJQncf
+x5J3qK6+KAfo07TBNG1aIBQfY346EaUc20aRHFfnad9EF4KAmgszA==
-----END RSA PRIVATE KEY-----""")
