Name: gottengeography
Version: 2.0
Release: 1%{?dist}
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
/bin/touch --no-create %{_datadir}/icons/hicolor &>/dev/null || :
if [ $1 -ge 1 ]; then
    /usr/bin/glib-compile-schemas %{_datadir}/glib-2.0/schemas &> /dev/null || :
fi

%postun
if [ $1 -eq 0 ]; then
    /bin/touch --no-create %{_datadir}/icons/hicolor &>/dev/null || :
    /usr/bin/gtk-update-icon-cache -f %{_datadir}/icons/hicolor &>/dev/null || :
    /usr/bin/glib-compile-schemas %{_datadir}/glib-2.0/schemas &> /dev/null || :
fi

%posttrans
/usr/bin/gtk-update-icon-cache -f %{_datadir}/icons/hicolor &>/dev/null || :

%changelog
* Thu Jun 28 2012 Robert Park <rbpark@exolucere.ca> - 2.0-1
- Major UI overhaul, allowing for per-camera and per-trackfile config
- Added Mallard help docs with basic tutorial including screenshots
- Massive improvement in testsuite coverage
- Convert to GtkApplication, enforcing single-instance UI
- Start using Gnome Shell menu
- Reduce some incompatibity with Python 2.6
- Updated geonames.org db dump
- Major performance enhancements, UI feels significantly more responsive
- Improve drag&drop accuracy
- More timezones available in the manual timezone selector
- Allow choosing UTC offsets as well as timezones
- Add support for CSV, and Garmin TCX
- Huge expansion in use of GObject properties/signals to automate things
- New animation when you search for a city
- Fixed a segfault when closing photos
- Implement general-purpose memoizer for performance, used in a few places
- Converted testsuite to Nose
- Allow multiple photos during drag & drop
- Use GtkInfoBar instead of GtkStatusBar
- No more preferences dialog


* Wed May 23 2012 Robert Park <rbpark@exolucere.ca> - 1.3-1
- Major module refactoring, enhances readability and maintainability
- Module cleanup, put data files in a more standard location
- Alter Google Maps link to honor the current zoom level
- Run glib-compile-schemas, gtk-update-icon-cache in post scripts
- Remember last-used window size on app launch
- Added geoname data to window titlebar
- Convert to GSettings
- Add new application icon
- Fix OpenCycleMap
- Increase testsuite coverage

* Sun May 13 2012 Robert Park <rbpark@exolucere.ca> - 1.2.1-1
- Remember the last used map source each run
- Make the map source selector indicate which map source is in use
- Updated translations


