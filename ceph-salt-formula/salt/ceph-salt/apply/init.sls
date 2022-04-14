{% if grains['id'] in pillar['ceph-salt']['minions']['all'] %}

include:
    - ..common.install-cephadm
    - ..reset
    - ..common.sshkey
    - .sysctl
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
