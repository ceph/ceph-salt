{% if 'ceph-salt' in grains and grains['ceph-salt']['member'] %}

include:
    - .provision-begin
    - .sshkey
    - .software
    - .container
    - .apparmor
    - .time
    - .cephtools
    - .provision-end
    - .cephbootstrap
    - .find-admin-host
    - .cephorch
    - .ceph-admin
    - .cleanup

{% else %}

nothing to do in this node:
  test.nop

{% endif %}
