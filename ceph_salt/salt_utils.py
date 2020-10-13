import contextlib
import copy
import logging
import os
import shutil

import yaml

import salt.client
import salt.minion
from salt.exceptions import SaltException

from .exceptions import CephSaltException, SaltCallException, PillarFileNotPureYaml


logger = logging.getLogger(__name__)


class SaltClient:

    @classmethod
    def _opts(cls, local=True):
        """
        Retrieves the Salt opts structure
        """
        _opts = salt.config.master_config('/etc/salt/master')
        if local:
            _opts['file_client'] = 'local'
        return _opts

    @classmethod
    def caller(cls, local=True):
        """
        Retrieves a new Salt caller client instance
        """
        return salt.client.Caller(mopts=cls._opts(local))

    @classmethod
    def local(cls):
        """
        Retrieves a new Salt local client instance
        """
        return salt.client.LocalClient()

    @classmethod
    def master(cls, local=True):
        return salt.minion.MasterMinion(cls._opts(local))

    @classmethod
    def pillar_fs_path(cls):
        pillar_dirs = cls._opts().get('pillar_roots', {'base': []})['base']
        if not pillar_dirs:
            return None
        return pillar_dirs[0]

    @classmethod
    def pki_minions_fs_path(cls):
        pki_dir = cls._opts().get('pki_dir', '/etc/salt/pki/master')
        return '{}/minions'.format(pki_dir)

    @classmethod
    def local_cmd(cls, target, func, args=None, tgt_type='glob', full_return=False):
        """
        Equal to `local().cmd(...)`, but with proper error checking.

        Note that Salt 'salt.client.LocalClient().cmd(...)' will return 'False' when minion is
        down, so if we need to distinguish between "'False' because return value is 'False'"
        and "'False' because minion is down" we need to use 'full_return=True'
        """
        if args is None:
            args = []
        try:
            result = cls.local().cmd(target, func, args, tgt_type=tgt_type,
                                     full_return=full_return)
            if result is None or not isinstance(result, dict):
                raise SaltCallException(target, func, result)
            # Result example when full_return, but minion is down: {'node1': False, ...}
            if full_return:
                for value in result.values():
                    if not isinstance(value, dict):
                        raise SaltCallException(target, func, result)
            if isinstance(target, str) \
                    and tgt_type == 'glob' \
                    and not any(c in target for c in '*?[]') \
                    and target not in result:
                raise SaltCallException(target, func, 'minion not in result: ' + result)

        except SaltException as ex:
            logger.exception(ex)
            raise SaltCallException(target, func, result)
        return result

    @classmethod
    def caller_cmd(cls, func, args=None):
        if args is None:
            args = []
        try:
            result = cls.caller(False).cmd(func, args)
        except SaltException as ex:
            logger.exception(ex)
            raise SaltCallException('master', func, result)
        return result


class GrainsManager:
    logger = logging.getLogger(__name__ + '.grains')

    @classmethod
    def _format_target(cls, target):
        tgt_type = 'glob'
        if isinstance(target, set):
            target = list(target)
        if isinstance(target, list):
            tgt_type = 'list'
        return target, tgt_type

    @classmethod
    def set_grain(cls, target, key, val):
        target, tgt_type = cls._format_target(target)
        cls.logger.debug("Adding '%s = %s' grain to %s", key, val, target)
        with contextlib.redirect_stdout(None):
            ret = SaltClient.local_cmd(target, 'grains.setval', [key, val], tgt_type=tgt_type,
                                       full_return=True)
        result = {minion: data.get('ret') for minion, data in ret.items()}
        cls.logger.info("Added '%s = %s' grain to %s: result=%s", key, val, target, result)

    @classmethod
    def del_grain(cls, target, key):
        target, tgt_type = cls._format_target(target)
        cls.logger.debug("Deleting '%s' grain from %s", key, target)
        with contextlib.redirect_stdout(None):
            ret = SaltClient.local_cmd(target, 'grains.delkey', [key], tgt_type=tgt_type,
                                       full_return=True)
        result = {minion: data.get('ret') for minion, data in ret.items()}
        cls.logger.info("Deleted '%s' grain from %s: result=%s", key, target, result)

    @classmethod
    def filter_by(cls, key, val=None):
        condition = '{}:{}'.format(key, val if val else '*')
        with contextlib.redirect_stdout(None):
            result = SaltClient.local_cmd(condition, 'test.true', tgt_type='grain',
                                          full_return=True)
        logger.debug("list of minions that match '%s': %s", condition, list(result))
        return list(result)

    @classmethod
    def get_grain(cls, target, key):
        target, tgt_type = cls._format_target(target)
        cls.logger.debug("Getting '%s' grain from %s", key, target)
        with contextlib.redirect_stdout(None):
            ret = SaltClient.local_cmd(target, 'grains.get', [key], tgt_type=tgt_type,
                                       full_return=True)
        result = {minion: data.get('ret') for minion, data in ret.items()}
        cls.logger.info("Got '%s' grain from %s: result=%s", key, target, result)
        return result


