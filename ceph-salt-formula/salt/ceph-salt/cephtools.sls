{% import 'macros.yml' as macros %}

{{ macros.begin_stage('Prepare to bootstrap the Ceph cluster') }}

{{ macros.begin_step('Install cephadm and other packages') }}

install cephadm:
  pkg.installed:
    - pkgs:
        - cephadm
{% if 'admin' in grains['ceph-salt']['roles'] %}
        - ceph-common
{% endif %}
    - failhard: True

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

{{ macros.begin_step('Run "cephadm check-host"') }}

have cephadm check the host:
  cmd.run:
    - name: |
        cephadm check-host
    - failhard: True

{{ macros.end_step('Run "cephadm check-host"') }}

{% set image = pillar['ceph-salt']['container']['images']['ceph'] %}

{{ macros.begin_step('Download ceph container image') }}
download ceph container image:
  cmd.run:
    - name: |
        cephadm --image {{ image }} pull
    - unless: podman image exists {{ image }}
    - failhard: True
{{ macros.end_step('Download ceph container image') }}

{{ macros.end_stage('Prepare to bootstrap the Ceph cluster') }}
