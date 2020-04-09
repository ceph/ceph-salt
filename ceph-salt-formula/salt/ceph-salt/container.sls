{% import 'macros.yml' as macros %}

{{ macros.begin_stage('Container environment') }}

{{ macros.begin_step('Configure registries') }}

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

{{ macros.end_step('Configure registries') }}

{{ macros.end_stage('Container environment') }}
