{% import 'macros.yml' as macros %}

{% if 'cephadm' in grains['ceph-salt']['roles'] %}

{% set my_hostname = salt['ceph_salt.hostname']() %}

{{ macros.begin_stage('Add host to ceph orchestrator') }}
add host to ceph orch:
  ceph_orch.add_host:
    - host: {{ my_hostname }}
    - failhard: True
{{ macros.end_stage('Add host to ceph orchestrator') }}

{% endif %}
