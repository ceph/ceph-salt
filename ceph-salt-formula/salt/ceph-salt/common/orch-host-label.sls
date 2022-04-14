{% import 'macros.yml' as macros %}

{% set my_hostname = salt['ceph_salt.hostname']() %}

{% if 'admin' in grains['ceph-salt']['roles'] %}

{% if pillar['ceph-salt'].get ('execution', {}).get('deployed') != False %}
{{ macros.begin_stage('Add host labels to ceph orchestrator') }}
add _admin host label to ceph orch:
  ceph_orch.add_host_label:
    - host: {{ my_hostname }}
    - label: {{ '_admin' }}
    - failhard: True
{{ macros.end_stage('Add host labels to ceph orchestrator') }}
{% endif %}

{% else %}

not an admin role:
  test.nop

{% endif %}
