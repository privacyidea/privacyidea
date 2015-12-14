%define name privacyidea
%define version 2.9~dev1
%define unmangled_version 2.9-dev1
%define release 1

Summary: two-factor authentication system e.g. for OTP devices
Name: %{name}
Version: %{version}
Release: %{release}
Group: System/Authentication
Prefix: /usr
Provides: privacyidea
Requires: python-flask-migrate python-qrcode python-netaddr python-flask python-flask-sqlalchemy python-pyrad python-yaml python-configobj python-beautifulsoup4 python-pandas python-matplotlib python-ecdsa python-pyjwt python-six python-crypto
Source0: %{name}-%{version}.tar.gz
License: AGPL v3
BuildRoot: %{_tmppath}/%{name}-%{version}-%{release}-buildroot
BuildArch: x86_64
Vendor: privacyidea.org <cornelius@privacyidea.org>
Url: http://www.privacyidea.org

%description
privacyIDEA
===========
privacyIDEA is an open solution for strong two-factor authentication.
privacyIDEA aims to not bind you to any decision of the authentication protocol or 
it does not dictate you where your user information should be stored. 
This is achieved by its totally modular architecture.
privacyIDEA is not only open as far as its modular architecture is concerned. 
But privacyIDEA is completely licensed under the AGPLv3.

%prep
%setup -n %{name}-%{version} -n %{name}-%{version}

%build
python setup.py build

%install
python setup.py install --single-version-externally-managed -O1 --root=$RPM_BUILD_ROOT --record=INSTALLED_FILES
mkdir -p $RPM_BUILD_ROOT/etc/privacyidea/
cp deploy/centos/pi.cfg $RPM_BUILD_ROOT/etc/privacyidea/
cp $RPM_BUILD_ROOT/usr/etc/privacyidea/dictionary $RPM_BUILD_ROOT/etc/privacyidea/
cp $RPM_BUILD_ROOT/usr/etc/privacyidea/*.wsgi $RPM_BUILD_ROOT/etc/privacyidea/
rm -fr $RPM_BUILD_ROOT/usr/etc 
# The installed files contains man pages as .1, but they will be .1.gz
# https://bugs.python.org/issue644744
#sed -e s/\.1$/.1*/g INSTALLED_FILES > INSTALLED_FILES_gz
# Remove all files .pyc and .pyo
#find $RPM_BUILD_ROOT -name \*.pyc -exec rm {} \;
#find $RPM_BUILD_ROOT -name \*.pyo -exec rm {} \;
#grep -v .pyc\$ INSTALLED_FILES_gz > INSTALLED_FILES
#grep -v .pyo\$ INSTALLED_FILES > INSTALLED_FILES_gz
#mv INSTALLED_FILES_gz INSTALLED_FILES

%clean
rm -rf $RPM_BUILD_ROOT

#%files -f INSTALLED_FILES
%files
%(config) /etc/privacyidea/*
/usr/lib/python2.7/site-packages/privacyidea/*
/usr/bin/*
/usr/lib/privacyidea/*
/usr/lib/python2.7/site-packages/authmodules/*
/usr/lib/python2.7/site-packages/privacyIDEA-*-info/*
/usr/share/man/man1/*
%defattr(-,root,root)

%post
# Post install
USERNAME=privacyidea
useradd -r $USERNAME -M
mkdir -p /var/log/privacyidea
mkdir -p /var/log/privacyidea
mkdir -p /var/lib/privacyidea
mkdir -p /var/run/privacyidea
touch /var/lib/privacyidea/token.sqlite
touch /var/log/privacyidea/privacyidea.log
if [ ! -e /etc/privacyidea/enckey ]; then
	dd if=/dev/urandom of=/etc/privacyidea/enckey bs=1 count=96
fi
#paster setup-app /etc/privacyidea/pi.cfg
chown -R $USERNAME /var/log/privacyidea
chown -R $USERNAME /var/lib/privacyidea
chown -R $USERNAME /etc/privacyidea
chown -R $USERNAME /var/run/privacyidea
chmod 600 /etc/privacyidea/enckey
# create certificate
if [ ! -e /etc/privacyidea/server.pem ]; then
        cd /etc/privacyidea
        openssl genrsa -out server.key 2048
        openssl req -new -key server.key -out server.csr -subj "/CN=privacyidea"
        openssl x509 -req -days 365 -in server.csr -signkey server.key -out server.crt
        cat server.crt server.key > server.pem
        rm -f server.crt server.key
        chown privacyidea server.pem
        chmod 400 server.pem
fi
echo
echo "=================================================================================================="
echo " 1. start privacyidea "
echo "    service privacyidea start"
echo " 2. Create your administrator like this: "
echo "    privacyidea-create-pwidresolver-user -u admin -p test -i 1000 >> /etc/privacyidea/admin-users"
echo " 3. and login at https://localhost:5001 with the user admin@admin"
echo "=================================================================================================="


%postun
# Post uninstall

%changelog
* Mon Dec 14 2015 Cornelius Kölbel <cornelius.koelbel@netknights.it>

- set version 2.9 dev1

