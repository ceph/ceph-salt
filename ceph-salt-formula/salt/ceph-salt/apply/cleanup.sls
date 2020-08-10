remove ceph-salt-ssh-id_rsa:
  file.absent:
    - name: /tmp/ceph-salt-ssh-id_rsa
    - failhard: True

remove ceph-salt-ssh-id_rsa.pub:
  file.absent:
    - name: /tmp/ceph-salt-ssh-id_rsa.pub
    - failhard: True

remove ceph-salt-registry-json:
  file.absent:
    - name: /tmp/ceph-salt-registry-json
    - failhard: True
