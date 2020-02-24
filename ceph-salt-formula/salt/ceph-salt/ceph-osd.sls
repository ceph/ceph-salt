{% import 'macros.yml' as macros %}

{{ macros.begin_stage('Deployment of Ceph OSDs') }}

{{ macros.begin_step('Spinning wheels for 60 seconds to work around https://tracker.ceph.com/issues/44270') }}

spin wheels for 60 seconds before creating any osds:
  cmd.run:
    - name: |
        sleep 60
    - failhard: True

{{ macros.end_step('Spinning wheels for 60 seconds to work around https://tracker.ceph.com/issues/44270') }}

{% set dg_list = pillar['ceph-salt'].get('storage', {'drive_groups': []}).get('drive_groups', []) %}
{% for dg_spec in dg_list %}

{{ macros.begin_step('Deploying OSD groups ' + (loop.index | string) + '/' + (dg_list | length | string)) }}

deploy ceph osds ({{ loop.index }}/{{ dg_list | length }}):
  cmd.run:
    - name: |
        echo '{{ dg_spec }}' | ceph orch osd create -i -
    - failhard: True

{{ macros.end_step('Deploying OSD groups ' + (loop.index | string) + '/' + (dg_list | length | string)) }}

{% endfor %}

{{ macros.end_stage('Deployment of Ceph OSDs') }}
