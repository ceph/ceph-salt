import datetime
import logging
import unittest
from typing import List

import mock

from ceph_bootstrap.salt_event import SaltEventProcessor, EventListener, CephSaltEvent, \
    SaltEvent, JobRetEvent


# pylint: disable=unused-argument


logger = logging.getLogger(__name__)


class SaltEventStream:
    _events = []
    _handler = None

    @classmethod
    def push_event(cls, tag, data):
        logger.info("push event: %s, %s", tag, data)
        cls._events.append((tag, data))

    @classmethod
    def flush_events(cls):
        if cls._handler:
            while cls._events:
                cls._handler(None)  # pylint: disable=not-callable

    @classmethod
    def set_event_handler(cls, handler):
        logger.info("Registering handler: %s", handler)
        cls._handler = handler

    @classmethod
    def unpack(cls, *args, **kwargs):
        logger.info("Unpack event: %s", cls._events)
        tag, data = cls._events.pop(0)
        return tag, data


class TestEventListener(EventListener):
    ceph_salt_events: List[CephSaltEvent] = []
    begin_stage_events = []
    end_stage_events = []
    begin_step_events = []
    end_step_events = []
    minion_reboot_events = []
    minion_start_events = []
    state_apply_return_events = []

    def handle_ceph_salt_event(self, event: CephSaltEvent):
        logger.info("received ceph-salt event: %s", event)
        self.ceph_salt_events.append(event)

    def handle_begin_stage(self, event: CephSaltEvent):
        self.begin_stage_events.append(event)

    def handle_end_stage(self, event: CephSaltEvent):
        self.end_stage_events.append(event)

    def handle_begin_step(self, event: CephSaltEvent):
        self.begin_step_events.append(event)

    def handle_end_step(self, event: CephSaltEvent):
        self.end_step_events.append(event)

    def handle_minion_reboot(self, event: CephSaltEvent):
        self.minion_reboot_events.append(event)

    def handle_minion_start(self, event: SaltEvent):
        self.minion_start_events.append(event)

    def handle_state_apply_return(self, event: JobRetEvent):
        self.state_apply_return_events.append(event)


