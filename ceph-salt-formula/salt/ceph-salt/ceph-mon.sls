{% import 'macros.yml' as macros %}

{% if pillar['ceph-salt']['minions']['mon'] | length > 1 %}
{% set add_mon_args = [] %}
{% for minion, ip in pillar['ceph-salt']['minions']['mon'].items() %}
{% if minion != grains['host'] %}
{% if add_mon_args.append(minion + ":" + ip) %}{% endif %}
{% endif %}
{% endfor %}

{{ macros.begin_stage('Deployment of Ceph MONs') }}

{% for add_mon_arg in add_mon_args %}

deploy remaining mon {{ add_mon_arg }}:
  cmd.run:
    - name: |
        ceph orch daemon add mon {{ add_mon_arg }}
    - failhard: True

{% endfor %}

generate up-to-date ceph.conf:
  cmd.run:
    - name: |
        ceph config generate-minimal-conf > /tmp/ceph.conf
        mv /tmp/ceph.conf /etc/ceph/
    - failhard: True

copy ceph.conf and keyring to other mons:
  cmd.run:
    - name: |
{%- for minion, ip in pillar['ceph-salt']['minions']['mon'].items() %}
{%- if minion != grains['id'] %}
        scp -o "StrictHostKeyChecking=no" /etc/ceph/ceph.conf root@{{ ip }}:/etc/ceph/
        scp -o "StrictHostKeyChecking=no" /etc/ceph/ceph.client.admin.keyring root@{{ ip }}:/etc/ceph/
{%- endif %}
{%- endfor %}
    - failhard: True

{{ macros.end_stage('Deployment of Ceph MONs') }}

{% endif %}
