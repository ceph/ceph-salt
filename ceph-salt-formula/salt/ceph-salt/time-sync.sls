{% if pillar['ceph-salt']['time_server'].get('enabled', True) %}
{% set time_server = pillar['ceph-salt']['time_server']['server_host'] %}

{% import 'macros.yml' as macros %}

{{ macros.begin_stage('Sync clocks') }}

/tmp/chrony_sync_clock.sh:
  file.managed:
    - source:
        - salt://ceph-salt/files/chrony_sync_clock.sh
    - user: root
    - group: root
    - mode: '0755'
    - makedirs: True
    - backup: minion
    - failhard: True

{% if grains['fqdn'] != time_server %}

{{ macros.begin_step('Wait for time server node to signal that it has synced its clock') }}
wait for time server sync:
  ceph_salt.wait_for_grain:
    - grain: ceph-salt:execution:timeserversynced
    - hosts: [ {{ pillar['ceph-salt']['time_server']['server_host'] }} ]
    - failhard: True
{{ macros.end_step('Wait for time server node to signal that it has synced its clock') }}

{% endif %}

{{ macros.begin_step('Force clock sync now') }}

run sync script:
  cmd.run:
    - name: |
        /tmp/chrony_sync_clock.sh
    - failhard: True

{{ macros.end_step('Force clock sync now') }}

{% if grains['fqdn'] == time_server %}
{{ macros.begin_step('Signal that time server node has synced its clock') }}
set timeserversynced:
  grains.present:
    - name: ceph-salt:execution:timeserversynced
    - value: True
{{ macros.end_step('Signal that time server node has synced its clock') }}
{% endif %}

delete clock sync script:
  file.absent:
    - name: |
        /tmp/chrony_sync_clock.sh
    - failhard: True

{{ macros.end_stage('Sync clocks') }}

{% endif %}

prevent empty time-sync:
  test.nop

