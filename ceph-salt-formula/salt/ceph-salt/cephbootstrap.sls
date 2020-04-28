{% import 'macros.yml' as macros %}

{% if grains['id'] == pillar['ceph-salt']['bootstrap_minion'] %}

{{ macros.begin_stage('Bootstrap the Ceph cluster') }}

{% set bootstrap_ceph_conf = pillar['ceph-salt'].get('bootstrap_ceph_conf', {}) %}

create bootstrap ceph conf:
  cmd.run:
    - name: |
        echo -en "" > /tmp/bootstrap-ceph.conf
{% for section, settings in bootstrap_ceph_conf.items() %}
        echo -en "[{{ section }}]\n" >> /tmp/bootstrap-ceph.conf
{% for setting, value in settings.items() %}
        echo -en "        {{ setting }} = {{ value }}\n" >> /tmp/bootstrap-ceph.conf
{% endfor %}
{% endfor %}
    - failhard: True

{{ macros.begin_step('Wait for other minions') }}
wait for other minions:
  ceph_salt.wait_for_grain:
    - grain: ceph-salt:execution:provisioned
    - hosts: {{ pillar['ceph-salt']['minions']['all'] }}
    - failhard: True
{{ macros.end_step('Wait for other minions') }}

{{ macros.begin_step('Run "cephadm bootstrap"') }}

{% set dashboard_username = pillar['ceph-salt'].get('dashboard', {'username': 'admin'}).get('username', 'admin') %}

run cephadm bootstrap:
  cmd.run:
    - name: |
        CEPHADM_IMAGE={{ pillar['ceph-salt']['container']['images']['ceph'] }} \
        cephadm --verbose bootstrap --mon-ip {{ pillar['ceph-salt']['bootstrap_mon_ip'] }} \
                --config /tmp/bootstrap-ceph.conf \
                --initial-dashboard-user {{ dashboard_username }} \
                --output-keyring /etc/ceph/ceph.client.admin.keyring \
                --skip-monitoring-stack \
                --skip-prepare-host \
                --skip-pull \
                --skip-ssh \
{%- for arg, value in pillar['ceph-salt'].get('bootstrap_arguments', {}).items() %}
                --{{ arg }} {{ value if value is not none else '' }} \
{%- endfor %}
                > /var/log/ceph/cephadm.log 2>&1
    - env:
      - NOTIFY_SOCKET: ''
    - creates:
      - /etc/ceph/ceph.client.admin.keyring
    - failhard: True

{{ macros.end_step('Run "cephadm bootstrap"') }}

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

{{ macros.begin_step('Configure cephadm MGR module') }}

configure ssh orchestrator:
  cmd.run:
    - name: |
        ceph config-key set mgr/cephadm/ssh_identity_key -i /tmp/ceph-salt-ssh-id_rsa
        ceph config-key set mgr/cephadm/ssh_identity_pub -i /tmp/ceph-salt-ssh-id_rsa.pub
        ceph mgr module enable cephadm && \
        ceph orch set backend cephadm
    - onchanges:
      - cmd: run cephadm bootstrap
    - failhard: True

{{ macros.end_step('Configure cephadm MGR module') }}

{{ macros.end_stage('Bootstrap the Ceph cluster') }}

{% endif %}
