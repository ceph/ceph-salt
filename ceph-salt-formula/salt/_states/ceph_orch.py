# -*- encoding: utf-8 -*-
import json
import time


def wait_for_admin_host(name, timeout=1800):
    ret = {'name': name, 'changes': {}, 'comment': '', 'result': False}
    starttime = time.time()
    timelimit = starttime + timeout
    configured_admin_host = None
    while not configured_admin_host:
        is_timedout = time.time() > timelimit
        if is_timedout:
            ret['comment'] = 'Timeout value reached.'
            return ret
        time.sleep(5)
        admin_hosts = __pillar__['ceph-salt']['minions']['admin']
        for admin_host in admin_hosts:
            provisioned = __salt__['ceph_salt.get_remote_grain'](admin_host,
                                                                'ceph-salt:execution:provisioned')
            if provisioned:
                configured_ret = __salt__['cmd.run_all']("ssh -o StrictHostKeyChecking=no "
                                                        "-i /tmp/ceph-salt-ssh-id_rsa root@{} "
                                                        "'salt-call ceph_orch.configured "
                                                        "--out=json --out-indent=-1'".format(
                                                            admin_host))
                if configured_ret['retcode'] == 0:
                    configured = json.loads(configured_ret['stdout'])['local']
                    if configured:
                        configured_admin_host = admin_host
                        break
    __salt__['grains.set']('ceph-salt:execution:admin_host', configured_admin_host)
    ret['result'] = True
    return ret


def add_host(name, host):
    ret = {'name': name, 'changes': {}, 'comment': '', 'result': False}
    admin_host = __salt__['grains.get']('ceph-salt:execution:admin_host')
    cmd_ret = __salt__['cmd.run_all']("ssh -o StrictHostKeyChecking=no "
                                      "-i /tmp/ceph-salt-ssh-id_rsa root@{} "
                                      "'cephadm shell -- ceph orch host add {}'".format(
                                          admin_host, host))
    if cmd_ret['retcode'] == 0:
        ret['result'] = True
    return ret


def copy_ceph_conf_and_keyring(name):
    ret = {'name': name, 'changes': {}, 'comment': '', 'result': False}
    admin_host = __salt__['grains.get']('ceph-salt:execution:admin_host')
    cmd_ret = __salt__['cmd.run_all']("scp -o StrictHostKeyChecking=no "
                                      "-i /tmp/ceph-salt-ssh-id_rsa "
                                      "root@{}:/etc/ceph/{{ceph.conf,ceph.client.admin.keyring}} "
                                      "/etc/ceph/".format(admin_host))
    if cmd_ret['retcode'] == 0:
        ret['result'] = True
    return ret
