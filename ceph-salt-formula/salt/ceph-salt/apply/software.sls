{% import 'macros.yml' as macros %}

{{ macros.begin_stage('Install required packages') }}

install required packages:
  pkg.installed:
    - pkgs:
      - iperf
      - iputils
      - lsof
      - podman
      - python3-filelock
      - rsync
    - failhard: True

/var/log/journal:
  file.directory:
    - user: root
    - group: root
    - mode: '0755'
    - makedirs: True
    - failhard: True

{{ macros.end_stage('Install required packages') }}
