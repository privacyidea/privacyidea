info:
	@echo "make clean        - remove all automatically created files"
	@echo "make epydoc       - create the API documentation"
	@echo "make doc-man      - create the documentation as man-page"
	@echo "make doc-html     - create the documentation as html"
	@echo "make pypi         - upload package to pypi"
	@echo "make debianzie    - prepare the debian build environment in DEBUILD"
	@echo "make builddeb     - build .deb file locally on ubuntu 14.04LTS!"
	@echo "make centos       - build .rpm file to be used with CentOS 7"
	@echo "make jessie	 - build .deb file for Debian Jessie"
	@echo "make venvdeb      - build .deb file, that contains the whole setup in a virtualenv."
	@echo "make linitian     - run lintian on debian package"
	@echo "make translate    - translate WebUI"
	@echo "                    This is to be used with debian Wheezy"
	@echo "make ppa-dev      - upload to launchpad development repo"
	@echo "make ppa          - upload to launchpad stable repo"
	
#VERSION=1.3~dev5
SHORT_VERSION=2.19
#SHORT_VERSION=2.10~dev7
VERSION_JESSIE=${SHORT_VERSION}
VERSION=${SHORT_VERSION}
LOCAL_SERIES=`lsb_release -a | grep Codename | cut -f2`
SRCDIRS=deploy authmodules migrations doc tests tools privacyidea 
SRCFILES=setup.py MANIFEST.in Makefile Changelog LICENSE pi-manage requirements.txt

clean:
	find . -name \*.pyc -exec rm {} \;
	rm -fr build/
	rm -fr dist/
	rm -fr DEBUILD
	rm -fr RHBUILD
	rm -fr cover
	rm -f .coverage
	(cd doc; make clean)

setversion:
	vim Makefile
	vim setup.py
	vim deploy/debian-ubuntu/changelog
	vim deploy/debian-virtualenv/changelog
	vim doc/conf.py
	vim Changelog
	@echo "!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!"
	@echo "Please set a tag like:  git tag 3.17"

translate:
	grunt nggettext_extract
	(cd po; msgmerge de.po template.pot > tmp.po; mv tmp.po de.po)
	(cd po; msgmerge it.po template.pot > tmp.po; mv tmp.po it.po)
	poedit po/de.po
	poedit po/it.po
	grunt nggettext_compile

translate-server:
	(cd privacyidea; pybabel extract -F babel.cfg -o messages.pot .)
	# pybabel init -i messages.pot -d translations -l de
	(cd privacyidea; pybabel update -i messages.pot -d translations)
	(poedit privacyidea/translations/de/LC_MESSAGES/messages.po)
	# create the .mo file
	(cd privacyidea; pybabel compile -d translations)

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
	(cd doc/installation/system/pimanage; make man)

doc-html:
	(cd doc; make html)

centos:
	make clean
	mkdir RHBUILD
	mkdir -p RHBUILD/{BUILD,RPMS,SOURCES,SPECS,SRPMS}
	# create tarball
	mkdir -p RHBUILD/SOURCES/privacyidea-${VERSION}
	rsync -a --exclude=".*" --exclude="privacyIDEA.egg-info" --exclude="RHBUILD" --exclude="debian" --exclude="dist" --exclude="build" \
                --exclude="tests" . RHBUILD/SOURCES/privacyidea-${VERSION} || true
	# We are using the same config file as in debia an replace it in setup.py
	cp deploy/centos/pi.cfg RHBUILD/SOURCES/privacyidea-${VERSION}/deploy/centos/
	# pack the modified source
	(cd RHBUILD/SOURCES/; tar -zcf privacyidea-${VERSION}.tar.gz privacyidea-${VERSION})
	rm -fr RHBUILD/SOURCES/privacyidea-${VERSION}
	# copy spec file
	cp deploy/centos/privacyidea.spec RHBUILD/SPECS
	# build it
	rpmbuild --define "_topdir $(CURDIR)/RHBUILD" -ba RHBUILD/SPECS/privacyidea.spec


