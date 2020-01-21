{% if pillar['ceph-salt']['minions'].get('mgr', {}) | length > 1 %}
{% set mgr_update_args = [pillar['ceph-salt']['minions']['mgr'] | length | string] %}
{% for minion in pillar['ceph-salt']['minions']['mgr'] %}
{% if minion != grains['id'] %}
{% if mgr_update_args.append(minion) %}{% endif %}
{% endif %}
{% endfor %}

deploy remaining mgrs:
  cmd.run:
    - name: |
        ceph orchestrator mgr update {{ mgr_update_args | join(' ') }}

{% endif %}