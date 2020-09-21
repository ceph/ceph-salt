{% import 'macros.yml' as macros %}

{{ macros.begin_stage('Ensure SSH keys are configured') }}

create ssh user group:
  group.present:
    - name: users

create ssh user:
  user.present:
    - name: cephadm
    - home: /home/cephadm
    - groups:
      - users
    - failhard: True

install sudo:
  pkg.installed:
    - pkgs:
      - sudo
    - failhard: True

configure sudoers:
  file.append:
    - name: /etc/sudoers.d/ceph-salt
    - text:
      - "cephadm ALL=NOPASSWD: /usr/bin/ceph -s"
      - "cephadm ALL=NOPASSWD: /usr/bin/ceph orch host add *"
      - "cephadm ALL=NOPASSWD: /usr/bin/ceph orch host ok-to-stop *"
      - "cephadm ALL=NOPASSWD: /usr/bin/ceph orch status --format=json"
      - "cephadm ALL=NOPASSWD: /usr/bin/python3"
      - "cephadm ALL=NOPASSWD: /usr/bin/rsync"

# make sure .ssh is present with the right permissions
create ssh dir:
  file.directory:
    - name: /home/cephadm/.ssh
    - user: cephadm
    - group: users
    - mode: '0700'
    - makedirs: True
    - failhard: True

# private key
create ceph-salt-ssh-id_rsa:
  file.managed:
    - name: /home/cephadm/.ssh/id_rsa
    - user: cephadm
    - group: users
    - mode: '0600'
    - contents_pillar: ceph-salt:ssh:private_key
    - failhard: True

# public key
create ceph-salt-ssh-id_rsa.pub:
  file.managed:
    - name: /home/cephadm/.ssh/id_rsa.pub
    - user: cephadm
    - group: users
    - mode: '0644'
    - contents_pillar: ceph-salt:ssh:public_key
    - failhard: True

# add public key to authorized_keys
install ssh key:
    ssh_auth.present:
      - user: cephadm
      - comment: ssh_key_created_by_ceph_salt
      - config: /%h/.ssh/authorized_keys
      - name: {{ pillar['ceph-salt']['ssh']['public_key'] }}
      - failhard: True

{{ macros.end_stage('Ensure SSH keys are configured') }}
