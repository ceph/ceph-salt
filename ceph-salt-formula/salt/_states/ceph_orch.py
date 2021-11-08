# -*- encoding: utf-8 -*-
import json
import logging
import time


logger = logging.getLogger(__name__)


def set_admin_host(name, if_grain=None, timeout=1800):
    ret = {'name': name, 'changes': {}, 'comment': '', 'result': False}
    if_grain_value = True
    if if_grain is not None:
        if_grain_value = __salt__['grains.get'](if_grain)
    if if_grain_value:
        __salt__['event.send']('ceph-salt/stage/begin',
                               data={'desc': "Find an admin host"})
        starttime = time.time()
        timelimit = starttime + timeout
        configured_admin_host = None
        while not configured_admin_host:
            is_timedout = time.time() > timelimit
            if is_timedout:
                ret['comment'] = 'Timeout value reached.'
                return ret
            time.sleep(15)
            bootstrap_minion = __pillar__['ceph-salt'].get('bootstrap_minion')
            if bootstrap_minion:
                failed = __salt__['ceph_salt.get_remote_grain'](bootstrap_minion, 'ceph-salt:execution:failed')
                if failed:
                    ret['comment'] = 'Bootstrap minion failed.'
                    return ret
            admin_hosts = __pillar__['ceph-salt']['minions']['admin']
            for admin_host in admin_hosts:
                failed = __salt__['ceph_salt.get_remote_grain'](admin_host, 'ceph-salt:execution:failed')
                if failed:
                    ret['comment'] = 'One or more admin minions failed.'
                    return ret
                status_ret = __salt__['ceph_salt.ssh'](
                    admin_host,
                    "if [[ -f /etc/ceph/ceph.conf "
                    "&& -f /etc/ceph/ceph.client.admin.keyring ]]; "
                    "then timeout 60 sudo ceph -s; "
                    "else (exit 1); fi")
                if status_ret['retcode'] == 0:
                    configured_admin_host = admin_host
                    break

        __salt__['event.send']('ceph-salt/stage/end',
                               data={'desc': "Find an admin host"})
        __salt__['grains.set']('ceph-salt:execution:admin_host', configured_admin_host)
    ret['result'] = True
    return ret

def wait_until_ceph_orch_available(name, timeout=1800):
    """
    Requires the following grains to be set:
      - ceph-salt:execution:admin_host
    """
    ret = {'name': name, 'changes': {}, 'comment': '', 'result': False}
    starttime = time.time()
    timelimit = starttime + timeout
    while True:
        is_timedout = time.time() > timelimit
        if is_timedout:
            ret['comment'] = 'Timeout value reached.'
            return ret
        time.sleep(15)
        admin_host = __salt__['grains.get']('ceph-salt:execution:admin_host')
        status_ret = __salt__['ceph_salt.ssh'](
                        admin_host,
                        "if [[ -f /etc/ceph/ceph.conf "
                        "&& -f /etc/ceph/ceph.client.admin.keyring ]]; "
                        "then timeout 60 sudo ceph orch status --format=json; "
                        "else (exit 1); fi")
        if status_ret['retcode'] == 0:
            status = json.loads(status_ret['stdout'])
            if status.get('available'):
                break
    ret['result'] = True
    return ret

def add_host(name, host, ipaddr, is_admin=False):
    """
    Requires the following grains to be set:
      - ceph-salt:execution:admin_host
    """
    ret = {'name': name, 'changes': {}, 'comment': '', 'result': False}
    admin_host = __salt__['grains.get']('ceph-salt:execution:admin_host')
    cmd_ret = __salt__['ceph_salt.ssh'](
                       admin_host,
                       "sudo ceph orch host add {} {}{}".format(
                           host,
                           ipaddr,
                           ' _admin' if is_admin else '',
                        ),
                       attempts=10)
    if cmd_ret['retcode'] == 0:
        ret['result'] = True
    else:
        ret['comment'] = cmd_ret.get('stderr')
    return ret


def rm_clusters(name):
    """
    Requires the following pillar to be set:
      - ceph-salt:execution:fsid
    """
    ret = {'name': name, 'changes': {}, 'comment': '', 'result': False}
    fsid = __salt__['pillar.get']('ceph-salt:execution:fsid')
    __salt__['ceph_salt.begin_stage']("Remove cluster {}".format(fsid))
    cmd_ret = __salt__['cmd.run_all']("cephadm rm-cluster --fsid {} "
                                      "--force".format(fsid))
    if cmd_ret['retcode'] == 0:
        __salt__['ceph_salt.end_stage']("Remove cluster {}".format(fsid))
        ret['result'] = True
    else:
        ret['comment'] = cmd_ret.get('stderr')
    return ret


def copy_ceph_conf_and_keyring_from_admin(name):
    """
    Requires the following grains to be set:
      - ceph-salt:execution:admin_host
    """
    ret = {'name': name, 'changes': {}, 'comment': '', 'result': False}
    admin_host = __salt__['grains.get']('ceph-salt:execution:admin_host')
    cmd_ret = __salt__['ceph_salt.sudo_rsync'](
                       "cephadm@{}:/etc/ceph/{{ceph.conf,ceph.client.admin.keyring}}".format(admin_host),
                       "/etc/ceph/",
                       False)
    if cmd_ret['retcode'] == 0:
        ret['result'] = True
    else:
        ret['comment'] = cmd_ret.get('stderr')
    return ret


