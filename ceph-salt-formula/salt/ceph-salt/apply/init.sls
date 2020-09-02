{% if 'ceph-salt' in grains and grains['ceph-salt']['member'] %}

include:
    - .provision-begin
    - ..common.sshkey
    - .tuned-off
    - .tuned-latency
    - .tuned-throughput
    - .software
    - .container
    - .apparmor
    - .time-prep
    - .time-sync
    - .cephtools
    - .provision-end
    - .cephbootstrap
    - .cephconfigure
    - .cephorch
    - .ceph-admin
    - .cleanup

{% else %}

nothing to do in this node:
  test.nop

{% endif %}
