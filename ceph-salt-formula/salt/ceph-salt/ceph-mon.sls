{% if pillar['ceph-salt']['minions']['mon'] | length > 1 %}
{% set mon_update_args = [pillar['ceph-salt']['minions']['mon'] | length | string] %}
{% for minion, ip in pillar['ceph-salt']['minions']['mon'].items() %}
{% if minion != grains['id'] %}
{% if mon_update_args.append(minion + ":" + ip) %}{% endif %}
{% endif %}
{% endfor %}

deploy remaining mons:
  cmd.run:
    - name: |
        ceph orchestrator mon update {{ mon_update_args | join(' ') }}

generate up-to-date ceph.conf:
  cmd.run:
    - name: |
        ceph config generate-minimal-conf > /tmp/ceph.conf
        mv /tmp/ceph.conf /etc/ceph/

copy ceph.conf and keyring to other mons:
  cmd.run:
    - name: |
{%- for minion, ip in pillar['ceph-salt']['minions']['mon'].items() %}
{%- if minion != grains['id'] %}
        scp -o "StrictHostKeyChecking=no" /etc/ceph/ceph.conf root@{{ ip }}:/etc/ceph/
        scp -o "StrictHostKeyChecking=no" /etc/ceph/ceph.client.admin.keyring root@{{ ip }}:/etc/ceph/
{%- endif %}
{%- endfor %}

{% endif %}
