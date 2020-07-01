# -*- encoding: utf-8 -*-
import json

def configured():
    if not __salt__['file.file_exists']("/etc/ceph/ceph.conf"):
        return False
    if not __salt__['file.file_exists']("/etc/ceph/ceph.client.admin.keyring"):
        return False
    status_ret = __salt__['cmd.run_all']("timeout 60 ceph orch status --format=json")
    if status_ret['retcode'] != 0:
        return False
    status = json.loads(status_ret['stdout'])
    return status.get('available', False)

def host_ls():
    ret = __salt__['cmd.run']("ceph orch host ls --format=json")
    return json.loads(ret)
