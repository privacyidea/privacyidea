CONTRIB1=python-flask-cache
VERSION1=0.13.1
URL1=https://pypi.python.org/packages/source/F/Flask-Cache/Flask-Cache-$(VERSION1).tar.gz

CONTRIB2=python-pyjwt
VERSION2=1.3.0
URL2=https://pypi.python.org/packages/source/P/PyJWT/PyJWT-$(VERSION2).tar.gz

CONTRIB3=python-ldap3
VERSION3=2.1.1
URL3=https://pypi.python.org/packages/f8/15/f8a33118b8e909e3953e5d9db6459693754ea42ae2aa481f4cab12e68c67/ldap3-$(VERSION3).tar.gz

CONTRIB4=python-flask-sqlalchemy
VERSION4=2.0
URL4=https://pypi.python.org/packages/source/F/Flask-SQLAlchemy/Flask-SQLAlchemy-$(VERSION4).tar.gz

CONTRIB5=python-pymysql
VERSION5=0.7.1
URL5=https://pypi.python.org/packages/source/P/PyMySQL/PyMySQL-$(VERSION5).tar.gz

CONTRIB6=python-pymysql_sa
VERSION6=1.0
URL6=https://pypi.python.org/packages/source/p/pymysql_sa/pymysql_sa-$(VERSION6).tar.gz

CONTRIB7=PyKCS
VERSION7=1.3.2
URL7=https://pypi.python.org/packages/source/p/pykcs11/PyKCS11-$(VERSION7).tar.gz

ME=Cornelius Kölbel <cornelius@privacyidea.org>

#series=trusty
series=xenial

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
	make pymysql

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
	(cd $(CONTRIB2); curl $(URL2) -o PyJWT-$(VERSION2).tar.gz; tar -zxf PyJWT-$(VERSION2).tar.gz)
	(cd $(CONTRIB2); cd PyJWT-$(VERSION2); patch < ../../patches/jwt_remove_setup_required)
	(cd $(CONTRIB2); cd PyJWT-$(VERSION2); find . -name \*.pyc -exec rm {} \;)
	(cd $(CONTRIB2); cd PyJWT-$(VERSION2); python setup.py sdist; cp dist/* ..)
	(cd $(CONTRIB2); py2dsc -m '$(ME)' PyJWT-$(VERSION2).tar.gz)
	(cd $(CONTRIB2)/deb_dist/pyjwt-$(VERSION2)/debian/; patch < ../../../../patches/jwt_add_provides)
	(cd $(CONTRIB2)/deb_dist/pyjwt-$(VERSION2); dch -v $(VERSION2)-2$(series)1 --distribution $(series) -M "built for privacyidea")
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


pymysql:
	mkdir -p $(CONTRIB5)
	mkdir -p DEBUILD
	(cd $(CONTRIB5); curl $(URL5) -o PyMySQL-$(VERSION5).tar.gz) 
	(cd $(CONTRIB5); py2dsc -m '$(ME)' PyMySQL-$(VERSION5).tar.gz)
	(cd $(CONTRIB5)/deb_dist/pymysql-$(VERSION5); dch -v $(VERSION5)-1$(series)1 --distribution $(series) -M "built for privacyidea")
	(cd $(CONTRIB5)/deb_dist/pymysql-$(VERSION5); debuild -sa -S)
	(cd $(CONTRIB5)/deb_dist/pymysql-$(VERSION5); debuild -b)
	(cp $(CONTRIB5)/deb_dist/* DEBUILD || true)
	#
	mkdir -p $(CONTRIB6)
	mkdir -p DEBUILD
	(cd $(CONTRIB6); curl $(URL6) -o pymysql_sa-$(VERSION6).tar.gz) 
	(cd $(CONTRIB6); py2dsc -m '$(ME)' pymysql_sa-$(VERSION6).tar.gz)
	(cd $(CONTRIB6)/deb_dist/pymysql-sa-$(VERSION6); dch -v $(VERSION6)-1$(series)1 --distribution $(series) -M "built for privacyidea")
	(cd $(CONTRIB6)/deb_dist/pymysql-sa-$(VERSION6); debuild -sa -S)
	(cd $(CONTRIB6)/deb_dist/pymysql-sa-$(VERSION6); debuild -b)
	(cp $(CONTRIB6)/deb_dist/* DEBUILD || true)

pykcs11:
	mkdir -p $(CONTRIB7)
	mkdir -p DEBUILD
	(cd $(CONTRIB7); curl $(URL7) -o PyKCS11-$(VERSION7).tar.gz)
	(cd $(CONTRIB7); py2dsc -m '$(ME)' PyKCS11-$(VERSION7).tar.gz)
	(cd $(CONTRIB7)/deb_dist/pykcs11-$(VERSION7); dch -v $(VERSION7)-1$(series)1 --distribution $(series) -M "built for privacyidea")
	(cd $(CONTRIB7)/deb_dist/pykcs11-$(VERSION7); debuild -sa -S)
	(cd $(CONTRIB7)/deb_dist/pykcs11-$(VERSION7); debuild -b)
	(cp $(CONTRIB7)/deb_dist/* DEBUILD || true)

	


ppa-dev:
	(cd DEBUILD; dput -f ppa:privacyidea/privacyidea-dev flask-cache_${VERSION1}-1${series}1_source.changes || true )
	(cd DEBUILD; dput -f ppa:privacyidea/privacyidea-dev pyjwt_${VERSION2}-1${series}1_source.changes || true)
	(cd DEBUILD; dput -f ppa:privacyidea/privacyidea-dev ldap3_${VERSION3}-1${series}1_source.changes || true)
	(cd DEBUILD; dput -f ppa:privacyidea/privacyidea-dev flask-sqlalchemy_${VERSION4}-1${series}1_source.changes || true)
	(cd DEBUILD; dput -f ppa:privacyidea/privacyidea-dev pymysql_${VERSION5}-1${series}1_source.changes || true)

ppa:
	(cd DEBUILD; dput -f ppa:privacyidea/privacyidea flask-cache_${VERSION1}-1${series}1_source.changes || true)
	(cd DEBUILD; dput -f ppa:privacyidea/privacyidea pyjwt_${VERSION2}-1${series}1_source.changes || true)
	(cd DEBUILD; dput -f ppa:privacyidea/privacyidea ldap3_${VERSION3}-1${series}1_source.changes || true)
	(cd DEBUILD; dput -f ppa:privacyidea/privacyidea flask-sqlalchemy_${VERSION4}-1${series}1_source.changes || true)
	(cd DEBUILD; dput -f ppa:privacyidea/privacyidea pymysql_${VERSION5}-1${series}1_source.changes || true)

	

clean:
	rm -fr $(CONTRIB1)
	rm -fr $(CONTRIB2)
	rm -fr $(CONTRIB3)
	rm -fr $(CONTRIB4)
	rm -fr $(CONTRIB5)
	rm -fr DEBUILD
