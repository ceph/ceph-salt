import curses
import datetime
import json
import logging
import os
import re
import signal
import threading
import time
from collections import OrderedDict
from typing import Dict, List

import yaml

from .core import CephNodeManager
from .exceptions import MinionDoesNotExistInConfiguration, ValidationException
from .logging_utils import LoggingUtil
from .salt_event import EventListener, SaltEventProcessor
from .salt_utils import SaltClient, GrainsManager, CephOrch, PillarManager
from .terminal_utils import PrettyPrinter as PP
from .validate.config import validate_config
from .validate.salt_master import check_salt_master_status
from .validate.salt_minion import sync_all


# pylint: disable=C0103
logger = logging.getLogger(__name__)


class ScreenKeyListener:
    def up_key(self):
        pass

    def down_key(self):
        pass

    def action_key(self):
        pass

    def quit_key(self):
        pass

    def collapse_expand_all_key(self):
        pass

    def pause_key(self):
        pass


class CursesScreen:
    HEADER_HEIGHT = 2
    FOOTER_HEIGHT = 3
    MIN_WIDTH = 80
    MIN_HEIGHT = 10

    COLOR_MARKER = 1
    COLOR_MINION = 4
    COLOR_STAGE = 5
    COLOR_STEP = 6
    COLOR_MENU = 7
    COLOR_SUCCESS = 8
    COLOR_ERROR = 9
    COLOR_WARNING = 10

    def __init__(self, num_rows=1000):
        self.num_rows = num_rows
        self.height = None
        self.width = None
        self.stdscr = None
        self.header = None
        self.body = None
        self.body_height = None
        self.body_width = None
        self.body_pos = 0
        self.footer = None
        self.scrollbar = None
        self.key_listeners = []
        self.previous_signal_handler = None

    def add_key_listener(self, listener):
        self.key_listeners.append(listener)

    @property
    def body_current_row(self):
        return self.body.getyx()[0]

    def refresh(self):
        if self.body:
            if self.body_pos > self.body_current_row - self.body_height:
                self.body_pos = max(0, self.body_current_row - self.body_height)
            self.body.refresh(self.body_pos, 0, self.HEADER_HEIGHT, 0,
                              self.height - self.FOOTER_HEIGHT - 1, self.body_width)

        if self.scrollbar:
            self._render_body_scrollbar()
            self.scrollbar.refresh()

        if self.header:
            self.header.refresh()
        if self.footer:
            self.footer.refresh()

    def start(self):
        os.unsetenv('LINES')
        os.unsetenv('COLUMNS')
        logger.info("initializing curses screen")
        self.stdscr = curses.initscr()
        self.height, self.width = self.stdscr.getmaxyx()
        self.body_height = self.height - self.HEADER_HEIGHT - self.FOOTER_HEIGHT
        self.body_width = self.width - 1
        logger.info("current terminal size: rows=%s cols=%s", self.height, self.width)
        curses.start_color()
        curses.use_default_colors()

        curses.init_pair(self.COLOR_MARKER, -1, -1)
        curses.init_pair(self.COLOR_MINION, curses.COLOR_CYAN, -1)
        curses.init_pair(self.COLOR_STAGE, curses.COLOR_YELLOW, -1)
        curses.init_pair(self.COLOR_STEP, curses.COLOR_BLUE, -1)
        curses.init_pair(self.COLOR_MENU, curses.COLOR_BLACK, curses.COLOR_GREEN)
        curses.init_pair(self.COLOR_SUCCESS, curses.COLOR_GREEN, -1)
        curses.init_pair(self.COLOR_ERROR, curses.COLOR_RED, -1)
        curses.init_pair(self.COLOR_WARNING, curses.COLOR_YELLOW, -1)

        curses.noecho()
        curses.cbreak()
        curses.curs_set(0)
        self.stdscr.keypad(True)

        if self.height > 2:
            self.header = curses.newwin(self.HEADER_HEIGHT, self.width, 0, 0)

        if self.height > 4:
            self.footer = curses.newwin(self.FOOTER_HEIGHT, self.width,
                                        self.height - self.FOOTER_HEIGHT, 0)

        if self.height > 5:
            self.body = curses.newpad(self.num_rows, self.width - 1)
            self.body.scrollok(True)
            self.scrollbar = curses.newwin(self.body_height + 1, 1, self.HEADER_HEIGHT,
                                           self.width - 1)

        logger.info("initializing scrollable pad: rows=%s visible_rows=%s cols=%s", self.num_rows,
                    self.body_height, self.width)

        self.stdscr.timeout(200)
        self.stdscr.refresh()
        self.refresh()

        logger.info("curses screen completed initialization")
        self.previous_signal_handler = signal.signal(signal.SIGWINCH, self._resize)

    def shutdown(self):
        logger.info("shutting down curses screen")
        signal.signal(signal.SIGWINCH, self.previous_signal_handler)
        curses.nocbreak()
        self.stdscr.keypad(False)
        curses.echo()
        curses.endwin()
        self.header = None
        self.footer = None
        self.body = None
        self.scrollbar = None

    def _resize(self, *args):  # pylint: disable=unused-argument
        logger.info("resizing windows")
        self.shutdown()
        self.start()

    def make_visible(self, row, lines):
        if self.body is None:
            return
        if row < self.body_pos:
            self.body_pos = row
        elif row + lines > self.body_pos + self.body_height:
            self.body_pos += row - (self.body_pos + self.body_height) + lines

    def has_scroll(self):
        if self.body is None:
            return False
        return self.body_current_row > self.body_height

    def _render_body_scrollbar(self):
        self.scrollbar.clear()
        current_row = self.body_current_row

        if current_row <= self.body_height:
            # no scrollbar needed
            return

        scroll_size = round((self.body_height / current_row) * self.body_height)
        if scroll_size == 0:
            scroll_size = 1
        current_pos = round((self.body_pos * self.body_height) / current_row)
        if current_pos >= self.body_height:
            current_pos = self.body_height - 1
        for i in range(0, scroll_size):
            self._write(self.scrollbar, current_pos + i, 0, "▐", CursesScreen.COLOR_MARKER, False,
                        False, False, 1)

    def clear_header(self):
        if self.header:
            self.header.move(0, 0)
            self.header.clrtoeol()

    def clear_footer(self):
        if self.footer:
            self.footer.move(0, 0)
            self.footer.erase()

    def clear_body(self):
        if self.body:
            self.body.clear()

    def clear_row(self, row):
        if self.body:
            self.body.move(row, 0)
            self.body.clrtoeol()

    def _write(self, window, row, col, text, color, bold, reverse, line_padding, width):
        if window is None:
            return

        if col >= self.width - 1:
            return

        attr = curses.color_pair(color)
        if bold:
            attr |= curses.A_BOLD
        if reverse:
            attr |= curses.A_REVERSE

        window.addstr(row, col, text, attr)
        if line_padding:
            if width > len(text) + col:
                padding = " " * (width - len(text) - col)
                window.addstr(row, col + len(text), padding, attr)

    def write_header(self, col, text, color, bold=False, reverse=False, line_padding=False):
        self._write(self.header, 0, col, text, color, bold, reverse, line_padding, self.width)

    def write_footer(self, col, text, color, bold=False, reverse=False, line_padding=False, row=0):
        self._write(self.footer, row + 1, col, text, color, bold, reverse, line_padding, self.width)

    def write_body(self, row, col, text, color, bold=False, reverse=False, line_padding=False):
        self._write(self.body, row, col, text, color, bold, reverse, line_padding, self.body_width)

    def wait_for_event(self):
        try:
            ch = self.stdscr.getch()
            if ch == -1:
                return False
            if ch == curses.KEY_NPAGE:
                if self.body:
                    if self.body_pos < self.body_current_row - self.body_height:
                        self.body_pos += min(
                            self.body_height - 1,
                            self.body_current_row - self.body_pos - self.body_height)
            elif ch == curses.KEY_PPAGE and self.body_pos > 0:
                if self.body:
                    self.body_pos -= min(self.body_pos, self.body_height - 1)
            elif ch == ord('j'):
                if self.body:
                    if self.body_pos < self.body_current_row - self.body_height:
                        self.body_pos += 1
            elif ch == ord('k'):
                if self.body:
                    if self.body_pos > 0:
                        self.body_pos -= 1
            elif ch == ord(' '):
                for listener in self.key_listeners:
                    listener.action_key()
            elif ch == ord('q'):
                for listener in self.key_listeners:
                    listener.quit_key()
            elif ch == ord('c'):
                for listener in self.key_listeners:
                    listener.collapse_expand_all_key()
            elif ch == curses.KEY_DOWN:
                for listener in self.key_listeners:
                    listener.down_key()
            elif ch == curses.KEY_UP:
                for listener in self.key_listeners:
                    listener.up_key()
            elif ch == ord('p'):
                for listener in self.key_listeners:
                    listener.pause_key()
            else:
                return False
        except KeyboardInterrupt:
            return False
        return True


