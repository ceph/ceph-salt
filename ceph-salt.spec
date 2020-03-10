#
# spec file for package ceph-salt
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

Name:           ceph-salt
Version:        15.1.0
Release:        1%{?dist}
Summary:        CLI tool to deploy Ceph clusters
License:        MIT
%if 0%{?suse_version}
Group:          System/Management
%endif
URL:            https://github.com/ceph/%{name}
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
Requires:       python3-PyYAML >= 5.1.2
Requires:       python3-setuptools
Requires:       python3-salt >= 2019.2.0
Requires:       python3-curses
%endif

Requires:       ceph-salt-formula
Requires:       salt-master >= 2019.2.0
Requires:       procps


%description
ceph-salt is a CLI tool for deploying Ceph clusters starting from version
Octopus.


%prep
%autosetup -n %{name}-%{version} -p1


%build
%py3_build


%install
%py3_install
%fdupes %{buildroot}%{python3_sitelib}
install -m 0755 -d %{buildroot}/%{_datadir}/%{name}

# ceph-salt-formula installation
%define fname ceph-salt
%define fdir  %{_datadir}/salt-formulas

mkdir -p %{buildroot}%{fdir}/states/
mkdir -p %{buildroot}%{fdir}/metadata/%{fname}/
cp -R ceph-salt-formula/salt/* %{buildroot}%{fdir}/states/
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
%{python3_sitelib}/ceph_salt*/
%{_bindir}/%{name}
%dir %{_datadir}/%{name}


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

