{% import 'macros.yml' as macros %}

{% if pillar['ceph-salt']['minions'].get('mgr', {}) | length > 1 %}
{% set mgr_update_args = [] %}
{% for minion in pillar['ceph-salt']['minions']['mgr'] %}
{% if minion != grains['host'] %}
{% if mgr_update_args.append(minion) %}{% endif %}
{% endif %}
{% endfor %}

{{ macros.begin_stage('Deployment of Ceph MGRs') }}

deploy remaining mgrs:
  cmd.run:
    - name: |
        ceph orch apply mgr {{ mgr_update_args | join(',') }}
    - failhard: True

{{ macros.end_stage('Deployment of Ceph MGRs') }}

{% endif %}
