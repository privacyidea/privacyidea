# -*- coding: utf-8 -*-
from __future__ import print_function
from setuptools import setup, find_packages
import os
import stat
import sys

#VERSION="2.1dev4"
VERSION="3.0.2dev2"

# Taken from kennethreitz/requests/setup.py
package_directory = os.path.realpath(os.path.dirname(__file__))


def get_file_contents(file_path):
    """Get the context of the file using full path name."""
    content = ""
    try:
        full_path = os.path.join(package_directory, file_path)
        content = open(full_path, 'r').read()
    except:
        print("### could not open file {0!r}".format(file_path), file=sys.stderr)
    return content


def get_file_list(file_path):
    full_path = os.path.join(package_directory, file_path)
    file_list = os.listdir(full_path)
    # now we need to add the path to the files
    return [file_path + f for f in file_list]


install_requires = ["Flask>=0.10.1",
                    "Flask-Migrate>=1.2.0",
                    "Flask-SQLAlchemy>=2.0",
                    "Flask-Script>=2.0.5",
                    "Jinja2>=2.10.1",
                    "Mako>=0.9.1",
                    "PyMySQL>=0.6.6",
                    "Pillow>=2.6.1",
                    "PyJWT>=1.3.0",
                    "PyYAML>=5.1",
                    "SQLAlchemy>=1.3.0",
                    "Werkzeug>=0.10.4",
                    "alembic>=0.6.7",
                    "bcrypt>=1.1.0",
                    "beautifulsoup4>=4.3.2",
                    "ldap3>=2.6",
                    "netaddr>=0.7.12",
                    "passlib>=1.6.2",
                    "pyOpenSSL>=17.5",
                    "pyrad>=2.0",
                    "qrcode>=5.1",
                    "requests>=2.7.0",
                    "sqlsoup>=0.9.0",
                    "ecdsa>=0.13",
                    "lxml>=4.2.5",
                    "python-gnupg>=0.4.4",
                    "defusedxml>=0.4.1",
                    "flask-babel>=0.9",
                    "croniter>=0.3.8",
                    "oauth2client>=2.0.1",
                    "configobj>=5.0.6"
                    ]

# For python 2.6 we need additional dependency importlib
try:
    import importlib
except ImportError:
    install_requires.append('importlib')


def get_man_pages(dir):
    """
    Get man pages in a directory.
    :param dir: 
    :return: list of file names
    """
    files = os.listdir(dir)
    r_files = []
    for file in files:
        if file.endswith(".1"):
            r_files.append(dir + "/" + file)
    return r_files


def get_scripts(dir):
    """
    Get files that are executable
    :param dir: 
    :return: list of file names
    """
    files = os.listdir(dir)
    r_files = []
    for file in files:
        if os.stat(dir + "/" + file)[stat.ST_MODE] & stat.S_IEXEC:
            r_files.append(dir + "/" + file)
    return r_files


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
    python_requires='>=2.7, !=3.0.*, !=3.1.*, !=3.2.*, !=3.3.*, !=3.4.*, !=3.5.*',
    packages=find_packages(),
    scripts=["pi-manage"] + get_scripts("tools"),
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
                  'deploy/privacyidea/dictionary']),
                ('share/man/man1', get_man_pages("tools")),
               ('lib/privacyidea/authmodules/OTRS',
                 ["authmodules/OTRS/privacyIDEA.pm"]),
                ('lib/privacyidea/migrations',
                 ["migrations/alembic.ini",
                  "migrations/env.py",
                  "migrations/README",
                  "migrations/script.py.mako"]),
                ('lib/privacyidea/migrations/versions',
                 get_file_list("migrations/versions/")),
                ('lib/privacyidea/', ['requirements.txt'])
                ],
    classifiers=["Framework :: Flask",
                 "License :: OSI Approved :: "
                 "GNU Affero General Public License v3",
                 "Programming Language :: Python",
                 "Development Status :: 5 - Production/Stable",
                 "Topic :: Internet",
                 "Topic :: Security",
                 "Topic :: System ::"
                 " Systems Administration :: Authentication/Directory",
                 'Programming Language :: Python',
                 'Programming Language :: Python :: 2',
                 'Programming Language :: Python :: 2.7',
                 'Programming Language :: Python :: 3',
                 'Programming Language :: Python :: 3.6',
                 'Programming Language :: Python :: 3.7'
                 ],
    #message_extractors={'privacyidea': [
    #        ('**.py', 'python', None),
    #        ('static/**.html', 'html', {'input_encoding': 'utf-8'})]},
    zip_safe=False,
    long_description=get_file_contents('README.rst')
)
