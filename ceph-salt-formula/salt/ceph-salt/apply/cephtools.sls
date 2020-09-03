{% import 'macros.yml' as macros %}

{% if 'cephadm' in grains['ceph-salt']['roles'] %}

{{ macros.begin_stage('Configure cephadm') }}

{{ macros.begin_step('Install cephadm and other packages') }}

install cephadm:
  pkg.installed:
    - pkgs:
        - cephadm
{% if 'admin' in grains['ceph-salt']['roles'] %}
        - ceph-base
        - ceph-common
{% endif %}
    - failhard: True

{{ macros.end_step('Install cephadm and other packages') }}

{{ macros.begin_step('Run "cephadm check-host"') }}

have cephadm check the host:
  cmd.run:
    - name: |
        cephadm check-host
    - failhard: True

{{ macros.end_step('Run "cephadm check-host"') }}

{{ macros.end_stage('Configure cephadm') }}

{% endif %}
