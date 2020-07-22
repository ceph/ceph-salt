reset updated:
  grains.present:
    - name: ceph-salt:execution:updated
    - value: False

reset failure:
  grains.present:
    - name: ceph-salt:execution:failed
    - value: False

{% set ssh_user = pillar['ceph-salt']['ssh']['user'] %}
{% set ssh_user_group = 'root' if ssh_user == 'root' else 'users' %}

# private key
create ceph-salt-ssh-id_rsa:
  file.managed:
    - name: /tmp/ceph-salt-ssh-id_rsa
    - user: {{ ssh_user }}
    - group: {{ ssh_user_group }}
    - mode: '0600'
    - contents_pillar: ceph-salt:ssh:private_key
    - failhard: True

# public key
create ceph-salt-ssh-id_rsa.pub:
  file.managed:
    - name: /tmp/ceph-salt-ssh-id_rsa.pub
    - user: {{ ssh_user }}
    - group: {{ ssh_user_group }}
    - mode: '0644'
    - contents_pillar: ceph-salt:ssh:public_key
    - failhard: True
