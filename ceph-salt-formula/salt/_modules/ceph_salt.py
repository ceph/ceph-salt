# -*- encoding: utf-8 -*-
import json

def get_remote_grain(host, grain):
    ret = __salt__['cmd.run_all']("ssh -o StrictHostKeyChecking=no root@{} "
                                  "'salt-call grains.get --out=json --out-indent=-1 {}'".format(
                                      host, grain))
    if ret['retcode'] != 0:
        return None
    return json.loads(ret['stdout'])['local']

def set_remote_grain(host, grain, value):
    return __salt__['cmd.run_all']("ssh -o StrictHostKeyChecking=no root@{} "
                                  "'salt-call grains.set {} {}'".format(host, grain, value))
