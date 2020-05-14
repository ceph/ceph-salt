# -*- encoding: utf-8 -*-
import json

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
