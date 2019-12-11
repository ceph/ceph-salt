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
Version:        0.0.1
Release:        1%{?dist}
Summary:        CLI tool to deploy Ceph clusters
License:        MIT
%if 0%{?suse_version}
Group:          System/Management
%endif
URL:            https://github.com/SUSE/ceph-bootstrap
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

%files
%license LICENSE
%doc CHANGELOG.md README.md
%{python3_sitelib}/ceph_bootstrap*/
%{_bindir}/ceph-bootstrap

%changelog

