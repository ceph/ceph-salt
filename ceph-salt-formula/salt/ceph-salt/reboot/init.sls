{% if 'ceph-salt' in grains and grains['ceph-salt']['member'] %}

include:
    - ..reset
    - ..common.sshkey
    - .reboot
    - .reboot-end

{% else %}

nothing to do in this node:
  test.nop

{% endif %}
