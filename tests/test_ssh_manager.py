import unittest
from ceph_bootstrap.core import SshKeyManager


class SshManagerTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.priv_key, cls.pub_key = SshKeyManager.generate_key_pair()
        cls.priv_key2, cls.pub_key2 = SshKeyManager.generate_key_pair()

    def test_generate_key_pair(self):
        try:
            SshKeyManager.check_keys(self.priv_key, self.pub_key)
        except Exception:  # pylint: disable=broad-except
            self.fail('SshKeyManager.check_keys raised an Exception')

    def test_key_check_error(self):
        with self.assertRaises(Exception) as ctx:
            SshKeyManager.check_keys(self.priv_key2, self.pub_key)
        self.assertEqual(str(ctx.exception), 'key pair does not match')

    def test_key_check_error2(self):
        with self.assertRaises(Exception) as ctx:
            SshKeyManager.check_keys(self.priv_key, None)
        self.assertEqual(str(ctx.exception), 'key pair does not match')

    def test_key_check_error3(self):
        with self.assertRaises(Exception) as ctx:
            SshKeyManager.check_keys(None, None)
        self.assertEqual(str(ctx.exception), 'invalid private key')

    def test_invalid_private_key(self):
        with self.assertRaises(Exception) as ctx:
            SshKeyManager.check_keys("invalid key", None)
        self.assertEqual(str(ctx.exception), 'invalid private key')

    def test_invalid_private_key2(self):
        with self.assertRaises(Exception) as ctx:
            SshKeyManager.check_keys(self.pub_key, None)
        self.assertEqual(str(ctx.exception), 'invalid private key')

    def test_private_key_not_set(self):
        with self.assertRaises(Exception) as ctx:
            SshKeyManager.check_private_key(None, None)
        self.assertEqual(str(ctx.exception), 'no private key set')

    def test_public_key_not_set(self):
        with self.assertRaises(Exception) as ctx:
            SshKeyManager.check_public_key(None, None)
        self.assertEqual(str(ctx.exception), 'no public key set')

    def test_private_key_does_not_match(self):
        with self.assertRaises(Exception) as ctx:
            SshKeyManager.check_public_key(None, self.pub_key)
        self.assertEqual(str(ctx.exception), 'private key does not match')

    def test_private_key_does_not_match2(self):
        with self.assertRaises(Exception) as ctx:
            SshKeyManager.check_public_key(self.priv_key2, self.pub_key)
        self.assertEqual(str(ctx.exception), 'private key does not match')

    def test_public_key_does_not_match(self):
        with self.assertRaises(Exception) as ctx:
            SshKeyManager.check_private_key(self.priv_key, None)
        self.assertEqual(str(ctx.exception), 'public key does not match')

    def test_public_key_does_not_match2(self):
        with self.assertRaises(Exception) as ctx:
            SshKeyManager.check_private_key(self.priv_key2, self.pub_key)
        self.assertEqual(str(ctx.exception), 'public key does not match')

    def test_fingerprint(self):
        key = """ssh-rsa AAAAB3NzaC1yc2EAAAADAQABAAABAQCrI0b980egkmfqFQcsYWrqb2TR3QX/dL+\
HA5UDa0RFLiOW0xh0liHqd02NZ3j4AoQsh6MSanrROAC2g/cYNDeLo/DR3NXTOPsIhwOkGCncFaOkraVZ/+ZoLsh\
8FFXPVz761PgbuzUmz5cQ+IAVSMS5YColvPaynLNtsDQqGwdiL9jB411HbiNnC0oiqU4FpPTa7zFq530WxrtLwee\
0P8s0ybiomlBY9m+tYNZJypz4lTPfHa9XHWRn5nxFiqiR5yswRRXeZDAEPBXgN9maIC1Rj2mmDVGpr4v3gKf9TBD\
PBVw2pLCZsH5ol3VJ1/DETsGRMzFubFeTUNOC3MzhhG+V"""
        fingerprint = SshKeyManager.key_fingerprint(key)
        self.assertEqual(fingerprint, "7f:fe:76:1b:30:a1:54:56:ff:c3:62:a2:19:3f:40:bd")
