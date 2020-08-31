# -*- encoding: utf-8 -*-
import logging
import subprocess
import time


logger = logging.getLogger(__name__)


def _send_event(tag, data):
    __salt__['event.send'](tag, data=data)
    return {
        'name': tag,
        'result': True,
        'changes': data,
        'comment': ''
    }


def begin_stage(name):
    return _send_event('ceph-salt/stage/begin', data={'desc': name})


def end_stage(name):
    return _send_event('ceph-salt/stage/end', data={'desc': name})


def begin_step(name):
    return _send_event('ceph-salt/step/begin', data={'desc': name})


def end_step(name):
    return _send_event('ceph-salt/step/end', data={'desc': name})


def set_reboot_needed(name, force=False):
    ret = {'name': name, 'changes': {}, 'comment': '', 'result': False}
    if force:
        needs_reboot = True
    else:
        if __grains__.get('os_family') == 'Suse':
            cmd_ret = __salt__['cmd.run_all']('zypper ps')
            needs_reboot = cmd_ret['stdout'].find('No processes using deleted files found') < 0
        else:
            ret['comment'] = 'Unsupported distribution: Unable to check if reboot is needed'
            return ret
    reboot_needed_step = "Reboot is not needed"
    if needs_reboot:
        if __grains__.get('os_family') == 'Suse':
            reboot_needed_step = "Reboot is needed because some processes are using deleted files"
        else:
            reboot_needed_step = "Reboot is needed"

    __salt__['event.send']('ceph-salt/step/start',
                               data={'desc': reboot_needed_step})
    __salt__['grains.set']('ceph-salt:execution:reboot_needed', needs_reboot)
    __salt__['event.send']('ceph-salt/step/end',
                               data={'desc': reboot_needed_step})
    # Try to guarantee that event reaches master before job finish
    time.sleep(5)

    ret['result'] = True
    return ret


def reboot_if_needed(name):
    """
    Requires the following grains to be set:
      - ceph-salt:execution:reboot_needed
    """
    ret = {'name': name, 'changes': {}, 'comment': '', 'result': False}
    needs_reboot = __salt__['grains.get']('ceph-salt:execution:reboot_needed')
    if needs_reboot:
        is_master = __salt__['service.status']('salt-master')
        if is_master:
            __salt__['event.send']('ceph-salt/stage/warning',
                                   data={'desc': "Salt master must be rebooted manually"})
            ret['result'] = True
            return ret
        __salt__['event.send']('ceph-salt/minion_reboot', data={'desc': 'Rebooting...'})
        # Try to guarantee that event reaches master before job finish
        time.sleep(5)
        __salt__['system.reboot']()
    ret['result'] = True
    return ret


def wait_for_grain(name, grain, hosts, timeout=1800):
    ret = {'name': name, 'changes': {}, 'comment': '', 'result': False}
    completed_counter = 0
    starttime = time.time()
    timelimit = starttime + timeout
    while completed_counter < len(hosts):
        is_timedout = time.time() > timelimit
        if is_timedout:
            ret['comment'] = 'Timeout value reached.'
            return ret
        time.sleep(15)
        completed_counter = 0
        for host in hosts:
            grain_value = __salt__['ceph_salt.get_remote_grain'](host, 'ceph-salt:execution:failed')
            if grain_value:
                ret['comment'] = 'One or more minions failed.'
                return ret
            grain_value = __salt__['ceph_salt.get_remote_grain'](host, grain)
            if grain_value:
                completed_counter += 1
        logger.info("Waiting for grain '%s' (%s/%s)", grain, completed_counter, len(hosts))
    ret['result'] = True
    return ret


