{% if grains['id'] in pillar['ceph-salt']['minions']['all'] %}

include:
    - ..reset
    - ..common.sshkey
    - .stop
    - .stop-end

{% else %}

nothing to do in this node:
  test.nop

{% endif %}
