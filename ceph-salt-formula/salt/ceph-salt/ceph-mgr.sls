{% import 'macros.yml' as macros %}

{% if pillar['ceph-salt']['minions'].get('mgr', {}) | length > 1 %}
{% set mgr_update_args = [] %}
{% for minion in pillar['ceph-salt']['minions']['mgr'] %}
{% if mgr_update_args.append(minion) %}{% endif %}
{% endfor %}

{{ macros.begin_stage('Deploy post-bootstrap Ceph MGRs') }}

deploy remaining mgrs:
  cmd.run:
    - name: |
        ceph orch apply mgr {{ mgr_update_args | join(',') }}
    - failhard: True

{{ macros.end_stage('Deploy post-bootstrap Ceph MGRs') }}

{% endif %}
