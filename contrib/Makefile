CONTRIB1=python-flask-cache
URL1=https://pypi.python.org/packages/source/F/Flask-Cache/Flask-Cache-0.13.1.tar.gz
VERSION1=0.13.1

CONTRIB2=python-pyjwt
URL2=https://pypi.python.org/packages/source/P/PyJWT/PyJWT-0.4.3.tar.gz
VERSION2=0.4.3

CONTRIB3=python-ldap3
URL3=https://pypi.python.org/packages/source/l/ldap3/ldap3-0.9.8.2.tar.gz
VERSION3=0.9.8.2

CONTRIB4=python-flask-migrate
VERSION4=1.3.0

CONTRIB5=python-flask-sqlalchemy
DATE=`date +"%Y%m%d"`
VERSION5=2.0-$(DATE)
URL5=https://github.com/mitsuhiko/flask-sqlalchemy.git

CONTRIB6=python-flask-script
VERSION6=2.0.6
URL6=https://github.com/smurfix/flask-script.git

CONTRIB7=python-flask
TAG7=0.10.1
VERSION7=$(TAG7)-$(DATE)
URL7=https://github.com/mitsuhiko/flask.git

CONTRIB8=python-itsdangerous
TAG8=0.24
VERSION8=$(TAG8)-$(DATE)
URL8=https://github.com/mitsuhiko/itsdangerous.git

CONTRIB9=python-pillow
TAG9=2.7.0
VERSION9=$(TAG9)
URL9=https://github.com/python-pillow/Pillow.git

CONTRIB10=python-cffi
VERSION10=0.8.6
URL10=https://pypi.python.org/packages/source/c/cffi/cffi-0.8.6.tar.gz

CONTRIB11=python-bcrypt
VERSION11=1.1.0
URL11=https://pypi.python.org/packages/source/b/bcrypt/bcrypt-1.1.0.tar.gz

CONTRIB12=python-qrcode
VERSION12=5.1
URL12=https://pypi.python.org/packages/source/q/qrcode/qrcode-5.1.tar.gz

CONTRIB13=python-sqlsoup
VERSION13=0.9.0
URL13=https://pypi.python.org/packages/source/s/sqlsoup/sqlsoup-0.9.0.tar.gz

ME=Cornelius Kölbel <cornelius@privacyidea.org>

info:
	@echo "make ubuntu - build packages for ubuntu 14.04LTS"
	@echo "make wheezy - build packages for Wheezy"
	@echo "make clean."

ubuntu:
	make clean
	make pyjwt
	make flask-cache
	make ldap3

wheezy:
	make clean 
	make pyjwt || true
	make flask-cache || true
	make ldap3 || true
	make flask-migrate || true
	make flask-sqlalchemy || true
	make flask-script || true
	make flask || true
	make itsdangerous || true
	make pillow || true
	make cffi || true
	make bcrypt || true
	make qrcode || true
	make sqlsoup || true


