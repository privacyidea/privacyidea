info:
	@echo "make clean        	 - remove all automatically created files"
	@echo "make doc-man          - create the documentation as man-page"
	@echo "make doc-html         - create the documentation as html"
	@echo "make pypi             - upload package to pypi"
	@echo "make translate        - translate WebUI"
	@echo "make translate-server - translate string in the server code."

	
SIGNING_KEY=53E66E1D2CABEFCDB1D3B83E106164552E8D8149

clean:
	find . -name \*.pyc -exec rm {} \;
	rm -fr build/
	rm -fr dist/
	rm -fr cover
	rm -f .coverage
	(cd doc; make clean)

setversion:
	vim Makefile
	vim setup.py
	vim doc/conf.py
	vim Changelog
	@echo "!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!"
	@echo "Please set a tag like:  git tag 3.17"

translate:
	grunt nggettext_extract
	for language in de nl ; do \
		(cd po; msgmerge $$language.po template.pot > tmp.po; mv tmp.po $$language.po) ; \
	done
	# Especially edit German language
	poedit po/de.po
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

