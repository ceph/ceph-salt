class SesBootException(Exception):
    pass


class SesNodeHasRolesException(SesBootException):
    def __init__(self, minion_id, roles):
        super(SesNodeHasRolesException, self).__init__(
            "Cannot remove host '{}' because it has roles defined: {}".format(minion_id, roles))
