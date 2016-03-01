%define name masakari-controller
Summary: %{name}
Name: %{name}
Version: 1.0.0
Release: 1
License: ASL 2.0
Group: System Environment/Daemons
Source0: masakari-controller.tar.gz
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
python setup.py install --single-version-externally-managed -O1 --root=$RPM_BUILD_ROOT --record=INSTALLED_FILES
install -m 755 etc/systemd/system/masakari-controller.service $RPM_BUILD_ROOT/etc/systemd/system/

%clean
rm -rf $RPM_BUILD_ROOT

%files -f INSTALLED_FILES
%defattr(-,root,root)
/etc/systemd/system/
%attr(755,openstack,openstack) /var/log/masakari/
