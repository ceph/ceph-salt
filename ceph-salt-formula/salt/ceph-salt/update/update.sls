{% import 'macros.yml' as macros %}

{{ macros.begin_stage('Update all packages') }}

install required packages:
  pkg.installed:
    - pkgs:
      - lsof
    - failhard: True

update packages:
  module.run:
    - name: pkg.upgrade
    - failhard: True

# in case any package update re-writes sudoers /etc/sudoers.d/<ssh_user>
{{ macros.sudoers('configure sudoers after package update') }}

{{ macros.end_stage('Update all packages') }}

{% if pillar['ceph-salt']['updates']['reboot'] %}

{{ macros.begin_stage('Find an admin host') }}
wait for admin host:
  ceph_orch.set_admin_host:
    - failhard: True
{{ macros.end_stage('Find an admin host') }}

{{ macros.begin_stage('Check if reboot is needed') }}
check if reboot is needed:
  ceph_salt.set_reboot_needed:
    - failhard: True
{{ macros.end_stage('Check if reboot is needed') }}

wait for ancestor minion:
  ceph_salt.wait_for_ancestor_minion_grain:
    - grain: ceph-salt:execution:updated
    - if_grain: ceph-salt:execution:reboot_needed
    - failhard: True

wait for ceph orch ok-to-stop:
  ceph_orch.wait_for_ceph_orch_host_ok_to_stop:
    - if_grain: ceph-salt:execution:reboot_needed
    - failhard: True

reboot:
   ceph_salt.reboot_if_needed:
     - ignore_running_services: True
     - failhard: True

{% else %}

skip reboot:
  test.nop

{% endif %}
