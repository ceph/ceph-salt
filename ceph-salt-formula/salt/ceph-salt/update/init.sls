{% if grains['id'] in pillar['ceph-salt']['minions']['all'] %}

include:
    - ..common.install-cephadm
    - ..reset
    - .update
    - ..common.sshkey
    - .update-end

{% else %}

nothing to do in this node:
  test.nop

{% endif %}
