import logging

from .exceptions import CephNodeHasRolesException
from .salt_utils import SaltClient, GrainsManager, PillarManager


logger = logging.getLogger(__name__)


CEPH_SALT_GRAIN_KEY = 'ceph-salt'


class CephNode:
    def __init__(self, minion_id):
        self.minion_id = minion_id
        self.short_name = minion_id.split('.', 1)[0]
        self.roles = None
        self.public_ip = None
        self._load()

    def _load(self):
        result = GrainsManager.get_grain(self.minion_id, CEPH_SALT_GRAIN_KEY)
        logger.info("Loading ceph-salt node '%s': result=%s", self.minion_id, result)
        if result is None or self.minion_id not in result:
            # not yet a ceph-salt node
            self.roles = set()
        elif not isinstance(result[self.minion_id], dict) or 'roles' not in result[self.minion_id]:
            # not yet a ceph-salt node
            self.roles = set()
        else:
            self.roles = set(result[self.minion_id]['roles'])

        result = GrainsManager.get_grain(self.minion_id, 'fqdn_ip4')
        self.public_ip = result[self.minion_id][0]

    def add_role(self, role):
        self.roles.add(role)

    def _role_list(self):
        return list(self.roles)

    def _grains_value(self):
        return {
            'member': True,
            'roles': self._role_list()
        }

    def save(self):
        GrainsManager.set_grain(self.minion_id, CEPH_SALT_GRAIN_KEY, self._grains_value())


class CephNodeManager:
    _ceph_salt_nodes = {}

    @classmethod
    def _load(cls):
        if not cls._ceph_salt_nodes:
            minions = GrainsManager.filter_by(CEPH_SALT_GRAIN_KEY)
            cls._ceph_salt_nodes = {minion: CephNode(minion) for minion in minions}

    @classmethod
    def save_in_pillar(cls):
        minions = []
        for node in cls._ceph_salt_nodes.values():
            if node.roles:
                minions.append(node.short_name)
        PillarManager.set('ceph-salt:minions:all', minions)
        PillarManager.set('ceph-salt:minions:mon',
                          {n.short_name: n.public_ip for n in cls._ceph_salt_nodes.values()
                           if 'mon' in n.roles})
        PillarManager.set('ceph-salt:minions:mgr',
                          [n.short_name for n in cls._ceph_salt_nodes.values() if 'mgr' in n.roles])

        # choose the the main Mon
        minions = [n.minion_id for n in cls._ceph_salt_nodes.values() if 'mon' in n.roles]
        minions.sort()
        if minions:  # i.e., it has at least one
            PillarManager.set('ceph-salt:bootstrap_mon', minions[0])

    @classmethod
    def ceph_salt_nodes(cls):
        cls._load()
        return cls._ceph_salt_nodes

    @classmethod
    def add_node(cls, minion_id):
        cls._load()
        node = CephNode(minion_id)
        node.save()
        cls._ceph_salt_nodes[minion_id] = node
        cls.save_in_pillar()

    @classmethod
    def remove_node(cls, minion_id):
        cls._load()
        if cls._ceph_salt_nodes[minion_id].roles:
            raise CephNodeHasRolesException(minion_id, cls._ceph_salt_nodes[minion_id].roles)
        del cls._ceph_salt_nodes[minion_id]
        GrainsManager.del_grain(minion_id, CEPH_SALT_GRAIN_KEY)
        cls.save_in_pillar()

    @classmethod
    def list_all_minions(cls):
        return SaltClient.caller().cmd('minion.list')['minions']
