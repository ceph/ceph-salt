{% import 'macros.yml' as macros %}

{% if 'admin' in grains['ceph-salt']['roles'] %}

{{ macros.begin_stage('Ensure keyring is present') }}
copy keyring from an admin node:
  ceph_orch.copy_keyring:
    - failhard: True
{{ macros.end_stage('Ensure keyring is present') }}

{% endif %}
