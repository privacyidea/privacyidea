import os
import unittest
from importlib.machinery import SourceFileLoader
from importlib.util import spec_from_loader, module_from_spec

SCRIPTS = [
    'creategoogleauthenticator-file',
    'getgooglecodes',
    'privacyidea-create-ad-users',
    'privacyidea-create-certificate',
    'privacyidea-create-pwidresolver-user',
    'privacyidea-create-sqlidresolver-user',
    'privacyidea-export-linotp-counter.py',
    'privacyidea-export-privacyidea-counter.py',
    'privacyidea-fix-access-rights',
    'privacyidea-migrate-linotp.py',
    'privacyidea-pip-update',
    'privacyidea-queue-huey',
    'privacyidea-sync-owncloud.py',
    'privacyidea-update-counter.py',
    'privacyidea-update-linotp-counter.py',
    'privacyidea-user-action',
    'ssha.py',
    '../pi-manage'
]


class ScriptsTestCase(unittest.TestCase):

    def test_01_loading_scripts(self):
        for script in SCRIPTS:
            with self.subTest(script=script):
                loader = SourceFileLoader(script, os.path.join('tools', script))
                spec = spec_from_loader(loader.name, loader)
                mod = module_from_spec(spec)
                loader.exec_module(mod)
