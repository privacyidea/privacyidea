CONTRIB1=python-flask-cache
URL1=https://pypi.python.org/packages/source/F/Flask-Cache/Flask-Cache-0.13.1.tar.gz
VERSION1=0.13.1

CONTRIB2=python-pyjwt
URL2=https://pypi.python.org/packages/source/P/PyJWT/PyJWT-0.4.3.tar.gz
VERSION2=0.4.3

CONTRIB3=python-ldap3
URL3=https://pypi.python.org/packages/source/l/ldap3/ldap3-0.9.8.4.tar.gz
VERSION3=0.9.8.4

CONTRIB4=python-flask-sqlalchemy
URL4=https://pypi.python.org/packages/source/F/Flask-SQLAlchemy/Flask-SQLAlchemy-2.0.tar.gz
VERSION4=2.0

ME=Cornelius Kölbel <cornelius@privacyidea.org>

info:
	@echo "make ubuntu  - build packages for ubuntu 14.04LTS"
	@echo "make ppa-dev - upload to ppa devel"
	@echo "make ppa     - upload to ppa"
	@echo "make clean."

ubuntu:
	make clean
	make pyjwt
	make flask-cache
	make ldap3
	make flask-sqlalchemy

ldap3:
	mkdir -p $(CONTRIB3)
	mkdir -p DEBUILD
	(cd $(CONTRIB3); curl $(URL3) -o ldap3-$(VERSION3).tar.gz)
	(cd $(CONTRIB3); py2dsc -m '$(ME)' ldap3-$(VERSION3).tar.gz)
	(cd $(CONTRIB3)/deb_dist/ldap3-$(VERSION3); dch -v $(VERSION3)-1$(series)1 --distribution $(series) -M "built for privacyidea")
	(cd $(CONTRIB3)/deb_dist/ldap3-$(VERSION3); debuild -sa -S)
	(cd $(CONTRIB3)/deb_dist/ldap3-$(VERSION3); debuild -b)
	(cp $(CONTRIB3)/deb_dist/* DEBUILD || true)


pyjwt:
	mkdir -p $(CONTRIB2)
	mkdir -p DEBUILD
	(cd $(CONTRIB2); curl $(URL2) -o pyjwt-$(VERSION2).tar.gz)
	(cd $(CONTRIB2); py2dsc -m '$(ME)' pyjwt-$(VERSION2).tar.gz)
	(cd $(CONTRIB2)/deb_dist/pyjwt-$(VERSION2); dch -v $(VERSION2)-1$(series)1 --distribution $(series) -M "built for privacyidea")
	(cd $(CONTRIB2)/deb_dist/pyjwt-$(VERSION2); debuild -sa -S)
	(cd $(CONTRIB2)/deb_dist/pyjwt-$(VERSION2); debuild -b)
	(cp $(CONTRIB2)/deb_dist/* DEBUILD || true)


flask-cache:
	mkdir -p $(CONTRIB1)
	mkdir -p DEBUILD
	(cd $(CONTRIB1); curl $(URL1) -o flask-cache-$(VERSION1).tar.gz) 
	(cd $(CONTRIB1); py2dsc -m '$(ME)' flask-cache-$(VERSION1).tar.gz)
	(cd $(CONTRIB1)/deb_dist/flask-cache-$(VERSION1); dch -v $(VERSION1)-1$(series)1 --distribution $(series) -M "built for privacyidea")
	(cd $(CONTRIB1)/deb_dist/flask-cache-$(VERSION1); debuild -sa -S)
	(cd $(CONTRIB1)/deb_dist/flask-cache-$(VERSION1); debuild -b)
	(cp $(CONTRIB1)/deb_dist/* DEBUILD || true)

flask-sqlalchemy:
	mkdir -p $(CONTRIB4)
	mkdir -p DEBUILD
	(cd $(CONTRIB4); curl $(URL4) -o flask-sqlalchemy-$(VERSION4).tar.gz) 
	(cd $(CONTRIB4); py2dsc -m '$(ME)' flask-sqlalchemy-$(VERSION4).tar.gz)
	(cd $(CONTRIB4)/deb_dist/flask-sqlalchemy-$(VERSION4); dch -v $(VERSION4)-1$(series)1 --distribution $(series) -M "built for privacyidea")
	(cd $(CONTRIB4)/deb_dist/flask-sqlalchemy-$(VERSION4); debuild -sa -S)
	(cd $(CONTRIB4)/deb_dist/flask-sqlalchemy-$(VERSION4); debuild -b)
	(cp $(CONTRIB4)/deb_dist/* DEBUILD || true)


ppa-dev:
	dput -f ppa:privacyidea/privacyidea-dev DEBUILD/flask-cache_${VERSION1}-*_source.changes || true
	dput -f ppa:privacyidea/privacyidea-dev DEBUILD/pyjwt_${VERSION2}-*_source.changes || true
	dput -f ppa:privacyidea/privacyidea-dev DEBUILD/ldap3_${VERSION3}-*_source.changes || true
	dput -f ppa:privacyidea/privacyidea-dev DEBUILD/flask-sqlalchemy_${VERSION4}-*_source.changes || true

ppa:
	dput -f ppa:privacyidea/privacyidea DEBUILD/flask-cache_${VERSION1}-*_source.changes || true
	dput -f ppa:privacyidea/privacyidea DEBUILD/pyjwt_${VERSION2}-*_source.changes || true
	dput -f ppa:privacyidea/privacyidea DEBUILD/ldap3_${VERSION3}-*_source.changes || true
	dput -f ppa:privacyidea/privacyidea DEBUILD/flask-sqlalchemy_${VERSION4}-*_source.changes || true

	

clean:
	rm -fr $(CONTRIB1)
	rm -fr $(CONTRIB2)
	rm -fr $(CONTRIB3)
	rm -fr $(CONTRIB4)
	rm -fr DEBUILD
