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

def ceph_configured():
    if not __salt__['file.file_exists']("/etc/ceph/ceph.conf"):
        return False
    if not __salt__['file.file_exists']("/etc/ceph/ceph.client.admin.keyring"):
        return False
    status_ret = __salt__['cmd.run_all']("ceph -s")
    return status_ret['retcode'] == 0

def host_ls():
    ret = __salt__['cmd.run']("ceph orch host ls --format=json")
    return json.loads(ret)

def fsid():
    ret = __salt__['cmd.run_all']("ceph -s --format=json")
    if ret['retcode'] == 0:
        status = json.loads(ret['stdout'])
        return status.get('fsid', None)
    return None
