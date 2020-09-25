{% if 'ceph-salt' in grains and grains['ceph-salt']['member'] %}

include:
    - ..reset
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
    - .cephbootstrap
    - .cephconfigure
    - .cephorch
    - .ceph-admin
    - .apply-end

{% else %}

nothing to do in this node:
  test.nop

{% endif %}
