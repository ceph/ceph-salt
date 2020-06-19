{% import 'macros.yml' as macros %}

{% if 'admin' in grains['ceph-salt']['roles'] %}

{{ macros.begin_stage('Ensure ceph.conf and keyring are present') }}
copy ceph.conf and keyring from an admin node:
  ceph_orch.copy_ceph_conf_and_keyring:
    - failhard: True
{{ macros.end_stage('Ensure ceph.conf and keyring are present') }}

{{ macros.begin_stage('Ensure cephadm MGR module is configured') }}

configure cephadm mgr module:
  cmd.run:
    - name: |
        ceph config-key set mgr/cephadm/ssh_identity_key -i /tmp/ceph-salt-ssh-id_rsa
        ceph config-key set mgr/cephadm/ssh_identity_pub -i /tmp/ceph-salt-ssh-id_rsa.pub
    - failhard: True

{{ macros.end_stage('Ensure cephadm MGR module is configured') }}

{% endif %}
