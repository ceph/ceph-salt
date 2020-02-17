{% import 'macros.yml' as macros %}

{{ macros.begin_stage('Ceph tools') }}

{{ macros.begin_step('Install cephadm and other packages') }}

install cephadm:
  pkg.installed:
    - pkgs:
        - cephadm
{% if 'mon' in grains['ceph-salt']['roles'] %}
        - ceph-common
    - failhard: True
{% endif %}

{{ macros.end_step('Install cephadm and other packages') }}

{{ macros.begin_step('Download ceph container image') }}
{% if 'container' in pillar['ceph-salt'] and 'ceph' in pillar['ceph-salt']['container']['images'] %}
download ceph container image:
  cmd.run:
    - name: |
        podman pull {{ pillar['ceph-salt']['container']['images']['ceph'] }}
    - failhard: True
{% endif %}
{{ macros.end_step('Download ceph container image') }}

{{ macros.end_stage('Ceph tools') }}
