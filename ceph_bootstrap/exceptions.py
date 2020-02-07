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


class SaltCallException(CephBootstrapException):
    def __init__(self, target, func, ret):
        super(SaltCallException, self).__init__(
            "Salt call target='{}' func='{}' failed: {}".format(target, func, ret))


class ValidationException(CephBootstrapException):
    pass


class PillarFileNotPureYaml(CephBootstrapException):
    def __init__(self, top_file_path):
        super(PillarFileNotPureYaml, self).__init__(
            "Salt pillar file '{}' may contain Jinja2 expressions".format(top_file_path))


class MinionDoesNotExistInConfiguration(CephBootstrapException):
    def __init__(self, minion_id):
        super(MinionDoesNotExistInConfiguration, self).__init__(
            "Minion '{}' does not exist in configuration".format(minion_id))
