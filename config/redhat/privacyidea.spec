%define name privacyidea
%define version 1.3.1~dev0
%define unmangled_version 1.3.1-dev0
%define release 1

Summary: two-factor authentication system e.g. for OTP devices
Name: %{name}
Version: %{version}
Release: %{release}
Group: System/Authentication
Prefix: /usr
Provides: privacyidea
Requires: python-setuptools python-pylons >= 0.9.7 python-webob >= 1.2 python-qrcode python-netaddr python-ldap python-pyrad python-yaml python-configobj python-repoze-who python-httplib2 python-crypto python-docutils
Source0: %{name}-%{version}.tar.gz
License: AGPL v3
BuildRoot: %{_tmppath}/%{name}-%{version}-%{release}-buildroot
BuildArch: noarch
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
#echo "HALLO ICH BIN HIER!"
#echo $RPM_BUILD_ROOT

%clean
rm -rf $RPM_BUILD_ROOT

#%files -f INSTALLED_FILES
%files
%(config) /etc/privacyidea/*
/usr/lib/python2.6/site-packages/privacyidea/*
/usr/bin/*
/usr/lib/privacyidea/authmodules/FreeRADIUS/*
/usr/lib/privacyidea/authmodules/OTRS/*
/usr/lib/python2.6/site-packages/privacyIDEA-1.2.1_dev0-py2.6.egg-info/*
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
if [ ! -e /etc/privacyidea/encKey ]; then
	dd if=/dev/urandom of=/etc/privacyidea/encKey bs=1 count=96
fi
paster setup-app /etc/privacyidea/privacyidea.ini
chown -R $USERNAME /var/log/privacyidea
chown -R $USERNAME /var/lib/privacyidea
chown -R $USERNAME /etc/privacyidea
chown -R $USERNAME /var/run/privacyidea
chmod 600 /etc/privacyidea/encKey
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
* Fri Jul 18 2014 Cornelius Kölbel <cornelius.koelbel@netknights.it>

- initial build for version 1.2.1
