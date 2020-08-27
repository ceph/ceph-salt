reset updated:
  grains.present:
    - name: ceph-salt:execution:updated
    - value: False

reset failure:
  grains.present:
    - name: ceph-salt:execution:failed
    - value: False
