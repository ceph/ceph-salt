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


def reboot_if_needed(name):
    ret = {'name': name, 'changes': {}, 'comment': '', 'result': False}
    if __grains__.get('os_family') == 'Suse':
        needs_reboot = __salt__['cmd.run_all']('zypper ps')['retcode'] > 0
    else:
        ret['comment'] = 'Unsupported distribution: Unable to check if reboot is needed'
        return ret
    if needs_reboot:
        is_master = __salt__['service.status']('salt-master')
        if is_master:
            ret['comment'] = 'Salt master must be rebooted manually'
            return ret
        running_ceph_containers = len(subprocess.check_output(['podman',
                                                               'ps',
                                                               '--filter',
                                                               'label=ceph=True',
                                                               '-q']).splitlines())
        if running_ceph_containers > 0:
            ret['comment'] = 'Running ceph containers found, please reboot manually'
            return ret
        __salt__['event.send']('ceph-salt/minion_reboot', data={'desc': 'Rebooting...'})
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
