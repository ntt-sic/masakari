%define name masakari-instancemonitor
Summary: %{name}
Name: %{name}
Version: 1.0.0
Release: 1
License: ASL 2.0
Group: System Environment/Daemons
Source0: masakari-instancemonitor.tar.gz
Url: https://github.com/ntt-sic/masakari
BuildRoot: /var/tmp/%{name}-buildroot
Vendor: NTT Software Innovation Center <openstack@lab.ntt.co.jp>
Packager: NTT Software Innovation Center <openstack@lab.ntt.co.jp>

%description

%define debug_package %{nil}

%prep
%setup -n %{name} -n %{name}

%build
python setup.py build

%install
mkdir -p $RPM_BUILD_ROOT/var/log/masakari/
mkdir -p $RPM_BUILD_ROOT/etc/systemd/system/
mkdir -p $RPM_BUILD_ROOT/etc/masakari/
python setup.py install --single-version-externally-managed -O1 --root=$RPM_BUILD_ROOT --record=INSTALLED_FILES
install -m 664 etc/systemd/system/masakari-instancemonitor.service $RPM_BUILD_ROOT/etc/systemd/system/
install -m 755 etc/masakari-instancemonitor.conf.sample $RPM_BUILD_ROOT/etc/masakari/
%clean
rm -rf $RPM_BUILD_ROOT

%files -f INSTALLED_FILES
%defattr(-,root,root)
%dir /etc/systemd/system/
/etc/systemd/system/masakari-instancemonitor.service
%dir /etc/masakari/
/etc/masakari/masakari-instancemonitor.conf.sample
%dir %attr(755,openstack,openstack) /var/log/masakari/
