# -*- encoding: utf-8 -*-
import json
import logging
import time


logger = logging.getLogger(__name__)


def set_admin_host(name, timeout=1800):
    ret = {'name': name, 'changes': {}, 'comment': '', 'result': False}
    starttime = time.time()
    timelimit = starttime + timeout
    configured_admin_host = None
    while not configured_admin_host:
        is_timedout = time.time() > timelimit
        if is_timedout:
            ret['comment'] = 'Timeout value reached.'
            return ret
        time.sleep(15)
        admin_hosts = __pillar__['ceph-salt']['minions']['admin']
        for admin_host in admin_hosts:
            failed = __salt__['ceph_salt.get_remote_grain'](admin_host, 'ceph-salt:execution:failed')
            if failed:
                ret['comment'] = 'One or more admin minions failed.'
                return ret
            provisioned = __salt__['ceph_salt.get_remote_grain'](admin_host,
                                                                'ceph-salt:execution:provisioned')
            if provisioned:
                ssh_user = __pillar__['ceph-salt']['ssh']['user']
                sudo = 'sudo ' if ssh_user != 'root' else ''
                status_ret = __salt__['cmd.run_all']("ssh -o StrictHostKeyChecking=no "
                                                     "-i /tmp/ceph-salt-ssh-id_rsa {}@{} "
                                                     "'if [[ -f /etc/ceph/ceph.conf "
                                                     "&& -f /etc/ceph/ceph.client.admin.keyring ]]; "
                                                     "then timeout 60 {}ceph -s; "
                                                     "else (exit 1); fi'".format(
                                                         ssh_user,
                                                         admin_host,
                                                         sudo))
                if status_ret['retcode'] == 0:
                    configured_admin_host = admin_host
                    break

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
        ssh_user = __pillar__['ceph-salt']['ssh']['user']
        sudo = 'sudo ' if ssh_user != 'root' else ''
        status_ret = __salt__['cmd.run_all']("ssh -o StrictHostKeyChecking=no "
                                             "-i /tmp/ceph-salt-ssh-id_rsa {}@{} "
                                             "'if [[ -f /etc/ceph/ceph.conf "
                                             "&& -f /etc/ceph/ceph.client.admin.keyring ]]; "
                                             "then timeout 60 {}ceph orch status --format=json; "
                                             "else (exit 1); fi'".format(
                                                 ssh_user,
                                                 admin_host,
                                                 sudo))
        if status_ret['retcode'] == 0:
            status = json.loads(status_ret['stdout'])
            if status.get('available'):
                break
    ret['result'] = True
    return ret

def add_host(name, host):
    """
    Requires the following grains to be set:
      - ceph-salt:execution:admin_host
    """
    ret = {'name': name, 'changes': {}, 'comment': '', 'result': False}
    admin_host = __salt__['grains.get']('ceph-salt:execution:admin_host')
    ssh_user = __pillar__['ceph-salt']['ssh']['user']
    sudo = 'sudo ' if ssh_user != 'root' else ''
    cmd_ret = __salt__['cmd.run_all']("ssh -o StrictHostKeyChecking=no "
                                      "-i /tmp/ceph-salt-ssh-id_rsa {}@{} "
                                      "'{}ceph orch host add {}'".format(ssh_user, admin_host,
                                                                       sudo, host))
    if cmd_ret['retcode'] == 0:
        ret['result'] = True
    return ret


def rm_clusters(name):
    """
    Requires the following pillar to be set:
      - ceph-salt:execution:fsid
    """
    ret = {'name': name, 'changes': {}, 'comment': '', 'result': False}
    fsid = __salt__['pillar.get']('ceph-salt:execution:fsid')
    if not fsid:
        ret['comment'] = "No cluster FSID provided. Ceph cluster FSID " \
                         "must be provided via custom Pillar value, e.g.: " \
                         "\"salt -G ceph-salt:member state.apply ceph-salt.purge " \
                         "pillar='{\"ceph-salt\": {\"execution\": {\"fsid\": \"$FSID\"}}}'\""
        return ret
    __salt__['ceph_salt.begin_stage']("Remove cluster {}".format(fsid))
    cmd_ret = __salt__['cmd.run_all']("cephadm rm-cluster --fsid {} "
                                      "--force".format(fsid))
    if cmd_ret['retcode'] == 0:
        __salt__['ceph_salt.end_stage']("Remove cluster {}".format(fsid))
        ret['result'] = True
    return ret


def copy_ceph_conf_and_keyring(name):
    """
    Requires the following grains to be set:
      - ceph-salt:execution:admin_host
    """
    ret = {'name': name, 'changes': {}, 'comment': '', 'result': False}
    admin_host = __salt__['grains.get']('ceph-salt:execution:admin_host')
    ssh_user = __pillar__['ceph-salt']['ssh']['user']
    sudo = 'sudo ' if ssh_user != 'root' else ''
    cmd_ret = __salt__['cmd.run_all']("{0}rsync --rsync-path='{0}rsync' "
                                      "-e 'ssh -o StrictHostKeyChecking=no "
                                      "-i /tmp/ceph-salt-ssh-id_rsa' "
                                      "{1}@{2}:/etc/ceph/{{ceph.conf,ceph.client.admin.keyring}} "
                                      "/etc/ceph/".format(sudo, ssh_user, admin_host))
    if cmd_ret['retcode'] == 0:
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
            ssh_user = __pillar__['ceph-salt']['ssh']['user']
            sudo = 'sudo ' if ssh_user != 'root' else ''
            cmd_ret = __salt__['cmd.run_all']("ssh -o StrictHostKeyChecking=no "
                                              "-i /tmp/ceph-salt-ssh-id_rsa {}@{} "
                                              "'{}ceph orch host ok-to-stop {}'".format(ssh_user, admin_host,
                                                                                        sudo, host))
            ok_to_stop = cmd_ret['retcode'] == 0
            if not ok_to_stop:
                logger.info("Waiting for 'ceph_orch.host_ok_to_stop'")
                time.sleep(15)
        __salt__['event.send']('ceph-salt/stage/end',
                               data={'desc': "Wait for 'ceph orch host ok-to-stop {}'".format(host)})
    ret['result'] = True
    return ret
