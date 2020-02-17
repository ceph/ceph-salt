import datetime
import fnmatch
import logging
import threading

import salt.config
import salt.utils.event
from tornado.ioloop import IOLoop

# pylint: disable=C0103
logger = logging.getLogger(__name__)


class SaltEvent:
    """
    Base class of a salt Event
    """
    def __init__(self, raw_event):
        self.raw_event = raw_event
        self.tag = raw_event['tag']
        self.minion = raw_event['data']['id']
        self.stamp = datetime.datetime.strptime(raw_event['data']['_stamp'], "%Y-%m-%dT%H:%M:%S.%f")

    def __str__(self):
        return "[{}] [{}] [{}]".format(self.stamp, self.minion, self.tag)


class JobRetEvent(SaltEvent):
    """
    Base class of a job return Event
    """
    def __init__(self, raw_event):
        super().__init__(raw_event)
        self.success = raw_event['data']['success']

    def __str__(self):
        return '{} {}'.format(super().__str__(), self.success)


class CephSaltEvent(SaltEvent):
    """
    Base class of a ceph-salt Event
    """
    def __init__(self, raw_event):
        super().__init__(raw_event)
        self.desc = raw_event['data']['data']['desc']

    def __str__(self):
        return '{} {}'.format(super().__str__(), self.desc)


class EventListener:
    """
    This class represents a listener object that listens to particular Salt events.
    """

    def handle_ceph_salt_event(self, event: CephSaltEvent):
        """Handle generic ceph-salt event
        Args:
            event (CephSaltEvent): the salt event
        """

    def handle_begin_stage(self, event: CephSaltEvent):
        """Handle begin stage ceph-salt event
        Args:
            event (CephSaltEvent): the salt event
        """

    def handle_end_stage(self, event: CephSaltEvent):
        """Handle end stage ceph-salt event
        Args:
            event (CephSaltEvent): the salt event
        """

    def handle_begin_step(self, event: CephSaltEvent):
        """Handle begin step ceph-salt event
        Args:
            event (CephSaltEvent): the salt event
        """

    def handle_end_step(self, event: CephSaltEvent):
        """Handle end step ceph-salt event
        Args:
            event (CephSaltEvent): the salt event
        """

    def handle_minion_reboot(self, event: CephSaltEvent):
        """Handle minion_reboot ceph-salt event
        Args:
            event (CephSaltEvent): the salt event
        """

    def handle_minion_start(self, event: SaltEvent):
        """Handle minion_start salt event
        Args:
            event (SaltEvent): the salt event
        """

    def handle_state_apply_return(self, event: JobRetEvent):
        """Handle state.apply job return event
        Args:
            event (JobRetEvent): the salt event
        """


class SaltEventProcessor(threading.Thread):
    """
    This class implements an execution loop to listen for the Salt event BUS.
    """
    def __init__(self, minions):
        super(SaltEventProcessor, self).__init__()
        self.running = False
        self.listeners = []
        self.io_loop = None
        self.event = threading.Event()
        self.minions = minions

    def add_listener(self, listener):
        """Adds an event listener to the listener list
        Args:
            listener (EventListener): the listener object
        """
        self.listeners.append(listener)

    def is_running(self):
        """
        Gets the running state of the processor
        """
        return self.running

    def start(self):
        self.running = True
        super(SaltEventProcessor, self).start()
        self.event.wait()

    def run(self):
        """
        Starts the IOLoop of Salt Event Processor
        """
        self.io_loop = IOLoop.current()
        self.event.set()

        opts = salt.config.client_config('/etc/salt/master')
        stream = salt.utils.event.get_event('master', io_loop=self.io_loop,
                                            transport=opts['transport'], opts=opts)
        stream.set_event_handler(self._handle_event_recv)

        self.io_loop.start()

    def stop(self):
        """
        Sets running flag to False
        """
        self.running = False
        self.io_loop.stop()
        self.listeners.clear()

    def _handle_event_recv(self, raw):
        """
        Handles the asynchronous reception of raw events
        """
        mtag, data = salt.utils.event.SaltEvent.unpack(raw)
        self._process({'tag': mtag, 'data': data})

    def _process(self, event):
        """Processes a raw event

        Creates the proper salt event class wrapper and notifies listeners

        Args:
            event (dict): the raw event data
        """
        logger.debug("Process event -> %s", event)
        wrapper = None
        if fnmatch.fnmatch(event['tag'], 'ceph-salt/*'):
            wrapper = CephSaltEvent(event)
        elif event['tag'] == 'minion_start':
            wrapper = SaltEvent(event)
        elif fnmatch.fnmatch(event['tag'], 'salt/job/*/ret/*'):
            wrapper = JobRetEvent(event)
        if wrapper:
            if wrapper.minion not in self.minions:
                return
            for listener in self.listeners:
                if fnmatch.fnmatch(event['tag'], 'ceph-salt/*'):
                    listener.handle_ceph_salt_event(wrapper)
                    if event['tag'] == 'ceph-salt/stage/begin':
                        listener.handle_begin_stage(wrapper)
                    elif event['tag'] == 'ceph-salt/stage/end':
                        listener.handle_end_stage(wrapper)
                    elif event['tag'] == 'ceph-salt/step/begin':
                        listener.handle_begin_step(wrapper)
                    elif event['tag'] == 'ceph-salt/step/end':
                        listener.handle_end_step(wrapper)
                    elif event['tag'] == 'ceph-salt/minion_reboot':
                        listener.handle_minion_reboot(wrapper)
                elif event['tag'] == 'minion_start':
                    listener.handle_minion_start(wrapper)
                elif fnmatch.fnmatch(event['tag'], 'salt/job/*/ret/*'):
                    if event['data'].get('fun') == 'state.apply':
                        listener.handle_state_apply_return(wrapper)
