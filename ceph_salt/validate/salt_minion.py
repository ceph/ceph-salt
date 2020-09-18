import contextlib

from ..exceptions import ValidationException
from ..salt_utils import SaltClient


class UnableToSyncAll(ValidationException):
    def __init__(self):
        super(UnableToSyncAll, self).__init__(
            "Sync failed, please run: "
            "\"salt -G 'ceph-salt:member' saltutil.sync_all\" manually and fix "
            "the problems reported")


def sync_all():
    with contextlib.redirect_stdout(None):
        result = SaltClient.local_cmd('ceph-salt:member', 'saltutil.sync_all', tgt_type='grain')
    for minion, value in result.items():
        if not value:
            raise UnableToSyncAll()
