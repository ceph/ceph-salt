# -*- encoding: utf-8 -*-
import json
import socket

def get_remote_grain(host, grain):
    """
    Reads remote host grain by accessing '/etc/salt/grains' file directly.
    """
    ssh_user = __pillar__['ceph-salt']['ssh']['user']
    sudo = 'sudo ' if ssh_user != 'root' else ''
    ret = __salt__['cmd.run_all']("ssh -o StrictHostKeyChecking=no "
                                  "-i /tmp/ceph-salt-ssh-id_rsa {}@{} "
                                  "\"{}python3 - <<EOF\n"
                                  "import json\n"
                                  "import salt.utils.data\n"
                                  "import yaml\n"
                                  "with open('/etc/salt/grains') as grains_file:\n"
                                  "    grains = yaml.full_load(grains_file)\n"
                                  "val = salt.utils.data.traverse_dict_and_list(grains, '{}')\n"
                                  "print(json.dumps({{'local': val}}))\n"
                                  "EOF\"".format(ssh_user, host, sudo, grain))
    if ret['retcode'] != 0:
        return None
    return json.loads(ret['stdout'])['local']

def set_remote_grain(host, grain, value):
    ssh_user = __pillar__['ceph-salt']['ssh']['user']
    sudo = 'sudo ' if ssh_user != 'root' else ''
    return __salt__['cmd.run_all']("ssh -o StrictHostKeyChecking=no "
                                   "-i /tmp/ceph-salt-ssh-id_rsa {}@{} "
                                   "'{}salt-call grains.set {} {}'".format(ssh_user, host, sudo,
                                                                           grain, value))

def probe_ntp(ahost):
    import ntplib
    conn = ntplib.NTPClient()
    success = False
    try:
        conn.request(ahost, version=3)
        return 0
    except socket.gaierror:
        return 2
    except ntplib.NTPException:
        return 1
    except:
        return 3
