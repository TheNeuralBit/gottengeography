#!/bin/bash

python2.7 ./setup.py sdist
mkdir -p rpmbuild/SOURCES
mv dist/* rpmbuild/SOURCES
cd rpmbuild/SPECS
rpmbuild -ba gottengeography.spec
cd ../..
mv rpmbuild/RPMS/noarch/* dist/

