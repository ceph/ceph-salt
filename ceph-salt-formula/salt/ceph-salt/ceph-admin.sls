{% import 'macros.yml' as macros %}

{% if pillar['ceph-salt']['minions']['admin'] | length > 1 %}

{{ macros.begin_stage('Ensure ceph.conf and keyring are present on all Admin nodes') }}

copy ceph.conf and keyring to other admin nodes:
  cmd.run:
    - name: |
{%- for minion in pillar['ceph-salt']['minions']['admin'] %}
{%- if minion != grains['host'] %}
        scp -o "StrictHostKeyChecking=no" /etc/ceph/ceph.conf root@{{ minion }}:/etc/ceph/
        scp -o "StrictHostKeyChecking=no" /etc/ceph/ceph.client.admin.keyring root@{{ minion }}:/etc/ceph/
{%- endif %}
{%- endfor %}
    - failhard: True

{{ macros.end_stage('Ensure ceph.conf and keyring are present on all Admin nodes') }}

{% endif %}
