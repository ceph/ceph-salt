{% import 'macros.yml' as macros %}

{% if 'admin' in grains['ceph-salt']['roles'] %}

{{ macros.begin_stage('Ensure cephadm MGR module is configured') }}

{% set auth = pillar['ceph-salt'].get('container', {}).get('auth', {}) %}

configure cephadm mgr module:
  cmd.run:
    - name: |
        ceph cephadm set-priv-key -i /home/cephadm/.ssh/id_rsa
        ceph cephadm set-pub-key -i /home/cephadm/.ssh/id_rsa.pub
        ceph cephadm set-user cephadm
{%- if auth %}
        ceph cephadm registry-login -i /tmp/ceph-salt-registry-json
{%- endif %}
        ceph config set mgr mgr/cephadm/manage_etc_ceph_ceph_conf true
        ceph config set mgr mgr/cephadm/use_repo_digest true --force
        ceph config set mgr mgr/cephadm/container_init true
    - failhard: True

{{ macros.end_stage('Ensure cephadm MGR module is configured') }}

{% endif %}
