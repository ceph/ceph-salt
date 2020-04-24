# -*- encoding: utf-8 -*-
import json

def configured():
    ret = __salt__['cmd.run_all']("sh -c 'type cephadm'")
    if ret['retcode'] != 0:
        return False
    if not __salt__['file.file_exists']("/etc/ceph/ceph.conf"):
        return False
    if not __salt__['file.file_exists']("/etc/ceph/ceph.client.admin.keyring"):
        return False
    ret = __salt__['cmd.run_all']("cephadm shell -- ceph orch status")
    if ret['retcode'] != 0:
        return False
    return True

def host_ls():
    ret = __salt__['cmd.run']("cephadm shell -- ceph orch host ls --format=json")
    return json.loads(ret)
