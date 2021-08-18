{% import 'macros.yml' as macros %}

{% if 'cephadm' in grains['ceph-salt']['roles'] %}

{% set my_hostname = salt['ceph_salt.hostname']() %}
{% set is_admin = 'admin' in grains['ceph-salt']['roles'] %}

{{ macros.begin_stage('Add host to ceph orchestrator') }}
add host to ceph orch:
  ceph_orch.add_host:
    - host: {{ my_hostname }}
    - is_admin: {{ is_admin }}
    - failhard: True
{{ macros.end_stage('Add host to ceph orchestrator') }}

{% else %}

no op:
  test.nop

{% endif %}
