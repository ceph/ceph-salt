import os
import fnmatch
import logging
import logging.config
from collections import defaultdict
import pytest

import yaml
from mock import patch
from pyfakefs.fake_filesystem_unittest import TestCase

from ceph_bootstrap.salt_utils import SaltClient


logging.config.dictConfig({
    'version': 1,
    'disable_existing_loggers': False,
    'formatters': {
        'standard': {
            'format': '%(asctime)s [%(levelname)s] [%(name)s] %(message)s'
        },
    },
    'handlers': {
        'console': {
            'level': 'DEBUG',
            'class': 'logging.StreamHandler',
            'formatter': 'standard'
        },
    },
    'loggers': {
        '': {
            'handlers': ['console'],
            'level': 'DEBUG',
            'propagate': True,
        }
    }
})


logger = logging.getLogger(__name__)


class ModuleUtil:
    @staticmethod
    def parse_module(module):
        return module.split('.', 1)


class SaltEnv:
    minions = []


class SaltGrainsMock:
    def __init__(self):
        self.logger = logging.getLogger(SaltGrainsMock.__name__)
        self.grains = {}

    def setval(self, key, value):
        self.logger.info('setval %s, %s', key, value)
        self.grains[key] = value

    def get(self, key):
        self.logger.info('get %s', key)
        return self.grains.get(key, '')

    def delkey(self, key):
        self.logger.info('delkey %s', key)
        del self.grains[key]

    def enumerate_entries(self, _dict=None):
        if _dict is None:
            _dict = self.grains

        entries = []
        for key, val in _dict.items():
            if isinstance(val, dict):
                _entries = self.enumerate_entries(val)
                entries.extend(["{}:{}".format(key, e) for e in _entries])
            elif isinstance(val, list):
                entries.extend(["{}:{}".format(key, e) for e in val])
            elif isinstance(val, bool):
                entries.append('{}:{}'.format(key, val))
                entries.append(key)
            else:
                entries.append('{}:{}'.format(key, val))

        self.logger.debug("grains enumeration: %s -> %s", _dict, entries)
        return entries


class TestMock:
    @staticmethod
    def ping():
        return True

    @staticmethod
    def true():
        return True


class SaltUtilMock:
    sync_all_result = True

    @staticmethod
    def pillar_refresh():
        return True

    @classmethod
    def sync_all(cls):
        return cls.sync_all_result


class StateMock:
    @staticmethod
    def sls_exists(state):
        return os.path.exists(os.path.join(SaltMockTestCase.states_fs_path(), state)) or \
            os.path.exists(os.path.join(SaltMockTestCase.states_fs_path(), "{}.sls".format(state)))


class ServiceMock:
    restart_result = True
    @classmethod
    def restart(cls, service):  # pylint: disable=unused-argument
        return cls.restart_result


class CephOrchMock:
    configured_result = True
    host_ls_result = []

    @classmethod
    def configured(cls):
        return cls.configured_result

    @classmethod
    def host_ls(cls):
        return cls.host_ls_result


class SaltLocalClientMock:

    def __init__(self):
        self.logger = logging.getLogger(SaltLocalClientMock.__name__)
        self.grains = defaultdict(SaltGrainsMock)

    def cmd(self, target, module, args=None, tgt_type=None):
        self.logger.info('cmd %s, %s, %s, tgt_type=%s', target, module, args, tgt_type)

        if args is None:
            args = []

        targets = []
        if tgt_type == 'grain':
            for minion, grains in self.grains.items():
                self.logger.info("grain filtering: %s <-> %s", grains.enumerate_entries(), target)
                if fnmatch.filter(grains.enumerate_entries(), target):
                    targets.append(minion)
        else:
            targets.append(target)

        result = {}
        for tgt in targets:
            mod, func = ModuleUtil.parse_module(module)
            if mod == 'grains':
                result[tgt] = getattr(self.grains[tgt], func)(*args)
            elif mod == 'test':
                result[tgt] = getattr(TestMock, func)(*args)
            elif mod == 'saltutil':
                result[tgt] = getattr(SaltUtilMock, func)(*args)
            elif mod == 'state':
                result[tgt] = getattr(StateMock, func)(*args)
            elif mod == 'service':
                result[tgt] = getattr(ServiceMock, func)(*args)
            elif mod == 'ceph_orch':
                result[tgt] = getattr(CephOrchMock, func)(*args)
            else:
                raise NotImplementedError()

        self.logger.info("Grains: %s", self.grains)

        return result


