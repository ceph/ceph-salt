import contextlib

from ..exceptions import ValidationException
from ..salt_utils import SaltClient


class UnableToSyncAll(ValidationException):
    def __init__(self):
        super(UnableToSyncAll, self).__init__(
            "Sync failed, please run: "
            "\"salt -G 'ceph-salt:member' saltutil.sync_all\" manually and fix "
            "the problems reported")


class UnableToSyncModules(ValidationException):
    def __init__(self, target):
        super(UnableToSyncModules, self).__init__(
            "Sync failed, please run: "
            "\"salt -G '{}' saltutil.sync_modules\" manually and fix "
            "the problems reported".format(target))


def sync_all():
    with contextlib.redirect_stdout(None):
        result = SaltClient.local_cmd('ceph-salt:member', 'saltutil.sync_all', tgt_type='grain')
    for minion, value in result.items():
        if not value:
            raise UnableToSyncAll()


def sync_modules(target='ceph-salt:member'):
    with contextlib.redirect_stdout(None):
        result = SaltClient.local_cmd(target, 'saltutil.sync_modules', tgt_type='grain')
    for value in result:
        if not value:
            raise UnableToSyncModules(target)