class Event:
    def __init__(self, ev_type: str, desc: str, stage_ev: "Event" = None):
        self.ev_type = ev_type
        self.desc = desc
        self.stage_ev = stage_ev

    def is_stage(self) -> bool:
        return 'stage' in self.ev_type

    def is_step(self) -> bool:
        return 'step' in self.ev_type

    def is_begin(self) -> bool:
        return 'begin' in self.ev_type

    def is_end(self) -> bool:
        return 'end' in self.ev_type

    def __str__(self) -> str:
        if self.stage_ev is None:
            return "EV({}, {})".format(self.ev_type, self.desc)
        return "EV({}, {}, {})".format(self.ev_type, self.desc, self.stage_ev)


class Step:
    def __init__(self, minion, desc, timestamp):
        self.minion = minion
        self.desc = desc
        self.begin_time = timestamp
        self.end_time = None
        self.failure = None
        self.success = None
        log_msg = "STEP [BEGIN] \"{}\" on minion {}".format(self.desc, self.minion)
        logger.info(log_msg)

    def end(self, timestamp, success=True):
        self.end_time = timestamp
        self.success = success
        log_msg = "STEP [END] \"{}\" on minion {} (success={})".format(
            self.desc, self.minion, self.success)
        logger.info(log_msg)

    def finished(self):
        return self.end_time is not None

    def report_failure(self, state_data):
        self.failure = state_data
        self.success = False


class Stage:
    def __init__(self, minion, desc, timestamp):
        self.minion = minion
        self.desc = desc
        self.steps = OrderedDict()
        self.begin_time = timestamp
        self.current_step = None
        self.end_time = None
        self.success = None
        self.warning = False
        log_msg = "STAGE [BEGIN] \"{}\" on minion {}".format(self.desc, self.minion)
        logger.info(log_msg)

    @property
    def last_step(self):
        if self.current_step is None and self.steps:
            return self.steps[next(reversed(self.steps))]
        return self.current_step

    def end(self, timestamp, success=True):
        self.end_time = timestamp
        self.current_step = None
        self.success = success
        for step in self.steps.values():
            if not step.finished():
                step.end(timestamp, True)
        log_msg = "STAGE [END] \"{}\" on minion {} (success={})".format(
            self.desc, self.minion, self.success)
        logger.info(log_msg)

    def step_begin(self, desc, timestamp):
        """
        :return: "False" if duplicated, otherwise "True"
        """
        if desc in self.steps:
            if self.steps[desc].begin_time:
                return False
            logger.warning("[%s] received begin_step event after end: %s", self.minion, desc)
            self.steps[desc].begin_time = timestamp
            return True
        self.steps[desc] = Step(self.minion, desc, timestamp)
        self.current_step = self.steps[desc]
        return True

    def step_end(self, desc, timestamp):
        """
        :return: "False" if duplicated, otherwise "True"
        """
        if desc not in self.steps:
            logger.warning("[%s] received end_step event without a begin: %s", self.minion, desc)
            self.steps[desc] = Step(self.minion, desc, None)
        if self.steps[desc].finished():
            return False
        self.steps[desc].end(timestamp)
        self.current_step = None
        return True

    def finished(self):
        return self.end_time is not None

    def report_failure(self, event: Event, state_data):
        _steps = self.steps
        self.steps = OrderedDict()
        self.success = False

        if event is None:
            self.steps['|failure|{}'.format(state_data['__id__'])] = state_data

        for key, val in _steps.items():
            self.steps[key] = val
            if event is not None and event.desc == key:
                if event.is_begin():
                    val.report_failure(state_data)
                if event.is_end():
                    self.steps['|failure|{}'.format(state_data['__id__'])] = state_data


class MinionExecution:
    def __init__(self, name):
        self.name = name
        self.stages = OrderedDict()
        self.current_stage = None
        self.begin_time = datetime.datetime.utcnow()
        self.end_time = None
        self.rebooting = False
        self.warnings = []
        self.success = None

    @property
    def last_stage(self):
        if self.current_stage is None and self.stages:
            return self.stages[next(reversed(self.stages))]
        return self.current_stage

    def stage_begin(self, desc, timestamp):
        """
        :return: "False" if duplicated, otherwise "True"
        """
        if desc in self.stages:
            if self.stages[desc].begin_time:
                return False
            logger.warning("[%s] received begin_stage event after end: %s", self.name, desc)
            self.stages[desc].begin_time = timestamp
            return True
        self.stages[desc] = Stage(self.name, desc, timestamp)
        self.current_stage = self.stages[desc]
        return True

    def stage_end(self, desc, timestamp):
        """
        :return: "False" if duplicated, otherwise "True"
        """
        if desc not in self.stages:
            logger.warning("[%s] received end_stage event without a begin: %s", self.name, desc)
            self.stages[desc] = Stage(self.name, desc, None)
        if self.stages[desc].finished():
            return False
        self.stages[desc].end(timestamp)
        self.current_stage = None
        return True

    def stage_warn(self, desc):
        self.stages[desc].warning = True
        self.warnings.append(desc)

    def step_begin(self, desc, timestamp):
        """
        :return: "False" if duplicated, "None" if outside stage, otherwise "True"
        """
        if self.current_stage:
            return self.current_stage.step_begin(desc, timestamp)
        logger.warning("[%s] received begin_step event outside of stage: %s", self.name, desc)
        return None

    def step_end(self, desc, timestamp):
        """
        :return: "False" if duplicated, "None" if outside stage, otherwise "True"
        """
        if self.current_stage:
            return self.current_stage.step_end(desc, timestamp)
        logger.warning("[%s] received end_step event outside of stage: %s", self.name, desc)
        return None

    def end(self, timestamp, success):
        self.end_time = timestamp
        self.success = success
        self.current_stage = None
        for stage in self.stages.values():
            if not stage.finished():
                stage.end(timestamp, True)

    def finished(self):
        return self.end_time is not None

    def report_failure(self, event: Event, state_data):
        _stages = self.stages
        self.stages = OrderedDict()
        self.success = False

        if isinstance(state_data, list):
            for error in state_data:
                self.stages['|failure|{}'.format(error)] = error
        else:
            if event is None:
                self.stages['|failure|{}'.format(state_data['__id__'])] = state_data

        for key, val in _stages.items():
            self.stages[key] = val
            if event is not None and event.is_stage() and event.desc == key:
                if event.is_begin():
                    val.report_failure(None, state_data)
                if event.is_end():
                    self.stages['|failure|{}'.format(state_data['__id__'])] = state_data
            elif event is not None and event.is_step() and event.stage_ev.desc == key:
                val.report_failure(event, state_data)


