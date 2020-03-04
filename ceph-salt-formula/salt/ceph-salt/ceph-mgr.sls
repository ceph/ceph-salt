{% import 'macros.yml' as macros %}

{% if pillar['ceph-salt']['minions'].get('mgr', {}) | length > 1 %}
{% set add_mgr_args = [] %}
{% for minion in pillar['ceph-salt']['minions']['mgr'] %}
{% if minion != grains['host'] %}
{% if add_mgr_args.append(minion) %}{% endif %}
{% endif %}
{% endfor %}

{{ macros.begin_stage('Deployment of Ceph MGRs') }}

{% for add_mgr_arg in add_mgr_args %}

deploy remaining mgr {{ add_mgr_arg }}:
  cmd.run:
    - name: |
        ceph orch daemon add mgr {{ add_mgr_arg }}
    - failhard: True

{% endfor %}

{{ macros.end_stage('Deployment of Ceph MGRs') }}

{% endif %}
