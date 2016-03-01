Summary: masakari-processmonitor
Name: masakari-processmonitor
Version: 1.0.0
Release: 1
License: ASL 2.0
Group: System Environment/Daemons
Source0: masakari-processmonitor.tar.gz
URL: https://github.com/ntt-sic/masakari
BuildRoot: /var/tmp/%{name}-buildroot
Requires: bash
Vendor: NTT Software Innovation Center <openstack@lab.ntt.co.jp>
Packager: NTT Software Innovation Center <openstack@lab.ntt.co.jp>

%description
masakari-processmonitor for vmha

%define debug_package %{nil}

%prep

%setup -n %{name}

%build

%install
mkdir -p $RPM_BUILD_ROOT/etc/masakari/
mkdir -p $RPM_BUILD_ROOT/opt/masakari/
mkdir -p $RPM_BUILD_ROOT/opt/masakari/processmonitor
mkdir -p $RPM_BUILD_ROOT/etc/init/
mkdir -p $RPM_BUILD_ROOT/var/log/masakari/
mkdir -p $RPM_BUILD_ROOT/etc/systemd/system/
install -m 755 processmonitor/*.sh $RPM_BUILD_ROOT/opt/masakari/processmonitor/
install -m 755 etc/masakari-processmonitor.conf.sample $RPM_BUILD_ROOT/etc/masakari/
install -m 755 etc/proc.list.sample $RPM_BUILD_ROOT/etc/masakari/
install -m 755 etc/systemd/system/masakari-processmonitor.service $RPM_BUILD_ROOT/etc/systemd/system/

%clean
rm -rf $RPM_BUILD_ROOT

%files
%defattr(-,root,root)
/opt/masakari/processmonitor/*.sh
/etc/masakari/masakari-processmonitor.conf.sample
/etc/masakari/proc.list.sample
/etc/systemd/system/masakari-processmonitor.service
%attr(755,openstack,openstack) /var/log/masakari/
%changelog
