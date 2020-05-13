{% import 'macros.yml' as macros %}

{{ macros.begin_stage('Install and update required packages') }}

install required packages:
  pkg.installed:
    - pkgs:
      - iputils
      - lsof
      - podman
    - failhard: True

{% if pillar['ceph-salt']['updates']['enabled'] %}

{{ macros.begin_step('Update all packages') }}

update packages:
  module.run:
    - name: pkg.upgrade
    - failhard: True

{{ macros.end_step('Update all packages') }}

{% else %}

updates disabled:
  test.nop

{% endif %}

{{ macros.end_stage('Install and update required packages') }}

{% if pillar['ceph-salt']['updates']['reboot'] %}

reboot:
   ceph_salt.reboot_if_needed:
     - failhard: True

{% endif %}
