include:
    - ..common.sshkey-cleanup

set rebooted:
  grains.present:
    - name: ceph-salt:execution:rebooted
    - value: True
