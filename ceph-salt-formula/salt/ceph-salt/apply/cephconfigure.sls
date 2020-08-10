{% import 'macros.yml' as macros %}

{% if 'cephadm' in grains['ceph-salt']['roles'] or 'admin' in grains['ceph-salt']['roles'] %}

{{ macros.begin_stage('Find an admin host') }}

find an admin host:
  ceph_orch.set_admin_host:
    - failhard: True

{{ macros.end_stage('Find an admin host') }}

{% endif %}


{% if 'admin' in grains['ceph-salt']['roles'] %}

{{ macros.begin_stage('Ensure ceph.conf and keyring are present') }}

copy ceph.conf and keyring from an admin node:
  ceph_orch.copy_ceph_conf_and_keyring:
    - failhard: True

{{ macros.end_stage('Ensure ceph.conf and keyring are present') }}

{% set admin_minion = pillar['ceph-salt'].get('bootstrap_minion', pillar['ceph-salt']['minions']['admin'][0]) %}

{% if grains['id'] == admin_minion %}

{{ macros.begin_stage('Ensure cephadm MGR module is enabled') }}

{% set ssh_user = pillar['ceph-salt']['ssh']['user'] %}

enable cephadm mgr module:
  cmd.run:
    - name: |
        ceph config-key set mgr/cephadm/ssh_identity_key -i /tmp/ceph-salt-ssh-id_rsa
        ceph config-key set mgr/cephadm/ssh_identity_pub -i /tmp/ceph-salt-ssh-id_rsa.pub
        ceph config-key set mgr/cephadm/ssh_user {{ ssh_user }}
        ceph mgr module enable cephadm && \
        ceph orch set backend cephadm
    - failhard: True

{{ macros.end_stage('Ensure cephadm MGR module is enabled') }}

{% endif %}

{% endif %}

{% if 'cephadm' in grains['ceph-salt']['roles'] or 'admin' in grains['ceph-salt']['roles'] %}

{{ macros.begin_stage('Wait until ceph orch is available') }}

wait for ceph orch available:
  ceph_orch.wait_until_ceph_orch_available:
    - failhard: True

{{ macros.end_stage('Wait until ceph orch is available') }}

{% endif %}