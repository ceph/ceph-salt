{% import 'macros.yml' as macros %}

{{ macros.begin_stage('Deployment of Ceph OSDs') }}

{% set dg_list = pillar['ceph-salt'].get('storage', {'drive_groups': []}).get('drive_groups', []) %}
{% for dg_spec in dg_list %}

{{ macros.begin_step('Deploying OSD groups ' + (loop.index | string) + '/' + (dg_list | length | string)) }}

deploy ceph osds ({{ loop.index }}/{{ dg_list | length }}):
  cmd.run:
    - name: |
        echo '{{ dg_spec }}' | ceph orchestrator osd create -i -

{{ macros.end_step('Deploying OSD groups ' + (loop.index | string) + '/' + (dg_list | length | string)) }}

{% endfor %}

{{ macros.end_stage('Deployment of Ceph OSDs') }}
