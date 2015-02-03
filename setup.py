# -*- coding: utf-8 -*-
from distutils.core import setup
import os
import sys

VERSION="2.0dev1"

# Taken from kennethreitz/requests/setup.py
package_directory = os.path.realpath(os.path.dirname(__file__))


def get_file_contents(file_path):
    """Get the context of the file using full path name."""
    content = ""
    try:
        full_path = os.path.join(package_directory, file_path)
        content = open(full_path, 'r').read()
    except:
        print >> sys.stderr, "### could not open file %r" % file_path
    return content


setup(
    name='privacyIDEA',
    version=VERSION,
    description='privacyIDEA: identity, multifactor authentication, '
                'authorization, audit',
    author='privacyidea.org',
    license='AGPLv3',
    author_email='cornelius@privacyidea.org',
    url='http://www.privacyidea.org',
    packages=['privacyidea'],
    scripts=['manage.py',
             'tools/privacyidea-convert-token',
             'tools/privacyidea-create-pwidresolver-user',
             'tools/privacyidea-create-sqlidresolver-user',
             'tools/privacyidea-pip-update',
             'tools/privacyidea-create-enckey',
             'tools/privacyidea-create-auditkeys',
             'tools/privacyidea-create-certificate',
             'tools/privacyidea-create-database',
             'tools/privacyidea-fix-access-rights',
             'tools/totp-token',
             'tools/privacyidea-create-ad-users',
             'tools/privacyidea-setup',
             'tools/privacyidea-backup',
             'tools/privacyidea-restore'
             ],
    install_requires=[],
    include_package_data=True,
    data_files=[('etc/privacyidea/',
                 ['deploy/privacyideaapp.wsgi',
                  'tests/testdata/dictionary']),
                ('share/man/man1',
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
                ('lib/privacyidea/authmodules/FreeRADIUS',
                 ["authmodules/FreeRADIUS/LICENSE",
                  "authmodules/FreeRADIUS/privacyidea_radius.pm"]),
                ('lib/privacyidea/authmodules/OTRS',
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
            ('static/**.html', 'html', {'input_encoding': 'utf-8'})]},
    zip_safe=False,
    long_description=get_file_contents('README.md')
)
