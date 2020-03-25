{% if pillar['ceph-salt']['time_server'].get('enabled', True) %}

{% import 'macros.yml' as macros %}

{{ macros.begin_stage('Setting up time synchronization') }}

{{ macros.begin_step('Install chrony package') }}
install chrony:
  pkg.installed:
    - pkgs:
      - chrony
    - refresh: True
    - failhard: True
{{ macros.end_step('Install chrony package') }}

service_reload:
  module.run:
    - name: service.systemctl_reload
    - failhard: True

{{ macros.begin_step('Configure chrony service') }}
/etc/chrony.conf:
  file.managed:
    - source:
        - salt://ceph-salt/files/chrony.conf.j2
    - template: jinja
    - user: root
    - group: root
    - mode: '0644'
    - makedirs: True
    - backup: minion
    - failhard: True

{{ macros.end_step('Configure chrony service') }}

{{ macros.end_stage('Setting up time synchronization') }}

{% endif %}

prevent empty file:
  test.nop

