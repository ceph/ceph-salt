{% import 'macros.yml' as macros %}

check fsid:
   ceph_salt.check_fsid:
     - formula: ceph-salt.stop
     - failhard: True

# first admin minion is the one who will stop services
{% set admin_minion = pillar['ceph-salt']['minions']['admin'][0] %}

{% if grains['id'] == admin_minion %}

{{ macros.begin_stage('Ensure noout OSD flag is set') }}
set noout osd flag:
  ceph_orch.set_osd_flag:
    - flag: noout
    - failhard: True
{{ macros.end_stage('Ensure noout OSD flag is set') }}

{{ macros.begin_stage('Stop ceph services') }}

{% for service in ['nfs', 'iscsi', 'rgw', 'mds', 'prometheus', 'grafana', 'node-exporter', 'alertmanager', 'rbd-mirror', 'crash', 'osd'] %}

{{ macros.begin_step("Stop '" ~ service ~ "'") }}
stop {{ service }}:
  ceph_orch.stop_service:
    - service: {{ service }}
    - failhard: True

wait {{ service }} stopped:
  ceph_orch.wait_until_service_stopped:
    - service: {{ service }}
    - failhard: True
{{ macros.end_step("Stop '" ~ service ~ "'") }}

{% endfor %}

{{ macros.end_stage('Stop ceph services') }}

{% else %}

{{ macros.begin_stage('Wait until ' ~ admin_minion ~ ' stops all ceph services') }}
wait for admin stopped:
  ceph_salt.wait_for_grain:
    - grain: ceph-salt:execution:stopped
    - hosts: [ {{ admin_minion }} ]
    - failhard: True
{{ macros.end_stage('Wait until ' ~ admin_minion ~ ' stops all ceph services') }}

{% endif %}

# Stop remaining services (mgr, mon)
stop cluster:
   ceph_orch.stop_ceph_fsid:
     - failhard: True
