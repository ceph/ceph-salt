{% import 'macros.yml' as macros %}

{{ macros.begin_stage('Add host to ceph orchestrator') }}

{% set bootstrap_host = pillar['ceph-salt']['bootstrap_minion'].split('.', 1)[0] %}

add host to ceph orch:
  cmd.run:
    - name: |
        ssh -o "StrictHostKeyChecking=no" -i /tmp/ceph-salt-ssh-id_rsa root@{{ bootstrap_host }} "ceph orch host add {{ grains['host'] }}"
    - failhard: True

{{ macros.end_stage('Add host to ceph orchestrator') }}
