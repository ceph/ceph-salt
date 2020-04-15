{% import 'macros.yml' as macros %}

{{ macros.begin_stage('Wait for an admin host') }}
wait for admin host:
  ceph_orch.wait_for_admin_host:
    - failhard: True
{{ macros.end_stage('Wait for an admin host') }}
