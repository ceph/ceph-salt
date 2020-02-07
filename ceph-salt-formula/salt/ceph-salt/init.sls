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
{% if pillar['ceph-salt'].get('deploy', {'mon': False}).get('mon', False) %}
    - .ceph-mon
{% endif %}
{% if pillar['ceph-salt'].get('deploy', {'mgr': False}).get('mgr', False) %}
    - .ceph-mgr
{% endif %}
{% if pillar['ceph-salt'].get('deploy', {'osd': False}).get('osd', False) %}
    - .ceph-osd
{% endif %}
{% endif %}
{% endif %}

{% else %}

nothing to do in this node:
  test.nop

{% endif %}
