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

POS = $(wildcard po/*.po)
translate:
	grunt nggettext_extract
	for language in $(POS); do \
		msgmerge -U --backup=off $$language po/template.pot; \
	done
	grunt nggettext_compile

translate-server:
	(cd privacyidea; pybabel extract -F babel.cfg -k lazy_gettext -o messages.pot .)
	# pybabel init -i messages.pot -d translations -l de
	(cd privacyidea; pybabel update -i messages.pot -d translations)
	# create the .mo file
	(cd privacyidea; pybabel compile -d translations)

pypi:
	make doc-man
	rm -fr dist
	python setup.py sdist
	gpg --detach-sign -a --default-key ${SIGNING_KEY} dist/*.tar.gz
	twine upload dist/*.tar.gz dist/*.tar.gz.asc

doc-man:
	(cd doc; make man)

doc-html:
	(cd doc; make html)

NPM_VERSION := $(shell npm --version 2>/dev/null)

update-contrib:
ifdef NPM_VERSION
	(cd privacyidea/static && npm install && ./update_contrib.sh)
else
	@echo "Command 'npm' not found! It is needed to install the JS contrib libraries."
endif