class PillarManager:

    CS_TOP_FILE = "ceph-salt-top.sls"
    CS_TOP_INCLUDE = "{% include 'ceph-salt-top.sls' %}"
    CS_TOP_CONTENT = """{% import_yaml "ceph-salt.sls" as ceph_salt %}
{% set ceph_salt_minions = ceph_salt.get('ceph-salt', {}).get('minions', {}).get('all', []) %}
{% if ceph_salt_minions %}
  {{ ceph_salt_minions|join(',') }}:
    - match: list
    - ceph-salt
{% endif %}
"""
    PILLAR_FILE = "ceph-salt.sls"
    pillar_data = {}
    logger = logging.getLogger(__name__ + '.pillar')

    @classmethod
    def pillar_installed(cls):
        pillar_base_path = SaltClient.pillar_fs_path()
        # pillar
        if not os.path.exists(os.path.join(pillar_base_path, cls.PILLAR_FILE)):
            return False
        # top.sls
        if not os.path.exists(os.path.join(pillar_base_path, "top.sls")):
            return False
        with open(os.path.join(pillar_base_path, "top.sls"), "r") as top_file:
            top_contents = top_file.read()
        if cls.CS_TOP_INCLUDE not in top_contents:
            return False
        # ceph-salt-top.sls
        if not os.path.exists(os.path.join(pillar_base_path, cls.CS_TOP_FILE)):
            return False
        with open(os.path.join(pillar_base_path, cls.CS_TOP_FILE), "r") as ceph_salt_top_file:
            ceph_salt_top_contents = ceph_salt_top_file.read()
        if cls.CS_TOP_CONTENT != ceph_salt_top_contents:
            return False
        return True

    @classmethod
    def install_pillar(cls):
        pillar_base_path = SaltClient.pillar_fs_path()
        try:
            with open(os.path.join(pillar_base_path, "top.sls"), "r") as top_file:
                top_contents = top_file.read()
        except FileNotFoundError:
            top_contents = ""
        if cls.CS_TOP_INCLUDE not in top_contents:
            if 'base:' in top_contents:
                new_top_contents = top_contents.replace('base:',
                                                        'base:\n{}'.format(cls.CS_TOP_INCLUDE))
            else:
                new_top_contents = 'base:\n{}\n{}'.format(cls.CS_TOP_INCLUDE, top_contents)
            logger.info("writing top.sls file...\n[OLD]\n%s\n[NEW]\n%s",
                        top_contents, new_top_contents)
            cls._save_file(new_top_contents, "top.sls")
        logger.info("writing %s file...", cls.CS_TOP_FILE)
        cls._save_file(cls.CS_TOP_CONTENT, cls.CS_TOP_FILE)
        if not os.path.exists(os.path.join(pillar_base_path, cls.PILLAR_FILE)):
            logger.info("creating ceph-salt.sls pillar file...")
            cls._save_yaml({'ceph-salt': {}}, cls.PILLAR_FILE)

    @staticmethod
    def _get_dict_value(dict_, key_path):
        path = key_path.split(":")
        _dict = dict_
        while True:
            if len(path) == 1:
                if path[0] in _dict:
                    return _dict[path[0]]
                return None
            if path[0] in _dict:
                _dict = _dict[path[0]]
                path = path[1:]
            else:
                return None

    @staticmethod
    def _set_dict_value(dict_, key_path, value):
        path = key_path.split(":")
        _dict = dict_
        while True:
            if len(path) == 1:
                _dict[path[0]] = value
                return
            if path[0] not in _dict:
                _dict[path[0]] = {}
            _dict = _dict[path[0]]
            path = path[1:]

    @classmethod
    def _del_dict_key(cls, dict_, key_path):
        if not key_path:
            return
        path = key_path.split(":")
        _dict = dict_
        for pkey in path[:-1]:
            _dict = _dict[pkey]
        cls.logger.info("Dict current pos: %s, last_key: %s", _dict, path[-1])
        if isinstance(_dict[path[-1]], dict):
            if _dict[path[-1]]:
                return
        del _dict[path[-1]]
        cls._del_dict_key(dict_, ":".join(path[:-1]))

    @classmethod
    def _load_yaml(cls, custom_file):
        pillar_base_path = SaltClient.pillar_fs_path()
        full_path = os.path.join(pillar_base_path, custom_file)
        cls.logger.info("Reading pillar items from file: %s", full_path)
        if not os.path.exists(full_path):
            return {}
        with open(full_path, 'r') as file:
            try:
                data = yaml.full_load(file)
                if data is None:
                    data = {}
            except yaml.error.YAMLError:
                raise PillarFileNotPureYaml(full_path)
        return data

    @staticmethod
    def _save_yaml(data, custom_file):
        pillar_base_path = SaltClient.pillar_fs_path()
        full_path = os.path.join(pillar_base_path, custom_file)
        with open(full_path, 'w') as file:
            content = yaml.dump(data, default_flow_style=False)
            if content == '{}\n':
                file.write("")
            else:
                file.write(content)
            file.write("\n")
        shutil.chown(full_path, "salt", "salt")
        os.chmod(full_path, 0o600)

    @staticmethod
    def _save_file(data, custom_file):
        pillar_base_path = SaltClient.pillar_fs_path()
        full_path = os.path.join(pillar_base_path, custom_file)
        with open(full_path, 'w') as file:
            file.write(data)
        shutil.chown(full_path, "salt", "salt")
        os.chmod(full_path, 0o644)

    @classmethod
    def _load(cls):
        if not cls.pillar_data:
            cls.pillar_data = cls._load_yaml(cls.PILLAR_FILE)
            cls.logger.debug("Loaded pillar data: %s", cls.pillar_data)

    @classmethod
    def _hide_dict_secrets(cls, pillar_data):
        if not isinstance(pillar_data, dict):
            return
        for key, val in pillar_data.items():
            if key in ('private_key', 'password'):
                pillar_data[key] = '?'
            cls._hide_dict_secrets(val)

    @classmethod
    def get(cls, key, default=None):
        cls._load()
        res = cls._get_dict_value(cls.pillar_data, key)
        if key in ('ceph-salt:ssh:private_key', 'ceph-salt:dashboard:password'):
            # don't log key value
            cls.logger.info("Got '%s' from pillar", key)
        else:
            res_log = copy.deepcopy(res)
            cls._hide_dict_secrets(res_log)
            cls.logger.info("Got '%s' from pillar: '%s'", key, res_log)
        if res is None and default is not None:
            res = default

        return res

    @classmethod
    def set(cls, key, value):
        cls._load()
        cls._set_dict_value(cls.pillar_data, key, value)
        cls._save_yaml(cls.pillar_data, cls.PILLAR_FILE)
        SaltClient.local().cmd('*', 'saltutil.pillar_refresh', tgt_type="compound")
        if key in ('ceph-salt:ssh:private_key', 'ceph-salt:dashboard:password'):
            cls.logger.info("Set '%s' to pillar", key)
        else:
            value_log = copy.deepcopy(value)
            cls._hide_dict_secrets(value_log)
            cls.logger.info("Set '%s' to pillar: '%s'", key, value_log)

    @classmethod
    def reset(cls, key):
        cls._load()
        logger.debug("Deleting key '%s' from pillar", key)
        if cls._get_dict_value(cls.pillar_data, key) is None:
            return
        cls._del_dict_key(cls.pillar_data, key)
        cls._save_yaml(cls.pillar_data, cls.PILLAR_FILE)
        SaltClient.local().cmd('*', 'saltutil.pillar_refresh', tgt_type="compound")
        cls.logger.info("Deleted '%s' from pillar", key)

    @classmethod
    def reload(cls):
        cls.pillar_data = {}
        cls._load()


