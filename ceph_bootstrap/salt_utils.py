import logging
import os
import yaml

import salt.client
import salt.minion


logger = logging.getLogger(__name__)


class SaltClient:
    _OPTS_ = None
    _CALLER_ = None
    _LOCAL_ = None
    _MASTER_ = None

    @classmethod
    def _opts(cls):
        """
        Initializes and retrieves the Salt opts structure
        """
        if cls._OPTS_ is None:
            logger.info("Initializing SaltClient with master config")
            cls._OPTS_ = salt.config.master_config('/etc/salt/master')
            # pylint: disable=unsupported-assignment-operation
            cls._OPTS_['file_client'] = 'local'
            logger.debug("SaltClient __opts__ = %s", cls._OPTS_)

        return cls._OPTS_

    @classmethod
    def caller(cls):
        """
        Initializes and retrieves the Salt caller client instance
        """
        if cls._CALLER_ is None:
            cls._CALLER_ = salt.client.Caller(mopts=cls._opts())
        return cls._CALLER_

    @classmethod
    def local(cls):
        """
        Initializes and retrieves the Salt local client instance
        """
        if cls._LOCAL_ is None:
            cls._LOCAL_ = salt.client.LocalClient()
        return cls._LOCAL_

    @classmethod
    def master(cls):
        if cls._MASTER_ is None:
            _opts = salt.config.master_config('/etc/salt/master')
            _opts['file_client'] = 'local'
            cls._MASTER_ = salt.minion.MasterMinion(_opts)
        return cls._MASTER_

    @classmethod
    def pillar_fs_path(cls):
        return cls.master().opts['pillar_roots']['base'][0]


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
        result = SaltClient.local().cmd(target, 'grains.setval', [key, val], tgt_type=tgt_type)
        cls.logger.info("Added '%s = %s' grain to %s: result=%s", key, val, target, result)

    @classmethod
    def del_grain(cls, target, key):
        target, tgt_type = cls._format_target(target)
        cls.logger.debug("Deleting '%s' grain from %s", key, target)
        result = SaltClient.local().cmd(target, 'grains.delkey', [key], tgt_type=tgt_type)
        cls.logger.info("Deleted '%s' grain from %s: result=%s", key, target, result)

    @classmethod
    def filter_by(cls, key, val=None):
        result = SaltClient.local().cmd('{}:{}'.format(key, val if val else '*'), 'test.ping',
                                        tgt_type='grain')
        return list(result)

    @classmethod
    def get_grain(cls, target, key):
        target, tgt_type = cls._format_target(target)
        cls.logger.debug("Getting '%s' grain from %s", key, target)
        result = SaltClient.local().cmd(target, 'grains.get', [key], tgt_type=tgt_type)
        cls.logger.info("Got '%s' grain from %s: result=%s", key, target, result)
        return result


class PillarManager:
    PILLAR_FILE = "ceph-salt.sls"
    pillar_data = {}
    logger = logging.getLogger(__name__ + '.pillar')

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
        full_path = "{}/{}".format(pillar_base_path, custom_file)
        cls.logger.info("Reading pillar items from file: %s", full_path)
        if not os.path.exists(full_path):
            return {}
        with open(full_path, 'r') as file:
            data = yaml.load(file)
            if data is None:
                data = {}
        return data

    @staticmethod
    def _save_yaml(data, custom_file):
        pillar_base_path = SaltClient.pillar_fs_path()
        full_path = "{}/{}".format(pillar_base_path, custom_file)
        with open(full_path, 'w') as file:
            content = yaml.dump(data, default_flow_style=False)
            if content == '{}\n':
                file.write("")
            else:
                file.write(content)
            file.write("\n")

    @classmethod
    def _load(cls):
        if not cls.pillar_data:
            cls.pillar_data = cls._load_yaml(cls.PILLAR_FILE)
            cls.logger.debug("Loaded pillar data: %s", cls.pillar_data)

    @classmethod
    def get(cls, key, default=None):
        cls._load()
        res = cls._get_dict_value(cls.pillar_data, key)
        if res is None:
            cls.logger.info("'%s' not found in pillar, using default value '%s'", key, default)
            return default

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
