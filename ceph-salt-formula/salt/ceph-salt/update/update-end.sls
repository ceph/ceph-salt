set updated:
  grains.present:
    - name: ceph-salt:execution:updated
    - value: True

{% if 'admin' not in grains['ceph-salt']['roles'] %}

{% set ssh_user = pillar['ceph-salt']['ssh']['user'] %}
{% set home = '/home/' ~ssh_user if ssh_user != 'root' else '/root' %}

remove ceph-salt-ssh-id_rsa:
  file.absent:
    - name: {{ home }}/.ssh/id_rsa
    - failhard: True

remove ceph-salt-ssh-id_rsa.pub:
  file.absent:
    - name: {{ home }}/.ssh/id_rsa.pub
    - failhard: True

{% endif %}
