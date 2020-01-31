import logging
import shutil
import subprocess

from salt.exceptions import SaltException

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


class CephSaltFormulaNotInstalled(ValidationException):
    def __init__(self):
        super(CephSaltFormulaNotInstalled, self).__init__("ceph-salt formula is not installed")


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


def check_salt_master_communication():
    try:
        logger.info("running test.ping in salt-master")
        result = SaltClient.caller(False).cmd('test.ping')
        logger.info("test.ping result: %s", result)
    except SaltException as ex:
        logger.exception(ex)
        logger.error("failed to run test.ping in salt-master")
        raise SaltMasterCommError(str(ex))


def check_ceph_salt_formula_installed():
    logger.info("checking if ceph-salt formula is installed")
    try:
        result = SaltClient.caller(False).cmd('state.sls_exists', ['ceph-salt'])
        if not result:
            logger.error("ceph-salt formula is not installed")
            raise CephSaltFormulaNotInstalled()
    except SaltException as ex:
        logger.exception(ex)
        logger.error("failed to run state.sls_exists in salt-master")
        raise SaltMasterCommError(str(ex))


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
    check_salt_master_communication()
    check_ceph_salt_pillar()