class CephSaltModel:
    def __init__(self, minion_id, state, pillar):
        self.minion_id = minion_id
        self.state = state
        self.pillar = pillar
        self._minions: Dict[str, MinionExecution] = {}
        self.begin_time = None
        self.end_time = None
        self._init_minions()

    def _init_minions(self) -> None:
        minions = GrainsManager.filter_by('ceph-salt', 'member')
        if self.minion_id is not None:
            if self.minion_id not in minions:
                raise MinionDoesNotExistInConfiguration(self.minion_id)
            minions = [self.minion_id]
        for minion in minions:
            logger.info("adding minion: %s", minion)
            self._minions[minion] = MinionExecution(minion)

    def finished(self) -> bool:
        return self.end_time is not None

    def end(self) -> None:
        self.end_time = datetime.datetime.utcnow()

    def begin(self) -> None:
        self.begin_time = datetime.datetime.utcnow()

    def minions_succeeded(self) -> int:
        return len([m for m in self._minions.values() if m.success])

    def minions_with_warnings(self) -> int:
        return len([m for m in self._minions.values() if m.warnings])

    def minions_failed(self) -> int:
        return len(self._minions) - self.minions_succeeded()

    def minions_finished(self) -> int:
        return len([m for m in self._minions.values() if m.finished()])

    def minions_rebooting(self) -> int:
        return len([m for m in self._minions.values() if m.rebooting])

    def minions_total(self) -> int:
        return len(self._minions)

    def get_minion(self, minion: str) -> MinionExecution:
        return self._minions[minion]

    def minions_list(self) -> List[MinionExecution]:
        return sorted(list(self._minions.values()), key=lambda m: m.name)

    def minions_names(self) -> List[MinionExecution]:
        return [m.name for m in self._minions.values()]


class Renderer:
    def __init__(self, model: CephSaltModel):
        self.model = model
        self.running = False
        if self.model.minion_id:
            self.cmd_str = "salt {} state.apply {}".format(self.model.minion_id, self.model.state)
        else:
            self.cmd_str = "salt -G 'ceph-salt:member' state.apply {}".format(self.model.state)

    def minion_update(self, minion: str):
        pass

    def minion_failure(self, minion: str, failure: dict):
        pass

    def execution_started(self):
        pass

    def execution_stopped(self):
        self.running = False

    def run(self):
        logger.info("started renderer")
        self.running = True
        while self.running:
            time.sleep(0.5)
        logger.info("ended renderer")


class CephSaltController(EventListener):
    def __init__(self, model: CephSaltModel, renderer: Renderer):
        self.model = model
        self.renderer = renderer
        self.executors = 0
        self.retcode = 0
        self.running = False

    def begin(self):
        self.retcode = 0
        self.running = True
        self.model.begin()
        self.renderer.execution_started()

    def end(self):
        self.running = False
        self.model.end()
        self.renderer.execution_stopped()

    def set_retcode(self, retcode):
        if retcode > self.retcode:
            self.retcode = retcode

    def handle_begin_stage(self, event):
        minion = self.model.get_minion(event.minion)
        if minion.stage_begin(event.desc, event.stamp):
            self.renderer.minion_update(event.minion)

    def handle_end_stage(self, event):
        minion = self.model.get_minion(event.minion)
        if minion.stage_end(event.desc, event.stamp):
            self.renderer.minion_update(event.minion)

    def handle_begin_step(self, event):
        minion = self.model.get_minion(event.minion)
        if minion.step_begin(event.desc, event.stamp):
            self.renderer.minion_update(event.minion)

    def handle_end_step(self, event):
        minion = self.model.get_minion(event.minion)
        if minion.step_end(event.desc, event.stamp):
            self.renderer.minion_update(event.minion)

    def handle_minion_reboot(self, event):
        minion = self.model.get_minion(event.minion)
        minion.rebooting = True
        if minion.stage_begin('Reboot', event.stamp):
            self.renderer.minion_update(event.minion)

    def handle_minion_start(self, event):
        minion = self.model.get_minion(event.minion)
        minion.rebooting = False
        if minion.stage_end('Reboot', event.stamp):
            self.renderer.minion_update(event.minion)
        if 'ceph-salt' in self.model.pillar:
            self.model.pillar['ceph-salt'].pop('force-reboot', None)
        executor = CephSaltExecutorThread(self, event.minion)
        executor.start()

    def handle_warning_stage(self, event):
        minion = self.model.get_minion(event.minion)
        minion.stage_begin(event.desc, event.stamp)
        self.renderer.minion_update(event.minion)
        minion.stage_warn(event.desc)
        minion.stage_end(event.desc, event.stamp)
        self.renderer.minion_update(event.minion)

    def handle_state_apply_return(self, event):
        if not event.success:
            SaltClient.local().cmd(event.minion, 'grains.set', ['ceph-salt:execution:failed', True])

    def minion_finished(self, minion_name, timestamp, success):
        minion = self.model.get_minion(minion_name)
        minion.end(timestamp, success)
        self.renderer.minion_update(minion_name)

    def minion_failure(self, minion_name: str, event: Event, failure: dict):
        minion = self.model.get_minion(minion_name)
        minion.report_failure(event, failure)
        self.renderer.minion_failure(minion_name, failure)


