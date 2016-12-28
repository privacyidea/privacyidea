# -*- coding: utf-8 -*-
from setuptools import setup, find_packages
import os
import glob
import sys

#VERSION="2.1dev4"
VERSION="2.17dev6"

# Taken from kennethreitz/requests/setup.py
package_directory = os.path.realpath(os.path.dirname(__file__))


def get_file_contents(file_path):
    """Get the context of the file using full path name."""
    content = ""
    try:
        full_path = os.path.join(package_directory, file_path)
        content = open(full_path, 'r').read()
    except:
        print >> sys.stderr, "### could not open file {0!r}".format(file_path)
    return content

def get_file_list(file_path):
    full_path = os.path.join(package_directory, file_path)
    file_list = os.listdir(full_path)
    # now we need to add the path to the files
    return [ file_path + f for f in file_list ]


install_requires = ["Flask>=0.10.1",
                    "Flask-Migrate>=1.2.0",
                    "Flask-SQLAlchemy>=2.0",
                    "Flask-Script>=2.0.5",
                    "Jinja2>=2.7.3",
                    "Mako>=0.9.1",
                    "MarkupSafe>=0.23",
                    "PyMySQL>=0.6.6",
                    "Pillow>=2.6.1",
                    "PyJWT>=1.3.0",
                    "PyYAML>=3.11",
                    "Pygments>=2.0.2",
                    "SQLAlchemy>=1.0.5",
                    "Werkzeug>=0.10.4",
                    "alembic>=0.6.7",
                    "argparse>=1.2.1",
                    "bcrypt>=1.1.0",
                    "beautifulsoup4>=4.3.2",
                    "cffi>=0.8.6",
                    "configobj>=5.0.6",
                    "docutils>=0.12",
                    "funcparserlib>=0.3.6",
                    "itsdangerous>=0.24",
                    "ldap3>=0.9.8.4",
                    "netaddr>=0.7.12",
                    "passlib>=1.6.2",
                    "pyasn1>=0.1.7",
                    "pyOpenSSL>=0.15.1",
                    "pycparser>=2.10",
                    "pycrypto>=2.6.1",
                    "pyrad>=2.0",
                    "pyusb>=1.0.0b2",
                    "qrcode>=5.1",
                    "requests>=2.7.0",
                    "sqlsoup>=0.9.0",
                    "ecdsa>=0.13",
                    "lxml>=3.3",
                    "python-gnupg>=0.3.8"
                    ]

# For python 2.6 we need additional dependency importlib
try:
    import importlib
except ImportError:
    install_requires.append('importlib')

setup(
    name='privacyIDEA',
    version=VERSION,
    description='privacyIDEA: identity, multifactor authentication (OTP), '
                'authorization, audit',
    author='privacyidea.org',
    license='AGPLv3',
    author_email='cornelius@privacyidea.org',
    url='http://www.privacyidea.org',
    keywords='OTP, two factor authentication, management, security',
    packages=find_packages(),
    scripts=['pi-manage',
             'tools/privacyidea-convert-token',
             'tools/privacyidea-create-pwidresolver-user',
             'tools/privacyidea-create-sqlidresolver-user',
             'tools/privacyidea-pip-update',
             'tools/privacyidea-create-certificate',
             'tools/privacyidea-fix-access-rights',
             'tools/privacyidea-create-ad-users',
             'tools/privacyidea-fetchssh',
             'tools/privacyidea-create-userdb',
             'tools/privacyidea-get-serial'
             ],
    extras_require={
        'dev': ["Sphinx>=1.3.1",
                "sphinxcontrib-httpdomain>=1.3.0"],
        'test': ["coverage>=3.7.1",
                 "mock>=1.0.1",
                 "pyparsing>=2.0.3",
                 "nose>=1.3.4",
                 "responses>=0.4.0",
                 "six>=1.8.0"],
    },
    install_requires=install_requires,
    include_package_data=True,
    data_files=[('etc/privacyidea/',
                 ['deploy/apache/privacyideaapp.wsgi',
                  'deploy/privacyidea/dictionary',
                  'deploy/privacyidea/enckey',
                  'deploy/privacyidea/private.pem',
                  'deploy/privacyidea/public.pem']),
                ('share/man/man1',
                 ["tools/privacyidea-convert-token.1",
                  "tools/privacyidea-create-pwidresolver-user.1",
                  "tools/privacyidea-create-sqlidresolver-user.1",
                  "tools/privacyidea-pip-update.1",
                  "tools/privacyidea-create-certificate.1",
                  "tools/privacyidea-fix-access-rights.1",
		  "tools/privacyidea-create-userdb.1",
		  "tools/privacyidea-create-ad-users.1",
		  "tools/privacyidea-fetchssh.1"
                  ]),
                ('lib/privacyidea/authmodules/FreeRADIUS',
                 ["authmodules/FreeRADIUS/LICENSE",
                  "authmodules/FreeRADIUS/privacyidea_radius.pm"]),
                ('lib/privacyidea/authmodules/OTRS',
                 ["authmodules/OTRS/privacyIDEA.pm"]),
                ('lib/privacyidea/migrations',
                 ["migrations/alembic.ini",
                  "migrations/env.py",
                  "migrations/README",
                  "migrations/script.py.mako"]),
                ('lib/privacyidea/migrations/versions',
                 get_file_list("migrations/versions/"))
                ],
    classifiers=["Framework :: Flask",
                 "License :: OSI Approved :: "
                 "GNU Affero General Public License v3",
                 "Programming Language :: Python",
                 "Development Status :: 5 - Production/Stable",
                 "Topic :: Internet",
                 "Topic :: Security",
                 "Topic :: System ::"
                 " Systems Administration :: Authentication/Directory"
                 ],
    #message_extractors={'privacyidea': [
    #        ('**.py', 'python', None),
    #        ('static/**.html', 'html', {'input_encoding': 'utf-8'})]},
    zip_safe=False,
    long_description=get_file_contents('README.rst')
)
