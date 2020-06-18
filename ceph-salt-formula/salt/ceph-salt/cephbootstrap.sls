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

{% set dashboard_username = pillar['ceph-salt']['dashboard']['username'] %}
{% set dashboard_password = pillar['ceph-salt']['dashboard']['password'] %}

run cephadm bootstrap:
  cmd.run:
    - name: |
        CEPHADM_IMAGE={{ pillar['ceph-salt']['container']['images']['ceph'] }} \
        cephadm --verbose bootstrap --mon-ip {{ pillar['ceph-salt']['bootstrap_mon_ip'] }} \
                --config /tmp/bootstrap-ceph.conf \
                --initial-dashboard-user {{ dashboard_username }} \
                --initial-dashboard-password {{ dashboard_password }} \
{%- if not pillar['ceph-salt']['dashboard']['password_update_required'] %}
                --dashboard-password-noupdate \
{%- endif %}
                --output-keyring /etc/ceph/ceph.client.admin.keyring \
                --output-config /etc/ceph/ceph.conf \
                --skip-monitoring-stack \
                --skip-prepare-host \
                --skip-pull \
                --ssh-private-key /tmp/ceph-salt-ssh-id_rsa \
                --ssh-public-key /tmp/ceph-salt-ssh-id_rsa.pub \
{%- for arg, value in pillar['ceph-salt'].get('bootstrap_arguments', {}).items() %}
                --{{ arg }} {{ value if value is not none else '' }} \
{%- endfor %}
                > /var/log/ceph/cephadm.log 2>&1
    - env:
      - NOTIFY_SOCKET: ''
    - creates:
      - /etc/ceph/ceph.conf
      - /etc/ceph/ceph.client.admin.keyring
    - failhard: True

{{ macros.end_step('Run "cephadm bootstrap"') }}

{{ macros.end_stage('Bootstrap the Ceph cluster') }}

{% endif %}
