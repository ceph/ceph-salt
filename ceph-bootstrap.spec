#
# spec file for package ceph-bootstrap
#
# Copyright (c) 2019 SUSE LINUX GmbH, Nuernberg, Germany.
#
# All modifications and additions to the file contributed by third parties
# remain the property of their copyright owners, unless otherwise agreed
# upon. The license for this file, and modifications and additions to the
# file, is the same license as for the pristine package itself (unless the
# license for the pristine package is not an Open Source License, in which
# case the license is the MIT License). An "Open Source License" is a
# license that conforms to the Open Source Definition (Version 1.9)
# published by the Open Source Initiative.

# Please submit bugfixes or comments via http://bugs.opensuse.org/
#


%if 0%{?el8} || (0%{?fedora} && 0%{?fedora} < 30)
%{python_enable_dependency_generator}
%endif

Name:           ceph-bootstrap
Version:        15.0.1
Release:        1%{?dist}
Summary:        CLI tool to deploy Ceph clusters
License:        MIT
%if 0%{?suse_version}
Group:          System/Management
%endif
URL:            https://github.com/SUSE/%{name}
Source0:        %{url}/archive/v%{version}/%{name}-%{version}.tar.gz
BuildArch:      noarch

%if 0%{?suse_version}
BuildRequires:  python-rpm-macros
%else
BuildRequires:  python3-devel
%endif
BuildRequires:  fdupes
BuildRequires:  python3-setuptools

%if 0%{?suse_version}
Requires:       python3-click >= 6.7
Requires:       python3-configshell-fb >= 1.1
Requires:       python3-pycryptodomex >= 3.4.6
Requires:       python3-PyYAML >= 3.13
Requires:       python3-setuptools
Requires:       python3-salt >= 2019.2.0
%endif

Requires:       ceph-salt-formula
Requires:       salt-master >= 2019.2.0


%description
ceph-bootstrap is a CLI tool for deploying Ceph clusters starting from version
Octopus.


%prep
%autosetup -n %{name}-%{version} -p1


%build
%py3_build


%install
%py3_install
%fdupes %{buildroot}%{python3_sitelib}
install -m 0755 -d %{buildroot}/%{_datadir}/%{name}

# qa script installation
install -m 0755 -d %{buildroot}/%{_datadir}/%{name}/qa
install -m 0755 -d %{buildroot}/%{_datadir}/%{name}/qa/common
install -m 0755 qa/health-ok.sh %{buildroot}/%{_datadir}/%{name}/qa/health-ok.sh
install -m 0644 qa/common/common.sh %{buildroot}/%{_datadir}/%{name}/qa/common/common.sh
install -m 0644 qa/common/helper.sh %{buildroot}/%{_datadir}/%{name}/qa/common/helper.sh
install -m 0644 qa/common/json.sh %{buildroot}/%{_datadir}/%{name}/qa/common/json.sh
install -m 0644 qa/common/zypper.sh %{buildroot}/%{_datadir}/%{name}/qa/common/zypper.sh

# ceph-salt-formula installation
%define fname ceph-salt
%define fdir  %{_datadir}/salt-formulas

mkdir -p %{buildroot}%{fdir}/states/%{fname}/
mkdir -p %{buildroot}%{fdir}/metadata/%{fname}/
cp -R ceph-salt-formula/states/* %{buildroot}%{fdir}/states/%{fname}/
cp ceph-salt-formula/metadata/* %{buildroot}%{fdir}/metadata/%{fname}/

mkdir -p %{buildroot}%{_datadir}/%{fname}/pillar

# pillar top sls file
cat <<EOF > %{buildroot}%{_datadir}/%{fname}/pillar/top.sls
base:
    '*':
    - ceph-salt
EOF

# empty ceph-salt.sls file
cat <<EOF > %{buildroot}%{_datadir}/%{fname}/pillar/ceph-salt.sls
ceph-salt:

EOF

cat <<EOF > %{buildroot}%{_datadir}/%{fname}/pillar.conf.example
pillar_roots:
    base:
    - /srv/pillar
    - %{_datadir}/%{fname}/pillar
EOF


%files
%license LICENSE
%doc CHANGELOG.md README.md
%{python3_sitelib}/ceph_bootstrap*/
%{_bindir}/%{name}
%dir %{_datadir}/%{name}


%package qa
Summary:    Integration test script for ceph-bootstrap
Group:      System/Management


%description qa
Integration test script for validating Ceph clusters deployed
by ceph-bootstrap


%files qa
%{_datadir}/%{name}/qa


%package -n ceph-salt-formula
Summary:    Ceph Salt Formula
Group:      System/Management

%if ! (0%{?sle_version:1} && 0%{?sle_version} < 150100)
Requires(pre):  salt-formulas-configuration
%else
Requires(pre):  salt-master
%endif


%description -n ceph-salt-formula
Salt Formula to deploy Ceph clusters.


%files -n ceph-salt-formula
%defattr(-,root,root,-)
%license LICENSE
%doc README.md
%dir %attr(0755, root, salt) %{fdir}/
%dir %attr(0755, root, salt) %{fdir}/states/
%dir %attr(0755, root, salt) %{fdir}/metadata/
%dir %attr(0755, root, root) %{_datadir}/%{fname}
%{fdir}/states/
%{fdir}/metadata/
%{_datadir}/%{fname}


%changelog

