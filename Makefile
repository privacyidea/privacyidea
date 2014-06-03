info:
	@echo "make translate - collect new strings and translate them"
	@echo "make clean - remove all automatically created files"
	@echo "make epydoc - create the API documentation"
	@echo "make pypi - upload package to pypi"

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

pypi:
	python setup.py sdist upload

epydoc:
	#pydoctor --add-package privacyidea --make-html 
	epydoc --html privacyidea -o API
depdoc:
	#sfood privacyidea | sfood-graph | dot -Tpng -o graph.png	
	dot -Tpng dependencies.dot -o dependencies.png
