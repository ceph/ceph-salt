{% import 'macros.yml' as macros %}

{% if pillar['ceph-salt']['container']['registries_enabled'] %}

{{ macros.begin_stage('Set up container environment') }}

{{ macros.begin_step('Configure container image registries') }}

/etc/containers/registries.conf:
  file.managed:
    - source:
        - salt://ceph-salt/files/registries.conf.j2
    - template: jinja
    - user: root
    - group: root
    - mode: '0644'
    - backup: minion
    - failhard: True

{{ macros.end_step('Configure container image registries') }}

{{ macros.end_stage('Set up container environment') }}

{% endif %}
