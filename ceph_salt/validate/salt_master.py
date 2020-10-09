import logging
import shutil
import subprocess

from ..exceptions import ValidationException
from ..salt_utils import SaltClient, PillarManager


logger = logging.getLogger(__name__)


class NoSaltMasterProcess(ValidationException):
    def __init__(self):
        super(NoSaltMasterProcess, self).__init__('No salt-master process is running')


class SaltMasterNotInstalled(ValidationException):
    def __init__(self):
        super(SaltMasterNotInstalled, self).__init__('salt-master is not installed')


class SaltMasterCommError(ValidationException):
    def __init__(self, salt_exception_error):
        super(SaltMasterCommError, self).__init__("Failed to communicate with salt-master: {}"
                                                  .format(salt_exception_error))


class NoPillarDirectoryConfigured(ValidationException):
    def __init__(self):
        super(NoPillarDirectoryConfigured, self).__init__(
            "Salt master 'pillar_roots' configuration does not have any directory")


class CephSaltPillarNotConfigured(ValidationException):
    def __init__(self):
        super(CephSaltPillarNotConfigured, self).__init__("ceph-salt pillar not configured")


def check_salt_master():
    try:
        logger.info("checking if salt-master is installed")
        if shutil.which('salt-master') is None:
            logger.error('salt-master is not installed')
            raise SaltMasterNotInstalled()

        logger.info("checking if salt-master process is running")
        count = subprocess.check_output(['pgrep', '-c', 'salt-master'])
        if int(count) > 0:
            return
    except subprocess.CalledProcessError as ex:
        logger.exception(ex)
    logger.error("no salt-master process found")
    raise NoSaltMasterProcess()


def check_ceph_salt_pillar():
    logger.info("checking if pillar directory is configured")
    if not SaltClient.pillar_fs_path():
        logger.info("salt-master pillar_roots configuration does not have any directory")
        raise NoPillarDirectoryConfigured()

    logger.info("checking if ceph-salt pillar is correctly configured")
    if not PillarManager.pillar_installed():
        logger.error("ceph-salt is not present in the pillar")
        raise CephSaltPillarNotConfigured()


def check_salt_master_status():
    check_salt_master()
    check_ceph_salt_pillar()
