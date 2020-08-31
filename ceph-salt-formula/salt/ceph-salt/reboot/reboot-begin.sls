reset rebooted:
  grains.present:
    - name: ceph-salt:execution:rebooted
    - value: False

reset failure:
  grains.present:
    - name: ceph-salt:execution:failed
    - value: False
