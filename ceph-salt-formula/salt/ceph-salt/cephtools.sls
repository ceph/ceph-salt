{% import 'macros.yml' as macros %}

{{ macros.begin_stage('Ceph tools') }}

{{ macros.begin_step('Install cephadm and other packages') }}

install cephadm:
  pkg.installed:
    - pkgs:
        - cephadm
{% if 'admin' in grains['ceph-salt']['roles'] %}
        - ceph-common
    - failhard: True
{% endif %}

{% if grains['id'] == pillar['ceph-salt']['bootstrap_minion'] %}
/var/log/ceph:
  file.directory:
    - user: ceph
    - group: ceph
    - mode: '0770'
    - makedirs: True
    - failhard: True
{% endif %}

{{ macros.end_step('Install cephadm and other packages') }}

{{ macros.begin_step('Download ceph container image') }}
download ceph container image:
  cmd.run:
    - name: |
        cephadm --image {{ pillar['ceph-salt']['container']['images']['ceph'] }} pull
    - failhard: True
{{ macros.end_step('Download ceph container image') }}

{{ macros.end_stage('Ceph tools') }}
