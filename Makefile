info:
	@echo "make clean        - remove all automatically created files"
	@echo "make doc-man      - create the documentation as man-page"
	@echo "make doc-html     - create the documentation as html"
	@echo "make pypi         - upload package to pypi"
	@echo "make venvdeb      - build .deb file, that contains the whole setup in a virtualenv."
	@echo "make linitian     - run lintian on debian package"
	@echo "make translate    - translate WebUI"

	
#VERSION=1.3~dev5
SHORT_VERSION=3.0~dev3
#SHORT_VERSION=2.10~dev7
VERSION_JESSIE=${SHORT_VERSION}
VERSION=${SHORT_VERSION}
LOCAL_SERIES=`lsb_release -a | grep Codename | cut -f2`
SRCDIRS=deploy authmodules migrations doc tests tools privacyidea 
SRCFILES=setup.py MANIFEST.in Makefile Changelog LICENSE pi-manage requirements.txt
SIGNING_KEY=53E66E1D2CABEFCDB1D3B83E106164552E8D8149

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
#	(cd po; msgmerge it.po template.pot > tmp.po; mv tmp.po it.po)
	poedit po/de.po
#	poedit po/it.po
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
	rm -fr dist
	python setup.py sdist
	gpg --detach-sign -a --default-key ${SIGNING_KEY} dist/*.tar.gz
	twine upload dist/*.tar.gz dist/*.tar.gz.asc


depdoc:
	#sfood privacyidea | sfood-graph | dot -Tpng -o graph.png	
	dot -Tpng dependencies.dot -o dependencies.png

doc-man:
	(cd doc; make man)
	(cd doc/installation/system/pimanage; make man)

doc-html:
	(cd doc; make html)


venvdeb:
	make debianize
	cp -r deploy/debian-virtualenv/* DEBUILD/privacyidea.org/debian/
	sed -e s/"trusty) trusty; urgency"/"$(LOCAL_SERIES)) $(LOCAL_SERIES); urgency"/g deploy/debian-virtualenv/changelog > DEBUILD/privacyidea.org/debian/changelog
	(cd DEBUILD/privacyidea.org; DH_VIRTUALENV_INSTALL_ROOT=/opt/privacyidea dpkg-buildpackage -us -uc)

lintian:
	(cd DEBUILD; lintian -i -I --show-overrides python-privacyidea_2.*_amd64.changes)