class CephSaltExecutorThread(threading.Thread):
    def __init__(self, controller: CephSaltController, minion_id=None):
        super(CephSaltExecutorThread, self).__init__()
        self.controller = controller
        self.minion_id = minion_id

    def run(self):
        self.controller.executors += 1
        try:
            if not self.controller.running:
                self.controller.begin()
            model = self.controller.model
            if self.minion_id:
                logger.info("Calling: salt '%s' state.apply %s", self.minion_id, model.state)
                returns = SaltClient.local().cmd_iter(self.minion_id, 'state.apply',
                                                      [model.state,
                                                       "pillar={}".format(model.pillar)])
            else:
                logger.info("Calling: salt -G 'ceph-salt:member' state.apply %s", model.state)
                returns = SaltClient.local().cmd_iter('ceph-salt:member', 'state.apply',
                                                      [model.state,
                                                       "pillar={}".format(model.pillar)],
                                                      tgt_type='grain')
            for ret in returns:
                logger.info("Response:\n%s", json.dumps(ret, sort_keys=True, indent=2))
                now = datetime.datetime.utcnow()
                for minion, data in ret.items():
                    self.controller.minion_finished(minion, now, ret[minion]['retcode'] == 0)
                    self._process_failures(minion, data['ret'])
                    if ret[minion]['retcode'] != 0:
                        self.controller.set_retcode(2)  # failure in state execution
        except Exception as ex:  # pylint: disable=broad-except
            logger.error("Failure in CephSaltExecutor execution")
            logger.exception(ex)
            self.controller.set_retcode(3)  # failure in CephSaltExecutor execution

        if not self.controller.model.minions_rebooting() and self.controller.executors <= 1:
            logger.info("Finishing CephSaltExecutor execution")
            self.controller.end()
        self.controller.executors -= 1

    def _find_outer_event(self, exec_seq, failure_idx, ev_type=None):
        def parse_event(state_name):
            logger.debug("Parse event: %s", state_name)
            match = re.match(r'^ceph_salt_\|-([a-z]+_[a-z]+)_.+_\|-(.+)_\|.*$', state_name)
            if match:
                if ev_type is None or ev_type in match[1]:
                    return match[1], match[2]
            return None

        logger.debug("find outer event: %s", failure_idx)
        for idx in range(failure_idx - 1, -1, -1):
            event = parse_event(exec_seq[idx][0])
            if event:
                if 'step' in event[0]:
                    stage_event = self._find_outer_event(exec_seq, idx, 'stage')
                    return Event(event[0], event[1], stage_event)
                return Event(event[0], event[1])
        return None

    def _process_failures(self, minion, states):
        if isinstance(states, list):
            self.controller.minion_failure(minion, None, states)
            return

        exec_seq = list(states.items())
        exec_seq.sort(key=lambda e: e[1]['__run_num__'])

        failures = []

        for idx, (state, data) in enumerate(exec_seq):
            if not data['result']:
                event = self._find_outer_event(exec_seq, idx)
                if event is None:
                    logger.warning("could not find the outer event for state: %s: %s",
                                   state, data)
                logger.info("Reporting failure: [%s] %s %s", minion, data['__id__'], event)
                data['state'] = state
                failures.append((event, data))

        # We need to revert the failure list because the insertion algorithm of `report_failure`
        # is adding the failure at the head. For instance, if there are two failures that happened
        # in the same stage, then report_failure adds them reversed.
        for event, data in reversed(failures):
            self.controller.minion_failure(minion, event, data)


class LoadingWidget(threading.Thread):
    FRAMES = ["⣾", "⣽", "⣻", "⢿", "⡿", "⣟", "⣯", "⣷"]
    INTERVAL = 0.2

    def __init__(self):
        super(LoadingWidget, self).__init__()
        self.num_frames = len(self.FRAMES)
        self.current_frame = 0
        self.running = False
        self.lock = threading.Lock()

    def loading_string(self):
        with self.lock:
            return self.FRAMES[self.current_frame]

    def run(self):
        self.running = True
        while self.running:
            with self.lock:
                self.current_frame = (self.current_frame + 1) % self.num_frames
            time.sleep(self.INTERVAL)

    def stop(self):
        self.running = False
        self.join()


