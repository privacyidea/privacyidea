info:
	@echo "make translate    - collect new strings and translate them"
	@echo "make clean        - remove all automatically created files"
	@echo "make epydoc       - create the API documentation"
	@echo "make doc-man      - create the documentation as man-page"
	@echo "make pypi         - upload package to pypi"
	@echo "make debianzie    - prepare the debian build environment in DEBUILD"
	@echo "make builddeb     - build .deb file locally on ubuntu 14.04!"
	@echo "make ppa-dev      - upload to launchpad development repo"
	
VERSION=1.2

translate:
	# according to http://docs.pylonsproject.org/projects/pylons-webframework/en/latest/i18n.html#using-babel
	# To add a new translation do:
	# python setip.py init_catalog -l es
	python setup.py extract_messages
	(cd privacyidea/i18n; msgmerge de/LC_MESSAGES/privacyidea.po privacyidea.pot > de.po; cp de.po de/LC_MESSAGES/privacyidea.po)
#	python setup.py init_catalog -l de
	gtranslator privacyidea/i18n/de/LC_MESSAGES/privacyidea.po
	python setup.py compile_catalog
clean:
	find . -name \*.pyc -exec rm {} \;
	rm -fr config/data
	rm -fr build/
	rm -fr dist/
	rm -fr privacyIDEA.egg-info/
	rm -fr API
	rm -fr privacyidea/tests/testdata/data/
	rm -fr DEBUILD

pypi:
	make doc-man
	python setup.py sdist upload

epydoc:
	#pydoctor --add-package privacyidea --make-html 
	epydoc --html privacyidea -o API
depdoc:
	#sfood privacyidea | sfood-graph | dot -Tpng -o graph.png	
	dot -Tpng dependencies.dot -o dependencies.png

doc-man:
	(cd doc; make man)

debianize:
	make doc-man
	rm -fr DEBUILD
	rm -fr build
	mkdir -p DEBUILD/privacyidea.org
	cp -r * DEBUILD/privacyidea.org || true
	# pylons TEST ARE BREAKING with pylons 1.0.1! Only allow 1.0.1 for debian package!
	sed s/'"Pylons>=0.9.7,<=1.0",'/'"Pylons>=0.9.7",'/g setup.py > DEBUILD/privacyidea.org/setup.py
	# We need to touch this, so that our config files 
	# are written to /etc
	touch DEBUILD/privacyidea.org/PRIVACYIDEA_DEBIAN_PACKAGE
	cp LICENSE DEBUILD/privacyidea.org/debian/copyright
	(cd DEBUILD; tar -zcf privacyidea_${VERSION}.orig.tar.gz --exclude=privacyidea.org/debian  privacyidea.org)

builddeb:
	make debianize
	(cd DEBUILD/privacyidea.org; debuild)

ppa-dev:
	make debianize
	(cd DEBUILD/privacyidea.org; debuild -S)
	# Upload to launchpad:
	dput ppa:privacyidea/privacyidea-dev DEBUILD/privacyidea_${VERSION}-?_source.changes

ppa:
	make debianize
	(cd DEBUILD/privacyidea.org; debuild -S)
	dput ppa:privacyidea/privacyidea DEBUILD/privacyidea_${VERSION}-?_source.changes
	
