{% import 'macros.yml' as macros %}

{{ macros.begin_stage('Add host to ceph orchestrator') }}
add host to ceph orch:
  ceph_orch.add_host:
    - host: {{ grains['host'] }}
    - failhard: True
{{ macros.end_stage('Add host to ceph orchestrator') }}
