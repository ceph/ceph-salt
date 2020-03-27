{% if 'ceph-salt' in grains and grains['ceph-salt']['member'] %}

include:
    - .provision-begin
    - .sshkey
    - .software
    - .apparmor
    - .time
    - .cephtools
    - .provision-end
{% if pillar['ceph-salt'].get('deploy', {'bootstrap': True}).get('bootstrap', True) %}
    - .cephbootstrap
{% if grains['id'] == pillar['ceph-salt']['bootstrap_minion'] %}
    - .ceph-admin
{% endif %}
{% endif %}

{% else %}

nothing to do in this node:
  test.nop

{% endif %}
