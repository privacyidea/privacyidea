CONTRIB1=python-flask-cache
VERSION1=0.13

CONTRIB2=python-pyjwt
VERSION2=0.4.1

CONTRIB3=python-ldap3
VERSION3=0.9.7.4

ME=Cornelius Kölbel <cornelius.koelbel@netknights.it>

all:
	make clean
	make pyjwt
	make flask-cache
	make ldap3
	

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
#	(cd $(CONTRIB2); cd pyjwt; git checkout $(VERSION2))
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