class CephOrch:

    @staticmethod
    def host_ls():
        with contextlib.redirect_stdout(None):
            result = SaltClient.local_cmd('ceph-salt:roles:admin', 'ceph_orch.configured',
                                          full_return=True,
                                          tgt_type='grain')
        for minion, value in result.items():
            if value.get('retcode') > 0:
                raise CephSaltException("Failed to check if ceph orch is configured "
                                        "on minion '{}'".format(minion))
            if value.get('ret') is True:
                host_ls_result = SaltClient.local_cmd(minion, 'ceph_orch.host_ls',
                                                      full_return=True)[minion]
                if value.get('retcode') > 0:
                    raise CephSaltException("Failed to list ceph orch hosts "
                                            "on minion '{}'".format(minion))
                return host_ls_result.get('ret')
        return []

    @staticmethod
    def deployed():
        with contextlib.redirect_stdout(None):
            result = SaltClient.local_cmd('ceph-salt:roles:admin', 'ceph_orch.ceph_configured',
                                          full_return=True,
                                          tgt_type='grain')
        for minion, value in result.items():
            if value.get('retcode') > 0:
                raise CephSaltException("Failed to check if ceph is configured "
                                        "on minion '{}'".format(minion))
            if value.get('ret') is True:
                return True
        return False
