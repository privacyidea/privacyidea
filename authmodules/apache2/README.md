This is the Apache module to be used with mod_python with the
privacyIDEA authentication system to add OTP to Apache basic authentication.
To protect an Apache directory or Location add this to your apache config:

    <Directory /var/www/html/secretdir>
        AuthType Basic
        AuthName "Protected Area"
        AuthBasicProvider wsgi
        WSGIAuthUserScript /usr/share/pyshared/privacyidea_apache.py
        Require valid-user
    </Directory>

The users authentication state is stored in a usually local redis database.

The code is tested in test_mod_apache.py

