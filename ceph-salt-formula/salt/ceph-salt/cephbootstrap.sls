{% import 'macros.yml' as macros %}

{{ macros.begin_stage('Ceph bootstrap') }}

{% if grains['id'] == pillar['ceph-salt']['bootstrap_minion'] %}
/var/log/ceph:
  file.directory:
    - user: ceph
    - group: ceph
    - mode: '0770'
    - makedirs: True
    - failhard: True

{{ macros.begin_step('Wait for other minions') }}
wait for other minions:
  ceph_salt.wait_for_grain:
    - grain: ceph-salt:execution:provisioned
    - failhard: True
{{ macros.end_step('Wait for other minions') }}

{{ macros.begin_step('Run cephadm bootstrap') }}

{% set dashboard_username = pillar['ceph-salt'].get('dashboard', {'username': 'admin'}).get('username', 'admin') %}

run cephadm bootstrap:
  cmd.run:
    - name: |
{%- if 'container' in pillar['ceph-salt'] and 'ceph' in pillar['ceph-salt']['container']['images'] %}
        CEPHADM_IMAGE={{ pillar['ceph-salt']['container']['images']['ceph'] }} \
{%- endif %}
        cephadm --verbose bootstrap --mon-ip {{ grains['fqdn_ip4'][0] }} \
                --initial-dashboard-user {{ dashboard_username }} \
                --output-keyring /etc/ceph/ceph.client.admin.keyring \
                --output-config /etc/ceph/ceph.conf \
                --skip-ssh > /var/log/ceph/cephadm.log 2>&1
    - creates:
      - /etc/ceph/ceph.conf
      - /etc/ceph/ceph.client.admin.keyring
    - failhard: True

{{ macros.end_step('Run cephadm bootstrap') }}

{% set dashboard_password = pillar['ceph-salt'].get('dashboard', {'password': None}).get('password', None) %}
{% if dashboard_password %}
set ceph-dashboard password:
  cmd.run:
    - name: |
        ceph dashboard ac-user-set-password --force-password admin {{ dashboard_password }}
    - onchanges:
      - cmd: run cephadm bootstrap
    - failhard: True
{% endif %}

{{ macros.begin_step('Configure SSH orchestrator') }}

configure ssh orchestrator:
  cmd.run:
    - name: |
        ceph config-key set mgr/cephadm/ssh_identity_key -i ~/.ssh/id_rsa
        ceph config-key set mgr/cephadm/ssh_identity_pub -i ~/.ssh/id_rsa.pub
        ceph mgr module enable cephadm && \
        ceph orch set backend cephadm && \
{% for minion in pillar['ceph-salt']['minions']['all'] %}
        ceph orch host add {{ minion }} && \
{% endfor %}
        true
    - onchanges:
      - cmd: run cephadm bootstrap
    - failhard: True

{{ macros.end_step('Configure SSH orchestrator') }}

{% endif %}

{{ macros.end_stage('Ceph bootstrap') }}
