{% if pillar['ceph-salt']['time_server'].get('enabled', True) %}

{% import 'macros.yml' as macros %}

{{ macros.begin_stage('Starting chrony and syncing clocks on time slave nodes') }}

{% set time_server = pillar['ceph-salt']['time_server']['server_host'] %}

{% if grains['fqdn'] != time_server %}

start chronyd on slaves:
  service.running:
    - name: chronyd
    - enable: True
    - failhard: True

sync slaves with time_server:
  cmd.run:
    - name: |
        chronyc makestep
        chronyc waitsync
    - failhard: True

{% endif %}

{{ macros.end_stage('Starting chrony and syncing clocks on time slave nodes') }}

{% endif %}

prevent empty file:
  test.nop

