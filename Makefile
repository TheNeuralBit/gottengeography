#!/usr/bin/make -f

doctest:
	nosetests3 --with-doctest gg/ -v

nose:
	nosetests3 --with-doctest -v

flakes:
	pyflakes gottengeography setup.py gg test

lint:
	pylint --include-ids=y gg test -d \
		E0611,E1101,E1120,W0613,W0403,W0142,W0141,W0102,R0903

install:
	python3 setup.py install

clean:
	rm -rf build/ *.egg-info/

# TODO Clean up the testsuite enough to include it here for automated
# tests during package building.
check: flakes # nose
