#!/usr/bin/make -f

build:
	python3 setup.py build

# TODO Clean up the testsuite enough to include it here for automated
# tests during package building.
check: flakes nose

autopilot:
	cd ./test; autopilot run gottengeography_autopilot

doctest:
	python3 -m nose --with-doctest gg/ -v

nose:
	python3 -m nose tests/ --with-coverage --cover-package=gg

flakes:
	pyflakes gottengeography setup.py gg tests

lint:
	pylint --include-ids=y gg test -d \
		E0611,E1101,E1120,W0613,W0403,W0142,W0141,W0102,R0903

install:
	python3 setup.py install

clean:
	rm -rf build/ *.egg-info/

cities:
	wget -t 10 'http://download.geonames.org/export/dump/cities1000.zip'
	unzip -u cities1000.zip
	./tools/update_cities.py cities1000.txt > data/cities.txt
	rm -f cities1000.*

territories:
	wget -t 10 'http://download.geonames.org/export/dump/countryInfo.txt'
	wget -t 10 'http://download.geonames.org/export/dump/admin1CodesASCII.txt'
	./tools/update_territories.py > gg/territories.py
	rm -f countryInfo.txt admin1CodesASCII.txt

translations:
	bzr branch lp:~gottengeography/gottengeography/translations
	mv translations/po/*.po po/
	rm -rf translations