class CursesRenderer(Renderer, ScreenKeyListener):
    def __init__(self, model: CephSaltModel):
        super(CursesRenderer, self).__init__(model)
        self.selected = None
        self.screen = CursesScreen()
        self.screen.add_key_listener(self)
        self.minions_ui = {}
        for minion_id, minion in enumerate(self.model.minions_list()):
            self.minions_ui[minion_id] = {
                'expanded': False,
                'jump_to': False,
                'minion': minion.name
            }
        self._render_lock = threading.Lock()
        self.running = None
        self.paused = None
        self.loading = LoadingWidget()

    def _render_header(self, now):
        if self.model.finished():
            total_minions = self.model.minions_total()
            finished_minions = self.model.minions_finished()
            finished_str = "Finished: {}/{}".format(finished_minions, total_minions)
            succeded_str = "Succeeded: {}".format(self.model.minions_succeeded())
            warning_str = "Warnings: {}".format(self.model.minions_with_warnings())
            failed_str = "Failed: {}".format(self.model.minions_failed())
            total_time_str = "Duration: {}".format(
                self.ftime(self.model.end_time - self.model.begin_time))

            self.screen.write_header(1, finished_str, CursesScreen.COLOR_MENU, False, False, True)
            self.screen.write_header(len(finished_str) + 3,
                                     succeded_str,
                                     CursesScreen.COLOR_MENU, False, False, True)
            self.screen.write_header(len(finished_str) + len(succeded_str) + 5,
                                     warning_str,
                                     CursesScreen.COLOR_MENU, False, False, True)
            self.screen.write_header(len(finished_str) + len(warning_str) + len(succeded_str) + 7,
                                     failed_str,
                                     CursesScreen.COLOR_MENU, False, False, True)

        else:
            self.screen.clear_header()
            run_cmd_str = "Running: {}".format(self.cmd_str)
            total_minions = self.model.minions_total()
            finished_minions = self.model.minions_finished()
            finished_str = "Finished: {}/{}".format(finished_minions, total_minions)
            if self.model.begin_time is None:
                total_time_str = "Duration: -"
            else:
                total_time_str = "Duration: {}".format(self.ftime(now - self.model.begin_time))

            if (len(run_cmd_str) + len(finished_str) + len(total_time_str) + 12) > \
                    self.screen.width:
                # Not enough space
                self.screen.write_header(1, finished_str, CursesScreen.COLOR_MENU, False, False,
                                         True)
            else:
                self.screen.write_header(1, run_cmd_str, CursesScreen.COLOR_MENU, False, False,
                                         True)
                col = max(int(self.screen.width / 2 - len(finished_str) / 2), len(run_cmd_str) + 6)
                self.screen.write_header(col, finished_str, CursesScreen.COLOR_MENU, False, False,
                                         True)

        self.screen.write_header(self.screen.width - len(total_time_str) - 1, total_time_str,
                                 CursesScreen.COLOR_MENU, False, False, True)

    def _add_key_shortcut(self, col, key, desc):
        key_str = " {}".format(key)
        self.screen.write_footer(col, key_str, CursesScreen.COLOR_MINION, False, False, False)
        col += len(key_str)
        desc_str = desc.ljust(9)[:9]
        self.screen.write_footer(col, desc_str, CursesScreen.COLOR_MINION, False, True, False)
        col += len(desc_str)
        return col

    def _render_footer(self):
        self.screen.clear_footer()
        if not self.paused:
            col = self._add_key_shortcut(0, "↑|↓", "Navigate")
            if self._all_collapsed():
                col = self._add_key_shortcut(col, "c", "ExpandAll")
            else:
                col = self._add_key_shortcut(col, "c", "CollapAll")
            if self.selected is not None:
                if self.minions_ui[self.selected]['expanded']:
                    col = self._add_key_shortcut(col, "space", "CollapSel")
                else:
                    col = self._add_key_shortcut(col, "space", "ExpandSel")
            if self.screen.has_scroll():
                col = self._add_key_shortcut(col, "j|k", "Scroll")
                col = self._add_key_shortcut(col, "PgDn|PgUp", "ScrollPage")
            if not self.model.finished():
                col = self._add_key_shortcut(col, "p", "Pause")

            self.screen.write_footer(col, " ", CursesScreen.COLOR_MINION, False, False, False)

        if self.paused:
            self.screen.write_footer(1, "Paused - Press p to resume",
                                     CursesScreen.COLOR_MARKER, True, False, False, row=1)
        elif self.model.finished():
            self.screen.write_footer(1, "Press q to exit",
                                     CursesScreen.COLOR_MARKER, True, False, False, row=1)

    def _render_minion_row(self, minion, minion_id, row, selected, now):
        marker = "-" if self._is_minion_expanded(minion_id) else "+"
        color = CursesScreen.COLOR_MINION if selected else CursesScreen.COLOR_MARKER
        self.screen.write_body(row, 1, marker, color, True, selected, True)
        self.screen.write_body(row, 3, minion.name, CursesScreen.COLOR_MINION, False, selected,
                               True)
        dots_len = self.screen.width - len(minion.name) - 18
        self.screen.write_body(row, 3 + len(minion.name) + 1, "." * dots_len,
                               CursesScreen.COLOR_MINION, False, selected, True)

        timer_str = "({})".format(self.ftime(
            (minion.end_time if minion.finished() else now) - minion.begin_time))
        if not minion.finished():
            color = CursesScreen.COLOR_MINION
            self.screen.write_body(row, 3 + len(minion.name) + 1 + dots_len + 2,
                                   self.loading.loading_string(), color, False, selected,
                                   True)
            color = CursesScreen.COLOR_MINION if selected else CursesScreen.COLOR_MARKER
            self.screen.write_body(row, self.screen.body_width - len(timer_str), timer_str,
                                   color, False, selected, True)
        else:
            color = CursesScreen.COLOR_MINION if selected else (
                CursesScreen.COLOR_WARNING if minion.warnings else (
                    CursesScreen.COLOR_SUCCESS if minion.success else CursesScreen.COLOR_ERROR))
            icon = "⚠" if minion.warnings else ("✓" if minion.success else "╳")
            self.screen.write_body(row, 3 + len(minion.name) + 1 + dots_len + 2,
                                   icon, color, False, selected,
                                   True)
            color = CursesScreen.COLOR_MINION if selected else CursesScreen.COLOR_MARKER
            self.screen.write_body(row, self.screen.body_width - len(timer_str), timer_str,
                                   color, False, selected, True)

    def _render_stage_row(self, stage, row, col, now):
        self.screen.write_body(row, col, stage.desc, CursesScreen.COLOR_STAGE)
        dots_len = self.screen.body_width - len(stage.desc) - 20
        self.screen.write_body(row, col + len(stage.desc) + 1, "." * dots_len,
                               CursesScreen.COLOR_STAGE)
        if stage.begin_time:
            timer_str = "({})".format(self.ftime(
                (stage.end_time if stage.finished() else now) - stage.begin_time))
        else:
            timer_str = " "
        if stage.finished():
            color = CursesScreen.COLOR_WARNING if stage.warning else (
                CursesScreen.COLOR_SUCCESS if stage.success else CursesScreen.COLOR_ERROR)
            icon = "⚠" if stage.warning else ("✓" if stage.success else "╳")
            self.screen.write_body(row, col + len(stage.desc) + 1 + dots_len + 2,
                                   icon, color)
        else:
            self.screen.write_body(row, col + len(stage.desc) + 1 + dots_len + 2,
                                   self.loading.loading_string(), CursesScreen.COLOR_STAGE)
        self.screen.write_body(row, self.screen.body_width - len(timer_str), timer_str,
                               CursesScreen.COLOR_MARKER)

    def _render_step_row(self, step, row, col, now):
        self.screen.write_body(row, col, step.desc, CursesScreen.COLOR_STEP)
        dots_len = self.screen.width - len(step.desc) - 24
        self.screen.write_body(row, col + len(step.desc) + 1, "." * dots_len,
                               CursesScreen.COLOR_STEP)
        if step.begin_time:
            timer_str = "({})".format(self.ftime(
                (step.end_time if step.finished() else now) - step.begin_time))
        else:
            timer_str = " "
        if step.finished():
            color = CursesScreen.COLOR_SUCCESS if step.success else CursesScreen.COLOR_ERROR
            self.screen.write_body(row, col + len(step.desc) + 1 + dots_len + 2,
                                   "✓" if step.success else "╳", color)
        else:
            self.screen.write_body(row, col + len(step.desc) + 1 + dots_len + 2,
                                   self.loading.loading_string(), CursesScreen.COLOR_STEP)
        self.screen.write_body(row, self.screen.body_width - len(timer_str), timer_str,
                               CursesScreen.COLOR_MARKER)
        if step.failure:
            self.screen.write_body(row + 1, col, "|_", CursesScreen.COLOR_MARKER)
            return self._render_failure(step.failure, row + 1, col + 3) + 1

        return 1

    @staticmethod
    def break_lines(desc, width):
        """
        Breaks the string into an array of strings of max length width
        """
        desc = desc.replace("\n", "")
        # list of characters that we will use to split a string in order of
        # preference
        split_chars = (' ', '|', ',', ')', '(', '/')

        def find_split_idx(text, reverse=True):
            for ch in split_chars:
                if reverse:
                    idx = text.rfind(ch)
                else:
                    idx = text.find(ch)
                if idx != -1:
                    return idx
            return -1

        result = []
        while len(desc) > width:
            idx = find_split_idx(desc[1:width])
            if idx != -1:
                idx += 1
                result.append(desc[0:idx])
                desc = desc[idx:]
            else:
                idx = find_split_idx(desc[width:], False)
                if idx != -1:
                    idx = idx + width
                    result.append(desc[:idx])
                    desc = desc[idx:]
                else:
                    break
        result.append(desc)
        return result

    def _render_failure(self, failure, row, col):
        if isinstance(failure, str):
            line_num = 0
            for line in failure.split('\n'):
                line_width = self.screen.body_width - col - 1
                for sline in self.break_lines(line, line_width):
                    self.screen.write_body(row + line_num, col, sline, CursesScreen.COLOR_ERROR)
                    line_num += 1
            return line_num

        self.screen.write_body(row, col, failure['__id__'], CursesScreen.COLOR_ERROR)
        col += 3
        st_match = re.match(r'^(.+)_\|-.+_\|.+_\|-(.+)$', failure['state'].replace('\n', ''))
        state = "{}.{}".format(st_match[1], st_match[2])

        line_num = 1
        self.screen.write_body(row + line_num, col, "SLS: ", CursesScreen.COLOR_MARKER)
        self.screen.write_body(row + line_num, col + 5, failure['__sls__'],
                               CursesScreen.COLOR_ERROR)
        line_num += 1
        self.screen.write_body(row + line_num, col, "State: ", CursesScreen.COLOR_MARKER)
        self.screen.write_body(row + line_num, col + 7, state, CursesScreen.COLOR_ERROR)
        line_num += 1

        if state == "cmd.run":
            self.screen.write_body(row + line_num, col, "Command: ", CursesScreen.COLOR_MARKER)
            line_width = self.screen.body_width - col - len("Command: ") - 1
            for line in self.break_lines(
                    failure['name'].replace('\n', ' ').replace('\\', ' '), line_width):
                self.screen.write_body(row + line_num, col + len("Command: "),
                                       line.strip(), CursesScreen.COLOR_ERROR)
                line_num += 1

            self.screen.write_body(row + line_num, col, "Error Description: ",
                                   CursesScreen.COLOR_MARKER)
            line_num += 1
            for line in failure['changes']['stderr'].split('\n'):
                line_width = self.screen.body_width - col - 4
                for sline in self.break_lines(line, line_width):
                    self.screen.write_body(row + line_num, col + 3, sline,
                                           CursesScreen.COLOR_ERROR)
                    line_num += 1
        else:
            self.screen.write_body(row + line_num, col, "Error Description: ",
                                   CursesScreen.COLOR_MARKER)
            line_num += 1
            line_width = self.screen.body_width - col - 4
            for line in failure['comment'].split('\n'):
                for sline in self.break_lines(line, line_width):
                    self.screen.write_body(row + line_num, col + 3, sline, CursesScreen.COLOR_ERROR)
                    line_num += 1

        return line_num + 1

    def _render_minion(self, minion, minion_id, row, selected, now):
        self._render_minion_row(minion, minion_id, row, selected, now)
        if not self._is_minion_expanded(minion_id):
            if minion.finished():
                return 1
            stage = minion.last_stage
            if stage:
                self.screen.write_body(row + 1, 3, "|_", CursesScreen.COLOR_MARKER)
                self._render_stage_row(stage, row + 1, 6, now)
                step = stage.last_step
                if step:
                    self.screen.write_body(row + 2, 6, "|_", CursesScreen.COLOR_MARKER)
                    self._render_step_row(step, row + 2, 9, now)
                    return 3
                return 2
            return 1

        idx = 1
        if minion.stages:
            self.screen.write_body(row + idx, 3, "|_", CursesScreen.COLOR_MARKER)
        for stage in minion.stages.values():
            if isinstance(stage, (dict, str)):
                # failure report
                idx += self._render_failure(stage, row + idx, 6)
                continue
            self._render_stage_row(stage, row + idx, 6, now)
            idx += 1
            if stage.steps:
                self.screen.write_body(row + idx, 6, "|_", CursesScreen.COLOR_MARKER)
            for step in stage.steps.values():
                if isinstance(step, dict) or isinstance(stage, str):
                    idx += self._render_failure(step, row + idx, 9)
                    continue
                idx += self._render_step_row(step, row + idx, 9, now)

        return idx

    def _update_screen(self):
        with self._render_lock:
            now = datetime.datetime.utcnow()
            self._render_header(now)
            self._render_footer()

            self.screen.clear_body()
            row = 0
            for minion_id, minion in enumerate(self.model.minions_list()):
                num_rows = self._render_minion(minion, minion_id, row, self.selected == minion_id,
                                               now)
                if self.selected == minion_id and self.minions_ui[minion_id]['jump_to']:
                    self.minions_ui[minion_id]['row'] = row
                    self.minions_ui[minion_id]['lines'] = num_rows

                self.screen.clear_row(row + num_rows)
                row += num_rows + 1

            for minion in self.minions_ui.values():
                if minion['jump_to']:
                    minion['jump_to'] = False
                    self.screen.make_visible(minion['row'], minion['lines'])

            self.screen.refresh()

    def _is_minion_expanded(self, idx):
        return self.minions_ui[idx]['expanded']

    def up_key(self):
        if self.selected is None:
            self.selected = 0
        else:
            if self.selected > 0:
                self.selected -= 1
        self.minions_ui[self.selected]['jump_to'] = True

    def down_key(self):
        if self.selected is None:
            self.selected = 0
        else:
            if self.selected + 1 < self.model.minions_total():
                self.selected += 1
        self.minions_ui[self.selected]['jump_to'] = True

    def action_key(self):
        if self.selected is None:
            return
        self.minions_ui[self.selected]['expanded'] = not self.minions_ui[self.selected]['expanded']
        self.minions_ui[self.selected]['jump_to'] = True

    def quit_key(self):
        if self.model.finished():
            self.running = False

    def pause_key(self):
        if self.model.finished():
            self.paused = False
        elif self.paused is not None:
            self.paused = not self.paused

    def _all_collapsed(self):
        for minion in self.minions_ui.values():
            if minion['expanded']:
                return False
        return True

    def collapse_expand_all_key(self):
        all_collap = self._all_collapsed()
        for minion in self.minions_ui.values():
            minion['expanded'] = all_collap

    @staticmethod
    def ftime(tr):
        if tr.seconds > 0:
            return "{}s".format(int(round(tr.seconds + tr.microseconds / 1000000.0)))
        return "{}s".format(round(tr.seconds + tr.microseconds / 1000000.0, 1))

    def execution_stopped(self):
        pass

    def minion_failure(self, minion: str, failure: dict):
        for minion_ui in self.minions_ui.values():
            if minion_ui['minion'] == minion:
                minion_ui['expanded'] = True
                break

    def run(self):
        self.loading.start()
        self.running = True
        self.paused = False
        has_failed = False
        try:
            self.screen.start()

            finished = False
            paused = False
            logger.info("started render loop")
            while self.running:
                finished = finished and self.model.finished()
                paused = paused and self.paused
                if (self.screen.wait_for_event() or not finished) and not paused:
                    if self.model.finished():
                        finished = True
                    if self.paused:
                        paused = True
                    self._update_screen()
            logger.info("finished render loop")
        except Exception as ex:  # pylint: disable=broad-except
            logger.exception(ex)
            has_failed = True
        self.screen.shutdown()
        self.loading.stop()
        if has_failed:
            PP.println("An error occurred in the UI, please check "
                       "'{}' for further details.".format(LoggingUtil.log_file))
        else:
            if self.model.minions_with_warnings():
                PP.println()
                for minion in self.model.minions_list():
                    for warning in minion.warnings:
                        PP.pl_orange('WARNING: {} - {}'.format(minion.name, warning))
                PP.println()
            PP.println("{}. Log file may be found at '{}'.".format(
                "Finished with warnings" if self.model.minions_with_warnings() else "Finished",
                LoggingUtil.log_file))


