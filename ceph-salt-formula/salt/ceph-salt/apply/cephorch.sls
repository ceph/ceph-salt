{% import 'macros.yml' as macros %}

{% if 'cephadm' in grains['ceph-salt']['roles'] %}

{{ macros.begin_stage('Add host to ceph orchestrator') }}
add host to ceph orch:
  ceph_orch.add_host:
    - host: {{ grains['fqdn'] }}
    - failhard: True
{{ macros.end_stage('Add host to ceph orchestrator') }}

{% endif %}
