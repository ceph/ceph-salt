set provisioned:
  grains.present:
    - name: ceph-salt:execution:provisioned
    - value: True