class TerminalRenderer(Renderer):
    def execution_started(self):
        PP.println("Starting the execution of: {}".format(self.cmd_str))
        PP.println()

    def minion_update(self, minion: str):
        minion = self.model.get_minion(minion)
        if minion.finished():
            PP.println("[{}] [{:<16}] Finished {}"
                       .format(minion.end_time, minion.name[:16],
                               "successfully" if minion.success else "with failures"))
            return
        stage = minion.last_stage
        if stage is not None:
            step = stage.last_step
            if stage.finished():
                PP.println("[{}] [{:<16}] [STAGE] [END  ] {}"
                           .format(stage.end_time, minion.name[:16], stage.desc))
            elif step is not None and step.finished():
                PP.println("[{}] [{:<16}] [STEP ] [END  ] {}"
                           .format(step.end_time, minion.name[:16], step.desc))
            elif step is not None:
                PP.println("[{}] [{:<16}] [STEP ] [BEGIN] {}"
                           .format(step.begin_time, minion.name[:16], step.desc))
            else:
                PP.println("[{}] [{:<16}] [STAGE] [BEGIN] {}"
                           .format(stage.begin_time, minion.name[:16], stage.desc))

    def minion_failure(self, minion, failure):
        PP.println()
        PP.println("Failure in minion: {}".format(minion))
        PP.println(yaml.dump(failure, indent=2, default_flow_style=False))
        PP.println()

    def execution_stopped(self):
        super(TerminalRenderer, self).execution_stopped()
        if self.model.minions_with_warnings():
            PP.println()
            for minion in self.model.minions_list():
                for warning in minion.warnings:
                    PP.println('WARNING: {} - {}'.format(minion.name, warning))
        PP.println()
        PP.println("Finished execution of {} formula".format(self.model.state))
        PP.println()
        PP.println("Summary: Total={} Succeeded={} Warnings={} Failed={}"
                   .format(self.model.minions_total(),
                           self.model.minions_succeeded(),
                           self.model.minions_with_warnings(),
                           self.model.minions_failed()))


