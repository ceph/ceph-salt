{% import 'macros.yml' as macros %}

{% if 'cephadm' in grains['ceph-salt']['roles'] %}

{% set my_hostname = salt['ceph_salt.hostname']() %}
{% set my_ipaddr = salt['ceph_salt.ip_address']() %}
{% set is_admin = 'admin' in grains['ceph-salt']['roles'] %}

{{ macros.begin_stage('Add host to ceph orchestrator') }}
add host to ceph orch:
  ceph_orch.add_host:
    - host: {{ my_hostname }}
    - ipaddr: {{ my_ipaddr }}
    - is_admin: {{ is_admin }}
    - failhard: True
{{ macros.end_stage('Add host to ceph orchestrator') }}

{% else %}

no op:
  test.nop

{% endif %}