debianize:
	make clean
	make doc-man
	mkdir -p DEBUILD/privacyidea.org/debian
	cp -r ${SRCDIRS} ${SRCFILES} DEBUILD/privacyidea.org || true
	# remove the requirement for pyOpenSSL otherwise we get a breaking dependency for trusty
	grep -v pyOpenSSL setup.py > DEBUILD/privacyidea.org/setup.py
	# We need to touch this, so that our config files 
	# are written to /etc
	touch DEBUILD/privacyidea.org/PRIVACYIDEA_PACKAGE
	cp LICENSE DEBUILD/privacyidea.org/debian/copyright
	cp LICENSE DEBUILD/privacyidea.org/debian/python-privacyidea.copyright
	cp LICENSE DEBUILD/privacyidea.org/debian/privacyidea-all.copyright
	cp authmodules/FreeRADIUS/copyright DEBUILD/privacyidea.org/debian/privacyidea-radius.copyright
	cp authmodules/simpleSAMLphp/LICENSE DEBUILD/privacyidea.org/debian/privacyidea-simplesamlphp.copyright
	(cd DEBUILD; tar -zcf python-privacyidea_${SHORT_VERSION}.orig.tar.gz --exclude=privacyidea.org/debian privacyidea.org)
	(cd DEBUILD; tar -zcf python-privacyidea_${VERSION}.orig.tar.gz --exclude=privacyidea.org/debian privacyidea.org)
	(cd DEBUILD; tar -zcf python-privacyidea_${VERSION_JESSIE}.orig.tar.gz --exclude=privacyidea.org/debian privacyidea.org)
	(cd DEBUILD; tar -zcf privacyidea-venv_${VERSION}.orig.tar.gz --exclude=privacyidea.org/debian privacyidea.org)

builddeb-nosign:
	make debianize
	cp -r deploy/debian-ubuntu/* DEBUILD/privacyidea.org/debian/
	sed -e s/"trusty) trusty; urgency"/"$(LOCAL_SERIES)) $(LOCAL_SERIES); urgency"/g deploy/debian-ubuntu/changelog > DEBUILD/privacyidea.org/debian/changelog
	(cd DEBUILD/privacyidea.org; debuild -b -i -us -uc)

builddeb:
	make debianize
	################## Renew the changelog
	cp -r deploy/debian-ubuntu/* DEBUILD/privacyidea.org/debian/
	sed -e s/"trusty) trusty; urgency"/"$(LOCAL_SERIES)) $(LOCAL_SERIES); urgency"/g deploy/debian-ubuntu/changelog > DEBUILD/privacyidea.org/debian/changelog
	################# Build
	(cd DEBUILD/privacyidea.org; debuild --no-lintian)

jessie:
	make debianize
	cp -r deploy/debian-jessie/* DEBUILD/privacyidea.org/debian/
	(cd DEBUILD/privacyidea.org; debuild --no-lintian)

venvdeb:
	make debianize
	cp -r deploy/debian-virtualenv/* DEBUILD/privacyidea.org/debian/
	sed -e s/"trusty) trusty; urgency"/"$(LOCAL_SERIES)) $(LOCAL_SERIES); urgency"/g deploy/debian-virtualenv/changelog > DEBUILD/privacyidea.org/debian/changelog
	(cd DEBUILD/privacyidea.org; DH_VIRTUALENV_INSTALL_ROOT=/opt/privacyidea dpkg-buildpackage -us -uc)

lintian:
	(cd DEBUILD; lintian -i -I --show-overrides python-privacyidea_2.*_amd64.changes)

ppa-dev:
	make debianize
	# trusty
	cp -r deploy/debian-ubuntu/* DEBUILD/privacyidea.org/debian/
	(cd DEBUILD/privacyidea.org; debuild -sa -S)
	# xenial
	sed -e s/"trusty) trusty; urgency"/"xenial) xenial; urgency"/g deploy/debian-ubuntu/changelog > DEBUILD/privacyidea.org/debian/changelog
	(cd DEBUILD/privacyidea.org; debuild -sa -S)
	dput ppa:privacyidea/privacyidea-dev DEBUILD/python-privacyidea_${VERSION}*_source.changes


ppa:
	make debianize
	# trusty
	cp deploy/debian-ubuntu/changelog DEBUILD/privacyidea.org/debian/
	cp -r deploy/debian-ubuntu/* DEBUILD/privacyidea.org/debian/
	(cd DEBUILD/privacyidea.org; debuild -sa -S)
	# xenial
	sed -e s/"trusty) trusty; urgency"/"xenial) xenial; urgency"/g deploy/debian-ubuntu/changelog > DEBUILD/privacyidea.org/debian/changelog
	(cd DEBUILD/privacyidea.org; debuild -sa -S)
	dput ppa:privacyidea/privacyidea DEBUILD/python-privacyidea_${VERSION}*_source.changes
