{% import 'macros.yml' as macros %}

{{ macros.begin_stage('Container environment') }}

{{ macros.begin_step('Configure registries') }}

{% with registries = pillar['ceph-salt'].get('container', {}).get('registries', []) %}
  {% if registries|length > 0 %}
/etc/containers/registries.conf:
  file.managed:
    - source:
        - salt://ceph-salt/files/registries.conf.j2
    - template: jinja
    - user: root
    - group: root
    - mode: '0644'
    - backup: minion
    - failhard: True
    - defaults:
        registries: {{ registries }}
  {% endif %}
{% endwith %}

{{ macros.end_step('Configure registries') }}

{{ macros.end_stage('Container environment') }}
