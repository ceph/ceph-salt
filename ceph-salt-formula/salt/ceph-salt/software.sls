{% import 'macros.yml' as macros %}

{{ macros.begin_stage('Install and update required packages') }}

install iputils:
  pkg.installed:
    - pkgs:
      - iputils
    - failhard: True

{% if pillar['ceph-salt'].get('upgrades', {'enabled': False})['enabled'] %}

{{ macros.begin_step('Upgrading all packages') }}

upgrade packages:
  module.run:
    - name: pkg.upgrade
    - failhard: True

{{ macros.end_step('Upgrading all packages') }}

{% else %}

upgrades disabled:
  test.nop

{% endif %}

{{ macros.end_stage('Install and update required packages') }}