class MinionMock:
    @staticmethod
    def list():
        return {
            'minions': SaltEnv.minions,
            'minions_denied': [],
            'minions_pre': [],
            'minions_rejected': []
        }


class SaltCallerMock:

    def cmd(self, fun, *args, **kwargs):
        mod, func = ModuleUtil.parse_module(fun)
        if mod == 'minion':
            return getattr(MinionMock, func)(*args, **kwargs)
        if mod == 'test':
            return getattr(TestMock, func)(*args, **kwargs)
        if mod == 'service':
            return getattr(ServiceMock, func)(*args)
        raise NotImplementedError()


class SaltMasterMinionMock:
    pass


class SaltMasterConfigMock:
    def __init__(self):
        self.opts = {'pillar_roots': {'base': ['/srv/pillar']}}

    def __call__(self, *args):
        logger.info("Getting salt options: %s", self.opts)
        return self.opts


# pylint: disable=invalid-name
class SaltMockTestCase(TestCase):
    def __init__(self, methodName='runTest'):
        super(SaltMockTestCase, self).__init__(methodName)
        self.capsys = None
        self.salt_env = SaltEnv

    @staticmethod
    def pillar_fs_path():
        return '/srv/pillar'

    @staticmethod
    def states_fs_path():
        return '/srv/salt'

    def setUp(self):
        super(SaltMockTestCase, self).setUp()
        self.setUpPyfakefs()
        self.local_fs = self.fs

        logger.info("Initializing Salt mocks")

        # pylint: disable=protected-access
        SaltClient._OPTS_ = None
        SaltClient._LOCAL_ = None
        SaltClient._CALLER_ = None
        SaltClient._MASTER_ = None

        self.caller_client = SaltCallerMock()
        self.local_client = SaltLocalClientMock()
        self.master_minion = SaltMasterMinionMock()
        self.master_config = SaltMasterConfigMock()

        patchers = [
            patch('salt.config.master_config', new=self.master_config),
            patch('salt.client.Caller', return_value=self.caller_client),
            patch('salt.client.LocalClient', return_value=self.local_client),
            patch('salt.minion.MasterMinion', return_value=self.master_minion),
            patch('shutil.chown'),
        ]
        for patcher in patchers:
            patcher.start()
            self.addCleanup(patcher.stop)
        self.fs.create_dir(self.pillar_fs_path())
        self.fs.create_dir(self.states_fs_path())
        self.fs.create_file(os.path.join(self.pillar_fs_path(), 'ceph-salt.sls'))

    def tearDown(self):
        super(SaltMockTestCase, self).tearDown()
        self.fs.remove_object(os.path.join(self.pillar_fs_path(), 'ceph-salt.sls'))
        self.salt_env.minions = []

    @pytest.fixture(autouse=True)
    def capsys(self, capsys):
        self.capsys = capsys

    def clearSysOut(self):
        self.capsys.readouterr()

    def assertInSysOut(self, text):
        out, _ = self.capsys.readouterr()
        self.assertIn(text, out)

    def assertGrains(self, target, key, value):
        self.assertIn(target, self.local_client.grains)
        target_grains = self.local_client.grains[target].grains
        self.assertIn(key, target_grains)
        self.assertEqual(target_grains[key], value)

    def assertNotInGrains(self, target, key):
        self.assertIn(target, self.local_client.grains)
        target_grains = self.local_client.grains[target].grains
        self.assertNotIn(key, target_grains)

    def assertYamlEqual(self, file_path, _dict):
        data = None
        with open(file_path, 'r') as file:
            data = yaml.load(file)
        self.assertDictEqual(data, _dict)
