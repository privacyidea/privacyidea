from setuptools import setup, find_packages
import os
import stat
import sys

VERSION = "3.11.1"

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


install_requires = [
    "argon2_cffi",
    "beautifulsoup4[lxml]",
    "cbor2",
    "configobj",
    "croniter",
    "cryptography",
    "defusedxml",
    "Flask",
    "Flask-Babel",
    "Flask-Migrate",
    "Flask-SQLAlchemy",
    "Flask-Versioned",
    "feedparser",
    "google-auth",
    "grpcio",
    "huey[redis]",
    "ldap3<2.9",
    "MarkupSafe",
    "netaddr",
    "passlib[bcrypt]",
    "protobuf",
    "pydash",
    "PyJWT",
    "PyMySQL",
    "pyOpenSSL<=24.0.0",
    "pyrad",
    "python-dateutil",
    "python-gnupg",
    "PyYAML",
    "requests",
    "segno",
    "smpplib",
    "SQLAlchemy<2.0",
    "webauthn"
]


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
    description='privacyIDEA: multifactor authentication management system',
    author='privacyidea.org',
    license='AGPLv3',
    author_email='cornelius@privacyidea.org',
    url='https://www.privacyidea.org',
    keywords='OTP, two factor authentication, management, security',
    python_requires='>=3.8',
    packages=find_packages(),
    scripts=get_scripts("tools"),
    entry_points={
        'console_scripts': [
            'privacyidea-token-janitor = privacyidea.cli.privacyideatokenjanitor:cli',
            'pi-manage = privacyidea.cli.pimanage:cli',
            'privacyidea-standalone = privacyidea.cli.tools.standalone:cli',
            'privacyidea-get-serial = privacyidea.cli.tools.get_serial:byotp_call',
            'privacyidea-usercache-cleanup = privacyidea.cli.tools.usercache_cleanup:delete_call',
            'privacyidea-get-unused-tokens = privacyidea.cli.tools.get_unused_tokens:cli',
            'privacyidea-expired-users = privacyidea.cli.tools.expired_users:expire_call',
            'privacyidea-cron = privacyidea.cli.tools.cron:cli',
            'pi-tokenjanitor = privacyidea.cli.pitokenjanitor:cli'
        ]},
    extras_require={
        'doc': ["Pallets-Sphinx-Themes",
                "Sphinx",
                "sphinxcontrib-httpdomain",
                "sphinxcontrib-spelling"],
        'test': ["mock",
                 "pyparsing",
                 "pytest",
                 "pytest-cov",
                 "responses",
                 "testfixtures"],
        'postgres': ['psycopg2'],
        'hsm': ['PyKCS11'],
        'kerberos': ['gssapi']
    },
    install_requires=install_requires,
    include_package_data=True,
    data_files=[('etc/privacyidea/',
                 ['deploy/apache/privacyideaapp.wsgi',
                  'deploy/privacyidea/dictionary']),
                ('share/man/man1', get_man_pages("tools")),
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
                 'Programming Language :: Python :: 3',
                 'Programming Language :: Python :: 3.8',
                 'Programming Language :: Python :: 3.9',
                 'Programming Language :: Python :: 3.10',
                 'Programming Language :: Python :: 3.11',
                 'Programming Language :: Python :: 3.12'
                 ],
    zip_safe=False,
    long_description=get_file_contents('README.rst')
)
