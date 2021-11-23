{% import 'macros.yml' as macros %}

{{ macros.begin_stage('Set up container environment') }}

{% if pillar['ceph-salt']['container']['registries_enabled'] %}

{{ macros.begin_step('Configure container image registries') }}

/etc/containers/registries.conf:
  file.managed:
    - source:
        - salt://ceph-salt/apply/files/registries.conf.j2
    - template: jinja
    - user: root
    - group: root
    - mode: '0644'
    - backup: minion
    - failhard: True

{{ macros.end_step('Configure container image registries') }}

{% endif %}

{% if grains['id'] == pillar['ceph-salt'].get('bootstrap_minion') or 'admin' in grains['ceph-salt']['roles'] %}
{% set auth = pillar['ceph-salt'].get('container', {}).get('auth', {}) %}
{% if auth %}
{{ macros.begin_step('Set container registry credentials') }}

create ceph-salt-registry-json:
  file.managed:
    - name: /tmp/ceph-salt-registry-json
    - source:
        - salt://ceph-salt/files/registry-login-json.j2
    - template: jinja
    - user: root
    - group: root
    - mode: '0600'
    - backup: minion
    - failhard: True

{{ macros.end_step('Set container registry credentials') }}
{% endif %}
{% endif %}


{{ macros.end_stage('Set up container environment') }}
