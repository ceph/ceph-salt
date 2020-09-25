include:
    - ..common.sshkey-cleanup

set stopped:
  grains.present:
    - name: ceph-salt:execution:stopped
    - value: True