class CephSaltExecutor:
    def __init__(self, interactive, minion_id, state, pillar, prompt_proceed):
        self.prompt_proceed = prompt_proceed
        self.pillar = pillar
        self.state = state
        self.minion_id = minion_id
        self.interactive = interactive
        self.model = None
        self.renderer = None
        self.controller = None
        self.event_proc = None
        self.executor = None

    @staticmethod
    def check_formula(state, prompt_proceed):
        # verify that ceph-salt formula is available
        PP.println("Checking if {} formula is available...".format(state))
        result = SaltClient.local_cmd('ceph-salt:member', 'state.sls_exists', [state],
                                      tgt_type='grain')
        if not all(result.values()):
            # check running jobs
            logger.error("%s formula not found: checking for running Salt jobs", state)
            result = SaltClient.local_cmd('ceph-salt:member', 'saltutil.running', tgt_type='grain')
            if any(result.values()):
                logger.error("Running Salt jobs detected: refusing to apply Salt Formula")
                PP.pl_red("Running Salt jobs detected. The safest thing to do in this case is "
                          "wait. Once the jobs complete or time out, you will be able to apply "
                          "the Salt Formula again.")
                return 5
            # reboot salt-master
            prompt_proceed("Formula not found. Do you want to "
                           "restart 'salt-master' to load '{}' formula? ".format(state), 'n')
            PP.println("Restarting 'salt-master' to load '{}' formula...".format(state))
            logger.info('restarting salt-master service')
            result = SaltClient.caller_cmd('service.restart', ['salt-master'])
            if not result:
                logger.warning('failed to restart salt-master process')
                PP.pl_red('Failed to restart salt-master service, please restart it manually')
                return 6

        # check ceph-salt formula again after salt-master restart
        result = SaltClient.local_cmd('ceph-salt:member', 'state.sls_exists', [state],
                                      tgt_type='grain')
        if not all(result.values()):
            PP.pl_red("Could not find {} formula. Please check if ceph-salt-formula package "
                      "is installed".format(state))
            return 7

        return 0

    @staticmethod
    def check_sync_all():
        PP.println("Syncing minions with the master...")
        try:
            sync_all()
        except ValidationException as e:
            logger.error(e)
            PP.pl_red(e)
            return 2
        return 0

    @staticmethod
    def check_cluster(state, minion_id, deployed):
        PP.println("Checking if there is an existing Ceph cluster...")
        if deployed:
            PP.println("Ceph cluster already exists")
        else:
            PP.println("No Ceph cluster deployed yet")

        # day 1, but minion_id specified
        if state in ['ceph-salt', 'ceph-salt.apply']:
            if minion_id is not None and not deployed:
                logger.error("ceph cluster not deployed and minion_id provided")
                PP.pl_red("Ceph cluster is not deployed yet, please apply the config to "
                          "all minions at the same time to bootstrap a new Ceph cluster: "
                          "\"ceph-salt apply\"")
                return 9
        # Invalid minion_id
        if minion_id is not None:
            salt_minions = CephNodeManager.list_all_minions()
            if minion_id not in salt_minions:
                logger.error("cannot find minion: %s", minion_id)
                PP.pl_red("Cannot find minion '{}'".format(minion_id))
                return 10
        return 0

    @staticmethod
    def ping_minions():
        # verify that all minions are alive
        PP.println("Checking if minions respond to ping...")
        all_minions = PillarManager.get('ceph-salt:minions:all', [])
        minion_count = len(all_minions)
        PP.println("Pinging {} minions...".format(minion_count))
        result = SaltClient.local_cmd('ceph-salt:member', 'test.ping', tgt_type='grain')
        # result will be something like {'node3.ses7.test': True, 'master.ses7.test': True,
        # 'node2.ses7.test': True, 'node1.ses7.test': True}
        minions_responding = 0
        retval = 0
        for minion, response in result.items():
            log_msg = "ping_minions: minion {} ".format(minion)
            if isinstance(response, bool) and response:
                minions_responding += 1
                log_msg += "responded to ping"
                logger.info(log_msg)
            else:
                log_msg += "DID NOT RESPOND TO PING"
                PP.pl_red("{} did not respond to ping".format(minion))
                logger.error(log_msg)
                retval = 4
        return retval

    @staticmethod
    def check_dns():
        retval = None
        PP.println("Checking if minions have functioning DNS...")
        minion_hostnames = PillarManager.get('ceph-salt:minions:all', [])
        minion_count = len(minion_hostnames)
        PP.println("Running DNS lookups on {} minions...".format(minion_count))
        salt_result = SaltClient.local().cmd(
            'ceph-salt:member',
            'ceph_salt.probe_dns',
            minion_hostnames,
            tgt_type='grain')
        log_msg = "probe_dns returned: {}".format(salt_result)
        logger.info(log_msg)
        if all(salt_result.values()):
            logger.info("All minion hostnames are resolvable on all minions")
            retval = 0
        else:
            bad_dns_list = []
            for hostname, result in salt_result.items():
                if result:
                    log_msg = ("All minion hostnames are resolvable on host {}"
                               .format(hostname))
                    logger.info(log_msg)
                else:
                    log_msg = ("All minion hostnames are NOT resolvable on host {}"
                               .format(hostname))
                    logger.error(log_msg)
                    bad_dns_list.append(hostname)
            PP.pl_red("DNS issues detected on host(s) {}".format(", ".join(bad_dns_list)))
            PP.pl_red("One or more minions cannot resolve the fully-qualified hostnames "
                      "of other minions. Please fix this issue and try again.")
            retval = 8
        return retval

    @staticmethod
    def check_time_sync():
        retval = None
        PP.println("/time_server is disabled. Will check if minions have a time_sync "
                   "service enabled and running...")
        minion_hostnames = PillarManager.get('ceph-salt:minions:all', [])
        minion_count = len(minion_hostnames)
        PP.println("Checking time sync service on {} minions...".format(minion_count))
        salt_result = SaltClient.local().cmd(
            'ceph-salt:member',
            'ceph_salt.probe_time_sync',
            [],
            tgt_type='grain')
        log_msg = "probe_time_sync returned: {}".format(salt_result)
        logger.info(log_msg)
        if all(salt_result.values()):
            logger.info("Time sync service is enabled and running on all minions")
            retval = 0
        else:
            bad_time_sync_list = []
            for hostname, result in salt_result.items():
                if result:
                    log_msg = ("Time sync service is enabled and running on host {}"
                               .format(hostname))
                    logger.info(log_msg)
                else:
                    log_msg = ("Time sync service is NOT enabled and running on host {}"
                               .format(hostname))
                    logger.error(log_msg)
                    bad_time_sync_list.append(hostname)
            PP.pl_red("Time sync issues detected on host(s) {}"
                      .format(", ".join(bad_time_sync_list)))
            PP.pl_red("/time_server is disabled. In that case, a time sync service "
                      "must be enabled and running on all minions. Please fix this "
                      "issue and try again.")
            retval = 14
        return retval

    @staticmethod
    def check_external_time_servers(ts_minion, external_ts_list):
        PP.println("Installing python3-ntplib on time server node...")
        salt_result = SaltClient.local().cmd(
            ts_minion, 'pkg.install', ["name='python3-ntplib'", "refresh=True"]
        )
        for external_ts in external_ts_list:
            max_attempts = 10
            for attempt in range(1, max_attempts + 1):
                PP.println("Probing external time server {} (attempt {} of {})...".format(
                    external_ts,
                    attempt,
                    max_attempts
                ))
                salt_result = SaltClient.local().cmd(
                    ts_minion,
                    'ceph_salt.probe_ntp',
                    [external_ts]
                )
                if salt_result[ts_minion] == 0:
                    break
                if salt_result[ts_minion] == 1:
                    time.sleep(3)
                    continue
                if salt_result[ts_minion] == 2:
                    PP.pl_red(
                        "Hostname '{}' could not be resolved to IP address (is it valid?)"
                        .format(external_ts)
                    )
                    return 12
                PP.pl_red(
                    "Problem communicating with external time server '{}' (check the log?)"
                    .format(external_ts)
                )
                return 13
            else:  # inner loop terminated without break
                PP.pl_red(
                    "External time server '{}' did not respond to probe"
                    .format(external_ts)
                )
                return 11
        return 0

    @staticmethod
    def check_prerequisites(minion_id, state, prompt_proceed):
        deployed = None

        # check salt master is configured
        try:
            check_salt_master_status()
        except ValidationException as e:
            logger.error(e)
            PP.pl_red(e)
            return 1, deployed

        # sync_all
        retcode = CephSaltExecutor.check_sync_all()
        if retcode > 0:
            return retcode, deployed

        deployed = CephOrch.deployed()

        # check config is valid
        error_msg = validate_config(deployed)
        if error_msg:
            logger.error(error_msg)
            PP.pl_red(error_msg)
            return 3, deployed

        # ping minions
        retcode = CephSaltExecutor.ping_minions()
        if retcode > 0:
            return retcode, deployed

        # check formula
        retcode = CephSaltExecutor.check_formula(state, prompt_proceed)
        if retcode > 0:
            return retcode, deployed

        # check dns
        retcode = CephSaltExecutor.check_dns()
        if retcode > 0:
            return retcode, deployed

        # check cluster
        if state not in ['ceph-salt.purge']:
            retcode = CephSaltExecutor.check_cluster(state, minion_id, deployed)
            if retcode > 0:
                return retcode, deployed

        # check external time servers, if any
        if state in ['ceph-salt', 'ceph-salt.apply']:
            time_server_enabled = PillarManager.get('ceph-salt:time_server:enabled')
            if time_server_enabled:
                time_server_host = PillarManager.get('ceph-salt:time_server:server_host')
                ext_time_servers = PillarManager.get('ceph-salt:time_server:external_time_servers')
                if ext_time_servers:
                    retcode = CephSaltExecutor.check_external_time_servers(
                        time_server_host,
                        ext_time_servers
                    )
                    if retcode > 0:
                        return retcode, deployed
            else:
                retcode = CephSaltExecutor.check_time_sync()
                if retcode > 0:
                    return retcode, deployed

        return 0, deployed

    def run(self):

        # validate
        retcode, deployed = self.check_prerequisites(self.minion_id, self.state,
                                                     self.prompt_proceed)
        if retcode > 0:
            return retcode

        # Reset minions to make sure that all of them start the execution at the same state.
        # For instance, ceph-salt relies on 'ceph-salt:execution:*' grains for the orchestration
        # so we need to ensure that those grains are reset beforehand
        PP.println("Reseting execution grains...")
        if self.minion_id:
            logger.info("Calling: salt '%s' state.apply ceph-salt.reset", self.minion_id)
            returns = SaltClient.local().cmd(self.minion_id, 'state.apply',
                                             ['ceph-salt.reset'])
        else:
            logger.info("Calling: salt -G 'ceph-salt:member' state.apply ceph-salt.reset")
            returns = SaltClient.local().cmd('ceph-salt:member', 'state.apply',
                                             ['ceph-salt.reset'],
                                             tgt_type='grain')
        for minion, data in returns.items():
            for state, ret in data.items():
                if not ret['result']:
                    logger.error("%s - %s - %s", minion, state, ret)
                    PP.pl_red('Failed to reset execution grains on {}'.format(minion))
                    return 100

        # init
        self.model = CephSaltModel(self.minion_id, self.state, self.pillar)
        if 'ceph-salt' not in self.pillar:
            self.pillar['ceph-salt'] = {}
        if 'execution' not in self.pillar['ceph-salt']:
            self.pillar['ceph-salt']['execution'] = {}
        minions = [self.minion_id] if self.minion_id else sorted(self.model.minions_names())
        self.pillar['ceph-salt']['execution']['minions'] = minions
        self.pillar['ceph-salt']['execution']['deployed'] = deployed
        if self.interactive:
            self.renderer = CursesRenderer(self.model)
        else:
            self.renderer = TerminalRenderer(self.model)
        self.controller = CephSaltController(self.model, self.renderer)
        self.event_proc = SaltEventProcessor(self.model.minions_names())
        self.event_proc.add_listener(self.controller)
        self.executor = CephSaltExecutorThread(self.controller, self.minion_id)

        # start
        PP.println("Starting...")
        self.event_proc.start()
        self.executor.start()
        self.renderer.run()
        self.event_proc.stop()
        self.executor.join()
        return self.controller.retcode


