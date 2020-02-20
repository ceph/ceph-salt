class CephSaltException(Exception):
    pass


class CephNodeHasRolesException(CephSaltException):
    def __init__(self, minion_id, roles):
        super(CephNodeHasRolesException, self).__init__(
            "Cannot remove host '{}' because it has roles defined: {}".format(minion_id, roles))


class CephNodeFqdnResolvesToLoopbackException(CephSaltException):
    def __init__(self, minion_id):
        super(CephNodeFqdnResolvesToLoopbackException, self).__init__(
            "Host '{}' FQDN resolves to the loopback interface IP address".format(minion_id))


class SaltCallException(CephSaltException):
    def __init__(self, target, func, ret):
        super(SaltCallException, self).__init__(
            "Salt call target='{}' func='{}' failed: {}".format(target, func, ret))


class ValidationException(CephSaltException):
    pass


class PillarFileNotPureYaml(CephSaltException):
    def __init__(self, top_file_path):
        super(PillarFileNotPureYaml, self).__init__(
            "Salt pillar file '{}' may contain Jinja2 expressions".format(top_file_path))


class MinionDoesNotExistInConfiguration(CephSaltException):
    def __init__(self, minion_id):
        super(MinionDoesNotExistInConfiguration, self).__init__(
            "Minion '{}' does not exist in configuration".format(minion_id))
