from ceph_salt.core import CephNode
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
        self.assertValidateConfig("No bootstrap minion specified in config")
        self.assertValidateConfig(None, deployed=True)

    def test_no_admin_minion(self):
        PillarManager.set('ceph-salt:minions:admin', [])
        self.assertValidateConfig("No admin minion specified in config")

    def test_bootstrap_minion_is_not_cephadm(self):
        PillarManager.set('ceph-salt:minions:admin', ['node2.ceph.com'])
        PillarManager.set('ceph-salt:minions:cephadm', ['node2.ceph.com'])
        self.assertValidateConfig("Bootstrap minion must have 'cephadm' role")
        self.assertValidateConfig(None, deployed=True)

    def test_ssh_no_private_key(self):
        PillarManager.reset('ceph-salt:ssh:private_key')
        self.assertValidateConfig("No SSH private key specified in config")

    def test_ssh_no_public_key(self):
        PillarManager.reset('ceph-salt:ssh:public_key')
        self.assertValidateConfig("No SSH public key specified in config")

    def test_ssh_invalid_key_pair(self):
        public_key = """ssh-rsa AAAAB3NzaC1yc2EAAAADAQABAAABAQCrI0b980egkmfqFQcsYWrqb2TR3QX/dL+\
HA5UDa0RFLiOW0xh0liHqd02NZ3j4AoQsh6MSanrROAC2g/cYNDeLo/DR3NXTOPsIhwOkGCncFaOkraVZ/+ZoLsh\
8FFXPVz761PgbuzUmz5cQ+IAVSMS5YColvPaynLNtsDQqGwdiL9jB411HbiNnC0oiqU4FpPTa7zFq530WxrtLwee\
0P8s0ybiomlBY9m+tYNZJypz4lTPfHa9XHWRn5nxFiqiR5yswRRXeZDAEPBXgN9maIC1Rj2mmDVGpr4v3gKf9TBD\
PBVw2pLCZsH5ol3VJ1/DETsGRMzFubFeTUNOC3MzhhG+V"""
        PillarManager.set('ceph-salt:ssh:public_key', public_key)
        self.assertValidateConfig("Invalid SSH key pair")

    def test_no_bootstrap_mon_ip(self):
        PillarManager.reset('ceph-salt:bootstrap_mon_ip')
        self.assertValidateConfig("No bootstrap Mon IP specified in config")

    def test_loopback_bootstrap_mon_ip(self):
        PillarManager.set('ceph-salt:bootstrap_mon_ip', '127.0.0.1')
        self.assertValidateConfig("Mon IP cannot be the loopback interface IP")

    def test_not_found_bootstrap_mon_ip(self):
        PillarManager.set('ceph-salt:bootstrap_mon_ip', '10.20.188.101')
        self.assertValidateConfig("Mon IP '10.20.188.101' is not an IP of the bootstrap minion "
                                  "'node1.ceph.com'")

    def test_no_dashboard_username(self):
        PillarManager.reset('ceph-salt:dashboard:username')
        self.assertValidateConfig("No dashboard username specified in config")

    def test_no_dashboard_password(self):
        PillarManager.reset('ceph-salt:dashboard:password')
        self.assertValidateConfig("No dashboard password specified in config")

    def test_dashboard_ssl_certificate(self):
        PillarManager.reset('ceph-salt:dashboard:ssl_certificate_key')
        self.assertValidateConfig("Dashboard SSL certificate provided, "
                                  "but no SSL certificate key specified")

    def test_dashboard_ssl_certificate_key(self):
        PillarManager.reset('ceph-salt:dashboard:ssl_certificate')
        self.assertValidateConfig("Dashboard SSL certificate key provided, "
                                  "but no SSL certificate specified")

    def test_dashboard_password_update_required_not_set(self):
        PillarManager.reset('ceph-salt:dashboard:password_update_required')
        self.assertValidateConfig("'ceph-salt:dashboard:password_update_required' "
                                  "must be of type Boolean")

    def test_time_server_enabled_not_set(self):
        PillarManager.reset('ceph-salt:time_server:enabled')
        self.assertValidateConfig("'ceph-salt:time_server:enabled' must be of type Boolean")

    def test_no_time_server_host(self):
        PillarManager.reset('ceph-salt:time_server:server_host')
        self.assertValidateConfig("No time server host specified in config")

    def test_no_time_server_subnet(self):
        PillarManager.reset('ceph-salt:time_server:subnet')
        self.assertValidateConfig("No time server subnet specified in config")

    def test_no_external_time_servers(self):
        PillarManager.reset('ceph-salt:time_server:external_time_servers')
        self.assertValidateConfig("No external time servers specified in config")

    def test_time_server_not_a_minion(self):
        not_minion_err = ('Time server is not a minion: {} '
                          'setting will not have any effect')
        PillarManager.set('ceph-salt:time_server:server_host', 'foo.example.com')
        PillarManager.reset('ceph-salt:time_server:external_time_servers')
        self.assertValidateConfig(not_minion_err.format('time server subnet'))
        PillarManager.reset('ceph-salt:time_server:subnet')
        PillarManager.set('ceph-salt:time_server:external_time_servers', ['pool.ntp.org'])
        self.assertValidateConfig(not_minion_err.format('external time servers'))

    def test_cephadm_not_cluster_minion(self):
        PillarManager.set('ceph-salt:minions:cephadm', ['node1.ceph.com', 'node4.ceph.com'])
        self.assertValidateConfig("Minion 'node4.ceph.com' has 'cephadm' role "
                                  "but is not a cluster minion")

    def test_admin_without_cephadm_role(self):
        PillarManager.set('ceph-salt:bootstrap_minion', 'node2.ceph.com')
        PillarManager.set('ceph-salt:bootstrap_mon_ip', '10.20.188.202')
        PillarManager.set('ceph-salt:minions:cephadm', ['node2.ceph.com'])
        PillarManager.set('ceph-salt:minions:admin', ['node3.ceph.com'])
        self.assertValidateConfig("Minion 'node3.ceph.com' has 'admin' role "
                                  "but not 'cephadm' role")

    def test_latency_without_cephadm_role(self):
        PillarManager.set('ceph-salt:bootstrap_minion', 'node2.ceph.com')
        PillarManager.set('ceph-salt:bootstrap_mon_ip', '10.20.188.202')
        PillarManager.set('ceph-salt:minions:admin', ['node2.ceph.com'])
        PillarManager.set('ceph-salt:minions:cephadm', ['node2.ceph.com'])
        PillarManager.set('ceph-salt:minions:latency', ['node3.ceph.com'])
        self.assertValidateConfig("Minion 'node3.ceph.com' has 'latency' role "
                                  "but not 'cephadm' role")

    def test_throughput_without_cephadm_role(self):
        PillarManager.set('ceph-salt:bootstrap_minion', 'node2.ceph.com')
        PillarManager.set('ceph-salt:bootstrap_mon_ip', '10.20.188.202')
        PillarManager.set('ceph-salt:minions:admin', ['node2.ceph.com'])
        PillarManager.set('ceph-salt:minions:cephadm', ['node2.ceph.com'])
        PillarManager.set('ceph-salt:minions:throughput', ['node3.ceph.com'])
        self.assertValidateConfig("Minion 'node3.ceph.com' has 'throughput' role "
                                  "but not 'cephadm' role")

    def test_latency_and_throughput_roles(self):
        PillarManager.set('ceph-salt:bootstrap_minion', 'node2.ceph.com')
        PillarManager.set('ceph-salt:bootstrap_mon_ip', '10.20.188.202')
        PillarManager.set('ceph-salt:minions:admin', ['node2.ceph.com'])
        PillarManager.set('ceph-salt:minions:cephadm', ['node2.ceph.com'])
        PillarManager.set('ceph-salt:minions:latency', ['node2.ceph.com'])
        PillarManager.set('ceph-salt:minions:throughput', ['node2.ceph.com'])
        self.assertValidateConfig("Minion 'node2.ceph.com' has both 'latency' "
                                  "and 'throughput' roles")

    def test_incomplete_registry_auth(self):
        PillarManager.set('ceph-salt:container:auth:username', 'testuser')
        self.assertValidateConfig("Registry auth configuration is incomplete")
        PillarManager.set('ceph-salt:container:auth:password', 'testpassword')
        self.assertValidateConfig("Registry auth configuration is incomplete")
        PillarManager.set('ceph-salt:container:auth:registry', '172.17.0.1:5000')
        self.assertValidateConfig(None)

    def test_no_ceph_container_image_path(self):
        PillarManager.reset('ceph-salt:container:images:ceph')
        self.assertValidateConfig("No Ceph container image path specified in config")

    def test_ceph_container_image_relative_path(self):
        PillarManager.set('ceph-salt:container:images:ceph', 'ceph/ceph:v15.2.2')
        self.assertValidateConfig("A relative image path was given, but only absolute image "
                                  "paths are supported")

    def test_valid(self):
        self.assertValidateConfig(None)

    # pylint: disable=invalid-name
    def assertValidateConfig(self, expected, deployed=False, ceph_nodes=None):
        if ceph_nodes is None:
            ceph_nodes = {}
            all = PillarManager.get('ceph-salt:minions:all', [])
            for i, minion_id in enumerate(all):
                ceph_node = CephNode(minion_id)
                # pylint: disable=protected-access
                ceph_node._ipsv4 = ['10.20.188.{}'.format(201 + i)]
                # pylint: disable=protected-access
                ceph_node._ipsv6 = ['fe80::5054:ff:fefc:{}'.format(1001 + i)]
                ceph_nodes[minion_id] = ceph_node
        self.assertEqual(validate_config(deployed, ceph_nodes), expected)

    @classmethod
    def create_valid_config(cls):
        PillarManager.set('ceph-salt:dashboard:username', 'admin1')
        PillarManager.set('ceph-salt:dashboard:password', 'admin2')
        PillarManager.set('ceph-salt:dashboard:password_update_required', True)
        PillarManager.set('ceph-salt:dashboard:ssl_certificate',
                          """-----BEGIN CERTIFICATE-----
MIIDNTCCAh2gAwIBAgIUNBWaDwDpsU7OWD1iNVDu9576ORgwDQYJKoZIhvcNAQEL
BQAwKjELMAkGA1UECgwCSVQxGzAZBgNVBAMMEmNlcGgtbWdyLWRhc2hib2FyZDAe
Fw0yMDA1MjYxNDIwMTZaFw0zMDA1MjQxNDIwMTZaMCoxCzAJBgNVBAoMAklUMRsw
GQYDVQQDDBJjZXBoLW1nci1kYXNoYm9hcmQwggEiMA0GCSqGSIb3DQEBAQUAA4IB
DwAwggEKAoIBAQCz1rqRFF4cu6by4a3bpxdt9nmAtf8yOhhUPs5dv5APvqg6E5o2
Uv5n+pR8gRpyBjVfUqEM6BAvXrLuVjXbiaJkRzbhR9YTpsVmLft6RyzyqxP9q3EN
W7QCSGwfOJJjdZ9M0iEvrAJ2C66dpDoTI65ewJYgW77COyglhj8FruiXi5q+W25V
+EbZ4aoOqbwiXyTRodPgL42WnKXSloTa1ojzKFMgaUZWjwswX6pf4qGhuIZZVuvx
P+7lpsag84mF1oZhijiKTJ9/gCmmyhEr3ZZEKxCsIXXQiVFdimbSxLXQBE9iX2EU
s1b+4iRxCsf5y7VW734svxyj++a8p4jquHc3AgMBAAGjUzBRMB0GA1UdDgQWBBSy
+awnKYIkZJnTuE65jKimjSGQGjAfBgNVHSMEGDAWgBSy+awnKYIkZJnTuE65jKim
jSGQGjAPBgNVHRMBAf8EBTADAQH/MA0GCSqGSIb3DQEBCwUAA4IBAQAf0wm2vNLy
1O97iFT0ZERnOY8U3LNebZwq2I0luSlrr02gWYK/m5CdQw1EHxERjuuuOOVDazGp
20qHJczzNowySjF1vU7wc2fzK89RQpXXlmLYl/eaH5bVCdyQ6yC/Mpka65LAqnVi
XseHg+sXSkWPftmajz2wIAsP2V1b4D3M5dR1+s6ksWLtABkoVZHW726J6wc9Cc8Q
r1BG2ZGm3Br8nfeaIY3M1A/tRTj+Y44ab1ZaFIr8sT8VwH1/TPfms1NzoydwGEkc
vmDVPjWIAnF9dV6HJ8kHOcndZyemx2yxFUI1f1DNchRxn9UO1FOITCbeX/mz8TAr
ZYUvxW5OQp8g
-----END CERTIFICATE-----""")
        PillarManager.set('ceph-salt:dashboard:ssl_certificate_key',
                          """-----BEGIN PRIVATE KEY-----
MIIEvQIBADANBgkqhkiG9w0BAQEFAASCBKcwggSjAgEAAoIBAQCz1rqRFF4cu6by
4a3bpxdt9nmAtf8yOhhUPs5dv5APvqg6E5o2Uv5n+pR8gRpyBjVfUqEM6BAvXrLu
VjXbiaJkRzbhR9YTpsVmLft6RyzyqxP9q3ENW7QCSGwfOJJjdZ9M0iEvrAJ2C66d
pDoTI65ewJYgW77COyglhj8FruiXi5q+W25V+EbZ4aoOqbwiXyTRodPgL42WnKXS
loTa1ojzKFMgaUZWjwswX6pf4qGhuIZZVuvxP+7lpsag84mF1oZhijiKTJ9/gCmm
yhEr3ZZEKxCsIXXQiVFdimbSxLXQBE9iX2EUs1b+4iRxCsf5y7VW734svxyj++a8
p4jquHc3AgMBAAECggEBAKstsAYaWf6Fi8LSl7dlU8LiggLGuXNoovHFmo7XoVur
QduN/xLIaso0VRQxmyd/y1vBffSYC5fbTvvX6Ynfd0h2FMHYq+emrWy2RhG9IAaY
Wv3xKzno2O33W5tYMNclBY2M0fPbibgtJHd+85x2MSqVrBB+45Nj1bHqF6DkPRbJ
PCoYVC11K3TOzf+x9ihOxBmvWEUnNuIjwvWoMK9KfhbiMYqIPwg3VIbrrXeebzJB
hs4wYssHnLK85LVmPXzgUODLqCR9oaaVh+BdkEepEGB/dh7fylMY8Za6IZ098Cy3
JQiVfwixRQuKg0ViyFMsgI6mZFIpbVPmps/4XZtdukECgYEA67LI0/08IHh3sFDZ
eYb5Yva01Kw1/Lwi1MgUSc9aeYU7vJcagVARiTcNtkWUqGIZ3uSOdcOpFSfhLntL
BC8gr7btpxiKmhVHme+dxs1lc8AEEwm5N6u6gS92rQxCnAW1/7s2eFGvGu43G4k7
/JpFeGV20+CJhLO4uexJQdsflOECgYEAw1Q5fMvCY1jMiq+kqXB0m3ZPjNcKwa3c
Uvhdebl7QirauO55zMaLDBhNlu7CaXGmhVixENyGZCpkrUSquqrTtQTRxjsqcS4g
yDFQIWyiXOg2T9YmAJU7EalrFyK6EimmA8hj62ZWwEdIkZNBtvcN5iBetGHxtdd3
nWEF2rzd9xcCgYAvgjgM0ux9twqZFZLgdh5qnkPQ4m13Zgy3SyUbw5n/CKYD24lS
K2t9dwViih/u2OdSEEvO3QOF6iXvkpaKX119TagVmFLHwCZQlwX8foZGkJvBoqIc
4JaVV5XaR7BddqE6zOer1PswuHePK1hWEFqUbA9JoebWQsunXkNd7OcuwQKBgEyf
xLF1CTuJwSuCfZjOeZ/myIwaa6jQuEaAEcNHhNfPEeBMBNHU7QUAn6de4DsXD1ju
Ev/nUn0GuFnUPxldHBG940DdQugFTWzbE3EZOZQyr+OfwWanI/XovQ7lW5L2bZ68
RJ46ljt1ez1IRBYvUm99MUmXxocsEEtXnUFSp8xfAoGAVr/QnNlwNoLY8LTKgfG1
BJGDcEjQZ0KwFnaPfCMTXwnWaMHfGA9k7VrDZwxpTfGQ0b2cl+tCk7by/SCmDW6k
RpDBiJHfMFDSRysZrjmuULRJvcrItRg2r3TIVuB8Wxze7Ugyb9G4hH7ZIW1y9QlG
SCzirUzUKN2oge2WieNI7MQ=
-----END PRIVATE KEY-----""")
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
        PillarManager.set('ceph-salt:container:registries_enabled', True)
        PillarManager.set('ceph-salt:container:images:ceph', 'docker.io/ceph/daemon-base:latest')
        PillarManager.set('ceph-salt:ssh:public_key', """ssh-rsa AAAAB3NzaC1yc2EAAAADAQABAAABAQ\
ClF4wYDBN6wC9Amp4xouZTDbOqZdkXxUezgbFrG1Nd+YtK7rF3sMdcE7ypKWkxwq3a/ZdWxnlAgQaCq2onXVo02/HhXrkaOf\
fH2GKzhEIw6sW0FnZ+y6XpBh6nvlD87mD8mrQbnhsjFjX+odS8gmNJOZOBxHdeWy86PHUesjttAUYwi42fWB6LkJrz74nbkp\
ueqi4w3EjuV3zSsQoAnVkCNO1ShlQYi1LeMB9EmejaGXBugAC+XsK0hn2kabRTa3ido6BbCXJDH+dkFnBKkiGQZY1Gl7+lJZ\
PkBcJB7nz233ba8bgrT0uSSu3fyWnnobKjnuas9lakvRedwKIy8LjZ""")
        PillarManager.set('ceph-salt:ssh:private_key',
                          """-----BEGIN RSA PRIVATE KEY-----
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