def run_disengage_safety():
    PillarManager.set('ceph-salt:execution:safety_disengage_time', time.time())
    return 0


def run_purge(non_interactive, yes_i_really_really_mean_it, prompt_proceed):
    admin_minions = GrainsManager.filter_by('ceph-salt:roles', 'admin')
    if not admin_minions:
        PP.pl_red("No ceph-salt admin minions found.")
        return 1
    admin_minion = admin_minions[0]
    if not SaltClient.local().cmd(admin_minion, 'ceph_salt.is_safety_disengaged')[admin_minion]:
        PP.pl_red("Safety is not disengaged. Run 'ceph-salt disengage-safety' "
                  "to disable protection against dangerous operations.")
        return 2
    fsid = None
    for minion in admin_minions:
        fsid = SaltClient.local().cmd(minion, 'ceph_orch.fsid')[minion]
        if fsid is not None:
            break
    if not fsid:
        PP.pl_red("Unable to find cluster FSID. Is ceph cluster running?")
        return 3
    if not yes_i_really_really_mean_it:
        if non_interactive:
            PP.pl_red("This command would completely REMOVE ceph cluster '{}' and all the data "
                      "it contains. If you are really sure you want to do that, include the "
                      "'--yes-i-really-really-mean-it' option.".format(fsid))
            return 4
        prompt_proceed("You are about to permanently REMOVE ceph cluster '{}'. "
                       "Proceed?".format(fsid), 'n')
        prompt_proceed("Proceed, even though this may destroy valuable data?", 'n')
    executor = CephSaltExecutor(not non_interactive, None,
                                'ceph-salt.purge', {
                                    'ceph-salt': {
                                        'execution': {
                                            'fsid': fsid
                                        }
                                    }
                                }, prompt_proceed)
    return executor.run()


def run_stop(non_interactive, yes_i_really_really_mean_it, prompt_proceed):
    admin_minions = PillarManager.get('ceph-salt:minions:admin', [])
    if not admin_minions:
        PP.pl_red("No ceph-salt admin minions found.")
        return 1
    admin_minion = admin_minions[0]
    fsid = SaltClient.local_cmd(admin_minion, 'ceph_orch.fsid',
                                full_return=True)[admin_minion].get('ret')
    if not fsid:
        PP.pl_red("Unable to find cluster FSID. Is ceph cluster running?")
        return 2
    if not yes_i_really_really_mean_it:
        if non_interactive:
            PP.pl_red("This command will STOP ceph cluster '{}'. "
                      "If you are really sure you want to do that, include the "
                      "'--yes-i-really-really-mean-it' option.".format(fsid))
            return 4
        prompt_proceed("You are about to STOP ceph cluster '{}'. "
                       "Proceed?".format(fsid), 'n')
        prompt_proceed("Before proceeding, make sure any clients accessing the cluster are "
                       "shut down or disconnected. Proceed?", 'n')
    executor = CephSaltExecutor(not non_interactive, None,
                                'ceph-salt.stop', {
                                    'ceph-salt': {
                                        'execution': {
                                            'fsid': fsid
                                        }
                                    }
                                }, prompt_proceed)
    return executor.run()
