import subprocess

from mock import patch
from salt.exceptions import SaltException

from ceph_bootstrap.validate.salt_master import check_salt_master, SaltMasterNotInstalled, \
    NoSaltMasterProcess, SaltMasterCommError, check_salt_master_communication, \
    check_ceph_salt_pillar, NoPillarDirectoryConfigured, CephSaltPillarNotConfigured

from . import SaltMockTestCase


# pylint: disable=unused-argument


class ValidateSaltMasterTest(SaltMockTestCase):

    @patch('shutil.which', return_value=None)
    def test_salt_master_installed(self, *args):
        with self.assertRaises(SaltMasterNotInstalled) as ctx:
            check_salt_master()

        self.assertEqual(str(ctx.exception), "salt-master is not installed")

    @patch('shutil.which', return_value="/usr/bin/salt-master")
    @patch('subprocess.check_output', return_value="0")
    def test_salt_master_running(self, *args):
        with self.assertRaises(NoSaltMasterProcess) as ctx:
            check_salt_master()

        self.assertEqual(str(ctx.exception), "No salt-master process is running")

    @patch('shutil.which', return_value="/usr/bin/salt-master")
    @patch('subprocess.check_output', side_effect=subprocess.CalledProcessError(1, "pgrep"))
    def test_salt_master_running_exception(self, *args):
        with self.assertRaises(NoSaltMasterProcess) as ctx:
            check_salt_master()

        self.assertEqual(str(ctx.exception), "No salt-master process is running")

    @patch('shutil.which', return_value="/usr/bin/salt-master")
    @patch('subprocess.check_output', return_value="1")
    def test_salt_master_ok(self, *args):
        check_salt_master()

    def test_salt_master_comm_ping(self):
        def cmd(*args, **kwargs):
            raise SaltException('testing')
        self.caller_client.cmd = cmd

        with self.assertRaises(SaltMasterCommError) as ctx:
            check_salt_master_communication()

        self.assertEqual(str(ctx.exception), "Failed to communicate with salt-master: testing")

    def test_salt_master_comm_ok(self):
        check_salt_master_communication()

    def test_ceph_salt_pillar_directory(self):
        self.master_config.opts = {}
        with self.assertRaises(NoPillarDirectoryConfigured) as ctx:
            check_ceph_salt_pillar()

        self.assertEqual(str(ctx.exception),
                         "Salt master 'pillar_roots' configuration does not have any directory")

    def test_ceph_salt_pillar_installed(self):
        self.fs.remove_object('/srv/pillar/ceph-salt.sls')
        with self.assertRaises(CephSaltPillarNotConfigured) as ctx:
            check_ceph_salt_pillar()

        self.assertEqual(str(ctx.exception), "ceph-salt pillar not configured")
        self.fs.create_file('/srv/pillar/ceph-salt.sls')
