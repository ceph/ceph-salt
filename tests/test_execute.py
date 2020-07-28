import datetime
import threading
import time
import logging
import os

import mock
import pytest

from ceph_salt.execute import CephSaltController, TerminalRenderer, CephSaltModel, Event, \
    CursesRenderer, CephSaltExecutor
from ceph_salt.exceptions import MinionDoesNotExistInConfiguration
from ceph_salt.salt_utils import GrainsManager
from ceph_salt.salt_event import CephSaltEvent
from ceph_salt.salt_utils import PillarManager

from . import SaltMockTestCase, ServiceMock, SaltUtilMock, CephOrchMock


# pylint: disable=unused-argument
logger = logging.getLogger(__name__)


def _event(tag, minion_id, desc, sec):
    return CephSaltEvent({
        'tag': 'ceph-salt/{}'.format(tag),
        'data': {
            'id': minion_id,
            'cmd': '_minion_event',
            'pretag': None,
            'data': {
                'desc': desc
            },
            'tag': 'ceph-salt/stage/begin',
            '_stamp': '2020-01-17T15:19:{}.719389'.format(sec)
        }
    })


def begin_stage(minion_id, desc, sec):
    return _event('stage/begin', minion_id, desc, sec)


def end_stage(minion_id, desc, sec):
    return _event('stage/end', minion_id, desc, sec)


def begin_step(minion_id, desc, sec):
    return _event('step/begin', minion_id, desc, sec)


def end_step(minion_id, desc, sec):
    return _event('step/end', minion_id, desc, sec)


def failure():
    return {
        "state": "file_|-/etc/chrony.conf_|-/etc/chrony.conf_|-managed",
        "__id__": "/etc/chrony.conf",
        "__run_num__": 21,
        "__sls__": "ceph-salt.time",
        "changes": {},
        "comment": "Unable to manage file: Jinja variable 'dict object' has no attribute "
                   "'external_time_servers'",
        "duration": 49.631,
        "name": "/etc/chrony.conf",
        "pchanges": {},
        "result": False,
        "start_time": "16:46:46.337877"
    }