bcrypt:
	mkdir -p $(CONTRIB11)
	(cd $(CONTRIB11); curl $(URL11) -o bcrypt.tgz; tar -zxf bcrypt.tgz) 
	(cd $(CONTRIB11); cd bcrypt-$(VERSION11); python setup.py sdist; cp dist/* ..)
	(cd $(CONTRIB11); py2dsc -m '$(ME)' bcrypt-$(VERSION11).tar.gz || true)
	(cd $(CONTRIB11)/deb_dist; rm -fr bcrypt-$(VERSION11).orig)
	(cd $(CONTRIB11)/deb_dist; rm -fr bcrypt_$(VERSION11).orig.tar.gz)
	(cd $(CONTRIB11)/deb_dist; cp -r bcrypt-$(VERSION11) bcrypt-$(VERSION11).orig)
	(cd $(CONTRIB11)/deb_dist; tar -zcf bcrypt_$(VERSION11).orig.tar.gz bcrypt-$(VERSION11).orig --exclude=debian)  
	(cd $(CONTRIB11)/deb_dist/bcrypt-$(VERSION11); debuild --no-lintian || true)
	(cd $(CONTRIB11)/deb_dist; cp -r bcrypt-$(VERSION11) bcrypt-$(VERSION11).orig)
	(cd $(CONTRIB11)/deb_dist; tar -zcf bcrypt_$(VERSION11).orig.tar.gz bcrypt-$(VERSION11).orig --exclude=debian)  
	(cd $(CONTRIB11)/deb_dist/bcrypt-$(VERSION11); debuild --no-lintian)


#rm bcrypt-1.1.0.orig/ -fr
#rm bcrypt_1.1.0.orig.tar.gz 
#mkdir bcrypt-1.1.0.orig
#cp -r bcrypt-1.1.0/* bcrypt-1.1.0.orig
#tar -zcf bcrypt_1.1.0.orig.tar.gz bcrypt-1.1.0.orig/ --exclude=debian
#cd bcrypt-1.1.0
#debuild

cffi:
	mkdir -p $(CONTRIB10)
	(cd $(CONTRIB10); curl $(URL10) -o cffi.tgz; tar -zxf cffi.tgz) 
	(cd $(CONTRIB10); cd cffi-$(VERSION10); python setup.py sdist; cp dist/* ..)
	(cd $(CONTRIB10); py2dsc -m '$(ME)' cffi-$(VERSION10).tar.gz)
	(cd $(CONTRIB10)/deb_dist/cffi-$(VERSION10); debuild --no-lintian)


qrcode:
	mkdir -p $(CONTRIB12)
	(cd $(CONTRIB12); curl $(URL12) -o qrcode.tgz; tar -zxf qrcode.tgz) 
	(cd $(CONTRIB12); cd qrcode-$(VERSION12); python setup.py sdist; cp dist/* ..)
	(cd $(CONTRIB12); py2dsc -m '$(ME)' qrcode-$(VERSION12).tar.gz)
	(cd $(CONTRIB12)/deb_dist/qrcode-$(VERSION12); debuild --no-lintian)

sqlsoup:
	mkdir -p $(CONTRIB13)
	(cd $(CONTRIB13); curl $(URL13) -o sqlsoup.tgz; tar -zxf sqlsoup.tgz) 
	(cd $(CONTRIB13); cd sqlsoup-$(VERSION13); python setup.py sdist; cp dist/* ..)
	(cd $(CONTRIB13); py2dsc -m '$(ME)' sqlsoup-$(VERSION13).tar.gz)
	(cd $(CONTRIB13)/deb_dist/sqlsoup-$(VERSION13); debuild --no-lintian)



pillow:  
	mkdir -p $(CONTRIB9)
	(cd $(CONTRIB9); git clone $(URL9); cd Pillow; git checkout $(TAG9))
	(cd $(CONTRIB9); cd Pillow; touch setup.cfg)
	(cd $(CONTRIB9); cd Pillow; python setup.py sdist; cp dist/* ..)
	(cd $(CONTRIB9); py2dsc -m '$(ME)' Pillow-$(VERSION9).tar.gz)
	(cd $(CONTRIB9)/deb_dist/pillow-$(VERSION9); debuild --no-lintian)



flask:
	mkdir -p $(CONTRIB7)
	(cd $(CONTRIB7); git clone $(URL7); cd flask; git checkout $(TAG7))
	(cd $(CONTRIB7); cd flask; touch setup.cfg)
	(cd $(CONTRIB7); cd flask; python setup.py sdist; cp dist/* ..)
	(cd $(CONTRIB7); py2dsc -m '$(ME)' Flask-$(VERSION7).tar.gz)
	(cd $(CONTRIB7)/deb_dist/flask-$(VERSION7); debuild --no-lintian)

itsdangerous:
	mkdir -p $(CONTRIB8)
	(cd $(CONTRIB8); git clone $(URL8); cd itsdangerous; git checkout $(TAG8))
	(cd $(CONTRIB8); cd itsdangerous; touch setup.cfg)
	(cd $(CONTRIB8); cd itsdangerous; python setup.py sdist; cp dist/* ..)
	(cd $(CONTRIB8); py2dsc -m '$(ME)' itsdangerous-$(TAG8).tar.gz)
	(cd $(CONTRIB8)/deb_dist/itsdangerous-$(TAG8); debuild --no-lintian)


flask-script:
	mkdir -p $(CONTRIB6)
	(cd $(CONTRIB6); git clone $(URL6))
	(cd $(CONTRIB6); cd flask-script; touch setup.cfg)
	(cd $(CONTRIB6); cd flask-script; python setup.py sdist; cp dist/* ..)
	(cd $(CONTRIB6); py2dsc -m '$(ME)' Flask-Script-$(VERSION6).tar.gz)
	(cd $(CONTRIB6)/deb_dist/flask-script-$(VERSION6); debuild)


flask-sqlalchemy:
	mkdir -p $(CONTRIB5)
	(cd $(CONTRIB5); git clone $(URL5))
	(cd $(CONTRIB5); cd flask-sqlalchemy; python setup.py sdist; cp dist/* ..)
	(cd $(CONTRIB5); py2dsc -m '$(ME)' Flask-SQLAlchemy-$(VERSION5).tar.gz)
	(cd $(CONTRIB5)/deb_dist/flask-sqlalchemy-$(VERSION5); debuild)

flask-migrate:
	mkdir -p $(CONTRIB4)
	(cd $(CONTRIB4); git clone https://github.com/miguelgrinberg/Flask-Migrate.git)
	(cd $(CONTRIB4); cd Flask-Migrate; touch setup.cfg)
	(cd $(CONTRIB4); cd Flask-Migrate; python setup.py sdist; cp dist/* ..)
	(cd $(CONTRIB4); py2dsc -m '$(ME)' Flask-Migrate-$(VERSION4).tar.gz)
	(cd $(CONTRIB4)/deb_dist/flask-migrate-$(VERSION4); debuild)
	

ldap3:
	mkdir -p $(CONTRIB3)
	mkdir -p DEBUILD
	(cd $(CONTRIB3); curl $(URL3) -o temp.tgz; tar -zxf temp.tgz)
	(cd $(CONTRIB3); cd ldap3-$(VERSION3); touch setup.cfg)
#	(cd $(CONTRIB3); cd ldap3-$(VERSION3); patch < ../../patches/remove-generated-timestamp)
	(cd $(CONTRIB3); cd ldap3-$(VERSION3); python setup.py sdist; cp dist/* ..)
	(cd $(CONTRIB3); py2dsc -m '$(ME)' ldap3-$(VERSION3).tar.gz)
	(cd $(CONTRIB3)/deb_dist/ldap3-$(VERSION3); dch -i --distribution trusty -M "built for privacyidea")
	(cd $(CONTRIB3)/deb_dist/ldap3-$(VERSION3); debuild -sa -S)
	(cd $(CONTRIB3)/deb_dist/ldap3-$(VERSION3); debuild -b)
	(cp $(CONTRIB3)/deb_dist/* DEBUILD || true)


pyjwt:
	mkdir -p $(CONTRIB2)
	mkdir -p DEBUILD
	(cd $(CONTRIB2); curl $(URL2) -o temp.tgz; tar -zxf temp.tgz)
	(cd $(CONTRIB2); cd PyJWT-$(VERSION2); python setup.py sdist; cp dist/* ..)
	(cd $(CONTRIB2); py2dsc -m '$(ME)' PyJWT-$(VERSION2).tar.gz)
	(cd $(CONTRIB2)/deb_dist/pyjwt-$(VERSION2); dch -i --distribution trusty -M "built for privacyidea")
	(cd $(CONTRIB2)/deb_dist/pyjwt-$(VERSION2); debuild -sa -S)
	(cd $(CONTRIB2)/deb_dist/pyjwt-$(VERSION2); debuild -b)
	(cp $(CONTRIB2)/deb_dist/* DEBUILD || true)


flask-cache:
	mkdir -p $(CONTRIB1)
	mkdir -p DEBUILD
	(cd $(CONTRIB1); curl $(URL1) -o temp.tgz; tar -zxf temp.tgz) 
	(cd $(CONTRIB1); cd Flask-Cache-$(VERSION1); python setup.py sdist; cp dist/* ..)
	(cd $(CONTRIB1); py2dsc -m '$(ME)' Flask-Cache-$(VERSION1).tar.gz)
	(cd $(CONTRIB1)/deb_dist/flask-cache-$(VERSION1); dch -i --distribution trusty -M "built for privacyidea")
	(cd $(CONTRIB1)/deb_dist/flask-cache-$(VERSION1); debuild -sa -S)
	(cd $(CONTRIB1)/deb_dist/flask-cache-$(VERSION1); debuild -b)
	(cp $(CONTRIB1)/deb_dist/* DEBUILD || true)

ppa-dev:
	dput ppa:privacyidea/privacyidea-dev DEBUILD/flask-cache_${VERSION1}-*_source.changes || true
	dput ppa:privacyidea/privacyidea-dev DEBUILD/pyjwt_${VERSION2}-*_source.changes || true
	dput ppa:privacyidea/privacyidea-dev DEBUILD/ldap3_${VERSION3}-*_source.changes || true

ppa:
	dput ppa:privacyidea/privacyidea DEBUILD/flask-cache_${VERSION1}-*_source.changes || true
	dput ppa:privacyidea/privacyidea DEBUILD/pyjwt_${VERSION2}-*_source.changes || true
	dput ppa:privacyidea/privacyidea DEBUILD/ldap3_${VERSION3}-*_source.changes || true

	

clean:
	rm -fr $(CONTRIB1)
	rm -fr $(CONTRIB2)
	rm -fr $(CONTRIB3)
	rm -fr $(CONTRIB4)
	rm -fr $(CONTRIB5)
	rm -fr $(CONTRIB6)
	rm -fr $(CONTRIB7)
	rm -fr $(CONTRIB8)
	rm -fr $(CONTRIB9)
	rm -fr $(CONTRIB10)
	rm -fr $(CONTRIB11)
	rm -fr $(CONTRIB12)
	rm -fr $(CONTRIB13)
	rm -fr DEBUILD
