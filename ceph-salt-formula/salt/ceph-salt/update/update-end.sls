include:
    - ..common.sshkey-cleanup

set updated:
  grains.present:
    - name: ceph-salt:execution:updated
    - value: True
