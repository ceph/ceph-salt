# -*- encoding: utf-8 -*-
import json
import ntplib
import socket
import time

def get_remote_grain(host, grain):
    """
    Reads remote host grain by accessing '/etc/salt/grains' file directly.
    """
    ret = __salt__['cmd.run_all']("ssh -o StrictHostKeyChecking=no "
                                  "-i /tmp/ceph-salt-ssh-id_rsa root@{} "
                                  "\"python3 - <<EOF\n"
                                  "import json\n"
                                  "import salt.utils.data\n"
                                  "import yaml\n"
                                  "with open('/etc/salt/grains') as grains_file:\n"
                                  "    grains = yaml.full_load(grains_file)\n"
                                  "val = salt.utils.data.traverse_dict_and_list(grains, '{}')\n"
                                  "print(json.dumps({{'local': val}}))\n"
                                  "EOF\"".format(host, grain))
    if ret['retcode'] != 0:
        return None
    return json.loads(ret['stdout'])['local']

def set_remote_grain(host, grain, value):
    return __salt__['cmd.run_all']("ssh -o StrictHostKeyChecking=no "
                                   "-i /tmp/ceph-salt-ssh-id_rsa root@{} "
                                   "'salt-call grains.set {} {}'".format(host, grain, value))

def probe_ntp(ahost, log_handler):
    conn = None
    max_attempts = 10
    for attempt in range(1, max_attempts + 1):
        log_handler(
            "Probing NTP server %s (attempt %s of %s)",
            str(ahost),
            str(attempt),
            str(max_attempts)
        )
        success = False
        conn = ntplib.NTPClient()
        try:
            conn.request(ahost, version=3)
            success = True
        except socket.gaierror:
            success = False
            break  # fail immediately: hostname is not resolvable
        except ntplib.NTPException:
            success = False
        if success:
            break
        else:
            # Failed to set up NTP connection, but that doesn't necessarily
            # mean the NTP server is not valid. Keep trying.
            time.sleep(3)
            continue
    return success
