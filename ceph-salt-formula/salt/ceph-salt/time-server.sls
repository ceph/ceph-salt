{% if pillar['ceph-salt']['time_server'].get('enabled', True) %}

{% import 'macros.yml' as macros %}

{{ macros.begin_stage('Starting chrony and syncing clocks on time_server node') }}

{% set time_server = pillar['ceph-salt']['time_server']['server_host'] %}
{% if grains['fqdn'] == time_server %}

start chronyd on time_server:
  service.running:
    - name: chronyd
    - enable: True
    - failhard: True

sync time_server with external time servers:
  cmd.run:
    - name: |
        chronyc makestep
        chronyc waitsync
    - failhard: True

{% endif %}

{{ macros.end_stage('Starting chrony and syncing clocks on time_server node') }}

{% endif %}

prevent empty file:
  test.nop

