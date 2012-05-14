Name: gottengeography
Version: 1.2.1
Release: 2%{?dist}
Source0: %{name}-%{version}.tar.gz
License: GPLv3
Group: Applications/Archiving
BuildRoot: %{_tmppath}/%{name}-%{version}-%{release}-buildroot
Prefix: %{_prefix}
BuildArch: noarch
BuildRequires: python-distutils-extra intltool
Requires: python >= 2.7 pyexiv2 >= 0.3 pygobject3 >= 3.0.3 libchamplain-gtk >= 0.12.2 python-dateutil >= 1.5
Url: http://exolucere.ca/gottengeography
Requires(post):%{_bindir}/glib-compile-schemas
Summary: Automagically geotag photos with GPX data

%description
GottenGeography is a GNOME application that aims to make it easy to record
geotags into your photographs. If you have a GPS device, GottenGeography can
load it's GPX data and directly compare timestamps between the GPX data and the
photos, automatically determining where each photo was taken. If you do not have
a GPS device, GottenGeography allows you to manually place photos onto a map,
and then record those locations into the photos.

%prep
%setup -q

%build
python setup.py build

%install
python setup.py install -O1 --root=%{buildroot} --record=INSTALLED_FILES

%clean
rm -rf %{buildroot}

%files -f INSTALLED_FILES
%defattr(-,root,root)

%post
if [ $1 -ge 1 ]; then
   glib-compile-schemas %{_datadir}/glib-2.0/schemas &> /dev/null || :
fi

%postun
if [ $1 -eq 0 ]; then
   glib-compile-schemas %{_datadir}/glib-2.0/schemas &> /dev/null || :
fi

%changelog
* Mon May 14 2012 Robert Park <rbpark@exolucere.ca> - 1.3-1
- Convert to GSettings
- Run glib-compile-schemas in post scripts
- Added geoname data to window titlebar

* Sun May 13 2012 Robert Park <rbpark@exolucere.ca> - 1.2.1-1
- Remember the last used map source each run
- Make the map source selector indicate which map source is in use
- Updated translations


