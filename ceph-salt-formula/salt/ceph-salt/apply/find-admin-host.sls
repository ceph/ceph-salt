{% import 'macros.yml' as macros %}

{% if 'cephadm' in grains['ceph-salt']['roles'] %}

{{ macros.begin_stage('Find an admin host') }}
wait for admin host:
  ceph_orch.set_admin_host:
    - failhard: True
{{ macros.end_stage('Find an admin host') }}

{% endif %}
