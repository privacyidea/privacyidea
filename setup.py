# -*- coding: utf-8 -*-
try:
    from setuptools import setup, find_packages
except ImportError:
    from ez_setup import use_setuptools
    use_setuptools()
    from setuptools import setup, find_packages

import os
import sys

# Taken from kennethreitz/requests/setup.py
package_directory = os.path.realpath(os.path.dirname(__file__))


def get_file_contents(file_path):
    """Get the context of the file using full path name."""
    content = ""
    try:
        full_path = os.path.join(package_directory, file_path)
        content = open(full_path, 'r').read()
    except:
        print >> sys.stderr, "### could not open file: %r" % file_path
    return content


def get_package():
    """
    returns a tuple of path.
    returns ("/", "/usr") if we do a pacakge installation.
    Then a file PRIVACYIDEA_PACKAGE needs to be created.
    """
    check_file = os.path.join(package_directory, "PRIVACYIDEA_PACKAGE")
    if os.path.isfile(check_file):
        return ("/", "/usr/")
    return ("", "")


setup(
    name='privacyIDEA',
    version='1.3',
    description='privacyIDEA: identity, multifactor authentication, '
                'authorization, audit',
    author='privacyidea.org',
    license='AGPL v3',
    author_email='cornelius@privacyidea.org',
    url='http://www.privacyidea.org',
    install_requires=["WebOb>=1.2,<1.4",
                      "Pylons>=0.9.7,<=1.0",
                      "SQLAlchemy>=0.6",
                      "docutils>=0.4",
                      "simplejson>=2.0",
                      "pycrypto>=1.0",
                      "repoze.who<=1.1",
                      "pyrad>=1.1",
                      "netaddr",
                      "qrcode>=2.4",
                      "configobj>=4.6.0",
                      "httplib2",
                      "pyyaml",
                      "python-ldap",
                      "Pillow",
                      "sqlsoup"
                      ],
    scripts=['tools/privacyidea-convert-token',
             'tools/privacyidea-create-pwidresolver-user',
             'tools/privacyidea-create-sqlidresolver-user',
             'tools/privacyidea-pip-update',
             'tools/privacyidea-create-enckey',
             'tools/privacyidea-create-auditkeys',
             'tools/privacyidea-create-certificate',
             'tools/privacyidea-create-database',
             'tools/privacyidea-fix-access-rights',
             'tools/totp-token',
             'tools/privacyidea-create-ad-users'
             ],
    setup_requires=["PasteScript>=1.6.3"],
    packages=find_packages(exclude=['ez_setup']),
    include_package_data=True,
    test_suite='nose.collector',
    data_files=[(get_package()[0] + 'etc/privacyidea/',
                 ['config/privacyidea.ini.example',
                  'config/privacyideaapp.wsgi',
                  'config/dictionary',
                  'config/dummy-encKey']),
                (get_package()[1] + 'share/man/man1',
                 ["tools/privacyidea-convert-token.1",
                  "tools/privacyidea-create-pwidresolver-user.1",
                  "tools/privacyidea-create-sqlidresolver-user.1",
                  "tools/totp-token.1",
                  "tools/privacyidea-pip-update.1",
                  "tools/privacyidea-create-enckey.1",
                  "tools/privacyidea-create-auditkeys.1",
                  "tools/privacyidea-create-certificate.1",
                  "tools/privacyidea-create-database.1",
                  "tools/privacyidea-fix-access-rights.1"
                  ]),
                (get_package()[1] + 'lib/privacyidea/authmodules/FreeRADIUS',
                 ["authmodules/FreeRADIUS/LICENSE",
                  "authmodules/FreeRADIUS/privacyidea_radius.pm"]),
                (get_package()[1] + 'lib/privacyidea/authmodules/OTRS',
                 ["authmodules/OTRS/privacyIDEA.pm"])
                ],
    classifiers=["Framework :: Pylons",
                 "License :: OSI Approved :: "
                 "GNU Affero General Public License v3",
                 "Programming Language :: Python",
                 "Development Status :: 5 - Production/Stable",
                 "Topic :: Internet",
                 "Topic :: Security",
                 "Topic :: System ::"
                 " Systems Administration :: Authentication/Directory"
                 ],
    message_extractors={'privacyidea': [
            ('**.py', 'python', None),
            ('templates/**.mako', 'mako', {'input_encoding': 'utf-8'}),
            ('lib/tokens/*.mako', 'mako', {'input_encoding': 'utf-8'}),
            ('public/**', 'ignore', None)]},
    zip_safe=False,
    paster_plugins=['PasteScript', 'Pylons'],
    entry_points="""
    [paste.app_factory]
    main = privacyidea.config.middleware:make_app

    [paste.app_install]
    main = pylons.util:PylonsInstaller

    [nose.plugins]
    pylons = pylons.test:PylonsPlugin
    """,
    long_description=get_file_contents('README.md')
)
