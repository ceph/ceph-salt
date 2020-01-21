{% import 'macros.yml' as macros %}

{{ macros.begin_stage('Install and configure AppArmor') }}

aa-enabled:
  cmd.run:
    - onfail:
      - test: apparmor

aa-teardown:
  cmd.run:
    - onlyif:
      - which aa-teardown

stop apparmor:
  service.dead:
    - enable: False

uninstall apparmor:
  pkg.removed:
    - pkgs:
      - apparmor
      - apparmor-utils

apparmor:
  test.nop

{{ macros.end_stage('Install and configure AppArmor') }}
