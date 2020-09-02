set rebooted:
  grains.present:
    - name: ceph-salt:execution:rebooted
    - value: True

{% if 'admin' not in grains['ceph-salt']['roles'] %}

remove ceph-salt-ssh-id_rsa:
  file.absent:
    - name: /home/cephadm/.ssh/id_rsa
    - failhard: True

remove ceph-salt-ssh-id_rsa.pub:
  file.absent:
    - name: /home/cephadm/.ssh/id_rsa.pub
    - failhard: True

{% endif %}
