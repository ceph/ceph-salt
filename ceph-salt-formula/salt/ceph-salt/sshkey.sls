{% import 'macros.yml' as macros %}

{{ macros.begin_stage('Distribute SSH keys') }}

# make sure .ssh is present with the right permissions
/home/root/.ssh:
  file.directory:
    - user: root
    - group: root
    - mode: '0700'
    - makedirs: True
    - failhard: True

# private key
create ceph-salt-ssh-id_rsa:
  file.managed:
    - name: /tmp/ceph-salt-ssh-id_rsa
    - user: root
    - group: root
    - mode: '0600'
    - contents_pillar: ceph-salt:ssh:private_key
    - failhard: True

# public key
create ceph-salt-ssh-id_rsa.pub:
  file.managed:
    - name: /tmp/ceph-salt-ssh-id_rsa.pub
    - user: root
    - group: root
    - mode: '0644'
    - contents_pillar: ceph-salt:ssh:public_key
    - failhard: True

# add public key to authorized_keys
install ssh key:
    ssh_auth.present:
      - user: root
      - comment: ssh_orchestrator_key
      - config: /%h/.ssh/authorized_keys
      - name: {{ pillar['ceph-salt']['ssh']['public_key'] }}
      - failhard: True

{{ macros.end_stage('Distribute SSH keys') }}