def wait_for_package(name, package, hosts, timeout=1800):
    ret = {'name': name, 'changes': {}, 'comment': '', 'result': False}
    completed_counter = 0
    starttime = time.time()
    timelimit = starttime + timeout
    while completed_counter < len(hosts):
        is_timedout = time.time() > timelimit
        if is_timedout:
            ret['comment'] = 'Timeout value reached.'
            return ret
        time.sleep(15)
        completed_counter = 0
        for host in hosts:
            grain_value = __salt__['ceph_salt.get_remote_grain'](host, 'ceph-salt:execution:failed')
            if grain_value:
                ret['comment'] = 'One or more minions failed.'
                return ret
            ssh_user = __pillar__['ceph-salt']['ssh']['user']
            cmd_ret = __salt__['cmd.run_all']("ssh -o StrictHostKeyChecking=no "
                                              "-i /tmp/ceph-salt-ssh-id_rsa {0}@{1} "
                                              "'rpm -qa {2} | grep {2}'".format(ssh_user, host,
                                                                                package))
            if cmd_ret['retcode'] == 0:
                completed_counter += 1
        logger.info("Waiting for package '%s' (%s/%s)", package, completed_counter, len(hosts))
    ret['result'] = True
    return ret


def wait_for_ancestor_minion_grain(name, grain, if_grain, timeout=36000):
    """
    This state will wait for a grain on the minion that appears immediately before
    the current minion, on the 'ceph-salt:execution:minions' pillar list.

    Usefull when dealing with sequential operations.
    """
    ret = {'name': name, 'changes': {}, 'comment': '', 'result': False}
    id = __grains__['id']
    minions = __pillar__['ceph-salt']['execution']['minions']
    if id not in minions:
        ret['comment'] = "Unexpected minion: Minion '{}' not in the execution plan".format(id)
        return ret
    if_grain_value = __salt__['grains.get'](if_grain)
    if if_grain_value:
        ancestor_minion = None
        for i in range(len(minions)):
            if i < (len(minions)-1) and minions[i+1] == id:
                ancestor_minion = minions[i]
                break
        if ancestor_minion:
            begin_stage("Wait for '{}'".format(ancestor_minion))
            ancestor_minion_ready = False
            starttime = time.time()
            timelimit = starttime + timeout
            while not ancestor_minion_ready:
                is_timedout = time.time() > timelimit
                if is_timedout:
                    ret['comment'] = 'Timeout value reached.'
                    return ret
                grain_value = __salt__['ceph_salt.get_remote_grain'](ancestor_minion, 'ceph-salt:execution:failed')
                if grain_value:
                    ret['comment'] = 'Minion {} failed.'.format(ancestor_minion)
                    return ret
                grain_value = __salt__['ceph_salt.get_remote_grain'](ancestor_minion, grain)
                if grain_value:
                    ancestor_minion_ready = True
                if not ancestor_minion_ready:
                    logger.info("Waiting for grain '%s' on '%s'", grain, ancestor_minion)
                    time.sleep(15)
            end_stage("Wait for '{}'".format(ancestor_minion))
    ret['result'] = True
    return ret

def check_safety(name):
    ret = {'name': name, 'changes': {}, 'comment': '', 'result': False}
    cmd_ret = __salt__['ceph_salt.is_safety_disengaged']()
    if cmd_ret is not True:
        ret['comment'] = "Safety is not disengaged. Run 'ceph-salt disengage-safety' to disable protection against dangerous operations."
        return ret
    ret['result'] = True
    return ret

def _add_to_blocking_queue(host, max_queue_size, timeout):
    python_script = '''
import json
import sys
import time
from filelock import FileLock, Timeout

BLOCKING_QUEUE = '/tmp/ceph-salt-blocking-queue.json'
BLOCKING_QUEUE_LOCK = '/tmp/ceph-salt-blocking-queue.lock'

minion_id = '{0}'
timeout = {1}
max_queue_size = {2}
starttime = time.time()
timelimit = starttime + timeout
while True:
    is_timedout = time.time() > timelimit
    if is_timedout:
        print('Timeout value reached.', file=sys.stderr)
        sys.exit(1)
    lock = FileLock(BLOCKING_QUEUE_LOCK)
    try:
        with lock.acquire(timeout=0):
            try:
                with open(BLOCKING_QUEUE, 'r') as db_file:
                    db_json = json.loads(db_file.read())
            except (FileNotFoundError, json.decoder.JSONDecodeError):
                db_json = []
            if minion_id in db_json:
                sys.exit(0)
            elif len(db_json) < max_queue_size:
                with open(BLOCKING_QUEUE, 'w') as db_file:
                    db_json.append(minion_id)
                    print(db_json)
                    db_file.write(json.dumps(db_json))
                    sys.exit(0)
    except Timeout:
        pass
    time.sleep(5)
'''.format(__grains__['id'], timeout, max_queue_size)
    ssh_user = __pillar__['ceph-salt']['ssh']['user']
    sudo = 'sudo ' if ssh_user != 'root' else ''
    return __salt__['cmd.run_all']("ssh -o StrictHostKeyChecking=no "
                                   "-i /tmp/ceph-salt-ssh-id_rsa {}@{} "
                                   "\"{}python3 - "
                                   "<<EOF\n{}\nEOF\"".format(ssh_user,
                                                             host,
                                                             sudo,
                                                             python_script))


