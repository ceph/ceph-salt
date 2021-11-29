{% import 'macros.yml' as macros %}

{% if 'cephadm' in grains['ceph-salt']['roles'] %}

{{ macros.begin_stage('Configure cephadm') }}

{{ macros.begin_step('Install ceph packages') }}

install cephadm:
  pkg.installed:
    - pkgs:
        - ceph-base
        - ceph-common
    - failhard: True

{{ macros.end_step('Install ceph packages') }}

{{ macros.begin_step('Run "cephadm check-host"') }}

have cephadm check the host:
  cmd.run:
    - name: |
        cephadm check-host
    - failhard: True

{{ macros.end_step('Run "cephadm check-host"') }}

{{ macros.end_stage('Configure cephadm') }}

{% endif %}