class ApplyTest(SaltMockTestCase):
    def setUp(self):
        super(ApplyTest, self).setUp()
        self.salt_env.minions = ['node1.ceph.com', 'node2.ceph.com']
        GrainsManager.set_grain('node1.ceph.com', 'host', 'node1')
        GrainsManager.set_grain('node2.ceph.com', 'host', 'node2')
        GrainsManager.set_grain('node1.ceph.com', 'fqdn_ip4', ['10.20.39.201'])
        GrainsManager.set_grain('node2.ceph.com', 'fqdn_ip4', ['10.20.39.202'])
        GrainsManager.set_grain('node1.ceph.com', 'ceph-salt', {'member': True,
                                                                'roles': ['mon'],
                                                                'execution': {}})
        GrainsManager.set_grain('node2.ceph.com', 'ceph-salt', {'member': True,
                                                                'roles': ['mgr'],
                                                                'execution': {}})

    def tearDown(self):
        super(ApplyTest, self).tearDown()
        PillarManager.reload()

    def test_minion_does_not_exist(self):
        with pytest.raises(MinionDoesNotExistInConfiguration):
            CephSaltModel('node3.ceph.com', 'ceph-salt', {})

    def test_controller_with_terminal_renderer(self):
        model = CephSaltModel(None, 'ceph-salt', {})
        renderer = TerminalRenderer(model)
        controller = CephSaltController(model, renderer)

        controller.begin()
        time.sleep(0.2)
        controller.handle_begin_stage(begin_stage('node1.ceph.com', 'Stage 1', 49))
        time.sleep(0.2)
        controller.handle_begin_stage(begin_stage('node2.ceph.com', 'Stage 1', 50))
        time.sleep(0.2)
        controller.handle_begin_step(begin_step('node1.ceph.com', 'Step 1', 51))
        time.sleep(0.2)
        controller.handle_end_step(end_step('node1.ceph.com', 'Step 1', 52))
        time.sleep(0.2)
        controller.handle_begin_step(begin_step('node2.ceph.com', 'Step 2', 53))
        time.sleep(0.2)
        controller.handle_end_step(end_step('node2.ceph.com', 'Step 2', 54))
        time.sleep(0.2)
        controller.handle_end_stage(end_stage('node2.ceph.com', 'Stage 1', 55))
        time.sleep(0.2)
        controller.handle_end_stage(end_stage('node1.ceph.com', 'Stage 1', 56))

        tstamp1 = datetime.datetime.strptime('2020-01-17T15:19:58.819390', "%Y-%m-%dT%H:%M:%S.%f")
        tstamp2 = datetime.datetime.strptime('2020-01-17T15:19:59.819390', "%Y-%m-%dT%H:%M:%S.%f")
        controller.minion_finished('node1.ceph.com', tstamp2, False)
        controller.minion_finished('node2.ceph.com', tstamp1, False)

        time.sleep(0.2)
        controller.minion_failure('node2.ceph.com', Event('begin_step', 'Step 2',
                                                          Event('begin_stage', 'Stage 1')),
                                  failure())
        time.sleep(0.2)
        controller.minion_failure('node1.ceph.com', Event('end_step', 'Step 1',
                                                          Event('begin_stage', 'Stage 1')),
                                  failure())

        time.sleep(0.2)
        controller.end()

        self.assertEqual(len(model.minions_list()), 2)
        self.assertIsNotNone(model.begin_time)
        self.assertTrue(model.finished())
        self.assertEqual(model.minions_finished(), 2)
        self.assertEqual(model.minions_total(), 2)
        self.assertEqual(model.minions_failed(), 2)
        self.assertEqual(model.minions_succeeded(), 0)

        node1 = model.get_minion('node1.ceph.com')
        self.assertTrue(node1.finished())
        self.assertEqual(len(node1.stages), 1)
        self.assertFalse(node1.success)
        stage = node1.last_stage
        self.assertEqual(stage.desc, 'Stage 1')
        self.assertEqual(len(stage.steps), 2)
        self.assertFalse(stage.success)
        steps = list(stage.steps.values())
        self.assertEqual(steps[0].desc, 'Step 1')
        self.assertTrue(steps[0].finished())
        self.assertTrue(steps[0].success)
        self.assertIsInstance(steps[1], dict)
        self.assertEqual(steps[1]['state'], 'file_|-/etc/chrony.conf_|-/etc/chrony.conf_|-managed')

        node2 = model.get_minion('node2.ceph.com')
        self.assertTrue(node2.finished())
        self.assertEqual(len(node2.stages), 1)
        self.assertFalse(node2.success)
        stage = node2.last_stage
        self.assertEqual(stage.desc, 'Stage 1')
        self.assertEqual(len(stage.steps), 1)
        self.assertFalse(stage.success)
        step = stage.last_step
        self.assertEqual(step.desc, 'Step 2')
        self.assertTrue(step.finished())
        self.assertFalse(step.success)
        self.assertIsNotNone(step.failure)
        self.assertEqual(step.failure['state'],
                         'file_|-/etc/chrony.conf_|-/etc/chrony.conf_|-managed')

    @mock.patch('curses.color_pair')
    @mock.patch('curses.newwin')
    @mock.patch('curses.endwin')
    @mock.patch('curses.curs_set')
    @mock.patch('curses.nocbreak')
    @mock.patch('curses.cbreak')
    @mock.patch('curses.noecho')
    @mock.patch('curses.echo')
    @mock.patch('curses.init_pair')
    @mock.patch('curses.use_default_colors')
    @mock.patch('curses.start_color')
    @mock.patch('curses.newpad')
    @mock.patch('curses.initscr')
    def test_controller_with_curses_renderer(self, initscr, newpad, *args):
        stdscr = mock.MagicMock()
        initscr.return_value = stdscr
        stdscr.getmaxyx = mock.MagicMock(return_value=(10, 80))

        class FakeGetCh:
            def __init__(self):
                self.next_char = None

            def __call__(self):
                time.sleep(0.2)
                cha = -1 if self.next_char is None else self.next_char
                self.next_char = None
                return cha

        fake_getch = FakeGetCh()
        stdscr.getch = mock.MagicMock(side_effect=fake_getch)

        body = mock.MagicMock()
        newpad.return_value = body

        class Addstr:
            def __init__(self):
                self.current_row = 0

            def __call__(self, row, *args):
                self.current_row = row

            def getyx(self):
                logger.info("return body current pos: %s, 80", self.current_row)
                return self.current_row, 80

        addstr = Addstr()
        body.addstr = mock.MagicMock(side_effect=addstr)
        body.getyx = mock.MagicMock(side_effect=addstr.getyx)

        model = CephSaltModel(None, 'ceph-salt', {})
        renderer = CursesRenderer(model)
        controller = CephSaltController(model, renderer)

        class ExecutionThread(threading.Thread):
            def run(self):
                while not renderer.running:
                    time.sleep(0.2)
                logger.info("starting injecting salt events in controller")

                controller.begin()
                time.sleep(0.3)
                controller.handle_begin_stage(begin_stage('node1.ceph.com', 'Stage 1', 49))
                time.sleep(0.3)
                controller.handle_begin_stage(begin_stage('node2.ceph.com', 'Stage 1', 50))
                time.sleep(0.3)
                controller.handle_begin_step(begin_step('node1.ceph.com', 'Step 1', 51))
                time.sleep(0.3)
                controller.handle_end_step(end_step('node1.ceph.com', 'Step 1', 52))
                time.sleep(0.3)
                controller.handle_begin_step(begin_step('node2.ceph.com', 'Step 2', 53))
                fake_getch.next_char = ord('c')
                time.sleep(0.3)
                controller.handle_end_step(end_step('node2.ceph.com', 'Step 2', 54))
                fake_getch.next_char = ord('j')
                time.sleep(0.3)
                fake_getch.next_char = ord('j')
                controller.handle_end_stage(end_stage('node2.ceph.com', 'Stage 1', 55))
                time.sleep(0.3)
                fake_getch.next_char = ord('j')
                controller.handle_end_stage(end_stage('node1.ceph.com', 'Stage 1', 56))

                tstamp1 = datetime.datetime.strptime('2020-01-17T15:19:58.819390',
                                                     "%Y-%m-%dT%H:%M:%S.%f")
                tstamp2 = datetime.datetime.strptime('2020-01-17T15:19:59.819390',
                                                     "%Y-%m-%dT%H:%M:%S.%f")
                controller.minion_finished('node1.ceph.com', tstamp2, False)
                controller.minion_finished('node2.ceph.com', tstamp1, False)

                time.sleep(0.3)
                controller.minion_failure(
                    'node2.ceph.com',
                    Event('begin_step', 'Step 2', Event('begin_stage', 'Stage 1')), failure())
                time.sleep(0.3)
                controller.minion_failure(
                    'node1.ceph.com',
                    Event('end_step', 'Step 1', Event('begin_stage', 'Stage 1')), failure())

                time.sleep(0.3)
                controller.end()
                fake_getch.next_char = ord('q')

        exec_thread = ExecutionThread()
        exec_thread.setDaemon(True)
        exec_thread.start()

        renderer.run()

        self.assertEqual(len(model.minions_list()), 2)
        self.assertIsNotNone(model.begin_time)
        self.assertTrue(model.finished())
        self.assertEqual(model.minions_finished(), 2)
        self.assertEqual(model.minions_total(), 2)
        self.assertEqual(model.minions_failed(), 2)
        self.assertEqual(model.minions_succeeded(), 0)

        node1 = model.get_minion('node1.ceph.com')
        self.assertTrue(node1.finished())
        self.assertEqual(len(node1.stages), 1)
        self.assertFalse(node1.success)
        stage = node1.last_stage
        self.assertEqual(stage.desc, 'Stage 1')
        self.assertEqual(len(stage.steps), 2)
        self.assertFalse(stage.success)
        steps = list(stage.steps.values())
        self.assertEqual(steps[0].desc, 'Step 1')
        self.assertTrue(steps[0].finished())
        self.assertTrue(steps[0].success)
        self.assertIsInstance(steps[1], dict)
        self.assertEqual(steps[1]['state'], 'file_|-/etc/chrony.conf_|-/etc/chrony.conf_|-managed')

        node2 = model.get_minion('node2.ceph.com')
        self.assertTrue(node2.finished())
        self.assertEqual(len(node2.stages), 1)
        self.assertFalse(node2.success)
        stage = node2.last_stage
        self.assertEqual(stage.desc, 'Stage 1')
        self.assertEqual(len(stage.steps), 1)
        self.assertFalse(stage.success)
        step = stage.last_step
        self.assertEqual(step.desc, 'Step 2')
        self.assertTrue(step.finished())
        self.assertFalse(step.success)
        self.assertIsNotNone(step.failure)
        self.assertEqual(step.failure['state'],
                         'file_|-/etc/chrony.conf_|-/etc/chrony.conf_|-managed')

    def test_check_formula_ok(self):
        self.fs.create_file(os.path.join(self.states_fs_path(), 'ceph-salt.sls'))
        self.assertEqual(CephSaltExecutor.check_formula('ceph-salt'), 0)
        self.fs.remove_object(os.path.join(self.states_fs_path(), 'ceph-salt.sls'))

    def test_check_formula_exists1(self):
        ServiceMock.restart_result = False
        self.assertEqual(CephSaltExecutor.check_formula('ceph-salt'), 3)
        ServiceMock.restart_result = True

    def test_check_formula_exists2(self):
        self.assertEqual(CephSaltExecutor.check_formula('ceph-salt'), 4)

    def test_check_formula_exists3(self):
        SaltUtilMock.sync_all_result = False
        self.fs.create_file(os.path.join(self.states_fs_path(), 'ceph-salt.sls'))
        self.assertEqual(CephSaltExecutor.check_formula('ceph-salt'), 5)
        SaltUtilMock.sync_all_result = True
        self.fs.remove_object(os.path.join(self.states_fs_path(), 'ceph-salt.sls'))

    def test_check_cluster_day1_with_minion(self):
        self.fs.create_file(os.path.join(self.states_fs_path(), 'ceph-salt.sls'))
        self.assertEqual(CephSaltExecutor.check_cluster('ceph-salt', 'node1.ceph.com', []), 6)
        self.fs.remove_object(os.path.join(self.states_fs_path(), 'ceph-salt.sls'))

    def test_check_minion_not_found(self):
        self.fs.create_file(os.path.join(self.states_fs_path(), 'ceph-salt.sls'))
        host_ls_result = [{'hostname': 'node1'}]
        CephOrchMock.host_ls_result = host_ls_result
        self.assertEqual(CephSaltExecutor.check_cluster('ceph-salt',
                                                        'node9.ceph.com', host_ls_result), 7)
        CephOrchMock.host_ls_result = []
        self.fs.remove_object(os.path.join(self.states_fs_path(), 'ceph-salt.sls'))
