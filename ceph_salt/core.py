import copy
import logging
import base64
import hashlib

from Cryptodome.PublicKey import RSA
import salt

from .exceptions import CephNodeHasRolesException
from .salt_utils import GrainsManager, PillarManager, SaltClient


logger = logging.getLogger(__name__)


CEPH_SALT_GRAIN_KEY = 'ceph-salt'


class CephNode:
    def __init__(self, minion_id):
        self.minion_id = minion_id
        self._ipsv4 = None
        self._ipsv6 = None
        self._hostname = None
        self._roles = None
        self._execution = None
        self._public_ip = None
        self._subnets = None
        self._public_subnet = None

    @property
    def ipsv4(self):
        if self._ipsv4 is None:
            result = GrainsManager.get_grain(self.minion_id, 'ipv4')
            self._ipsv4 = result[self.minion_id]
        return self._ipsv4

    @property
    def ipsv6(self):
        if self._ipsv6 is None:
            result = GrainsManager.get_grain(self.minion_id, 'ipv6')
            self._ipsv6 = result[self.minion_id]
        return self._ipsv6

    @property
    def hostname(self):
        if self._hostname is None:
            result = GrainsManager.get_grain(self.minion_id, 'host')
            self._hostname = result[self.minion_id]
        return self._hostname

    @property
    def public_ip(self):
        if self._public_ip is None:
            result = GrainsManager.get_grain(self.minion_id, 'fqdn_ip4')
            _public_ip = result[self.minion_id][0]
            if _public_ip == '127.0.0.1':
                logger.debug('fqdn_ipv4 grain is 127.0.0.1, falling back to ipv4 grain')
                result = GrainsManager.get_grain(self.minion_id, 'ipv4')
                for addr in result[self.minion_id]:
                    if addr != '127.0.0.1':
                        _public_ip = addr
                        break
                if _public_ip == '127.0.0.1':
                    logger.warning("'%s' public IP is the loopback interface IP ('127.0.0.1')",
                                   self.minion_id)
            self._public_ip = _public_ip
        return self._public_ip

    @property
    def subnets(self):
        if self._subnets is None:
            result = SaltClient.local_cmd(self.minion_id, 'network.subnets')
            self._subnets = result[self.minion_id]
        return self._subnets

    @property
    def public_subnet(self):
        if self._public_subnet is None:
            if self.public_ip and self.subnets:
                for subnet in self.subnets:
                    if salt.utils.network.in_subnet(subnet, self.public_ip):
                        self._public_subnet = subnet
                        break
        return self._public_subnet

    @property
    def roles(self):
        if self._roles is None:
            roles = PillarManager.get('ceph-salt:minions', {})
            _roles = set()
            for role, minions in roles.items():
                if role != 'all' and self.minion_id in minions:
                    _roles.add(role)
            self._roles = _roles
        return self._roles

    @property
    def execution(self):
        if self._execution is None:
            result = GrainsManager.get_grain(self.minion_id, CEPH_SALT_GRAIN_KEY)
            self._execution = {}
            if 'execution' in result[self.minion_id]:
                self._execution = result[self.minion_id]['execution']
        return self._execution

    def add_role(self, role):
        self.roles.add(role)

    def _role_list(self):
        role_list = list(self.roles)
        role_list.sort()
        return role_list

    def _grains_value(self):
        return {
            'member': True,
            'execution': self.execution,
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
        minions = [n.minion_id for n in cls._ceph_salt_nodes.values()]
        PillarManager.set('ceph-salt:minions:all', minions)
        PillarManager.set('ceph-salt:minions:admin',
                          [n.minion_id for n in cls._ceph_salt_nodes.values()
                           if 'admin' in n.roles])
        PillarManager.set('ceph-salt:minions:cephadm',
                          [n.minion_id for n in cls._ceph_salt_nodes.values()
                           if 'cephadm' in n.roles])
        PillarManager.set('ceph-salt:minions:latency',
                          [n.minion_id for n in cls._ceph_salt_nodes.values()
                           if 'latency' in n.roles])
        PillarManager.set('ceph-salt:minions:throughput',
                          [n.minion_id for n in cls._ceph_salt_nodes.values()
                           if 'throughput' in n.roles])

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
        roles = cls.all_roles(cls._ceph_salt_nodes[minion_id])
        if roles:
            raise CephNodeHasRolesException(minion_id, sorted(roles))
        del cls._ceph_salt_nodes[minion_id]
        GrainsManager.del_grain(minion_id, CEPH_SALT_GRAIN_KEY)
        cls.save_in_pillar()

    @classmethod
    def list_all_minions(cls):
        return SaltClient.caller().cmd('minion.list')['minions']

    @staticmethod
    def all_roles(ceph_salt_node):
        roles = copy.deepcopy(ceph_salt_node.roles)
        bootstrap_minion = PillarManager.get('ceph-salt:bootstrap_minion')
        if ceph_salt_node.minion_id == bootstrap_minion:
            roles.add('bootstrap')
        return roles


class SshKeyManager:
    @staticmethod
    def key_fingerprint(key):
        key = base64.b64decode(key.split()[1].encode('ascii'))
        fp_plain = hashlib.md5(key).hexdigest()
        return ':'.join(a + b for a, b in zip(fp_plain[::2], fp_plain[1::2]))

    @staticmethod
    def generate_key_pair(bits=2048):
        key = RSA.generate(bits)
        private_key = key.exportKey('PEM')
        public_key = key.publickey().exportKey('OpenSSH')
        return private_key.decode('utf-8'), public_key.decode('utf-8')

    @classmethod
    def check_keys(cls, stored_priv_key, stored_pub_key):
        try:
            key = RSA.import_key(stored_priv_key)
        except (ValueError, IndexError, TypeError):
            raise Exception('invalid private key')

        if not key.has_private():
            raise Exception('invalid private key')

        pub_key = key.publickey().exportKey('OpenSSH').decode('utf-8')
        if not stored_pub_key or pub_key.split()[1] != stored_pub_key.split()[1]:
            raise Exception('key pair does not match')

    @classmethod
    def check_public_key(cls, stored_priv_key, stored_pub_key):
        if not stored_pub_key:
            raise Exception('no public key set')
        if not stored_priv_key:
            raise Exception('private key does not match')
        try:
            cls.check_keys(stored_priv_key, stored_pub_key)
        except Exception as ex:
            if str(ex) == 'key pair does not match':
                ex = Exception('private key does not match')
            raise ex

    @classmethod
    def check_private_key(cls, stored_priv_key, stored_pub_key):
        if not stored_priv_key:
            raise Exception('no private key set')
        if not stored_pub_key:
            raise Exception('public key does not match')
        try:
            cls.check_keys(stored_priv_key, stored_pub_key)
        except Exception as ex:
            if str(ex) == 'key pair does not match':
                ex = Exception('public key does not match')
            raise ex
