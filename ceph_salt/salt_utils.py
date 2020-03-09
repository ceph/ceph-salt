import contextlib
import logging
import os
import shutil

import yaml

import salt.client
import salt.minion
from salt.exceptions import SaltException

from .exceptions import SaltCallException, PillarFileNotPureYaml


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
    def local_cmd(cls, target, func, args=None, tgt_type='glob'):
        """
        Equal to `local().cmd(...)`, but with proper error checking.
        """
        if args is None:
            args = []
        try:
            result = cls.local().cmd(target, func, args, tgt_type=tgt_type)
            if result is None or not isinstance(result, dict):
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
            result = SaltClient.local().cmd(target, 'grains.setval', [key, val], tgt_type=tgt_type)
        cls.logger.info("Added '%s = %s' grain to %s: result=%s", key, val, target, result)

    @classmethod
    def del_grain(cls, target, key):
        target, tgt_type = cls._format_target(target)
        cls.logger.debug("Deleting '%s' grain from %s", key, target)
        with contextlib.redirect_stdout(None):
            result = SaltClient.local().cmd(target, 'grains.delkey', [key], tgt_type=tgt_type)
        cls.logger.info("Deleted '%s' grain from %s: result=%s", key, target, result)

    @classmethod
    def filter_by(cls, key, val=None):
        condition = '{}:{}'.format(key, val if val else '*')
        with contextlib.redirect_stdout(None):
            result = SaltClient.local().cmd(condition, 'test.true', tgt_type='grain')
            if result is None or not isinstance(result, dict):
                raise SaltCallException(condition, 'test.true', result)
        logger.debug("list of minions that match '%s': %s", condition, list(result))
        return list(result)

    @classmethod
    def get_grain(cls, target, key):
        target, tgt_type = cls._format_target(target)
        cls.logger.debug("Getting '%s' grain from %s", key, target)
        with contextlib.redirect_stdout(None):
            result = SaltClient.local().cmd(target, 'grains.get', [key], tgt_type=tgt_type)
        cls.logger.info("Got '%s' grain from %s: result=%s", key, target, result)
        return result


class PillarManager:
    PILLAR_FILE = "ceph-salt.sls"
    pillar_data = {}
    logger = logging.getLogger(__name__ + '.pillar')

    @classmethod
    def pillar_installed(cls):
        pillar_base_path = SaltClient.pillar_fs_path()
        if not os.path.exists(os.path.join(pillar_base_path, cls.PILLAR_FILE)):
            return False
        try:
            top_data = cls._load_yaml("top.sls")
            if 'base' not in top_data:
                return False
            if 'ceph-salt:member' not in top_data['base']:
                return False
            if 'ceph-salt' not in top_data['base']['ceph-salt:member']:
                return False
        except PillarFileNotPureYaml:
            with open(os.path.join(pillar_base_path, "top.sls"), "r") as top_file:
                contents = top_file.read()
            if 'ceph-salt:member' in contents and 'ceph-salt' in contents:
                return True
            return False
        return True

    @classmethod
    def install_pillar(cls):
        pillar_base_path = SaltClient.pillar_fs_path()

        top_data = cls._load_yaml("top.sls")
        if 'base' not in top_data:
            top_data['base'] = {}
        if 'ceph-salt:member' not in top_data['base']:
            top_data['base']['ceph-salt:member'] = [{'match': 'grain'}, 'ceph-salt']
        logger.info("writing top.sls file: %s", top_data)
        cls._save_yaml(top_data, "top.sls")

        if not os.path.exists(os.path.join(pillar_base_path, cls.PILLAR_FILE)):
            logger.info("creating ceph-salt.sls pillar file: %s", top_data)
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

    @classmethod
    def _load(cls):
        if not cls.pillar_data:
            cls.pillar_data = cls._load_yaml(cls.PILLAR_FILE)
            cls.logger.debug("Loaded pillar data: %s", cls.pillar_data)

    @classmethod
    def get(cls, key):
        cls._load()
        res = cls._get_dict_value(cls.pillar_data, key)
        if key == 'ceph-salt:ssh:private_key':
            # don't log key value
            cls.logger.info("Got '%s' from pillar", key)
        else:
            cls.logger.info("Got '%s' from pillar: '%s'", key, res)

        return res

    @classmethod
    def set(cls, key, value):
        cls._load()
        cls._set_dict_value(cls.pillar_data, key, value)
        cls._save_yaml(cls.pillar_data, cls.PILLAR_FILE)
        SaltClient.local().cmd('*', 'saltutil.pillar_refresh', tgt_type="compound")
        if key == 'ceph-salt:ssh:private_key':
            cls.logger.info("Set '%s' to pillar", key)
        else:
            cls.logger.info("Set '%s' to pillar: '%s'", key, value)

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
