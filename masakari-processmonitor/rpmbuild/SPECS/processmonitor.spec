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

%prep

%setup -n %{name}

%build

%install
mkdir -p $RPM_BUILD_ROOT/etc/masakari/
mkdir -p $RPM_BUILD_ROOT/opt/masakari/
mkdir -p $RPM_BUILD_ROOT/opt/masakari/processmonitor
mkdir -p $RPM_BUILD_ROOT/etc/init/
install -m 755 processmonitor/*.sh $RPM_BUILD_ROOT/opt/masakari/processmonitor/
install -m 755 etc/masakari-processmonitor.conf.sample $RPM_BUILD_ROOT/etc/masakari/
install -m 755 etc/proc.list.sample $RPM_BUILD_ROOT/etc/masakari/
install -m 755 init/masakari-processmonitor.conf $RPM_BUILD_ROOT/etc/init/

%clean
rm -rf $RPM_BUILD_ROOT

%files
%defattr(-,root,root)
/opt/masakari/processmonitor/*.sh
/etc/init/masakari-processmonitor.conf
/etc/masakari/masakari-processmonitor.conf.sample
/etc/masakari/proc.list.sample
%changelog
