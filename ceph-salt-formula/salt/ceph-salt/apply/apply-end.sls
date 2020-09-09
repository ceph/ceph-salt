include:
    - ..common.sshkey-cleanup

remove ceph-salt-registry-json:
  file.absent:
    - name: /tmp/ceph-salt-registry-json
    - failhard: True
