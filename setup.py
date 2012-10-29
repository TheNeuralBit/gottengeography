#!/usr/bin/python3

from sys import argv
from os.path import join
from distutils.core import setup
from subprocess import Popen, PIPE

from DistUtilsExtra.command import build_extra, build_i18n, build_help
from distutils.command.install_data import install_data as _install_data
from distutils.command.build_py import build_py as _build_py
from distutils.command.install import install

from gg.version import PACKAGE, VERSION, AUTHOR, EMAIL


root = '--root' in ' '.join(argv)


data_files = [
    ('/usr/share/icons/hicolor/scalable/apps', ['data/%s.svg' % PACKAGE]),
    ('/usr/share/glib-2.0/schemas', ['data/ca.%s.gschema.xml' % PACKAGE]),
    ('/usr/share/applications', ['data/%s.desktop' % PACKAGE]),
    ('share/doc/' + PACKAGE, ['README.md', 'AUTHORS', 'THANKS']),
    ('share/' + PACKAGE, ['data/cities.txt', 'data/trackfile.ui', 'data/camera.ui',
        'data/%s.ui' % PACKAGE, 'data/%s.svg' % PACKAGE])
]


build_info_template = """# -*- coding: UTF-8 -*-

# Distutils installation details:
PREFIX='%s'
PKG_DATA_DIR='%s'
REVISION='Version %s'
"""


class build_py(_build_py):
    """Clobber gg/build_info.py with the real package data dir.

    Inspired by a distutils-sig posting by Wolodja Wentland in Sept 2009.
    """
    def build_module(self, module, module_file, package):
        if (module_file == 'gg/build_info.py'):
            try:
                iobj = self.distribution.command_obj['install']
                with open(module_file, 'w') as module_fp:
                    module_fp.write(build_info_template % (
                        iobj.prefix,
                        join(iobj.prefix, 'share', PACKAGE),
                        VERSION if root else Popen(('git', 'describe'),
                            stdout=PIPE).communicate()[0].strip()
                    ))
            except KeyError:
                pass

        _build_py.build_module(self, module, module_file, package)


# If the --root option has been specified, then most likely we are installing
# to a fakeroot, eg, when a debian package is being made. In this case, don't
# override install_data at all. If --root has NOT been specified, eg, during
# a default install to the user's system, then we need to override install_data
# to call glib-compile-schemas. If we don't do this, then the program won't
# actually run after it's been installed, because GSettings is quite fussy
# about this.
if root:
    install_data = _install_data
else:
    class install_data(_install_data):
        """Compile GLib schemas so that our GSettings schema works."""
        def run(self):
            _install_data.run(self)
            command = ('glib-compile-schemas', '/usr/share/glib-2.0/schemas/')
            print(' '.join(command))
            Popen(command, stdout=PIPE, stderr=PIPE).communicate()


# Allow non-Ubuntu distros to ignore install_layout option from setup.cfg
if not hasattr(install, 'install_layout'):
    setattr(install, 'install_layout', None)


setup(
    name=PACKAGE,
    version=VERSION,
    description='Automagically geotag photos with GPX data.',
    long_description=
"""GottenGeography is a GNOME application that aims to make it easy to record
geotags into your photographs. If you have a GPS device, GottenGeography can
load it's GPX data and directly compare timestamps between the GPX data and the
photos, automatically determining where each photo was taken. If you do not have
a GPS device, GottenGeography allows you to manually place photos onto a map,
and then record those locations into the photos.
""",
    author=AUTHOR,
    author_email=EMAIL,
    url='http://gottengeography.ca',
    download_url='https://github.com/robru/gottengeography/downloads',
    license='GPLv3',
    packages=['gg'],
    scripts=['gottengeography'],
    data_files=data_files,
    cmdclass = { 'build': build_extra.build_extra,
                 'build_i18n': build_i18n.build_i18n,
                 'build_help': build_help.build_help,
                 'build_py': build_py,
                 'install': install,
                 'install_data': install_data }
)