def _remove_from_blocking_queue(host, timeout):
    python_script = '''
import json
import sys
from filelock import FileLock

BLOCKING_QUEUE = '/tmp/ceph-salt-blocking-queue.json'
BLOCKING_QUEUE_LOCK = '/tmp/ceph-salt-blocking-queue.lock'

minion_id = '{0}'
timeout = {1}

lock = FileLock(BLOCKING_QUEUE_LOCK)
with lock.acquire(timeout=600):
    try:
        with open(BLOCKING_QUEUE, 'r') as db_file:
            db_json = json.loads(db_file.read())
    except (FileNotFoundError, json.decoder.JSONDecodeError):
        db_json = []
    with open(BLOCKING_QUEUE, 'w') as db_file:
        if minion_id in db_json:
            db_json.remove(minion_id)
        print(db_json)
        db_file.write(json.dumps(db_json))
'''.format(__grains__['id'], timeout)
    ssh_user = __pillar__['ceph-salt']['ssh']['user']
    sudo = 'sudo ' if ssh_user != 'root' else ''
    return __salt__['cmd.run_all']("ssh -o StrictHostKeyChecking=no "
                                   "-i /tmp/ceph-salt-ssh-id_rsa {}@{} "
                                   "\"{}python3 - "
                                   "<<EOF\n{}\nEOF\"".format(ssh_user,
                                                             host,
                                                             sudo,
                                                             python_script))


def pull_image(name, max_degree_of_parallelism=10, add_timeout=3600, remove_timeout=600):
    ret = {'name': name, 'changes': {}, 'comment': '', 'result': False}
    admin_minion = __pillar__['ceph-salt']['minions']['admin'][0]
    required_package = 'python3-filelock'
    __salt__['event.send']('ceph-salt/step/begin',
                           data={'desc': "Wait for package '{}' to be available on '{}'".format(required_package, admin_minion)})
    # Guarantee that 'admin_minion' has 'python3-filelock' installed
    wait_ret = wait_for_package(name, required_package, [admin_minion])
    if not wait_ret['result']:
        return wait_ret
    __salt__['event.send']('ceph-salt/step/end',
                           data={'desc': "Wait for package '{}' to be available on '{}'".format(required_package, admin_minion)})
    __salt__['event.send']('ceph-salt/step/begin',
                           data={'desc': "Wait for other minions to complete download"})
    # Wait for a slot to pull image
    cmd_ret = _add_to_blocking_queue(admin_minion, max_degree_of_parallelism, add_timeout)
    if cmd_ret['retcode'] > 0:
        ret['comment'] = cmd_ret['stderr']
        return ret
    __salt__['event.send']('ceph-salt/step/end',
                           data={'desc': "Wait for other minions to complete download"})
    __salt__['event.send']('ceph-salt/step/begin',
                           data={'desc': "Download ceph container image"})
    # Pull image
    ceph_image = __pillar__['ceph-salt']['container']['images']['ceph']
    cmd_ret = __salt__['cmd.run_all']("cephadm --image {} pull".format(ceph_image))
    if cmd_ret['retcode'] > 0:
        ret['comment'] = 'Failed to pull image {}'.format(ceph_image)
        return ret
    # Release slot
    cmd_ret = _remove_from_blocking_queue(admin_minion, remove_timeout)
    if cmd_ret['retcode'] > 0:
        ret['comment'] = cmd_ret['stderr']
        return ret
    __salt__['event.send']('ceph-salt/step/end',
                           data={'desc': "Download ceph container image"})
    ret['result'] = True
    return ret
