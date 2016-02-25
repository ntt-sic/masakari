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

%prep

%setup -n %{name}

%build

%install
mkdir -p $RPM_BUILD_ROOT/etc/masakari/
mkdir -p $RPM_BUILD_ROOT/opt/masakari/
mkdir -p $RPM_BUILD_ROOT/opt/masakari/hostmonitor/
mkdir -p $RPM_BUILD_ROOT/etc/init.d/
install -m 755 hostmonitor/masakari-hostmonitor.sh $RPM_BUILD_ROOT/opt/masakari/hostmonitor/
install -m 755 etc/masakari-hostmonitor.conf.sample $RPM_BUILD_ROOT/etc/masakari/
install -m 755 init.d/masakari-hostmonitor $RPM_BUILD_ROOT/etc/init.d/

%clean
rm -rf $RPM_BUILD_ROOT

%files
%defattr(-,root,root)
/opt/masakari/hostmonitor/masakari-hostmonitor.sh
/etc/init.d/masakari-hostmonitor
/etc/masakari/masakari-hostmonitor.conf.sample

%changelog
