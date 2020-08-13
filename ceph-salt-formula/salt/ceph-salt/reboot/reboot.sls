{% import 'macros.yml' as macros %}

install required packages:
  pkg.installed:
    - pkgs:
      - lsof
    - failhard: True

{{ macros.begin_stage('Check if reboot is needed') }}
check if reboot is needed:
  ceph_salt.set_reboot_needed:
    - force: {{ pillar['ceph-salt'].get('force-reboot', False) }}
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
    - grain: ceph-salt:execution:rebooted
    - if_grain: ceph-salt:execution:reboot_needed
    - failhard: True

wait for ceph orch ok-to-stop:
  ceph_orch.wait_for_ceph_orch_host_ok_to_stop:
    - if_grain: ceph-salt:execution:reboot_needed
    - failhard: True

{% endif %}

reboot:
   ceph_salt.reboot_if_needed:
     - ignore_running_services: True
     - failhard: True
