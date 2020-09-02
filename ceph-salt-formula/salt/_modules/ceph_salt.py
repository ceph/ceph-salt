# -*- encoding: utf-8 -*-
import json
import socket
import time

import logging

log = logging.getLogger(__name__)


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


def get_remote_grain(host, grain):
    """
    Reads remote host grain by accessing '/etc/salt/grains' file directly.
    """
    ssh_user = __pillar__['ceph-salt']['ssh']['user']
    sudo = 'sudo ' if ssh_user != 'root' else ''
    home = '/home/{}'.format(ssh_user) if ssh_user != 'root' else '/root'    
    ret = __salt__['cmd.run_all']("ssh -o StrictHostKeyChecking=no "
                                  "-i {}/.ssh/id_rsa {}@{} "
                                  "\"{}python3 - <<EOF\n"
                                  "import json\n"
                                  "import salt.utils.data\n"
                                  "import yaml\n"
                                  "with open('/etc/salt/grains') as grains_file:\n"
                                  "    grains = yaml.full_load(grains_file)\n"
                                  "val = salt.utils.data.traverse_dict_and_list(grains, '{}')\n"
                                  "print(json.dumps({{'local': val}}))\n"
                                  "EOF\"".format(home, ssh_user, host, sudo, grain))
    if ret['retcode'] != 0:
        return None
    return json.loads(ret['stdout'])['local']


def probe_ntp(ahost):
    import ntplib
    conn = ntplib.NTPClient()
    try:
        conn.request(ahost, version=3)
        return 0
    except socket.gaierror:
        return 2
    except ntplib.NTPException:
        return 1
    except:
        return 3


def is_safety_disengaged():
    execution = __pillar__['ceph-salt'].get('execution', {})
    safety_disengage_time = execution.get('safety_disengage_time')
    if safety_disengage_time and safety_disengage_time + 60 > time.time():
        return True
    return False


def probe_dns(*hostnames):
    """
    given a list of hostnames, verify that all can be resolved to IP addresses
    """
    ret_status = True
    for hostname in hostnames:
        log_msg = "probe_dns: attempting to resolve minion hostname ->{}<-".format(hostname)
        log.info(log_msg)
        try:
            socket.gethostbyname(hostname)
        except Exception as exc:
            log.error(exc)
            ret_status = False
        if not ret_status:
            break
    return ret_status
