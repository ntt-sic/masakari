%define name masakari-controller
%define version 1.0.0
%define unmangled_version 1.0.0
%define unmangled_version 1.0.0
%define release 1

Summary: UNKNOWN
Name: %{name}
Version: %{version}
Release: %{release}
Source0: %{name}.tar.gz
License: ASL 2.0
Group: System Environment/Daemons
BuildRoot: /var/tmp/%{name}-buildroot
Prefix: %{_prefix}
BuildArch: noarch
Vendor: NTT Software Innovation Center <openstack@lab.ntt.co.jp>
Packager: NTT Software Innovation Center <openstack@lab.ntt.co.jp>
Url: https://github.com/ntt-sic/masakari

%description

%define debug_package %{nil}

%prep
%setup -n %{name}-%{unmangled_version} -n %{name}-%{unmangled_version}

%build
python setup.py build

%install
mkdir -p $RPM_BUILD_ROOT/var/log/masakari/
python setup.py install --single-version-externally-managed -O1 --root=$RPM_BUILD_ROOT --record=INSTALLED_FILES

install -m 755 etc/systemd/system/masakari-controller.service $RPM_BUILD_ROOT/etc/systemd/system/


%clean
rm -rf $RPM_BUILD_ROOT

%files -f INSTALLED_FILES
%defattr(-,root,root)
%attr(755,openstack,openstack) /var/log/masakari/
