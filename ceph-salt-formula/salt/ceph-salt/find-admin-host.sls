{% import 'macros.yml' as macros %}

{% if 'cephadm' in grains['ceph-salt']['roles'] %}

{{ macros.begin_stage('Wait for an admin host') }}
wait for admin host:
  ceph_orch.wait_for_admin_host:
    - failhard: True
{{ macros.end_stage('Wait for an admin host') }}

{% endif %}
