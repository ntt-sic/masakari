Summary: masakari-hostmonitor
Name: masakari-hostmonitor
Version: 1.0.0
Release: 1
License: ASL 2.0
Group: System Environment/Daemons
Source0: masakari-hostmonitor.tar.gz
URL: https://github.com/ntt-sic/masakari
BuildRoot: /var/tmp/%{name}-buildroot
Requires: bash
Vendor: NTT Software Innovation Center <openstack@lab.ntt.co.jp>
Packager: NTT Software Innovation Center <openstack@lab.ntt.co.jp>

%description
masakari hostmonitor for vmha

%define debug_package %{nil}
%prep

%setup -n %{name}

%build

%install
mkdir -p $RPM_BUILD_ROOT/etc/masakari/
mkdir -p $RPM_BUILD_ROOT/opt/masakari/
mkdir -p $RPM_BUILD_ROOT/opt/masakari/hostmonitor/
mkdir -p $RPM_BUILD_ROOT/var/log/masakari/
mkdir -p $RPM_BUILD_ROOT/etc/systemd/system/
install -m 755 hostmonitor/masakari-hostmonitor.sh $RPM_BUILD_ROOT/opt/masakari/hostmonitor/
install -m 755 etc/masakari-hostmonitor.conf.sample $RPM_BUILD_ROOT/etc/masakari/
install -m 755 etc/systemd/system/masakari-hostmonitor.service $RPM_BUILD_ROOT/etc/systemd/system/

%clean
rm -rf $RPM_BUILD_ROOT

%files
%defattr(-,root,root)
%dir /opt/masakari/
/opt/masakari/hostmonitor/masakari-hostmonitor.sh
%dir /etc/systemd/system/
/etc/systemd/system/masakari-hostmonitor.service
%dir /etc/masakari/
/etc/masakari/masakari-hostmonitor.conf.sample
%dir %attr(755,openstack,openstack) /var/log/masakari/

%changelog
