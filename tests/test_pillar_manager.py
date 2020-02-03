import os
from ceph_bootstrap.salt_utils import PillarManager
from . import SaltMockTestCase


class PillarManagerTest(SaltMockTestCase):

    def tearDown(self):
        super(PillarManagerTest, self).tearDown()
        PillarManager.reload()

    def test_pillar_set(self):
        PillarManager.set('ceph-salt:test:enabled', True)
        file_path = os.path.join(self.pillar_fs_path(), PillarManager.PILLAR_FILE)
        self.assertYamlEqual(file_path, {'ceph-salt': {'test': {'enabled': True}}})

    def test_pillar_get(self):
        PillarManager.set('ceph-salt:test', 'some text')
        val = PillarManager.get('ceph-salt:test')
        self.assertEqual(val, 'some text')

    def test_pillar_reset(self):
        PillarManager.set('ceph-salt:test', 'some text')
        val = PillarManager.get('ceph-salt:test')
        self.assertEqual(val, 'some text')
        PillarManager.reset('ceph-salt:test')
        val = PillarManager.get('ceph-salt:test')
        self.assertIsNone(val)

    def test_pillar_installed_no_top(self):
        self.fs.remove_object('/srv/pillar/ceph-salt.sls')
        self.assertFalse(PillarManager.pillar_installed())
        self.fs.create_file('/srv/pillar/ceph-salt.sls')

    def test_pillar_installed_no_top2(self):
        self.assertFalse(PillarManager.pillar_installed())

    def test_pillar_installed_top_with_jinja(self):
        self.fs.remove_object('/srv/pillar/ceph-salt.sls')
        self.fs.create_file('/srv/pillar/top.sls', contents='{% set x = 2 %}')
        self.assertFalse(PillarManager.pillar_installed())
        self.fs.create_file('/srv/pillar/ceph-salt.sls')
        self.fs.remove_object('/srv/pillar/top.sls')

    def test_pillar_installed_top_with_jinja2(self):
        self.fs.create_file('/srv/pillar/top.sls', contents='''
{% set x = 2 %}'
base:
    'ceph-salt:member':
        - ceph-salt
''')
        self.assertTrue(PillarManager.pillar_installed())
        self.fs.remove_object('/srv/pillar/top.sls')

    def test_pillar_installed_top_without_base(self):
        self.fs.remove_object('/srv/pillar/ceph-salt.sls')
        self.fs.create_file('/srv/pillar/top.sls', contents='')
        self.assertFalse(PillarManager.pillar_installed())
        self.fs.create_file('/srv/pillar/ceph-salt.sls')
        self.fs.remove_object('/srv/pillar/top.sls')

    def test_pillar_installed_top_without_ceph_salt(self):
        self.fs.create_file('/srv/pillar/top.sls', contents='''
base:
  '*': []
''')
        self.assertFalse(PillarManager.pillar_installed())
        self.fs.remove_object('/srv/pillar/top.sls')

    def test_pillar_installed(self):
        self.fs.create_file('/srv/pillar/top.sls', contents='''
base:
  'ceph-salt:member': [ceph-salt]
''')
        self.assertTrue(PillarManager.pillar_installed())
        self.fs.remove_object('/srv/pillar/top.sls')

    def test_pillar_install(self):
        self.fs.remove_object('/srv/pillar/ceph-salt.sls')
        self.assertFalse(PillarManager.pillar_installed())
        PillarManager.install_pillar()
        self.assertTrue(PillarManager.pillar_installed())

    def test_pillar_install2(self):
        self.fs.create_file('/srv/pillar/top.sls', contents='''
base:
  '*': []
''')
        self.assertFalse(PillarManager.pillar_installed())
        PillarManager.install_pillar()
        self.assertTrue(PillarManager.pillar_installed())
        self.fs.remove_object('/srv/pillar/top.sls')

    def test_pillar_install3(self):
        self.fs.remove_object('/srv/pillar/ceph-salt.sls')
        self.fs.create_file('/srv/pillar/top.sls', contents='')
        self.assertFalse(PillarManager.pillar_installed())
        PillarManager.install_pillar()
        self.assertTrue(PillarManager.pillar_installed())
