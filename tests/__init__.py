import os
import fnmatch
import logging
import logging.config
from collections import defaultdict
import pytest

import yaml
from mock import patch
from pyfakefs.fake_filesystem_unittest import TestCase

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
    @staticmethod
    def pillar_refresh():
        return True


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
            else:
                raise NotImplementedError()

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
        raise NotImplementedError()


class SaltClientMock:

    caller_client = SaltCallerMock()
    local_client = SaltLocalClientMock()
    local_fs = None

    @classmethod
    def caller(cls):
        return cls.caller_client

    @classmethod
    def local(cls):
        return cls.local_client

    @classmethod
    def pillar_fs_path(cls):
        return '/srv/pillar'


# pylint: disable=invalid-name
class SaltMockTestCase(TestCase):

    def __init__(self, methodName='runTest'):
        super(SaltMockTestCase, self).__init__(methodName)
        self.capsys = None
        self.salt_env = SaltEnv
        self.salt_client = None

    def setUp(self):
        super(SaltMockTestCase, self).setUp()
        self.setUpPyfakefs()
        self.salt_client = SaltClientMock
        self.salt_client.local_fs = self.fs
        patchers = [
            patch('ceph_bootstrap.salt_utils.SaltClient', new=self.salt_client),
            patch('ceph_bootstrap.core.SaltClient', new=self.salt_client)
        ]
        for patcher in patchers:
            patcher.start()
            self.addCleanup(patcher.stop)
        self.fs.create_dir(self.salt_client.pillar_fs_path())
        self.fs.create_file(os.path.join(self.salt_client.pillar_fs_path(), 'ceph-salt.sls'))

    def tearDown(self):
        super(SaltMockTestCase, self).tearDown()
        self.fs.remove_object(os.path.join(self.salt_client.pillar_fs_path(), 'ceph-salt.sls'))

    @pytest.fixture(autouse=True)
    def capsys(self, capsys):
        self.capsys = capsys

    def clearSysOut(self):
        self.capsys.readouterr()

    def assertInSysOut(self, text):
        out, _ = self.capsys.readouterr()
        self.assertIn(text, out)

    def assertGrains(self, target, key, value):
        local = self.salt_client.local()
        self.assertIn(target, local.grains)
        target_grains = local.grains[target].grains
        self.assertIn(key, target_grains)
        self.assertEqual(target_grains[key], value)

    def assertNotInGrains(self, target, key):
        local = self.salt_client.local()
        self.assertIn(target, local.grains)
        target_grains = local.grains[target].grains
        self.assertNotIn(key, target_grains)

    def assertYamlEqual(self, file_path, _dict):
        data = None
        with open(file_path, 'r') as file:
            data = yaml.load(file)
        self.assertDictEqual(data, _dict)
