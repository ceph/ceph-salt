{% import 'macros.yml' as macros %}

{% if 'admin' in grains['ceph-salt']['roles'] %}

{{ macros.begin_stage('Ensure ceph.conf and keyring are present') }}
copy ceph.conf and keyring from an admin node:
  ceph_orch.copy_ceph_conf_and_keyring:
    - failhard: True
{{ macros.end_stage('Ensure ceph.conf and keyring are present') }}

{% endif %}
