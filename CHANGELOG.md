# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

## [15.2.13] - 2020-10-08
### Added
- Use '--container-init' option on 'cephadm bootstrap' (#396)
- Support FQDN environments (#422)
### Fixed
- Spell "Resetting" correctly (#423)
- Add "Conflicts: deepsea-cli" to spec file (#421)
- Expand the userpath during ssh key import (#425)
- Reduce ceph-salt pillar file permissions (#415)

## [15.2.12] - 2020-09-28
### Added
- Convert tags to repo_digest (#397)
- Add 'ceph-salt stop' command (#404)
- Validate duplicated registries (#403)
- Validate '/cephadm_bootstrap/mon_ip' (#401)
- Retry SSH 'host add' execution on connection closed (#398)
### Changed
- Change cephadm bootstrap output redirect file (#395)
### Fixed
- Handle unresponsive minions properly (#411)
- Display 'stderr' on stage/step failure (#408)
- Restart 'chronyd' service to apply chrony config (#407)
- Install 'sudo' before 'sudoers' configuration (#400)
- Fix salt warn when 'ceph-salt config' is executed for the first time (#399)

## [15.2.11] - 2020-09-11
### Added
- Ask user confirmation before restarting 'salt-master' service (#392)
- Execute salt sync-all on 'ceph-salt' config and status commands (#391)
- Support bootstrap minion without admin role (#383)
- Ignore 'cephbootstrap' salt state when ceph cluster already running (#385)
- Add tuned 'latency' and 'throughput' roles (#361, #364, #387)
- Improve SSH keys stage description (#376)
- Remove 'ceph-salt:execution:provisioned' grain (#374)
- Sanity-check time sync services when /time_server is disabled (#367)
- Always use SSH 'cephadm' user (#363)
- Use salt module for SSH executions (#363)
- Set 'UserKnownHostsFile' and 'ConnectTimeout' on SSH connections (#363)
- Verify whether minion nodes can resolve hostnames (#356)
- Install ceph-salt ssh keys on admin minions (#257)
- Add 'test.ping' sanity check (#354)
### Changed
- Move ceph image path config to bootstrap section (#386)
- Only pull ceph image on bootstrap minion (#353)
### Fixed
- Install 'sudo' package (#384)
- Fix reboot in parallel with cluster running (#380)
- Rename '/etc/sudoers.d' file to avoid collision with cephadm (#363)
- Bootstrap minion don't need to wait for other minions (#351)

## [15.2.10] - 2020-08-31
### Added
- Add 'ceph-salt reboot [--force] [minion_id]' command (#325)
- Write INFO message to log when stage/step begins/ends (#344)
- Test on Python 3.8 instead of 3.7 (#338)
- Add 'network' runner (#329)
- Check for running jobs when failing to re-apply formula (#332)
### Removed
- Remove '/system_update' config option (#345)
### Fixed
- More meaningful SSH key comment (#337)

## [15.2.9] - 2020-08-10
### Added
- Add 'ceph-salt update [--reboot] [minion_id]' command (#303)
- Enable 'ceph.conf' management by cephadm (#291)
- Suggest 'secure=false' on custom registries configuration help (#323)
- Make use of cephadm for registry authentication (#295)

## [15.2.8] - 2020-08-10
### Added
- Change default SSH user from 'root' to 'ceph-salt' (#319)
- Make bootstrap minion optional (#315)
- Purge ceph cluster (#306)
- Install 'ceph-base' on admin minions (#305)
- Declare RPM dependencies in spec file (#302)
### Fixed
- 'cephadm' MGR module should only be enabled after cluster bootstrapped (#322)
- Support SSH users that are configured by packages (#318)
- aa-teardown can fail if apparmor is disabled on the boot command line (#316)
- Configure 'qualified-search-registries = ["docker.io"]' (#321)
- SSH pub and priv key should be set via 'cephadm' (#312)
- Only create a single MON and MGR during bootstrap (#308)
- Handle value errors on command line (#313)
- Omit chrony.conf useless and counterproductive options (#311)
- Install rsync (#301)

## [15.2.7] - 2020-07-17
### Added
- Only allow authentication on a single registry (#298)
- Allow user to specify sudo ssh user (#290)
- Rely on "bootstrap" to configure MGR module (#270)
### Removed
- Drop unqualified image name support (#299)
### Fixed
- Check 'ceph orch status' output (#283)
- Optimize 'ceph-salt status' (#293)
- Improve "no minions matched" message when adding/removing minions (#287)

## [15.2.6] - 2020-07-01
### Added
- Support registry authentication (#277)
- Allow users to disable custom registries configuration (#262)
- Allow to re-apply config (#269)
- Add "Conflicts: deepsea" to spec file (#259)
- Switch to reactive UI refresh after execution is complete (#254)
- Allow user to "paused" UI refresh during execution (#254)
- Report log file location on exit (#255)
- Allow users to provide their dashboard cert for bootstrap (#253)
### Removed
- Don't log scrollbar info when rendering scrollbar (#263)
### Fixed
- Fix log location message (#278)
- Reduce the number of remote grain requests (#271)
- Optimize "ceph_orch.wait_for_admin_host" state (#276)
- Handle execution errors on command line (#264)
- Improve containers step/stage descriptions (#268)
- Fix python3-ntplib required version (#249)

## [15.2.5] - 2020-05-25
### Added
- Support SSH keys import and export (#243)
- Probe external time servers (#247)
- Persist journal logs (#244)
- Add 'cephadm' role (#235)
### Fixed
- Retry first chronyc execution (#239)

## [15.2.4] - 2020-05-15
### Added
- Enforce dashboard password change upon first login (#220)
- User feedback when adding/removing minions (#227)
- Optimize "ceph-salt config" command (#224)
- Optimize remote grain get (#230)
- Persist default values in pillar data (#219)
- Log warn when public IP is loopback IP (#216)
### Fixed
- Fix error on 'ceph-salt status' when pillar data is empty (#221)
- Don't log dashboard password (#228)
- Unable to see dashboard password (#220)
- Do not log pillar data secrets (#234)
- Wait longer for clock sync (#233)

## [15.2.3] - 2020-05-04
### Added
- Support time server not managed by ceph-salt (#206)
- Sync clocks to avoid clock skew when MONs start (#202)
### Fixed
- Wait for admin should fail if any admin failed (#207)
- Store minion_id in pillar instead of hostname (#211)

## [15.2.2] - 2020-04-28
### Added
- Advanced settings for "cephadm bootstrap" (#170)
- Rename `ceph-salt deploy` to `ceph-salt apply` (#200)
- Require Salt >= 3000 (#185)
### Removed
- Remove "disable cephadm bootstrap" functionality (#184)
### Fixed
- Fix `status` error when no minions are specified (#188)

## [15.2.1] - 2020-04-16
### Added
- Support adding new hosts after initial deployment (#175)
- Skip monitoring stack on bootstrap (#179)
- Allow explicit set chrony subnet (#165)
- Avoid 127.0.0.1 as a nodes public_ip (#174)
- Allow users to configure custom registries (#113)
- Rename minions "rm" command to "remove" (#167)
- Use lowercase on config nodes (#166)
- Support quoted string values (#162)
- Support salt 3000 (#159)
- Allow explicit set bootstrap Mon IP (#156)
### Removed
- OSDs are no longer deployed by `ceph-salt` (#146)
- Additional MONs and MGRs are no longer deployed by `ceph-salt` (#151)
### Fixed
- Install private/public keys on admin nodes (#155)
- Fix "status" error when ceph_orch salt module is not available (#157)

## [15.2.0] - 2020-03-25
### Added
- Support bootstrap ceph config (#129)
- Run "cephadm check-host" on all minions (#137)
### Fixed
- Improve descriptions of stages and steps (#144)
- Do not omit bootstrap MGR from "ceph orch apply mgr" (#136)
- Use new OSD creation syntax (#133)
- Work around podman/runc bug (#134)

## [15.1.1] - 2020-03-18
### Added
- Add "Admin" role (#121)
- Support config export and import (#90)
- Add "status" command (#112)
- Automatically set chooseleaf type if needed (#105)
- Improve error handling when calling salt commands (#89)
- Rename ceph-bootstrap to ceph-salt (#93)
### Fixed
- Use `cephadm pull` instead of `podman pull` (#122)
- Handle execution errors (#126)
- Fix error when deploying additional mgrs (#119)
- Bump PyYAML dependency (#117)
- No default value for Ceph container image path (#115)
- Work around timing issue in cephadm device list (#109)
- Renamed "host" field to "hostname" (#111)
- Use "ceph orch daemon add mon" to add remaining MONs (#108)
- Tell ceph orch the right number of mgrs (#106)
- Add `--skip-prepare-host` to `cephadm bootstrap` (#98)
- Fix salt job return event processing (#95)
- Check os_family before executing zypper command (#92)
- Eliminate implicit dependency on which (#85)
### Removed
- Migrate ceph-bootstrap-qa to sesdev (#88)

## [15.1.0] - 2020-02-17
### Added
- System update and reboot during deployment (#11)
- Ensure ceph-salt-formula is loaded by the salt-master before deploy (#65)
- Automatic pillar setup (#8)
- Check salt-master is up and running (#61)
- Wait more verbosely on QA ceph_health_test (#62)
### Fixed
- Rename calls to Ceph Orchestrator Apply (#80)
- Rename calls to Ceph Orchestrator (#73)
- Explicitly install podman (#72)

## [15.0.2] - 2020-01-29
### Added
- New "deploy" command with real-time feedback (#9)
- Use salt-event bus to notify about execution progress (#30)
- Initial integration testing (#33)
### Fixed
- Require root privileges (#18)
- Remove salt python API terminal output (#10)
- Hide Dashboard password (#48)
- Fixed error when deploying without any role (#45)
- Fixed error when deploying without any time server (#40)
- Fixed bootstrap help message (#36)

## [15.0.1] - 2020-01-17
### Added
- Each config shell command now returns a success or error message (#13)
- Moved ceph-salt-formula into ceph-bootstrap project as a subpackage (#26)
### Fixed
- Check if minion FQDN resolves to loopback IP address (#21)
- Fixed "help" command when help text is not provided (#14)
- Fixed "bootstrap_mon" update when the last MON is removed (#17)
- Minions without role are also added to "ceph-salt:minions:all" (#22)
- Fix minion removal upon error (#24)

## [0.1.0] - 2019-12-12
### Added
- Mgr/Mon roles configuration
- Configuration of drive groups specifications to be used in OSD deployment
- Ceph-dashboard credentials configuration
- Ceph daemon container image path configuration
- Control Mon/Mgr/OSD deployment with enable/disable flags

## [0.0.1] - 2019-12-03
### Added
- `sesboot`: CLI tool
- RPM spec file.
- Minimal README.
- The CHANGELOG file.

[Unreleased]: https://github.com/ceph/ceph-salt/compare/v15.2.13...HEAD
[15.2.13]: https://github.com/ceph/ceph-salt/releases/tag/v15.2.13
[15.2.12]: https://github.com/ceph/ceph-salt/releases/tag/v15.2.12
[15.2.11]: https://github.com/ceph/ceph-salt/releases/tag/v15.2.11
[15.2.10]: https://github.com/ceph/ceph-salt/releases/tag/v15.2.10
[15.2.9]: https://github.com/ceph/ceph-salt/releases/tag/v15.2.9
[15.2.8]: https://github.com/ceph/ceph-salt/releases/tag/v15.2.8
[15.2.7]: https://github.com/ceph/ceph-salt/releases/tag/v15.2.7
[15.2.6]: https://github.com/ceph/ceph-salt/releases/tag/v15.2.6
[15.2.5]: https://github.com/ceph/ceph-salt/releases/tag/v15.2.5
[15.2.4]: https://github.com/ceph/ceph-salt/releases/tag/v15.2.4
[15.2.3]: https://github.com/ceph/ceph-salt/releases/tag/v15.2.3
[15.2.2]: https://github.com/ceph/ceph-salt/releases/tag/v15.2.2
[15.2.1]: https://github.com/ceph/ceph-salt/releases/tag/v15.2.1
[15.2.0]: https://github.com/ceph/ceph-salt/releases/tag/v15.2.0
[15.1.1]: https://github.com/ceph/ceph-salt/releases/tag/v15.1.1
[15.1.0]: https://github.com/ceph/ceph-salt/releases/tag/v15.1.0
[15.0.2]: https://github.com/ceph/ceph-salt/releases/tag/v15.0.2
[15.0.1]: https://github.com/ceph/ceph-salt/releases/tag/v15.0.1
[0.1.0]: https://github.com/ceph/ceph-salt/releases/tag/v0.1.0
[0.0.1]: https://github.com/ceph/ceph-salt/releases/tag/v0.0.1
