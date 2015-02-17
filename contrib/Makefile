CONTRIB1=python-flask-cache
VERSION1=0.13

CONTRIB2=python-pyjwt
VERSION2=0.4.1

CONTRIB3=python-ldap3
VERSION3=0.9.7.4

CONTRIB4=python-flask-migrate
VERSION4=1.3.0

CONTRIB5=python-flask-sqlalchemy
VERSION5=2.0-20150217
URL5=https://github.com/mitsuhiko/flask-sqlalchemy.git

CONTRIB6=python-flask-script
VERSION6=2.0.6
URL6=https://github.com/smurfix/flask-script.git

ME=Cornelius Kölbel <cornelius.koelbel@netknights.it>


ubuntu:
	make clean
	make pyjwt
	make flask-cache
	make ldap3

debian:
	make clean
	make pyjwt
	make flask-cache
	make ldap3
	make flask-migrate
	make flask-sqlalchemy
	make flask-script

flask-script:
	mkdir -p $(CONTRIB6)
	(cd $(CONTRIB6); git clone $(URL6))
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
	(cd $(CONTRIB4); cd Flask-Migrate; python setup.py sdist; cp dist/* ..)
	(cd $(CONTRIB4); py2dsc -m '$(ME)' Flask-Migrate-$(VERSION4).tar.gz)
	(cd $(CONTRIB4)/deb_dist/flask-migrate-$(VERSION4); debuild)
	

ldap3:
	mkdir -p $(CONTRIB3)
	(cd $(CONTRIB3); git clone https://github.com/cannatag/ldap3.git)
	(cd $(CONTRIB3); cd ldap3; patch < ../../patches/remove-generated-timestamp)
	(cd $(CONTRIB3); cd ldap3; python setup.py sdist; cp dist/* ..)
	(cd $(CONTRIB3); py2dsc -m '$(ME)' ldap3-$(VERSION3).tar.gz)
	(cd $(CONTRIB3)/deb_dist/ldap3-$(VERSION3); debuild)


pyjwt:
	mkdir -p $(CONTRIB2)
	(cd $(CONTRIB2); git clone https://github.com/jpadilla/pyjwt.git)
	(cd $(CONTRIB2); cd pyjwt; python setup.py sdist; cp dist/* ..)
	(cd $(CONTRIB2); py2dsc -m '$(ME)' PyJWT-$(VERSION2).tar.gz)
	(cd $(CONTRIB2)/deb_dist/pyjwt-$(VERSION2); debuild)


flask-cache:
	mkdir -p $(CONTRIB1)
	(cd $(CONTRIB1); git clone https://github.com/thadeusb/flask-cache.git)
	(cd $(CONTRIB1); cd flask-cache; python setup.py sdist; cp dist/* ..)
	(cd $(CONTRIB1); py2dsc -m '$(ME)' Flask-Cache-$(VERSION1).tar.gz)
	(cd $(CONTRIB1)/deb_dist/flask-cache-$(VERSION1); debuild)
clean:
	rm -fr $(CONTRIB1)
	rm -fr $(CONTRIB2)
	rm -fr $(CONTRIB3)
	rm -fr $(CONTRIB4)
	rm -fr $(CONTRIB5)
	rm -fr $(CONTRIB6)
