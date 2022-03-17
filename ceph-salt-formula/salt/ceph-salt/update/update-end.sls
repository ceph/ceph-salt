include:
    - ..common.sshkey-cleanup
    - ..common.orch-host-label

set updated:
  grains.present:
    - name: ceph-salt:execution:updated
    - value: True
