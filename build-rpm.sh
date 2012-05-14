#!/bin/bash

python2.7 ./setup.py sdist
cd rpmbuild/SPECS
rpmbuild -ba gottengeography.spec
