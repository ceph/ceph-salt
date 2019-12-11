class CephBootstrapException(Exception):
    pass


class CephNodeHasRolesException(CephBootstrapException):
    def __init__(self, minion_id, roles):
        super(CephNodeHasRolesException, self).__init__(
            "Cannot remove host '{}' because it has roles defined: {}".format(minion_id, roles))
