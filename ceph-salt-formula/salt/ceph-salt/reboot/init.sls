{% if 'ceph-salt' in grains and grains['ceph-salt']['member'] %}

include:
    - .reboot-begin
    - ..common.sshkey
    - .reboot
    - .reboot-end

{% else %}

nothing to do in this node:
  test.nop

{% endif %}
