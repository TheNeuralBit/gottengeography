check:
	nosetests-2.7 --with-doctest -v

lint:
	pylint -d E0611,E1101,E1120,W0613,W0403,W0142,W0141,W0102,R0903 \
               --include-ids=y gg test

install:
	python setup.py install
