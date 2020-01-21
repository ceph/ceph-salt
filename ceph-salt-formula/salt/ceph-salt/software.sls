install iputils:
  pkg.installed:
    - pkgs:
      - iputils

{% if pillar['ceph-salt'].get('upgrades', {'enabled': False})['enabled'] %}

upgrade packages:
  module.run:
    - name: pkg.upgrade

{% else %}

upgrades disabled:
  test.nop

{% endif %}
