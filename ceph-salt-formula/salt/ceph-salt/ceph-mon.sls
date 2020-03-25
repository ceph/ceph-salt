{% import 'macros.yml' as macros %}

{% if pillar['ceph-salt']['minions']['mon'] | length > 1 %}
{% set add_mon_args = [] %}
{% for minion, ip in pillar['ceph-salt']['minions']['mon'].items() %}
{% if minion != grains['host'] %}
{% if add_mon_args.append(minion + ":" + ip) %}{% endif %}
{% endif %}
{% endfor %}

{{ macros.begin_stage('Deploy post-bootstrap Ceph MONs') }}

{% for add_mon_arg in add_mon_args %}

deploy remaining mon {{ add_mon_arg }}:
  cmd.run:
    - name: |
        ceph orch daemon add mon {{ add_mon_arg }}
    - failhard: True

{% endfor %}

{{ macros.end_stage('Deploy post-bootstrap Ceph MONs') }}

{% endif %}
