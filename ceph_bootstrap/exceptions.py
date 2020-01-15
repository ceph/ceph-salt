class CephBootstrapException(Exception):
    pass


class CephNodeHasRolesException(CephBootstrapException):
    def __init__(self, minion_id, roles):
        super(CephNodeHasRolesException, self).__init__(
            "Cannot remove host '{}' because it has roles defined: {}".format(minion_id, roles))


class CephNodeFqdnResolvesToLoopbackException(CephBootstrapException):
    def __init__(self, minion_id):
        super(CephNodeFqdnResolvesToLoopbackException, self).__init__(
            "Host '{}' FQDN resolves to the loopback interface IP address".format(minion_id))
