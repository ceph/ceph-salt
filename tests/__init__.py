import logging
import logging.config
import unittest
from collections import defaultdict

from mock import patch


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


class SaltGrainsMock:
    def __init__(self):
        self.logger = logging.getLogger(SaltGrainsMock.__name__)
        self.grains = {}

    def setval(self, key, value):
        self.logger.info('setval %s, %s', key, value)
        self.grains[key] = value

    def get(self, key):
        self.logger.info('get %s', key)
        return self.grains[key]

    def delkey(self, key):
        self.logger.info('delkey %s', key)
        del self.grains[key]


class SaltLocalClientMock:

    def __init__(self):
        self.logger = logging.getLogger(SaltLocalClientMock.__name__)
        self.grains = defaultdict(SaltGrainsMock)

    def _parse_module(self, module):
        return module.split('.', 1)

    def cmd(self, target, module, args, tgt_type=None):
        self.logger.info('cmd %s, %s, %s, tgt_type=%s', target, module, args, tgt_type)

        mod, func = self._parse_module(module)
        if mod == 'grains':
            return getattr(self.grains[target], func)(*args)

        raise NotImplementedError()


class SaltClientMock:
    local_client = SaltLocalClientMock()

    @classmethod
    def local(cls):
        return cls.local_client


# pylint: disable=invalid-name
class SaltMockTestCase(unittest.TestCase):
    def __init__(self, methodName='runTest'):
        super(SaltMockTestCase, self).__init__(methodName)
        self.local_client = None

    def setUp(self):
        super(SaltMockTestCase, self).setUp()
        patcher = patch('sesboot.salt_utils.SaltClient', new_callable=SaltClientMock)
        self.local_client = patcher.start()
        self.addCleanup(patcher.stop)

    def assertGrains(self, target, key, value):
        local = self.local_client.local()
        self.assertIn(target, local.grains)
        target_grains = local.grains[target].grains
        self.assertIn(key, target_grains)
        self.assertEqual(target_grains[key], value)

    def assertNotInGrains(self, target, key):
        local = self.local_client.local()
        self.assertIn(target, local.grains)
        target_grains = local.grains[target].grains
        self.assertNotIn(key, target_grains)
