{% import 'macros.yml' as macros %}

{% if 'admin' in grains['ceph-salt']['roles'] %}

{{ macros.begin_stage('Ensure cephadm MGR module is configured') }}

{% set ssh_user = pillar['ceph-salt']['ssh']['user'] %}

configure cephadm mgr module:
  cmd.run:
    - name: |
        ceph cephadm set-priv-key -i /tmp/ceph-salt-ssh-id_rsa
        ceph cephadm set-pub-key -i /tmp/ceph-salt-ssh-id_rsa.pub
        ceph cephadm set-user {{ ssh_user }}
    - failhard: True

{{ macros.end_stage('Ensure cephadm MGR module is configured') }}

{% endif %}
