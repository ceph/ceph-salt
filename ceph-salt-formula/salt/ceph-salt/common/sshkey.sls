{% import 'macros.yml' as macros %}

{{ macros.begin_stage('Distribute SSH keys') }}

{% set ssh_user = pillar['ceph-salt']['ssh']['user'] %}
{% set ssh_user_group = 'root' if ssh_user == 'root' else 'users' %}

{% if ssh_user != 'root' %}

create ssh user group:
  group.present:
    - name: {{ ssh_user_group }}

create ssh user:
  user.present:
    - name: {{ ssh_user }}
    - home: /home/{{ssh_user}}
    - groups:
      - {{ ssh_user_group }}
    - failhard: True

{% endif %}

{{ macros.sudoers('configure sudoers') }}

# make sure .ssh is present with the right permissions
create ssh dir:
  file.directory:
    - name: /home/{{ ssh_user }}/.ssh
    - user: {{ ssh_user }}
    - group: {{ ssh_user_group }}
    - mode: '0700'
    - makedirs: True
    - failhard: True

{% set home = '/home/' ~ssh_user if ssh_user != 'root' else '/root' %}

# private key
create ceph-salt-ssh-id_rsa:
  file.managed:
    - name: {{ home }}/.ssh/id_rsa
    - user: {{ ssh_user }}
    - group: {{ ssh_user_group }}
    - mode: '0600'
    - contents_pillar: ceph-salt:ssh:private_key
    - failhard: True

# public key
create ceph-salt-ssh-id_rsa.pub:
  file.managed:
    - name: {{ home }}/.ssh/id_rsa.pub
    - user: {{ ssh_user }}
    - group: {{ ssh_user_group }}
    - mode: '0644'
    - contents_pillar: ceph-salt:ssh:public_key
    - failhard: True

# add public key to authorized_keys
install ssh key:
    ssh_auth.present:
      - user: {{ ssh_user }}
      - comment: ssh_key_created_by_ceph_salt
      - config: /%h/.ssh/authorized_keys
      - name: {{ pillar['ceph-salt']['ssh']['public_key'] }}
      - failhard: True

{{ macros.end_stage('Distribute SSH keys') }}
