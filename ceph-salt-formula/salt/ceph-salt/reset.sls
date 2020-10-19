reset failure:
  grains.present:
    - name: ceph-salt:execution:failed
    - value: False

reset updated:
  grains.present:
    - name: ceph-salt:execution:updated
    - value: False

reset rebooted:
  grains.present:
    - name: ceph-salt:execution:rebooted
    - value: False

reset stopped:
  grains.present:
    - name: ceph-salt:execution:stopped
    - value: False

reset stoptimeserversyncedped:
  grains.present:
    - name: ceph-salt:execution:timeserversynced
    - value: False