def copy_ceph_conf_and_keyring_to_any_admin(name):
    ret = {'name': name, 'changes': {}, 'comment': '', 'result': False}
    admin_host = __pillar__['ceph-salt']['minions']['admin'][0]
    cmd_ret = __salt__['ceph_salt.sudo_rsync'](
                       "/tmp/ceph.client.admin.keyring",
                       "cephadm@{}:/etc/ceph/ceph.client.admin.keyring".format(admin_host),
                       True)
    if cmd_ret['retcode'] != 0:
        ret['comment'] = cmd_ret.get('stderr')
        return ret
    cmd_ret = __salt__['ceph_salt.sudo_rsync'](
                       "/etc/ceph/ceph.conf",
                       "cephadm@{}:/etc/ceph/".format(admin_host),
                       True)
    if cmd_ret['retcode'] != 0:
        ret['comment'] = cmd_ret.get('stderr')
        return ret
    ret['result'] = True
    return ret


def wait_for_ceph_orch_host_ok_to_stop(name, if_grain, timeout=36000):
    """
    Requires the following grains to be set:
      - ceph-salt:execution:admin_host
    """
    ret = {'name': name, 'changes': {}, 'comment': '', 'result': False}
    if_grain_value = __salt__['grains.get'](if_grain)
    if if_grain_value:
        host = __grains__['host']
        __salt__['event.send']('ceph-salt/stage/begin',
                               data={'desc': "Wait for 'ceph orch host ok-to-stop {}'".format(host)})
        ok_to_stop = False
        starttime = time.time()
        timelimit = starttime + timeout
        while not ok_to_stop:
            is_timedout = time.time() > timelimit
            if is_timedout:
                ret['comment'] = 'Timeout value reached.'
                return ret
            admin_host = __salt__['grains.get']('ceph-salt:execution:admin_host')
            cmd_ret = __salt__['ceph_salt.ssh'](
                               admin_host,
                               "sudo ceph orch host ok-to-stop {}".format(host))
            ok_to_stop = cmd_ret['retcode'] == 0
            if not ok_to_stop:
                logger.info("Waiting for 'ceph_orch.host_ok_to_stop'")
                time.sleep(15)
        __salt__['event.send']('ceph-salt/stage/end',
                               data={'desc': "Wait for 'ceph orch host ok-to-stop {}'".format(host)})
    ret['result'] = True
    return ret


def stop_service(name, service):
    ret = {'name': name, 'changes': {}, 'comment': '', 'result': False}
    cmd_ret = __salt__['cmd.run_all'](
                       "ceph orch stop {}".format(service))
    if cmd_ret['retcode'] == 0:
        ret['result'] = True
    else:
        ret['comment'] = cmd_ret.get('stderr')
    return ret


def wait_until_service_stopped(name, service, timeout=1800):
    ret = {'name': name, 'changes': {}, 'comment': '', 'result': False}
    service_stopped = False
    starttime = time.time()
    timelimit = starttime + timeout
    while not service_stopped:
        is_timedout = time.time() > timelimit
        if is_timedout:
            ret['comment'] = 'Timeout value reached.'
            return ret
        cmd_ret = __salt__['cmd.run_all'](
                           "ceph orch ls --service-type {} --format json".format(service))
        if cmd_ret['retcode'] != 0:
            ret['comment'] = cmd_ret.get('stderr')
            return ret
        try:
            status = json.loads(cmd_ret['stdout'])[0]['status']
            service_stopped = status['running'] == 0
        except json.decoder.JSONDecodeError as exc:
            if 'No services reported' in cmd_ret['stdout']:
                service_stopped = True
            else:
                raise exc
    ret['result'] = True
    return ret


def stop_ceph_fsid(name):
    """
    Requires the following pillar to be set:
      - ceph-salt:execution:fsid
    """
    ret = {'name': name, 'changes': {}, 'comment': '', 'result': False}
    fsid = __salt__['pillar.get']('ceph-salt:execution:fsid')
    service = 'ceph-{}.target'.format(fsid)
    __salt__['ceph_salt.begin_stage']("Stop '{}'".format(service))
    cmd_ret = __salt__['cmd.run_all']("systemctl stop {} ".format(service))
    if cmd_ret['retcode'] == 0:
        __salt__['ceph_salt.end_stage']("Stop '{}'".format(service))
        ret['result'] = True
    else:
        ret['comment'] = cmd_ret.get('stderr')
    return ret


def set_osd_flag(name, flag):
    ret = {'name': name, 'changes': {}, 'comment': '', 'result': False}
    cmd_ret = __salt__['cmd.run_all'](
                       "ceph osd set {}".format(flag))
    if cmd_ret['retcode'] == 0:
        ret['result'] = True
    else:
        ret['comment'] = cmd_ret.get('stderr')
    return ret
