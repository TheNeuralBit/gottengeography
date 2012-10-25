#!/usr/bin/make -f

doctest:
	python3 -m doctest gg/*.py -v

check:
	nosetests-3.2 --with-doctest -v

flakes:
	pyflakes gottengeography setup.py gg test

lint:
	pylint --include-ids=y gg test -d \
		E0611,E1101,E1120,W0613,W0403,W0142,W0141,W0102,R0903

install:
	python3 setup.py install