class TestSaltEvent(unittest.TestCase):

    def __init__(self, methodName='runTest'):
        super(TestSaltEvent, self).__init__(methodName)
        self.processor = None

    def setUp(self):
        patchers = [
            mock.patch('salt.utils.event.get_event', return_value=SaltEventStream),
            mock.patch('salt.config.client_config'),
            mock.patch("salt.utils.event.SaltEvent", new_callable=SaltEventStream),
        ]
        for patcher in patchers:
            patcher.start()
            self.addCleanup(patcher.stop)

        self.processor = SaltEventProcessor(['node1.test.com', 'node2.test.com'])
        self.processor.start()

    def tearDown(self):
        if self.processor.is_running():
            self.processor.stop()
        self.processor = None

    def test_listener(self):
        listener = TestEventListener()
        self.processor.add_listener(listener)

        SaltEventStream.push_event('ceph-salt/stage/begin', {
            'id': 'node1.test.com',
            'cmd': '_minion_event',
            'pretag': None,
            'data': {
                'desc': 'Doing stuff 1'
            },
            'tag': 'ceph-salt/stage/begin',
            '_stamp': '2020-01-17T15:19:54.719389'
        })
        SaltEventStream.push_event('ceph-salt/step/begin', {
            'id': 'node1.test.com',
            'cmd': '_minion_event',
            'pretag': None,
            'data': {
                'desc': 'Doing step 1'
            },
            'tag': 'ceph-salt/stage/begin',
            '_stamp': '2020-01-17T15:19:55.719389'
        })
        SaltEventStream.push_event('ceph-salt/step/end', {
            'id': 'node1.test.com',
            'cmd': '_minion_event',
            'pretag': None,
            'data': {
                'desc': 'Doing step 1'
            },
            'tag': 'ceph-salt/stage/begin',
            '_stamp': '2020-01-17T15:19:56.719389'
        })
        SaltEventStream.push_event('ceph-salt/stage/end', {
            'id': 'node1.test.com',
            'cmd': '_minion_event',
            'pretag': None,
            'data': {
                'desc': 'Doing stuff 1'
            },
            'tag': 'ceph-salt/stage/begin',
            '_stamp': '2020-01-17T15:19:57.719389'
        })
        SaltEventStream.push_event('20200117161959615228', {
            'minions': ['node1.test.com'],
            '_stamp': '2020-01-17T15:19:59.615651'
        })
        SaltEventStream.push_event('ceph-salt/stage/begin', {
            'id': 'node2.test.com',
            'cmd': '_minion_event',
            'pretag': None,
            'data': {
                'desc': 'Doing stuff 2'
            },
            'tag': 'ceph-salt/stage/begin',
            '_stamp': '2020-01-17T15:20:54.719389'
        })
        SaltEventStream.push_event('ceph-salt/minion_reboot', {
            'id': 'node2.test.com',
            'data': {
                'desc': 'Rebooting...'
            },
            'tag': 'ceph-salt/minion_reboot',
            '_stamp': '2020-01-17T15:20:54.719389'
        })
        SaltEventStream.flush_events()

        tstamp1 = datetime.datetime.strptime('2020-01-17T15:19:54.719389', "%Y-%m-%dT%H:%M:%S.%f")
        tstamp2 = datetime.datetime.strptime('2020-01-17T15:19:55.719389', "%Y-%m-%dT%H:%M:%S.%f")
        tstamp3 = datetime.datetime.strptime('2020-01-17T15:19:56.719389', "%Y-%m-%dT%H:%M:%S.%f")
        tstamp4 = datetime.datetime.strptime('2020-01-17T15:19:57.719389', "%Y-%m-%dT%H:%M:%S.%f")
        tstamp5 = datetime.datetime.strptime('2020-01-17T15:20:54.719389', "%Y-%m-%dT%H:%M:%S.%f")
        tstamp6 = datetime.datetime.strptime('2020-01-17T15:20:54.719389', "%Y-%m-%dT%H:%M:%S.%f")

        self.assertEqual(len(listener.ceph_salt_events), 6)
        self.assertEqual(len(listener.begin_stage_events), 2)
        self.assertEqual(len(listener.end_stage_events), 1)
        self.assertEqual(len(listener.begin_step_events), 1)
        self.assertEqual(len(listener.end_step_events), 1)
        self.assertEqual(len(listener.minion_reboot_events), 1)

        self.assertEqual(listener.ceph_salt_events[0].minion, "node1.test.com")
        self.assertEqual(listener.ceph_salt_events[0].desc, "Doing stuff 1")
        self.assertEqual(listener.ceph_salt_events[0].tag, "ceph-salt/stage/begin")
        self.assertEqual(listener.ceph_salt_events[0].stamp, tstamp1)

        self.assertEqual(listener.ceph_salt_events[1].minion, "node1.test.com")
        self.assertEqual(listener.ceph_salt_events[1].desc, "Doing step 1")
        self.assertEqual(listener.ceph_salt_events[1].tag, "ceph-salt/step/begin")
        self.assertEqual(listener.ceph_salt_events[1].stamp, tstamp2)

        self.assertEqual(listener.ceph_salt_events[2].minion, "node1.test.com")
        self.assertEqual(listener.ceph_salt_events[2].desc, "Doing step 1")
        self.assertEqual(listener.ceph_salt_events[2].tag, "ceph-salt/step/end")
        self.assertEqual(listener.ceph_salt_events[2].stamp, tstamp3)

        self.assertEqual(listener.ceph_salt_events[3].minion, "node1.test.com")
        self.assertEqual(listener.ceph_salt_events[3].desc, "Doing stuff 1")
        self.assertEqual(listener.ceph_salt_events[3].tag, "ceph-salt/stage/end")
        self.assertEqual(listener.ceph_salt_events[3].stamp, tstamp4)

        self.assertEqual(listener.ceph_salt_events[4].minion, "node2.test.com")
        self.assertEqual(listener.ceph_salt_events[4].desc, "Doing stuff 2")
        self.assertEqual(listener.ceph_salt_events[4].tag, "ceph-salt/stage/begin")
        self.assertEqual(listener.ceph_salt_events[4].stamp, tstamp5)

        self.assertEqual(listener.ceph_salt_events[5].minion, "node2.test.com")
        self.assertEqual(listener.ceph_salt_events[5].desc, "Rebooting...")
        self.assertEqual(listener.ceph_salt_events[5].tag, "ceph-salt/minion_reboot")
        self.assertEqual(listener.ceph_salt_events[5].stamp, tstamp6)

        self.assertEqual(listener.ceph_salt_events[0], listener.begin_stage_events[0])
        self.assertEqual(listener.ceph_salt_events[1], listener.begin_step_events[0])
        self.assertEqual(listener.ceph_salt_events[2], listener.end_step_events[0])
        self.assertEqual(listener.ceph_salt_events[3], listener.end_stage_events[0])
        self.assertEqual(listener.ceph_salt_events[4], listener.begin_stage_events[1])
        self.assertEqual(listener.ceph_salt_events[5], listener.minion_reboot_events[0])

    def test_events_ignored(self):
        listener = TestEventListener()
        self.processor.add_listener(listener)

        SaltEventStream.push_event('minion_start', {
            'id': 'node1.test.com',
            'tag': 'minion_start',
            '_stamp': '2020-01-17T15:20:54.719389'
        })
        SaltEventStream.push_event('minion_start', {
            'id': 'node2.test.com',
            'tag': 'minion_start',
            '_stamp': '2020-01-17T15:20:54.719389'
        })
        SaltEventStream.push_event('minion_start', {
            'id': 'node3.test.com',
            'tag': 'minion_start',
            '_stamp': '2020-01-17T15:20:54.719389'
        })
        SaltEventStream.flush_events()

        self.assertEqual(len(listener.minion_start_events), 2)

    def test_state_apply_return(self):
        listener = TestEventListener()
        self.processor.add_listener(listener)

        SaltEventStream.push_event('salt/job/20200215120107564789/ret/node1.test.com', {
            'id': 'node1.test.com',
            'tag': 'salt/job/20200215120107564789/ret/node1.test.com',
            '_stamp': '2020-01-17T15:20:54.719389',
            'fun': 'state.apply',
            'success': True
        })
        SaltEventStream.flush_events()

        self.assertEqual(len(listener.state_apply_return_events), 1)
