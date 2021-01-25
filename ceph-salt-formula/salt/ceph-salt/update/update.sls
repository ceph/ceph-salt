{% import 'macros.yml' as macros %}

{{ macros.begin_stage('Update all packages') }}

lsof sanity:
  file.exists:
    - name: /usr/bin/lsof
    - failhard: True

update packages:
  module.run:
    - name: pkg.upgrade
    - failhard: True

{{ macros.end_stage('Update all packages') }}

{% if pillar['ceph-salt'].get('execution', {}).get('reboot-if-needed', False) %}

{{ macros.begin_stage('Check if reboot is needed') }}
check if reboot is needed:
  ceph_salt.set_reboot_needed:
    - failhard: True
{{ macros.end_stage('Check if reboot is needed') }}

# if ceph cluster already exists, then minions are rebooted sequentially (orchestrated reboot)
# otherwise minions are rebooted in parallel
{% if pillar['ceph-salt'].get('execution', {}).get('deployed') != False %}

wait for admin host:
  ceph_orch.set_admin_host:
    - if_grain: ceph-salt:execution:reboot_needed
    - failhard: True

wait for ancestor minion:
  ceph_salt.wait_for_ancestor_minion_grain:
    - grain: ceph-salt:execution:updated
    - if_grain: ceph-salt:execution:reboot_needed
    - failhard: True

wait for ceph orch ok-to-stop:
  ceph_orch.wait_for_ceph_orch_host_ok_to_stop:
    - if_grain: ceph-salt:execution:reboot_needed
    - failhard: True

{% endif %}

reboot:
   ceph_salt.reboot_if_needed:
     - failhard: True

{% else %}

skip reboot:
  test.nop

{% endif %}
